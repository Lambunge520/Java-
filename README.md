# LJM Java 核心环境管家

LJM Java 核心环境管家是一款跨平台 Java 环境管理工具，用于扫描、注册、修复、更新本机 Java 环境，解决 Minecraft、IDE、启动器或其他程序无法识别本机 Java 的问题。

## 下载

请前往 [GitHub Releases](https://github.com/Lambunge520/Java-/releases) 下载最新版本。

当前版本：`2.6 Stable`

## 主要功能

- 本地 Java 扫描、注册、注销与环境变量设置。
- Java 损坏检测、智能修复、完整修复、修复前备份与失败回滚。
- Java 更新检测、断点续传、下载缓存复用、SHA256 校验。
- 多镜像源测速、自动记忆最快源，优先使用更适合当前网络的源。
- 支持 Eclipse Temurin、IBM Semeru OpenJ9、Azul Zulu、Alibaba Dragonwell、GraalVM、Microsoft Build of OpenJDK、Oracle Java 等多类型 Java。
- 支持 Windows、Linux、macOS，包含托盘、开机自启、最小化启动、多语言界面。
- 支持 GitHub Release 压缩包热更新，可自动识别并处理 zip、tar.gz、tgz 等发布包。

## 界面预览

<img width="1486" height="826" alt="LJM Java Manager preview" src="https://github.com/user-attachments/assets/a1e57824-eac3-4405-8cd2-8b31aae86e3d" />

<img width="1920" height="1080" alt="LJM Java Manager settings preview" src="https://github.com/user-attachments/assets/6b7beef3-be99-4efb-9780-a5de93cc8250" />

<img width="1493" height="833" alt="LJM Java Manager update preview" src="https://github.com/user-attachments/assets/5d93ff5d-c531-42b4-a8e4-42d91d3e6d52" />

## 目录结构

仓库根目录只保留用户和维护者最常看的入口文件，源码、脚本、资源和依赖分别收纳到固定目录：

```text
.
├─ src/                 # 桌面端与无桌面端源码
├─ scripts/             # Windows/Linux/macOS 打包脚本
├─ assets/              # 图标、桌面入口等资源
├─ vendor/deps/         # 跨平台内置依赖
├─ docs/releases/       # 版本发行说明
├─ .github/workflows/   # GitHub Actions 自动构建
├─ README.md
├─ requirements.txt
└─ LICENSE
```

## 源码运行

```powershell
python .\src\LJM.pyw
python .\src\LJM_headless.pyw
```

## 本地打包

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\build_headless_windows.ps1
```

```bash
./scripts/build_linux.sh
./scripts/build_headless_linux.sh
./scripts/build_macos.sh
./scripts/build_headless_macos.sh
```

打包产物默认输出到 `dist/`，发布说明位于 `docs/releases/`。

## 维护说明

桌面端和无桌面端共用 `src/LJM.pyw` 核心版本与核心逻辑，后续版本升级默认同时维护 Windows、Linux、macOS 三个平台产物。维护约定见 `docs/MAINTENANCE.md`。

提交或发布前可运行清理脚本，避免临时文件和打包产物进入 GitHub：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\clean_workspace.ps1
```
