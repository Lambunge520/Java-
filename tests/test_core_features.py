import importlib.machinery
import importlib.util
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


def load_headless():
    root = Path(__file__).resolve().parents[1]
    headless_path = root / "src" / "LJM_headless.pyw"
    loader = importlib.machinery.SourceFileLoader("ljm_headless_test", str(headless_path))
    spec = importlib.util.spec_from_file_location("ljm_headless_test", str(headless_path), loader=loader)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CoreFeatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = load_core()

    def test_version_and_user_agent_are_28(self):
        self.assertEqual(self.core.VERSION, "2.8 Stable")
        self.assertEqual(self.core.default_headers()["User-Agent"], "JavaManager/2.8")

    def test_github_feedback_url_prefills_issue_context(self):
        url = self.core.build_github_feedback_url("下载 OpenJ9 时速度很慢")
        parsed = urlparse(url)
        query = parse_qs(parsed.query)

        self.assertEqual(f"{parsed.scheme}://{parsed.netloc}{parsed.path}", "https://github.com/Lambunge520/Java-/issues/new")
        self.assertEqual(query["template"][0], "bug_report.md")
        self.assertIn("2.8 Stable", query["body"][0])
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

    def test_microsoft_github_mirror_uses_profile_release_source(self):
        calls = []
        original = self.core.JavaDownloadEngine._fetch_github_profile_releases

        def fake_profile(vendor, major_version, direct_first=False, mirrors_only=False):
            calls.append((vendor, major_version, direct_first, mirrors_only))
            return {"version": "21.0.1", "url": "https://example.invalid/jdk.zip"}

        try:
            self.core.JavaDownloadEngine._fetch_github_profile_releases = staticmethod(fake_profile)
            result = self.core.JavaDownloadEngine._fetch_github_mirror("Microsoft Build of OpenJDK", "21")
        finally:
            self.core.JavaDownloadEngine._fetch_github_profile_releases = original

        self.assertEqual(result["version"], "21.0.1")
        self.assertEqual(calls, [("Microsoft Build of OpenJDK", "21", False, True)])
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

    def test_minecraft_java_guidance_matches_major_versions(self):
        guidance_21 = self.core.minecraft_java_guidance("21", language="en_US")
        guidance_17 = self.core.minecraft_java_guidance("17", language="en_US")
        guidance_8 = self.core.minecraft_java_guidance("8", language="en_US")

        self.assertIn("1.20.5", guidance_21)
        self.assertIn("1.18", guidance_17)
        self.assertIn("1.16.5", guidance_8)

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
            self.core.JavaDownloadEngine.get_latest_download_info = staticmethod(lambda vendor, major: dict(primary))
            self.core.JavaDownloadEngine.get_download_info_candidates = staticmethod(lambda vendor, major: [dict(primary), dict(fallback)])
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


class HeadlessFeatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.headless = load_headless()

    def test_headless_parser_has_download_move_delete_and_feedback_commands(self):
        parser = self.headless.build_parser()

        download_args = parser.parse_args(["download", "Eclipse Temurin", "21", r"D:\Java"])
        move_args = parser.parse_args(["move", "Temurin_21", r"D:\Java\Temurin_21"])
        delete_args = parser.parse_args(["delete", "Temurin_21", "--files", "--force"])
        vendors_args = parser.parse_args(["vendors"])
        feedback_args = parser.parse_args(["feedback", "--message", "OpenJ9 source is slow"])

        self.assertEqual(download_args.command, "download")
        self.assertIs(download_args.func, self.headless.command_download)
        self.assertEqual(move_args.command, "move")
        self.assertIs(move_args.func, self.headless.command_move)
        self.assertEqual(delete_args.command, "delete")
        self.assertIs(delete_args.func, self.headless.command_delete)
        self.assertTrue(delete_args.files)
        self.assertTrue(delete_args.force)
        self.assertEqual(vendors_args.command, "vendors")
        self.assertIs(vendors_args.func, self.headless.command_vendors)
        self.assertEqual(feedback_args.command, "feedback")
        self.assertIs(feedback_args.func, self.headless.command_feedback)

    def test_headless_feedback_exports_github_issue_url(self):
        parser = self.headless.build_parser()
        args = parser.parse_args(["feedback", "--message", "Java update list is blocked"])

        payload = self.headless.command_feedback(args)

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["action"], "feedback")
        self.assertIn("https://github.com/Lambunge520/Java-/issues/new", payload["url"])
        self.assertIn("2.8 Stable", payload["body"])
        self.assertIn("Java update list is blocked", payload["body"])

    def test_headless_vendors_export_platform_guidance(self):
        payload = self.headless.command_vendors(None)
        vendors = {item["vendor"]: item for item in payload["items"]}

        self.assertGreaterEqual(len(vendors), 21)
        self.assertIn("Oracle JDK", vendors)
        self.assertIn("Red Hat OpenJDK", vendors)
        self.assertTrue(vendors["Oracle JDK"]["platforms"])
        self.assertTrue(vendors["Red Hat OpenJDK"]["platforms"])


if __name__ == "__main__":
    unittest.main()
