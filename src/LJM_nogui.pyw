import argparse
import ctypes
import importlib.machinery
import importlib.util
import json
import locale
import os
import shlex
import sys
import tarfile
import tempfile
import threading
import time
import traceback
import zipfile


if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(os.path.abspath(sys.executable))
    RESOURCE_DIR = getattr(sys, "_MEIPASS", APP_DIR)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    RESOURCE_DIR = APP_DIR

CORE_PATH = os.path.join(RESOURCE_DIR, "LJM.pyw")
DEFAULT_RESULT_FILE = os.path.join(APP_DIR, "ljm_nogui_result.json")
DEFAULT_LOG_FILE = os.path.join(APP_DIR, "ljm_nogui.log")
TERMINAL_EXIT_COMMANDS = {"exit", "quit", "q", "退出"}
TERMINAL_HELP_COMMANDS = {"help", "?", "h", "帮助", "幫助"}
TERMINAL_CLEAR_COMMANDS = {"clear", "cls", "清屏"}
TERMINAL_VERSION_COMMANDS = {"version", "ver", "版本"}
TERMINAL_STATUS_COMMANDS = {"status", "状态", "狀態"}
TERMINAL_CANONICAL_COMMANDS = {
    "list",
    "scan",
    "check-updates",
    "repair",
    "update",
    "download",
    "vendors",
    "feedback",
    "move",
    "delete",
    "set-default",
    "terminal",
}
TERMINAL_COMMAND_ALIASES = {
    "ls": "list",
    "列表": "list",
    "扫描": "scan",
    "掃描": "scan",
    "下载": "download",
    "下載": "download",
    "修复": "repair",
    "修復": "repair",
    "更新": "update",
    "检查更新": "check-updates",
    "檢查更新": "check-updates",
    "移动": "move",
    "移動": "move",
    "删除": "delete",
    "刪除": "delete",
    "默认": "set-default",
    "預設": "set-default",
    "发行商": "vendors",
    "發行商": "vendors",
    "反馈": "feedback",
    "反饋": "feedback",
}

TERMINAL_TEXT = {
    "zh_CN": {
        "connected": "已成功接入 LJM Java Manager NoGUI 终端环境。",
        "title": "LJM Java Manager NoGUI 终端 {version}",
        "hint": "输入 help/帮助 查看命令，输入 exit/退出 离开终端环境。",
        "prompt": "ljm无桌面> ",
        "commands_title": "可用命令:",
        "cmd_list": "  list / 列表",
        "cmd_scan": "  scan <文件夹> / 扫描 <文件夹>",
        "cmd_vendors": "  vendors / 发行商",
        "cmd_check": "  check-updates / 检查更新",
        "cmd_download": "  download \"Eclipse Temurin\" 21 <安装父目录> --package-type jdk",
        "cmd_repair": "  repair <注册名或Java目录> --mode smart",
        "cmd_update": "  update <注册名或Java目录>",
        "cmd_move": "  move <注册名或Java目录> <新的Java目录>",
        "cmd_delete": "  delete <注册名或Java目录> [--files] [--force]",
        "cmd_default": "  set-default <注册名或Java目录>",
        "cmd_feedback": "  feedback --message \"反馈内容\"",
        "cmd_builtin": "  help/帮助, status/状态, version/版本, pwd, cd <目录>, clear/清屏, exit/退出",
        "parse_error": "命令解析失败: {error}",
        "unknown_error": "命令执行失败: {error}",
        "version": "当前 NoGUI 版本: {version}",
        "status": "已接入终端环境；结果文件: {result}; 日志文件: {log}; 当前目录: {cwd}",
        "cwd": "当前目录: {cwd}",
        "cd_missing": "请提供要进入的目录。",
        "cd_done": "当前目录已切换到: {cwd}",
        "cd_failed": "目录不存在: {path}",
        "bye": "已退出 NoGUI 终端环境。",
    },
    "en_US": {
        "connected": "Successfully connected to the LJM Java Manager NoGUI terminal environment.",
        "title": "LJM Java Manager NoGUI Terminal {version}",
        "hint": "Type help for commands, exit to leave the terminal environment.",
        "prompt": "ljm-nogui> ",
        "commands_title": "Available commands:",
        "cmd_list": "  list",
        "cmd_scan": "  scan <folder>",
        "cmd_vendors": "  vendors",
        "cmd_check": "  check-updates",
        "cmd_download": "  download \"Eclipse Temurin\" 21 <parent-folder> --package-type jdk",
        "cmd_repair": "  repair <name-or-java-home> --mode smart",
        "cmd_update": "  update <name-or-java-home>",
        "cmd_move": "  move <name-or-java-home> <new-java-home>",
        "cmd_delete": "  delete <name-or-java-home> [--files] [--force]",
        "cmd_default": "  set-default <name-or-java-home>",
        "cmd_feedback": "  feedback --message \"text\"",
        "cmd_builtin": "  help, status, version, pwd, cd <folder>, clear/cls, exit",
        "parse_error": "Command parse failed: {error}",
        "unknown_error": "Command failed: {error}",
        "version": "Current NoGUI version: {version}",
        "status": "Terminal environment connected; result file: {result}; log file: {log}; current directory: {cwd}",
        "cwd": "Current directory: {cwd}",
        "cd_missing": "Provide a folder to enter.",
        "cd_done": "Current directory changed to: {cwd}",
        "cd_failed": "Folder does not exist: {path}",
        "bye": "Exited the NoGUI terminal environment.",
    },
}


def load_core():
    loader = importlib.machinery.SourceFileLoader("ljm_desktop_core", CORE_PATH)
    spec = importlib.util.spec_from_file_location("ljm_desktop_core", CORE_PATH, loader=loader)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


core = load_core()


def log_line(message, log_file=DEFAULT_LOG_FILE):
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{stamp}] {message}\n")


def terminal_language():
    try:
        lang = core.active_language()
    except Exception:
        lang = ""
    return "zh_CN" if str(lang).lower().startswith("zh") else "en_US"


def terminal_text(key, language=None, **kwargs):
    lang = language or terminal_language()
    table = TERMINAL_TEXT.get(lang, TERMINAL_TEXT["en_US"])
    template = table.get(key, TERMINAL_TEXT["en_US"].get(key, key))
    try:
        return template.format(**kwargs)
    except Exception:
        return template


def configure_terminal_environment():
    if os.name == "nt":
        try:
            ctypes.windll.kernel32.SetConsoleOutputCP(65001)
            ctypes.windll.kernel32.SetConsoleCP(65001)
        except Exception:
            pass
    stdin_is_tty = bool(getattr(sys.stdin, "isatty", lambda: False)())
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
    if stdin_is_tty and hasattr(sys.stdin, "reconfigure"):
        try:
            sys.stdin.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if os.name != "nt":
        try:
            import readline  # noqa: F401
        except Exception:
            pass


def safe_print(message, end="\n"):
    try:
        if sys.stdout:
            print(str(message), end=end, flush=True)
    except UnicodeEncodeError:
        try:
            sys.stdout.buffer.write((str(message) + end).encode("utf-8", errors="replace"))
            sys.stdout.flush()
        except Exception:
            pass
    except Exception:
        pass


def write_result(payload, output_path=DEFAULT_RESULT_FILE, emit_stdout=False):
    payload = {
        "tool": "LJM Java Manager NoGUI",
        "desktop_version": getattr(core, "VERSION", "unknown"),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        **payload,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    if emit_stdout:
        safe_print(json.dumps(payload, ensure_ascii=False, indent=2))
    return payload


def progress_logger(prefix):
    def update_progress(percent, downloaded, total):
        if total:
            log_line(f"{prefix}: {percent:.1f}% ({downloaded}/{total})")
        else:
            log_line(f"{prefix}: downloaded {downloaded}")

    def update_status(message):
        log_line(f"{prefix}: {message}")

    return update_progress, update_status


def registry_rows():
    if hasattr(core, "cleanup_stale_java_registrations"):
        core.cleanup_stale_java_registrations()
    rows = []
    for version_name, java_home in core.JavaRegistryAdapter.get_all():
        runtime = core.read_java_runtime_info(java_home)
        report = core.get_java_health_report(java_home)
        rows.append(
            {
                "registry_name": version_name,
                "java_home": java_home,
                "vendor": runtime["vendor"],
                "major": runtime["major"],
                "package_type": runtime.get("package_type", "jdk"),
                "update_java_home": core.runtime_update_java_home(runtime),
                "nested_jre_home": runtime.get("nested_jre_home", ""),
                "version": core.version_display_text(runtime["version"]),
                "status": report["status"],
                "healthy": report["healthy"],
                "usable": report["usable"],
            }
        )
    return rows


def resolve_target(value):
    value_norm = core.normalize_text(value)
    if not value_norm:
        raise ValueError("target is empty")
    if os.path.isdir(value_norm):
        return value_norm, None
    for version_name, java_home in core.JavaRegistryAdapter.get_all():
        if value_norm.lower() == version_name.lower() or value_norm.lower() == java_home.lower():
            return java_home, version_name
    raise FileNotFoundError(f"Java target not found: {value}")


def find_source_jdk(extract_dir):
    return core.find_source_jdk_dir(extract_dir)


def download_latest_jdk(vendor, major, log_prefix="download", package_type="jdk"):
    package_type = core.normalize_java_package_type(package_type)
    primary_info = core.JavaDownloadEngine.get_latest_download_info(vendor, major, package_type=package_type)
    if not primary_info:
        raise RuntimeError(f"no available update source for {vendor} {package_type} {major}")

    progress_cb, status_cb = progress_logger(log_prefix)
    info_queue = [primary_info]
    seen_info = {core.JavaDownloadEngine._download_info_identity(primary_info)}
    fallback_loaded = False
    last_error = None

    while info_queue:
        info = dict(info_queue.pop(0))
        suffix = core.download_info_archive_suffix(info)
        fd, archive_path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        try:
            expected_sha256 = core.resolve_download_sha256(info)
            urls = info.get("urls") or [info["url"]]
            used_url = core.NetworkEngine.download_from_candidates(
                urls,
                archive_path,
                progress_cb,
                status_cb,
                expected_sha256=expected_sha256,
            )
            if core.APP_CONFIG.get("verify_download_sha256", True) and expected_sha256:
                core.verify_file_sha256(archive_path, expected_sha256)
            if not core.archive_quick_check(archive_path, suffix):
                raise RuntimeError("downloaded archive failed structure validation")
            info["used_url"] = used_url
            info["archive_path"] = archive_path
            info["archive_suffix"] = suffix
            return info
        except Exception as exc:
            last_error = exc
            try:
                if os.path.exists(archive_path):
                    os.remove(archive_path)
            except Exception:
                pass
            if not fallback_loaded:
                for candidate in core.JavaDownloadEngine.get_download_info_candidates(vendor, major, package_type=package_type):
                    key = core.JavaDownloadEngine._download_info_identity(candidate)
                    if key not in seen_info:
                        seen_info.add(key)
                        info_queue.append(candidate)
                fallback_loaded = True

    raise last_error


def extract_archive(info):
    extract_dir = tempfile.mkdtemp(prefix="ljm_nogui_extract_")
    if info["archive_suffix"] == ".tar.gz":
        with tarfile.open(info["archive_path"], "r:gz") as tar_ref:
            core.safe_extract_tar(tar_ref, extract_dir)
    else:
        with zipfile.ZipFile(info["archive_path"], "r") as zip_ref:
            core.safe_extract_zip(zip_ref, extract_dir)
    return extract_dir


def repair_or_update_target(target, mode="smart", vendor=None, major=None):
    java_home, registry_name = resolve_target(target)
    runtime = core.read_java_runtime_info(java_home)
    update_java_home = core.runtime_update_java_home(runtime)
    vendor = vendor or runtime["vendor"]
    major = str(major or runtime["major"])
    package_type = core.runtime_update_package_type(runtime)
    info = None
    extract_dir = ""
    try:
        info = download_latest_jdk(vendor, major, log_prefix=f"{vendor}-{package_type}-{major}", package_type=package_type)
        extract_dir = extract_archive(info)
        source_jdk = find_source_jdk(extract_dir)
        if mode == "smart":
            core.repair_java_home_smart(source_jdk, update_java_home)
        elif mode == "full":
            core.replace_java_home_atomically(source_jdk, update_java_home)
        else:
            raise ValueError("mode must be smart or full")
        synced = core.JavaRegistryAdapter.sync_runtime_registration(update_java_home, preferred_name=registry_name)
        return {
            "requested_java_home": java_home,
            "java_home": update_java_home,
            "nested_jre_home": runtime.get("nested_jre_home", ""),
            "registry_name": registry_name,
            "vendor": vendor,
            "major": major,
            "package_type": package_type,
            "mode": mode,
            "latest_version": core.version_display_text(info["version"]),
            "source": info.get("source"),
            "used_url": info.get("used_url"),
            "synced_registry_names": synced,
        }
    finally:
        if info and info.get("archive_path") and os.path.exists(info["archive_path"]):
            os.remove(info["archive_path"])
        if extract_dir and os.path.exists(extract_dir):
            core.shutil.rmtree(extract_dir, ignore_errors=True)


def set_default_java(target):
    java_home, registry_name = resolve_target(target)
    if core.IS_WIN:
        import ctypes
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
            0,
            winreg.KEY_WRITE,
        )
        try:
            winreg.SetValueEx(key, "JAVA_HOME", 0, winreg.REG_SZ, java_home)
        finally:
            winreg.CloseKey(key)
        ctypes.windll.user32.SendMessageTimeoutW(0xFFFF, 0x001A, 0, "Environment", 0, 1000, None)
        written = ["HKLM\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment"]
    else:
        written = core.write_unix_java_environment(java_home)
    return {"java_home": java_home, "registry_name": registry_name, "written": written}


def command_list(_args):
    return {"ok": True, "items": registry_rows()}


def command_scan(args):
    homes = core.discover_java_homes(args.paths, max_depth=args.max_depth)
    registered = []
    for java_home in homes:
        runtime = core.read_java_runtime_info(java_home)
        register_home = core.runtime_update_java_home(runtime)
        if core.normalize_path(register_home) != core.normalize_path(java_home):
            runtime = core.read_java_runtime_info(register_home)
        registry_name = core.build_registry_name(runtime)
        synced = core.JavaRegistryAdapter.sync_runtime_registration(register_home, preferred_name=registry_name)
        for synced_name in synced:
            registered.append({"registry_name": synced_name, "java_home": register_home})
    return {"ok": True, "found": homes, "registered": registered}


def command_check_updates(_args):
    rows = []
    for item in registry_rows():
        if not item["usable"]:
            rows.append({**item, "latest_version": "", "has_update": False, "error": "runtime is not usable"})
            continue
        try:
            info = core.JavaDownloadEngine.get_latest_download_info(item["vendor"], item["major"], package_type=item.get("package_type"))
            if not info:
                rows.append({**item, "latest_version": "", "has_update": False, "error": "no update source"})
                continue
            latest = core.version_display_text(info["version"])
            rows.append(
                {
                    **item,
                    "latest_version": latest,
                    "has_update": core.is_update_available(item["version"], latest, item["major"]),
                    "source": info.get("source"),
                }
            )
        except Exception as exc:
            rows.append({**item, "latest_version": "", "has_update": False, "error": str(exc)})
    return {"ok": True, "items": rows}


def command_repair(args):
    result = repair_or_update_target(args.target, mode=args.mode, vendor=args.vendor, major=args.major)
    return {"ok": True, "action": "repair", "result": result}


def command_update(args):
    result = repair_or_update_target(args.target, mode="full", vendor=args.vendor, major=args.major)
    return {"ok": True, "action": "update", "result": result}


def command_download(args):
    progress_cb, status_cb = progress_logger(f"download-{args.vendor}-{args.major}")
    result = core.download_and_install_java(args.vendor, args.major, args.parent, progress_cb, status_cb, package_type=args.package_type)
    return {"ok": True, "action": "download", "result": result}


def command_vendors(_args):
    items = []
    for vendor in core.JAVA_VENDOR_OPTIONS:
        profile = core.java_vendor_profile(vendor)
        items.append(
            {
                "vendor": vendor,
                "foojay": profile.get("foojay"),
                "scenario": profile.get("scenario"),
                "platforms": profile.get("platforms"),
                "minecraft": profile.get("minecraft"),
                "minecraft_performance": profile.get("minecraft_perf"),
                "pros": profile.get("pros"),
                "cons": profile.get("cons"),
            }
        )
    return {
        "ok": True,
        "platform": core.current_java_download_platform_text(),
        "majors": list(core.JAVA_MAJOR_OPTIONS),
        "items": items,
    }


def command_feedback(args):
    message = getattr(args, "message", "") or ""
    title = getattr(args, "title", "") or ""
    return {
        "ok": True,
        "action": "feedback",
        "url": core.build_github_feedback_url(message, title=title),
        "title": title or f"[Feedback] LJM Java Manager {core.VERSION}",
        "body": core.github_feedback_body(message),
    }


def command_move(args):
    java_home, registry_name = resolve_target(args.target)
    if not args.force:
        processes = core.find_processes_using_java_home(java_home)
        if processes:
            raise RuntimeError("target Java is in use: " + "; ".join(processes[:5]))
    result = core.move_java_home(java_home, args.destination, preferred_name=registry_name)
    return {"ok": True, "action": "move", "result": result}


def command_delete(args):
    java_home, registry_name = resolve_target(args.target)
    if args.files and not args.force:
        processes = core.find_processes_using_java_home(java_home)
        if processes:
            raise RuntimeError("target Java is in use: " + "; ".join(processes[:5]))
    result = core.delete_java_home(java_home, delete_files=args.files, preferred_name=registry_name)
    return {"ok": True, "action": "delete", "result": result}


def command_set_default(args):
    return {"ok": True, "action": "set-default", "result": set_default_java(args.target)}


def command_terminal(_args):
    return {"ok": True, "action": "terminal"}


def command_version(_args):
    return {"ok": True, "action": "version", "version": getattr(core, "VERSION", "unknown")}


def command_status(_args):
    return {
        "ok": True,
        "action": "status",
        "version": getattr(core, "VERSION", "unknown"),
        "result_file": DEFAULT_RESULT_FILE,
        "log_file": DEFAULT_LOG_FILE,
        "cwd": os.getcwd(),
        "platform": sys.platform,
    }


def build_parser():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--output", default=argparse.SUPPRESS, help="JSON result file path")
    common.add_argument("--stdout", action="store_true", default=argparse.SUPPRESS, help="also print JSON when running with python.exe")

    parser = argparse.ArgumentParser(
        description="LJM Java Manager nogui edition. No desktop window, no tray.",
        parents=[common],
    )

    sub = parser.add_subparsers(dest="command")

    p_list = sub.add_parser("list", parents=[common], help="list registered/discovered Java runtimes")
    p_list.set_defaults(func=command_list)

    p_scan = sub.add_parser("scan", parents=[common], help="scan directories and register Java runtimes")
    p_scan.add_argument("paths", nargs="+", help="directories to scan")
    p_scan.add_argument("--max-depth", type=int, default=6)
    p_scan.set_defaults(func=command_scan)

    p_check = sub.add_parser("check-updates", parents=[common], help="check all Java runtimes for updates")
    p_check.set_defaults(func=command_check_updates)

    p_repair = sub.add_parser("repair", parents=[common], help="repair a Java runtime")
    p_repair.add_argument("target", help="registered name or Java home path")
    p_repair.add_argument("--mode", choices=("smart", "full"), default="smart")
    p_repair.add_argument("--vendor")
    p_repair.add_argument("--major")
    p_repair.set_defaults(func=command_repair)

    p_update = sub.add_parser("update", parents=[common], help="download latest same-major runtime and fully replace target")
    p_update.add_argument("target", help="registered name or Java home path")
    p_update.add_argument("--vendor")
    p_update.add_argument("--major")
    p_update.set_defaults(func=command_update)

    p_download = sub.add_parser("download", parents=[common], help="download and register a new Java runtime under a parent folder")
    p_download.add_argument("vendor", help="Java vendor, for example: Eclipse Temurin")
    p_download.add_argument("major", help="Java major version, for example: 21")
    p_download.add_argument("parent", help="parent folder for the new Java installation")
    p_download.add_argument("--package-type", choices=("jdk", "jre"), default="jdk", help="runtime package type to download")
    p_download.set_defaults(func=command_download)

    p_vendors = sub.add_parser("vendors", parents=[common], help="list supported Java vendors and usage guidance")
    p_vendors.set_defaults(func=command_vendors)

    p_feedback = sub.add_parser("feedback", parents=[common], help="generate a prefilled GitHub feedback issue URL")
    p_feedback.add_argument("--message", default="", help="optional feedback text to prefill")
    p_feedback.add_argument("--title", default="", help="optional GitHub issue title")
    p_feedback.set_defaults(func=command_feedback)

    p_move = sub.add_parser("move", parents=[common], help="move a registered Java runtime and update registry/index")
    p_move.add_argument("target", help="registered name or Java home path")
    p_move.add_argument("destination", help="new Java home path; must not already exist")
    p_move.add_argument("--force", action="store_true", help="move even when related Java processes are detected")
    p_move.set_defaults(func=command_move)

    p_delete = sub.add_parser("delete", parents=[common], help="unregister a Java runtime and optionally delete its folder")
    p_delete.add_argument("target", help="registered name or Java home path")
    p_delete.add_argument("--files", action="store_true", help="delete the Java folder in addition to unregistering it")
    p_delete.add_argument("--force", action="store_true", help="delete even when related Java processes are detected")
    p_delete.set_defaults(func=command_delete)

    p_default = sub.add_parser("set-default", parents=[common], help="set target as default JAVA_HOME")
    p_default.add_argument("target", help="registered name or Java home path")
    p_default.set_defaults(func=command_set_default)

    p_terminal = sub.add_parser("terminal", parents=[common], help="start the interactive terminal environment")
    p_terminal.add_argument("--attach-console", action="store_true", help=argparse.SUPPRESS)
    p_terminal.set_defaults(func=command_terminal)

    p_version = sub.add_parser("version", parents=[common], help="print NoGUI version information")
    p_version.set_defaults(func=command_version)

    p_status = sub.add_parser("status", parents=[common], help="print NoGUI terminal and file status")
    p_status.set_defaults(func=command_status)

    return parser


def terminal_help_text(language=None):
    lang = language or terminal_language()
    return "\n".join(
        [
            terminal_text("commands_title", lang),
            terminal_text("cmd_list", lang),
            terminal_text("cmd_scan", lang),
            terminal_text("cmd_vendors", lang),
            terminal_text("cmd_check", lang),
            terminal_text("cmd_download", lang),
            terminal_text("cmd_repair", lang),
            terminal_text("cmd_update", lang),
            terminal_text("cmd_move", lang),
            terminal_text("cmd_delete", lang),
            terminal_text("cmd_default", lang),
            terminal_text("cmd_feedback", lang),
            terminal_text("cmd_builtin", lang),
        ]
    )


def terminal_split(command_line, platform_name=None):
    platform_name = platform_name or os.name
    if platform_name == "nt":
        tokens = shlex.split(command_line, posix=False)
        cleaned = []
        for token in tokens:
            if len(token) >= 2 and token[0] == token[-1] and token[0] in ("'", '"'):
                cleaned.append(token[1:-1])
            else:
                cleaned.append(token)
        return cleaned
    return shlex.split(command_line, posix=True)


def should_start_terminal(argv):
    return not argv


def terminal_stream_is_tty(stream):
    try:
        return bool(stream and stream.isatty())
    except Exception:
        return False


def terminal_encoding():
    return getattr(sys.stdin, "encoding", None) or locale.getpreferredencoding(False) or "utf-8"


def open_terminal_console_input():
    paths = ["CONIN$"] if os.name == "nt" else ["/dev/tty"]
    for path in paths:
        try:
            return open(path, "r", encoding=terminal_encoding(), errors="replace")
        except Exception:
            continue
    return None


def decode_terminal_input_bytes(data):
    if not data:
        return ""
    encodings = ["utf-8-sig", "utf-16"]
    for candidate in (getattr(sys.stdin, "encoding", None), locale.getpreferredencoding(False), "mbcs" if os.name == "nt" else None):
        if candidate and candidate not in encodings:
            encodings.append(candidate)
    for encoding in encodings:
        try:
            return data.decode(encoding)
        except Exception:
            continue
    return data.decode("utf-8", errors="replace")


def terminal_text_lines_from_stream(stream, language=None, close_stream=False):
    lang = language or terminal_language()
    try:
        while True:
            try:
                safe_print(terminal_text("prompt", lang), end="")
                line = stream.readline()
            except (EOFError, KeyboardInterrupt):
                return
            if line == "":
                return
            yield line.rstrip("\r\n")
    finally:
        if close_stream:
            try:
                stream.close()
            except Exception:
                pass


def terminal_stdin_lines(language=None):
    lang = language or terminal_language()
    if terminal_stream_is_tty(sys.stdin):
        yield from terminal_text_lines_from_stream(sys.stdin, lang)
        return
    buffer = getattr(sys.stdin, "buffer", None)
    if buffer is not None:
        text = decode_terminal_input_bytes(buffer.read())
        for line in text.splitlines():
            yield line
        return
    for line in sys.stdin:
        yield line


def terminal_input_lines(language=None, attach_console=False):
    if terminal_stream_is_tty(sys.stdin):
        yield from terminal_stdin_lines(language)
        return
    piped_lines = list(terminal_stdin_lines(language))
    if piped_lines:
        for line in piped_lines:
            yield line
        return
    if attach_console:
        console = open_terminal_console_input()
        if console is not None:
            yield from terminal_text_lines_from_stream(console, language, close_stream=True)


def normalize_terminal_argv(argv):
    if not argv:
        return argv
    command = argv[0].strip()
    lower_command = command.lower()
    if lower_command in TERMINAL_CANONICAL_COMMANDS:
        argv[0] = lower_command
    else:
        argv[0] = TERMINAL_COMMAND_ALIASES.get(lower_command, TERMINAL_COMMAND_ALIASES.get(command, command))
    return argv


def clear_terminal_screen():
    if os.name == "nt":
        os.system("cls")
    else:
        safe_print("\033[2J\033[H")


def handle_terminal_builtin(command_argv, language=None):
    if not command_argv:
        return True
    lang = language or terminal_language()
    command = command_argv[0].lower()
    if command in TERMINAL_HELP_COMMANDS:
        safe_print(terminal_help_text(lang))
        return True
    if command in TERMINAL_CLEAR_COMMANDS:
        clear_terminal_screen()
        return True
    if command in TERMINAL_VERSION_COMMANDS:
        safe_print(terminal_text("version", lang, version=getattr(core, "VERSION", "unknown")))
        return True
    if command in TERMINAL_STATUS_COMMANDS:
        safe_print(
            terminal_text(
                "status",
                lang,
                result=DEFAULT_RESULT_FILE,
                log=DEFAULT_LOG_FILE,
                cwd=os.getcwd(),
            )
        )
        return True
    if command == "pwd":
        safe_print(terminal_text("cwd", lang, cwd=os.getcwd()))
        return True
    if command == "cd":
        if len(command_argv) < 2:
            safe_print(terminal_text("cd_missing", lang))
            return True
        target = os.path.abspath(os.path.expanduser(command_argv[1]))
        if not os.path.isdir(target):
            safe_print(terminal_text("cd_failed", lang, path=command_argv[1]))
            return True
        os.chdir(target)
        safe_print(terminal_text("cd_done", lang, cwd=os.getcwd()))
        return True
    return False


def execute_parsed_args(args, parser=None, interactive=False):
    if not hasattr(args, "output"):
        args.output = DEFAULT_RESULT_FILE
    if not hasattr(args, "stdout"):
        args.stdout = False
    if not args.command:
        help_text = parser.format_help() if parser else ""
        payload = {"ok": False, "error": "no command provided", "help": help_text}
        write_result(payload, args.output, args.stdout or interactive)
        return 2
    if args.command == "terminal":
        return run_terminal(parser, attach_console=getattr(args, "attach_console", False))

    try:
        core.NetworkEngine.apply_proxy_settings()
        result = args.func(args)
        write_result(result, args.output, args.stdout or interactive)
        return 0
    except Exception as exc:
        log_line(traceback.format_exc())
        payload = {"ok": False, "error": str(exc), "traceback": traceback.format_exc()}
        write_result(payload, args.output, args.stdout or interactive)
        return 1


def run_terminal(parser=None, attach_console=False):
    configure_terminal_environment()
    parser = parser or build_parser()
    language = terminal_language()
    safe_print(terminal_text("connected", language))
    safe_print(terminal_text("title", language, version=getattr(core, "VERSION", "unknown")))
    safe_print(terminal_text("hint", language))
    for line in terminal_input_lines(language, attach_console=attach_console):
        try:
            command_line = line.strip().lstrip("\ufeff")
        except KeyboardInterrupt:
            safe_print("")
            safe_print(terminal_text("bye", language))
            return 0
        if not command_line:
            continue
        if command_line.lower() in TERMINAL_EXIT_COMMANDS:
            safe_print(terminal_text("bye", language))
            return 0
        try:
            command_argv = normalize_terminal_argv(terminal_split(command_line))
        except ValueError as exc:
            safe_print(terminal_text("parse_error", language, error=exc))
            continue
        if not command_argv:
            continue
        if command_argv[0].lower() in TERMINAL_EXIT_COMMANDS:
            safe_print(terminal_text("bye", language))
            return 0
        if handle_terminal_builtin(command_argv, language=language):
            continue
        try:
            args = parser.parse_args(command_argv)
        except SystemExit:
            safe_print(terminal_text("hint", language))
            continue
        result_code = execute_parsed_args(args, parser=parser, interactive=True)
        if result_code:
            safe_print(terminal_text("unknown_error", language, error=f"exit code {result_code}"))
    safe_print(terminal_text("bye", language))
    return 0


def main(argv=None):
    parser = build_parser()
    auto_terminal = argv is None
    argv = list(sys.argv[1:] if argv is None else argv)
    if auto_terminal and should_start_terminal(argv):
        return run_terminal(parser)
    args = parser.parse_args(argv)
    return execute_parsed_args(args, parser=parser)


if __name__ == "__main__":
    sys.exit(main())
