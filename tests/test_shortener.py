"""단축기 테스트. SPEC.md 4절과 6절의 경계 사례."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from base62 import decode, encode  # noqa: E402
from shortener import Shortener  # noqa: E402


class ShortenerTests(unittest.TestCase):
    def make(self, **kwargs):
        return Shortener(**kwargs)

    # --- 코드 만들기 ---
    def test_first_codes_are_serial_numbers(self):
        s = self.make()
        self.assertEqual(s.shorten("https://a.com"), "0")
        self.assertEqual(s.shorten("https://b.com"), "1")
        self.assertEqual(len(s), 2)

    def test_same_url_gets_same_code(self):
        s = self.make()
        first = s.shorten("https://a.com/long/path?q=1")
        second = s.shorten("https://a.com/long/path?q=1")
        self.assertEqual(first, second)
        self.assertEqual(len(s), 1)
        # 같은 URL은 일련번호를 쓰지 않는다
        self.assertEqual(s.shorten("https://b.com"), "1")

    def test_surrounding_whitespace_is_ignored(self):
        s = self.make()
        code = s.shorten("https://a.com")
        self.assertEqual(s.shorten("  https://a.com \n"), code)
        self.assertEqual(s.expand(code), "https://a.com")

    def test_trailing_slash_is_a_different_url(self):
        s = self.make()
        self.assertNotEqual(s.shorten("https://a.com"), s.shorten("https://a.com/"))

    def test_many_urls_get_distinct_codes_and_round_trip(self):
        s = self.make()
        urls = ["https://example.com/item/%d" % i for i in range(1000)]
        codes = [s.shorten(u) for u in urls]
        self.assertEqual(len(set(codes)), 1000)
        for u, c in zip(urls, codes):
            self.assertEqual(s.expand(c), u)
        self.assertEqual(len(s), 1000)

    def test_codes_are_base62_of_serial(self):
        s = self.make()
        codes = [s.shorten("https://a.com/%d" % i) for i in range(100)]
        self.assertEqual(codes[62], "10")
        self.assertEqual([decode(c) for c in codes], list(range(100)))

    def test_reserved_code_is_skipped(self):
        start = decode("table")
        s = self.make(start=start)
        code = s.shorten("https://a.com")
        self.assertNotEqual(code, "table")
        self.assertEqual(code, encode(start + 1))
        self.assertIsNone(s.expand("table"))

    # --- 되돌리기 ---
    def test_unknown_or_malformed_codes_expand_to_none(self):
        s = self.make()
        s.shorten("https://a.com")
        for bad in ("1", "zz", "00", "", "a-b", "../etc", None, 0):
            with self.subTest(bad=bad):
                self.assertIsNone(s.expand(bad))

    # --- 올바른 URL ---
    def test_accepts_http_and_https(self):
        s = self.make()
        for good in ("http://a.com", "https://a.com/x?y=1#z", "HTTPS://A.COM", "http://localhost:8000/"):
            with self.subTest(good=good):
                self.assertEqual(s.expand(s.shorten(good)), good)

    def test_rejects_invalid_urls(self):
        s = self.make()
        bad_urls = (
            "",
            "   ",
            "ftp://a.com",
            "javascript:alert(1)",
            "example.com",
            "http://",
            "https://",
            "http:///path",
            "https://a.com/with space",
            "https://a.com/\nLocation: https://evil.com",
            "https://a.com/\ttab",
            "mailto:me@a.com",
        )
        for bad in bad_urls:
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    s.shorten(bad)
        self.assertEqual(len(s), 0)

    def test_rejects_non_strings(self):
        s = self.make()
        for bad in (None, 123, b"https://a.com"):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    s.shorten(bad)

    def test_length_limit_is_2048(self):
        s = self.make()
        prefix = "https://a.com/"
        ok = prefix + "x" * (2048 - len(prefix))
        too_long = ok + "x"
        self.assertEqual(len(ok), 2048)
        self.assertEqual(s.expand(s.shorten(ok)), ok)
        with self.assertRaises(ValueError):
            s.shorten(too_long)

    def test_failed_shorten_does_not_use_a_serial_number(self):
        s = self.make()
        with self.assertRaises(ValueError):
            s.shorten("ftp://a.com")
        self.assertEqual(s.shorten("https://a.com"), "0")



class ProbingShortenerTests(ShortenerTests):
    """같은 단축기 테스트를 선형 탐지 테이블로 다시 돌린다 (과제 #8)."""

    def make(self, **kwargs):
        return Shortener(table="probe", **kwargs)

    def test_uses_probing_table(self):
        self.assertEqual(self.make().table.kind, "probe")


class TableChoiceTests(unittest.TestCase):
    def test_default_is_chaining(self):
        self.assertEqual(Shortener().table.kind, "chain")
        self.assertEqual(Shortener(table="chain").table.kind, "chain")

    def test_unknown_table_is_rejected(self):
        for bad in ("dict", "", None, "PROBE"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    Shortener(table=bad)

if __name__ == "__main__":
    unittest.main()
