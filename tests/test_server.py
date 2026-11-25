"""웹 서버 테스트. 포트 0으로 실제 서버를 띄우고 HTTP 요청을 보낸다."""
import http.client
import os
import sys
import threading
import unittest
from urllib.parse import urlencode

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from server import make_server  # noqa: E402
from shortener import Shortener  # noqa: E402


class ServerTests(unittest.TestCase):
    def make_shortener(self):
        return Shortener()

    def setUp(self):
        self.server, self.app = make_server(port=0, host="127.0.0.1", shortener=self.make_shortener(), quiet=True)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
        self.thread.start()
        self.port = self.server.server_address[1]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def request(self, method, path, body=None, headers=()):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        h = [("Content-Type", "application/x-www-form-urlencoded")] if body is not None else []
        h += list(headers)
        custom_host = any(name.lower() == "host" for name, _ in h)
        conn.putrequest(method, path, skip_host=custom_host, skip_accept_encoding=True)
        for name, value in h:
            conn.putheader(name, value)
        data = body.encode("utf-8") if body is not None else b""
        if body is not None:
            conn.putheader("Content-Length", str(len(data)))
        conn.endheaders(data if body is not None else None)
        res = conn.getresponse()
        text = res.read().decode("utf-8")
        conn.close()
        return res, text

    def shorten(self, url, headers=()):
        return self.request("POST", "/shorten", urlencode([("url", url)]), headers)

    def test_index_has_form(self):
        res, text = self.request("GET", "/")
        self.assertEqual(res.status, 200)
        self.assertIn("<form", text)
        self.assertIn("name='url'", text)
        self.assertIn("viewport", text)

    def test_shorten_uses_forwarded_host_behind_proxy(self):
        res, text = self.shorten("https://a.com/very/long/path", headers=[
            ("Host", "localhost:8000"),
            ("X-Forwarded-Host", "abc-8000.app.github.dev"),
            ("X-Forwarded-Proto", "https"),
        ])
        self.assertEqual(res.status, 200)
        self.assertIn("https://abc-8000.app.github.dev/0", text)
        self.assertNotIn("localhost:8000/0", text)

    def test_first_forwarded_value_is_used(self):
        _, text = self.shorten("https://a.com", headers=[
            ("X-Forwarded-Host", "first.example, second.example"),
            ("X-Forwarded-Proto", "https, http"),
        ])
        self.assertIn("https://first.example/0", text)

    def test_shorten_without_proxy_uses_host(self):
        _, text = self.shorten("https://a.com")
        self.assertIn("http://127.0.0.1:%d/0" % self.port, text)

    def test_short_link_redirects(self):
        self.shorten("https://a.com/x?y=1")
        res, _ = self.request("GET", "/0")
        self.assertEqual(res.status, 302)
        self.assertEqual(res.getheader("Location"), "https://a.com/x?y=1")

    def test_same_url_same_link(self):
        _, first = self.shorten("https://a.com")
        _, second = self.shorten("https://a.com")
        self.assertIn("/0'", first)
        self.assertIn("/0'", second)
        self.assertEqual(len(self.app.shortener), 1)

    def test_unknown_code_is_404(self):
        for path in ("/zz", "/00", "/favicon.ico", "/a/b"):
            with self.subTest(path=path):
                res, _ = self.request("GET", path)
                self.assertEqual(res.status, 404)

    def test_invalid_url_is_400(self):
        for bad in ("ftp://a.com", "", "example.com", "https://a b.com"):
            with self.subTest(bad=bad):
                res, text = self.shorten(bad)
                self.assertEqual(res.status, 400)
                self.assertIn("<form", text)
        self.assertEqual(len(self.app.shortener), 0)

    def test_html_is_escaped(self):
        res, text = self.shorten("https://a.com/<script>alert(1)</script>")
        self.assertEqual(res.status, 200)
        self.assertNotIn("<script>alert(1)</script>", text)
        self.assertIn("&lt;script&gt;", text)
        res, text = self.shorten("javascript:<script>alert(1)</script>")
        self.assertEqual(res.status, 400)
        self.assertNotIn("<script>alert(1)</script>", text)

    def test_too_large_body_is_rejected(self):
        res, _ = self.request("POST", "/shorten", "url=" + "a" * 20000)
        self.assertEqual(res.status, 413)

    def test_post_elsewhere_is_404(self):
        res, _ = self.request("POST", "/other", "url=https://a.com")
        self.assertEqual(res.status, 404)

    def test_table_page_shows_chain_and_horner_steps(self):
        self.shorten("https://a.com")
        self.shorten("https://b.com")
        res, text = self.request("GET", "/table", headers=[("X-Forwarded-Host", "abc-8000.app.github.dev"),
                                                           ("X-Forwarded-Proto", "https")])
        self.assertEqual(res.status, 200)
        self.assertIn("개별 체이닝", text)
        self.assertIn("NULL", text)
        self.assertIn("https://a.com", text)
        self.assertIn("https://abc-8000.app.github.dev/1", text)
        self.assertIn("mod 11", text)
        self.assertIn("길이", text)


if __name__ == "__main__":
    unittest.main()
