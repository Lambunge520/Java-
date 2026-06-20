# LJM Java Manager

LJM is a cross-platform Java runtime manager for desktop users, Minecraft players, launchers, IDEs, servers, scripts, and NoGUI environments.

Current version: `2.9.4`

## Download / 下载

Download from [GitHub Releases](https://github.com/Lambunge520/Java-/releases).

- Desktop Windows: `LJM-Java-Manager-windows.zip`
- Desktop Linux: `LJM-Java-Manager-linux.tar.gz`, then run `LJM-Java-Manager.run`
- Desktop macOS: `LJM-Java-Manager-macos.zip`, then run `LJM-Java-Manager.app`
- NoGUI / 无桌面版: choose assets with `nogui` in the name. Linux uses `.run`; macOS uses `.command`.
- Checksums / 校验: `SHA256SUMS-gui.txt` and `SHA256SUMS-nogui.txt`

NoGUI documentation: [docs/NOGUI_USAGE.md](docs/NOGUI_USAGE.md)

## Features / 功能

- Scan, register, unregister, move, delete, repair, and update local Java runtimes.
- Download JDK/JRE packages from multiple vendors and automatically fall back between official, GitHub, and mirror sources.
- Give Minecraft-oriented Java recommendations by version, vendor, runtime type, and performance profile.
- Repair launcher-visible stale registrations for PCL/HMCL-style repeated install/uninstall workflows.
- Automatically fix common Linux/macOS executable permission issues for downloaded Java runtimes.
- Desktop edition includes UI, tray, backup manager, cache manager, and feedback entry.
- NoGUI edition is designed for scripts, servers, scheduled tasks, CI, and other headless environments.

## Run From Source / 从源码运行

```powershell
python .\src\LJM.pyw
python .\src\LJM_nogui.pyw list --stdout
```

```bash
python3 ./src/LJM_nogui.pyw list --stdout
```

## Build / 本地打包

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\build_nogui_windows.ps1
```

```bash
./scripts/build_linux.sh
./scripts/build_nogui_linux.sh
./scripts/build_macos.sh
./scripts/build_nogui_macos.sh
```

Build outputs are written to `dist/`. GitHub Actions builds and uploads both desktop and NoGUI assets on `v*` tags.

Maintenance notes: [docs/MAINTENANCE.md](docs/MAINTENANCE.md)
