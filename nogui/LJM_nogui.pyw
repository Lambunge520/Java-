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

try:
    import readline as _readline
except Exception:
    _readline = None

try:
    import msvcrt as _msvcrt
except Exception:
    _msvcrt = None


# The shared desktop core normally hides/elevates the Windows console during
# startup. NoGUI must keep the caller's terminal and only request privileges
# when a concrete operation actually needs them.
os.environ["LJM_NOGUI"] = "1"


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
TERMINAL_TASKS_COMMANDS = {"tasks", "task", "jobs", "ps", "任务", "任務"}
TERMINAL_CANCEL_COMMANDS = {"cancel", "stop", "kill", "取消", "停止"}
TERMINAL_WAIT_COMMANDS = {"wait", "等待"}
TERMINAL_INTERRUPT = object()
TERMINAL_PROGRESS_BAR_WIDTH = 24
TERMINAL_PROGRESS_RENDER_INTERVAL = 0.8
TERMINAL_COMPLETION_COMMANDS = (
    "list",
    "scan",
    "check-updates",
    "download",
    "repair",
    "update",
    "move",
    "delete",
    "set-default",
    "vendors",
    "feedback",
    "language",
    "status",
    "version",
    "tasks",
    "cancel",
    "wait",
    "help",
    "clear",
    "pwd",
    "cd",
    "exit",
)
TERMINAL_COMPLETION_OPTIONS = {
    "list": ("--stdout", "--output"),
    "scan": ("--max-depth", "--stdout", "--output"),
    "check-updates": ("--stdout", "--output"),
    "download": ("--package-type", "--stdout", "--output"),
    "repair": ("--mode", "--vendor", "--major", "--stdout", "--output"),
    "update": ("--vendor", "--major", "--stdout", "--output"),
    "move": ("--force", "--stdout", "--output"),
    "delete": ("--files", "--force", "--stdout", "--output"),
    "set-default": ("--stdout", "--output"),
    "vendors": ("--stdout", "--output"),
    "feedback": ("--title", "--message", "--stdout", "--output"),
    "language": ("--stdout", "--output"),
    "status": ("--stdout", "--output"),
    "version": ("--stdout", "--output"),
}
_READLINE_COMPLETION_MATCHES = []
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
    "language",
    "tasks",
    "cancel",
    "wait",
    "terminal",
}
TERMINAL_COMMAND_ALIASES = {
    "l": "list",
    "ls": "list",
    "s": "scan",
    "cscan": "scan",
    "cu": "check-updates",
    "check": "check-updates",
    "checks": "check-updates",
    "updcheck": "check-updates",
    "r": "repair",
    "fix": "repair",
    "u": "update",
    "up": "update",
    "upd": "update",
    "dl": "download",
    "d": "download",
    "ven": "vendors",
    "vendor": "vendors",
    "vds": "vendors",
    "fb": "feedback",
    "mv": "move",
    "rm": "delete",
    "del": "delete",
    "def": "set-default",
    "default": "set-default",
    "java-default": "set-default",
    "lang": "language",
    "la": "language",
    "st": "status",
    "stat": "status",
    "v": "version",
    "jobs": "tasks",
    "job": "tasks",
    "ps": "tasks",
    "task": "tasks",
    "t": "tasks",
    "c": "cancel",
    "x": "cancel",
    "stop": "cancel",
    "kill": "cancel",
    "w": "wait",
    "列表": "list",
    "扫描": "scan",
    "掃描": "scan",
    "查更新": "check-updates",
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
    "语言": "language",
    "語言": "language",
    "任务": "tasks",
    "任務": "tasks",
    "取消": "cancel",
    "停止": "cancel",
    "等待": "wait",
}

TERMINAL_TEXT = {
    "zh_CN": {
        "connected": "已成功接入 LJM Java Manager NoGUI 终端环境。",
        "title": "LJM Java Manager NoGUI 终端 {version}",
        "hint": "输入 help/帮助 查看命令，输入 exit/退出 离开终端环境。",
        "prompt": "ljm无桌面> ",
        "commands_title": "可用命令:",
        "cmd_list": "  list / l / ls / 列表",
        "cmd_scan": "  scan / s <文件夹> / 扫描 <文件夹>",
        "cmd_vendors": "  vendors / ven / 发行商",
        "cmd_check": "  check-updates / cu / 检查更新",
        "cmd_download": "  download / dl \"Eclipse Temurin\" 21 <安装父目录> --package-type jdk",
        "cmd_repair": "  repair / r <注册名或Java目录> --mode smart",
        "cmd_update": "  update / u <注册名或Java目录>",
        "cmd_move": "  move / mv <注册名或Java目录> <新的Java目录>",
        "cmd_delete": "  delete / rm <注册名或Java目录> [--files] [--force]",
        "cmd_default": "  set-default / def <注册名或Java目录>",
        "cmd_language": "  language / lang [auto|zh_CN|en_US] / 语言 [自动|中文|English]",
        "cmd_tasks": "  tasks / t 查看后台任务，cancel / c [任务ID|all] 取消，wait / w [任务ID|all] 等待",
        "cmd_feedback": "  feedback --message \"反馈内容\"",
        "cmd_builtin": "  help/帮助, status/状态, version/版本, pwd, cd <目录>, clear/清屏, exit/退出；Tab 补全命令和参数",
        "language_auto": "自动跟随系统语言",
        "language_zh_CN": "简体中文",
        "language_en_US": "English",
        "language_show": "显示语言: {configured}; 当前生效: {active}; 系统检测: {detected}",
        "language_set": "显示语言已切换为: {configured}; 当前生效: {active}; 系统检测: {detected}",
        "parse_error": "命令解析失败: {error}",
        "unknown_error": "命令执行失败: {error}",
        "version": "当前 NoGUI 版本: {version}",
        "status": "已接入终端环境；结果文件: {result}; 日志文件: {log}; 当前目录: {cwd}",
        "cwd": "当前目录: {cwd}",
        "cd_missing": "请提供要进入的目录。",
        "cd_done": "当前目录已切换到: {cwd}",
        "cd_failed": "目录不存在: {path}",
        "task_started": "后台任务 #{task_id} 已开始: {label}",
        "task_progress": "任务 #{task_id} {label} {bar} {percent} {size} {message}",
        "task_completed": "任务 #{task_id} 已完成: {label}",
        "task_failed": "任务 #{task_id} 失败: {label} - {error}",
        "task_cancelled": "任务 #{task_id} 已取消: {label}",
        "task_cancel_requested": "已请求取消任务: {targets}",
        "task_cancel_none": "没有可取消的运行中任务。",
        "task_none": "暂无后台任务。",
        "task_list_header": "后台任务:",
        "task_line": "  #{task_id} [{status}] {task_type}: {detail} {bar} {percent} {size} {message}",
        "task_type_download": "下载",
        "task_type_update": "更新",
        "task_type_repair": "修复",
        "task_type_task": "任务",
        "task_wait_done": "等待完成: {targets}",
        "task_wait_none": "没有可等待的任务。",
        "task_ctrl_c_cancel": "已收到 Ctrl+C，请输入要取消的任务编号，例如 1；也可以输入 1 2 或 all。",
        "task_ctrl_c_no_task": "已收到 Ctrl+C；当前没有运行中的后台任务。再次输入 exit 可退出。",
        "task_cancel_selection_empty": "没有输入任务编号，已退出取消选择。",
        "bye": "已退出 NoGUI 终端环境。",
    },
    "en_US": {
        "connected": "Successfully connected to the LJM Java Manager NoGUI terminal environment.",
        "title": "LJM Java Manager NoGUI Terminal {version}",
        "hint": "Type help for commands, exit to leave the terminal environment.",
        "prompt": "ljm-nogui> ",
        "commands_title": "Available commands:",
        "cmd_list": "  list / l / ls",
        "cmd_scan": "  scan / s <folder>",
        "cmd_vendors": "  vendors / ven",
        "cmd_check": "  check-updates / cu",
        "cmd_download": "  download / dl \"Eclipse Temurin\" 21 <parent-folder> --package-type jdk",
        "cmd_repair": "  repair / r <name-or-java-home> --mode smart",
        "cmd_update": "  update / u <name-or-java-home>",
        "cmd_move": "  move / mv <name-or-java-home> <new-java-home>",
        "cmd_delete": "  delete / rm <name-or-java-home> [--files] [--force]",
        "cmd_default": "  set-default / def <name-or-java-home>",
        "cmd_language": "  language / lang [auto|zh_CN|en_US]",
        "cmd_tasks": "  tasks / t, cancel / c [task-id|all], wait / w [task-id|all]",
        "cmd_feedback": "  feedback --message \"text\"",
        "cmd_builtin": "  help, status, version, pwd, cd <folder>, clear/cls, exit; Tab completes commands and arguments",
        "language_auto": "Follow system language",
        "language_zh_CN": "Simplified Chinese",
        "language_en_US": "English",
        "language_show": "Display language: {configured}; active: {active}; detected system language: {detected}",
        "language_set": "Display language changed to: {configured}; active: {active}; detected system language: {detected}",
        "parse_error": "Command parse failed: {error}",
        "unknown_error": "Command failed: {error}",
        "version": "Current NoGUI version: {version}",
        "status": "Terminal environment connected; result file: {result}; log file: {log}; current directory: {cwd}",
        "cwd": "Current directory: {cwd}",
        "cd_missing": "Provide a folder to enter.",
        "cd_done": "Current directory changed to: {cwd}",
        "cd_failed": "Folder does not exist: {path}",
        "task_started": "Background task #{task_id} started: {label}",
        "task_progress": "Task #{task_id} {label} {bar} {percent} {size} {message}",
        "task_completed": "Task #{task_id} completed: {label}",
        "task_failed": "Task #{task_id} failed: {label} - {error}",
        "task_cancelled": "Task #{task_id} cancelled: {label}",
        "task_cancel_requested": "Cancel requested for: {targets}",
        "task_cancel_none": "No running task can be cancelled.",
        "task_none": "No background tasks.",
        "task_list_header": "Background tasks:",
        "task_line": "  #{task_id} [{status}] {task_type}: {detail} {bar} {percent} {size} {message}",
        "task_type_download": "Download",
        "task_type_update": "Update",
        "task_type_repair": "Repair",
        "task_type_task": "Task",
        "task_wait_done": "Wait finished: {targets}",
        "task_wait_none": "No task to wait for.",
        "task_ctrl_c_cancel": "Ctrl+C received. Enter the task number to cancel, such as 1; you can also enter 1 2 or all.",
        "task_ctrl_c_no_task": "Ctrl+C received; no running background task. Type exit to leave.",
        "task_cancel_selection_empty": "No task number entered; cancel selection closed.",
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

TERMINAL_OUTPUT_LOCK = threading.RLock()
TERMINAL_TASK_LOCK = threading.RLock()
TERMINAL_TASKS = {}
TERMINAL_TASK_COUNTER = 0

LANGUAGE_CHOICES = ("auto", "zh_CN", "en_US")
LANGUAGE_VALUE_ALIASES = {
    "auto": "auto",
    "system": "auto",
    "systemdefault": "auto",
    "default": "auto",
    "follow-system": "auto",
    "follow_system": "auto",
    "followsystem": "auto",
    "windows": "auto",
    "windows-default": "auto",
    "windows_default": "auto",
    "windowsdefault": "auto",
    "自动": "auto",
    "自動": "auto",
    "跟随系统": "auto",
    "跟隨系統": "auto",
    "系统": "auto",
    "系統": "auto",
    "系统默认": "auto",
    "系統預設": "auto",
    "windows默认": "auto",
    "windows預設": "auto",
    "zh": "zh_CN",
    "zh-cn": "zh_CN",
    "zh_cn": "zh_CN",
    "cn": "zh_CN",
    "chinese": "zh_CN",
    "simplified-chinese": "zh_CN",
    "simplified_chinese": "zh_CN",
    "中文": "zh_CN",
    "简体中文": "zh_CN",
    "簡體中文": "zh_CN",
    "汉语": "zh_CN",
    "漢語": "zh_CN",
    "en": "en_US",
    "en-us": "en_US",
    "en_us": "en_US",
    "english": "en_US",
    "英文": "en_US",
}


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


def normalize_language_value(value):
    raw = str(value or "").strip()
    if not raw:
        return ""
    key = raw.replace(" ", "").strip()
    lower_key = key.lower()
    if key in LANGUAGE_CHOICES:
        return key
    if lower_key in LANGUAGE_VALUE_ALIASES:
        return LANGUAGE_VALUE_ALIASES[lower_key]
    if key in LANGUAGE_VALUE_ALIASES:
        return LANGUAGE_VALUE_ALIASES[key]
    raise ValueError("language must be auto, zh_CN, or en_US")


def language_label(value, language=None):
    normalized = normalize_language_value(value) if value else "auto"
    return terminal_text(f"language_{normalized}", language or terminal_language())


def language_state_payload(changed=False):
    configured = core.APP_CONFIG.get("language", "auto")
    detected = core.detect_system_language()
    active = core.active_language()
    lang = active
    message_key = "language_set" if changed else "language_show"
    return {
        "ok": True,
        "action": "language",
        "changed": bool(changed),
        "configured": configured,
        "configured_label": language_label(configured, lang),
        "active": active,
        "active_label": language_label(active, lang),
        "detected": detected,
        "detected_label": language_label(detected, lang),
        "available": [
            {"value": value, "label": language_label(value, lang)}
            for value in LANGUAGE_CHOICES
        ],
        "message": terminal_text(
            message_key,
            lang,
            configured=language_label(configured, lang),
            active=language_label(active, lang),
            detected=language_label(detected, lang),
        ),
    }


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
    with TERMINAL_OUTPUT_LOCK:
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


def format_size_pair(downloaded, total):
    try:
        downloaded = int(downloaded or 0)
    except Exception:
        downloaded = 0
    try:
        total = int(total or 0)
    except Exception:
        total = 0
    if total > 0:
        return f"{core.format_file_size(downloaded)}/{core.format_file_size(total)}"
    if downloaded > 0:
        return core.format_file_size(downloaded)
    return "-"


def format_progress_bar(percent, width=TERMINAL_PROGRESS_BAR_WIDTH):
    try:
        value = max(0.0, min(100.0, float(percent or 0.0)))
    except Exception:
        value = 0.0
    filled = int(round(width * value / 100.0))
    return "[" + ("#" * filled) + ("-" * (width - filled)) + "]"


def task_snapshot(task):
    with TERMINAL_TASK_LOCK:
        return {
            "id": task.get("id"),
            "label": task.get("label", ""),
            "kind": task.get("kind", "task"),
            "detail": task.get("detail", task.get("label", "")),
            "action": task.get("action", ""),
            "status": task.get("status", ""),
            "progress": float(task.get("progress", 0.0) or 0.0),
            "downloaded": int(task.get("downloaded", 0) or 0),
            "total": int(task.get("total", 0) or 0),
            "message": task.get("message", ""),
            "error": task.get("error", ""),
            "started_at": task.get("started_at", 0),
            "finished_at": task.get("finished_at", 0),
        }


def format_task_line(task, language=None):
    item = task_snapshot(task)
    percent = f"{item['progress']:.1f}%" if item["total"] or item["progress"] else "--"
    task_type = terminal_text(f"task_type_{item['kind']}", language)
    return terminal_text(
        "task_line",
        language,
        task_id=item["id"],
        status=item["status"],
        task_type=task_type,
        detail=item["detail"],
        bar=format_progress_bar(item["progress"]),
        percent=percent,
        size=format_size_pair(item["downloaded"], item["total"]),
        message=item["message"],
    )


def terminal_task_records():
    with TERMINAL_TASK_LOCK:
        return [task_snapshot(task) for task in sorted(TERMINAL_TASKS.values(), key=lambda item: item.get("id", 0))]


def running_terminal_tasks():
    with TERMINAL_TASK_LOCK:
        return [task for task in sorted(TERMINAL_TASKS.values(), key=lambda item: item.get("id", 0)) if task.get("status") in ("running", "cancelling")]


def split_terminal_task_refs(ref=""):
    raw = str(ref or "").strip()
    if not raw:
        return []
    return [part.strip().lstrip("#") for part in raw.replace(",", " ").split() if part.strip()]


def is_terminal_task_ref_input(ref=""):
    refs = split_terminal_task_refs(ref)
    if not refs:
        return False
    for item in refs:
        if item.lower() in ("all", "*", "全部"):
            continue
        if not item.isdigit():
            return False
    return True


def resolve_terminal_task_refs(ref=""):
    refs = split_terminal_task_refs(ref)
    with TERMINAL_TASK_LOCK:
        tasks = sorted(TERMINAL_TASKS.values(), key=lambda item: item.get("id", 0))
        running = [task for task in tasks if task.get("status") in ("running", "cancelling")]
        if not refs:
            return running[-1:] if running else []
        if any(item.lower() in ("all", "*", "全部") for item in refs):
            return running
        task_ids = set()
        for item in refs:
            try:
                task_ids.add(int(item))
            except Exception:
                continue
        return [task for task in tasks if int(task.get("id", -1)) in task_ids]


def request_cancel_terminal_tasks(ref="", language=None):
    targets = [task for task in resolve_terminal_task_refs(ref) if task.get("status") in ("running", "cancelling")]
    if not targets:
        safe_print(terminal_text("task_cancel_none", language))
        return []
    labels = []
    with TERMINAL_TASK_LOCK:
        for task in targets:
            task["status"] = "cancelling"
            task["message"] = "cancel requested"
            task["cancel_event"].set()
            labels.append(f"#{task.get('id')}")
    safe_print(terminal_text("task_cancel_requested", language, targets=", ".join(labels)))
    return targets


def wait_terminal_tasks(ref="", language=None):
    targets = resolve_terminal_task_refs(ref)
    if not targets:
        safe_print(terminal_text("task_wait_none", language))
        return []
    labels = []
    for task in targets:
        thread = task.get("thread")
        if thread:
            thread.join()
        labels.append(f"#{task.get('id')}")
    safe_print(terminal_text("task_wait_done", language, targets=", ".join(labels)))
    return targets


def print_terminal_tasks(language=None):
    records = terminal_task_records()
    if not records:
        safe_print(terminal_text("task_none", language))
        return
    safe_print(terminal_text("task_list_header", language))
    with TERMINAL_TASK_LOCK:
        for task in sorted(TERMINAL_TASKS.values(), key=lambda item: item.get("id", 0)):
            safe_print(format_task_line(task, language))


def render_task_progress(task, force=False):
    now = time.time()
    with TERMINAL_TASK_LOCK:
        if not force and now - float(task.get("last_render", 0) or 0) < TERMINAL_PROGRESS_RENDER_INTERVAL:
            return
        task["last_render"] = now
        snapshot = task_snapshot(task)
    percent = f"{snapshot['progress']:.1f}%" if snapshot["total"] or snapshot["progress"] else "--"
    safe_print(
        terminal_text(
            "task_progress",
            terminal_language(),
            task_id=snapshot["id"],
            label=snapshot["label"],
            bar=format_progress_bar(snapshot["progress"]),
            percent=percent,
            size=format_size_pair(snapshot["downloaded"], snapshot["total"]),
            message=snapshot["message"],
        )
    )


def progress_logger(prefix, task=None):
    def update_progress(percent, downloaded, total):
        if total:
            log_line(f"{prefix}: {percent:.1f}% ({downloaded}/{total})")
        else:
            log_line(f"{prefix}: downloaded {downloaded}")
        if task is not None:
            with TERMINAL_TASK_LOCK:
                task["progress"] = max(0.0, min(100.0, float(percent or 0.0)))
                task["downloaded"] = int(downloaded or 0)
                task["total"] = int(total or 0)
            render_task_progress(task)

    def update_status(message):
        log_line(f"{prefix}: {message}")
        if task is not None:
            with TERMINAL_TASK_LOCK:
                task["message"] = str(message or "")
            render_task_progress(task)

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


def download_latest_jdk(vendor, major, log_prefix="download", package_type="jdk", progress_callback=None, status_callback=None, cancel_event=None):
    package_type = core.normalize_java_package_type(package_type)
    primary_info = core.JavaDownloadEngine.get_latest_download_info(vendor, major, package_type=package_type)
    if not primary_info:
        raise RuntimeError(f"no available update source for {vendor} {package_type} {major}")

    progress_cb, status_cb = progress_callback, status_callback
    if not progress_cb or not status_cb:
        progress_cb, status_cb = progress_logger(log_prefix)
    info_queue = [primary_info]
    seen_info = {core.JavaDownloadEngine._download_info_identity(primary_info)}
    fallback_loaded = False
    last_error = None

    while info_queue:
        core.ensure_not_cancelled(cancel_event)
        info = dict(info_queue.pop(0))
        suffix = core.download_info_archive_suffix(info)
        fd, archive_path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        try:
            core.ensure_not_cancelled(cancel_event)
            expected_sha256 = core.resolve_download_sha256(info)
            urls = info.get("urls") or [info["url"]]
            used_url = core.NetworkEngine.download_from_candidates(
                urls,
                archive_path,
                progress_cb,
                status_cb,
                cancel_event=cancel_event,
                expected_sha256=expected_sha256,
            )
            if core.APP_CONFIG.get("verify_download_sha256", True) and expected_sha256:
                core.verify_file_sha256(archive_path, expected_sha256, cancel_event=cancel_event)
            if not core.archive_quick_check(archive_path, suffix):
                raise RuntimeError("downloaded archive failed structure validation")
            info["used_url"] = used_url
            info["archive_path"] = archive_path
            info["archive_suffix"] = suffix
            return info
        except core.OperationCancelled:
            raise
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


def repair_or_update_target(target, mode="smart", vendor=None, major=None, progress_callback=None, status_callback=None, cancel_event=None):
    java_home, registry_name = resolve_target(target)
    runtime = core.read_java_runtime_info(java_home)
    update_java_home = core.runtime_update_java_home(runtime)
    vendor = vendor or runtime["vendor"]
    major = str(major or runtime["major"])
    package_type = core.runtime_update_package_type(runtime)
    info = None
    extract_dir = ""
    try:
        core.ensure_not_cancelled(cancel_event)
        info = download_latest_jdk(
            vendor,
            major,
            log_prefix=f"{vendor}-{package_type}-{major}",
            package_type=package_type,
            progress_callback=progress_callback,
            status_callback=status_callback,
            cancel_event=cancel_event,
        )
        extract_dir = extract_archive(info)
        core.ensure_not_cancelled(cancel_event)
        source_jdk = find_source_jdk(extract_dir)
        if mode == "smart":
            core.repair_java_home_smart(source_jdk, update_java_home, cancel_event=cancel_event)
            final_java_home = update_java_home
        elif mode == "full":
            final_java_home = core.resolve_update_java_home_target_path(update_java_home, info)
            if core.normalize_path(final_java_home) != core.normalize_path(update_java_home):
                old_names = core.JavaRegistryAdapter.find_version_names_by_home(update_java_home)
                core.replace_java_home_atomically(source_jdk, final_java_home, cancel_event=cancel_event)
                core.ensure_not_cancelled(cancel_event)
                if os.path.exists(update_java_home):
                    core.force_remove_tree(update_java_home)
                for name in old_names:
                    core.unregister_java_registry_name(name, java_home=update_java_home)
                if not registry_name and old_names:
                    registry_name = old_names[0]
            else:
                core.replace_java_home_atomically(source_jdk, final_java_home, cancel_event=cancel_event)
        else:
            raise ValueError("mode must be smart or full")
        core.ensure_not_cancelled(cancel_event)
        synced = core.JavaRegistryAdapter.sync_runtime_registration(final_java_home, preferred_name=registry_name)
        return {
            "requested_java_home": java_home,
            "java_home": final_java_home,
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
    task = getattr(args, "terminal_task", None)
    progress_cb, status_cb = progress_logger(f"repair-{args.target}", task=task)
    result = repair_or_update_target(
        args.target,
        mode=args.mode,
        vendor=args.vendor,
        major=args.major,
        progress_callback=progress_cb,
        status_callback=status_cb,
        cancel_event=getattr(args, "cancel_event", None),
    )
    return {"ok": True, "action": "repair", "result": result}


def command_update(args):
    task = getattr(args, "terminal_task", None)
    progress_cb, status_cb = progress_logger(f"update-{args.target}", task=task)
    result = repair_or_update_target(
        args.target,
        mode="full",
        vendor=args.vendor,
        major=args.major,
        progress_callback=progress_cb,
        status_callback=status_cb,
        cancel_event=getattr(args, "cancel_event", None),
    )
    return {"ok": True, "action": "update", "result": result}


def command_download(args):
    task = getattr(args, "terminal_task", None)
    progress_cb, status_cb = progress_logger(f"download-{args.vendor}-{args.major}", task=task)
    result = core.download_and_install_java(
        args.vendor,
        args.major,
        args.parent,
        progress_cb,
        status_cb,
        cancel_event=getattr(args, "cancel_event", None),
        package_type=args.package_type,
    )
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


def command_language(args):
    value = getattr(args, "value", None)
    changed = False
    if value:
        core.APP_CONFIG["language"] = normalize_language_value(value)
        core.save_config(core.APP_CONFIG)
        changed = True
    return language_state_payload(changed=changed)


def command_status(_args):
    return {
        "ok": True,
        "action": "status",
        "version": getattr(core, "VERSION", "unknown"),
        "result_file": DEFAULT_RESULT_FILE,
        "log_file": DEFAULT_LOG_FILE,
        "cwd": os.getcwd(),
        "platform": sys.platform,
        "nogui_mode": bool(getattr(core, "IS_NOGUI", False)),
        "language": language_state_payload(changed=False),
        "tasks": terminal_task_records(),
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

    p_list = sub.add_parser("list", aliases=["l", "ls"], parents=[common], help="list registered/discovered Java runtimes")
    p_list.set_defaults(func=command_list)

    p_scan = sub.add_parser("scan", aliases=["s"], parents=[common], help="scan directories and register Java runtimes")
    p_scan.add_argument("paths", nargs="+", help="directories to scan")
    p_scan.add_argument("--max-depth", type=int, default=6)
    p_scan.set_defaults(func=command_scan)

    p_check = sub.add_parser("check-updates", aliases=["cu", "check"], parents=[common], help="check all Java runtimes for updates")
    p_check.set_defaults(func=command_check_updates)

    p_repair = sub.add_parser("repair", aliases=["r", "fix"], parents=[common], help="repair a Java runtime")
    p_repair.add_argument("target", help="registered name or Java home path")
    p_repair.add_argument("--mode", choices=("smart", "full"), default="smart")
    p_repair.add_argument("--vendor")
    p_repair.add_argument("--major")
    p_repair.set_defaults(func=command_repair)

    p_update = sub.add_parser("update", aliases=["u", "up", "upd"], parents=[common], help="download latest same-major runtime and fully replace target")
    p_update.add_argument("target", help="registered name or Java home path")
    p_update.add_argument("--vendor")
    p_update.add_argument("--major")
    p_update.set_defaults(func=command_update)

    p_download = sub.add_parser("download", aliases=["dl", "d"], parents=[common], help="download and register a new Java runtime under a parent folder")
    p_download.add_argument("vendor", help="Java vendor, for example: Eclipse Temurin")
    p_download.add_argument("major", help="Java major version, for example: 21")
    p_download.add_argument("parent", help="parent folder for the new Java installation")
    p_download.add_argument("--package-type", choices=("jdk", "jre"), default="jdk", help="runtime package type to download")
    p_download.set_defaults(func=command_download)

    p_vendors = sub.add_parser("vendors", aliases=["ven", "vendor", "vds"], parents=[common], help="list supported Java vendors and usage guidance")
    p_vendors.set_defaults(func=command_vendors)

    p_feedback = sub.add_parser("feedback", aliases=["fb"], parents=[common], help="generate a prefilled GitHub feedback issue URL")
    p_feedback.add_argument("--message", default="", help="optional feedback text to prefill")
    p_feedback.add_argument("--title", default="", help="optional GitHub issue title")
    p_feedback.set_defaults(func=command_feedback)

    p_move = sub.add_parser("move", aliases=["mv"], parents=[common], help="move a registered Java runtime and update registry/index")
    p_move.add_argument("target", help="registered name or Java home path")
    p_move.add_argument("destination", help="new Java home path; must not already exist")
    p_move.add_argument("--force", action="store_true", help="move even when related Java processes are detected")
    p_move.set_defaults(func=command_move)

    p_delete = sub.add_parser("delete", aliases=["rm", "del"], parents=[common], help="unregister a Java runtime and optionally delete its folder")
    p_delete.add_argument("target", help="registered name or Java home path")
    p_delete.add_argument("--files", action="store_true", help="delete the Java folder in addition to unregistering it")
    p_delete.add_argument("--force", action="store_true", help="delete even when related Java processes are detected")
    p_delete.set_defaults(func=command_delete)

    p_default = sub.add_parser("set-default", aliases=["def", "default"], parents=[common], help="set target as default JAVA_HOME")
    p_default.add_argument("target", help="registered name or Java home path")
    p_default.set_defaults(func=command_set_default)

    p_terminal = sub.add_parser("terminal", parents=[common], help="start the interactive terminal environment")
    p_terminal.add_argument("--attach-console", action="store_true", help=argparse.SUPPRESS)
    p_terminal.set_defaults(func=command_terminal)

    p_version = sub.add_parser("version", aliases=["v", "ver"], parents=[common], help="print NoGUI version information")
    p_version.set_defaults(func=command_version)

    p_language = sub.add_parser("language", aliases=["lang", "la"], parents=[common], help="show or set display language: auto, zh_CN, en_US")
    p_language.add_argument("value", nargs="?", help="auto, zh_CN, en_US, or aliases such as zh/en/中文/English")
    p_language.set_defaults(func=command_language)

    p_status = sub.add_parser("status", aliases=["st", "stat"], parents=[common], help="print NoGUI terminal and file status")
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
            terminal_text("cmd_language", lang),
            terminal_text("cmd_tasks", lang),
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


def terminal_completion_token(line, cursor=None):
    text = str(line or "")
    cursor = len(text) if cursor is None else max(0, min(int(cursor), len(text)))
    prefix = text[:cursor]
    quote = ""
    token_start = 0
    escaped = False
    for index, char in enumerate(prefix):
        if escaped:
            escaped = False
            continue
        if char == "\\" and os.name != "nt":
            escaped = True
            continue
        if char in ('"', "'"):
            if quote == char:
                quote = ""
            elif not quote:
                quote = char
            continue
        if char.isspace() and not quote:
            token_start = index + 1
    return token_start, prefix[token_start:], prefix[:token_start]


def terminal_completion_tokens_before(text):
    before = str(text or "").strip()
    if not before:
        return []
    try:
        return terminal_split(before)
    except ValueError:
        return before.split()


def terminal_completion_format(value, quoted=False):
    value = str(value or "")
    if quoted or any(char.isspace() for char in value):
        return f'"{value}"'
    return value


def terminal_registered_name_candidates():
    try:
        return [str(name).strip() for name, _path in core.JavaRegistryAdapter.get_all() if str(name).strip()]
    except Exception:
        return []


def terminal_task_id_candidates():
    with TERMINAL_TASK_LOCK:
        ids = [str(task_id) for task_id in sorted(TERMINAL_TASKS)]
    return ids + ["all"]


def terminal_completion_candidates(line, cursor=None):
    _start, raw_current, before = terminal_completion_token(line, cursor)
    tokens = terminal_completion_tokens_before(before)
    quoted = raw_current.startswith(('"', "'"))
    current = raw_current[1:] if quoted else raw_current
    current_lower = current.lower()

    if not tokens:
        values = TERMINAL_COMPLETION_COMMANDS
    else:
        command = normalize_terminal_argv([tokens[0]])[0]
        argument_index = len(tokens) - 1
        previous = tokens[-1] if tokens else ""
        if previous == "--mode":
            values = ("smart", "full")
        elif previous == "--package-type":
            values = ("jdk", "jre")
        elif previous == "--major":
            values = core.JAVA_MAJOR_OPTIONS
        elif command == "download" and argument_index == 0:
            values = core.JAVA_VENDOR_OPTIONS
        elif command == "download" and argument_index == 1:
            values = core.JAVA_MAJOR_OPTIONS
        elif command == "language" and argument_index == 0:
            values = LANGUAGE_CHOICES
        elif command in ("cancel", "wait") and argument_index == 0:
            values = terminal_task_id_candidates()
        elif command in ("repair", "update", "move", "delete", "set-default") and argument_index == 0:
            values = terminal_registered_name_candidates()
        elif current.startswith("-"):
            values = TERMINAL_COMPLETION_OPTIONS.get(command, ())
        else:
            values = TERMINAL_COMPLETION_OPTIONS.get(command, ()) if not current else ()

    matches = []
    for value in values:
        logical = str(value)
        if logical.lower().startswith(current_lower):
            formatted = terminal_completion_format(logical, quoted=quoted)
            if formatted not in matches:
                matches.append(formatted)
    return sorted(matches, key=lambda item: item.lower())


def terminal_complete_line(line, cursor=None):
    text = str(line or "")
    cursor = len(text) if cursor is None else max(0, min(int(cursor), len(text)))
    start, raw_current, _before = terminal_completion_token(text, cursor)
    candidates = terminal_completion_candidates(text, cursor)
    if not candidates:
        return text, cursor, []
    if len(candidates) == 1:
        replacement = candidates[0] + " "
    else:
        replacement = os.path.commonprefix(candidates)
        if len(replacement) <= len(raw_current):
            return text, cursor, candidates
    updated = text[:start] + replacement + text[cursor:]
    return updated, start + len(replacement), candidates


def _readline_terminal_completer(_text, state):
    global _READLINE_COMPLETION_MATCHES
    if _readline is None:
        return None
    if state == 0:
        _READLINE_COMPLETION_MATCHES = terminal_completion_candidates(
            _readline.get_line_buffer(),
            _readline.get_endidx(),
        )
    if state < len(_READLINE_COMPLETION_MATCHES):
        return _READLINE_COMPLETION_MATCHES[state]
    return None


def configure_terminal_completion():
    if _readline is None:
        return False
    try:
        _readline.set_completer_delims(" \t\n")
        _readline.set_completer(_readline_terminal_completer)
        if "libedit" in str(getattr(_readline, "__doc__", "")).lower():
            _readline.parse_and_bind("bind ^I rl_complete")
        else:
            _readline.parse_and_bind("tab: complete")
        return True
    except Exception:
        return False


def windows_console_line_editor_available(stream):
    if os.name != "nt" or _msvcrt is None or stream is None:
        return False
    try:
        return bool(stream.isatty() and os.isatty(stream.fileno()))
    except Exception:
        return False


def posix_readline_input_available(stream):
    if os.name == "nt" or _readline is None or stream is not sys.stdin:
        return False
    try:
        return bool(stream.isatty() and os.isatty(stream.fileno()))
    except Exception:
        return False


def redraw_windows_console_line(prompt, line, cursor, previous_width=0):
    display = f"{prompt}{line}"
    width = max(previous_width, len(display))
    with TERMINAL_OUTPUT_LOCK:
        sys.stdout.write("\r" + (" " * width) + "\r" + display)
        if cursor < len(line):
            sys.stdout.write("\b" * (len(line) - cursor))
        sys.stdout.flush()
    return len(display)


def windows_console_readline(prompt):
    line = ""
    cursor = 0
    width = redraw_windows_console_line(prompt, line, cursor)
    while True:
        char = _msvcrt.getwch()
        if char in ("\r", "\n"):
            safe_print("")
            return line + "\n"
        if char == "\x03":
            safe_print("")
            raise KeyboardInterrupt()
        if char == "\x1a" and not line:
            safe_print("")
            return ""
        if char in ("\x00", "\xe0"):
            key = _msvcrt.getwch()
            if key == "K" and cursor > 0:
                cursor -= 1
            elif key == "M" and cursor < len(line):
                cursor += 1
            elif key == "G":
                cursor = 0
            elif key == "O":
                cursor = len(line)
            elif key == "S" and cursor < len(line):
                line = line[:cursor] + line[cursor + 1:]
            width = redraw_windows_console_line(prompt, line, cursor, width)
            continue
        if char == "\b":
            if cursor > 0:
                line = line[:cursor - 1] + line[cursor:]
                cursor -= 1
                width = redraw_windows_console_line(prompt, line, cursor, width)
            continue
        if char == "\t":
            updated, updated_cursor, candidates = terminal_complete_line(line, cursor)
            if updated != line:
                line, cursor = updated, updated_cursor
                width = redraw_windows_console_line(prompt, line, cursor, width)
            elif candidates:
                safe_print("")
                safe_print("  ".join(candidates))
                width = redraw_windows_console_line(prompt, line, cursor)
            continue
        if char.isprintable():
            line = line[:cursor] + char + line[cursor:]
            cursor += len(char)
            width = redraw_windows_console_line(prompt, line, cursor, width)


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
                prompt = terminal_text("prompt", lang)
                if windows_console_line_editor_available(stream):
                    line = windows_console_readline(prompt)
                elif posix_readline_input_available(stream):
                    try:
                        line = input(prompt) + "\n"
                    except EOFError:
                        return
                else:
                    safe_print(prompt, end="")
                    line = stream.readline()
            except KeyboardInterrupt:
                yield TERMINAL_INTERRUPT
                continue
            except EOFError:
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
    if command in TERMINAL_TASKS_COMMANDS:
        print_terminal_tasks(lang)
        return True
    if command in TERMINAL_CANCEL_COMMANDS:
        request_cancel_terminal_tasks(command_argv[1] if len(command_argv) > 1 else "", lang)
        return True
    if command in TERMINAL_WAIT_COMMANDS:
        wait_terminal_tasks(command_argv[1] if len(command_argv) > 1 else "", lang)
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


def should_run_as_terminal_task(args):
    return getattr(args, "func", None) in {command_download, command_update, command_repair}


def terminal_task_kind(args, command_argv=None):
    if getattr(args, "func", None) is command_download:
        return "download"
    if getattr(args, "func", None) is command_update:
        return "update"
    if getattr(args, "func", None) is command_repair:
        return "repair"
    action = str(getattr(args, "command", "") or (command_argv[0] if command_argv else "task"))
    if action in ("download", "dl", "d"):
        return "download"
    if action in ("update", "u", "up", "upd"):
        return "update"
    if action in ("repair", "r", "fix"):
        return "repair"
    return "task"


def build_terminal_task_detail(args, command_argv):
    kind = terminal_task_kind(args, command_argv)
    if kind == "download":
        package_type = getattr(args, "package_type", "jdk")
        return f"{getattr(args, 'vendor', '')} {package_type} {getattr(args, 'major', '')}".strip()
    if kind == "update":
        return str(getattr(args, "target", "")).strip()
    if kind == "repair":
        mode = getattr(args, "mode", "smart")
        target = str(getattr(args, "target", "")).strip()
        return f"{target} ({mode})".strip()
    return " ".join(command_argv).strip() or str(getattr(args, "command", "") or "task")


def build_terminal_task_label(args, command_argv):
    kind = terminal_task_kind(args, command_argv)
    detail = build_terminal_task_detail(args, command_argv)
    task_type = terminal_text(f"task_type_{kind}", terminal_language())
    if detail:
        return f"{task_type}: {detail}"
    return task_type


def start_terminal_task(args, command_argv, parser=None, language=None):
    global TERMINAL_TASK_COUNTER
    if not getattr(args, "output", ""):
        args.output = DEFAULT_RESULT_FILE
    if not hasattr(args, "stdout"):
        args.stdout = False
    with TERMINAL_TASK_LOCK:
        TERMINAL_TASK_COUNTER += 1
        task_id = TERMINAL_TASK_COUNTER
        task_kind = terminal_task_kind(args, command_argv)
        task_detail = build_terminal_task_detail(args, command_argv)
        task = {
            "id": task_id,
            "action": str(getattr(args, "command", "") or ""),
            "kind": task_kind,
            "detail": task_detail,
            "label": build_terminal_task_label(args, command_argv),
            "argv": list(command_argv),
            "status": "running",
            "progress": 0.0,
            "downloaded": 0,
            "total": 0,
            "message": "",
            "error": "",
            "result": None,
            "started_at": time.time(),
            "finished_at": 0,
            "last_render": 0,
            "cancel_event": threading.Event(),
            "thread": None,
        }
        TERMINAL_TASKS[task_id] = task

    args.cancel_event = task["cancel_event"]
    args.terminal_task = task

    def worker():
        try:
            core.NetworkEngine.apply_proxy_settings()
            result = args.func(args)
            with TERMINAL_TASK_LOCK:
                task["status"] = "completed"
                task["progress"] = max(float(task.get("progress", 0.0) or 0.0), 100.0)
                task["result"] = result
                task["finished_at"] = time.time()
                task["message"] = ""
            write_result({"ok": True, "task_id": task_id, **result}, args.output, False)
            render_task_progress(task, force=True)
            safe_print(terminal_text("task_completed", terminal_language(), task_id=task_id, label=task["label"]))
        except core.OperationCancelled:
            with TERMINAL_TASK_LOCK:
                task["status"] = "cancelled"
                task["finished_at"] = time.time()
                task["message"] = ""
            write_result({"ok": False, "task_id": task_id, "action": task["action"], "cancelled": True}, args.output, False)
            safe_print(terminal_text("task_cancelled", terminal_language(), task_id=task_id, label=task["label"]))
        except Exception as exc:
            log_line(traceback.format_exc())
            with TERMINAL_TASK_LOCK:
                task["status"] = "failed"
                task["error"] = str(exc)
                task["finished_at"] = time.time()
            write_result({"ok": False, "task_id": task_id, "action": task["action"], "error": str(exc), "traceback": traceback.format_exc()}, args.output, False)
            safe_print(terminal_text("task_failed", terminal_language(), task_id=task_id, label=task["label"], error=exc))

    thread = threading.Thread(target=worker, name=f"ljm-nogui-task-{task_id}", daemon=True)
    with TERMINAL_TASK_LOCK:
        task["thread"] = thread
    thread.start()
    safe_print(terminal_text("task_started", language, task_id=task_id, label=task["label"]))
    return task


def execute_parsed_args(args, parser=None, interactive=False):
    if not getattr(args, "output", ""):
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
    configure_terminal_completion()
    parser = parser or build_parser()
    language = terminal_language()
    cancel_selection_pending = False
    safe_print(terminal_text("connected", language))
    safe_print(terminal_text("title", language, version=getattr(core, "VERSION", "unknown")))
    safe_print(terminal_text("hint", language))
    for line in terminal_input_lines(language, attach_console=attach_console):
        if line is TERMINAL_INTERRUPT:
            language = terminal_language()
            if running_terminal_tasks():
                safe_print(terminal_text("task_ctrl_c_cancel", language))
                print_terminal_tasks(language)
                cancel_selection_pending = True
            else:
                safe_print(terminal_text("task_ctrl_c_no_task", language))
            continue
        try:
            command_line = line.strip().lstrip("\ufeff")
        except KeyboardInterrupt:
            language = terminal_language()
            if running_terminal_tasks():
                safe_print(terminal_text("task_ctrl_c_cancel", language))
                print_terminal_tasks(language)
                cancel_selection_pending = True
                continue
            safe_print(terminal_text("task_ctrl_c_no_task", language))
            continue
        if not command_line:
            if cancel_selection_pending:
                safe_print(terminal_text("task_cancel_selection_empty", language))
                cancel_selection_pending = False
            continue
        if cancel_selection_pending and is_terminal_task_ref_input(command_line):
            request_cancel_terminal_tasks(command_line, language)
            cancel_selection_pending = False
            continue
        if cancel_selection_pending:
            cancel_selection_pending = False
        if command_line.lower() in TERMINAL_EXIT_COMMANDS:
            if running_terminal_tasks():
                safe_print(terminal_text("task_ctrl_c_cancel", language))
                request_cancel_terminal_tasks("all", language)
                wait_terminal_tasks("all", language)
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
            if running_terminal_tasks():
                safe_print(terminal_text("task_ctrl_c_cancel", language))
                request_cancel_terminal_tasks("all", language)
                wait_terminal_tasks("all", language)
            safe_print(terminal_text("bye", language))
            return 0
        if handle_terminal_builtin(command_argv, language=language):
            continue
        try:
            args = parser.parse_args(command_argv)
        except SystemExit:
            safe_print(terminal_text("hint", language))
            continue
        if should_run_as_terminal_task(args):
            start_terminal_task(args, command_argv, parser=parser, language=language)
            language = terminal_language()
            continue
        result_code = execute_parsed_args(args, parser=parser, interactive=True)
        language = terminal_language()
        if result_code:
            safe_print(terminal_text("unknown_error", language, error=f"exit code {result_code}"))
    if running_terminal_tasks():
        safe_print(terminal_text("task_ctrl_c_cancel", language))
        request_cancel_terminal_tasks("all", language)
        wait_terminal_tasks("all", language)
    safe_print(terminal_text("bye", language))
    return 0


def main(argv=None):
    configure_terminal_environment()
    parser = build_parser()
    auto_terminal = argv is None
    argv = list(sys.argv[1:] if argv is None else argv)
    if auto_terminal and should_start_terminal(argv):
        return run_terminal(parser)
    args = parser.parse_args(argv)
    return execute_parsed_args(args, parser=parser)


if __name__ == "__main__":
    sys.exit(main())
