# 维护约定

本项目后续更新默认同时维护桌面端和无桌面端，避免出现版本号、功能逻辑或平台适配不同步的问题。

## 版本同步

- 工具版本统一写在 `src/LJM.pyw` 的 `VERSION`。
- 无桌面端 `src/LJM_headless.pyw` 会加载同一个核心文件，因此桌面端版本升级时无桌面端自动跟随同一版本。
- 修改 Java 检测、更新、下载、修复、镜像源、缓存、校验等核心逻辑时，必须确认无桌面端命令也能继续调用对应能力。

## 平台同步

每次发布都默认维护以下产物：

- Windows 桌面端：`scripts/build_windows.ps1`
- Windows 无桌面端：`scripts/build_headless_windows.ps1`
- Linux 桌面端：`scripts/build_linux.sh`
- Linux 无桌面端：`scripts/build_headless_linux.sh`
- macOS 桌面端：`scripts/build_macos.sh`
- macOS 无桌面端：`scripts/build_headless_macos.sh`

GitHub Actions 中的 GUI 和 headless 工作流都会在 `v*` 标签发布时运行，并把产物上传到同一个 Release。

## 收尾清理

提交或发布前应清理本地临时产物，避免把无用文件推到 GitHub：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\clean_workspace.ps1
```

```bash
./scripts/clean_workspace.sh
```

清理范围包括 `build/`、`dist/`、`__pycache__/`、本地 release 压缩包、校验文件、日志、临时结果文件等。`javamanager_config.json` 是本机配置，不会被清理脚本删除，也不会提交到 GitHub。
