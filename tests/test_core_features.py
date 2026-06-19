import importlib.machinery
import importlib.util
import os
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

    def test_version_and_user_agent_are_293(self):
        self.assertEqual(self.core.VERSION, "2.9.3")
        self.assertEqual(self.core.default_headers()["User-Agent"], "JavaManager/2.9.3")

    def test_github_feedback_url_prefills_issue_context(self):
        url = self.core.build_github_feedback_url("下载 OpenJ9 时速度很慢")
        parsed = urlparse(url)
        query = parse_qs(parsed.query)

        self.assertEqual(f"{parsed.scheme}://{parsed.netloc}{parsed.path}", "https://github.com/Lambunge520/Java-/issues/new")
        self.assertEqual(query["template"][0], "bug_report.md")
        self.assertIn("2.9.3", query["body"][0])
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
        idle = self.core.tray_tooltip_text("2.9.3", active_tasks=0, background_running=False, language="zh_CN")
        busy = self.core.tray_tooltip_text("2.9.3", active_tasks=2, background_running=False, language="zh_CN")
        background = self.core.tray_tooltip_text("2.9.3", active_tasks=0, background_running=True, language="zh_CN")
        english = self.core.tray_tooltip_text("2.9.3", active_tasks=1, background_running=False, language="en_US")

        self.assertIn("工作状态", idle)
        self.assertIn("空闲", idle)
        self.assertIn("正在执行 2 个任务", busy)
        self.assertIn("后台检查", background)
        self.assertIn("Work status", english)
        self.assertIn("running 1 task", english)
        self.assertLessEqual(len(idle), 127)

    def test_release_notes_and_workflows_are_bilingual(self):
        root = Path(__file__).resolve().parents[1]
        notes = (root / "docs" / "releases" / "RELEASE_NOTES_2.9.3.md").read_text(encoding="utf-8")
        template = (root / "docs" / "releases" / "RELEASE_NOTES_TEMPLATE_BILINGUAL.md").read_text(encoding="utf-8")
        gui_workflow = (root / ".github" / "workflows" / "build-packages.yml").read_text(encoding="utf-8")
        nogui_workflow = (root / ".github" / "workflows" / "build-nogui-packages.yml").read_text(encoding="utf-8")

        self.assertIn("## 中文", notes)
        self.assertIn("## English", notes)
        self.assertIn("国内网络", notes)
        self.assertIn("China network", notes)
        self.assertIn("## 中文", template)
        self.assertIn("## English", template)
        for workflow in (gui_workflow, nogui_workflow):
            self.assertIn("RELEASE_NOTES_FILE", workflow)
            self.assertIn('RELEASE_VERSION="${RELEASE_TAG#v}"', workflow)
            self.assertIn("RELEASE_NOTES_TEMPLATE_BILINGUAL.md", workflow)
            self.assertIn('--notes-file "$RELEASE_NOTES_FILE"', workflow)

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
        self.assertIn("2.9.3", payload["body"])
        self.assertIn("Java update list is blocked", payload["body"])

    def test_nogui_defaults_use_nogui_name(self):
        self.assertEqual(Path(self.nogui.DEFAULT_RESULT_FILE).name, "ljm_nogui_result.json")
        self.assertEqual(Path(self.nogui.DEFAULT_LOG_FILE).name, "ljm_nogui.log")
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "result.json"
            payload = self.nogui.write_result({"ok": True}, output_path=str(output))

        self.assertEqual(payload["tool"], "LJM Java Manager NoGUI")

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
