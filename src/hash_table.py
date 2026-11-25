"""개별 체이닝 해시 테이블.

칸마다 단일 연결 리스트를 두고, 같은 칸으로 온 키는 체인 끝에 붙인다.
해시 함수는 호너 방식 h <- (31*h + ord(c)) mod M 이다.
파이썬 내장 사전·집합·해시 함수는 쓰지 않는다 (SPEC.md 3절).
"""

HORNER_BASE = 31
DEFAULT_CAPACITY = 11
DEFAULT_MAX_LOAD = 0.75


def horner(key, m):
    """호너 방식으로 key의 칸 번호(0 ~ m-1)를 구한다. 빈 문자열은 0."""
    h = 0
    for ch in key:
        h = (HORNER_BASE * h + ord(ch)) % m
    return h


def horner_steps(key, m):
    """호너 계산 과정을 글자마다 (글자, 글자 코드, 이전 h, 새 h)로 돌려준다.

    마지막 항목의 새 h가 칸 번호다. 화면에서 계산 근거를 보여 줄 때 쓴다.
    """
    steps = []
    h = 0
    for ch in key:
        new_h = (HORNER_BASE * h + ord(ch)) % m
        steps.append((ch, ord(ch), h, new_h))
        h = new_h
    return steps


def is_prime(n):
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    d = 3
    while d * d <= n:
        if n % d == 0:
            return False
        d += 2
    return True


def next_prime(n):
    """n 이상인 가장 작은 소수."""
    while not is_prime(n):
        n += 1
    return n


def check_key(key):
    if not isinstance(key, str):
        raise TypeError("키는 문자열이어야 합니다: %r" % (key,))


def check_capacity(capacity):
    if isinstance(capacity, bool) or not isinstance(capacity, int):
        raise TypeError("capacity는 정수여야 합니다: %r" % (capacity,))
    if capacity < 1:
        raise ValueError("capacity는 1 이상이어야 합니다: %d" % capacity)


class _Node:
    __slots__ = ("key", "value", "next")

    def __init__(self, key, value):
        self.key = key
        self.value = value
        self.next = None


class HashTable:
    """개별 체이닝 해시 테이블. 키는 문자열.

    max_load: 새 키를 넣은 뒤 적재율이 이 값을 넘으면 칸 수를 늘린다.
              None이면 늘리지 않는다 (적재율 실험용).
    """

    kind = "chain"

    def __init__(self, capacity=DEFAULT_CAPACITY, max_load=DEFAULT_MAX_LOAD):
        check_capacity(capacity)
        if max_load is not None and not max_load > 0:
            raise ValueError("max_load는 None이거나 양수여야 합니다: %r" % (max_load,))
        self._slots = [None] * capacity
        self._size = 0
        self.max_load = max_load

    # --- 기본 정보 ---
    @property
    def capacity(self):
        return len(self._slots)

    def __len__(self):
        return self._size

    def load_factor(self):
        return self._size / len(self._slots)

    def slot_of(self, key):
        check_key(key)
        return horner(key, len(self._slots))

    # --- 찾기 ---
    def find(self, key):
        """(찾았는가, 값, 비교한 노드 수)."""
        node = self._slots[self.slot_of(key)]
        compared = 0
        while node is not None:
            compared += 1
            if node.key == key:
                return True, node.value, compared
            node = node.next
        return False, None, compared

    def get(self, key, default=None):
        found, value, _ = self.find(key)
        return value if found else default

    def __contains__(self, key):
        return self.find(key)[0]

    # --- 넣기 ---
    def put(self, key, value):
        i = self.slot_of(key)
        node = self._slots[i]
        if node is None:
            self._slots[i] = _Node(key, value)
        else:
            while True:
                if node.key == key:
                    node.value = value  # 이미 있으면 값만 바꾼다
                    return
                if node.next is None:
                    break
                node = node.next
            node.next = _Node(key, value)  # 체인 끝에 붙인다
        self._size += 1
        if self.max_load is not None and self.load_factor() > self.max_load:
            self._grow()

    def _grow(self):
        old = self._slots
        self._slots = [None] * next_prime(2 * len(old))
        self._size = 0
        for head in old:
            node = head
            while node is not None:
                self._put_without_grow(node.key, node.value)
                node = node.next

    def _put_without_grow(self, key, value):
        max_load, self.max_load = self.max_load, None
        try:
            self.put(key, value)
        finally:
            self.max_load = max_load

    # --- 화면 표시용 ---
    def buckets(self):
        """칸마다 [(키, 값), ...] 목록. 체인 순서 그대로."""
        result = []
        for head in self._slots:
            chain = []
            node = head
            while node is not None:
                chain.append((node.key, node.value))
                node = node.next
            result.append(chain)
        return result

    def items(self):
        for chain in self.buckets():
            for pair in chain:
                yield pair
