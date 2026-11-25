"""URL 단축기.

새 URL마다 일련번호를 하나씩 주고, 그 번호를 base62로 바꾼 것을 짧은 코드로 쓴다.
URL의 해시값을 코드로 쓰지 않는다: 서로 다른 URL이 같은 코드를 받을 수 있기 때문이다.
URL->코드, 코드->URL 대응은 직접 만든 해시 테이블 두 개에 저장한다.
테이블은 개별 체이닝(table="chain", 기본)과 선형 탐지(table="probe") 중에서 고른다.
"""

from base62 import encode
from hash_table import HashTable
from probing_table import ProbingTable

MAX_URL_LENGTH = 2048
# 서버 경로와 겹치는 코드는 주지 않는다 (/table)
RESERVED_CODES = ("table",)


def normalize_url(url):
    """올바른 URL이면 앞뒤 공백을 지운 URL을, 아니면 예외를 던진다 (SPEC.md 4절)."""
    if not isinstance(url, str):
        raise TypeError("URL은 문자열이어야 합니다: %r" % (url,))
    url = url.strip()
    if url == "":
        raise ValueError("URL이 비어 있습니다")
    if len(url) > MAX_URL_LENGTH:
        raise ValueError("URL이 너무 깁니다 (%d자, 최대 %d자)" % (len(url), MAX_URL_LENGTH))
    head = url[:8].lower()
    if head.startswith("http://"):
        rest = url[7:]
    elif head.startswith("https://"):
        rest = url[8:]
    else:
        raise ValueError("http:// 또는 https://로 시작해야 합니다")
    if rest == "" or rest[0] in "/?#":
        raise ValueError("호스트가 없습니다")
    for ch in url:
        if ch.isspace() or ord(ch) < 32 or ord(ch) == 127:
            raise ValueError("URL 가운데에 공백이나 제어 문자가 있습니다")
    return url


def table_class(name):
    """"chain" -> 개별 체이닝 HashTable, "probe" -> 선형 탐지 ProbingTable."""
    if name == "chain":
        return HashTable
    if name == "probe":
        return ProbingTable
    raise ValueError('table은 "chain" 또는 "probe"여야 합니다: %r' % (name,))


class Shortener:
    def __init__(self, start=0, table="chain"):
        if isinstance(start, bool) or not isinstance(start, int) or start < 0:
            raise ValueError("start는 0 이상의 정수여야 합니다: %r" % (start,))
        make_table = table_class(table)
        self._next = start
        self._code_of = make_table()  # URL -> 코드
        self._url_of = make_table()  # 코드 -> URL

    @property
    def table(self):
        """URL -> 코드 해시 테이블 (화면 표시용)."""
        return self._code_of

    def __len__(self):
        return len(self._code_of)

    def shorten(self, url):
        """URL의 짧은 코드. 같은 URL에는 언제나 같은 코드를 준다."""
        url = normalize_url(url)
        found, code, _ = self._code_of.find(url)
        if found:
            return code
        code = self._new_code()
        self._code_of.put(url, code)
        self._url_of.put(code, url)
        return code

    def expand(self, code):
        """코드의 원래 URL. 없거나 잘못된 코드면 None."""
        if not isinstance(code, str):
            return None
        return self._url_of.get(code)

    def _new_code(self):
        while True:
            code = encode(self._next)
            self._next += 1
            if code not in RESERVED_CODES:
                return code
