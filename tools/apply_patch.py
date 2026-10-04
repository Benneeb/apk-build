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


# Keep image/resource packs on the original external game folder even when
# scripts/CSV run from the Android app-private mirror.
replace_exact(
    "Scripts/Emuera/Program.cs",
    """			ContentDir = uEmuera.Utils.ResolveExistingDirectoryPath(ContentDir);
			GenericUtils.Info($"[LOAD] CsvDir={CsvDir}, ErbDir={ErbDir}");""",
    """			ContentDir = uEmuera.Utils.ResolveExistingDirectoryPath(ContentDir);
			if (Godot.OS.GetName() == "Android")
				ContentDir = global::gEmuera.GodotHost.AndroidGameMirror.ResolveContentDirectory(ExeDir, ContentDir);
			GenericUtils.Info($"[LOAD] CsvDir={CsvDir}, ErbDir={ErbDir}, ContentDir={ContentDir}");"""
)

# Use a PC-like logical width on high-resolution phone screens. The Godot root
# still occupies the whole safe area; Emuera content is scaled to it separately.
replace_exact(
    "Scripts/Emuera/Program.cs",
    """			if (safeWidth > 0 && System.Math.Abs(Config.WindowX - safeWidth) > 1)
			{
				int previousWidth = Config.WindowX;
				Config.UpdateWindowWidth(System.Math.Max(320, safeWidth));
				GenericUtils.Info($"[LOAD] Android dynamic window width: {previousWidth} -> {Config.WindowX}, safe={safeWidth}, viewport={viewportWidth}");
				return;
			}
			GenericUtils.Info($"[LOAD] Android keeps configured window width: {Config.WindowX}, safe={safeWidth}, viewport={viewportWidth}");""",
    """			int targetWidth = global::EmueraContent.GetAndroidLogicalContentWidth(safeWidth);
			if (targetWidth > 0 && System.Math.Abs(Config.WindowX - targetWidth) > 1)
			{
				int previousWidth = Config.WindowX;
				Config.UpdateWindowWidth(System.Math.Max(320, targetWidth));
				GenericUtils.Info($"[LOAD] Android logical window width: {previousWidth} -> {Config.WindowX}, target={targetWidth}, safe={safeWidth}, viewport={viewportWidth}");
				return;
			}
			GenericUtils.Info($"[LOAD] Android keeps logical window width: {Config.WindowX}, target={targetWidth}, safe={safeWidth}, viewport={viewportWidth}");"""
)

replace_exact(
    "Scripts/EmueraContent.cs",
    """	const int SystemButtonTouchSize = 48;""",
    """	static int SystemButtonTouchSize => OS.HasFeature("mobile") ? 56 : 48;"""
)

replace_exact(
    "Scripts/EmueraContent.cs",
    """		int targetWidth = System.Math.Max(MinDynamicContentWidth, ContentSafeWidth);""",
    """		int targetWidth = System.Math.Max(MinDynamicContentWidth, GetAndroidLogicalContentWidth(ContentSafeWidth));"""
)

replace_exact(
    "Scripts/EmueraContent.cs",
    """		ApplySafeAreaLayout(true);

		// Keep one-time MultiLanguage texts""",
    """		ApplySafeAreaLayout(true);
		ApplyMobileViewportScale();

		// Keep one-time MultiLanguage texts"""
)

replace_exact(
    "Scripts/EmueraContent.cs",
    """	void OnViewportSizeChanged()
	{
		ApplySafeAreaLayout();
		virtualCursor?.RefreshViewportBounds();
		QueueScaleBoundsUpdate();
	}""",
    """	void OnViewportSizeChanged()
	{
		ApplySafeAreaLayout();
		ApplyMobileViewportScale();
		virtualCursor?.RefreshViewportBounds();
		QueueScaleBoundsUpdate();
	}"""
)

replace_exact(
    "Scripts/EmueraContent.cs",
    """	public void SetContentScale(float scale)
	{
		if (scrollContainer != null)""",
    """	public void SetContentScale(float scale)
	{
		if (OS.HasFeature("mobile"))
			mobileAutoScaleEnabled = false;
		if (scrollContainer != null)"""
)

# Make direct in-console controls easier to tap without moving their visual content.
replace_exact(
    "Scripts/EmueraContent.cs",
    """		Rect2 hitRect = GetButtonVisualBounds(button, buttonTop, buttonHeight, button.PointX, button.PointX);""",
    """		Rect2 hitRect = ExpandMobileConsoleHitRect(GetButtonVisualBounds(button, buttonTop, buttonHeight, button.PointX, button.PointX));"""
)

# All Canvas button hit rectangles pass through this one registration point.
replace_exact(
    "Scripts/EmueraContent.Canvas.cs",
    """		void AddHitRect(ConsoleButtonHit hit)
		{
			int index = hitRects.Count;""",
    """		void AddHitRect(ConsoleButtonHit hit)
		{
			if (owner != null)
				hit.Rect = owner.ExpandMobileConsoleHitRect(hit.Rect);
			int index = hitRects.Count;"""
)

# Auxiliary UI buttons (input/scale dialogs etc.) should meet a phone touch target.
replace_exact(
    "Scripts/EmueraContent.cs",
    """		GEmueraTheme.ApplySystemButton(btn);
		// 保留游戏配置的 focus 色作为 hover/press 强调，避免改动行为语义。""",
    """		GEmueraTheme.ApplySystemButton(btn);
		if (OS.HasFeature("mobile") && btn.CustomMinimumSize.Y < 52)
			btn.CustomMinimumSize = new Vector2(btn.CustomMinimumSize.X, 52);
		// 保留游戏配置的 focus 色作为 hover/press 强调，避免改动行为语义。"""
)

# Quick command overlay: preserve user settings but enforce phone-friendly minima.
replace_exact(
    "Scripts/Panels/QuickButtons.cs",
    """	int EffectiveButtonWidth => ConfiguredButtonWidth;

	int QuickButtonHeight => EffectiveFontSize * 3 + QuickButtonPadding * 2;

	int EffectiveFontSize => fontSize > 0 ? fontSize : ConfiguredFontSize;""",
    """	int EffectiveButtonWidth => OS.HasFeature("mobile") ? Mathf.Max(ConfiguredButtonWidth, 120) : ConfiguredButtonWidth;

	int QuickButtonHeight => OS.HasFeature("mobile")
		? Mathf.Max(56, EffectiveFontSize * 3 + QuickButtonPadding * 2)
		: EffectiveFontSize * 3 + QuickButtonPadding * 2;

	int EffectiveFontSize
	{
		get
		{
			int size = fontSize > 0 ? fontSize : ConfiguredFontSize;
			return OS.HasFeature("mobile") ? Mathf.Max(size, 16) : size;
		}
	}"""
)

src_mobile = workspace / "engine-overrides/MobileUsabilityPatch.cs"
dst_mobile = root / "Scripts/GodotHost/MobileUsabilityPatch.cs"
shutil.copyfile(src_mobile, dst_mobile)
print(f"[overlay] {dst_mobile.relative_to(root)}")
