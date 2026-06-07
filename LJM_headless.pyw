import argparse
import importlib.util
import json
import os
import sys
import tarfile
import tempfile
import threading
import time
import traceback
import zipfile


APP_DIR = os.path.dirname(os.path.abspath(__file__))
CORE_PATH = os.path.join(APP_DIR, "LJM.pyw")
DEFAULT_RESULT_FILE = os.path.join(APP_DIR, "ljm_headless_result.json")
DEFAULT_LOG_FILE = os.path.join(APP_DIR, "ljm_headless.log")


def load_core():
    spec = importlib.util.spec_from_file_location("ljm_desktop_core", CORE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


core = load_core()


def log_line(message, log_file=DEFAULT_LOG_FILE):
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{stamp}] {message}\n")


def safe_print(message):
    try:
        if sys.stdout:
            print(message)
    except Exception:
        pass


def write_result(payload, output_path=DEFAULT_RESULT_FILE, emit_stdout=False):
    payload = {
        "tool": "LJM Java Manager Headless",
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
    exe = "java.exe" if core.IS_WIN else "java"
    for root_dir, dirs, _files in os.walk(extract_dir):
        if "bin" in dirs and os.path.exists(os.path.join(root_dir, "bin", exe)):
            return root_dir
        candidate_jre = os.path.join(root_dir, "jre", "bin", exe)
        if os.path.exists(candidate_jre):
            return root_dir
    raise FileNotFoundError("download archive does not contain a recognizable Java home")


def download_latest_jdk(vendor, major, log_prefix="download"):
    info = core.JavaDownloadEngine.get_latest_download_info(vendor, major)
    if not info:
        raise RuntimeError(f"no available update source for {vendor} {major}")

    suffix = core.current_archive_suffix(info["url"])
    fd, archive_path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    progress_cb, status_cb = progress_logger(log_prefix)
    urls = info.get("urls") or [info["url"]]
    used_url = core.NetworkEngine.download_from_candidates(urls, archive_path, progress_cb, status_cb)
    info["used_url"] = used_url
    info["archive_path"] = archive_path
    info["archive_suffix"] = suffix
    return info


def extract_archive(info):
    extract_dir = tempfile.mkdtemp(prefix="ljm_headless_extract_")
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
    vendor = vendor or runtime["vendor"]
    major = str(major or runtime["major"])
    info = None
    extract_dir = ""
    try:
        info = download_latest_jdk(vendor, major, log_prefix=f"{vendor}-{major}")
        extract_dir = extract_archive(info)
        source_jdk = find_source_jdk(extract_dir)
        if mode == "smart":
            core.repair_java_home_smart(source_jdk, java_home)
        elif mode == "full":
            core.replace_java_home_atomically(source_jdk, java_home)
        else:
            raise ValueError("mode must be smart or full")
        synced = core.JavaRegistryAdapter.sync_runtime_registration(java_home, preferred_name=registry_name)
        return {
            "java_home": java_home,
            "registry_name": registry_name,
            "vendor": vendor,
            "major": major,
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
        registry_name = core.build_registry_name(runtime)
        jvm_path = core.find_jvm_library(java_home)
        if core.JavaRegistryAdapter.register(registry_name, java_home, jvm_path):
            registered.append({"registry_name": registry_name, "java_home": java_home})
    return {"ok": True, "found": homes, "registered": registered}


def command_check_updates(_args):
    rows = []
    for item in registry_rows():
        if not item["usable"]:
            rows.append({**item, "latest_version": "", "has_update": False, "error": "runtime is not usable"})
            continue
        try:
            info = core.JavaDownloadEngine.get_latest_download_info(item["vendor"], item["major"])
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


def command_set_default(args):
    return {"ok": True, "action": "set-default", "result": set_default_java(args.target)}


def build_parser():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--output", default=argparse.SUPPRESS, help="JSON result file path")
    common.add_argument("--stdout", action="store_true", default=argparse.SUPPRESS, help="also print JSON when running with python.exe")

    parser = argparse.ArgumentParser(
        description="LJM Java Manager headless edition. No desktop window, no tray.",
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

    p_update = sub.add_parser("update", parents=[common], help="download latest same-major JDK and fully replace target")
    p_update.add_argument("target", help="registered name or Java home path")
    p_update.add_argument("--vendor")
    p_update.add_argument("--major")
    p_update.set_defaults(func=command_update)

    p_default = sub.add_parser("set-default", parents=[common], help="set target as default JAVA_HOME")
    p_default.add_argument("target", help="registered name or Java home path")
    p_default.set_defaults(func=command_set_default)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "output"):
        args.output = DEFAULT_RESULT_FILE
    if not hasattr(args, "stdout"):
        args.stdout = False
    if not args.command:
        help_text = parser.format_help()
        payload = {"ok": False, "error": "no command provided", "help": help_text}
        write_result(payload, args.output, args.stdout)
        return 2

    try:
        core.NetworkEngine.apply_proxy_settings()
        result = args.func(args)
        write_result(result, args.output, args.stdout)
        return 0
    except Exception as exc:
        log_line(traceback.format_exc())
        payload = {"ok": False, "error": str(exc), "traceback": traceback.format_exc()}
        write_result(payload, args.output, args.stdout)
        return 1


if __name__ == "__main__":
    sys.exit(main())
