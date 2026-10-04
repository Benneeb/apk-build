# gEmuera Android build workspace

This repository builds a custom Android APK from the upstream [gEmuera](https://github.com/wwwXiaoHan17/gEmuera) source.

The workflow:

1. checks out a pinned upstream gEmuera revision,
2. applies the TW startup-optimization patch,
3. installs .NET 8/9 and the Android workload,
4. installs Godot 4.7 .NET and export templates,
5. exports an arm64 Android APK,
6. uploads the APK as a GitHub Actions artifact.

The engine patch adds:
- optional app-private game mirroring on Android for games containing `.gemuera-cache-revision`;
- startup timing with delta + cumulative timings;
- `startup_profile.tsv` output.

The game-side lazy-loading configuration is separate and should be installed into the eraTWKR game folder.
