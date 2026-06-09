import importlib.machinery
import importlib.util
import tempfile
import time
import unittest
from pathlib import Path


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
            "GraalVM": "graalvm",
            "Azul Zulu": "zulu",
            "Amazon Corretto": "corretto",
            "BellSoft Liberica": "liberica",
            "SAP SapMachine": "sap_machine",
            "JetBrains Runtime": "jetbrains",
        }

        for vendor, distribution in expected.items():
            with self.subTest(vendor=vendor):
                self.assertIn(vendor, self.core.JAVA_VENDOR_OPTIONS)
                profile = self.core.java_vendor_profile(vendor)
                self.assertEqual(profile["foojay"], distribution)
                self.assertTrue(profile["scenario"])
                self.assertTrue(profile["pros"])
                self.assertTrue(profile["cons"])

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


class HeadlessFeatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.headless = load_headless()

    def test_headless_parser_has_download_and_move_commands(self):
        parser = self.headless.build_parser()

        download_args = parser.parse_args(["download", "Eclipse Temurin", "21", r"D:\Java"])
        move_args = parser.parse_args(["move", "Temurin_21", r"D:\Java\Temurin_21"])
        vendors_args = parser.parse_args(["vendors"])

        self.assertEqual(download_args.command, "download")
        self.assertIs(download_args.func, self.headless.command_download)
        self.assertEqual(move_args.command, "move")
        self.assertIs(move_args.func, self.headless.command_move)
        self.assertEqual(vendors_args.command, "vendors")
        self.assertIs(vendors_args.func, self.headless.command_vendors)


if __name__ == "__main__":
    unittest.main()
