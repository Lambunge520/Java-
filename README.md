# LJM(local Java manager) Java 核心环境管家

LJM 是一个跨平台 Java 环境管理工具，用来扫描、注册、下载、修复、更新、移动和删除本机 Java，适合 Minecraft、IDE、启动器、服务端和脚本环境使用。

## 下载

请前往 [Releases](https://github.com/Lambunge520/Java-/releases) 下载最新版本。

当前版本：`2.9 Stable`

## 选哪个包

- Windows 桌面端：`LJM-Java-Manager-windows.zip`
- Linux 桌面端：`LJM-Java-Manager-linux.tar.gz`，解压后运行 `LJM-Java-Manager.run`
- macOS 桌面端：`LJM-Java-Manager-macos.zip`，解压后运行 `LJM-Java-Manager.app`
- 无桌面端：选择名称带 `nogui` 的压缩包；Linux 运行 `.run`，macOS 运行 `.command`

## 主要功能

- 扫描、注册、注销 Java，并设置默认 `JAVA_HOME`。
- 下载、更新和修复 Java，支持多发行商、多版本和 Windows/Linux/macOS 自动匹配。
- 移动 Java 目录或删除 Java 文件时会处理常见权限问题。
- Linux/macOS 自动补齐 Java 启动器可执行权限，减少手动 `chmod`。
- 下载源会在官方源、GitHub 直连和镜像源之间自动降级；Adoptium 源已补齐 `latest` 与 `feature_releases` 双接口兜底。
- 桌面端提供图形界面和反馈入口；`nogui` 端适合脚本批处理、服务器和无桌面环境。

## 源码运行

```powershell
python .\src\LJM.pyw
python .\src\LJM_nogui.pyw
python .\src\LJM_nogui.pyw feedback --stdout --message "这里写反馈内容"
python .\src\LJM_nogui.pyw delete Temurin_21 --files --force
```

## 本地打包

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

打包产物输出到 `dist/` 或 GitHub Actions 资产。桌面端和 `nogui` 共用 `src/LJM.pyw` 核心逻辑；维护约定见 `docs/MAINTENANCE.md`。
