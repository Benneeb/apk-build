#!/usr/bin/env python3
from pathlib import Path
import shutil
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
workspace = Path(__file__).resolve().parents[1]

def replace_exact(rel, old, new):
    path = root / rel
    text = path.read_text(encoding="utf-8-sig")
    if new in text:
        print(f"[already patched] {rel}")
        return
    if old not in text:
        raise SystemExit(f"Patch anchor not found in {rel}")
    text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")
    print(f"[patched] {rel}")

replace_exact(
    "Scripts/EmueraMain.cs",
    """\t\tif (!string.IsNullOrEmpty(eraPath) && uEmuera.Utils.DirectoryExists(eraPath))
\t\t{
\t\t\tSys.ExeDir = uEmuera.Utils.NormalizePath(eraPath + "/");
\t\t}""",
    """\t\tif (!string.IsNullOrEmpty(eraPath) && uEmuera.Utils.DirectoryExists(eraPath))
\t\t{
\t\t\t// Optional Android app-private mirror. Only opt-in games are mirrored.
\t\t\tif (string.Equals(OS.GetName(), "Android", StringComparison.OrdinalIgnoreCase))
\t\t\t{
\t\t\t\tUpdateStartupStatus("Optimizing game storage...");
\t\t\t\teraPath = AndroidGameMirror.PrepareGameDirectory(eraPath, UpdateStartupStatus);
\t\t\t}
\t\t\tSys.ExeDir = uEmuera.Utils.NormalizePath(eraPath + "/");
\t\t}"""
)

replace_exact(
    "Scripts/GodotHost/EmueraStartupComponent.cs",
    """        if (string.IsNullOrEmpty(eraPath) || !uEmuera.Utils.DirectoryExists(eraPath))
            eraPath = ProjectSettings.GlobalizePath(DefaultFallbackEraPath);

        if (!string.IsNullOrEmpty(eraPath) && uEmuera.Utils.DirectoryExists(eraPath))""",
    """        if (string.IsNullOrEmpty(eraPath) || !uEmuera.Utils.DirectoryExists(eraPath))
            eraPath = ProjectSettings.GlobalizePath(DefaultFallbackEraPath);

        if (!string.IsNullOrEmpty(eraPath) && uEmuera.Utils.DirectoryExists(eraPath) &&
            string.Equals(OS.GetName(), "Android", StringComparison.OrdinalIgnoreCase))
        {
            eraPath = gEmuera.GodotHost.AndroidGameMirror.PrepareGameDirectory(
                eraPath, status => EmitStatus(status));
        }

        if (!string.IsNullOrEmpty(eraPath) && uEmuera.Utils.DirectoryExists(eraPath))"""
)

replace_exact(
    "Scripts/Emuera/GameProc/Process.cs",
    """            Stopwatch loadStopwatch = Stopwatch.StartNew();
            void MarkLoad(string stage)
            {
                long ms = loadStopwatch.ElapsedMilliseconds;
                if (Config.DisplayReport)
                    GenericUtils.Info($"[LOADTIME] {stage}: {ms}ms");""",
    """            Stopwatch loadStopwatch = Stopwatch.StartNew();
            long lastLoadMarkMs = 0;
            void MarkLoad(string stage)
            {
                long ms = loadStopwatch.ElapsedMilliseconds;
                long deltaMs = ms - lastLoadMarkMs;
                lastLoadMarkMs = ms;
                string profileLine = $"[LOADTIME] {stage}: delta={deltaMs}ms cumulative={ms}ms";
                GenericUtils.Info(profileLine);"""
)

replace_exact(
    "Scripts/Emuera/GameProc/Process.cs",
    """                        File.AppendAllText(Path.Combine(dir, "load_times.log"),
                            $"[LOADTIME] {stage}: {ms}ms\\n");""",
    """                        File.AppendAllText(Path.Combine(dir, "load_times.log"),
                            profileLine + "\\n");
                        File.AppendAllText(Path.Combine(dir, "startup_profile.tsv"),
                            $"{DateTime.UtcNow:O}\\t{stage}\\t{deltaMs}\\t{ms}\\n");"""
)


replace_exact(
    "gemuera-c#.csproj",
    """    <None Include="NativeLibs\\android\\arm64-v8a\\libe_sqlite3.so" CopyToOutputDirectory="PreserveNewest" TargetPath="libe_sqlite3.so" />""",
    """    <None Include="NativeLibs\\android\\arm64-v8a\\libe_sqlite3.so" Condition="Exists('NativeLibs\\android\\arm64-v8a\\libe_sqlite3.so')" CopyToOutputDirectory="PreserveNewest" TargetPath="libe_sqlite3.so" />"""
)

src = workspace / "engine-overrides/AndroidGameMirror.cs"
dst = root / "Scripts/GodotHost/AndroidGameMirror.cs"
dst.parent.mkdir(parents=True, exist_ok=True)
shutil.copyfile(src, dst)
print(f"[overlay] {dst.relative_to(root)}")
