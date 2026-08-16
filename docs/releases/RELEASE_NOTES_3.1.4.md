# LJM Java Manager 3.1.4

## 更新内容

- 修复部分发行商（如 Corretto 四段式版本号）与安装后 release 文件版本格式不一致时，Java 更新完成后重新扫描仍提示有更新的问题。
- 云端更新前先比对当前版本与云端最新构建，已是最新时直接提示并跳过下载，不再重复下载同版本安装包。
- Java 文件夹更新改名后，注册项名称同步重建为新版本名，不再保留旧版本号名称。
- 下载页 Minecraft 建议新增兼容判定行和 Java 大版本快速对照，并支持按 MC 版本反查推荐 Java 大版本。
- NoGUI `scan` 不带参数时自动扫描常见 Java 安装根目录，与桌面端行为一致。
- NoGUI `set-default` 在 Windows 无管理员权限时自动回退写入当前用户环境变量，不再直接失败。
- GitHub 直连镜像列表新增备用镜像源，提升弱网环境下载成功率。
- 三端安装包瘦身：桌面端只内置当前平台的托盘依赖组件，NoGUI 版不再内置托盘依赖，单包体积大幅减小。
- 移除桌面端的更新日志独立界面，更新内容统一通过 GitHub Release 页面查看。
- GUI 与 NoGUI 同步升级到 3.1.4；GraalVM 区分与 Minecraft 版本匹配逻辑保持不变。

桌面版选择不带 `nogui` 的资产；无桌面版选择带 `nogui` 的资产。

## Update Content

- Fix update detection reporting phantom updates after a Java runtime was already updated, caused by vendor version format differences (for example Corretto four-part versions versus the installed release file text).
- Cloud updates now compare the installed build with the latest cloud build first and skip the download entirely when the runtime is already current.
- After an update renames the Java folder to the new version, the registry entry name is rebuilt from the new version instead of keeping the stale one.
- The download page Minecraft advice adds a compatibility verdict and a quick Java-to-Minecraft mapping, plus reverse lookup of recommended Java majors for a Minecraft version.
- NoGUI `scan` without arguments now scans common Java install roots, matching the desktop behavior.
- NoGUI `set-default` on Windows falls back to the current user environment variables when administrator rights are unavailable.
- The GitHub mirror list gains an extra fallback mirror for better download success on weak networks.
- Smaller packages: desktop builds now embed only the tray dependencies of their own platform, and NoGUI builds no longer bundle tray dependencies at all.
- Removed the standalone desktop changelog page; release notes are now read from the GitHub Release page.
- GUI and NoGUI are both updated to 3.1.4; GraalVM edition separation and Minecraft matching behavior are unchanged.

Choose assets without `nogui` for desktop. Choose assets with `nogui` for NoGUI.
