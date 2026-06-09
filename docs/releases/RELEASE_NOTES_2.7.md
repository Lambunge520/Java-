# LJM Java 核心环境管家 2.7 Stable

## 重点更新

- 桌面端和无桌面端同步升级到 2.7，共用同一套 Java 核心检测、下载、移动、修复与更新逻辑。
- 优化 Java 搜索与筛选逻辑，支持多关键字跨字段匹配，并减少扫描明显无关目录造成的卡顿。
- 新增独立「Java 下载」界面，可选择发行商、大版本和下载/安装位置，下载后自动注册。
- 新增独立「Java 移动」界面，可移动已注册 Java 目录，并自动同步注册信息。
- 无桌面端新增 `download`、`move` 和 `vendors` 命令，便于脚本化下载、迁移 Java 环境并查看支持类型。
- Java 下载页新增发行商适合场景、优点、缺点和当前系统包匹配说明。
- 支持更多 Java 类型：Amazon Corretto、BellSoft Liberica、SAP SapMachine、OpenLogic OpenJDK、JetBrains Runtime、Tencent Kona、Huawei Bi Sheng、Mandrel、Liberica Native Image Kit、Gluon GraalVM、GraalVM Community 等。
- 下载后的 Java 文件夹名保留发行商类型、大版本和真实版本号，例如 `GraalVM_jdk21_21.0.11`、`Azul_Zulu_jdk17_17.0.12_7`。
- 所有主界面栏目、设置页和关于页新增滚动容器，表格/列表补充竖向与横向滚动条，避免低分辨率或缩放较大时内容被挤出屏幕。
- 鼠标滚轮、触摸板高精度滚动、Shift 横向滚动和触摸屏拖拽滚动统一适配；触摸拖拽会避开按钮、输入框、表格等交互控件，减少误触。
- 增强主窗口、弹窗和栏目切换的淡入/淡出动画，动画时长更明显，同时不销毁重建文本控件，减少文字闪烁。
- 桌面端新增单实例保护，重复启动时会通过本机回环通道唤醒并置顶已有窗口，避免用户误开多个程序；无桌面端不加锁，保留脚本并发能力。

## 兼容性

- Windows、Linux、macOS 构建脚本继续同步维护。
- 下载功能复用既有镜像源、断点续传、缓存复用、SHA256 校验和安全解压机制。
- 下载链路优化 GitHub 代理候选，覆盖 `github.com`、`api.github.com`、`objects.githubusercontent.com`、`release-assets.githubusercontent.com` 等常见 Release 跳转域名。
- Foojay 元数据请求增加 curl JSON 兜底，缓解部分 Windows/TLS/证书吊销链路导致的源不可用问题。
- Foojay 包选择增加 Java 大版本二次校验，避免 Native Image Kit 等特殊发行版把发行版版本号误判为 Java 大版本。
- 移动功能会阻止目标路径位于源 Java 目录内部，降低误操作风险。
