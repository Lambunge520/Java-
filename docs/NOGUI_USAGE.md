# NoGUI Usage / NoGUI 使用文档

## 中文

NoGUI 是 LJM Java Manager 的命令行版本，不启动桌面窗口和托盘，适合服务器、无桌面环境、脚本批处理、计划任务和 CI 使用。它复用桌面版核心逻辑，支持扫描、注册、下载、修复、更新、移动、删除 Java，并可设置默认 `JAVA_HOME`。

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
python .\src\LJM_nogui.pyw list --stdout
```

Linux/macOS:

```bash
python3 ./src/LJM_nogui.pyw list --stdout
```

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

如果不确定名称，先运行：

```powershell
.\LJM-Java-Manager-nogui.exe list --stdout
```

### 权限提示

- Windows 设置系统级 `JAVA_HOME` 可能需要管理员权限。
- 删除或移动正在被进程占用的 Java 会失败；确认无风险后可加 `--force`。
- Linux/macOS 如果无法执行，确认 `.run`、`.command` 和主程序都有执行权限。
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

NoGUI is the command-line edition of LJM Java Manager. It does not start a desktop window or tray icon, so it is suitable for servers, headless systems, scripts, scheduled tasks, and CI jobs. It reuses the desktop core logic and supports scanning, registering, downloading, repairing, updating, moving, deleting Java runtimes, and setting the default `JAVA_HOME`.

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
python .\src\LJM_nogui.pyw list --stdout
```

Linux/macOS:

```bash
python3 ./src/LJM_nogui.pyw list --stdout
```

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

If you are not sure, run:

```powershell
.\LJM-Java-Manager-nogui.exe list --stdout
```

### Permission Notes

- Setting a system-level `JAVA_HOME` on Windows may require administrator privileges.
- Deleting or moving a Java runtime that is still used by a process can fail; use `--force` only when it is safe.
- On Linux/macOS, make sure `.run`, `.command`, and the main executable have execute permission.
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
