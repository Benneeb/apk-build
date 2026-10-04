using Godot;
using System;
using System.IO;
using System.Security.Cryptography;
using System.Text;

namespace gEmuera.GodotHost
{
    internal static class AndroidGameMirror
    {
        const string RevisionMarkerName = ".gemuera-cache-revision";
        const string MirrorRevisionName = ".source_revision";
        const string SourceGameRootName = ".source_game_root";

        public static string PrepareGameDirectory(string sourceGameDir, Action<string> status = null)
        {
            if (!string.Equals(OS.GetName(), "Android", StringComparison.OrdinalIgnoreCase))
                return sourceGameDir;
            if (string.IsNullOrWhiteSpace(sourceGameDir) || !Directory.Exists(sourceGameDir))
                return sourceGameDir;

            sourceGameDir = Path.GetFullPath(sourceGameDir);
            string sourceMarker = Path.Combine(sourceGameDir, RevisionMarkerName);
            if (!File.Exists(sourceMarker))
                return sourceGameDir;

            string revision;
            try { revision = File.ReadAllText(sourceMarker, Encoding.UTF8).Trim(); }
            catch { return sourceGameDir; }
            if (revision.Length == 0)
                return sourceGameDir;

            string userRoot = OS.GetUserDataDir();
            if (string.IsNullOrWhiteSpace(userRoot))
                userRoot = ProjectSettings.GlobalizePath("user://");
            string mirrorRoot = Path.Combine(userRoot, "game-mirror", StablePathId(sourceGameDir));
            string mirrorRevision = Path.Combine(mirrorRoot, MirrorRevisionName);
            string sourceRootFile = Path.Combine(mirrorRoot, SourceGameRootName);

            // Always refresh the original external root marker. This also repairs
            // mirrors produced by v1, so the image fix does not require deleting cache.
            try
            {
                Directory.CreateDirectory(mirrorRoot);
                File.WriteAllText(sourceRootFile, sourceGameDir, new UTF8Encoding(false));
            }
            catch { }

            if (IsUsableMirror(mirrorRoot, mirrorRevision, revision))
            {
                status?.Invoke("Using optimized private game cache...");
                return NormalizeWithTrailingSlash(mirrorRoot);
            }

            try
            {
                status?.Invoke("Optimizing game files for Android (first run)...");
                bool existed = Directory.Exists(mirrorRoot);
                Directory.CreateDirectory(mirrorRoot);
                if (existed)
                    ClearMirrorPreservingUserData(mirrorRoot);
                CopySourceTree(sourceGameDir, mirrorRoot, existed, status);
                File.WriteAllText(mirrorRevision, revision, new UTF8Encoding(false));
                File.WriteAllText(sourceRootFile, sourceGameDir, new UTF8Encoding(false));
                if (IsUsableMirror(mirrorRoot, mirrorRevision, revision))
                    return NormalizeWithTrailingSlash(mirrorRoot);
            }
            catch (Exception e)
            {
                global::GenericUtils.Warn($"[STARTUP] Android private mirror unavailable: {e.Message}");
            }
            return sourceGameDir;
        }

        /// <summary>
        /// Resource images deliberately stay on shared storage. eraTWKR portrait packs
        /// are commonly installed/updated independently of ERB/CSV, and mirroring them
        /// made the engine use a stale or incomplete resources directory.
        /// </summary>
        public static string ResolveContentDirectory(string exeDir, string currentContentDir)
        {
            if (!string.Equals(OS.GetName(), "Android", StringComparison.OrdinalIgnoreCase))
                return currentContentDir;
            if (string.IsNullOrWhiteSpace(exeDir))
                return currentContentDir;

            try
            {
                string mirrorRoot = Path.GetFullPath(exeDir);
                string sourceRootFile = Path.Combine(mirrorRoot, SourceGameRootName);
                if (!File.Exists(sourceRootFile))
                    return currentContentDir;

                string sourceRoot = File.ReadAllText(sourceRootFile, Encoding.UTF8).Trim();
                if (sourceRoot.Length == 0 || !Directory.Exists(sourceRoot))
                    return currentContentDir;

                string lower = Path.Combine(sourceRoot, "resources");
                if (Directory.Exists(lower))
                {
                    string resolved = uEmuera.Utils.ResolveExistingDirectoryPath(lower);
                    global::GenericUtils.Info($"[LOAD] Android external ContentDir={resolved}");
                    return NormalizeWithTrailingSlash(resolved);
                }

                string upper = Path.Combine(sourceRoot, "RESOURCES");
                if (Directory.Exists(upper))
                {
                    string resolved = uEmuera.Utils.ResolveExistingDirectoryPath(upper);
                    global::GenericUtils.Info($"[LOAD] Android external ContentDir={resolved}");
                    return NormalizeWithTrailingSlash(resolved);
                }
            }
            catch (Exception e)
            {
                global::GenericUtils.Warn($"[STARTUP] External resources fallback unavailable: {e.Message}");
            }

            return currentContentDir;
        }

        static bool IsUsableMirror(string mirrorRoot, string revisionFile, string expectedRevision)
        {
            try
            {
                if (!Directory.Exists(mirrorRoot) || !File.Exists(revisionFile))
                    return false;
                string current = File.ReadAllText(revisionFile, Encoding.UTF8).Trim();
                if (!string.Equals(current, expectedRevision, StringComparison.Ordinal))
                    return false;
                return Directory.Exists(Path.Combine(mirrorRoot, "ERB")) ||
                       Directory.Exists(Path.Combine(mirrorRoot, "erb"));
            }
            catch { return false; }
        }

        static void ClearMirrorPreservingUserData(string mirrorRoot)
        {
            foreach (string dir in Directory.EnumerateDirectories(mirrorRoot))
            {
                if (IsPersistentRootName(Path.GetFileName(dir)))
                    continue;
                Directory.Delete(dir, true);
            }
            foreach (string file in Directory.EnumerateFiles(mirrorRoot))
            {
                string name = Path.GetFileName(file);
                if (string.Equals(name, "emuera.log", StringComparison.OrdinalIgnoreCase) ||
                    string.Equals(name, MirrorRevisionName, StringComparison.OrdinalIgnoreCase) ||
                    string.Equals(name, SourceGameRootName, StringComparison.OrdinalIgnoreCase))
                    continue;
                File.Delete(file);
            }
        }

        static void CopySourceTree(string sourceRoot, string targetRoot, bool preserveExistingUserData, Action<string> status)
        {
            int copied = 0;
            int skippedResources = 0;
            foreach (string sourceFile in Directory.EnumerateFiles(sourceRoot, "*", SearchOption.AllDirectories))
            {
                string relative = Path.GetRelativePath(sourceRoot, sourceFile);
                string first = FirstPathComponent(relative);

                // Images/resource CSVs are read from their original external folder.
                // This avoids duplicate storage and guarantees newly installed portraits
                // are visible immediately without bumping the script cache revision.
                if (IsResourceRootName(first))
                {
                    skippedResources++;
                    continue;
                }

                if (preserveExistingUserData && IsPersistentRootName(first))
                    continue;
                string targetFile = Path.Combine(targetRoot, relative);
                string targetDir = Path.GetDirectoryName(targetFile);
                if (!string.IsNullOrEmpty(targetDir))
                    Directory.CreateDirectory(targetDir);
                File.Copy(sourceFile, targetFile, true);
                copied++;
                if ((copied % 250) == 0)
                    status?.Invoke($"Optimizing game files... {copied}");
            }
            global::GenericUtils.Info($"[STARTUP] Android private mirror synchronized: files={copied}, resource_files_external={skippedResources}, source={sourceRoot}, target={targetRoot}");
        }

        static bool IsResourceRootName(string name) =>
            string.Equals(name, "resources", StringComparison.OrdinalIgnoreCase);

        static bool IsPersistentRootName(string name) =>
            string.Equals(name, "sav", StringComparison.OrdinalIgnoreCase) ||
            string.Equals(name, "save", StringComparison.OrdinalIgnoreCase) ||
            string.Equals(name, "debug", StringComparison.OrdinalIgnoreCase);

        static string FirstPathComponent(string relative)
        {
            int slash = relative.IndexOf(Path.DirectorySeparatorChar);
            int alt = relative.IndexOf(Path.AltDirectorySeparatorChar);
            if (slash < 0 || (alt >= 0 && alt < slash))
                slash = alt;
            return slash < 0 ? relative : relative.Substring(0, slash);
        }

        static string StablePathId(string path)
        {
            byte[] data = Encoding.UTF8.GetBytes(path.Replace('\\', '/').TrimEnd('/').ToLowerInvariant());
            using SHA256 sha = SHA256.Create();
            byte[] hash = sha.ComputeHash(data);
            return BitConverter.ToString(hash, 0, 8).Replace("-", "").ToLowerInvariant();
        }

        static string NormalizeWithTrailingSlash(string path)
        {
            string normalized = uEmuera.Utils.NormalizePath(path);
            return normalized.EndsWith("/", StringComparison.Ordinal) ? normalized : normalized + "/";
        }
    }
}
