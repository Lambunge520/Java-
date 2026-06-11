# LJM(local Java manager) Java 核心环境管家

LJM(local java manager) Java 核心环境管家是一款跨平台 Java 环境管理工具，用于扫描、注册、修复、更新本机 Java 环境，解决 Minecraft、IDE、启动器或其他程序无法识别本机 Java 的问题。

## 下载

请前往 [GitHub Releases](https://github.com/Lambunge520/Java-/releases) 下载最新版本。

当前版本：`2.8 Stable`

## 主要功能

- 本地 Java 扫描、注册、注销与环境变量设置。
- 独立 Java 下载界面，可选择发行商、大版本和下载/安装位置，自动匹配当前 Windows/Linux/macOS 与 CPU 架构包，完成后自动注册。
- 独立 Java 移动界面，可迁移已注册 Java 目录并同步注册信息。
- Java 损坏检测、智能修复、完整修复、修复前备份与失败回滚。
- Java 更新检测、断点续传、下载缓存复用、SHA256 校验。
- 多镜像源测速、自动记忆最快源，优先使用更适合当前网络的源。
- 支持 Eclipse Temurin、IBM Semeru OpenJ9、IBM Semeru Certified、Azul Zulu、Alibaba Dragonwell、GraalVM、GraalVM Community、Microsoft Build of OpenJDK、Oracle Java、Oracle JDK、Oracle OpenJDK、Amazon Corretto、BellSoft Liberica、SAP SapMachine、OpenLogic OpenJDK、Red Hat OpenJDK、JetBrains Runtime、Tencent Kona、Huawei Bi Sheng、Mandrel、Liberica Native Image Kit、Gluon GraalVM、Generic OpenJDK 等多类型 Java，并在下载页展示适合场景、平台覆盖、优点与缺点。
- Java 下载目录名会保留发行商类型和大版本，例如 `GraalVM_jdk21_21.0.11`、`Azul_Zulu_jdk17_17.0.12_7`，便于区分不同 Java 类型。
- 下载链路会优先使用 Foojay/厂商元数据，并对 GitHub Release、`objects.githubusercontent.com`、`release-assets.githubusercontent.com` 等地址生成代理候选；Foojay 在当前网络下异常时会尝试 curl JSON 兜底。
- 界面加入主窗口和弹窗淡入/淡出动画，栏目切换不销毁重建文本控件，降低文字闪烁。
- 所有主界面栏目、设置页和关于页支持滚动；鼠标滚轮、触摸板高精度滚动、Shift 横向滚动和触摸屏拖拽滚动统一适配。
- 桌面端加入单实例保护，重复打开时不会新建多个窗口，会唤醒并置顶已有窗口；无桌面端保持可多开，方便脚本批处理。
- 支持 Windows、Linux、macOS，包含托盘、开机自启、最小化启动、多语言界面。
- 内置 GitHub 反馈入口，桌面工具栏、关于页、托盘菜单可直接打开预填系统信息的 Issue；无桌面端可用 `feedback` 命令生成同一条反馈链接。
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
├─ tests/               # 核心行为回归测试
├─ .github/workflows/   # GitHub Actions 自动构建
├─ README.md
├─ requirements.txt
└─ LICENSE
```

## 源码运行

```powershell
python .\src\LJM.pyw
python .\src\LJM_headless.pyw
python .\src\LJM_headless.pyw feedback --stdout --message "这里写反馈内容"
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

桌面端和无桌面端共用 `src/LJM.pyw` 核心版本与核心逻辑，后续版本升级默认同时维护 Windows、Linux、macOS 三个平台产物。2.7 起无桌面端也支持 `download`、`move` 和 `vendors` 命令，2.8 起 `vendors` 会同步输出各 Java 类型的平台覆盖说明。维护约定见 `docs/MAINTENANCE.md`。

提交或发布前可运行清理脚本，避免临时文件和打包产物进入 GitHub：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\clean_workspace.ps1
```
