import importlib.machinery
import importlib.util
import inspect
import io
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

    def test_version_and_user_agent_are_314(self):
        self.assertEqual(self.core.VERSION, "3.1.4")
        self.assertEqual(self.core.default_headers()["User-Agent"], "JavaManager/3.1.4")

    def test_logging_setup_keeps_python38_compatibility(self):
        source = inspect.getsource(self.core)
        self.assertIn("logging.basicConfig(**_LOGGING_CONFIG, encoding=\"utf-8\")", source)
        self.assertIn("except (TypeError, ValueError):", source)
        self.assertIn("logging.basicConfig(**_LOGGING_CONFIG)", source)

    def test_github_feedback_url_prefills_issue_context(self):
        url = self.core.build_github_feedback_url("下载 OpenJ9 时速度很慢")
        parsed = urlparse(url)
        query = parse_qs(parsed.query)

        self.assertEqual(f"{parsed.scheme}://{parsed.netloc}{parsed.path}", "https://github.com/Lambunge520/Java-/issues/new")
        self.assertEqual(query["template"][0], "bug_report.md")
        self.assertIn("3.1.4", query["body"][0])
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

    def test_parallel_download_uses_range_segments_and_merges_file(self):
        url = "https://fast-mirror.invalid/jdk.zip"
        payload = b"0123456789abcdef"
        ranges = []
        original_detect = self.core.NetworkEngine.detect_environment
        original_open = self.core.NetworkEngine.open_request_with_mode
        original_min = self.core.PARALLEL_DOWNLOAD_MIN_BYTES
        original_segment_min = self.core.PARALLEL_DOWNLOAD_SEGMENT_MIN_BYTES
        original_workers = self.core.PARALLEL_DOWNLOAD_MAX_WORKERS

        class FakeResponse:
            def __init__(self, status, data, headers):
                self.status = status
                self._data = data
                self._offset = 0
                self.headers = headers

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def getcode(self):
                return self.status

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
            range_header = request_obj.get_header("Range")
            ranges.append(range_header or "")
            if not range_header:
                return FakeResponse(200, payload, {"Content-Length": str(len(payload)), "Accept-Ranges": "bytes"})
            match = re.match(r"bytes=(\d+)-(\d+)", range_header)
            self.assertIsNotNone(match)
            start, end = int(match.group(1)), int(match.group(2))
            return FakeResponse(206, payload[start:end + 1], {"Content-Length": str(end - start + 1)})

        try:
            self.core.PARALLEL_DOWNLOAD_MIN_BYTES = 8
            self.core.PARALLEL_DOWNLOAD_SEGMENT_MIN_BYTES = 4
            self.core.PARALLEL_DOWNLOAD_MAX_WORKERS = 3
            self.core.NetworkEngine.detect_environment = staticmethod(fake_detect_environment)
            self.core.NetworkEngine.open_request_with_mode = staticmethod(fake_open_request)
            with tempfile.TemporaryDirectory() as tmp:
                dest = os.path.join(tmp, "jdk.zip")
                result = self.core.NetworkEngine.download_from_candidates(
                    [url],
                    dest,
                    lambda *_args: None,
                    lambda *_args: None,
                )
                data = Path(dest).read_bytes()
        finally:
            self.core.PARALLEL_DOWNLOAD_MIN_BYTES = original_min
            self.core.PARALLEL_DOWNLOAD_SEGMENT_MIN_BYTES = original_segment_min
            self.core.PARALLEL_DOWNLOAD_MAX_WORKERS = original_workers
            self.core.NetworkEngine.detect_environment = original_detect
            self.core.NetworkEngine.open_request_with_mode = original_open

        self.assertEqual(result, url)
        self.assertEqual(data, payload)
        self.assertIn("", ranges)
        self.assertTrue(any(item.startswith("bytes=") for item in ranges))

    def test_download_retries_with_resume_after_network_change(self):
        url = "https://network-change.invalid/jdk.zip"
        payload = b"resume-ok"
        calls = []
        original_detect = self.core.NetworkEngine.detect_environment
        original_open = self.core.NetworkEngine.open_request_with_mode

        class FlakyResponse:
            status = 200

            def __init__(self):
                self._calls = 0
                self.headers = {"Content-Length": str(len(payload))}

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def getcode(self):
                return self.status

            def read(self, _size=-1):
                self._calls += 1
                if self._calls == 1:
                    return payload[:4]
                raise OSError("network changed")

        class ResumeResponse:
            status = 206

            def __init__(self, start):
                self._data = payload[start:]
                self._offset = 0
                self.headers = {"Content-Length": str(len(self._data))}

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def getcode(self):
                return self.status

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
            range_header = request_obj.get_header("Range")
            calls.append(range_header or "")
            if not range_header:
                return FlakyResponse()
            match = re.match(r"bytes=(\d+)-", range_header)
            self.assertIsNotNone(match)
            return ResumeResponse(int(match.group(1)))

        try:
            self.core.NetworkEngine.detect_environment = staticmethod(fake_detect_environment)
            self.core.NetworkEngine.open_request_with_mode = staticmethod(fake_open_request)
            with tempfile.TemporaryDirectory() as tmp:
                dest = os.path.join(tmp, "jdk.zip")
                result = self.core.NetworkEngine.download_from_candidates(
                    [url],
                    dest,
                    lambda *_args: None,
                    lambda *_args: None,
                )
                data = Path(dest).read_bytes()
        finally:
            self.core.NetworkEngine.detect_environment = original_detect
            self.core.NetworkEngine.open_request_with_mode = original_open

        self.assertEqual(result, url)
        self.assertEqual(data, payload)
        self.assertEqual(calls[0], "")
        self.assertIn("bytes=4-", calls)

    def test_download_from_candidates_allows_missing_callbacks(self):
        url = "https://callback-optional.invalid/jdk.zip"
        payload = b"ok"
        original_detect = self.core.NetworkEngine.detect_environment
        original_open = self.core.NetworkEngine.open_request_with_mode

        class FakeResponse:
            status = 200
            headers = {"Content-Length": str(len(payload))}

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def getcode(self):
                return 200

            def read(self, _size=-1):
                data = getattr(self, "_data", payload)
                self._data = b""
                return data

        try:
            self.core.NetworkEngine.detect_environment = staticmethod(
                lambda *_args, **_kwargs: {"effective_direct": True, "system_proxies": {}, "windows_proxy": {}}
            )
            self.core.NetworkEngine.open_request_with_mode = staticmethod(lambda *_args, **_kwargs: FakeResponse())
            with tempfile.TemporaryDirectory() as tmp:
                dest = os.path.join(tmp, "jdk.zip")
                result = self.core.NetworkEngine.download_from_candidates([url], dest, None, None)
                data = Path(dest).read_bytes()
        finally:
            self.core.NetworkEngine.detect_environment = original_detect
            self.core.NetworkEngine.open_request_with_mode = original_open

        self.assertEqual(result, url)
        self.assertEqual(data, payload)

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

    def test_corretto_official_source_uses_permanent_latest_url(self):
        original_redirect = self.core.NetworkEngine.resolve_redirect_location
        try:
            self.core.NetworkEngine.resolve_redirect_location = staticmethod(
                lambda _urls, timeout=6: "https://corretto.aws/downloads/resources/21.0.11.10.1/amazon-corretto-21.0.11.10.1-windows-x64-jdk.zip"
            )
            result = self.core.JavaDownloadEngine._fetch_corretto("21", package_type="jdk")
        finally:
            self.core.NetworkEngine.resolve_redirect_location = original_redirect

        self.assertEqual(result["source"], "Amazon Corretto permanent URL")
        self.assertEqual(result["vendor"], "Amazon Corretto")
        self.assertIn("amazon-corretto-21-x64-windows-jdk.zip", result["url"])
        self.assertIn("21.0.11", result["version"])
        self.assertGreaterEqual(len(result["urls"]), 2)

    def test_download_candidates_expand_foojay_distribution_fallbacks(self):
        calls = []
        original_chain = self.core.JavaDownloadEngine._resolve_source_chain
        original_fetch = self.core.JavaDownloadEngine._fetch_foojay_distribution
        original_github = self.core.JavaDownloadEngine._fetch_github_profile_releases

        def fake_fetch(distribution, vendor, major_version, resolve_final_url=False, package_type="jdk"):
            calls.append((distribution, vendor, major_version, package_type))
            return {
                "version": f"{major_version}.0.{len(calls)}",
                "url": f"https://download.example.invalid/{distribution}-{package_type}.zip",
                "urls": [f"https://download.example.invalid/{distribution}-{package_type}.zip"],
                "source": f"Foojay {distribution}",
                "vendor": vendor,
                "package_type": package_type,
            }

        try:
            self.core.JavaDownloadEngine._resolve_source_chain = staticmethod(lambda _vendor: [])
            self.core.JavaDownloadEngine._fetch_foojay_distribution = staticmethod(fake_fetch)
            self.core.JavaDownloadEngine._fetch_github_profile_releases = staticmethod(lambda *_args, **_kwargs: None)

            candidates = self.core.JavaDownloadEngine.get_download_info_candidates("AOJ OpenJDK", "8", package_type="jdk")
        finally:
            self.core.JavaDownloadEngine._resolve_source_chain = original_chain
            self.core.JavaDownloadEngine._fetch_foojay_distribution = original_fetch
            self.core.JavaDownloadEngine._fetch_github_profile_releases = original_github

        self.assertEqual([item["source"] for item in candidates], ["Foojay aoj", "Foojay aoj_openj9"])
        self.assertIn(("aoj", "AOJ OpenJDK", "8", "jdk"), calls)
        self.assertIn(("aoj_openj9", "AOJ OpenJDK", "8", "jdk"), calls)

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

    def test_release_metadata_detects_more_java_vendors(self):
        cases = [
            ('IMPLEMENTOR="AdoptOpenJDK"\n', "AOJ OpenJDK", "hotspot"),
            ('IMPLEMENTOR="AdoptOpenJDK"\nJVM_VARIANT="OpenJ9"\n', "AOJ OpenJ9", "openj9"),
            ('IMPLEMENTOR="IBM"\nIMPLEMENTOR_VERSION="Semeru Certified"\n', "IBM Semeru Certified", "openj9"),
            ('IMPLEMENTOR="OpenLogic"\n', "OpenLogic OpenJDK", "hotspot"),
            ('IMPLEMENTOR="Red Hat, Inc."\n', "Red Hat OpenJDK", "hotspot"),
            ('IMPLEMENTOR="Mandrel"\n', "Mandrel", "hotspot"),
            ('IMPLEMENTOR="BellSoft"\nIMPLEMENTOR_VERSION="Liberica Native Image Kit"\n', "Liberica Native Image Kit", "hotspot"),
            ('IMPLEMENTOR="Gluon"\nJAVA_RUNTIME_NAME="GraalVM Runtime Environment"\n', "Gluon GraalVM", "hotspot"),
            ('IMPLEMENTOR="GraalVM Community"\n', "GraalVM Community", "hotspot"),
        ]

        for release_extra, expected_vendor, expected_jvm in cases:
            with self.subTest(vendor=expected_vendor), tempfile.TemporaryDirectory() as tmp:
                java_home = Path(tmp) / expected_vendor.replace(" ", "_")
                java_home.mkdir(parents=True)
                (java_home / "release").write_text(f'JAVA_VERSION="21.0.1"\n{release_extra}', encoding="utf-8")

                runtime = self.core.read_java_runtime_info(str(java_home))

                self.assertEqual(runtime["vendor"], expected_vendor)
                self.assertEqual(runtime["jvm_impl"], expected_jvm)

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

    def test_update_target_path_renames_tool_versioned_java_folder(self):
        info = {
            "vendor": "Eclipse Temurin",
            "major_version": "21",
            "version": "21.0.8+9",
            "package_type": "jdk",
        }
        with tempfile.TemporaryDirectory() as tmp:
            old_path = Path(tmp) / "Eclipse_Temurin_jdk21_21.0.1"
            old_path.mkdir()
            custom_path = Path(tmp) / "MyCustomJava"
            custom_path.mkdir()
            occupied = Path(tmp) / "Eclipse_Temurin_jdk21_21.0.8_9"
            occupied.mkdir()

            renamed = self.core.resolve_update_java_home_target_path(str(old_path), info)
            custom = self.core.resolve_update_java_home_target_path(str(custom_path), info)

        self.assertEqual(Path(renamed).name, "Eclipse_Temurin_jdk21_21.0.8_9_2")
        self.assertEqual(Path(custom).name, "MyCustomJava")

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
            "Trava OpenJDK": "trava",
            "ojdkbuild": "ojdk_build",
            "AOJ OpenJDK": "aoj",
            "AOJ OpenJ9": "aoj_openj9",
            "Eliya OpenJDK": "eliya",
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

    def test_oracle_graalvm_never_falls_back_to_community_assets(self):
        profile = self.core.JAVA_VENDOR_PROFILES["GraalVM"]
        self.assertNotIn("graalvm/graalvm-ce-builds", profile.get("github_repos", ()))
        self.assertFalse(
            self.core.JavaDownloadEngine._is_desired_asset_name(
                "graalvm-community-jdk-21.0.2_windows-x64_bin.zip",
                "GraalVM",
            )
        )
        self.assertTrue(
            self.core.JavaDownloadEngine._is_desired_asset_name(
                "graalvm-community-jdk-21.0.2_windows-x64_bin.zip",
                "GraalVM Community",
            )
        )

        calls = []
        original_foojay = self.core.JavaDownloadEngine._fetch_foojay_distribution
        original_github = self.core.JavaDownloadEngine._request_github_releases
        try:
            def fake_foojay(distribution, vendor, major_version, **_kwargs):
                calls.append((distribution, vendor, str(major_version)))
                return {
                    "version": "21.0.11",
                    "url": "https://download.oracle.com/graalvm/21/latest/graalvm-jdk-21_windows-x64_bin.zip",
                    "urls": ["https://download.oracle.com/graalvm/21/latest/graalvm-jdk-21_windows-x64_bin.zip"],
                    "source": "Foojay graalvm",
                    "vendor": vendor,
                }

            self.core.JavaDownloadEngine._fetch_foojay_distribution = staticmethod(fake_foojay)
            self.core.JavaDownloadEngine._request_github_releases = staticmethod(
                lambda *_args, **_kwargs: self.fail("Oracle GraalVM must not query the Community GitHub repository")
            )
            result = self.core.JavaDownloadEngine._fetch_graalvm("21")
            mirror_result = self.core.JavaDownloadEngine._fetch_graalvm("21", mirrors_only=True)
        finally:
            self.core.JavaDownloadEngine._fetch_foojay_distribution = original_foojay
            self.core.JavaDownloadEngine._request_github_releases = original_github

        self.assertEqual(calls, [("graalvm", "GraalVM", "21")])
        self.assertEqual(result["source"], "Oracle GraalVM via Foojay")
        self.assertIsNone(mirror_result)

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

    def test_download_page_minecraft_advice_is_dynamic_and_explicit(self):
        mainstream = self.core.minecraft_download_advice("Eclipse Temurin", "21", language="zh_CN")
        graal = self.core.minecraft_download_advice("GraalVM", "21", language="zh_CN")
        experimental = self.core.minecraft_download_advice("Eclipse Temurin", "22", language="en_US")

        self.assertIn("MC 当前选择: Eclipse Temurin JDK 21", mainstream)
        self.assertIn("MC 版本匹配: Minecraft 1.20.5-1.21.x", mainstream)
        self.assertIn("MC 建议等级: 推荐", mainstream)
        self.assertIn("MC 当前选择: GraalVM JDK 21", graal)
        self.assertIn("性能实验", graal)
        self.assertIn("MC selection: Eclipse Temurin JDK 22", experimental)
        self.assertIn("MC recommendation: Experimental", experimental)

    def test_update_detection_ignores_vendor_version_text_asymmetry(self):
        # Corretto latest versions look like 21.0.8.9.1 while the installed
        # release file reports 21.0.8+9-LTS; both describe the same build.
        self.assertFalse(self.core.is_update_available("21.0.8+9-LTS", "21.0.8.9.1", "21"))
        # Foojay java_version texts carry no build number; comparing them
        # against an installed build must not flag a phantom update.
        self.assertFalse(self.core.is_update_available("21.0.8+12-LTS", "21.0.8", "21"))
        self.assertFalse(self.core.is_update_available("1.8.0_452", "8u452", "8"))
        # Genuine updates must still be detected.
        self.assertTrue(self.core.is_update_available("21.0.7+11", "21.0.8", "21"))
        self.assertTrue(self.core.is_update_available("21.0.8+9", "21.0.8+12", "21"))
        self.assertTrue(self.core.is_update_available("1.8.0_312", "1.8.0_452", "8"))
        # A different major on the remote side is not an update for this row.
        self.assertFalse(self.core.is_update_available("21.0.8+9", "22.0.1+8", "21"))

    def test_recommended_java_majors_for_minecraft_bands(self):
        self.assertEqual(self.core.recommended_java_majors_for_minecraft("1.21.1"), ["21"])
        self.assertEqual(self.core.recommended_java_majors_for_minecraft("1.20.5"), ["21"])
        self.assertEqual(self.core.recommended_java_majors_for_minecraft("1.20.4"), ["17"])
        self.assertEqual(self.core.recommended_java_majors_for_minecraft("1.18"), ["17"])
        self.assertEqual(self.core.recommended_java_majors_for_minecraft("1.16.5"), ["8"])
        self.assertEqual(self.core.recommended_java_majors_for_minecraft("26.2"), ["25", "26"])
        self.assertEqual(self.core.recommended_java_majors_for_minecraft("not-a-version"), [])

    def test_minecraft_advice_includes_quick_reference_and_compatibility(self):
        zh = self.core.minecraft_download_advice("Eclipse Temurin", "21", language="zh_CN")
        en = self.core.minecraft_download_advice("Eclipse Temurin", "21", language="en_US")

        self.assertIn("MC 兼容判定:", zh)
        self.assertIn("MC 快速对照:", zh)
        self.assertIn("Java 21 →", zh)
        self.assertIn("Java 8 →", zh)
        self.assertIn("MC compatibility:", en)
        self.assertIn("MC quick reference:", en)

    def test_github_mirror_prefix_list_is_wellformed(self):
        prefixes = self.core.GITHUB_MIRROR_PREFIXES
        self.assertTrue(prefixes)
        for prefix in prefixes:
            self.assertTrue(prefix.startswith("https://"), prefix)
            self.assertTrue(prefix.endswith("/"), prefix)
        self.assertIn("https://ghproxy.link/", prefixes)
        self.assertIn("https://ghfast.top/", prefixes)

    def test_gui_build_scripts_stage_platform_deps_only(self):
        root = Path(__file__).resolve().parents[1]
        scripts = {
            "windows": (root / "scripts" / "build_windows.ps1").read_text(encoding="utf-8-sig"),
            "linux": (root / "scripts" / "build_linux.sh").read_text(encoding="utf-8"),
            "macos": (root / "scripts" / "build_macos.sh").read_text(encoding="utf-8"),
        }

        # Every GUI build must stage only its own platform's vendored wheels
        # instead of embedding vendor/deps wholesale (all three platforms).
        for name, script in scripts.items():
            self.assertIn("deps-stage", script, name)
            self.assertNotIn('"$Deps;deps"', script, name)
            self.assertNotIn('"$DEPS:deps"', script, name)
        self.assertIn("windows-", scripts["windows"])
        self.assertIn("linux-x86_64", scripts["linux"])
        self.assertIn("linux-aarch64", scripts["linux"])
        self.assertIn("macos-arm64", scripts["macos"])
        self.assertIn("macos-x86_64", scripts["macos"])

    def test_nogui_build_scripts_skip_tray_dependencies(self):
        root = Path(__file__).resolve().parents[1]
        for name in ("build_nogui_windows.ps1", "build_nogui_linux.sh", "build_nogui_macos.sh"):
            script = (root / "scripts" / name).read_text(encoding="utf-8-sig" if name.endswith(".ps1") else "utf-8")
            # NoGUI never starts the tray, so the vendored wheels must not be
            # referenced at all in its build scripts.
            self.assertNotIn("vendor", script, name)
            self.assertNotIn(":deps", script, name)
            self.assertNotIn(";deps", script, name)

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
            "setup_backup_tab",
        ):
            match = re.search(rf"    def {function_name}\(self\):\n(?P<body>.*?)(?=\n    def |\nclass |\Z)", source, re.S)
            self.assertIsNotNone(match, function_name)
            self.assertIn("_create_tab_motion_header", match.group("body"), function_name)

    def test_management_tabs_use_checkbox_selection(self):
        for function_name, tree_name in (
            ("setup_update_tab", "tree_up"),
            ("setup_move_tab", "tree_move"),
            ("setup_delete_tab", "tree_delete"),
            ("setup_backup_tab", "tree_backup"),
        ):
            source = inspect.getsource(getattr(self.core.JavaManagerApp, function_name))
            self.assertIn('"selected"', source, function_name)
            self.assertIn("selectmode=\"none\"", source, function_name)
            self.assertIn("on_checked_tree_click", source, function_name)
            self.assertIn(tree_name, source, function_name)

    def test_unregister_selected_uses_equivalent_java_home_cleanup(self):
        calls = []

        class Tree:
            def get_children(self):
                return ("row1", "row2", "row3")

        app = object.__new__(self.core.JavaManagerApp)
        app.tree_reg = Tree()
        app.reg_items = {
            "row1": {
                "key": "root-key",
                "registry_name": "Root",
                "java_home": "C:\\Java\\jdk8",
            },
            "row2": {
                "key": "missing-name-key",
                "registry_name": "MissingNameOnly",
                "java_home": "",
            },
            "row3": {
                "key": "unchecked-key",
                "registry_name": "Unchecked",
                "java_home": "C:\\Java\\unchecked",
            },
        }
        app.reg_checked_items = {"root-key", "missing-name-key"}
        app.refresh_all_data = lambda: calls.append(("refresh",))

        original_unregister_home = self.core.unregister_java_home
        original_unregister = self.core.JavaRegistryAdapter.unregister
        original_warning = self.core.messagebox.showwarning
        try:
            self.core.unregister_java_home = lambda path, preferred_name=None: calls.append(("home", path, preferred_name))
            self.core.JavaRegistryAdapter.unregister = staticmethod(lambda name: calls.append(("name", name)))
            self.core.messagebox.showwarning = lambda *_args, **_kwargs: calls.append(("warning",))

            self.core.JavaManagerApp.unregister_selected(app)
        finally:
            self.core.unregister_java_home = original_unregister_home
            self.core.JavaRegistryAdapter.unregister = original_unregister
            self.core.messagebox.showwarning = original_warning

        self.assertEqual(
            calls,
            [
                ("home", "C:\\Java\\jdk8", "Root"),
                ("name", "MissingNameOnly"),
                ("refresh",),
            ],
        )

    def test_registration_check_buttons_update_visible_rows(self):
        events = []

        class Tree:
            def get_children(self):
                return ("row1", "row2")

            def set(self, item_id, column, value):
                events.append((item_id, column, value))

        app = object.__new__(self.core.JavaManagerApp)
        app.tree_reg = Tree()
        app.reg_items = {
            "row1": {"key": "one"},
            "row2": {"key": "two"},
        }
        app.reg_checked_items = set()

        self.core.JavaManagerApp.select_all_registered_java(app)
        self.assertEqual(app.reg_checked_items, {"one", "two"})
        self.assertTrue(all(value == "☑" for _item, _col, value in events[-2:]))

        self.core.JavaManagerApp.clear_registered_java_selection(app)
        self.assertEqual(app.reg_checked_items, set())
        self.assertTrue(all(value == "☐" for _item, _col, value in events[-2:]))

    def test_registration_tab_uses_checkbox_treeview(self):
        source = inspect.getsource(self.core.JavaManagerApp.setup_reg_tab)

        self.assertIn("ttk.Treeview", source)
        self.assertIn("select_all_registered_java", source)
        self.assertIn("clear_registered_java_selection", source)
        self.assertIn("on_registration_tree_click", source)
        self.assertIn("open_default_java_panel", source)
        self.assertIn("choose_system_default_java", source)
        self.assertNotIn("Listbox", source)

    def test_release_notes_and_workflows_are_bilingual(self):
        root = Path(__file__).resolve().parents[1]
        notes = (root / "docs" / "releases" / "RELEASE_NOTES_3.1.4.md").read_text(encoding="utf-8")
        template = (root / "docs" / "releases" / "RELEASE_NOTES_TEMPLATE_BILINGUAL.md").read_text(encoding="utf-8")
        gui_workflow = (root / ".github" / "workflows" / "build-packages.yml").read_text(encoding="utf-8")
        nogui_workflow = (root / ".github" / "workflows" / "build-nogui-packages.yml").read_text(encoding="utf-8")

        self.assertIn("## 更新内容", notes)
        self.assertIn("## Update Content", notes)
        self.assertIn("GraalVM", notes)
        self.assertIn("Minecraft", notes)
        self.assertLessEqual(len(notes.splitlines()), 32)
        self.assertIn("## 更新内容", template)
        self.assertIn("## Update Content", template)
        for workflow in (gui_workflow, nogui_workflow):
            self.assertIn("RELEASE_NOTES_FILE", workflow)
            self.assertIn('RELEASE_VERSION="${RELEASE_TAG#v}"', workflow)
            self.assertIn('default: "v3.1.4"', workflow)
            self.assertIn("RELEASE_NOTES_TEMPLATE_BILINGUAL.md", workflow)
            self.assertIn('--notes-file "$RELEASE_NOTES_FILE"', workflow)
            self.assertIn("group: ljm-release-", workflow)
            self.assertIn("cancel-in-progress: false", workflow)
            self.assertIn("Verify release notes UTF-8", workflow)
            self.assertIn('grep -F "## 更新内容"', workflow)
            self.assertIn('grep -F "## ????"', workflow)
            self.assertNotIn("python-source.zip", workflow)
            self.assertNotIn("Prepare Python source package", workflow)
            self.assertNotIn("LJM_nogui.cmd", workflow)

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
        self.assertIn("3.1.4", readme)
        self.assertIn("python .\\src\\LJM_nogui.py", readme)
        self.assertIn("./src/LJM_nogui", readme)
        self.assertNotIn("Current version:", readme)
        self.assertIn("python .\\LJM_nogui.py", standalone)
        self.assertIn("pythonw.exe", docs)
        self.assertNotIn("LJM_nogui.cmd", docs)
        self.assertNotIn("LJM_nogui.cmd", standalone)
        self.assertIn("../docs/NOGUI_USAGE.md", standalone)

        for path in (root / "docs").rglob("*.md"):
            text = path.read_text(encoding="utf-8").lower()
            legacy_term = "head" + "less"
            self.assertNotIn(legacy_term, text, str(path))
            self.assertNotIn("ljm_" + legacy_term, text, str(path))
            self.assertNotIn("sha256sums-" + legacy_term, text, str(path))

    def test_nogui_source_launchers_attach_to_terminal(self):
        root = Path(__file__).resolve().parents[1]
        for directory in ("src", "nogui"):
            py_launcher = (root / directory / "LJM_nogui.py").read_text(encoding="utf-8")
            sh_launcher = (root / directory / "LJM_nogui").read_text(encoding="utf-8")

            self.assertIn("LJM_nogui.pyw", py_launcher)
            self.assertIn('args = sys.argv[1:] or ["terminal", "--attach-console"]', py_launcher)
            self.assertNotIn("cmd", py_launcher.lower())
            self.assertTrue(sh_launcher.startswith("#!/usr/bin/env sh"))
            self.assertIn('if [ "$#" -eq 0 ]; then', sh_launcher)
            self.assertIn("set -- terminal", sh_launcher)
            self.assertIn('PY_SCRIPT="$SCRIPT_DIR/LJM_nogui.py"', sh_launcher)
            self.assertIn('python3 "$PY_SCRIPT" "$@"', sh_launcher)
            self.assertIn('python "$PY_SCRIPT" "$@"', sh_launcher)

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

    def test_unix_self_update_script_skips_running_executable_during_bundle_copy(self):
        app = object.__new__(self.core.JavaManagerApp)
        original_path = self.core.APP_EXECUTABLE_PATH
        try:
            self.core.APP_EXECUTABLE_PATH = "/opt/ljm/LJM-Java-Manager"
            script = app._unix_self_update_script(
                temp_new="/opt/ljm/LJM-Java-Manager.new",
                bundle_dir="/tmp/ljm-update/bundle",
                cleanup_dir="/tmp/ljm-update",
                target_dir="/opt/ljm",
                launch_command='"/opt/ljm/LJM-Java-Manager"',
            )
        finally:
            self.core.APP_EXECUTABLE_PATH = original_path

        self.assertIn('LJM_MAIN_REL="./LJM-Java-Manager"', script)
        self.assertIn("set -e", script)
        self.assertIn('if [ "$item" = "$LJM_MAIN_REL" ]; then continue; fi', script)
        self.assertIn('if [ -L "$src" ]; then', script)
        self.assertIn('cp -P "$src" "$dst"', script)
        self.assertIn("while ! mv -f", script)
        self.assertIn("chmod +x", script)
        self.assertNotIn("cp -R", script)

    def test_java_transfer_tasks_are_embedded_in_task_progress_panel(self):
        download_source = inspect.getsource(self.core.JavaManagerApp.run_download_java)
        update_source = inspect.getsource(self.core.JavaManagerApp.download_and_extract_popup_v2)
        start_source = inspect.getsource(self.core.JavaManagerApp.start_download_java)
        repair_source = inspect.getsource(self.core.JavaManagerApp.cloud_repair_java)
        perform_update_source = inspect.getsource(self.core.JavaManagerApp.perform_update)
        task_panel_source = inspect.getsource(self.core.JavaManagerApp.open_task_progress_panel)
        tray_setup_source = inspect.getsource(self.core.JavaManagerApp._setup_tray_icon)

        for source in (download_source, update_source):
            self.assertNotIn("tk.Toplevel", source)
            self.assertNotIn("top.iconify", source)
            self.assertNotIn("minimize_task", source)
            self.assertIn("_register_java_transfer", source)
            self.assertIn("_clear_java_transfer", source)
            self.assertIn("_create_transfer_control", source)
            self.assertIn("_update_task_record", source)
        for source in (start_source, repair_source, perform_update_source):
            self.assertIn("_guard_java_transfer_start", source)
        action_source = inspect.getsource(self.core.JavaManagerApp._refresh_task_action_buttons)
        self.assertIn("task_progress_pause_all", action_source)
        self.assertIn("task_progress_cancel_all", action_source)
        self.assertIn("Clean.Vertical.TScrollbar", inspect.getsource(self.core.JavaManagerApp._create_task_scroll_body))
        self.assertIn("show_active_java_transfer_from_tray", tray_setup_source)

    def test_active_java_transfer_records_can_be_completed_or_failed(self):
        app = object.__new__(self.core.JavaManagerApp)
        app._active_java_transfer = None
        app._active_java_transfer_lock = self.core.threading.RLock()
        app._task_records_lock = self.core.threading.RLock()
        app._task_records = {"running": {}, "completed": [], "failed": []}
        events = []

        class FakeRoot:
            def after(self, _delay, callback):
                callback()

        class FakeWindow:
            def winfo_exists(self):
                return True

        app.root = FakeRoot()
        app._update_task_badge = lambda: None
        app._refresh_task_progress_panel = lambda: None
        window = FakeWindow()
        original_info = self.core.messagebox.showinfo
        try:
            self.core.messagebox.showinfo = lambda title, text: events.append(("info", title, text))
            task_id = self.core.JavaManagerApp._register_java_transfer(app, "download", "下载 Java", window)

            self.assertTrue(self.core.JavaManagerApp._guard_java_transfer_start(app))
            self.assertIn(task_id, app._task_records["running"])
            self.assertFalse(any(item[0] == "info" for item in events if isinstance(item, tuple)))

            self.core.JavaManagerApp._clear_java_transfer(app, task_id, status="completed", detail="done")
            self.assertEqual(app._task_records["completed"][0]["detail"], "done")
            self.assertTrue(self.core.JavaManagerApp._guard_java_transfer_start(app))
        finally:
            self.core.messagebox.showinfo = original_info

    def test_task_progress_refresh_keeps_focused_panel_in_front(self):
        app = object.__new__(self.core.JavaManagerApp)
        app._task_records_lock = self.core.threading.RLock()
        app._task_records = {"running": {}, "completed": [], "failed": []}
        events = []

        class Root:
            def after(self, delay, callback):
                events.append(("after", delay))
                callback()

        class FocusedChild:
            def __init__(self, top):
                self.top = top

            def winfo_toplevel(self):
                return self.top

        class Window:
            def __init__(self):
                self.focused_child = FocusedChild(self)

            def winfo_exists(self):
                return True

            def focus_displayof(self):
                return self.focused_child

            def deiconify(self):
                events.append("deiconify")

            def state(self, value):
                events.append(("state", value))

            def lift(self):
                events.append("lift")

            def focus_force(self):
                events.append("focus")

            def attributes(self, *args):
                events.append(("attributes", args))

            def after(self, delay, callback):
                events.append(("window-after", delay))
                callback()

        app.root = Root()
        app._task_progress_window = Window()
        app._task_progress_bodies = {"running": object(), "completed": object(), "failed": object()}
        app._populate_task_body = lambda _body, _records, bucket: events.append(("populate", bucket))
        app._refresh_task_action_buttons = lambda: events.append("actions")

        self.core.JavaManagerApp._refresh_task_progress_panel(app)

        self.assertIn(("populate", "running"), events)
        self.assertIn("lift", events)
        self.assertIn("focus", events)

    def test_task_progress_refresh_is_coalesced_during_active_downloads(self):
        app = object.__new__(self.core.JavaManagerApp)
        app._task_records_lock = self.core.threading.RLock()
        app._task_records = {"running": {}, "completed": [], "failed": []}
        app._task_progress_refresh_job = None
        app._task_progress_window = type("Window", (), {"winfo_exists": lambda self: True})()
        events = []
        delayed = []

        class Root:
            def after(self, delay, callback):
                events.append(("after", delay))
                if delay == 0:
                    callback()
                    return "immediate"
                delayed.append(callback)
                return f"job-{len(delayed)}"

        app.root = Root()
        app._update_task_badge = lambda: events.append("badge")
        app._refresh_task_progress_panel = lambda: events.append("refresh")

        self.core.JavaManagerApp._queue_task_ui_refresh(app)
        self.core.JavaManagerApp._queue_task_ui_refresh(app)

        self.assertEqual(events.count(("after", 180)), 1)
        self.assertEqual(events.count("refresh"), 0)
        delayed[0]()
        self.assertEqual(events.count("refresh"), 1)
        self.assertIsNone(app._task_progress_refresh_job)

    def test_task_action_buttons_are_not_rebuilt_when_state_is_unchanged(self):
        app = object.__new__(self.core.JavaManagerApp)
        app._task_records_lock = self.core.threading.RLock()
        app._task_records = {
            "running": {"task-1": {"id": "task-1", "started_at": 1}},
            "completed": [],
            "failed": [],
        }
        app._task_progress_action_state = None
        events = []

        class FakeFrame:
            def __init__(self):
                self.children = []

            def winfo_children(self):
                return list(self.children)

        class FakeButton:
            def __init__(self, parent, **kwargs):
                self.parent = parent
                self.kwargs = kwargs
                parent.children.append(self)
                events.append(("create", kwargs.get("text")))

            def pack(self, **_kwargs):
                return None

            def destroy(self):
                events.append(("destroy", self.kwargs.get("text")))
                self.parent.children.remove(self)

        app._task_progress_action_frame = FakeFrame()
        app._active_task_tab_key = lambda: "running"
        app._traverse_and_paint = lambda _frame: events.append("paint")
        app._refresh_task_progress_panel = lambda: None
        app.cancel_all_running_tasks = lambda: None
        app.resume_all_running_tasks = lambda: None
        app.pause_all_running_tasks = lambda: None

        original_button = self.core.tk.Button
        try:
            self.core.tk.Button = FakeButton
            self.core.JavaManagerApp._refresh_task_action_buttons(app)
            first_create_count = len([event for event in events if event[0] == "create"])
            self.core.JavaManagerApp._refresh_task_action_buttons(app)
        finally:
            self.core.tk.Button = original_button

        self.assertEqual(first_create_count, 4)
        self.assertEqual(len([event for event in events if event[0] == "create"]), 4)
        self.assertFalse(any(event[0] == "destroy" for event in events))

    def test_transfer_task_messages_use_task_panel_parent(self):
        download_source = inspect.getsource(self.core.JavaManagerApp.run_download_java)
        update_source = inspect.getsource(self.core.JavaManagerApp.download_and_extract_popup_v2)

        self.assertIn("_show_task_message", download_source)
        self.assertIn("_show_task_message", update_source)
        self.assertNotIn("lambda: messagebox.showinfo(tr(\"download_done\")", download_source)
        self.assertNotIn("lambda: messagebox.showinfo(tr(\"task_done_title\")", update_source)

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

    def test_java_repair_plan_chooses_local_smart_or_full(self):
        runtime = {"vendor": "Eclipse Temurin", "major": "21"}
        healthy = {"exists": True, "usable": True, "healthy": True, "issues": [], "warnings": []}
        warning_only = {"exists": True, "usable": True, "healthy": False, "issues": [], "warnings": ["缺失 release 元数据"]}
        missing_core = {"exists": True, "usable": False, "healthy": False, "issues": ["缺失核心 java 可执行文件"], "warnings": []}
        missing_path = {"exists": False, "usable": False, "healthy": False, "issues": ["Java 目录不存在"], "warnings": []}

        self.assertEqual(self.core.plan_java_repair(runtime, healthy)["action"], "local")
        self.assertEqual(self.core.plan_java_repair(runtime, warning_only)["download_mode"], "smart")
        self.assertEqual(self.core.plan_java_repair(runtime, missing_core)["download_mode"], "full")
        self.assertEqual(self.core.plan_java_repair(runtime, missing_path)["download_mode"], "full")
        self.assertEqual(self.core.plan_java_repair(runtime, healthy, requested_mode="full")["download_mode"], "full")

    def test_cloud_repair_uses_local_repair_for_healthy_runtime(self):
        calls = []
        app = object.__new__(self.core.JavaManagerApp)

        class Tree:
            def selection(self):
                return ("row1",)

            def item(self, _row):
                return {"values": ("21", "Eclipse Temurin", r"C:\Java\jdk-21", "正常可用")}

        app.tree_fix = Tree()
        app.fix_items = {
            "row1": {
                "registry_name": "Temurin_21",
                "java_home": r"C:\Java\jdk-21",
                "runtime": {
                    "vendor": "Eclipse Temurin",
                    "major": "21",
                    "java_home": r"C:\Java\jdk-21",
                    "update_java_home": r"C:\Java\jdk-21",
                    "package_type": "jdk",
                    "version": "21.0.1",
                },
                "report": {"exists": True, "usable": True, "healthy": True, "issues": [], "warnings": []},
            }
        }
        app.refresh_all_data = lambda: calls.append(("refresh",))
        app.download_and_extract = lambda *_args, **_kwargs: calls.append(("download",))

        original_ask = self.core.messagebox.askyesno
        original_info = self.core.messagebox.showinfo
        original_error = self.core.messagebox.showerror
        original_local = self.core.apply_local_java_repair
        try:
            self.core.messagebox.askyesno = lambda *_args, **_kwargs: True
            self.core.messagebox.showinfo = lambda *args, **_kwargs: calls.append(("info", args[0]))
            self.core.messagebox.showerror = lambda *args, **_kwargs: calls.append(("error", args[0]))
            self.core.apply_local_java_repair = lambda path, preferred_name=None: calls.append(("local", path, preferred_name)) or {}

            self.core.JavaManagerApp.cloud_repair_java(app)
        finally:
            self.core.messagebox.askyesno = original_ask
            self.core.messagebox.showinfo = original_info
            self.core.messagebox.showerror = original_error
            self.core.apply_local_java_repair = original_local

        self.assertIn(("local", r"C:\Java\jdk-21", "Temurin_21"), calls)
        self.assertIn(("refresh",), calls)
        self.assertNotIn(("download",), calls)

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

    def test_standalone_nogui_build_scripts_fallback_to_repo_vendor_deps(self):
        root = Path(__file__).resolve().parents[1]
        linux_script = (root / "nogui" / "build_linux.sh").read_text(encoding="utf-8")
        macos_script = (root / "nogui" / "build_macos.sh").read_text(encoding="utf-8")
        windows_script = (root / "nogui" / "build_windows.ps1").read_text(encoding="utf-8")

        for script in (linux_script, macos_script):
            self.assertIn('DEPS="$ROOT/deps"', script)
            self.assertIn('vendor/deps', script)
            self.assertIn('--add-data "$DEPS:deps"', script)
        self.assertIn('$Deps = Join-Path $Root "deps"', windows_script)
        self.assertIn('"vendor\\deps"', windows_script)
        self.assertIn('--add-data "$Deps;deps"', windows_script)

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

    def test_validate_java_move_target_rejects_symbolic_link_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            real_source = Path(tmp) / "real-jdk"
            link_source = Path(tmp) / "linked-jdk"
            target = Path(tmp) / "moved-jdk"
            real_source.mkdir()
            try:
                os.symlink(real_source, link_source, target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symbolic links unavailable: {exc}")

            with self.assertRaisesRegex(ValueError, "symbolic link"):
                self.core.validate_java_move_target(str(link_source), str(target))

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
        self.assertNotIn("PATH=", desktop_env)
        self.assertNotIn("export PATH", profile_text)

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
            self.assertNotIn("setenv PATH", launch_text)

    def test_windows_java_environment_sets_java_home_without_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            java_home = Path(tmp) / "jdk-21"
            java_home.mkdir()

            calls = []

            class FakeWinreg:
                HKEY_LOCAL_MACHINE = object()
                KEY_READ = 1
                KEY_WRITE = 2
                REG_SZ = 1

                @staticmethod
                def OpenKey(_root, path, _reserved, access):
                    calls.append(("OpenKey", path, access))
                    return "key"

                @staticmethod
                def QueryValueEx(_key, name):
                    calls.append(("QueryValueEx", name))
                    return (r"C:\Windows\System32;C:\Tools", None)

                @staticmethod
                def SetValueEx(_key, name, _reserved, _kind, value):
                    calls.append(("SetValueEx", name, value))

                @staticmethod
                def CloseKey(key):
                    calls.append(("CloseKey", key))

            original_winreg = getattr(self.core, "winreg", None)
            original_broadcast = self.core.broadcast_environment_change
            original_path = os.environ.get("PATH")
            try:
                self.core.winreg = FakeWinreg
                self.core.broadcast_environment_change = lambda: calls.append(("broadcast",))
                self.core.write_windows_java_environment(str(java_home))
            finally:
                if original_winreg is not None:
                    self.core.winreg = original_winreg
                self.core.broadcast_environment_change = original_broadcast
                if original_path is None:
                    os.environ.pop("PATH", None)
                else:
                    os.environ["PATH"] = original_path

            self.assertIn(("SetValueEx", "JAVA_HOME", str(java_home)), calls)
            self.assertNotIn("Path", [call[1] for call in calls if call[0] == "SetValueEx"])
            self.assertEqual(os.environ.get("PATH"), original_path)

    def test_windows_unregister_removes_external_java_entries_by_home(self):
        class FakeKey:
            def __init__(self, hive, path):
                self.hive = hive
                self.path = path

        class FakeWinreg:
            HKEY_LOCAL_MACHINE = "HKLM"
            HKEY_CURRENT_USER = "HKCU"
            KEY_READ = 1
            KEY_WRITE = 2
            KEY_ALL_ACCESS = 3
            KEY_WOW64_64KEY = 0x100
            KEY_WOW64_32KEY = 0x200

            registry = {
                ("HKLM", r"SOFTWARE\JavaSoft\JDK"): {
                    "17": r"C:\Java\jdk-17",
                },
                ("HKCU", r"SOFTWARE\JavaSoft\Java Development Kit"): {
                    "21": r"C:\Users\User\Apps\jdk-21",
                },
            }
            deleted = []

            @staticmethod
            def OpenKey(root, path, _reserved, _access):
                if isinstance(root, FakeKey):
                    entries = FakeWinreg.registry.get((root.hive, root.path), {})
                    if path not in entries:
                        raise FileNotFoundError(path)
                    return FakeKey(root.hive, f"{root.path}\\{path}")
                if (root, path) not in FakeWinreg.registry:
                    raise FileNotFoundError(path)
                return FakeKey(root, path)

            @staticmethod
            def EnumKey(key, index):
                names = list(FakeWinreg.registry.get((key.hive, key.path), {}).keys())
                if index >= len(names):
                    raise OSError()
                return names[index]

            @staticmethod
            def QueryValueEx(key, name):
                if name != "JavaHome":
                    raise FileNotFoundError(name)
                parent_path, version_name = key.path.rsplit("\\", 1)
                return (FakeWinreg.registry[(key.hive, parent_path)][version_name], None)

            @staticmethod
            def DeleteKey(parent, version_name):
                entries = FakeWinreg.registry.get((parent.hive, parent.path), {})
                if version_name not in entries:
                    raise FileNotFoundError(version_name)
                del entries[version_name]
                FakeWinreg.deleted.append((parent.hive, parent.path, version_name))

            @staticmethod
            def CloseKey(_key):
                return None

        original_is_win = self.core.IS_WIN
        original_winreg = getattr(self.core, "winreg", None)
        try:
            self.core.IS_WIN = True
            self.core.winreg = FakeWinreg

            removed = self.core.JavaRegistryAdapter.unregister(
                "Display_Name_Does_Not_Matter",
                java_home=r"C:\Users\User\Apps\jdk-21",
            )
        finally:
            self.core.IS_WIN = original_is_win
            if original_winreg is not None:
                self.core.winreg = original_winreg

        self.assertTrue(removed)
        self.assertIn(("HKCU", r"SOFTWARE\JavaSoft\Java Development Kit", "21"), FakeWinreg.deleted)
        self.assertIn("17", FakeWinreg.registry[("HKLM", r"SOFTWARE\JavaSoft\JDK")])
        self.assertNotIn("21", FakeWinreg.registry[("HKCU", r"SOFTWARE\JavaSoft\Java Development Kit")])

    def test_sync_runtime_registration_does_not_change_java_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            java_home = Path(tmp) / "jdk-21"
            bin_dir = java_home / "bin"
            bin_dir.mkdir(parents=True)
            (bin_dir / ("java.exe" if self.core.IS_WIN else "java")).write_text("", encoding="utf-8")
            (java_home / "release").write_text('JAVA_VERSION="21.0.1"\nIMPLEMENTOR="Eclipse Temurin"\n', encoding="utf-8")

            calls = []
            original_find = self.core.JavaRegistryAdapter.find_version_names_by_home
            original_register = self.core.JavaRegistryAdapter.register
            original_configure = self.core.configure_registered_java_environment
            try:
                self.core.JavaRegistryAdapter.find_version_names_by_home = staticmethod(lambda _home: [])
                self.core.JavaRegistryAdapter.register = staticmethod(lambda _name, _home, _jvm: True)
                self.core.configure_registered_java_environment = lambda home: calls.append(home)

                synced = self.core.JavaRegistryAdapter.sync_runtime_registration(str(java_home), preferred_name="Temurin_21")
            finally:
                self.core.JavaRegistryAdapter.find_version_names_by_home = original_find
                self.core.JavaRegistryAdapter.register = original_register
                self.core.configure_registered_java_environment = original_configure

            self.assertEqual(synced, ["Temurin_21"])
            self.assertEqual(calls, [])

    def test_scan_folder_uses_registration_sync(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "src" / "LJM.pyw").read_text(encoding="utf-8")

        match = re.search(r"    def scan_folder\(self\):\n(?P<body>.*?)(?=\n    def |\nclass |\Z)", source, re.S)
        self.assertIsNotNone(match)
        body = match.group("body")
        self.assertIn("JavaRegistryAdapter.sync_runtime_registration(register_home", body)
        self.assertNotIn("JavaRegistryAdapter.register(registry_name, register_home", body)

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

    def test_validate_java_delete_target_rejects_symbolic_link_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            real_source = Path(tmp) / "real-jdk"
            link_source = Path(tmp) / "linked-jdk"
            (real_source / "bin").mkdir(parents=True)
            (real_source / "bin" / ("java.exe" if self.core.IS_WIN else "java")).write_text("", encoding="utf-8")
            try:
                os.symlink(real_source, link_source, target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symbolic links unavailable: {exc}")

            with self.assertRaisesRegex(ValueError, "symbolic link"):
                self.core.validate_java_delete_target(str(link_source))

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

    def test_java_backup_is_compressed_and_restorable_without_plain_java_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            backup_root = Path(tmp) / "backups"
            java_home = Path(tmp) / "Eclipse_Temurin_jdk21_21.0.1"
            java_bin = java_home / "bin"
            java_bin.mkdir(parents=True)
            java_exe = "java.exe" if self.core.IS_WIN else "java"
            (java_bin / java_exe).write_text("java", encoding="utf-8")
            (java_home / "release").write_text('JAVA_VERSION="21.0.1"\nIMPLEMENTOR="Eclipse Temurin"\n', encoding="utf-8")

            original_backup_root = self.core.backup_root_dir
            original_find = self.core.JavaRegistryAdapter.find_version_names_by_home
            original_sync = self.core.JavaRegistryAdapter.sync_runtime_registration
            synced = []
            try:
                self.core.backup_root_dir = lambda: str(backup_root)
                self.core.JavaRegistryAdapter.find_version_names_by_home = staticmethod(lambda _home: ["Temurin_21"])
                self.core.JavaRegistryAdapter.sync_runtime_registration = staticmethod(lambda path, preferred_name=None: synced.append((path, preferred_name)) or ["Temurin_21"])

                backup_dir = Path(self.core.create_java_backup(str(java_home), operation="update"))
                archive_path = backup_dir / "java_home.zip"
                plain_java_home = backup_dir / "java_home"

                (java_home / "release").write_text('JAVA_VERSION="broken"\n', encoding="utf-8")
                (java_bin / java_exe).unlink()
                restored_path = self.core.restore_java_backup(str(backup_dir))
            finally:
                self.core.backup_root_dir = original_backup_root
                self.core.JavaRegistryAdapter.find_version_names_by_home = original_find
                self.core.JavaRegistryAdapter.sync_runtime_registration = original_sync

            self.assertTrue(archive_path.exists())
            self.assertFalse(plain_java_home.exists())
            with zipfile.ZipFile(archive_path, "r") as archive:
                names = set(archive.namelist())
            self.assertIn("java_home/release", names)
            self.assertIn(f"java_home/bin/{java_exe}", names)
            self.assertEqual(Path(restored_path), java_home)
            self.assertIn('JAVA_VERSION="21.0.1"', (java_home / "release").read_text(encoding="utf-8"))
            self.assertTrue((java_bin / java_exe).exists())
            self.assertEqual(synced, [(str(java_home), "Temurin_21")])

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

    def test_remove_cached_archive_cleans_parallel_download_parts(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "Temurin_jdk_21.zip"
            url = "https://download.example.invalid/jdk.zip"
            part = Path(self.core.NetworkEngine._download_part_path(str(archive), url))
            segment = Path(f"{part}.0")
            merge = Path(f"{part}.merge")
            unrelated = Path(tmp) / "Other_jdk_21.zip.0123456789abcdef.part.0"

            archive.write_bytes(b"bad-cache")
            Path(str(archive) + ".json").write_text("{}", encoding="utf-8")
            part.write_bytes(b"part")
            segment.write_bytes(b"segment")
            merge.write_bytes(b"merge")
            unrelated.write_bytes(b"keep")

            self.core.remove_cached_archive(str(archive))

            self.assertFalse(archive.exists())
            self.assertFalse(Path(str(archive) + ".json").exists())
            self.assertFalse(part.exists())
            self.assertFalse(segment.exists())
            self.assertFalse(merge.exists())
            self.assertTrue(unrelated.exists())

    def test_safe_extract_zip_rejects_backslash_path_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive_path = Path(tmp) / "bad.zip"
            extract_dir = Path(tmp) / "extract"
            extract_dir.mkdir()
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("..\\evil.txt", "blocked")

            with zipfile.ZipFile(archive_path, "r") as archive:
                with self.assertRaisesRegex(Exception, "越界路径"):
                    self.core.safe_extract_zip(archive, str(extract_dir))

            self.assertFalse((Path(tmp) / "evil.txt").exists())

    def test_safe_extract_zip_rejects_unsafe_symlink_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive_path = Path(tmp) / "bad-link.zip"
            extract_dir = Path(tmp) / "extract"
            extract_dir.mkdir()
            link_info = zipfile.ZipInfo("jdk/link")
            link_info.external_attr = 0o120777 << 16
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr(link_info, "../../outside")

            with zipfile.ZipFile(archive_path, "r") as archive:
                with self.assertRaisesRegex(Exception, "越界链接"):
                    self.core.safe_extract_zip(archive, str(extract_dir))

    def test_safe_extract_zip_preserves_unix_executable_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive_path = Path(tmp) / "mode.zip"
            extract_dir = Path(tmp) / "extract"
            extract_dir.mkdir()
            file_info = zipfile.ZipInfo("jdk/bin/java")
            file_info.external_attr = 0o100755 << 16
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr(file_info, "java")

            chmod_calls = []
            original_chmod = self.core.os.chmod
            try:
                self.core.os.chmod = lambda path, mode: chmod_calls.append((Path(path), mode))
                with zipfile.ZipFile(archive_path, "r") as archive:
                    self.core.safe_extract_zip(archive, str(extract_dir))
            finally:
                self.core.os.chmod = original_chmod

            extracted = extract_dir / "jdk" / "bin" / "java"
            self.assertTrue(extracted.exists())
            self.assertIn((extracted, 0o755), chmod_calls)

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

    def test_main_ui_has_home_fade_navigation_without_extra_menu_bar(self):
        source = Path("src/LJM.pyw").read_text(encoding="utf-8")

        self.assertIn("PAGE_FADE_STEPS = 12", source)
        self.assertIn("def _switch_notebook_tab", source)
        self.assertIn("def _fade_switch_to_tab", source)
        self.assertIn("self.notebook.bind(\"<ButtonPress-1>\", self._on_notebook_button_press)", source)
        self.assertIn("self.root.config(menu=\"\")", source)
        self.assertNotIn("def _setup_menu_bar", source)
        self.assertNotIn("def _theme_menu_bar", source)
        self.assertNotIn("tk.Menubutton(", source)
        self.assertNotIn("tk.Menu(self.root", source)
        self.assertNotIn("self._setup_menu_bar()", source)
        self.assertNotIn("self._theme_menu_bar()", source)
        self.assertNotIn("self.root.config(menu=self.menubar)", source)
        self.assertNotIn('widget_class == "Menubutton"', source)
        self.assertIn("self.notebook.add(self.tab_home, text=tr(\"tab_home\"))", source)
        # The standalone changelog page was removed in 3.1.4.
        self.assertNotIn("tab_changelog", source)
        self.assertNotIn("def load_changelog_text", source)
        self.assertNotIn("def setup_changelog_tab", source)
        self.assertNotIn("home_changelog", source)
        self.assertIn("def setup_home_tab", source)
        self.assertIn("def open_default_java_panel", source)
        self.assertIn("def read_current_default_java_home", source)
        self.assertIn("def open_task_progress_panel", source)
        self.assertIn("self.task_progress_button", source)
        self.assertIn("side=tk.RIGHT", source)
        self.assertIn("command=self.open_feedback", source)
        self.assertIn("command=self.open_settings", source)
        self.assertIn("command=self.open_about", source)
        self.assertIn('"home_about": "关于"', source)
        self.assertIn('"home_about": "About"', source)
        self.assertNotIn('tk.Button(toolbar, text=tr("toolbar_settings")', source)
        self.assertNotIn('tk.Button(toolbar, text=tr("toolbar_feedback")', source)
        self.assertNotIn('tk.Button(toolbar, text=tr("toolbar_about")', source)

    def test_theme_paints_text_widgets_and_scrollbars(self):
        source = Path("src/LJM.pyw").read_text(encoding="utf-8")

        self.assertIn('style.configure(\n            "TScrollbar"', source)
        self.assertIn('elif widget_class == "Text":', source)
        self.assertIn("bg=self.current_field", source)
        self.assertIn("fg=self.current_fg", source)
        self.assertIn("insertbackground=self.current_fg", source)
        self.assertIn("selectbackground=self.current_btn", source)
        self.assertNotIn("changelog", source)

    def test_notebook_fade_navigation_does_not_use_blocking_overlay(self):
        source = Path("src/LJM.pyw").read_text(encoding="utf-8")

        self.assertIn("def _selected_tab_motion_canvas", source)
        self.assertNotIn("tk.Canvas(self.notebook", source)
        self.assertNotIn("overlay.place(relx=0, rely=0, relwidth=1, relheight=1)", source)

        fade_match = re.search(r"    def _fade_switch_to_tab\(self, target_tab.*?\):\n(?P<body>.*?)(?=\n    def |\nclass |\Z)", source, re.S)
        self.assertIsNotNone(fade_match)
        fade_body = fade_match.group("body")
        self.assertNotIn("_ensure_notebook_fade_overlay", fade_body)
        self.assertNotIn("_draw_notebook_fade_overlay", fade_body)

        cancel_match = re.search(r"    def _cancel_notebook_fade\(self, reset_state=True\):\n(?P<body>.*?)(?=\n    def |\nclass |\Z)", source, re.S)
        self.assertIsNotNone(cancel_match)
        cancel_body = cancel_match.group("body")
        self.assertIn("self._notebook_switching = False", cancel_body)
        self.assertIn("self._pending_notebook_tab = None", cancel_body)

    def test_notebook_switch_selects_tab_before_scheduling_animation(self):
        app = object.__new__(self.core.JavaManagerApp)
        events = []

        class Root:
            def __init__(self):
                self.jobs = []
                self.cancelled = []

            def after(self, delay, callback):
                job = f"job-{len(self.jobs) + 1}"
                self.jobs.append((job, delay, callback))
                events.append(("after", delay))
                return job

            def after_cancel(self, job):
                self.cancelled.append(job)
                events.append(("cancel", job))

        class Notebook:
            def __init__(self):
                self.selected = "tab-home"

            def select(self, tab=None):
                if tab is not None:
                    self.selected = str(tab)
                    events.append(("select", self.selected))
                return self.selected

        root = Root()
        app.root = root
        app.notebook = Notebook()
        app._ui_ready_for_tab_fade = True
        app._notebook_switching = False
        app._notebook_fade_job = None
        app._notebook_fade_overlay = None
        app._notebook_fade_generation = 0
        app._pending_notebook_tab = None
        app._tab_motion_headers = {"tab-download": object()}
        app._animate_selected_tab_motion_header = lambda: events.append("animate")
        app._draw_tab_motion_header = lambda _canvas, progress: events.append(("draw", round(progress, 2)))

        switched = self.core.JavaManagerApp._switch_notebook_tab(app, "tab-download")

        self.assertTrue(switched)
        self.assertEqual(app.notebook.selected, "tab-download")
        self.assertIn(("select", "tab-download"), events)
        self.assertIn(("draw", 0.0), events)
        self.assertEqual(root.jobs[-1][1], self.core.PAGE_FADE_INTERVAL_MS)
        self.assertIsNone(app._notebook_fade_overlay)

        self.core.JavaManagerApp._cancel_notebook_fade(app)

        self.assertFalse(app._notebook_switching)
        self.assertIsNone(app._pending_notebook_tab)

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

    def test_nogui_entry_tkinter_import_is_optional_for_source_usage(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "src" / "LJM_nogui_entry.py").read_text(encoding="utf-8")
        core_source = (root / "src" / "LJM.pyw").read_text(encoding="utf-8")

        self.assertIn("try:\n    import tkinter as tk", source)
        self.assertIn("except Exception:", source)
        self.assertIn("try:\n    import tkinter as tk", core_source)
        self.assertIn("TK_IMPORT_ERROR", core_source)
        self.assertIn('args = sys.argv[1:] or ["terminal", "--attach-console"]', source)

    def test_nogui_scan_uses_shared_registration_sync(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "src" / "LJM_nogui.pyw").read_text(encoding="utf-8")
        match = re.search(r"def command_scan\(args\):\n(?P<body>.*?)(?=\ndef |\nclass |\Z)", source, re.S)
        self.assertIsNotNone(match)
        body = match.group("body")
        self.assertIn("core.JavaRegistryAdapter.sync_runtime_registration(register_home", body)
        self.assertNotIn("core.JavaRegistryAdapter.register(registry_name, register_home", body)

    def test_nogui_update_download_uses_checksum_archive_check_and_fallback_sources(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "src" / "LJM_nogui.pyw").read_text(encoding="utf-8")
        match = re.search(r"def download_latest_jdk\(.*?\):\n(?P<body>.*?)(?=\ndef |\nclass |\Z)", source, re.S)
        self.assertIsNotNone(match)
        body = match.group("body")

        self.assertIn("core.resolve_download_sha256(info)", body)
        self.assertIn("expected_sha256=expected_sha256", body)
        self.assertIn("core.verify_file_sha256", body)
        self.assertIn("core.archive_quick_check", body)
        self.assertIn("core.JavaDownloadEngine.get_download_info_candidates", body)

    def test_nogui_parser_has_download_move_delete_and_feedback_commands(self):
        parser = self.nogui.build_parser()

        download_args = parser.parse_args(["download", "Eclipse Temurin", "21", r"D:\Java"])
        move_args = parser.parse_args(["move", "Temurin_21", r"D:\Java\Temurin_21"])
        delete_args = parser.parse_args(["delete", "Temurin_21", "--files", "--force"])
        vendors_args = parser.parse_args(["vendors"])
        feedback_args = parser.parse_args(["feedback", "--message", "OpenJ9 source is slow"])
        terminal_args = parser.parse_args(["terminal"])
        terminal_attach_args = parser.parse_args(["terminal", "--attach-console"])
        version_args = parser.parse_args(["version"])
        status_args = parser.parse_args(["status"])
        language_args = parser.parse_args(["language", "en"])
        short_download_args = parser.parse_args(["dl", "Eclipse Temurin", "21", r"D:\Java"])
        short_update_args = parser.parse_args(["u", "Temurin_21"])
        short_repair_args = parser.parse_args(["r", "Temurin_21"])
        short_version_args = parser.parse_args(["v"])
        short_status_args = parser.parse_args(["st"])

        self.assertEqual(download_args.command, "download")
        self.assertIs(download_args.func, self.nogui.command_download)
        self.assertIs(short_download_args.func, self.nogui.command_download)
        self.assertIs(short_update_args.func, self.nogui.command_update)
        self.assertIs(short_repair_args.func, self.nogui.command_repair)
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
        self.assertEqual(terminal_args.command, "terminal")
        self.assertIs(terminal_args.func, self.nogui.command_terminal)
        self.assertTrue(terminal_attach_args.attach_console)
        self.assertEqual(version_args.command, "version")
        self.assertIs(version_args.func, self.nogui.command_version)
        self.assertIs(short_version_args.func, self.nogui.command_version)
        self.assertEqual(status_args.command, "status")
        self.assertIs(status_args.func, self.nogui.command_status)
        self.assertIs(short_status_args.func, self.nogui.command_status)
        self.assertEqual(language_args.command, "language")
        self.assertEqual(language_args.value, "en")
        self.assertIs(language_args.func, self.nogui.command_language)

    def test_nogui_scan_accepts_optional_paths(self):
        parser = self.nogui.build_parser()

        bare_scan = parser.parse_args(["scan"])
        path_scan = parser.parse_args(["scan", r"D:\Java", "--max-depth", "3"])

        self.assertEqual(bare_scan.command, "scan")
        self.assertIs(bare_scan.func, self.nogui.command_scan)
        self.assertEqual(bare_scan.paths, [])
        self.assertEqual(path_scan.paths, [r"D:\Java"])
        self.assertEqual(path_scan.max_depth, 3)

        source = inspect.getsource(self.nogui.command_scan)
        self.assertIn("args.paths or None", source)

    def test_nogui_update_skips_download_when_already_current(self):
        parser = self.nogui.build_parser()
        update_args = parser.parse_args(["u", "Temurin_21"])

        self.assertIs(update_args.func, self.nogui.command_update)
        source = inspect.getsource(self.nogui.command_update)
        self.assertIn("skip_when_current=True", source)
        worker_source = inspect.getsource(self.nogui.repair_or_update_target)
        self.assertIn("skip_when_current", worker_source)
        self.assertIn("up_to_date", worker_source)

    def test_gui_already_latest_dialog_shows_formatted_message(self):
        source = inspect.getsource(self.nogui.core)
        self.assertIn("already_latest_text = tr(", source)
        self.assertIn("text=already_latest_text", source)

    def test_nogui_registry_name_is_rebuilt_after_versioned_folder_rename(self):
        source = inspect.getsource(self.nogui.repair_or_update_target)
        self.assertIn("build_registry_name", source)

    def test_nogui_set_default_falls_back_to_hkcu_environment(self):
        source = inspect.getsource(self.nogui.set_default_java)
        self.assertIn("HKEY_LOCAL_MACHINE", source)
        self.assertIn("HKEY_CURRENT_USER", source)
        self.assertIn("HKCU\\\\Environment", source)

    def test_nogui_terminal_environment_helpers(self):
        argv = self.nogui.terminal_split(r'download "Eclipse Temurin" 21 D:\Java --package-type jdk', platform_name="nt")
        self.assertEqual(argv, ["download", "Eclipse Temurin", "21", r"D:\Java", "--package-type", "jdk"])
        posix_argv = self.nogui.terminal_split('scan "/opt/java runtimes" --stdout', platform_name="posix")
        self.assertEqual(posix_argv, ["scan", "/opt/java runtimes", "--stdout"])
        self.assertEqual(self.nogui.normalize_terminal_argv(["LIST"]), ["list"])
        self.assertEqual(self.nogui.normalize_terminal_argv(["列表"]), ["list"])
        self.assertEqual(self.nogui.normalize_terminal_argv(["dl"]), ["download"])
        self.assertEqual(self.nogui.normalize_terminal_argv(["u"]), ["update"])
        self.assertEqual(self.nogui.normalize_terminal_argv(["r"]), ["repair"])
        self.assertEqual(self.nogui.normalize_terminal_argv(["st"]), ["status"])
        self.assertEqual(self.nogui.normalize_terminal_argv(["v"]), ["version"])
        self.assertEqual(self.nogui.normalize_terminal_argv(["任务"]), ["tasks"])
        self.assertEqual(self.nogui.normalize_terminal_argv(["c", "all"]), ["cancel", "all"])
        self.assertTrue(self.nogui.is_terminal_task_ref_input("1 2"))
        self.assertTrue(self.nogui.is_terminal_task_ref_input("1,2"))
        self.assertFalse(self.nogui.is_terminal_task_ref_input("cancel 1"))
        self.assertEqual(self.nogui.normalize_terminal_argv(["检查更新"]), ["check-updates"])
        self.assertEqual(self.nogui.normalize_terminal_argv(["语言", "中文"]), ["language", "中文"])
        self.assertIn("check-updates", self.nogui.terminal_help_text("en_US"))
        self.assertIn("language", self.nogui.terminal_help_text("en_US"))
        self.assertIn("cancel", self.nogui.terminal_help_text("en_US"))
        self.assertIn("exit", self.nogui.terminal_help_text("en_US"))
        self.assertIn("已成功接入", self.nogui.terminal_text("connected", "zh_CN"))
        self.assertIn("Successfully connected", self.nogui.terminal_text("connected", "en_US"))
        self.assertIn("ljm", self.nogui.terminal_text("prompt", "zh_CN"))
        self.assertEqual(self.nogui.decode_terminal_input_bytes("状态\n".encode("utf-8-sig")).strip(), "状态")
        self.assertEqual(self.nogui.format_progress_bar(50, width=10), "[#####-----]")

        class FakeStdin:
            def __init__(self, is_tty):
                self.is_tty = is_tty

            def isatty(self):
                return self.is_tty

        original_stdin = self.nogui.sys.stdin
        try:
            self.nogui.sys.stdin = FakeStdin(True)
            self.assertTrue(self.nogui.should_start_terminal([]))
            self.assertFalse(self.nogui.should_start_terminal(["list"]))
            self.nogui.sys.stdin = FakeStdin(False)
            self.assertTrue(self.nogui.should_start_terminal([]))
        finally:
            self.nogui.sys.stdin = original_stdin

        self.assertTrue(self.nogui.core.IS_NOGUI)
        self.assertTrue(self.nogui.command_status(None)["nogui_mode"])

    def test_nogui_tab_completion_covers_commands_arguments_and_windows_editor(self):
        self.assertEqual(self.nogui.terminal_completion_candidates("down"), ["download"])
        self.assertEqual(self.nogui.terminal_complete_line("ver")[:2], ("version ", 8))
        self.assertIn(
            '"GraalVM Community"',
            self.nogui.terminal_completion_candidates('download "Graal'),
        )
        self.assertIn(
            "21",
            self.nogui.terminal_completion_candidates('download "Eclipse Temurin" 2'),
        )
        self.assertEqual(self.nogui.terminal_completion_candidates("language zh"), ["zh_CN"])
        self.assertIn("--mode", self.nogui.terminal_completion_candidates("repair Java --m"))
        self.assertEqual(self.nogui.terminal_completion_candidates("repair --mode s"), ["smart"])
        self.assertIn("all", self.nogui.terminal_completion_candidates("c "))
        self.assertIn("input(prompt)", inspect.getsource(self.nogui.terminal_text_lines_from_stream))

        original_get_all = self.nogui.core.JavaRegistryAdapter.get_all
        original_msvcrt = self.nogui._msvcrt
        original_print = self.nogui.safe_print
        original_stdout = self.nogui.sys.stdout
        try:
            self.nogui.core.JavaRegistryAdapter.get_all = staticmethod(
                lambda: [("Java 21", r"C:\Java\jdk21"), ("Temurin_17", r"C:\Java\jdk17")]
            )
            self.assertIn('"Java 21"', self.nogui.terminal_completion_candidates("update J"))

            class FakeMsvcrt:
                def __init__(self):
                    self.keys = iter(["v", "e", "r", "\t", "\r"])

                def getwch(self):
                    return next(self.keys)

            self.nogui._msvcrt = FakeMsvcrt()
            self.nogui.safe_print = lambda *_args, **_kwargs: None
            self.nogui.sys.stdout = io.StringIO()
            self.assertEqual(self.nogui.windows_console_readline("ljm> "), "version \n")
        finally:
            self.nogui.core.JavaRegistryAdapter.get_all = original_get_all
            self.nogui._msvcrt = original_msvcrt
            self.nogui.safe_print = original_print
            self.nogui.sys.stdout = original_stdout

    def test_nogui_mode_keeps_windows_console_owned_by_terminal_entry(self):
        root = Path(__file__).resolve().parents[1]
        core_source = (root / "src" / "LJM.pyw").read_text(encoding="utf-8")
        nogui_source = (root / "src" / "LJM_nogui.pyw").read_text(encoding="utf-8")
        entry_source = (root / "src" / "LJM_nogui_entry.py").read_text(encoding="utf-8")
        py_launcher = (root / "src" / "LJM_nogui.py").read_text(encoding="utf-8")
        shell_launcher = (root / "src" / "LJM_nogui").read_text(encoding="utf-8")

        self.assertIn('IS_NOGUI = str(os.environ.get("LJM_NOGUI", ""))', core_source)
        self.assertIn("if not IS_NOGUI:", core_source)
        self.assertIn('os.environ["LJM_NOGUI"] = "1"', nogui_source)
        self.assertIn('os.environ["LJM_NOGUI"] = "1"', entry_source)
        self.assertIn('os.environ["LJM_NOGUI"] = "1"', py_launcher)
        self.assertIn("export LJM_NOGUI=1", shell_launcher)

    def test_nogui_terminal_background_tasks_can_report_progress_and_cancel(self):
        events = []
        original_print = self.nogui.safe_print
        original_tasks = dict(self.nogui.TERMINAL_TASKS)
        original_counter = self.nogui.TERMINAL_TASK_COUNTER
        release = self.nogui.threading.Event()

        class Args:
            command = "download"
            vendor = "Eclipse Temurin"
            major = "21"
            output = ""
            stdout = False

        def fake_download(args):
            progress_cb, status_cb = self.nogui.progress_logger("fake-download", task=args.terminal_task)
            status_cb("connecting")
            progress_cb(50, 5, 10)
            release.wait(2)
            if args.cancel_event.is_set():
                raise self.nogui.core.OperationCancelled()
            progress_cb(100, 10, 10)
            return {"ok": True, "action": "download", "result": {"java_home": "fake"}}

        try:
            with self.nogui.TERMINAL_TASK_LOCK:
                self.nogui.TERMINAL_TASKS.clear()
                self.nogui.TERMINAL_TASK_COUNTER = 0
            self.nogui.safe_print = lambda message, end="\n": events.append(str(message))
            with tempfile.TemporaryDirectory() as tmp:
                args = Args()
                args.func = fake_download
                args.output = str(Path(tmp) / "result.json")
                task = self.nogui.start_terminal_task(args, ["download", "Eclipse Temurin", "21", r"D:\Java"], language="en_US")
                deadline = time.time() + 2
                while task["progress"] < 50 and time.time() < deadline:
                    time.sleep(0.02)
                self.assertEqual(task["status"], "running")
                self.assertGreaterEqual(task["progress"], 50)
                task_line = self.nogui.format_task_line(task, "en_US")
                self.assertIn("#1", task_line)
                self.assertIn("Download", task_line)
                self.assertIn("Eclipse Temurin jdk 21", task_line)

                cancelled = self.nogui.request_cancel_terminal_tasks(str(task["id"]), "en_US")
                self.assertEqual(cancelled, [task])
                release.set()
                task["thread"].join(2)

                self.assertEqual(task["status"], "cancelled")
                self.assertTrue(Path(args.output).exists())
                self.assertTrue(any("started" in item.lower() for item in events))
                self.assertTrue(any("cancel" in item.lower() for item in events))
        finally:
            release.set()
            self.nogui.safe_print = original_print
            with self.nogui.TERMINAL_TASK_LOCK:
                self.nogui.TERMINAL_TASKS.clear()
                self.nogui.TERMINAL_TASKS.update(original_tasks)
                self.nogui.TERMINAL_TASK_COUNTER = original_counter

    def test_nogui_ctrl_c_enters_cancel_selection_mode(self):
        events = []
        original_print = self.nogui.safe_print
        original_tasks = dict(self.nogui.TERMINAL_TASKS)
        original_counter = self.nogui.TERMINAL_TASK_COUNTER
        original_configure = self.nogui.configure_terminal_environment
        original_stdin = self.nogui.sys.stdin
        interrupt_marker = self.nogui.TERMINAL_INTERRUPT

        class Args:
            command = "download"
            vendor = "Eclipse Temurin"
            major = "21"
            output = ""
            stdout = False

        def fake_download(args):
            progress_cb, _status_cb = self.nogui.progress_logger("fake-download", task=args.terminal_task)
            progress_cb(25, 1, 4)
            deadline = time.time() + 2
            while not args.cancel_event.is_set() and time.time() < deadline:
                time.sleep(0.02)
            if args.cancel_event.is_set():
                raise self.nogui.core.OperationCancelled()
            return {"ok": True, "action": "download"}

        class FakeStdin:
            def __init__(self):
                self.lines = iter([interrupt_marker, "1\n", "exit\n"])

            def isatty(self):
                return True

            def readline(self):
                item = next(self.lines, "")
                if item is interrupt_marker:
                    raise KeyboardInterrupt()
                return item

        try:
            with self.nogui.TERMINAL_TASK_LOCK:
                self.nogui.TERMINAL_TASKS.clear()
                self.nogui.TERMINAL_TASK_COUNTER = 0
            self.nogui.safe_print = lambda message, end="\n": events.append(str(message))
            self.nogui.configure_terminal_environment = lambda: None
            self.nogui.sys.stdin = FakeStdin()
            args = Args()
            args.func = fake_download
            task = self.nogui.start_terminal_task(args, ["download", "Eclipse Temurin", "21", r"D:\Java"], language="en_US")
            self.assertEqual(task["id"], 1)

            self.assertEqual(self.nogui.run_terminal(self.nogui.build_parser()), 0)
            task["thread"].join(2)

            self.assertEqual(task["status"], "cancelled")
            self.assertTrue(any("Enter the task number" in item or "任务编号" in item for item in events))
            self.assertTrue(any("#1" in item and ("Download" in item or "下载" in item) for item in events))
        finally:
            self.nogui.safe_print = original_print
            self.nogui.configure_terminal_environment = original_configure
            self.nogui.sys.stdin = original_stdin
            with self.nogui.TERMINAL_TASK_LOCK:
                self.nogui.TERMINAL_TASKS.clear()
                self.nogui.TERMINAL_TASKS.update(original_tasks)
                self.nogui.TERMINAL_TASK_COUNTER = original_counter

    def test_nogui_terminal_console_fallback_handles_empty_stdin(self):
        original_stdin = self.nogui.sys.stdin
        original_open_console = self.nogui.open_terminal_console_input
        original_print = self.nogui.safe_print

        class EmptyPipe:
            def __init__(self):
                self.buffer = io.BytesIO(b"")

            def isatty(self):
                return False

            @property
            def encoding(self):
                return "utf-8"

        try:
            self.nogui.sys.stdin = EmptyPipe()
            self.nogui.open_terminal_console_input = lambda: io.StringIO("version\nexit\n")
            self.nogui.safe_print = lambda message, end="\n": None
            lines = list(self.nogui.terminal_input_lines("en_US", attach_console=True))
        finally:
            self.nogui.sys.stdin = original_stdin
            self.nogui.open_terminal_console_input = original_open_console
            self.nogui.safe_print = original_print

        self.assertEqual(lines, ["version", "exit"])

    def test_nogui_terminal_pipe_input_still_wins_over_console_fallback(self):
        original_stdin = self.nogui.sys.stdin
        original_open_console = self.nogui.open_terminal_console_input
        original_print = self.nogui.safe_print

        class Pipe:
            def __init__(self):
                self.buffer = io.BytesIO(b"status\nexit\n")

            def isatty(self):
                return False

            @property
            def encoding(self):
                return "utf-8"

        try:
            self.nogui.sys.stdin = Pipe()
            self.nogui.open_terminal_console_input = lambda: io.StringIO("version\nexit\n")
            self.nogui.safe_print = lambda message, end="\n": None
            lines = list(self.nogui.terminal_input_lines("en_US", attach_console=True))
        finally:
            self.nogui.sys.stdin = original_stdin
            self.nogui.open_terminal_console_input = original_open_console
            self.nogui.safe_print = original_print

        self.assertEqual(lines, ["status", "exit"])

    def test_nogui_terminal_prints_localized_connected_message(self):
        events = []
        original_print = self.nogui.safe_print
        original_configure = self.nogui.configure_terminal_environment
        original_language = self.nogui.terminal_language
        original_stdin = self.nogui.sys.stdin

        class FakeStdin:
            def __init__(self):
                self.lines = iter(["退出\n"])

            def isatty(self):
                return True

            def readline(self):
                return next(self.lines, "")

        try:
            self.nogui.sys.stdin = FakeStdin()
            self.nogui.configure_terminal_environment = lambda: events.append(("configure",))
            self.nogui.terminal_language = lambda: "zh_CN"
            self.nogui.safe_print = lambda message, end="\n": events.append(("prompt", str(message)) if end == "" else str(message))
            self.assertEqual(self.nogui.run_terminal(self.nogui.build_parser()), 0)
        finally:
            self.nogui.safe_print = original_print
            self.nogui.configure_terminal_environment = original_configure
            self.nogui.terminal_language = original_language
            self.nogui.sys.stdin = original_stdin

        self.assertIn(("configure",), events)
        self.assertTrue(any("已成功接入" in item for item in events if isinstance(item, str)))
        self.assertTrue(any(item[0] == "prompt" and "ljm" in item[1] for item in events if isinstance(item, tuple)))
        self.assertTrue(any("已退出" in item for item in events if isinstance(item, str)))

    def test_nogui_language_command_follows_system_and_can_switch(self):
        parser = self.nogui.build_parser()
        original_language = self.nogui.core.APP_CONFIG.get("language", "auto")
        original_save_config = self.nogui.core.save_config
        original_detect = self.nogui.core.detect_system_language
        saved = []
        try:
            self.nogui.core.APP_CONFIG["language"] = "auto"
            self.nogui.core.save_config = lambda config: saved.append(dict(config))
            self.nogui.core.detect_system_language = lambda: "en_US"

            self.assertEqual(self.nogui.terminal_language(), "en_US")
            show_payload = self.nogui.command_language(parser.parse_args(["language"]))
            self.assertFalse(show_payload["changed"])
            self.assertEqual(show_payload["configured"], "auto")
            self.assertEqual(show_payload["active"], "en_US")

            switch_payload = self.nogui.command_language(parser.parse_args(["language", "中文"]))
            self.assertTrue(switch_payload["changed"])
            self.assertEqual(switch_payload["configured"], "zh_CN")
            self.assertEqual(switch_payload["active"], "zh_CN")
            self.assertEqual(self.nogui.terminal_language(), "zh_CN")
            self.assertEqual(saved[-1]["language"], "zh_CN")

            auto_payload = self.nogui.command_language(parser.parse_args(["language", "windows-default"]))
            self.assertEqual(auto_payload["configured"], "auto")
            self.assertEqual(auto_payload["active"], "en_US")
        finally:
            self.nogui.core.APP_CONFIG["language"] = original_language
            self.nogui.core.save_config = original_save_config
            self.nogui.core.detect_system_language = original_detect

    def test_nogui_entry_and_build_scripts_keep_dynamic_core_imports_visible(self):
        root = Path(__file__).resolve().parents[1]
        entry = (root / "src" / "LJM_nogui_entry.py").read_text(encoding="utf-8")
        scripts = "\n".join(
            (root / path).read_text(encoding="utf-8")
            for path in (
                "scripts/build_windows.ps1",
                "scripts/build_linux.sh",
                "scripts/build_macos.sh",
                "scripts/build_nogui_windows.ps1",
                "scripts/build_nogui_linux.sh",
                "scripts/build_nogui_macos.sh",
            )
        )

        for module_name in ("plistlib", "hashlib", "locale", "socket", "stat"):
            self.assertIn(f"import {module_name}", entry)
            self.assertIn(f"--hidden-import {module_name}", scripts)

        self.assertIn("import readline", entry)
        self.assertIn("import msvcrt", entry)

        self.assertIn("NoGUI terminal smoke test failed", scripts)
        self.assertIn("printf 'status\\nexit\\n'", scripts)

    def test_nogui_feedback_exports_github_issue_url(self):
        parser = self.nogui.build_parser()
        args = parser.parse_args(["feedback", "--message", "Java update list is blocked"])

        payload = self.nogui.command_feedback(args)

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["action"], "feedback")
        self.assertIn("https://github.com/Lambunge520/Java-/issues/new", payload["url"])
        self.assertIn("3.1.4", payload["body"])
        self.assertIn("Java update list is blocked", payload["body"])

    def test_nogui_full_update_uses_versioned_target_rename(self):
        source = inspect.getsource(self.nogui.repair_or_update_target)

        self.assertIn("resolve_update_java_home_target_path", source)
        self.assertIn("unregister_java_registry_name", source)
        self.assertIn("final_java_home", source)

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
