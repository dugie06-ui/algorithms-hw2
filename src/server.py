"""URL 단축기 웹 서버. 표준 http.server만 쓴다.

    make serve                 # http://localhost:8000, 개별 체이닝
    make serve TABLE=probe     # 같은 서버를 선형 탐지 테이블로
    python3 src/server.py --port 8000 --table probe

    GET  /          URL 입력 폼
    POST /shorten   짧은 링크 결과 화면 (잘못된 URL이면 400)
    GET  /<코드>    원래 URL로 302 리디렉션 (없으면 404)
    GET  /table     해시 테이블 시각화: 체인(또는 선형 탐지의 칸)과 호너 해시 계산 과정
"""

import argparse
import html
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qsl

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hash_table import HORNER_BASE, horner, horner_steps  # noqa: E402
from shortener import Shortener  # noqa: E402

MAX_BODY = 16 * 1024

STYLE = """
* { box-sizing: border-box; }
body { margin: 0; font-family: -apple-system, "Segoe UI", "Noto Sans KR", sans-serif;
       color: #111827; background: #f9fafb; line-height: 1.5; }
main { max-width: 960px; margin: 0 auto; padding: 24px 16px 48px; }
h1 { font-size: 1.5rem; margin: 0 0 4px; }
h1 a { color: inherit; text-decoration: none; }
.sub { color: #6b7280; margin: 0 0 20px; font-size: .9rem; }
form { display: flex; gap: 8px; flex-wrap: wrap; }
input[type=text] { flex: 1 1 260px; padding: 12px; font-size: 1rem; border: 1px solid #d1d5db; border-radius: 8px; }
button { padding: 12px 20px; font-size: 1rem; border: 0; border-radius: 8px; background: #2563eb; color: white; }
.card { background: white; border: 1px solid #e5e7eb; border-radius: 12px; padding: 16px; margin: 16px 0; }
.short { font-size: 1.25rem; font-weight: 600; word-break: break-all; }
.long { color: #4b5563; word-break: break-all; font-size: .9rem; }
.error { border-color: #fca5a5; background: #fef2f2; color: #991b1b; }
nav { margin-top: 20px; font-size: .9rem; }
nav a { margin-right: 12px; }
code, .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
.stats { display: flex; gap: 16px; flex-wrap: wrap; font-size: .9rem; color: #374151; }
.row { display: flex; align-items: flex-start; gap: 6px; padding: 6px 0; border-top: 1px solid #f3f4f6; flex-wrap: wrap; }
.idx { min-width: 64px; font-weight: 600; }
.len { color: #6b7280; font-size: .8rem; display: block; font-weight: 400; }
.arrow { color: #9ca3af; padding-top: 6px; }
.null { color: #9ca3af; font-size: .8rem; padding-top: 7px; }
.node { background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 4px 8px; max-width: 320px; font-size: .85rem; }
.node.probe { background: #fff7ed; border-color: #fed7aa; }
.node summary { cursor: pointer; word-break: break-all; }
.node .meta { color: #374151; }
.empty { color: #9ca3af; font-size: .85rem; padding-top: 6px; }
table.steps { border-collapse: collapse; margin-top: 6px; font-size: .8rem; }
table.steps td { padding: 1px 6px; border-bottom: 1px solid #e5e7eb; white-space: nowrap; }
.final { font-weight: 600; margin-top: 4px; }
"""


def page(title, body):
    return ("<!doctype html><html lang='ko'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width, initial-scale=1'>"
            "<title>%s</title><style>%s</style></head><body><main>%s</main></body></html>"
            % (html.escape(title), STYLE, body))


def esc(s):
    return html.escape(str(s), quote=True)


def first_value(header_value):
    """'a, b' 처럼 프록시를 여러 번 거친 헤더에서 첫 번째 값."""
    if not header_value:
        return ""
    return header_value.split(",")[0].strip()


class App:
    """서버가 들고 있는 상태: 단축기와 포트."""

    def __init__(self, shortener, port):
        self.shortener = shortener
        self.port = port

    # --- 화면 ---
    def header(self):
        t = self.shortener.table
        return ("<h1><a href='/'>URL 단축기</a></h1>"
                "<p class='sub'>고급알고리즘 과제2 · 해시 테이블: %s · 저장된 URL %d개</p>"
                % (esc(table_kind_name(t)), len(self.shortener)))

    def form(self, value=""):
        return ("<form method='post' action='/shorten'>"
                "<input type='text' name='url' inputmode='url' autocomplete='off' autocapitalize='off' "
                "spellcheck='false' placeholder='https://로 시작하는 긴 URL' value='%s' required>"
                "<button type='submit'>줄이기</button></form>" % esc(value))

    def nav(self):
        return "<nav><a href='/'>새 URL 줄이기</a><a href='/table'>해시 테이블 보기</a></nav>"

    def index_page(self):
        return page("URL 단축기", self.header() + self.form() + self.nav())

    def result_page(self, url, code, base):
        link = base + "/" + code
        body = (self.header() + "<div class='card'>"
                "<div>짧은 링크</div>"
                "<div class='short'><a href='%s'>%s</a></div>"
                "<div class='long'>원래 URL: %s</div>"
                "<div class='long'>코드 <code>%s</code></div>"
                "</div>" % (esc(link), esc(link), esc(url), esc(code))
                + self.form() + self.nav())
        return page("짧은 링크", body)

    def error_page(self, message, value=""):
        body = (self.header() + "<div class='card error'>%s</div>" % esc(message)
                + self.form(value) + self.nav())
        return page("잘못된 요청", body)

    def not_found_page(self, path):
        body = (self.header() + "<div class='card error'>없는 짧은 링크입니다: <code>%s</code></div>" % esc(path)
                + self.nav())
        return page("찾을 수 없음", body)

    def table_page(self, base):
        t = self.shortener.table
        m = t.capacity
        body = [self.header()]
        body.append("<div class='stats'><span>방식: <b>%s</b></span><span>칸 수 M = <b>%d</b></span>"
                    "<span>키 수 n = <b>%d</b></span><span>적재율 α = n/M = <b>%.3f</b></span></div>"
                    % (esc(table_kind_name(t)), m, len(t), t.load_factor()))
        body.append("<p class='sub'>칸 번호는 호너 방식 <code>h ← (%d·h + 글자 코드) mod %d</code>, 처음 h = 0. "
                    "마지막 h가 칸 번호입니다. 노드를 누르면 계산 과정이 펼쳐집니다.</p>" % (HORNER_BASE, m))
        if getattr(t, "kind", "chain") == "probe":
            body.append("<p class='sub'>선형 탐지: 처음 칸 h가 차 있으면 h+1, h+2, … (mod %d)로 옮겨 가며 빈 칸에 넣습니다. "
                        "마지막 칸 다음은 0번 칸입니다.</p>" % m)
        body.append(render_table(t, base))
        body.append(self.nav())
        return page("해시 테이블", "".join(body))


def table_kind_name(table):
    return "개별 체이닝" if getattr(table, "kind", "chain") == "chain" else "선형 탐지"


def render_steps(key, m):
    rows = ["<table class='steps'>"]
    for ch, code, before, after in horner_steps(key, m):
        rows.append("<tr><td class='mono'>%s</td><td>(%d·%d + %d) mod %d</td><td>= <b>%d</b></td></tr>"
                    % (esc(repr(ch)), HORNER_BASE, before, code, m, after))
    rows.append("</table>")
    rows.append("<div class='final'>→ 칸 %d</div>" % horner(key, m))
    return "".join(rows)


def render_node(key, code, base, m, extra="", css="node"):
    link = base + "/" + code
    return ("<details class='%s'><summary>%s</summary>"
            "<div class='meta'>코드 <code>%s</code> · <a href='%s'>%s</a>%s</div>%s</details>"
            % (css, esc(key), esc(code), esc(link), esc(link), extra, render_steps(key, m)))


def render_chain_table(table, base):
    m = table.capacity
    rows = []
    for i, chain in enumerate(table.buckets()):
        parts = ["<div class='row'><div class='idx'>[%d]<span class='len'>길이 %d</span></div>" % (i, len(chain))]
        for key, code in chain:
            parts.append("<span class='arrow'>→</span>")
            parts.append(render_node(key, code, base, m))
        parts.append("<span class='arrow'>→</span><span class='null'>NULL</span></div>")
        rows.append("".join(parts))
    return "<div class='card'>%s</div>" % "".join(rows)


def render_probe_table(table, base):
    m = table.capacity
    rows = []
    for i, slot in enumerate(table.slots()):
        if slot is None:
            parts = ["<div class='row'><div class='idx'>[%d]</div>" % i]
            parts.append("<span class='empty'>비어 있음</span>")
        else:
            key, code = slot
            path = table.probe_path(key)
            parts = ["<div class='row'><div class='idx'>[%d]<span class='len'>h=%d · %d칸</span></div>"
                     % (i, path[0], len(path))]
            extra = ("<div>처음 칸 h = <b>%d</b> · 들여다본 칸 <b>%d</b>개: %s</div>"
                     % (path[0], len(path), " → ".join("[%d]" % j for j in path)))
            parts.append(render_node(key, code, base, m, extra, "node probe"))
        parts.append("</div>")
        rows.append("".join(parts))
    return "<div class='card'>%s</div>" % "".join(rows)


def render_table(table, base):
    if getattr(table, "kind", "chain") == "probe":
        return render_probe_table(table, base)
    return render_chain_table(table, base)


def make_handler(app, quiet=False):
    class Handler(BaseHTTPRequestHandler):
        server_version = "URLShortener/1.0"

        def log_message(self, fmt, *args):
            if not quiet:
                super().log_message(fmt, *args)

        def base_url(self):
            """짧은 링크 앞부분. 프록시 뒤에서는 X-Forwarded-* 를 먼저 본다."""
            proto = first_value(self.headers.get("X-Forwarded-Proto")).lower()
            if proto not in ("http", "https"):
                proto = "http"
            host = first_value(self.headers.get("X-Forwarded-Host"))
            if not host:
                host = first_value(self.headers.get("Host"))
            if not host:
                host = "localhost:%d" % app.port
            return proto + "://" + host

        def send_html(self, status, body):
            data = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            path = self.path.split("?", 1)[0].split("#", 1)[0]
            if path == "/":
                self.send_html(200, app.index_page())
            elif path == "/table":
                self.send_html(200, app.table_page(self.base_url()))
            else:
                url = app.shortener.expand(path[1:])
                if url is None:
                    self.send_html(404, app.not_found_page(path))
                    return
                self.send_response(302)
                self.send_header("Location", url)
                self.send_header("Content-Length", "0")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()

        def do_POST(self):
            path = self.path.split("?", 1)[0]
            if path != "/shorten":
                self.send_html(404, app.not_found_page(path))
                return
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                length = -1
            if length < 0 or length > MAX_BODY:
                self.send_html(413, app.error_page("요청이 너무 큽니다."))
                return
            raw = self.rfile.read(length).decode("utf-8", errors="replace")
            url = ""
            for name, value in parse_qsl(raw, keep_blank_values=True):
                if name == "url":
                    url = value
                    break
            try:
                code = app.shortener.shorten(url)
            except (ValueError, TypeError) as e:
                self.send_html(400, app.error_page("줄일 수 없는 URL입니다: %s" % e, url))
                return
            self.send_html(200, app.result_page(url.strip(), code, self.base_url()))

    return Handler


def make_server(port=8000, host="0.0.0.0", shortener=None, quiet=False):
    app = App(shortener if shortener is not None else Shortener(), port)
    server = ThreadingHTTPServer((host, port), make_handler(app, quiet))
    app.port = server.server_address[1]
    return server, app


def main(argv=None):
    parser = argparse.ArgumentParser(description="URL 단축기 웹 서버")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--table", choices=("chain", "probe"), default="chain",
                        help="chain: 개별 체이닝, probe: 선형 탐지")
    args = parser.parse_args(argv)
    server, app = make_server(args.port, args.host, Shortener(table=args.table))
    print("URL 단축기: http://localhost:%d  (해시 테이블: %s, 끄려면 Ctrl+C)"
          % (app.port, table_kind_name(app.shortener.table)), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
