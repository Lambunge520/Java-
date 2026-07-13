# LJM Java Manager 3.1.3

## 更新内容

- 修复下载页选择 GraalVM 后可能下载成 GraalVM Community 的问题。
- Oracle GraalVM 与 GraalVM Community 使用独立下载链，不再跨版本类型兜底。
- 下载页新增更清晰的动态 Minecraft Java 建议，显示当前选择、MC 版本匹配、建议等级、兼容性和性能判断。
- Windows NoGUI 保留当前终端，不再继承桌面版隐藏控制台和启动时自动提权逻辑。
- NoGUI 交互终端新增跨平台 Tab 补全，支持命令、发行商、Java 大版本、语言、已注册 Java、任务编号和常用参数。
- GUI 与 NoGUI 同步升级到 3.1.3，并增强 Windows、Linux、macOS 打包后的终端模式校验。
- 修复 Ubuntu 20.04 / Python 3.8 打包成品启动时日志编码参数不兼容的问题。
- Release 资产只上传三端成品包与 SHA256 校验文件，不再额外上传 Python 源码压缩包。

桌面版选择不带 `nogui` 的资产；无桌面版选择带 `nogui` 的资产。

## Update Content

- Fix selecting GraalVM on the download page potentially resolving a GraalVM Community package.
- Oracle GraalVM and GraalVM Community now use separate download chains without cross-edition fallback.
- Add clearer dynamic Minecraft Java advice with the current selection, MC version match, recommendation level, compatibility, and performance notes.
- Windows NoGUI now keeps the current terminal instead of inheriting desktop console hiding and startup elevation.
- Add cross-platform NoGUI Tab completion for commands, vendors, Java majors, languages, registered Java names, task IDs, and common options.
- GUI and NoGUI are both updated to 3.1.3 with stronger packaged terminal-mode checks for Windows, Linux, and macOS.
- Fix packaged startup compatibility for the logging encoding option on Ubuntu 20.04 / Python 3.8.
- Release assets now contain only finished platform packages and SHA256 checksum files, without extra Python source archives.

Choose assets without `nogui` for desktop. Choose assets with `nogui` for NoGUI.
