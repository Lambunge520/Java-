# LJM Java Manager 3.1.1

## 更新内容

- Java 注册不再自动修改 `JAVA_HOME`，避免下载、更新、修复时误改系统默认 Java。
- 注册管理页新增系统默认 Java 选择，可查看当前默认 Java 并手动切换。
- Windows 会扫描更多 JDK/JRE 注册表位置，方便管理其他安装器注册的 Java。
- 右上角新增任务进度入口和运行角标，可查看、取消、清空和删除任务记录。
- Java 下载、修复、更新进度整合到任务列表，不再自动弹出独立进度窗口。
- 放大任务角标并减少刷新闪烁；更新、移动、卸载/删除和备份列表加入复选框。
- 优化 Java 筛选位置和本地修复文案，修复旧逻辑提示混淆。

桌面版选择不带 `nogui` 的资产；无桌面版选择带 `nogui` 的资产。

## Update Content

- Java registration no longer changes `JAVA_HOME`, preventing downloads, updates, or repairs from changing the system default Java.
- Added a System Default Java panel in Registry to view and switch the current default Java.
- Windows now scans more JDK/JRE registry locations for Java installed by other installers.
- Added an upper-right task entry with a running-task badge, plus cancel, clear, and delete actions.
- Java download, repair, and update progress now lives in the task list instead of auto-opening a separate progress window.
- Enlarged the task badge, reduced badge flicker, and added checkbox selection to update, move, uninstall/delete, and backup lists.
- Improved Java filter placement and local repair wording.

Choose assets without `nogui` for desktop. Choose assets with `nogui` for NoGUI.
