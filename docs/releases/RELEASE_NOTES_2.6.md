# LJM Java 核心环境管家 2.6 Stable

## 重点更新

- Java 修复功能增强：支持智能修复与完整修复，修复前自动备份，失败后可回滚。
- 下载体验增强：支持断点续传、下载缓存复用、SHA256 校验和压缩包结构检查。
- 更新源策略增强：支持多镜像源测速、自动记忆最快源，并优先使用更适合当前网络的源。
- 更新检测增强：优化 Java 大版本更新判断、版本对比和是否有更新列表显示逻辑。
- 新增后台托盘定时检查 Java 更新：支持每天、每周或关闭，只提醒不强制安装。
- 新增 Java 进程占用检测：更新或修复前提示 Minecraft、IDE、java.exe 等可能占用目标目录的进程。
- 新增搜索/筛选 Java 列表：可按版本、厂商、路径或损坏状态快速过滤。
- 新增 Microsoft Build of OpenJDK 与 Oracle Java 支持。
- 新增多语言支持：自动识别系统语言，支持简体中文与英文，并可在设置中手动切换。
- 托盘与启动体验增强：支持开机自启、最小化到托盘启动、托盘常驻和托盘菜单切换页面。
- 自更新增强：支持 GitHub Release 中的 exe/pyw/py 直接更新，也支持 zip、tar.gz、tgz 压缩包热更新。

## 下载说明

- Windows 用户优先下载 `LJM-Java-Manager-windows.zip`。
- Linux 用户优先下载 `LJM-Java-Manager-linux.tar.gz`。
- macOS 用户优先下载 `LJM-Java-Manager-macos.zip`。
- 无桌面环境或服务器用户可选择名称带 `nogui` 的 NoGUI 包。

## 校验

Release 会附带 `SHA256SUMS-gui.txt` 与 `SHA256SUMS-nogui.txt`，下载后可用于校验文件完整性。
