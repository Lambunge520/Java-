# LJM Java 核心环境管家 2.9 Stable

## 下载建议

- 桌面端：Windows 下载 `LJM-Java-Manager-windows.zip`，Linux 下载 `LJM-Java-Manager-linux.tar.gz` 后运行 `.run`，macOS 下载 `LJM-Java-Manager-macos.zip` 后运行 `.app`。
- 无桌面端：下载名称带 `nogui` 的压缩包；Linux 运行 `.run`，macOS 运行 `.command`。
- 校验文件：`SHA256SUMS-gui.txt` / `SHA256SUMS-nogui.txt`。

## 本版重点

- 修复 Java 移动、删除、卸载时常见的权限访问问题。
- Linux/macOS 会自动补齐 Java 启动器可执行权限，减少用户手动执行 `chmod` 的情况。
- 补齐 Linux shell/桌面会话与 macOS launchd 的默认 Java 环境配置。
- 无桌面端统一命名为 `nogui`，同步更新入口、构建脚本和发布产物。
- Linux 发布包新增 `.run` 入口，macOS GUI 使用 `.app`，macOS nogui 使用 `.command`。
- Java 下载/更新源增强：Adoptium 官方源增加 `latest` 与 `feature_releases` 双接口兜底，失败后仍会自动降级到 GitHub 与镜像源。
