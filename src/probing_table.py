"""선형 탐지(linear probing) 해시 테이블.

HashTable(개별 체이닝)과 같은 인터페이스: put, get, find, len, in, load_factor(), capacity.
같은 호너 해시로 처음 칸 h를 구하고, 차 있으면 h+1, h+2, ... (mod M) 순서로 빈 칸을 찾는다.
칸마다 키 하나만 둔다. find의 비용은 들여다본 칸 수다.
파이썬 내장 사전·집합·해시 함수는 쓰지 않는다 (SPEC.md 7절).
"""

from hash_table import DEFAULT_CAPACITY, check_capacity, check_key, horner, next_prime

DEFAULT_MAX_LOAD = 0.5


class ProbingTable:
    """선형 탐지 해시 테이블. 키는 문자열.

    max_load: None이거나 0 < max_load < 1. 새 키를 넣은 뒤 적재율이 넘으면 칸 수를 늘린다.
              None이면 늘리지 않고, 가득 찬 테이블에 새 키를 넣으면 OverflowError.
    """

    kind = "probe"

    def __init__(self, capacity=DEFAULT_CAPACITY, max_load=DEFAULT_MAX_LOAD):
        check_capacity(capacity)
        if max_load is not None and not 0 < max_load < 1:
            raise ValueError("선형 탐지의 max_load는 None이거나 0과 1 사이여야 합니다: %r" % (max_load,))
        self._keys = [None] * capacity  # None = 빈 칸 (키는 문자열뿐이므로 겹치지 않는다)
        self._values = [None] * capacity
        self._size = 0
        self.max_load = max_load

    # --- 기본 정보 ---
    @property
    def capacity(self):
        return len(self._keys)

    def __len__(self):
        return self._size

    def load_factor(self):
        return self._size / len(self._keys)

    def slot_of(self, key):
        """처음 칸(호너 해시값)."""
        check_key(key)
        return horner(key, len(self._keys))

    def _probe(self, key):
        """(찾았는가, 멈춘 칸 번호 또는 -1, 들여다본 칸 수).

        키를 찾거나 빈 칸을 만나면 멈춘다. M칸을 다 보고도 둘 다 아니면 칸 번호 -1 (가득 참).
        """
        m = len(self._keys)
        i = self.slot_of(key)
        for looked in range(1, m + 1):
            k = self._keys[i]
            if k is None:
                return False, i, looked
            if k == key:
                return True, i, looked
            i = (i + 1) % m
        return False, -1, m

    # --- 찾기 ---
    def find(self, key):
        """(찾았는가, 값, 들여다본 칸 수)."""
        found, i, looked = self._probe(key)
        return found, (self._values[i] if found else None), looked

    def get(self, key, default=None):
        found, value, _ = self.find(key)
        return value if found else default

    def __contains__(self, key):
        return self._probe(key)[0]

    # --- 넣기 ---
    def put(self, key, value):
        found, i, _ = self._probe(key)
        if found:
            self._values[i] = value  # 이미 있으면 값만 바꾼다
            return
        if i < 0:
            raise OverflowError("테이블이 가득 찼습니다 (%d칸)" % len(self._keys))
        self._keys[i] = key
        self._values[i] = value
        self._size += 1
        if self.max_load is not None and self.load_factor() > self.max_load:
            self._grow()

    def _grow(self):
        old_keys, old_values = self._keys, self._values
        m = next_prime(2 * len(old_keys))
        self._keys = [None] * m
        self._values = [None] * m
        self._size = 0
        max_load, self.max_load = self.max_load, None
        try:
            for k, v in zip(old_keys, old_values):
                if k is not None:
                    self.put(k, v)
        finally:
            self.max_load = max_load

    # --- 화면 표시용 ---
    def slots(self):
        """칸마다 (키, 값) 또는 None."""
        return [None if k is None else (k, v) for k, v in zip(self._keys, self._values)]

    def probe_path(self, key):
        """find(key)가 들여다보는 칸 번호를 순서대로."""
        m = len(self._keys)
        start = self.slot_of(key)
        looked = self._probe(key)[2]
        return [(start + j) % m for j in range(looked)]

    def items(self):
        for slot in self.slots():
            if slot is not None:
                yield slot
