# LJM Java Manager 2.9.4

## 中文

- 修复反复下载、卸载、注销 Java 后，PCL/HMCL 仍可能读到旧 Java 注册项的问题。
- 注销会同步清理同一 JDK 的根目录、内置 `jre`、`bin` 等等价注册路径。
- 删除 Java 时会清理关联的 LJM 备份目录，避免启动器继续扫描备份运行时。
- 新增独立备份管理界面，支持刷新、恢复、删除和打开备份目录。
- 设置页新增下载缓存管理，可查看缓存大小并一键清空缓存。
- 优化 Java 管理页切换动画，取消托盘图标左键单击恢复窗口，保留双击和右键菜单恢复。
- NoGUI 列表读取会自动移除丢失路径和 LJM 备份路径注册项。

桌面版请选择不带 `nogui` 的资产；无桌面版请选择带 `nogui` 的资产。

## English

- Fixed stale Java registry entries that PCL/HMCL could still see after repeated download, uninstall, and unregister workflows.
- Unregister now removes equivalent paths for the same JDK, including root, bundled `jre`, and `bin` registrations.
- Deleting Java now removes related LJM backup folders so launchers do not rescan backup runtimes.
- Added an independent Backup Manager page for refreshing, restoring, deleting, and opening backups.
- Added download cache management in Settings, including cache size display and one-click clearing.
- Improved Java management page transitions. Tray single-left-click restore is disabled; double-click and right-click menu restore remain available.
- NoGUI list output now prunes missing paths and LJM backup registrations too.

Choose assets without `nogui` for the desktop edition. Choose assets with `nogui` for the NoGUI edition.
