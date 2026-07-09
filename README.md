# LJM Java Manager

LJM 是一个跨平台 Java 运行时管理工具，用来扫描、注册、下载、修复、更新、移动和删除本机 Java，适合 Minecraft 玩家、启动器、IDE、服务端、脚本任务和无桌面环境使用。

当前版本：`3.1.2`

## 下载

请前往 [GitHub Releases](https://github.com/Lambunge520/Java-/releases) 下载。

- 桌面端 Windows：`LJM-Java-Manager-windows.zip`
- 桌面端 Linux：`LJM-Java-Manager-linux.tar.gz`，解压后运行 `LJM-Java-Manager.run`
- 桌面端 macOS：`LJM-Java-Manager-macos.zip`，解压后运行 `LJM-Java-Manager.app`
- 无桌面版：选择名称带 `nogui` 的资产；Linux 使用 `.run`，macOS 使用 `.command`
- 校验文件：`SHA256SUMS-gui.txt` 和 `SHA256SUMS-nogui.txt`

NoGUI 使用文档：[docs/NOGUI_USAGE.md](docs/NOGUI_USAGE.md)

## 主要功能

- 扫描、注册、注销、移动、删除、修复和更新本机 Java。
- 从多个 Java 发行商下载 JDK/JRE，并在官方源、GitHub 直连和镜像源之间自动兜底。
- 按 Minecraft 版本、发行商、运行时类型和性能差距给出 Java 选择建议。
- 新增 Minecraft JVM 参数调整界面，可按启动器、Java 大版本、MC 版本和电脑配置生成推荐参数。
- 修复 PCL/HMCL 反复安装、卸载后仍能看到旧 Java 注册项的问题。
- Java 注册不再改动 JAVA_HOME；系统默认 Java 通过注册管理页的独立入口设置。
- 系统默认 Java 选择界面会显示当前 JAVA_HOME，并可识别其他安装器注册过的 Java。
- 右上角任务入口集中显示 Java 下载、修复、更新进度，支持运行角标、取消和记录清理。
- 云端更新、移动、卸载/删除和备份管理列表支持复选框选择。
- 备份会保存为压缩包，避免启动器扫描到备份里的 Java。
- 云端更新完成后，工具命名的 Java 文件夹会同步更新到新版本号。
- NoGUI 新增 `language` 命令，可在 `auto`、`zh_CN`、`en_US` 间切换，默认跟随系统语言。
- NoGUI 终端支持短命令、后台下载/更新/修复任务、进度条和取消命令。
- 新增主页、菜单栏导航和更新日志独立界面，独立页面切换带淡入淡出动画。
- 优化 Windows、Linux、macOS 工具本体热更新和权限处理逻辑。
- 自动处理 Linux/macOS 常见可执行权限问题，减少普通用户手动 `chmod` 的需要。
- 桌面端提供图形界面、托盘、备份管理、下载缓存管理和反馈入口。
- NoGUI 版适合脚本、服务器、计划任务、CI 和其他无桌面环境。

## 从源码运行

```powershell
python .\src\LJM.pyw
python .\src\LJM_nogui.py
python .\src\LJM_nogui.py list --stdout
```

```bash
chmod +x ./src/LJM_nogui
./src/LJM_nogui
./src/LJM_nogui list --stdout
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

打包产物会输出到 `dist/`。GitHub Actions 会在 `v*` 标签发布时构建并上传桌面端和 NoGUI 端资产。

维护约定：[docs/MAINTENANCE.md](docs/MAINTENANCE.md)
