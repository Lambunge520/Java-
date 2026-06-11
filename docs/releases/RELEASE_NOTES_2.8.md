# LJM Java 核心环境管家 2.8 Stable

本版本重点增强 Java 类型覆盖、更新源元数据选择和桌面/无桌面端一致性。

## 主要更新

- 桌面端和无桌面端同步升级到 2.8，共用同一套核心检测、下载、移动、修复与更新逻辑。
- 新增 Red Hat OpenJDK、Oracle JDK、Oracle OpenJDK、IBM Semeru Certified 支持，并保留 Oracle Java 兼容入口。
- 下载页增加各 Java 类型的平台覆盖说明，便于提前判断当前 Windows/Linux/macOS 环境是否适合该发行版。
- 无桌面端 `vendors` 命令同步输出平台覆盖信息，方便脚本和自动化系统读取。
- 新增 GitHub 反馈入口：桌面工具栏、关于页和托盘菜单可打开预填系统信息的 GitHub Issue；无桌面端新增 `feedback` 命令。
- Foojay 元数据候选包会按真实 Java 版本选择最高版本，减少接口返回顺序导致的“最新版本显示不准”问题。
- 继续保留 GitHub 代理源、镜像测速、断点续传、缓存复用、SHA256 校验、修复前备份与失败回滚等稳定性机制。

## Java 类型覆盖

当前内置覆盖 Eclipse Temurin、IBM Semeru OpenJ9、IBM Semeru Certified、Azul Zulu、Alibaba Dragonwell、GraalVM、GraalVM Community、Microsoft Build of OpenJDK、Oracle Java、Oracle JDK、Oracle OpenJDK、Amazon Corretto、BellSoft Liberica、SAP SapMachine、OpenLogic OpenJDK、Red Hat OpenJDK、JetBrains Runtime、Tencent Kona、Huawei Bi Sheng、Mandrel、Liberica Native Image Kit、Gluon GraalVM、Generic OpenJDK。

## 验证

- `python -m unittest tests.test_core_features`
- `python -m py_compile src\LJM.pyw src\LJM_headless.pyw src\LJM_headless_entry.py`
- `python src\LJM_headless.pyw feedback --stdout --message "OpenJ9 source is slow"`
