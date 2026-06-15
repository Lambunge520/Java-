# LJM Java Manager NoGUI

无桌面端版本，入口文件为 `LJM_nogui.pyw`。它复用 `LJM.pyw` 的核心逻辑，不启动桌面窗口和托盘，适合命令行、脚本或计划任务调用。

## 本地运行

```powershell
python .\LJM_nogui.pyw list --stdout
python .\LJM_nogui.pyw scan "D:\Java" --stdout
python .\LJM_nogui.pyw check-updates --stdout
python .\LJM_nogui.pyw repair "Java 21" --mode smart --stdout
python .\LJM_nogui.pyw update "Java 21" --stdout
python .\LJM_nogui.pyw set-default "Java 21" --stdout
python .\LJM_nogui.pyw delete "Java 21" --files --force --stdout
```

默认结果会写入 `ljm_nogui_result.json`，错误日志会写入 `ljm_nogui.log`。加上 `--stdout` 后会同时把 JSON 输出到控制台。

## 本地打包

```powershell
powershell -ExecutionPolicy Bypass -File .\build_windows.ps1
```

打包结果在 `dist\LJM-Java-Manager-nogui.exe`。

## GitHub 打包

推送到 GitHub 后，可以在 Actions 页面手动运行 `Build LJM nogui packages`，也可以推送 `v*` 标签自动打包：

```powershell
git tag v2.9-nogui
git push origin v2.9-nogui
```

Actions 会生成：

- `LJM-Java-Manager-nogui-windows.zip`
- `LJM-Java-Manager-nogui-linux.tar.gz`，解包后优先运行 `LJM-Java-Manager-nogui.run`
- `LJM-Java-Manager-nogui-macos.zip`，解包后优先运行 `LJM-Java-Manager-nogui.command`
