# LJM Java Manager NoGUI

## 中文

这是 LJM Java Manager 的无桌面版目录。终端入口文件为 `LJM_nogui.py`，会复用 `LJM.pyw` 的核心逻辑，不启动桌面窗口和托盘，适合命令行、服务器、脚本和计划任务。

从 Release 下载成品时请选择名称带 `nogui` 的资产。Windows 使用 `.exe`，Linux 优先使用 `.run`，macOS 优先使用 `.command`。

注册、下载、更新和修复不会自动修改 `JAVA_HOME`；需要切换系统默认 Java 时使用 `set-default`。NoGUI 会同时管理 LJM 注册过的 Java 和系统/其他安装器注册过的 Java。

常用命令：

```powershell
python .\LJM_nogui.py list --stdout
python .\LJM_nogui.py scan "D:\Java" --stdout
python .\LJM_nogui.py check-updates --stdout
python .\LJM_nogui.py repair "Java 21" --mode smart --stdout
python .\LJM_nogui.py update "Java 21" --stdout
python .\LJM_nogui.py set-default "Java 21" --stdout
python .\LJM_nogui.py delete "Java 21" --files --force --stdout
```

终端环境：

```powershell
python .\LJM_nogui.py
```

在 Windows 终端里请使用 `LJM_nogui.py` 这个控制台入口。不要直接输入 `LJM_nogui.pyw`，它会以无控制台方式启动，无法稳定接入当前终端。
不带参数运行 `python .\LJM_nogui.py` 会自动进入 NoGUI 终端环境；带 `list`、`version`、`status` 等参数时才执行一次性命令后返回。

成功接入后会显示 NoGUI 终端环境提示；终端文案会跟随系统语言。可在 cmd、PowerShell、Linux/macOS 终端中输入 `help`、`状态`、`版本`、`清屏`、`退出` 以及各个 Java 管理命令。

完整使用说明见 [../docs/NOGUI_USAGE.md](../docs/NOGUI_USAGE.md)。

## English

This directory contains the NoGUI edition of LJM Java Manager. The terminal entry file is `LJM_nogui.py`; it reuses the core logic from `LJM.pyw` and does not start a desktop window or tray icon. It is intended for command-line usage, servers, scripts, and scheduled tasks.

When downloading release builds, choose assets with `nogui` in the name. Use `.exe` on Windows, `.run` on Linux, and `.command` on macOS.

Registration, download, update, and repair do not change `JAVA_HOME` automatically. Use `set-default` when you want to switch the system default Java. NoGUI manages Java registered by LJM and Java registered by the system or other installers.

Common commands:

```powershell
python .\LJM_nogui.py list --stdout
python .\LJM_nogui.py scan "D:\Java" --stdout
python .\LJM_nogui.py check-updates --stdout
python .\LJM_nogui.py repair "Java 21" --mode smart --stdout
python .\LJM_nogui.py update "Java 21" --stdout
python .\LJM_nogui.py set-default "Java 21" --stdout
python .\LJM_nogui.py delete "Java 21" --files --force --stdout
```

Terminal environment:

```powershell
python .\LJM_nogui.py
```

Use the `LJM_nogui.py` console entry from Windows terminals. Do not run `LJM_nogui.pyw` directly from a Windows terminal, because it starts without reliably attaching to the current console.
Running `python .\LJM_nogui.py` without arguments enters the NoGUI terminal environment. Passing `list`, `version`, `status`, or another command still runs that one command and returns.

After connecting, NoGUI prints a terminal environment message. Terminal text follows the system language. In cmd, PowerShell, Linux, and macOS terminals, type `help`, `status`, `version`, `clear`, `exit`, or any Java management command.

Full documentation: [../docs/NOGUI_USAGE.md](../docs/NOGUI_USAGE.md).
