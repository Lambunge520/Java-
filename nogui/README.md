# LJM Java Manager NoGUI

## 中文

这是 LJM Java Manager 的无桌面版目录。入口文件为 `LJM_nogui.pyw`，会复用 `LJM.pyw` 的核心逻辑，不启动桌面窗口和托盘，适合命令行、服务器、脚本和计划任务。

常用命令：

```powershell
python .\LJM_nogui.pyw list --stdout
python .\LJM_nogui.pyw scan "D:\Java" --stdout
python .\LJM_nogui.pyw check-updates --stdout
python .\LJM_nogui.pyw repair "Java 21" --mode smart --stdout
python .\LJM_nogui.pyw update "Java 21" --stdout
python .\LJM_nogui.pyw set-default "Java 21" --stdout
python .\LJM_nogui.pyw delete "Java 21" --files --force --stdout
```

完整使用说明见 [../docs/NOGUI_USAGE.md](../docs/NOGUI_USAGE.md)。

## English

This directory contains the NoGUI edition of LJM Java Manager. The entry file is `LJM_nogui.pyw`; it reuses the core logic from `LJM.pyw` and does not start a desktop window or tray icon. It is intended for command-line usage, servers, scripts, and scheduled tasks.

Common commands:

```powershell
python .\LJM_nogui.pyw list --stdout
python .\LJM_nogui.pyw scan "D:\Java" --stdout
python .\LJM_nogui.pyw check-updates --stdout
python .\LJM_nogui.pyw repair "Java 21" --mode smart --stdout
python .\LJM_nogui.pyw update "Java 21" --stdout
python .\LJM_nogui.pyw set-default "Java 21" --stdout
python .\LJM_nogui.pyw delete "Java 21" --files --force --stdout
```

Full documentation: [../docs/NOGUI_USAGE.md](../docs/NOGUI_USAGE.md).
