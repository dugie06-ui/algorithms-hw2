"""선형 탐지 테이블 테스트.

ProbingContractTests: 해시 테이블 공통 테스트(test_hash_table.TableContract)를 선형 탐지에 그대로 돌린다.
ProbingTests: 선형 탐지에만 해당하는 것 (끝 칸 -> 0번 칸, 가득 찬 테이블, 들여다본 칸 수).
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import test_hash_table  # noqa: E402  (클래스를 직접 import하면 체이닝 테스트가 이 파일에서 한 번 더 돈다)
from hash_table import horner  # noqa: E402
from probing_table import ProbingTable  # noqa: E402

# M = 11에서 처음 칸이 10인 키들: ord("b") = 98, ord("m") = 109, ord("x") = 120, 모두 mod 11 = 10
LAST_SLOT_KEYS = ("b", "m", "x")


class ProbingContractTests(test_hash_table.TableContract):
    table_class = ProbingTable


class ProbingTests(unittest.TestCase):
    def test_last_slot_keys(self):
        for k in LAST_SLOT_KEYS:
            self.assertEqual(horner(k, 11), 10)

    def test_same_home_slot_goes_to_next_slot(self):
        t = ProbingTable(capacity=11, max_load=None)
        t.put("a", 1)  # 처음 칸 9
        t.put("l", 2)  # 처음 칸 9 -> 10
        slots = t.slots()
        self.assertEqual(slots[9], ("a", 1))
        self.assertEqual(slots[10], ("l", 2))
        self.assertEqual(t.find("a"), (True, 1, 1))
        self.assertEqual(t.find("l"), (True, 2, 2))

    def test_wraps_from_last_slot_to_slot_zero(self):
        t = ProbingTable(capacity=11, max_load=None)
        t.put("b", 1)
        t.put("m", 2)
        slots = t.slots()
        self.assertEqual(slots[10], ("b", 1))
        self.assertEqual(slots[0], ("m", 2))
        self.assertEqual(t.find("m"), (True, 2, 2))
        self.assertEqual(t.probe_path("m"), [10, 0])

    def test_miss_cost_counts_the_empty_slot_after_wrapping(self):
        """끝 칸에서 0번 칸으로 넘어간 뒤 빈 칸에서 멈춘다."""
        t = ProbingTable(capacity=11, max_load=None)
        t.put("b", 1)
        t.put("m", 2)
        # "x": 10번(b), 0번(m), 1번(빈 칸) -> 3칸
        self.assertEqual(t.find("x"), (False, None, 3))
        self.assertEqual(t.probe_path("x"), [10, 0, 1])
        # "c": 99 % 11 = 0 -> 0번(m), 1번(빈 칸) -> 2칸
        self.assertEqual(t.find("c"), (False, None, 2))
        # "d": 100 % 11 = 1 -> 처음 칸이 비어 있으니 1칸
        self.assertEqual(t.find("d"), (False, None, 1))

    def test_full_table(self):
        t = ProbingTable(capacity=5, max_load=None)
        keys = ["https://a.com/%d" % i for i in range(5)]
        for i, k in enumerate(keys):
            t.put(k, i)
        self.assertEqual(len(t), 5)
        self.assertAlmostEqual(t.load_factor(), 1.0)
        for i, k in enumerate(keys):
            self.assertEqual(t.get(k), i)
        # 없는 키: 모든 칸을 보고 멈춘다 (무한 반복하지 않는다)
        self.assertEqual(t.find("https://없는.키"), (False, None, 5))
        self.assertFalse("https://없는.키" in t)
        # 새 키는 넣을 수 없다
        with self.assertRaises(OverflowError):
            t.put("https://새.키", 99)
        self.assertEqual(len(t), 5)
        # 있는 키의 값 바꾸기는 된다
        t.put(keys[0], "new")
        self.assertEqual(t.get(keys[0]), "new")
        self.assertEqual(len(t), 5)

    def test_single_slot_table(self):
        t = ProbingTable(capacity=1, max_load=None)
        t.put("a", 1)
        with self.assertRaises(OverflowError):
            t.put("b", 2)
        self.assertEqual(t.find("b"), (False, None, 1))

    def test_max_load_must_be_below_one(self):
        for bad in (1, 1.5, 4):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    ProbingTable(max_load=bad)

    def test_default_max_load_keeps_table_at_most_half_full(self):
        t = ProbingTable()
        for i in range(500):
            t.put("https://a.com/%d" % i, i)
            self.assertLessEqual(t.load_factor(), 0.5)
        for i in range(500):
            self.assertEqual(t.get("https://a.com/%d" % i), i)

    def test_every_key_is_reachable_without_gaps(self):
        t = ProbingTable(capacity=101, max_load=None)
        for i in range(90):
            t.put("https://example.com/page/%d" % i, i)
        slots = t.slots()
        for i, slot in enumerate(slots):
            if slot is None:
                continue
            key = slot[0]
            path = t.probe_path(key)
            self.assertEqual(path[0], horner(key, 101))
            self.assertEqual(path[-1], i)
            for j in path[:-1]:
                self.assertIsNotNone(slots[j], "처음 칸과 자기 칸 사이에 빈 칸이 있으면 찾을 수 없다")
            self.assertEqual(t.find(key)[2], len(path))

    def test_kind(self):
        self.assertEqual(ProbingTable().kind, "probe")


if __name__ == "__main__":
    unittest.main()
