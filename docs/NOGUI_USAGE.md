# NoGUI Usage / NoGUI 使用文档

## 中文

NoGUI 是 LJM Java Manager 的命令行版本，不启动桌面窗口和托盘，适合服务器、无桌面环境、脚本批处理、计划任务和 CI 使用。它复用桌面版核心逻辑，支持扫描、注册、下载、修复、更新、移动、删除 Java，并可设置默认 `JAVA_HOME`。

### 3.1.3 重要变化

- Java 注册、下载、更新和修复不再自动修改 `JAVA_HOME`。
- 如需修改系统默认 Java，请使用 `set-default` 命令。
- NoGUI 会读取工具自身注册的 Java，也会扫描系统里其他安装器注册过的 Java，方便统一管理。
- Windows 会额外读取 JDK/JRE、旧版 JavaSoft、HKLM/HKCU 以及 32/64 位注册表视图。
- LJM 备份会保存为压缩包，避免启动器扫描到备份里的 Java。
- 完整更新工具命名的 Java 文件夹后，目录名会同步到新版本号。
- NoGUI 新增 `language` 命令，可切换 `auto`、`zh_CN`、`en_US`；默认 `auto` 会跟随 Windows 或当前系统语言。
- 下载、更新、修复结果仍以 JSON 和日志为准；NoGUI 不显示桌面端的任务管理窗口。
- Windows NoGUI 会保留当前 cmd、PowerShell 或 Windows Terminal，不再执行桌面版的隐藏控制台和启动时自动提权逻辑。只有确实需要系统权限的命令才可能要求用户使用管理员终端重试。
- `GraalVM` 与 `GraalVM Community` 下载链已完全分开；选择 `GraalVM` 时只获取非 Community 的 Oracle GraalVM 包。
- Java 发行商信息会给出更明确的 Minecraft 版本范围、兼容性和性能差异，GUI 下载页会随发行商与 Java 大版本动态更新建议。
- NoGUI 交互终端支持 Tab 补全命令和参数，Windows 使用内置控制台补全，Linux/macOS 使用系统 readline，不需要额外安装依赖。

### 下载哪个包

前往 [Releases](https://github.com/Lambunge520/Java-/releases) 下载名称带 `nogui` 的资产：

- Windows: `LJM-Java-Manager-nogui-windows.zip`
- Linux: `LJM-Java-Manager-nogui-linux.tar.gz`
- macOS: `LJM-Java-Manager-nogui-macos.zip`
- 校验文件: `SHA256SUMS-nogui.txt`

桌面版资产名称不带 `nogui`。如果只想在命令行里使用，优先选择 NoGUI 包。

### 快速上手

在解压目录打开终端后，直接运行 NoGUI 程序即可接入终端环境；终端不会因为命令执行完就自动关闭。接入成功后会显示成功提示，然后可以继续输入 LJM 的管理命令。

Windows:

```powershell
.\LJM-Java-Manager-nogui.exe
.\LJM-Java-Manager-nogui.exe terminal
.\LJM-Java-Manager-nogui.exe list --stdout
```

Linux:

```bash
./LJM-Java-Manager-nogui.run
./LJM-Java-Manager-nogui.run terminal
./LJM-Java-Manager-nogui.run list --stdout
```

macOS:

```bash
./LJM-Java-Manager-nogui.command
./LJM-Java-Manager-nogui.command terminal
./LJM-Java-Manager-nogui.command list --stdout
```

普通用户优先使用上面的 `.exe`、`.run`、`.command` 入口，不需要额外写 `cmd` 脚本。

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

终端环境支持短命令：`l`/`ls` 列表，`s` 扫描，`cu` 检查更新，`dl` 下载，`r` 修复，`u` 更新，`mv` 移动，`rm` 删除，`def` 设置默认 Java，`lang` 切换语言，`t`/`tasks` 查看任务，`c`/`cancel` 取消任务，`w`/`wait` 等待任务。

输入残缺命令后按 `Tab` 可以自动补全，例如 `down<Tab>` 补为 `download`、`ver<Tab>` 补为 `version`。下载命令还会补全 Java 发行商和大版本；修复、更新、移动、删除可补全已注册 Java 名称；取消和等待命令可补全任务编号。存在多个候选时，再按一次 `Tab` 会显示候选列表。

在交互终端里执行 `download`/`dl`、`update`/`u`、`repair`/`r` 时会自动作为后台任务运行并显示下载进度条，终端仍可继续输入其他命令。第一个开始的任务标记为 `1`，后续任务依次为 `2`、`3`、`4`。输入 `tasks` 查看进度和任务类型，输入 `c 1`、`cancel 2` 或 `cancel all` 取消任务；按 `Ctrl+C` 后会列出可取消任务，再输入 `1`、`2` 或 `1 3` 即可取消指定任务。

### 交互终端命令速查

| 操作 | 命令 |
| --- | --- |
| 查看帮助 | `help` 或 `帮助` |
| 查看 Java 列表 | `list`、`l`、`ls` |
| 扫描并注册 Java | `scan "D:\Java" --max-depth 6`、`s "D:\Java"`；不带参数时扫描常见安装根目录 |
| 检查更新 | `check-updates`、`cu`、`检查更新`；已是最新版本时 `update` 会直接跳过下载 |
| 下载 Java | `download "Eclipse Temurin" 21 "D:\Java" --package-type jdk` 或 `dl "Eclipse Temurin" 21 "D:\Java"` |
| 修复 Java | `repair "Java 21" --mode smart` 或 `r "Java 21"` |
| 更新 Java | `update "Java 21"` 或 `u "Java 21"` |
| 移动 Java | `move "Java 21" "D:\Java\jdk-21-new"` 或 `mv "Java 21" "D:\Java\jdk-21-new"` |
| 注销或删除 Java | `delete "Java 21"`、`delete "Java 21" --files --force`、`rm "Java 21"` |
| 设置默认 Java | `set-default "Java 21"` 或 `def "Java 21"` |
| 切换显示语言 | `language auto`、`lang zh_CN`、`lang en_US` |
| 查看任务 | `tasks`、`t`、`ps`、`jobs` |
| 取消任务 | `c 1`、`cancel 2`、`cancel all` |
| 等待任务 | `wait all`、`w 1` |
| 退出终端 | `exit` 或 `退出` |

任务编号从 `1` 开始递增，不会因为前一个任务结束而重新从 `1` 开始。`tasks` 会显示任务类型、目标、状态、百分比和下载大小；下载、更新、修复都可以用编号单独取消。按 `Ctrl+C` 时不会直接关闭终端，而是进入取消选择流程；输入任务编号即可取消，留空则退出取消选择。

### 输出和日志

NoGUI 默认把执行结果写入程序目录下的 `ljm_nogui_result.json`，错误日志写入 `ljm_nogui.log`。

- `--stdout`: 同时把 JSON 结果输出到控制台，适合脚本读取。
- `--output <path>`: 把 JSON 结果写入指定文件。
- `status` 输出中的 `nogui_mode: true` 表示共享核心已按 NoGUI 模式加载，当前终端不会被桌面版启动逻辑隐藏。

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

# 交互终端里的短命令示例
dl "Eclipse Temurin" 21 "D:\Java" --package-type jdk
u "Java 21"
r "Java 21" --mode smart
tasks
cancel 1
wait all

# 检查更新
.\LJM-Java-Manager-nogui.exe check-updates --stdout

# 智能修复已有 Java
.\LJM-Java-Manager-nogui.exe repair "Java 21" --mode smart --stdout

# 更新已有 Java
.\LJM-Java-Manager-nogui.exe update "Java 21" --stdout

# 设置默认 JAVA_HOME
.\LJM-Java-Manager-nogui.exe set-default "Java 21" --stdout

# 查看或切换显示语言
.\LJM-Java-Manager-nogui.exe language --stdout
.\LJM-Java-Manager-nogui.exe language zh_CN --stdout
.\LJM-Java-Manager-nogui.exe language en_US --stdout
.\LJM-Java-Manager-nogui.exe language auto --stdout

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

这适合 IDE、命令行脚本或其他依赖 `JAVA_HOME` 的工具。Windows 上优先写入系统级 `JAVA_HOME`，没有管理员权限时自动回退写入当前用户环境变量。Minecraft 启动器通常有自己的 Java 选择逻辑，是否使用系统默认 Java 取决于启动器设置。

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

## English

NoGUI is the command-line edition of LJM Java Manager. It does not start a desktop window or tray icon, so it is suitable for servers, systems without a desktop environment, scripts, scheduled tasks, and CI jobs. It reuses the desktop core logic and supports scanning, registering, downloading, repairing, updating, moving, deleting Java runtimes, and setting the default `JAVA_HOME`.

### Important Changes In 3.1.3

- Java registration, download, update, and repair no longer change `JAVA_HOME` automatically.
- To change the system default Java, use the `set-default` command.
- NoGUI reads Java registered by LJM and Java registered by other installers, so both can be managed in one place.
- On Windows, NoGUI scans JDK/JRE, legacy JavaSoft keys, HKLM/HKCU, and 32-bit/64-bit registry views.
- LJM backups are stored as archives so launchers do not scan backup Java runtimes.
- After a full update of an LJM-named Java folder, the folder name follows the new Java version.
- NoGUI adds the `language` command to switch between `auto`, `zh_CN`, and `en_US`; `auto` follows Windows or the current system language.
- Download, update, and repair results are reported through JSON and logs. NoGUI does not show the desktop task manager window.
- Windows NoGUI keeps the current cmd, PowerShell, or Windows Terminal session. It no longer runs the desktop edition's console-hiding and startup auto-elevation path. Commands that truly need system privileges may ask the user to retry from an administrator terminal.
- The `GraalVM` and `GraalVM Community` download chains are now fully separated. Selecting `GraalVM` only resolves non-Community Oracle GraalVM packages.
- Java vendor information now provides clearer Minecraft version ranges, compatibility notes, and performance differences; the GUI download page updates this advice with the selected vendor and Java major.
- The NoGUI interactive terminal supports Tab completion for commands and arguments. Windows uses the built-in console editor, while Linux/macOS use the system readline module with no extra dependency.

### Which Package To Download

Go to [Releases](https://github.com/Lambunge520/Java-/releases) and download assets with `nogui` in the name:

- Windows: `LJM-Java-Manager-nogui-windows.zip`
- Linux: `LJM-Java-Manager-nogui-linux.tar.gz`
- macOS: `LJM-Java-Manager-nogui-macos.zip`
- Checksums: `SHA256SUMS-nogui.txt`

Desktop assets do not contain `nogui` in the file name. If you only need command-line usage, choose a NoGUI package.

### Quick Start

Open a terminal in the extracted folder and run the NoGUI program directly. It enters the terminal environment and keeps the terminal open. After the success message appears, you can keep typing LJM management commands.

Windows:

```powershell
.\LJM-Java-Manager-nogui.exe
.\LJM-Java-Manager-nogui.exe terminal
.\LJM-Java-Manager-nogui.exe list --stdout
```

Linux:

```bash
./LJM-Java-Manager-nogui.run
./LJM-Java-Manager-nogui.run terminal
./LJM-Java-Manager-nogui.run list --stdout
```

macOS:

```bash
./LJM-Java-Manager-nogui.command
./LJM-Java-Manager-nogui.command terminal
./LJM-Java-Manager-nogui.command list --stdout
```

Regular users should prefer the bundled `.exe`, `.run`, or `.command` entry. No extra `cmd` wrapper script is needed.

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

The terminal supports short commands: `l`/`ls` for list, `s` for scan, `cu` for check updates, `dl` for download, `r` for repair, `u` for update, `mv` for move, `rm` for delete, `def` for default Java, `lang` for language, `t`/`tasks` for task status, `c`/`cancel` for cancellation, and `w`/`wait` for waiting.

Press `Tab` after a partial command to complete it, for example `down<Tab>` becomes `download` and `ver<Tab>` becomes `version`. Completion also covers Java vendors and majors for downloads, registered Java names for management commands, and task IDs for cancel/wait. Press `Tab` again when several candidates are available to list them.

Inside the interactive terminal, `download`/`dl`, `update`/`u`, and `repair`/`r` run as background tasks and show a download progress bar while the prompt keeps accepting other commands. The first started task is marked `1`, then `2`, `3`, `4`, and so on. Use `tasks` to view progress and task type, `c 1`, `cancel 2`, or `cancel all` to cancel. Pressing `Ctrl+C` lists cancellable tasks; then enter `1`, `2`, or `1 3` to cancel selected tasks.

### Interactive Command Cheat Sheet

| Action | Command |
| --- | --- |
| Show help | `help` |
| List Java runtimes | `list`, `l`, `ls` |
| Scan and register Java | `scan "D:\Java" --max-depth 6` or `s "D:\Java"`; bare `scan` checks common install roots |
| Check updates | `check-updates`, `cu` |
| Download Java | `download "Eclipse Temurin" 21 "D:\Java" --package-type jdk` or `dl "Eclipse Temurin" 21 "D:\Java"` |
| Repair Java | `repair "Java 21" --mode smart` or `r "Java 21"` |
| Update Java | `update "Java 21"` or `u "Java 21"` |
| Move Java | `move "Java 21" "D:\Java\jdk-21-new"` or `mv "Java 21" "D:\Java\jdk-21-new"` |
| Unregister or delete Java | `delete "Java 21"`, `delete "Java 21" --files --force`, `rm "Java 21"` |
| Set default Java | `set-default "Java 21"` or `def "Java 21"` |
| Switch display language | `language auto`, `lang zh_CN`, `lang en_US` |
| View tasks | `tasks`, `t`, `ps`, `jobs` |
| Cancel tasks | `c 1`, `cancel 2`, `cancel all` |
| Wait for tasks | `wait all`, `w 1` |
| Exit terminal | `exit` |

Task IDs start at `1` and keep increasing; they do not restart when an earlier task finishes. `tasks` shows task type, target, status, percentage, and downloaded size. Download, update, and repair tasks can all be cancelled by ID. Pressing `Ctrl+C` does not immediately close the terminal; it enters cancel-selection mode. Type task IDs to cancel them, or submit an empty line to leave cancel selection.

### Output And Logs

NoGUI writes the result JSON to `ljm_nogui_result.json` and errors to `ljm_nogui.log` by default.

- `--stdout`: also prints JSON to the console for scripts.
- `--output <path>`: writes JSON to a custom output file.
- `nogui_mode: true` in the `status` output confirms that the shared core was loaded in NoGUI mode and will not hide the current terminal.

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

# Short commands inside the interactive terminal
dl "Eclipse Temurin" 21 "D:\Java" --package-type jdk
u "Java 21"
r "Java 21" --mode smart
tasks
cancel 1
wait all

# Check updates
.\LJM-Java-Manager-nogui.exe check-updates --stdout

# Smart repair an existing Java runtime
.\LJM-Java-Manager-nogui.exe repair "Java 21" --mode smart --stdout

# Update an existing Java runtime
.\LJM-Java-Manager-nogui.exe update "Java 21" --stdout

# Set default JAVA_HOME
.\LJM-Java-Manager-nogui.exe set-default "Java 21" --stdout

# Show or switch display language
.\LJM-Java-Manager-nogui.exe language --stdout
.\LJM-Java-Manager-nogui.exe language zh_CN --stdout
.\LJM-Java-Manager-nogui.exe language en_US --stdout
.\LJM-Java-Manager-nogui.exe language auto --stdout

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

This is useful for IDEs, command-line scripts, and tools that rely on `JAVA_HOME`. On Windows the machine-level `JAVA_HOME` is written first; without administrator rights it falls back to the current user's environment variables. Minecraft launchers usually have their own Java selection logic, so whether they use the system default Java depends on launcher settings.

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
