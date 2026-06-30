# LJM Java Manager

LJM 是一个跨平台 Java 运行时管理工具，用来扫描、注册、下载、修复、更新、移动和删除本机 Java，适合 Minecraft 玩家、启动器、IDE、服务端、脚本任务和无桌面环境使用。

当前版本：`3.0`

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
- 自动处理 Linux/macOS 常见可执行权限问题，减少普通用户手动 `chmod` 的需要。
- 桌面端提供图形界面、托盘、备份管理、下载缓存管理和反馈入口。
- NoGUI 版适合脚本、服务器、计划任务、CI 和其他无桌面环境。

## 从源码运行

```powershell
python .\src\LJM.pyw
python .\src\LJM_nogui.pyw list --stdout
```

```bash
python3 ./src/LJM_nogui.pyw list --stdout
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
