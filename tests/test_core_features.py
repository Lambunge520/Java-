import importlib.machinery
import importlib.util
import json
import os
import re
import tempfile
import time
import unittest
import zipfile
from pathlib import Path
from urllib.parse import parse_qs, urlparse


def load_core():
    root = Path(__file__).resolve().parents[1]
    core_path = root / "src" / "LJM.pyw"
    loader = importlib.machinery.SourceFileLoader("ljm_core_test", str(core_path))
    spec = importlib.util.spec_from_file_location("ljm_core_test", str(core_path), loader=loader)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_nogui():
    root = Path(__file__).resolve().parents[1]
    nogui_path = root / "src" / "LJM_nogui.pyw"
    loader = importlib.machinery.SourceFileLoader("ljm_nogui_test", str(nogui_path))
    spec = importlib.util.spec_from_file_location("ljm_nogui_test", str(nogui_path), loader=loader)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CoreFeatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = load_core()

    def test_version_and_user_agent_are_30(self):
        self.assertEqual(self.core.VERSION, "3.0")
        self.assertEqual(self.core.default_headers()["User-Agent"], "JavaManager/3.0")

    def test_github_feedback_url_prefills_issue_context(self):
        url = self.core.build_github_feedback_url("下载 OpenJ9 时速度很慢")
        parsed = urlparse(url)
        query = parse_qs(parsed.query)

        self.assertEqual(f"{parsed.scheme}://{parsed.netloc}{parsed.path}", "https://github.com/Lambunge520/Java-/issues/new")
        self.assertEqual(query["template"][0], "bug_report.md")
        self.assertIn("3.0", query["body"][0])
        self.assertIn("Tool version", query["body"][0])
        self.assertIn("Download platform", query["body"][0])
        self.assertIn("下载 OpenJ9 时速度很慢", query["body"][0])
        self.assertLess(len(url), 6000)

    def test_network_route_candidates_keep_proxy_fallback_when_auto_direct(self):
        env = {
            "effective_direct": True,
            "system_proxies": {"https": "http://127.0.0.1:7890"},
        }

        self.assertEqual(self.core.NetworkEngine.connection_mode_candidates(env), ("direct", "proxy", "default"))

    def test_network_route_candidates_keep_direct_fallback_when_proxy_first(self):
        env = {
            "effective_direct": False,
            "system_proxies": {"https": "http://127.0.0.1:7890"},
        }

        self.assertEqual(self.core.NetworkEngine.connection_mode_candidates(env), ("proxy", "direct", "default"))

    def test_github_mirror_candidates_include_more_domestic_fallbacks(self):
        url = "https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21/test.zip"
        variants = self.core.build_github_url_variants(url)

        self.assertIn(url, variants)
        self.assertGreaterEqual(len(variants), 6)
        self.assertTrue(any("gh.llkk.cc" in item or "gh-proxy.com" in item for item in variants))

    def test_github_direct_first_keeps_mirror_fallbacks(self):
        url = "https://github.com/microsoft/openjdk/releases/download/jdk-21/test.zip"
        variants = self.core.build_github_url_variants(url, direct_first=True)

        self.assertEqual(variants[0], url)
        self.assertGreaterEqual(len(variants), 6)
        self.assertTrue(any(item.startswith("https://gh") and url in item for item in variants[1:]))

    def test_official_source_chain_degrades_to_github_and_mirrors(self):
        previous_source = self.core.APP_CONFIG.get("update_source")
        previous_mirror = self.core.APP_CONFIG.get("enable_mirror")
        try:
            self.core.APP_CONFIG["update_source"] = "official"
            self.core.APP_CONFIG["enable_mirror"] = False

            chain = self.core.JavaDownloadEngine._resolve_source_chain("Eclipse Temurin")
        finally:
            self.core.APP_CONFIG["update_source"] = previous_source
            self.core.APP_CONFIG["enable_mirror"] = previous_mirror

        self.assertEqual(chain[0], self.core.JavaDownloadEngine._fetch_official)
        self.assertIn(self.core.JavaDownloadEngine._fetch_github_direct, chain)
        self.assertIn(self.core.JavaDownloadEngine._fetch_github_mirror, chain)

    def test_new_user_download_source_prefers_mirrors_with_fallbacks(self):
        self.assertEqual(self.core.DEFAULT_CONFIG["update_source"], "mirror")
        self.assertTrue(self.core.DEFAULT_CONFIG["enable_mirror"])

        previous_source = self.core.APP_CONFIG.get("update_source")
        previous_mirror = self.core.APP_CONFIG.get("enable_mirror")
        try:
            self.core.APP_CONFIG["update_source"] = "mirror"
            self.core.APP_CONFIG["enable_mirror"] = True

            chain = self.core.JavaDownloadEngine._resolve_source_chain("Eclipse Temurin")
        finally:
            self.core.APP_CONFIG["update_source"] = previous_source
            self.core.APP_CONFIG["enable_mirror"] = previous_mirror

        self.assertEqual(chain[0], self.core.JavaDownloadEngine._fetch_github_mirror)
        self.assertIn(self.core.JavaDownloadEngine._fetch_official, chain)
        self.assertIn(self.core.JavaDownloadEngine._fetch_github_direct, chain)

    def test_download_from_candidates_tries_next_url_before_slow_route_fallback(self):
        first_url = "https://slow-mirror.invalid/jdk.zip"
        second_url = "https://fast-mirror.invalid/jdk.zip"
        calls = []
        payload = b"download-ok"
        original_detect = self.core.NetworkEngine.detect_environment
        original_open = self.core.NetworkEngine.open_request_with_mode

        class FakeResponse:
            status = 200

            def __init__(self, data):
                self._data = data
                self._offset = 0
                self.headers = {"Content-Length": str(len(data))}

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def getcode(self):
                return 200

            def read(self, size=-1):
                if self._offset >= len(self._data):
                    return b""
                if size is None or size < 0:
                    size = len(self._data) - self._offset
                chunk = self._data[self._offset:self._offset + size]
                self._offset += len(chunk)
                return chunk

        def fake_detect_environment(*_args, **_kwargs):
            return {
                "effective_direct": True,
                "system_proxies": {},
                "windows_proxy": {},
            }

        def fake_open_request(request_obj, timeout=10, mode="default", info=None):
            calls.append((request_obj.full_url, mode))
            if request_obj.full_url == first_url:
                raise TimeoutError("slow mirror")
            return FakeResponse(payload)

        try:
            self.core.NetworkEngine.detect_environment = staticmethod(fake_detect_environment)
            self.core.NetworkEngine.open_request_with_mode = staticmethod(fake_open_request)
            with tempfile.TemporaryDirectory() as tmp:
                dest = os.path.join(tmp, "jdk.zip")
                result = self.core.NetworkEngine.download_from_candidates(
                    [first_url, second_url],
                    dest,
                    lambda *_args: None,
                    lambda *_args: None,
                )
        finally:
            self.core.NetworkEngine.detect_environment = original_detect
            self.core.NetworkEngine.open_request_with_mode = original_open

        self.assertEqual(result, second_url)
        self.assertEqual(calls[:2], [(first_url, "direct"), (second_url, "direct")])
        self.assertEqual(len(calls), 2)

    def test_microsoft_github_mirror_uses_profile_release_source(self):
        calls = []
        original = self.core.JavaDownloadEngine._fetch_github_profile_releases

        def fake_profile(vendor, major_version, direct_first=False, mirrors_only=False, package_type="jdk"):
            calls.append((vendor, major_version, direct_first, mirrors_only, package_type))
            return {"version": "21.0.1", "url": "https://example.invalid/jdk.zip"}

        try:
            self.core.JavaDownloadEngine._fetch_github_profile_releases = staticmethod(fake_profile)
            result = self.core.JavaDownloadEngine._fetch_github_mirror("Microsoft Build of OpenJDK", "21")
        finally:
            self.core.JavaDownloadEngine._fetch_github_profile_releases = original

        self.assertEqual(result["version"], "21.0.1")
        self.assertEqual(calls, [("Microsoft Build of OpenJDK", "21", False, True, "jdk")])
        self.assertIn(
            "microsoft/openjdk-adoptium-marketplace-data",
            self.core.java_vendor_github_repos("Microsoft Build of OpenJDK", "21"),
        )

    def test_github_asset_selection_respects_requested_java_major(self):
        releases = [
            {
                "tag_name": "apr-2026-psu",
                "draft": False,
                "published_at": "2026-04-15T00:00:00Z",
                "assets": [
                    {"name": "jdk11-windows-x64.zip", "browser_download_url": "https://github.com/example/releases/jdk11.zip"},
                    {"name": "jdk21-windows-x64.zip", "browser_download_url": "https://github.com/example/releases/jdk21.zip"},
                ],
            }
        ]

        result = self.core.JavaDownloadEngine._pick_github_release_asset(releases, "21", "Microsoft Build of OpenJDK")

        self.assertEqual(result["asset_name"], "jdk21-windows-x64.zip")
        self.assertIn("jdk21.zip", result["url"])

    def test_adoptium_api_uses_feature_release_fallback(self):
        calls = []
        original_request = self.core.NetworkEngine.request_json

        def fake_request(url, *_args, **_kwargs):
            calls.append(url)
            if "/v3/assets/latest/" in url:
                raise RuntimeError("latest endpoint unavailable")
            if "/v3/assets/feature_releases/" in url:
                return [
                    {
                        "release_name": "jdk-21.0.3+9",
                        "version_data": {"openjdk_version": "21.0.3+9"},
                        "binaries": [
                            {
                                "image_type": "jdk",
                                "jvm_impl": "hotspot",
                                "package": {
                                    "link": "https://download.example.invalid/temurin-21.zip",
                                    "checksum": "a" * 64,
                                    "checksum_link": "https://download.example.invalid/temurin-21.zip.sha256",
                                    "name": "OpenJDK21U-jdk_x64_windows_hotspot_21.0.3_9.zip",
                                },
                            }
                        ],
                    }
                ]
            raise AssertionError(f"unexpected URL: {url}")

        try:
            self.core.NetworkEngine.request_json = staticmethod(fake_request)
            result = self.core.JavaDownloadEngine._fetch_adoptium_api("21", "hotspot", "Eclipse Temurin")
        finally:
            self.core.NetworkEngine.request_json = original_request

        self.assertIn("/v3/assets/latest/21/hotspot", calls[0])
        self.assertIn("/v3/assets/feature_releases/21/ga", calls[1])
        self.assertEqual(result["version"], "21.0.3+9")
        self.assertEqual(result["url"], "https://download.example.invalid/temurin-21.zip")
        self.assertEqual(result["source"], "Adoptium API feature_releases hotspot")

    def test_standalone_nogui_core_keeps_updated_java_source_endpoints(self):
        root = Path(__file__).resolve().parents[1]
        desktop_core = (root / "src" / "LJM.pyw").read_text(encoding="utf-8")
        standalone_core = (root / "nogui" / "LJM.pyw").read_text(encoding="utf-8")

        for marker in ("ADOPTIUM_API_ENDPOINTS", "_adoptium_asset_entries", "feature_releases"):
            with self.subTest(marker=marker):
                self.assertIn(marker, desktop_core)
                self.assertIn(marker, standalone_core)

    def test_java_filter_matches_multiple_terms_across_fields(self):
        row = {
            "version_name": "Temurin_17.0.12",
            "java_home": r"D:\Java\Eclipse Adoptium\jdk-17.0.12",
            "status": "正常可用",
            "mark": "[OK]",
            "runtime": {
                "vendor": "Eclipse Temurin",
                "version": "17.0.12+7",
                "major": "17",
            },
        }

        self.assertTrue(self.core.java_row_matches_query(row, "temurin 17 ok"))
        self.assertTrue(self.core.java_row_matches_query(row, "adoptium 正常"))
        self.assertFalse(self.core.java_row_matches_query(row, "temurin 21"))

    def test_legacy_jre8_nested_home_detects_major_8_not_default_17(self):
        with tempfile.TemporaryDirectory() as tmp:
            java_home = Path(tmp) / "Java" / "jre1.8.0_351" / "jre"
            bin_dir = java_home / "bin"
            bin_dir.mkdir(parents=True)
            (bin_dir / ("java.exe" if self.core.IS_WIN else "java")).write_text("", encoding="utf-8")

            runtime = self.core.read_java_runtime_info(str(java_home))

        self.assertEqual(runtime["major"], "8")
        self.assertIn("1.8.0_351", runtime["version"])
        self.assertEqual(runtime["package_type"], "jre")

    def test_embedded_jre_inside_vendor_jdk_uses_parent_jdk_update_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            jdk_home = Path(tmp) / "Java" / "dragonwell-8.29.28"
            jre_home = jdk_home / "jre"
            (jdk_home / "bin").mkdir(parents=True)
            (jre_home / "bin").mkdir(parents=True)
            (jdk_home / "release").write_text(
                'JAVA_VERSION="1.8.0_452"\nIMPLEMENTOR="Alibaba Dragonwell"\n',
                encoding="utf-8",
            )
            (jdk_home / "bin" / ("java.exe" if self.core.IS_WIN else "java")).write_text("", encoding="utf-8")
            (jdk_home / "bin" / ("javac.exe" if self.core.IS_WIN else "javac")).write_text("", encoding="utf-8")
            (jre_home / "bin" / ("java.exe" if self.core.IS_WIN else "java")).write_text("", encoding="utf-8")

            runtime = self.core.read_java_runtime_info(str(jre_home))

        self.assertEqual(runtime["vendor"], "Alibaba Dragonwell")
        self.assertEqual(runtime["major"], "8")
        self.assertEqual(runtime["package_type"], "jdk")
        self.assertEqual(Path(self.core.runtime_update_java_home(runtime)), jdk_home)
        self.assertEqual(self.core.runtime_update_package_type(runtime), "jdk")
        self.assertEqual(Path(runtime["nested_jre_home"]), jre_home)

    def test_jre_runtime_update_requests_jre_package_type(self):
        calls = []
        original_fetch = self.core.JavaDownloadEngine._fetch_foojay_distribution
        original_cache = dict(self.core.JavaDownloadEngine._cache)

        def fake_fetch(distribution, vendor, major_version, resolve_final_url=False, package_type="jdk"):
            calls.append((distribution, vendor, major_version, package_type))
            return {
                "version": "1.8.0_402",
                "url": "https://download.example.invalid/jre8.zip",
                "urls": ["https://download.example.invalid/jre8.zip"],
                "source": "Foojay temurin",
                "vendor": vendor,
                "package_type": package_type,
            }

        try:
            self.core.JavaDownloadEngine._cache.clear()
            self.core.JavaDownloadEngine._fetch_foojay_distribution = staticmethod(fake_fetch)
            result = self.core.JavaDownloadEngine.get_latest_download_info("Eclipse Temurin", "8", package_type="jre")
        finally:
            self.core.JavaDownloadEngine._fetch_foojay_distribution = original_fetch
            self.core.JavaDownloadEngine._cache.clear()
            self.core.JavaDownloadEngine._cache.update(original_cache)

        self.assertEqual(result["package_type"], "jre")
        self.assertIn(("temurin", "Eclipse Temurin", "8", "jre"), calls)

    def test_next_available_java_install_dir_uses_versioned_name(self):
        info = {
            "vendor": "IBM Semeru OpenJ9",
            "major_version": "26",
            "version": "26.0.1+9",
        }
        with tempfile.TemporaryDirectory() as tmp:
            first = self.core.next_available_java_install_dir(tmp, info)
            Path(first).mkdir()

            second = self.core.next_available_java_install_dir(tmp, info)

        self.assertEqual(Path(first).name, "IBM_Semeru_OpenJ9_jdk26_26.0.1_9")
        self.assertEqual(Path(second).name, "IBM_Semeru_OpenJ9_jdk26_26.0.1_9_2")

    def test_java_vendor_profiles_include_scenarios_and_foojay_ids(self):
        expected = {
            "Eclipse Temurin": "temurin",
            "IBM Semeru OpenJ9": "semeru",
            "Azul Zulu": "zulu",
            "Alibaba Dragonwell": "dragonwell",
            "GraalVM": "graalvm",
            "GraalVM Community": "graalvm_community",
            "Microsoft Build of OpenJDK": "microsoft",
            "Oracle Java": "oracle_open_jdk",
            "Oracle JDK": "oracle",
            "Oracle OpenJDK": "oracle_open_jdk",
            "Amazon Corretto": "corretto",
            "BellSoft Liberica": "liberica",
            "SAP SapMachine": "sap_machine",
            "OpenLogic OpenJDK": "openlogic",
            "JetBrains Runtime": "jetbrains",
            "Tencent Kona": "kona",
            "Huawei Bi Sheng": "bisheng",
            "Mandrel": "mandrel",
            "Liberica Native Image Kit": "liberica_native",
            "Gluon GraalVM": "gluon_graalvm",
            "Red Hat OpenJDK": "redhat",
            "IBM Semeru Certified": "semeru_certified",
        }

        for vendor, distribution in expected.items():
            with self.subTest(vendor=vendor):
                self.assertIn(vendor, self.core.JAVA_VENDOR_OPTIONS)
                profile = self.core.java_vendor_profile(vendor)
                self.assertEqual(profile["foojay"], distribution)
                self.assertTrue(profile["scenario"])
                self.assertTrue(profile["pros"])
                self.assertTrue(profile["cons"])
                self.assertTrue(profile["platforms"])
                self.assertTrue(profile["minecraft"])
                self.assertTrue(profile["minecraft_perf"])

    def test_minecraft_java_guidance_matches_major_versions(self):
        guidance_21 = self.core.minecraft_java_guidance("21", language="en_US")
        guidance_17 = self.core.minecraft_java_guidance("17", language="en_US")
        guidance_8 = self.core.minecraft_java_guidance("8", language="en_US")
        guidance_25 = self.core.minecraft_java_guidance("25", language="en_US")
        guidance_22_zh = self.core.minecraft_java_guidance("22", language="zh_CN")

        self.assertIn("1.20.5", guidance_21)
        self.assertIn("1.18", guidance_17)
        self.assertIn("1.16.5", guidance_8)
        self.assertIn("Minecraft 26", guidance_25)
        self.assertIn("Java 25", guidance_25)
        self.assertIn("实验", guidance_22_zh)

    def test_minecraft_jvm_profile_splits_launcher_argument_fields(self):
        pclce = self.core.build_minecraft_jvm_profile(
            launcher="PCLCE",
            profile="balanced",
            java_major="17",
            java_vendor="Eclipse Temurin",
            minecraft_version="1.20.1",
            system_memory_mb=16384,
            cpu_count=8,
            os_name="Windows",
            language="en_US",
        )
        pcl2 = self.core.build_minecraft_jvm_profile(
            launcher="PCL2",
            profile="balanced",
            java_major="17",
            java_vendor="Eclipse Temurin",
            minecraft_version="1.20.1",
            system_memory_mb=16384,
            cpu_count=8,
            os_name="Windows",
            language="en_US",
        )
        hmcl = self.core.build_minecraft_jvm_profile(
            launcher="HMCL",
            profile="balanced",
            java_major="17",
            java_vendor="Eclipse Temurin",
            minecraft_version="1.20.1",
            system_memory_mb=16384,
            cpu_count=8,
            os_name="Windows",
            language="en_US",
        )

        self.assertEqual(pclce["launcher"], "PCLCE")
        self.assertEqual(pclce["output_mode"], "split")
        self.assertIn("-Xms", pclce["head_args"])
        self.assertIn("-Xmx", pclce["head_args"])
        self.assertIn("-XX:+UseG1GC", pclce["tail_args"])
        self.assertEqual(pclce["combined_args"], f"{pclce['head_args']} {pclce['tail_args']}".strip())
        self.assertIn("PCLCE", pclce["copy_hint"])
        self.assertGreaterEqual(pclce["memory_mb"], 4096)
        self.assertLessEqual(pclce["memory_mb"], 8192)

        self.assertEqual(pcl2["launcher"], "PCL2")
        self.assertEqual(pcl2["output_mode"], "combined")
        self.assertEqual(pcl2["head_args"], "")
        self.assertEqual(pcl2["tail_args"], "")
        self.assertIn("-Xmx", pcl2["combined_args"])
        self.assertIn("-XX:+UseG1GC", pcl2["combined_args"])
        self.assertEqual(pcl2["combined_label"], "PCL2 combined JVM arguments")

        self.assertEqual(hmcl["launcher"], "HMCL")
        self.assertEqual(hmcl["output_mode"], "combined")
        self.assertEqual(hmcl["head_args"], "")
        self.assertEqual(hmcl["tail_args"], "")
        self.assertIn("-Xmx", hmcl["combined_args"])
        self.assertIn("-XX:+UseG1GC", hmcl["combined_args"])
        self.assertIn("HMCL", hmcl["copy_hint"])
        self.assertEqual(hmcl["combined_label"], "HMCL combined JVM arguments")

    def test_minecraft_jvm_profile_respects_java_and_mc_version_bands(self):
        legacy = self.core.build_minecraft_jvm_profile(
            launcher="PCL Community",
            profile="stable",
            java_major="8",
            java_vendor="Azul Zulu",
            minecraft_version="1.12.2",
            system_memory_mb=8192,
            cpu_count=4,
            os_name="Linux",
            language="en_US",
        )
        modern_perf = self.core.build_minecraft_jvm_profile(
            launcher="PCL",
            profile="performance",
            java_major="21",
            java_vendor="GraalVM",
            minecraft_version="1.21.1",
            system_memory_mb=32768,
            cpu_count=16,
            os_name="Linux",
            language="en_US",
        )

        legacy_args = f"{legacy['head_args']} {legacy['tail_args']} {legacy['combined_args']}"
        modern_args = f"{modern_perf['head_args']} {modern_perf['tail_args']} {modern_perf['combined_args']}"
        self.assertIn("legacy", legacy["minecraft_band"])
        self.assertIn("-XX:+UseG1GC", legacy_args)
        self.assertNotIn("UseZGC", legacy_args)
        self.assertNotIn("MaxRAMPercentage", legacy_args)
        self.assertLessEqual(legacy["memory_mb"], 4096)

        self.assertIn("modern", modern_perf["minecraft_band"])
        self.assertIn("-XX:+UseZGC", modern_args)
        self.assertIn("unstable", " ".join(modern_perf["warnings"]).lower())
        self.assertGreaterEqual(modern_perf["memory_mb"], 8192)
        self.assertLessEqual(modern_perf["memory_mb"], 12288)

    def test_minecraft_jvm_profile_uses_modern_gc_without_blind_flag_copying(self):
        perf21 = self.core.build_minecraft_jvm_profile(
            launcher="PCL2",
            profile="performance",
            java_major="21",
            java_vendor="Eclipse Temurin",
            minecraft_version="1.21.11",
            system_memory_mb=16384,
            cpu_count=12,
            os_name="Windows",
            language="en_US",
        )
        perf17 = self.core.build_minecraft_jvm_profile(
            launcher="PCL2",
            profile="performance",
            java_major="17",
            java_vendor="Eclipse Temurin",
            minecraft_version="1.20.1",
            system_memory_mb=16384,
            cpu_count=12,
            os_name="Windows",
            language="en_US",
        )
        balanced17 = self.core.build_minecraft_jvm_profile(
            launcher="PCL2",
            profile="balanced",
            java_major="17",
            java_vendor="Eclipse Temurin",
            minecraft_version="1.20.1",
            system_memory_mb=16384,
            cpu_count=12,
            os_name="Windows",
            language="en_US",
        )

        self.assertIn("-XX:+UseZGC", perf21["combined_args"])
        self.assertIn("-XX:+ZGenerational", perf21["combined_args"])
        self.assertIn(f"-Xms{perf21['memory_mb']}M", perf21["combined_args"])
        self.assertIn(f"-Xmx{perf21['memory_mb']}M", perf21["combined_args"])

        self.assertIn("-XX:+UseZGC", perf17["combined_args"])
        self.assertNotIn("-XX:+ZGenerational", perf17["combined_args"])

        self.assertIn("-XX:+UseG1GC", balanced17["combined_args"])
        self.assertIn("-XX:+UnlockExperimentalVMOptions", balanced17["combined_args"])
        self.assertIn("-XX:G1NewSizePercent=30", balanced17["combined_args"])
        self.assertIn("-XX:MaxGCPauseMillis=20", balanced17["combined_args"])
        self.assertEqual(balanced17["combined_args"].count("-XX:G1ReservePercent="), 1)

    def test_minecraft_jvm_profile_uses_selected_device_config_without_gpu_detection(self):
        profile = self.core.build_minecraft_jvm_profile(
            launcher="PCL2",
            profile="balanced",
            java_major="21",
            java_vendor="Eclipse Temurin",
            minecraft_version="1.21.1",
            system_memory_mb=32768,
            cpu_count=12,
            os_name="Windows 11",
            gpu_vram_mb=8192,
            language="en_US",
        )
        low_vram = self.core.build_minecraft_jvm_profile(
            launcher="PCL2",
            profile="performance",
            java_major="21",
            java_vendor="Eclipse Temurin",
            minecraft_version="1.21.1",
            system_memory_mb=8192,
            cpu_count=8,
            os_name="Linux",
            gpu_vram_mb=1024,
            language="en_US",
        )

        self.assertEqual(profile["system_memory_mb"], 32768)
        self.assertEqual(profile["gpu_vram_mb"], 8192)
        self.assertNotIn("gpu_name", profile)
        self.assertIn("Windows 11", profile["summary"])
        self.assertIn("32 GB RAM", profile["summary"])
        self.assertIn("8 GB VRAM", profile["summary"])
        self.assertIn("VRAM", " ".join(low_vram["warnings"]))
        self.assertEqual(self.core.MINECRAFT_DEVICE_VRAM_PRESETS[0], "auto")
        self.assertEqual(self.core.selected_device_memory_mb("20 GB"), 20480)
        self.assertEqual(self.core.selected_device_memory_mb("16"), 16384)
        self.assertEqual(self.core.selected_device_memory_mb("8"), 8192)
        self.assertEqual(self.core.parse_gpu_vram_mb("6"), 6144)
        self.assertIsNone(self.core.parse_gpu_vram_mb("auto"))
        typed_profile = self.core.build_minecraft_jvm_profile(
            launcher="PCL2",
            profile="performance",
            java_major="17",
            java_vendor="Eclipse Temurin",
            minecraft_version="1.21.1",
            system_memory_mb="16",
            cpu_count=8,
            os_name="Windows",
            gpu_vram_mb="6",
            language="en_US",
        )
        original_detect_vram = self.core.detect_system_vram_mb
        try:
            self.core.detect_system_vram_mb = lambda force_refresh=False: 6144
            auto_vram_profile = self.core.build_minecraft_jvm_profile(
                launcher="PCL2",
                profile="balanced",
                java_major="21",
                java_vendor="Eclipse Temurin",
                minecraft_version="1.21.1",
                system_memory_mb="16",
                cpu_count=8,
                os_name="Windows",
                gpu_vram_mb="auto",
                language="en_US",
            )
            auto_vram_profile_zh = self.core.build_minecraft_jvm_profile(
                launcher="PCL2",
                profile="balanced",
                java_major="21",
                java_vendor="Eclipse Temurin",
                minecraft_version="1.21.1",
                system_memory_mb="16",
                cpu_count=8,
                os_name="Windows",
                gpu_vram_mb="自动",
                language="zh_CN",
            )
        finally:
            self.core.detect_system_vram_mb = original_detect_vram
        self.assertEqual(typed_profile["system_memory_mb"], 16384)
        self.assertEqual(typed_profile["gpu_vram_mb"], 6144)
        self.assertNotIn("0.0 GB RAM", typed_profile["summary"])
        self.assertIn("16 GB RAM", typed_profile["summary"])
        self.assertIn("6 GB VRAM", typed_profile["summary"])
        self.assertEqual(auto_vram_profile["gpu_vram_mb"], 6144)
        self.assertIn("6 GB VRAM", auto_vram_profile["summary"])
        self.assertNotIn("Current device VRAM", auto_vram_profile["summary"])
        self.assertNotIn("Auto VRAM", auto_vram_profile["summary"])
        self.assertNotIn("unknown VRAM", auto_vram_profile["summary"])
        self.assertEqual(auto_vram_profile_zh["gpu_vram_mb"], 6144)
        self.assertIn("6 GB VRAM", auto_vram_profile_zh["summary"])
        self.assertNotIn("当前设备显存", auto_vram_profile_zh["summary"])
        self.assertNotIn("显存自动", auto_vram_profile_zh["summary"])

    def test_minecraft_vendor_advice_includes_performance_differences(self):
        hotspot = self.core.java_vendor_profile("Eclipse Temurin", language="zh_CN")
        openj9 = self.core.java_vendor_profile("IBM Semeru OpenJ9", language="zh_CN")
        graal = self.core.java_vendor_profile("GraalVM", language="en_US")

        self.assertIn("主流整合包", hotspot["minecraft"])
        self.assertIn("性能差距", hotspot["minecraft_perf"])
        self.assertIn("内存占用", openj9["minecraft_perf"])
        self.assertIn("performance", graal["minecraft_perf"].lower())

    def test_every_java_vendor_has_specific_minecraft_guidance(self):
        for vendor, profile in self.core.JAVA_VENDOR_PROFILES.items():
            with self.subTest(vendor=vendor):
                self.assertTrue(profile.get("minecraft_zh"))
                self.assertTrue(profile.get("minecraft_en"))
                self.assertTrue(profile.get("minecraft_perf_zh"))
                self.assertTrue(profile.get("minecraft_perf_en"))
                self.assertIn("性能差距", profile["minecraft_perf_zh"])
                self.assertIn("Performance gap", profile["minecraft_perf_en"])

    def test_tray_tooltip_includes_work_status(self):
        idle = self.core.tray_tooltip_text("2.9.4", active_tasks=0, background_running=False, language="zh_CN")
        busy = self.core.tray_tooltip_text("2.9.4", active_tasks=2, background_running=False, language="zh_CN")
        background = self.core.tray_tooltip_text("2.9.4", active_tasks=0, background_running=True, language="zh_CN")
        english = self.core.tray_tooltip_text("2.9.4", active_tasks=1, background_running=False, language="en_US")

        self.assertIn("工作状态", idle)
        self.assertIn("空闲", idle)
        self.assertIn("正在执行 2 个任务", busy)
        self.assertIn("后台检查", background)
        self.assertIn("Work status", english)
        self.assertIn("running 1 task", english)
        self.assertLessEqual(len(idle), 127)

    def test_management_tabs_have_motion_header_animation(self):
        self.assertEqual(self.core.blend_color("#000000", "#ffffff", 0.5), "#808080")
        root = Path(__file__).resolve().parents[1]
        source = (root / "src" / "LJM.pyw").read_text(encoding="utf-8")

        self.assertIn("TAB_MOTION_INTERVAL_MS = 18", source)
        self.assertIn("def _animate_tab_motion_header", source)
        for function_name in (
            "setup_reg_tab",
            "setup_fix_tab",
            "setup_fix_tab_enhanced",
            "setup_update_tab",
            "setup_download_tab",
            "setup_move_tab",
            "setup_delete_tab",
        ):
            match = re.search(rf"    def {function_name}\(self\):\n(?P<body>.*?)(?=\n    def |\nclass |\Z)", source, re.S)
            self.assertIsNotNone(match, function_name)
            self.assertIn("_create_tab_motion_header", match.group("body"), function_name)

    def test_unregister_selected_uses_equivalent_java_home_cleanup(self):
        calls = []

        class Listbox:
            def curselection(self):
                return (0, 1)

            def get(self, index):
                return (
                    "[OK] Root  [C:\\Java\\jdk8]",
                    "[!] MissingNameOnly",
                )[index]

        app = type("App", (), {})()
        app.lb_reg = Listbox()
        app.refresh_all_data = lambda: calls.append(("refresh",))

        original_unregister_home = self.core.unregister_java_home
        original_unregister = self.core.JavaRegistryAdapter.unregister
        try:
            self.core.unregister_java_home = lambda path, preferred_name=None: calls.append(("home", path, preferred_name))
            self.core.JavaRegistryAdapter.unregister = staticmethod(lambda name: calls.append(("name", name)))

            self.core.JavaManagerApp.unregister_selected(app)
        finally:
            self.core.unregister_java_home = original_unregister_home
            self.core.JavaRegistryAdapter.unregister = original_unregister

        self.assertEqual(
            calls,
            [
                ("home", "C:\\Java\\jdk8", "Root"),
                ("name", "MissingNameOnly"),
                ("refresh",),
            ],
        )

    def test_release_notes_and_workflows_are_bilingual(self):
        root = Path(__file__).resolve().parents[1]
        notes = (root / "docs" / "releases" / "RELEASE_NOTES_3.0.md").read_text(encoding="utf-8")
        template = (root / "docs" / "releases" / "RELEASE_NOTES_TEMPLATE_BILINGUAL.md").read_text(encoding="utf-8")
        gui_workflow = (root / ".github" / "workflows" / "build-packages.yml").read_text(encoding="utf-8")
        nogui_workflow = (root / ".github" / "workflows" / "build-nogui-packages.yml").read_text(encoding="utf-8")

        self.assertIn("## 中文", notes)
        self.assertIn("## English", notes)
        self.assertIn("JVM", notes)
        self.assertIn("Minecraft", notes)
        self.assertLessEqual(len(notes.splitlines()), 32)
        self.assertIn("## 中文", template)
        self.assertIn("## English", template)
        for workflow in (gui_workflow, nogui_workflow):
            self.assertIn("RELEASE_NOTES_FILE", workflow)
            self.assertIn('RELEASE_VERSION="${RELEASE_TAG#v}"', workflow)
            self.assertIn("RELEASE_NOTES_TEMPLATE_BILINGUAL.md", workflow)
            self.assertIn('--notes-file "$RELEASE_NOTES_FILE"', workflow)
            self.assertIn("python-source.zip", workflow)
            self.assertIn("src/LJM.pyw", workflow)

    def test_nogui_usage_docs_are_bilingual_and_asset_focused(self):
        root = Path(__file__).resolve().parents[1]
        docs = (root / "docs" / "NOGUI_USAGE.md").read_text(encoding="utf-8")
        readme = (root / "README.md").read_text(encoding="utf-8")
        standalone = (root / "nogui" / "README.md").read_text(encoding="utf-8")

        for text in (docs, standalone):
            self.assertIn("## 中文", text)
            self.assertIn("## English", text)
        for marker in (
            "LJM-Java-Manager-nogui-windows.zip",
            "LJM-Java-Manager-nogui-linux.tar.gz",
            "LJM-Java-Manager-nogui-macos.zip",
            "SHA256SUMS-nogui.txt",
            "LJM-Java-Manager-nogui.run",
            "LJM-Java-Manager-nogui.command",
        ):
            self.assertIn(marker, docs)
        self.assertIn("docs/NOGUI_USAGE.md", readme)
        self.assertIn("当前版本：`3.0`", readme)
        self.assertNotIn("Current version:", readme)
        self.assertIn("../docs/NOGUI_USAGE.md", standalone)

    def test_windows_self_update_script_retries_locked_old_executable_and_skips_payload_copy(self):
        app = object.__new__(self.core.JavaManagerApp)
        original_path = self.core.APP_EXECUTABLE_PATH
        try:
            self.core.APP_EXECUTABLE_PATH = r"C:\LJM\LJM-Java-Manager.exe"
            script = app._windows_self_update_script(
                temp_new=r"C:\LJM\LJM-Java-Manager.exe.new",
                bundle_dir=r"C:\Temp\ljm-update\bundle",
                cleanup_dir=r"C:\Temp\ljm-update",
                target_dir=r"C:\LJM",
                launch_command=r'"C:\LJM\LJM-Java-Manager.exe"',
            )
        finally:
            self.core.APP_EXECUTABLE_PATH = original_path

        self.assertIn(":replace_self_update", script)
        self.assertIn("if errorlevel 1", script)
        self.assertIn('/XF "LJM-Java-Manager.exe"', script)
        self.assertIn("robocopy", script.lower())
        self.assertNotIn("xcopy", script.lower())

    def test_new_vendor_registry_tokens_are_clear(self):
        cases = [
            ("Oracle JDK", "OracleJDK_21.0.9"),
            ("Oracle OpenJDK", "OracleOpenJDK_21.0.2"),
            ("Red Hat OpenJDK", "RedHat_17.0.16"),
            ("IBM Semeru Certified", "SemeruCertified_21.0.9"),
        ]

        for vendor, expected in cases:
            with self.subTest(vendor=vendor):
                self.assertEqual(
                    self.core.build_registry_name({"vendor": vendor, "version": expected.split("_", 1)[1]}),
                    expected,
                )

    def test_java_install_dir_name_keeps_vendor_type_visible(self):
        cases = [
            ({"vendor": "GraalVM", "major_version": "21", "version": "21.0.2"}, "GraalVM_jdk21_21.0.2"),
            ({"vendor": "Azul Zulu", "major_version": "17", "version": "17.0.12+7"}, "Azul_Zulu_jdk17_17.0.12_7"),
            ({"vendor": "Amazon Corretto", "major_version": "21", "version": "21.0.8"}, "Amazon_Corretto_jdk21_21.0.8"),
        ]

        for info, expected in cases:
            with self.subTest(vendor=info["vendor"]):
                self.assertEqual(self.core.java_install_dir_name(info), expected)

    def test_foojay_item_major_filter_uses_java_version_not_distribution_version(self):
        wrong_java_major = {
            "java_version": "21.3.3.1",
            "distribution_version": "21.3.3.1",
            "jdk_version": "21",
            "filename": "bellsoft-liberica-vm-full-openjdk11.0.17+7-21.3.3.1+1-windows-amd64.zip",
        }
        matching_java_major = {
            "java_version": "21.0.11+11",
            "distribution_version": "21.0.11+11",
            "filename": "bellsoft-jdk21.0.11+11-windows-amd64.zip",
        }

        self.assertFalse(self.core.JavaDownloadEngine._foojay_item_matches_major(wrong_java_major, "21"))
        self.assertTrue(self.core.JavaDownloadEngine._foojay_item_matches_major(matching_java_major, "21"))

    def test_foojay_item_selection_prefers_highest_java_version(self):
        items = [
            {
                "java_version": "17.0.3",
                "distribution_version": "17.0.3.0.6",
                "filename": "java-17-openjdk-17.0.3.0.6-2.win.x86_64.zip",
            },
            {
                "java_version": "21.0.2",
                "distribution_version": "21.0.2+13",
                "filename": "openjdk-21.0.2_windows-x64_bin.zip",
            },
            {
                "java_version": "17.0.16+8",
                "distribution_version": "17.0.16.0.8",
                "filename": "java-17-openjdk-17.0.16.0.8-1.win.jdk.x86_64.zip",
            },
        ]

        selected = self.core.JavaDownloadEngine._select_best_foojay_item(items, "17")

        self.assertEqual(selected["java_version"], "17.0.16+8")

    def test_download_and_install_switches_metadata_source_after_download_failure(self):
        primary = {
            "vendor": "Eclipse Temurin",
            "major_version": "21",
            "version": "21.0.1",
            "url": "https://primary.invalid/jdk.zip",
            "urls": ["https://primary.invalid/jdk.zip"],
            "source": "Primary",
        }
        fallback = {
            "vendor": "Eclipse Temurin",
            "major_version": "21",
            "version": "21.0.2",
            "url": "https://fallback.invalid/jdk.zip",
            "urls": ["https://fallback.invalid/jdk.zip"],
            "source": "Fallback",
        }
        calls = []
        previous_cache = self.core.APP_CONFIG.get("download_cache_enabled")
        previous_verify = self.core.APP_CONFIG.get("verify_download_sha256")
        original_latest = self.core.JavaDownloadEngine.get_latest_download_info
        original_candidates = self.core.JavaDownloadEngine.get_download_info_candidates
        original_download = self.core.NetworkEngine.download_from_candidates
        original_sync = self.core.JavaRegistryAdapter.sync_runtime_registration

        def fake_download(urls, dest, *_args, **_kwargs):
            calls.append(list(urls))
            if len(calls) == 1:
                raise RuntimeError("primary failed")
            with zipfile.ZipFile(dest, "w") as archive:
                archive.writestr("jdk-21/release", 'JAVA_VERSION="21.0.2"\nIMPLEMENTOR="Eclipse Temurin"\n')
                archive.writestr("jdk-21/bin/java.exe" if self.core.IS_WIN else "jdk-21/bin/java", "")
            return urls[0]

        try:
            self.core.APP_CONFIG["download_cache_enabled"] = False
            self.core.APP_CONFIG["verify_download_sha256"] = False
            self.core.JavaDownloadEngine.get_latest_download_info = staticmethod(lambda vendor, major, package_type="jdk": dict(primary))
            self.core.JavaDownloadEngine.get_download_info_candidates = staticmethod(lambda vendor, major, package_type="jdk": [dict(primary), dict(fallback)])
            self.core.NetworkEngine.download_from_candidates = staticmethod(fake_download)
            self.core.JavaRegistryAdapter.sync_runtime_registration = staticmethod(lambda java_home, preferred_name=None: ["Temurin_21"])

            with tempfile.TemporaryDirectory() as tmp:
                result = self.core.download_and_install_java("Eclipse Temurin", "21", tmp)
        finally:
            self.core.APP_CONFIG["download_cache_enabled"] = previous_cache
            self.core.APP_CONFIG["verify_download_sha256"] = previous_verify
            self.core.JavaDownloadEngine.get_latest_download_info = original_latest
            self.core.JavaDownloadEngine.get_download_info_candidates = original_candidates
            self.core.NetworkEngine.download_from_candidates = original_download
            self.core.JavaRegistryAdapter.sync_runtime_registration = original_sync

        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[1], fallback["urls"])
        self.assertEqual(result["source"], "Fallback")
        self.assertIn("21.0.2", result["latest_version"])

    def test_download_and_install_uses_requested_jre_package_type(self):
        info = {
            "vendor": "Eclipse Temurin",
            "major_version": "8",
            "version": "1.8.0_402",
            "package_type": "jre",
            "url": "https://download.invalid/jre.zip",
            "urls": ["https://download.invalid/jre.zip"],
            "source": "Test JRE",
        }
        calls = []
        previous_cache = self.core.APP_CONFIG.get("download_cache_enabled")
        previous_verify = self.core.APP_CONFIG.get("verify_download_sha256")
        original_latest = self.core.JavaDownloadEngine.get_latest_download_info
        original_download = self.core.NetworkEngine.download_from_candidates
        original_sync = self.core.JavaRegistryAdapter.sync_runtime_registration

        def fake_latest(vendor, major, package_type="jdk"):
            calls.append((vendor, major, package_type))
            return dict(info)

        def fake_download(urls, dest, *_args, **_kwargs):
            with zipfile.ZipFile(dest, "w") as archive:
                archive.writestr("jre-8/bin/java.exe" if self.core.IS_WIN else "jre-8/bin/java", "")
            return urls[0]

        try:
            self.core.APP_CONFIG["download_cache_enabled"] = False
            self.core.APP_CONFIG["verify_download_sha256"] = False
            self.core.JavaDownloadEngine.get_latest_download_info = staticmethod(fake_latest)
            self.core.NetworkEngine.download_from_candidates = staticmethod(fake_download)
            self.core.JavaRegistryAdapter.sync_runtime_registration = staticmethod(lambda java_home, preferred_name=None: ["Temurin_8_JRE"])

            with tempfile.TemporaryDirectory() as tmp:
                result = self.core.download_and_install_java("Eclipse Temurin", "8", tmp, package_type="jre")
        finally:
            self.core.APP_CONFIG["download_cache_enabled"] = previous_cache
            self.core.APP_CONFIG["verify_download_sha256"] = previous_verify
            self.core.JavaDownloadEngine.get_latest_download_info = original_latest
            self.core.NetworkEngine.download_from_candidates = original_download
            self.core.JavaRegistryAdapter.sync_runtime_registration = original_sync

        self.assertEqual(calls, [("Eclipse Temurin", "8", "jre")])
        self.assertEqual(result["package_type"], "jre")
        self.assertIn("_jre8_", Path(result["java_home"]).name)

    def test_download_and_install_repairs_unix_java_permissions_from_zip(self):
        info = {
            "vendor": "Eclipse Temurin",
            "major_version": "21",
            "version": "21.0.2",
            "url": "https://download.invalid/jdk.zip",
            "urls": ["https://download.invalid/jdk.zip"],
            "source": "Test Zip",
        }
        previous_cache = self.core.APP_CONFIG.get("download_cache_enabled")
        previous_verify = self.core.APP_CONFIG.get("verify_download_sha256")
        original_latest = self.core.JavaDownloadEngine.get_latest_download_info
        original_download = self.core.NetworkEngine.download_from_candidates
        original_sync = self.core.JavaRegistryAdapter.sync_runtime_registration
        original_is_win = self.core.IS_WIN
        original_platform = self.core.sys.platform
        original_chmod = self.core.os.chmod
        chmod_calls = []

        def fake_download(urls, dest, *_args, **_kwargs):
            with zipfile.ZipFile(dest, "w") as archive:
                archive.writestr("jdk-21/release", 'JAVA_VERSION="21.0.2"\nIMPLEMENTOR="Eclipse Temurin"\n')
                archive.writestr("jdk-21/bin/java", "")
                archive.writestr("jdk-21/lib/server/libjvm.so", "")
            return urls[0]

        def record_chmod(path, mode, *_args, **_kwargs):
            chmod_calls.append((Path(path), mode))

        try:
            self.core.APP_CONFIG["download_cache_enabled"] = False
            self.core.APP_CONFIG["verify_download_sha256"] = False
            self.core.IS_WIN = False
            self.core.sys.platform = "linux"
            self.core.os.chmod = record_chmod
            self.core.JavaDownloadEngine.get_latest_download_info = staticmethod(lambda vendor, major, package_type="jdk": dict(info))
            self.core.NetworkEngine.download_from_candidates = staticmethod(fake_download)
            self.core.JavaRegistryAdapter.sync_runtime_registration = staticmethod(lambda java_home, preferred_name=None: ["Temurin_21"])

            with tempfile.TemporaryDirectory() as tmp:
                result = self.core.download_and_install_java("Eclipse Temurin", "21", tmp)
                installed_java = Path(result["java_home"]) / "bin" / "java"
                self.assertTrue(installed_java.exists())
                self.assertTrue(any(path == installed_java and mode & 0o111 for path, mode in chmod_calls))
        finally:
            self.core.APP_CONFIG["download_cache_enabled"] = previous_cache
            self.core.APP_CONFIG["verify_download_sha256"] = previous_verify
            self.core.IS_WIN = original_is_win
            self.core.sys.platform = original_platform
            self.core.os.chmod = original_chmod
            self.core.JavaDownloadEngine.get_latest_download_info = original_latest
            self.core.NetworkEngine.download_from_candidates = original_download
            self.core.JavaRegistryAdapter.sync_runtime_registration = original_sync

    def test_linux_packages_include_run_launcher_entries(self):
        root = Path(__file__).resolve().parents[1]
        gui_script = (root / "scripts" / "build_linux.sh").read_text(encoding="utf-8")
        nogui_script = (root / "scripts" / "build_nogui_linux.sh").read_text(encoding="utf-8")
        desktop_entry = (root / "assets" / "build" / "ljm-java-manager.desktop").read_text(encoding="utf-8")
        gui_workflow = (root / ".github" / "workflows" / "build-packages.yml").read_text(encoding="utf-8")
        nogui_workflow = (root / ".github" / "workflows" / "build-nogui-packages.yml").read_text(encoding="utf-8")

        self.assertIn("LJM-Java-Manager.run", gui_script)
        self.assertIn("LJM-Java-Manager-nogui.run", nogui_script)
        self.assertIn("LJM-Java-Manager.run", gui_workflow)
        self.assertIn("LJM-Java-Manager-nogui.run", nogui_workflow)
        self.assertIn("Exec=./LJM-Java-Manager.run", desktop_entry)

    def test_macos_nogui_packages_include_command_launcher(self):
        root = Path(__file__).resolve().parents[1]
        script = (root / "scripts" / "build_nogui_macos.sh").read_text(encoding="utf-8")
        standalone_script = (root / "nogui" / "build_macos.sh").read_text(encoding="utf-8")
        workflow = (root / ".github" / "workflows" / "build-nogui-packages.yml").read_text(encoding="utf-8")

        self.assertIn("LJM-Java-Manager-nogui.command", script)
        self.assertIn("LJM-Java-Manager-nogui.command", standalone_script)
        self.assertIn("LJM-Java-Manager-nogui.command", workflow)
        self.assertIn("LJM-Java-Manager-nogui-macos", workflow)

    def test_macos_gui_package_uses_app_bundle_launcher(self):
        root = Path(__file__).resolve().parents[1]
        script = (root / "scripts" / "build_macos.sh").read_text(encoding="utf-8")
        workflow = (root / ".github" / "workflows" / "build-packages.yml").read_text(encoding="utf-8")
        readme = (root / "README.md").read_text(encoding="utf-8")

        self.assertIn('--name "LJM-Java-Manager"', script)
        self.assertIn("--windowed", script)
        self.assertIn("LJM-Java-Manager.app/Contents/MacOS/LJM-Java-Manager", script)
        self.assertIn("dist/LJM-Java-Manager.app", workflow)
        self.assertIn("LJM-Java-Manager-macos.zip", workflow)
        self.assertIn("LJM-Java-Manager.app", readme)

    def test_scroll_units_support_mousewheel_touchpad_and_linux_buttons(self):
        self.assertEqual(self.core.scroll_units_from_wheel_event(delta=120), -1)
        self.assertEqual(self.core.scroll_units_from_wheel_event(delta=-240), 2)
        self.assertEqual(self.core.scroll_units_from_wheel_event(delta=30), -1)
        self.assertEqual(self.core.scroll_units_from_wheel_event(delta=-30), 1)
        self.assertEqual(self.core.scroll_units_from_wheel_event(num=4), -1)
        self.assertEqual(self.core.scroll_units_from_wheel_event(num=5), 1)

    def test_touch_drag_scroll_skips_interactive_controls(self):
        self.assertTrue(self.core.widget_class_allows_touch_scroll("Frame"))
        self.assertTrue(self.core.widget_class_allows_touch_scroll("Label"))
        self.assertTrue(self.core.widget_class_allows_touch_scroll("Canvas"))
        self.assertFalse(self.core.widget_class_allows_touch_scroll("Entry"))
        self.assertFalse(self.core.widget_class_allows_touch_scroll("Button"))
        self.assertFalse(self.core.widget_class_allows_touch_scroll("Treeview"))

    def test_single_instance_port_is_stable(self):
        port_a = self.core.single_instance_port(r"D:\ljm\src\LJM.pyw")
        port_b = self.core.single_instance_port(r"D:\ljm\src\LJM.pyw")
        port_c = self.core.single_instance_port(r"D:\other\src\LJM.pyw")

        self.assertEqual(port_a, port_b)
        self.assertNotEqual(port_a, port_c)
        self.assertGreaterEqual(port_a, 43000)
        self.assertLessEqual(port_a, 48999)

    def test_single_instance_guard_notifies_existing_instance(self):
        events = []
        guard = self.core.SingleInstanceGuard(0, on_show=lambda: events.append("show"))
        try:
            self.assertTrue(guard.acquire())
            self.assertFalse(self.core.SingleInstanceGuard(guard.port).acquire())
            self.assertTrue(self.core.notify_existing_instance(guard.port))

            deadline = time.time() + 2
            while time.time() < deadline and not events:
                time.sleep(0.05)

            self.assertEqual(events, ["show"])
        finally:
            guard.close()

    def test_validate_java_move_target_rejects_nested_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "jdk-17"
            nested = source / "moved"
            source.mkdir()

            with self.assertRaisesRegex(ValueError, "inside source"):
                self.core.validate_java_move_target(str(source), str(nested))

    def test_move_java_home_commits_stage_without_shutil_move(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "jdk-21"
            target = Path(tmp) / "moved" / "jdk-21"
            bin_dir = source / "bin"
            bin_dir.mkdir(parents=True)
            (bin_dir / ("java.exe" if self.core.IS_WIN else "java")).write_text("", encoding="utf-8")
            (source / "release").write_text('JAVA_VERSION="21.0.1"', encoding="utf-8")

            original_move = self.core.shutil.move
            original_find = self.core.JavaRegistryAdapter.find_version_names_by_home
            original_unregister = self.core.JavaRegistryAdapter.unregister
            original_sync = self.core.JavaRegistryAdapter.sync_runtime_registration
            calls = {"unregistered": []}

            def guarded_move(src, dst, *args, **kwargs):
                if Path(src).name.startswith(".ljm_move_stage_"):
                    raise PermissionError("stage directory should be committed without shutil.move")
                return original_move(src, dst, *args, **kwargs)

            try:
                self.core.shutil.move = guarded_move
                self.core.JavaRegistryAdapter.find_version_names_by_home = staticmethod(lambda _home: ["Temurin_21"])
                self.core.JavaRegistryAdapter.unregister = staticmethod(lambda name: calls["unregistered"].append(name))
                self.core.JavaRegistryAdapter.sync_runtime_registration = staticmethod(lambda home, preferred_name=None: [preferred_name or "Temurin_21"])

                result = self.core.move_java_home(str(source), str(target), preferred_name="Temurin_21")
            finally:
                self.core.shutil.move = original_move
                self.core.JavaRegistryAdapter.find_version_names_by_home = original_find
                self.core.JavaRegistryAdapter.unregister = original_unregister
                self.core.JavaRegistryAdapter.sync_runtime_registration = original_sync

            self.assertFalse(source.exists())
            self.assertTrue((target / "release").exists())
            self.assertEqual(result["java_home"], str(target))
            self.assertEqual(calls["unregistered"], ["Temurin_21"])

    def test_write_linux_java_environment_includes_shell_and_desktop_targets(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            java_home = Path(tmp) / "jdk-21"
            java_home.mkdir()

            written = self.core.write_unix_java_environment(
                str(java_home),
                platform_name="linux",
                home_dir=str(home),
                update_process_env=False,
            )

            expected = {
                str(home / ".profile"),
                str(home / ".xprofile"),
                str(home / ".config" / "environment.d" / "ljm-java.conf"),
            }
            self.assertTrue(expected.issubset(set(written)))
            profile_text = (home / ".profile").read_text(encoding="utf-8")
            desktop_env = (home / ".config" / "environment.d" / "ljm-java.conf").read_text(encoding="utf-8")
            self.assertIn("export JAVA_HOME=", profile_text)
            self.assertIn(f"JAVA_HOME={java_home}", desktop_env)
            self.assertIn(f"PATH={java_home}{os.sep}bin:${{PATH}}", desktop_env)

    def test_write_macos_java_environment_includes_launch_agent(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            java_home = Path(tmp) / "jdk-21"
            java_home.mkdir()

            written = self.core.write_unix_java_environment(
                str(java_home),
                platform_name="darwin",
                home_dir=str(home),
                update_process_env=False,
            )

            launch_agent = home / "Library" / "LaunchAgents" / "com.ljm.javamgr.java-environment.plist"
            self.assertIn(str(home / ".zprofile"), written)
            self.assertIn(str(launch_agent), written)
            launch_text = launch_agent.read_text(encoding="utf-8")
            self.assertIn(str(java_home), launch_text)
            self.assertIn("launchctl", launch_text)

    def test_validate_java_delete_target_requires_java_home_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "not look like a Java home"):
                self.core.validate_java_delete_target(tmp)

            java_home = Path(tmp) / "jdk-21"
            bin_dir = java_home / "bin"
            bin_dir.mkdir(parents=True)
            (bin_dir / ("java.exe" if self.core.IS_WIN else "java")).write_text("", encoding="utf-8")
            (java_home / "release").write_text('JAVA_VERSION="21.0.1"', encoding="utf-8")

            self.assertEqual(Path(self.core.validate_java_delete_target(str(java_home))).resolve(), java_home.resolve())

    def test_delete_java_home_uses_permission_retry_removal(self):
        with tempfile.TemporaryDirectory() as tmp:
            java_home = Path(tmp) / "jdk-21"
            bin_dir = java_home / "bin"
            bin_dir.mkdir(parents=True)
            (bin_dir / ("java.exe" if self.core.IS_WIN else "java")).write_text("", encoding="utf-8")
            (java_home / "release").write_text('JAVA_VERSION="21.0.1"', encoding="utf-8")

            original_rmtree = self.core.shutil.rmtree
            original_find = self.core.JavaRegistryAdapter.find_version_names_by_home
            original_unregister = self.core.JavaRegistryAdapter.unregister
            calls = {"retried": False, "unregistered": []}

            def guarded_rmtree(path, *args, **kwargs):
                if kwargs.get("onerror") is None:
                    raise PermissionError("delete should retry with writable permissions")
                calls["retried"] = True
                return original_rmtree(path, *args, **kwargs)

            try:
                self.core.shutil.rmtree = guarded_rmtree
                self.core.JavaRegistryAdapter.find_version_names_by_home = staticmethod(lambda _home: ["Temurin_21"])
                self.core.JavaRegistryAdapter.unregister = staticmethod(lambda name: calls["unregistered"].append(name))

                result = self.core.delete_java_home(str(java_home), delete_files=True, preferred_name="Temurin_21")
            finally:
                self.core.shutil.rmtree = original_rmtree
                self.core.JavaRegistryAdapter.find_version_names_by_home = original_find
                self.core.JavaRegistryAdapter.unregister = original_unregister

            self.assertTrue(calls["retried"])
            self.assertFalse(java_home.exists())
            self.assertTrue(result["deleted_files"])
            self.assertEqual(calls["unregistered"], ["Temurin_21"])

    def test_unregister_java_home_removes_equivalent_jdk_jre_and_bin_entries(self):
        self.assertEqual(self.core.java_home_equivalent_paths(""), [])
        with tempfile.TemporaryDirectory() as tmp:
            java_home = Path(tmp) / "jdk8"
            (java_home / "bin").mkdir(parents=True)
            (java_home / "jre" / "bin").mkdir(parents=True)
            java_exe = "java.exe" if self.core.IS_WIN else "java"
            javac_exe = "javac.exe" if self.core.IS_WIN else "javac"
            (java_home / "bin" / java_exe).write_text("", encoding="utf-8")
            (java_home / "bin" / javac_exe).write_text("", encoding="utf-8")
            (java_home / "jre" / "bin" / java_exe).write_text("", encoding="utf-8")
            (java_home / "release").write_text('JAVA_VERSION="1.8.0_402"', encoding="utf-8")
            other_home = Path(tmp) / "jdk17"
            other_home.mkdir()

            registry = {
                "Root": str(java_home),
                "NestedJre": str(java_home / "jre"),
                "BinPath": str(java_home / "bin"),
                "Other": str(other_home),
            }
            removed = []
            original_get_all = self.core.JavaRegistryAdapter.get_all
            original_unregister = self.core.JavaRegistryAdapter.unregister
            try:
                self.core.JavaRegistryAdapter.get_all = staticmethod(lambda: list(registry.items()))
                self.core.JavaRegistryAdapter.unregister = staticmethod(lambda name: removed.append(name))

                names = self.core.unregister_java_home(str(java_home), preferred_name="Root")
            finally:
                self.core.JavaRegistryAdapter.get_all = original_get_all
                self.core.JavaRegistryAdapter.unregister = original_unregister

            self.assertEqual(names, ["Root", "NestedJre", "BinPath"])
            self.assertEqual(removed, ["Root", "NestedJre", "BinPath"])

    def test_delete_java_home_removes_related_backups_to_stop_launcher_rescan(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "state"
            backup_root = state_dir / "backups"
            java_home = Path(tmp) / "jdk-21"
            (java_home / "bin").mkdir(parents=True)
            java_exe = "java.exe" if self.core.IS_WIN else "java"
            (java_home / "bin" / java_exe).write_text("", encoding="utf-8")
            (java_home / "release").write_text('JAVA_VERSION="21.0.1"', encoding="utf-8")
            related_backup = backup_root / "20260620_jdk-21"
            unrelated_backup = backup_root / "20260620_jdk-17"
            (related_backup / "java_home" / "bin").mkdir(parents=True)
            (unrelated_backup / "java_home").mkdir(parents=True)
            (related_backup / "manifest.json").write_text(
                '{"target_path": "' + str(java_home).replace("\\", "\\\\") + '"}',
                encoding="utf-8",
            )
            (unrelated_backup / "manifest.json").write_text(
                '{"target_path": "' + str(Path(tmp) / "jdk-17").replace("\\", "\\\\") + '"}',
                encoding="utf-8",
            )

            original_backup_root = self.core.backup_root_dir
            original_find = self.core.JavaRegistryAdapter.find_version_names_by_home
            original_unregister = self.core.JavaRegistryAdapter.unregister
            try:
                self.core.backup_root_dir = lambda: str(backup_root)
                self.core.JavaRegistryAdapter.find_version_names_by_home = staticmethod(lambda _home: ["Temurin_21"])
                self.core.JavaRegistryAdapter.unregister = staticmethod(lambda _name: None)

                result = self.core.delete_java_home(str(java_home), delete_files=True, preferred_name="Temurin_21")
            finally:
                self.core.backup_root_dir = original_backup_root
                self.core.JavaRegistryAdapter.find_version_names_by_home = original_find
                self.core.JavaRegistryAdapter.unregister = original_unregister

            self.assertTrue(result["deleted_files"])
            self.assertFalse(java_home.exists())
            self.assertFalse(related_backup.exists())
            self.assertTrue(unrelated_backup.exists())

    def test_backup_management_records_include_size_and_can_delete_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            backup_root = Path(tmp) / "backups"
            backup_dir = backup_root / "20260620_jdk-21"
            java_home = backup_dir / "java_home"
            java_home.mkdir(parents=True)
            (java_home / "release").write_text('JAVA_VERSION="21.0.1"', encoding="utf-8")
            (backup_dir / "manifest.json").write_text(
                json.dumps(
                    {
                        "created_at": 10,
                        "created_text": "2026-06-20 12:00:00",
                        "operation": "update",
                        "target_path": str(Path(tmp) / "jdk-21"),
                        "entries": ["release"],
                        "registry_names": ["Temurin_21"],
                    }
                ),
                encoding="utf-8",
            )
            original_backup_root = self.core.backup_root_dir
            try:
                self.core.backup_root_dir = lambda: str(backup_root)

                records = self.core.list_java_backup_records()
                deleted = self.core.delete_java_backup(str(backup_dir))
            finally:
                self.core.backup_root_dir = original_backup_root

            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["operation"], "update")
            self.assertEqual(records[0]["registry_names"], ["Temurin_21"])
            self.assertGreater(records[0]["size_bytes"], 0)
            self.assertTrue(deleted["deleted"])
            self.assertFalse(backup_dir.exists())

    def test_download_cache_management_stats_and_clear_contents(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp) / "downloads"
            nested = cache_dir / "nested"
            nested.mkdir(parents=True)
            (cache_dir / "jdk.zip").write_bytes(b"12345")
            (nested / "part.tmp").write_bytes(b"12")
            original_cache_dir = self.core.download_cache_dir
            original_engine_cache = dict(self.core.JavaDownloadEngine._cache)
            try:
                self.core.download_cache_dir = lambda: str(cache_dir)
                self.core.JavaDownloadEngine._cache["sample"] = {"time": 1, "data": {}}

                stats = self.core.download_cache_stats()
                result = self.core.clear_download_cache()
            finally:
                self.core.download_cache_dir = original_cache_dir
                self.core.JavaDownloadEngine._cache.clear()
                self.core.JavaDownloadEngine._cache.update(original_engine_cache)

            self.assertEqual(stats["file_count"], 2)
            self.assertEqual(stats["size_bytes"], 7)
            self.assertEqual(result["file_count"], 2)
            self.assertEqual(result["size_bytes"], 7)
            self.assertTrue(cache_dir.exists())
            self.assertEqual(list(cache_dir.iterdir()), [])
            self.assertNotIn("sample", self.core.JavaDownloadEngine._cache)

    def test_registry_cleanup_prunes_missing_and_ljm_backup_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            backup_root = Path(tmp) / "backups"
            backup_java = backup_root / "20260620_jdk" / "java_home"
            backup_java.mkdir(parents=True)
            live_java = Path(tmp) / "jdk-21"
            live_java.mkdir()
            registry = {
                "Empty": "",
                "Missing": str(Path(tmp) / "missing-jdk"),
                "Backup": str(backup_java),
                "Live": str(live_java),
            }
            removed = []
            original_get_all = self.core.JavaRegistryAdapter.get_all
            original_unregister = self.core.JavaRegistryAdapter.unregister
            original_backup_root = self.core.backup_root_dir
            try:
                self.core.JavaRegistryAdapter.get_all = staticmethod(lambda: list(registry.items()))
                self.core.JavaRegistryAdapter.unregister = staticmethod(lambda name: removed.append(name))
                self.core.backup_root_dir = lambda: str(backup_root)

                removed_names = self.core.cleanup_stale_java_registrations()
            finally:
                self.core.JavaRegistryAdapter.get_all = original_get_all
                self.core.JavaRegistryAdapter.unregister = original_unregister
                self.core.backup_root_dir = original_backup_root

            self.assertEqual(removed_names, ["Empty", "Missing", "Backup"])
            self.assertEqual(removed, ["Empty", "Missing", "Backup"])

    def test_windows_tray_left_click_does_not_restore_window(self):
        events = []

        class Root:
            def after(self, delay, callback):
                events.append(("after", delay))
                callback()

        tray = self.core.WindowsTrayIcon(Root(), "tooltip", "", lambda: events.append("show"), lambda: None)

        result = tray._wndproc(None, tray.WM_TRAYICON, None, tray.WM_LBUTTONUP)

        self.assertEqual(result, 0)
        self.assertNotIn("show", events)
        self.assertNotIn(("after", 0), events)

    def test_windows_tray_double_click_shows_window(self):
        events = []

        class Root:
            def after(self, delay, callback):
                events.append(("after", delay))
                callback()

        tray = self.core.WindowsTrayIcon(Root(), "tooltip", "", lambda: events.append("show"), lambda: None)

        result = tray._wndproc(None, tray.WM_TRAYICON, None, tray.WM_LBUTTONDBLCLK)

        self.assertEqual(result, 0)
        self.assertIn("show", events)

    def test_windows_tray_double_click_callback_is_guarded(self):
        events = []

        class Root:
            def after(self, delay, callback):
                events.append(("after", delay))
                callback()

        def broken_show():
            events.append("show")
            raise RuntimeError("restore failed")

        tray = self.core.WindowsTrayIcon(Root(), "tooltip", "", broken_show, lambda: None)

        result = tray._wndproc(None, tray.WM_TRAYICON, None, tray.WM_LBUTTONDBLCLK)

        self.assertEqual(result, 0)
        self.assertIn("show", events)

    def test_pystray_menu_does_not_make_show_item_left_click_default(self):
        source = Path("src/LJM.pyw").read_text(encoding="utf-8")
        match = re.search(r"class PystrayTrayIcon:\n(?P<body>.*?)(?=\n\nclass JavaRegistryAdapter:)", source, re.S)

        self.assertIsNotNone(match)
        self.assertNotIn("default=True", match.group("body"))

    def test_windows_tray_uses_dedicated_message_window(self):
        source = Path("src/LJM.pyw").read_text(encoding="utf-8")
        match = re.search(r"class WindowsTrayIcon:\n(?P<body>.*?)(?=\n\nclass PystrayTrayIcon:)", source, re.S)

        self.assertIsNotNone(match)
        body = match.group("body")
        self.assertIn("def _create_message_window", body)
        self.assertIn("CreateWindowExW", body)
        self.assertNotIn("SetWindowLongPtrW", body)

    def test_show_from_tray_restores_visible_window_without_zero_alpha(self):
        events = []
        app = object.__new__(self.core.JavaManagerApp)

        class Tray:
            def show(self):
                events.append("tray-show")

        class Root:
            def winfo_exists(self):
                return True

            def deiconify(self):
                events.append("deiconify")

            def state(self, value):
                events.append(("state", value))

            def lift(self):
                events.append("lift")

            def focus_force(self):
                events.append("focus")

            def update_idletasks(self):
                events.append("update")

        app.root = Root()
        app.tray_icon = Tray()
        app._cancel_window_fade = lambda window: events.append("cancel-fade")
        app._set_window_alpha = lambda window, alpha: events.append(("alpha", alpha)) or True
        app._force_show_root_window = lambda: events.append("force-show")
        app._fade_in_window = lambda *args, **kwargs: events.append("fade-in")

        self.core.JavaManagerApp.show_from_tray(app)

        self.assertIn("deiconify", events)
        self.assertIn(("state", "normal"), events)
        self.assertIn("force-show", events)
        self.assertNotIn(("alpha", 0.0), events)
        self.assertNotIn("fade-in", events)

    def test_tab_change_uses_tab_animation_without_root_alpha_fade(self):
        source = Path("src/LJM.pyw").read_text(encoding="utf-8")
        match = re.search(r"    def on_tab_changed\(self, event\):\n(?P<body>(?:        .*\n)+)", source)

        self.assertIsNotNone(match)
        self.assertIn("_animate_selected_tab_motion_header()", match.group("body"))
        self.assertNotIn("_fade_in_window(self.root", match.group("body"))

    def test_window_fade_cancels_previous_pending_job(self):
        app = object.__new__(self.core.JavaManagerApp)
        app._window_fade_jobs = {}
        alpha_values = []

        def set_alpha(_window, alpha):
            alpha_values.append(alpha)
            return True

        app._set_window_alpha = set_alpha

        class Window:
            def __init__(self):
                self.cancelled = []
                self.jobs = []

            def winfo_exists(self):
                return True

            def after(self, _delay, callback):
                job = f"job-{len(self.jobs) + 1}"
                self.jobs.append((job, callback))
                return job

            def after_cancel(self, job):
                self.cancelled.append(job)

        window = Window()

        app._fade_in_window(window, duration=100, steps=2, start_alpha=0.0)
        first_job = window.jobs[-1][0]
        app._fade_out_window(window, duration=100, steps=2)

        self.assertIn(first_job, window.cancelled)
        self.assertEqual(app._window_fade_jobs[str(window)], window.jobs[-1][0])

    def test_ensure_java_home_executables_repairs_unix_launchers(self):
        with tempfile.TemporaryDirectory() as tmp:
            java_home = Path(tmp) / "jdk-21"
            bin_dir = java_home / "bin"
            lib_dir = java_home / "lib"
            bin_dir.mkdir(parents=True)
            lib_dir.mkdir()
            java_bin = bin_dir / "java"
            javac_bin = bin_dir / "javac"
            helper = lib_dir / "jspawnhelper"
            for path in (java_bin, javac_bin, helper):
                path.write_text("", encoding="utf-8")

            original_chmod = self.core.os.chmod
            chmod_calls = []

            def record_chmod(path, mode):
                chmod_calls.append((Path(path).name, mode))

            try:
                self.core.os.chmod = record_chmod
                changed = self.core.ensure_java_home_executables(str(java_home), platform_name="linux")
            finally:
                self.core.os.chmod = original_chmod

            self.assertEqual({Path(path).name for path in changed}, {"java", "javac", "jspawnhelper"})
            self.assertEqual({name for name, _mode in chmod_calls}, {"java", "javac", "jspawnhelper"})
            self.assertTrue(all(mode & 0o111 for _name, mode in chmod_calls))

    def test_backup_tab_and_settings_cache_management_ui_are_wired(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "src" / "LJM.pyw").read_text(encoding="utf-8")

        self.assertIn('"tab_backup"', source)
        self.assertIn("def setup_backup_tab", source)
        self.assertIn("def refresh_backup_tab", source)
        self.assertIn("def restore_selected_backup", source)
        self.assertIn("def delete_selected_backup", source)
        self.assertIn("def clear_download_cache_from_settings", source)
        self.assertIn("download_cache_status", source)
        self.assertIn("_create_tab_motion_header(self.tab_backup", source)

    def test_jvm_args_tab_ui_is_wired(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "src" / "LJM.pyw").read_text(encoding="utf-8")

        self.assertIn('"tab_jvm_args"', source)
        self.assertIn("def setup_jvm_args_tab", source)
        self.assertIn("def refresh_jvm_args_preview", source)
        self.assertIn("def copy_jvm_args", source)
        self.assertIn("MINECRAFT_VERSION_PRESETS", source)
        self.assertIn("jvm_mc_version_box", source)
        self.assertIn('self.jvm_mc_version_box.bind("<<ComboboxSelected>>"', source)
        self.assertIn("jvm_head_label_var", source)
        self.assertIn("jvm_combined_label_var", source)
        self.assertIn("def apply_jvm_output_mode", source)
        self.assertIn("grid_remove", source)
        self.assertNotIn("tr(\"jvm_generate\")", source)
        self.assertNotIn("请先生成", source)
        self.assertNotIn("Generate them first", source)
        self.assertIn("MINECRAFT_DEVICE_MEMORY_PRESETS", source)
        self.assertIn("MINECRAFT_DEVICE_OS_PRESETS", source)
        self.assertIn("MINECRAFT_DEVICE_VRAM_PRESETS", source)
        self.assertIn("jvm_os_var", source)
        self.assertIn("jvm_vram_var", source)
        self.assertIn('vram_values = ("自动",)', source)
        self.assertIn('vram_values = ("Auto",)', source)
        self.assertNotIn('vram_values = ("未指定",)', source)
        self.assertNotIn('vram_values = ("Unknown",)', source)
        self.assertIn('ttk.Combobox(main, textvariable=self.jvm_memory_var, values=memory_values, width=18)', source)
        self.assertIn('ttk.Combobox(main, textvariable=self.jvm_vram_var, values=vram_values, width=18)', source)
        self.assertNotIn('textvariable=self.jvm_memory_var, values=memory_values, state="readonly"', source)
        self.assertNotIn('textvariable=self.jvm_vram_var, values=vram_values, state="readonly"', source)
        self.assertIn("detect_system_vram_mb", source)
        self.assertNotIn("detect_primary_gpu_info", source)
        self.assertNotIn("_detect_windows_gpu_info", source)
        self.assertNotIn("gpu_name", source)
        self.assertNotIn("Chipset Model", source)
        self.assertIn("width=18", source)
        self.assertIn('copy_button.grid(row=row * 2, column=1, sticky="w"', source)
        self.assertIn("_create_tab_motion_header(self.tab_jvm_args", source)
        self.assertIn("self.notebook.add(self.tab_jvm_args", source)
        self.assertIn("show_tab(self.tab_jvm_args", source)

    def test_minecraft_version_presets_include_common_user_shortcuts(self):
        for version in ("1.12.2", "1.16.5", "1.20.1", "1.21.11", "26.2"):
            self.assertIn(version, self.core.MINECRAFT_VERSION_PRESETS)
        self.assertNotIn("26", self.core.MINECRAFT_VERSION_PRESETS)
        self.assertNotIn("2", self.core.MINECRAFT_VERSION_PRESETS)

class NoguiFeatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nogui = load_nogui()

    def test_nogui_parser_has_download_move_delete_and_feedback_commands(self):
        parser = self.nogui.build_parser()

        download_args = parser.parse_args(["download", "Eclipse Temurin", "21", r"D:\Java"])
        move_args = parser.parse_args(["move", "Temurin_21", r"D:\Java\Temurin_21"])
        delete_args = parser.parse_args(["delete", "Temurin_21", "--files", "--force"])
        vendors_args = parser.parse_args(["vendors"])
        feedback_args = parser.parse_args(["feedback", "--message", "OpenJ9 source is slow"])

        self.assertEqual(download_args.command, "download")
        self.assertIs(download_args.func, self.nogui.command_download)
        self.assertEqual(move_args.command, "move")
        self.assertIs(move_args.func, self.nogui.command_move)
        self.assertEqual(delete_args.command, "delete")
        self.assertIs(delete_args.func, self.nogui.command_delete)
        self.assertTrue(delete_args.files)
        self.assertTrue(delete_args.force)
        self.assertEqual(vendors_args.command, "vendors")
        self.assertIs(vendors_args.func, self.nogui.command_vendors)
        self.assertEqual(feedback_args.command, "feedback")
        self.assertIs(feedback_args.func, self.nogui.command_feedback)

    def test_nogui_feedback_exports_github_issue_url(self):
        parser = self.nogui.build_parser()
        args = parser.parse_args(["feedback", "--message", "Java update list is blocked"])

        payload = self.nogui.command_feedback(args)

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["action"], "feedback")
        self.assertIn("https://github.com/Lambunge520/Java-/issues/new", payload["url"])
        self.assertIn("3.0", payload["body"])
        self.assertIn("Java update list is blocked", payload["body"])

    def test_nogui_defaults_use_nogui_name(self):
        self.assertEqual(Path(self.nogui.DEFAULT_RESULT_FILE).name, "ljm_nogui_result.json")
        self.assertEqual(Path(self.nogui.DEFAULT_LOG_FILE).name, "ljm_nogui.log")
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "result.json"
            payload = self.nogui.write_result({"ok": True}, output_path=str(output))

        self.assertEqual(payload["tool"], "LJM Java Manager NoGUI")

    def test_nogui_registry_rows_prunes_stale_entries_before_listing(self):
        calls = []
        original_cleanup = self.nogui.core.cleanup_stale_java_registrations
        original_get_all = self.nogui.core.JavaRegistryAdapter.get_all
        original_runtime = self.nogui.core.read_java_runtime_info
        original_health = self.nogui.core.get_java_health_report
        original_update_home = self.nogui.core.runtime_update_java_home
        original_version_text = self.nogui.core.version_display_text
        try:
            self.nogui.core.cleanup_stale_java_registrations = lambda: calls.append("cleanup")
            self.nogui.core.JavaRegistryAdapter.get_all = staticmethod(lambda: [("Temurin_21", r"C:\Java\jdk21")])
            self.nogui.core.read_java_runtime_info = lambda _path: {
                "vendor": "Eclipse Temurin",
                "major": "21",
                "package_type": "jdk",
                "nested_jre_home": "",
                "version": "21.0.2",
            }
            self.nogui.core.get_java_health_report = lambda _path: {
                "status": "OK",
                "healthy": True,
                "usable": True,
            }
            self.nogui.core.runtime_update_java_home = lambda _runtime: r"C:\Java\jdk21"
            self.nogui.core.version_display_text = lambda version: version

            rows = self.nogui.registry_rows()
        finally:
            self.nogui.core.cleanup_stale_java_registrations = original_cleanup
            self.nogui.core.JavaRegistryAdapter.get_all = original_get_all
            self.nogui.core.read_java_runtime_info = original_runtime
            self.nogui.core.get_java_health_report = original_health
            self.nogui.core.runtime_update_java_home = original_update_home
            self.nogui.core.version_display_text = original_version_text

        self.assertEqual(calls, ["cleanup"])
        self.assertEqual(rows[0]["registry_name"], "Temurin_21")

    def test_nogui_vendors_export_platform_guidance(self):
        payload = self.nogui.command_vendors(None)
        vendors = {item["vendor"]: item for item in payload["items"]}

        self.assertGreaterEqual(len(vendors), 21)
        self.assertIn("Oracle JDK", vendors)
        self.assertIn("Red Hat OpenJDK", vendors)
        self.assertTrue(vendors["Oracle JDK"]["platforms"])
        self.assertTrue(vendors["Eclipse Temurin"]["minecraft_performance"])
        self.assertTrue(vendors["Red Hat OpenJDK"]["platforms"])


if __name__ == "__main__":
    unittest.main()
