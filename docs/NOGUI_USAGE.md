# NoGUI Usage / NoGUI 使用文档

## nogui使用说明

NoGUI 是 LJM Java Manager 的命令行版本，不启动桌面窗口和托盘，适合服务器、无桌面环境、脚本批处理、计划任务和 CI 使用。它复用桌面版核心逻辑，支持扫描、注册、下载、修复、更新、移动、删除 Java，并可设置默认 `JAVA_HOME`。

### 3.1.1 重要变化

- Java 注册、下载、更新和修复不再自动修改 `JAVA_HOME`。
- 如需修改系统默认 Java，请使用 `set-default` 命令。
- NoGUI 会读取工具自身注册的 Java，也会扫描系统里其他安装器注册过的 Java，方便统一管理。
- Windows 会额外读取 JDK/JRE、旧版 JavaSoft、HKLM/HKCU 以及 32/64 位注册表视图。
- 下载、更新、修复结果仍以 JSON 和日志为准；NoGUI 不显示桌面端的任务管理窗口。

### 下载哪个包

前往 [Releases](https://github.com/Lambunge520/Java-/releases) 下载名称带 `nogui` 的资产：

- Windows: `LJM-Java-Manager-nogui-windows.zip`
- Linux: `LJM-Java-Manager-nogui-linux.tar.gz`
- macOS: `LJM-Java-Manager-nogui-macos.zip`
- 校验文件: `SHA256SUMS-nogui.txt`

桌面版资产名称不带 `nogui`。如果只想在命令行里使用，优先选择 NoGUI 包。

### 解压后运行

Windows:

```powershell
Expand-Archive .\LJM-Java-Manager-nogui-windows.zip -DestinationPath .\ljm-nogui
cd .\ljm-nogui
.\LJM-Java-Manager-nogui.exe list --stdout
```

Linux:

```bash
mkdir -p ljm-nogui
tar -xzf LJM-Java-Manager-nogui-linux.tar.gz -C ljm-nogui
cd ljm-nogui
chmod +x ./LJM-Java-Manager-nogui.run ./LJM-Java-Manager-nogui
./LJM-Java-Manager-nogui.run list --stdout
```

macOS:

```bash
unzip LJM-Java-Manager-nogui-macos.zip -d ljm-nogui
cd ljm-nogui/LJM-Java-Manager-nogui-macos
chmod +x ./LJM-Java-Manager-nogui.command ./LJM-Java-Manager-nogui
./LJM-Java-Manager-nogui.command list --stdout
```

如果 macOS 提示文件来自互联网而无法运行，可在解压目录执行：

```bash
xattr -dr com.apple.quarantine .
```

### 从源码运行

Windows:

```powershell
python .\src\LJM_nogui.py
python .\src\LJM_nogui.py list --stdout
```

在 Windows 终端里请使用 `LJM_nogui.py` 这个控制台入口；不要直接输入 `LJM_nogui.pyw`，`.pyw` 会通过 `pythonw.exe` 启动，无法稳定接入当前终端。
不带参数运行 `python .\src\LJM_nogui.py` 会自动进入 NoGUI 终端环境；带 `list`、`version`、`status` 等参数时才执行一次性命令后返回。

Linux/macOS:

```bash
chmod +x ./src/LJM_nogui
./src/LJM_nogui
./src/LJM_nogui list --stdout
```

如果源码包解压后没有执行权限，执行一次 `chmod +x ./src/LJM_nogui` 即可。也可以继续使用 `python3 ./src/LJM_nogui.py` 或 `python3 ./src/LJM_nogui.py list --stdout`。

### 终端环境

如果普通用户不想记完整命令，可以直接进入 NoGUI 终端环境：

```powershell
.\LJM-Java-Manager-nogui.exe terminal
```

Linux/macOS 使用对应入口：

```bash
./LJM-Java-Manager-nogui.run terminal
./LJM-Java-Manager-nogui.command terminal
```

在真实终端里不带任何参数启动时，也会自动进入终端环境。进入后输入 `help` 查看命令，输入 `exit` 退出。

成功接入后会显示“已成功接入 LJM Java Manager NoGUI 终端环境”。终端提示词和帮助内容会跟随系统语言自动切换；Windows 的 cmd、PowerShell，以及 Linux/macOS 常见终端都可以直接输入 NoGUI 命令。终端内还支持 `帮助`、`退出`、`清屏`、`状态`、`版本`、`pwd` 和 `cd <目录>` 等辅助命令。

### 输出和日志

NoGUI 默认把执行结果写入程序目录下的 `ljm_nogui_result.json`，错误日志写入 `ljm_nogui.log`。

- `--stdout`: 同时把 JSON 结果输出到控制台，适合脚本读取。
- `--output <path>`: 把 JSON 结果写入指定文件。

示例：

```powershell
.\LJM-Java-Manager-nogui.exe list --stdout --output .\result.json
```

### 常用命令

```powershell
# 查看已注册 Java
.\LJM-Java-Manager-nogui.exe list --stdout

# 扫描目录并注册 Java
.\LJM-Java-Manager-nogui.exe scan "D:\Java" --max-depth 6 --stdout

# 查看支持的 Java 发行商和 Minecraft 建议
.\LJM-Java-Manager-nogui.exe vendors --stdout

# 下载并注册 Java
.\LJM-Java-Manager-nogui.exe download "Eclipse Temurin" 21 "D:\Java" --package-type jdk --stdout

# 检查更新
.\LJM-Java-Manager-nogui.exe check-updates --stdout

# 智能修复已有 Java
.\LJM-Java-Manager-nogui.exe repair "Java 21" --mode smart --stdout

# 更新已有 Java
.\LJM-Java-Manager-nogui.exe update "Java 21" --stdout

# 设置默认 JAVA_HOME
.\LJM-Java-Manager-nogui.exe set-default "Java 21" --stdout

# 移动 Java 目录
.\LJM-Java-Manager-nogui.exe move "Java 21" "D:\Java\jdk-21-new" --stdout

# 只注销 Java，不删除文件
.\LJM-Java-Manager-nogui.exe delete "Java 21" --stdout

# 注销并删除 Java 文件
.\LJM-Java-Manager-nogui.exe delete "Java 21" --files --force --stdout

# 生成 GitHub 反馈链接
.\LJM-Java-Manager-nogui.exe feedback --title "NoGUI 反馈" --message "这里写反馈内容" --stdout
```

在 Linux/macOS 上，把上面示例中的 `.\LJM-Java-Manager-nogui.exe` 替换为 `./LJM-Java-Manager-nogui.run` 或 `./LJM-Java-Manager-nogui.command`。

### 目标参数怎么写

`repair`、`update`、`set-default`、`move`、`delete` 的目标参数可以填写：

- LJM 注册名，例如 `Java 21`、`Temurin_21`
- Java Home 路径，例如 `D:\Java\jdk-21`

目标既可以来自 LJM 自己注册的 Java，也可以来自系统或其他安装器已注册的 Java。Windows 上常见的 `.msi`、`.exe` 安装器注册项会在 `list` 中一起显示。

如果不确定名称，先运行：

```powershell
.\LJM-Java-Manager-nogui.exe list --stdout
```

### 注册和默认 Java 的区别

`scan`、`download`、`repair`、`update` 会维护 LJM 可识别的 Java 注册信息，但不会改动系统默认 `JAVA_HOME`。

只有 `set-default` 会把目标 Java 设置为默认 `JAVA_HOME`：

```powershell
.\LJM-Java-Manager-nogui.exe set-default "Temurin_21" --stdout
```

这适合 IDE、命令行脚本或其他依赖 `JAVA_HOME` 的工具。Minecraft 启动器通常有自己的 Java 选择逻辑，是否使用系统默认 Java 取决于启动器设置。

### 权限提示

- Windows 设置系统级 `JAVA_HOME` 可能需要管理员权限。
- 删除或移动正在被进程占用的 Java 会失败；确认无风险后可加 `--force`。
- Linux/macOS 如果无法执行，优先使用包内 `.run` 或 `.command` 入口；如果权限丢失，确认 `.run`、`.command` 和主程序都有执行权限。
- 下载、更新和修复需要联网；失败时可查看 `ljm_nogui.log`。

### 本地打包

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_nogui_windows.ps1
```

```bash
./scripts/build_nogui_linux.sh
./scripts/build_nogui_macos.sh
```

产物会输出到 `dist/`。GitHub Actions 发布时会上传到 Release。

## Instructions for use

NoGUI is the command-line edition of LJM Java Manager. It does not start a desktop window or tray icon, so it is suitable for servers, headless systems, scripts, scheduled tasks, and CI jobs. It reuses the desktop core logic and supports scanning, registering, downloading, repairing, updating, moving, deleting Java runtimes, and setting the default `JAVA_HOME`.

### Important Changes In 3.1.1

- Java registration, download, update, and repair no longer change `JAVA_HOME` automatically.
- To change the system default Java, use the `set-default` command.
- NoGUI reads Java registered by LJM and Java registered by other installers, so both can be managed in one place.
- On Windows, NoGUI scans JDK/JRE, legacy JavaSoft keys, HKLM/HKCU, and 32-bit/64-bit registry views.
- Download, update, and repair results are reported through JSON and logs. NoGUI does not show the desktop task manager window.

### Which Package To Download

Go to [Releases](https://github.com/Lambunge520/Java-/releases) and download assets with `nogui` in the name:

- Windows: `LJM-Java-Manager-nogui-windows.zip`
- Linux: `LJM-Java-Manager-nogui-linux.tar.gz`
- macOS: `LJM-Java-Manager-nogui-macos.zip`
- Checksums: `SHA256SUMS-nogui.txt`

Desktop assets do not contain `nogui` in the file name. If you only need command-line usage, choose a NoGUI package.

### Run After Extracting

Windows:

```powershell
Expand-Archive .\LJM-Java-Manager-nogui-windows.zip -DestinationPath .\ljm-nogui
cd .\ljm-nogui
.\LJM-Java-Manager-nogui.exe list --stdout
```

Linux:

```bash
mkdir -p ljm-nogui
tar -xzf LJM-Java-Manager-nogui-linux.tar.gz -C ljm-nogui
cd ljm-nogui
chmod +x ./LJM-Java-Manager-nogui.run ./LJM-Java-Manager-nogui
./LJM-Java-Manager-nogui.run list --stdout
```

macOS:

```bash
unzip LJM-Java-Manager-nogui-macos.zip -d ljm-nogui
cd ljm-nogui/LJM-Java-Manager-nogui-macos
chmod +x ./LJM-Java-Manager-nogui.command ./LJM-Java-Manager-nogui
./LJM-Java-Manager-nogui.command list --stdout
```

If macOS blocks the downloaded files, run this inside the extracted folder:

```bash
xattr -dr com.apple.quarantine .
```

### Run From Source

Windows:

```powershell
python .\src\LJM_nogui.py
python .\src\LJM_nogui.py list --stdout
```

Use the `LJM_nogui.py` console entry from Windows terminals. Do not run `LJM_nogui.pyw` directly from a Windows terminal, because `.pyw` starts through `pythonw.exe` and cannot reliably attach to the current console.
Running `python .\src\LJM_nogui.py` without arguments enters the NoGUI terminal environment. Passing `list`, `version`, `status`, or another command still runs that one command and returns.

Linux/macOS:

```bash
chmod +x ./src/LJM_nogui
./src/LJM_nogui
./src/LJM_nogui list --stdout
```

If a source package loses execute permission after extracting, run `chmod +x ./src/LJM_nogui` once. You can also keep using `python3 ./src/LJM_nogui.py` or `python3 ./src/LJM_nogui.py list --stdout`.

### Terminal Environment

If users do not want to remember full commands, start the interactive NoGUI terminal:

```powershell
.\LJM-Java-Manager-nogui.exe terminal
```

Use the matching launcher on Linux/macOS:

```bash
./LJM-Java-Manager-nogui.run terminal
./LJM-Java-Manager-nogui.command terminal
```

When started with no arguments in a real terminal, NoGUI also enters this environment automatically. Type `help` for commands and `exit` to quit.

After connecting, NoGUI prints `Successfully connected to the LJM Java Manager NoGUI terminal environment.` The prompt and help text follow the detected system language. Windows cmd, PowerShell, and common Linux/macOS terminals can call NoGUI commands directly. Built-in helpers include `help`, `exit`, `clear`/`cls`, `status`, `version`, `pwd`, and `cd <folder>`.

### Output And Logs

NoGUI writes the result JSON to `ljm_nogui_result.json` and errors to `ljm_nogui.log` by default.

- `--stdout`: also prints JSON to the console for scripts.
- `--output <path>`: writes JSON to a custom output file.

Example:

```powershell
.\LJM-Java-Manager-nogui.exe list --stdout --output .\result.json
```

### Common Commands

```powershell
# List registered Java runtimes
.\LJM-Java-Manager-nogui.exe list --stdout

# Scan and register Java runtimes
.\LJM-Java-Manager-nogui.exe scan "D:\Java" --max-depth 6 --stdout

# Show supported vendors and Minecraft guidance
.\LJM-Java-Manager-nogui.exe vendors --stdout

# Download and register Java
.\LJM-Java-Manager-nogui.exe download "Eclipse Temurin" 21 "D:\Java" --package-type jdk --stdout

# Check updates
.\LJM-Java-Manager-nogui.exe check-updates --stdout

# Smart repair an existing Java runtime
.\LJM-Java-Manager-nogui.exe repair "Java 21" --mode smart --stdout

# Update an existing Java runtime
.\LJM-Java-Manager-nogui.exe update "Java 21" --stdout

# Set default JAVA_HOME
.\LJM-Java-Manager-nogui.exe set-default "Java 21" --stdout

# Move a Java directory
.\LJM-Java-Manager-nogui.exe move "Java 21" "D:\Java\jdk-21-new" --stdout

# Unregister Java without deleting files
.\LJM-Java-Manager-nogui.exe delete "Java 21" --stdout

# Unregister and delete Java files
.\LJM-Java-Manager-nogui.exe delete "Java 21" --files --force --stdout

# Generate a GitHub feedback URL
.\LJM-Java-Manager-nogui.exe feedback --title "NoGUI feedback" --message "Write feedback here" --stdout
```

On Linux/macOS, replace `.\LJM-Java-Manager-nogui.exe` with `./LJM-Java-Manager-nogui.run` or `./LJM-Java-Manager-nogui.command`.

### Target Argument

The target argument for `repair`, `update`, `set-default`, `move`, and `delete` can be:

- An LJM registry name, such as `Java 21` or `Temurin_21`
- A Java Home path, such as `D:\Java\jdk-21`

Targets can come from Java registered by LJM or from Java registered by the operating system or another installer. On Windows, common `.msi` and `.exe` installer registry entries are shown by `list` too.

If you are not sure, run:

```powershell
.\LJM-Java-Manager-nogui.exe list --stdout
```

### Registration Versus Default Java

`scan`, `download`, `repair`, and `update` maintain Java registration data that LJM can manage, but they do not change the system default `JAVA_HOME`.

Only `set-default` sets a target Java as the default `JAVA_HOME`:

```powershell
.\LJM-Java-Manager-nogui.exe set-default "Temurin_21" --stdout
```

This is useful for IDEs, command-line scripts, and tools that rely on `JAVA_HOME`. Minecraft launchers usually have their own Java selection logic, so whether they use the system default Java depends on launcher settings.

### Permission Notes

- Setting a system-level `JAVA_HOME` on Windows may require administrator privileges.
- Deleting or moving a Java runtime that is still used by a process can fail; use `--force` only when it is safe.
- On Linux/macOS, prefer the bundled `.run` or `.command` launcher. If execute permission is lost, make sure `.run`, `.command`, and the main executable are executable.
- Download, update, and repair commands require network access. Check `ljm_nogui.log` if a command fails.

### Local Build

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_nogui_windows.ps1
```

```bash
./scripts/build_nogui_linux.sh
./scripts/build_nogui_macos.sh
```

Build outputs are written to `dist/`. GitHub Actions uploads release assets automatically when publishing.
