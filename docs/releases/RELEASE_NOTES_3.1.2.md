# LJM Java Manager 3.1.2

## 更新内容

- 备份改为压缩包保存，避免 HMCL、PCL 等启动器扫描到备份里的 Java。
- 恢复备份兼容新压缩包和旧备份目录。
- 云端完整更新后，工具命名的 Java 文件夹会同步替换为新版本号。
- NoGUI 新增 language 命令切换显示语言，默认跟随系统语言。
- NoGUI 终端支持短命令、后台任务进度条和取消命令。
- 修复 NoGUI 打包版缺少 plistlib 导致启动失败的问题。
- 同步增强 NoGUI 更新逻辑和使用文档。

桌面版选择不带 `nogui` 的资产；无桌面版选择带 `nogui` 的资产。

## Update Content

- Backups are now stored as archives so launchers do not scan backup Java runtimes.
- Backup restore supports both new archives and older backup folders.
- After a full cloud update, LJM-named Java folders are renamed to the new Java version.
- NoGUI adds a language command for display language switching and keeps auto system language by default.
- NoGUI terminal adds short commands, background task progress bars, and cancellation commands.
- Fix NoGUI packaged builds missing plistlib at startup.
- NoGUI update logic and usage docs are updated too.

Choose assets without `nogui` for desktop. Choose assets with `nogui` for NoGUI.
