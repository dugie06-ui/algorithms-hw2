"""base62 인코딩과 디코딩.

음이 아닌 정수를 0-9, a-z, A-Z 62글자로 된 문자열로 바꾸고 되돌린다.
글자 순서는 0-9, a-z, A-Z 이다. 단축기는 일련번호를 이 문자열로 바꿔 짧은 코드로 쓴다.

    encode(0)   -> "0"
    encode(61)  -> "Z"
    encode(62)  -> "10"
    decode("10") -> 62
"""

ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
BASE = len(ALPHABET)  # 62


def _digit(ch):
    """글자 하나의 값(0~61). 알파벳에 없는 글자면 -1."""
    if "0" <= ch <= "9":
        return ord(ch) - ord("0")
    if "a" <= ch <= "z":
        return ord(ch) - ord("a") + 10
    if "A" <= ch <= "Z":
        return ord(ch) - ord("A") + 36
    return -1


def encode(n):
    """음이 아닌 정수 n을 base62 문자열로 바꾼다.

    0은 빈 문자열이 아니라 "0"이다.
    정수가 아니면 TypeError, 음수면 ValueError.
    """
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError("encode()는 정수만 받습니다: %r" % (n,))
    if n < 0:
        raise ValueError("encode()는 음수를 받지 않습니다: %d" % n)
    if n == 0:
        return ALPHABET[0]
    digits = []
    while n > 0:
        n, r = divmod(n, BASE)
        digits.append(ALPHABET[r])
    digits.reverse()
    return "".join(digits)


def decode(s):
    """base62 문자열 s를 정수로 되돌린다.

    encode()가 만드는 꼴만 받는다. 빈 문자열, 알파벳에 없는 글자,
    "0"이 아닌데 0으로 시작하는 문자열("00", "0a")은 ValueError.
    그래서 decode(encode(n)) == n 이고 encode(decode(s)) == s 이다.
    문자열이 아니면 TypeError.
    """
    if not isinstance(s, str):
        raise TypeError("decode()는 문자열만 받습니다: %r" % (s,))
    if s == "":
        raise ValueError("decode()는 빈 문자열을 받지 않습니다")
    if len(s) > 1 and s[0] == "0":
        raise ValueError("0으로 시작하는 코드는 쓰지 않습니다: %r" % s)
    n = 0
    for ch in s:
        d = _digit(ch)
        if d < 0:
            raise ValueError("base62 글자가 아닙니다: %r" % ch)
        n = n * BASE + d
    return n
