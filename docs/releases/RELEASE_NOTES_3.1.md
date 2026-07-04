# LJM Java Manager 3.1

## 更新内容

- Java 注册会同步设置 `JAVA_HOME`，不再修改系统 PATH。
- 新增主页、菜单栏导航和更新日志独立界面，页面切换加入淡入淡出动画。
- 扫盘注册、下载后自动注册、注册表急救会走同一套注册逻辑。
- 修复 Linux/macOS self-update 覆盖正在运行本体时可能失败的问题。
- 优化 Windows、Linux、macOS 下 Java 环境写入和权限失败提示。
- NoGUI 与桌面端同步本次核心逻辑。

桌面版选择不带 `nogui` 的资产；无桌面版选择带 `nogui` 的资产。

## Update Content

- Java registration now sets `JAVA_HOME` without changing the system PATH.
- Added Home, menu navigation, and an independent Changelog page with fade page transitions.
- Folder scan, post-download registration, and registry repair now use the same registration flow.
- Fixed Linux/macOS self-update failures when replacing the running app executable.
- Improved Java environment writes and permission feedback on Windows, Linux, and macOS.
- NoGUI is synced with the desktop core changes.

Choose assets without `nogui` for desktop. Choose assets with `nogui` for NoGUI.
