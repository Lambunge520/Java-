# LJM Java 核心环境管家 2.8 Stable

本版本重点增强 Java 类型覆盖、更新源元数据选择和桌面/无桌面端一致性。

## 主要更新

- 桌面端和无桌面端同步升级到 2.8，共用同一套核心检测、下载、移动、修复与更新逻辑。
- 新增 Red Hat OpenJDK、Oracle JDK、Oracle OpenJDK、IBM Semeru Certified 支持，并保留 Oracle Java 兼容入口。
- 下载页增加各 Java 类型的平台覆盖说明，便于提前判断当前 Windows/Linux/macOS 环境是否适合该发行版。
- 无桌面端 `vendors` 命令同步输出平台覆盖信息，方便脚本和自动化系统读取。
- 新增 GitHub 反馈入口：桌面工具栏、关于页和托盘菜单可打开预填系统信息的 GitHub Issue；无桌面端新增 `feedback` 命令。
- Java 下载与更新检测链路热修：请求和下载会在直连、系统代理、系统默认连接之间轮切兜底，适配国内网络、VPN、代理工具和 PAC 混合环境。
- GitHub Release、`objects.githubusercontent.com`、`release-assets.githubusercontent.com` 等地址新增多组国内镜像/代理候选，并支持记忆测速后的最快源优先。
- 官方源异常时自动降级到 GitHub 直连和 GitHub 镜像；Microsoft Build of OpenJDK 等带 GitHub Release 的发行版也会使用 GitHub 代理源检测和下载。
- 修复 GitHub Release 资产选择的大版本匹配问题，避免同一 release 同时包含 `jdk11`、`jdk17`、`jdk21` 时误选其它大版本包。
- Java 下载取消响应优化，下载分块缩小并缩短连接等待，降低卡在慢源时的取消等待时间。
- 新增独立 Java 卸载/删除界面，可选择仅注销注册信息或删除 Java 目录并同步注销；无桌面端新增 `delete` 命令。
- 下载页 Java 类型说明加入 Minecraft 性能、稳定性、兼容性建议，按 Java 8/17/21 对应常见 Minecraft 版本给出推荐。
- Foojay 元数据候选包会按真实 Java 版本选择最高版本，减少接口返回顺序导致的“最新版本显示不准”问题。
- 继续保留 GitHub 代理源、镜像测速、断点续传、缓存复用、SHA256 校验、修复前备份与失败回滚等稳定性机制。

## Java 类型覆盖

当前内置覆盖 Eclipse Temurin、IBM Semeru OpenJ9、IBM Semeru Certified、Azul Zulu、Alibaba Dragonwell、GraalVM、GraalVM Community、Microsoft Build of OpenJDK、Oracle Java、Oracle JDK、Oracle OpenJDK、Amazon Corretto、BellSoft Liberica、SAP SapMachine、OpenLogic OpenJDK、Red Hat OpenJDK、JetBrains Runtime、Tencent Kona、Huawei Bi Sheng、Mandrel、Liberica Native Image Kit、Gluon GraalVM、Generic OpenJDK。

## 验证

- `python -m unittest tests.test_core_features`
- `python -m py_compile src\LJM.pyw src\LJM_headless.pyw src\LJM_headless_entry.py`
- `python src\LJM_headless.pyw feedback --stdout --message "OpenJ9 source is slow"`
- `python src\LJM_headless.pyw delete --help`
