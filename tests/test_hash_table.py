"""해시 테이블 테스트.

TableContract: 어떤 충돌 처리 방식이든 지켜야 하는 공통 동작. make_table()로 테이블을 만든다.
    과제에서 선형 탐지 테이블도 이 클래스를 상속해 그대로 돌린다.
ChainingTests: 개별 체이닝에만 해당하는 것 (같은 칸 체인, 비교 노드 수, 적재율 > 1).
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from hash_table import HashTable, horner, horner_steps  # noqa: E402

# M = 11에서 같은 칸(9)으로 가는 두 키: ord("a") = 97, ord("l") = 108, 둘 다 mod 11 = 9
SAME_SLOT_A = "a"
SAME_SLOT_B = "l"


def url(i):
    return "https://example.com/page/%d" % i


class TableContract(unittest.TestCase):
    table_class = HashTable

    def make_table(self, **kwargs):
        return self.table_class(**kwargs)

    # --- 빈 테이블 ---
    def test_empty_table(self):
        t = self.make_table()
        self.assertEqual(len(t), 0)
        self.assertIsNone(t.get("https://a.com"))
        self.assertFalse("https://a.com" in t)
        self.assertEqual(t.load_factor(), 0)
        self.assertEqual(t.find("https://a.com")[:2], (False, None))

    def test_default_capacity_is_11(self):
        self.assertEqual(self.make_table().capacity, 11)

    # --- 넣기, 찾기, 바꾸기 ---
    def test_put_then_get(self):
        t = self.make_table()
        t.put("https://a.com", "0")
        self.assertEqual(t.get("https://a.com"), "0")
        self.assertTrue("https://a.com" in t)
        self.assertEqual(len(t), 1)

    def test_get_default(self):
        t = self.make_table()
        self.assertEqual(t.get("없는 키", "기본값"), "기본값")

    def test_put_same_key_updates_value_and_keeps_size(self):
        t = self.make_table()
        t.put("https://a.com", "0")
        t.put("https://a.com", "1")
        self.assertEqual(t.get("https://a.com"), "1")
        self.assertEqual(len(t), 1)

    def test_value_none_is_still_found(self):
        t = self.make_table()
        t.put("k", None)
        found, value, _ = t.find("k")
        self.assertTrue(found)
        self.assertIsNone(value)
        self.assertTrue("k" in t)

    def test_keys_in_same_slot_are_both_found(self):
        t = self.make_table(capacity=11, max_load=None)
        self.assertEqual(horner(SAME_SLOT_A, 11), horner(SAME_SLOT_B, 11))
        t.put(SAME_SLOT_A, 1)
        t.put(SAME_SLOT_B, 2)
        self.assertEqual(t.get(SAME_SLOT_A), 1)
        self.assertEqual(t.get(SAME_SLOT_B), 2)
        self.assertEqual(len(t), 2)

    def test_find_returns_found_value_and_positive_cost(self):
        t = self.make_table()
        t.put("https://a.com", "0")
        found, value, cost = t.find("https://a.com")
        self.assertEqual((found, value), (True, "0"))
        self.assertGreaterEqual(cost, 1)
        found, value, cost = t.find("https://b.com")
        self.assertEqual((found, value), (False, None))
        self.assertGreaterEqual(cost, 0)

    # --- 특이한 키 ---
    def test_empty_string_key(self):
        t = self.make_table()
        t.put("", "empty")
        self.assertEqual(t.get(""), "empty")
        self.assertTrue("" in t)

    def test_korean_key(self):
        t = self.make_table()
        t.put("https://예시.한국/경로", "k")
        self.assertEqual(t.get("https://예시.한국/경로"), "k")

    def test_very_long_key(self):
        t = self.make_table()
        key = "https://a.com/" + "x" * 10000
        t.put(key, "long")
        self.assertEqual(t.get(key), "long")
        self.assertIsNone(t.get(key + "y"))

    def test_non_string_key_is_rejected(self):
        t = self.make_table()
        for bad in (1, None, 1.5, ("a",), b"https://a.com"):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    t.put(bad, "x")
                with self.assertRaises(TypeError):
                    t.get(bad)

    # --- 적재율과 늘리기 ---
    def test_load_factor(self):
        t = self.make_table(capacity=11, max_load=None)
        for i in range(5):
            t.put(url(i), i)
        self.assertAlmostEqual(t.load_factor(), 5 / 11)

    def test_grows_when_load_factor_exceeds_max_load(self):
        t = self.make_table(capacity=11, max_load=0.75)
        for i in range(8):
            t.put(url(i), i)
        self.assertEqual(t.capacity, 11)  # 8/11 = 0.727 <= 0.75
        t.put(url(8), 8)  # 9/11 = 0.818 > 0.75
        self.assertGreater(t.capacity, 11)
        self.assertLessEqual(t.load_factor(), 0.75)
        for i in range(9):
            self.assertEqual(t.get(url(i)), i)
        self.assertEqual(len(t), 9)

    def test_does_not_grow_without_max_load(self):
        t = self.make_table(capacity=11, max_load=None)
        for i in range(10):
            t.put(url(i), i)
        self.assertEqual(t.capacity, 11)
        for i in range(10):
            self.assertEqual(t.get(url(i)), i)

    def test_updating_does_not_grow(self):
        t = self.make_table(capacity=11, max_load=0.75)
        for i in range(8):
            t.put(url(i), i)
        for i in range(8):
            t.put(url(i), i + 100)
        self.assertEqual(t.capacity, 11)
        self.assertEqual(len(t), 8)

    def test_many_keys(self):
        t = self.make_table()
        for i in range(2000):
            t.put(url(i), i)
        self.assertEqual(len(t), 2000)
        for i in range(2000):
            self.assertEqual(t.get(url(i)), i)
        self.assertFalse(url(2000) in t)

    # --- 잘못된 설정 ---
    def test_invalid_capacity(self):
        for bad in (0, -1, 1.5, "11"):
            with self.subTest(bad=bad):
                with self.assertRaises((ValueError, TypeError)):
                    self.make_table(capacity=bad)

    def test_invalid_max_load(self):
        for bad in (0, -0.5):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    self.make_table(max_load=bad)


class HornerTests(unittest.TestCase):
    def test_hand_calculated(self):
        # "ab", M = 11: h = (31*0 + 97) % 11 = 9, h = (31*9 + 98) % 11 = 377 % 11 = 3
        self.assertEqual(horner("ab", 11), 3)
        self.assertEqual(horner("ab", 11), (31 * 97 + 98) % 11)

    def test_empty_string_is_slot_zero(self):
        self.assertEqual(horner("", 11), 0)

    def test_always_in_range(self):
        for i in range(500):
            self.assertTrue(0 <= horner(url(i), 4093) < 4093)

    def test_same_every_time(self):
        self.assertEqual(horner("https://a.com", 4093), horner("https://a.com", 4093))

    def test_steps_end_at_slot(self):
        steps = horner_steps("ab", 11)
        self.assertEqual(len(steps), 2)
        # (글자, 글자 코드, 이전 h, 새 h)
        self.assertEqual(steps[0], ("a", 97, 0, 9))
        self.assertEqual(steps[1], ("b", 98, 9, 3))
        self.assertEqual(steps[-1][3], horner("ab", 11))
        self.assertEqual(horner_steps("", 11), [])


class ChainingTests(unittest.TestCase):
    def test_same_slot_keys_form_a_chain_in_insert_order(self):
        t = HashTable(capacity=11, max_load=None)
        t.put(SAME_SLOT_A, 1)
        t.put(SAME_SLOT_B, 2)
        buckets = t.buckets()
        self.assertEqual(len(buckets), 11)
        self.assertEqual(buckets[9], [(SAME_SLOT_A, 1), (SAME_SLOT_B, 2)])
        self.assertEqual(sum(len(b) for b in buckets), 2)

    def test_find_cost_counts_compared_nodes(self):
        t = HashTable(capacity=11, max_load=None)
        t.put(SAME_SLOT_A, 1)
        t.put(SAME_SLOT_B, 2)
        self.assertEqual(t.find(SAME_SLOT_A), (True, 1, 1))
        self.assertEqual(t.find(SAME_SLOT_B), (True, 2, 2))
        # "w" = 119, 119 % 11 = 9: 같은 칸이지만 없는 키 -> 체인 전체(2개)와 비교
        self.assertEqual(t.find("w"), (False, None, 2))
        # "b" = 98, 98 % 11 = 10: 빈 칸 -> 비교 0번
        self.assertEqual(t.find("b"), (False, None, 0))

    def test_load_factor_can_exceed_one_without_max_load(self):
        t = HashTable(capacity=11, max_load=None)
        for i in range(44):
            t.put(url(i), i)
        self.assertEqual(t.capacity, 11)
        self.assertAlmostEqual(t.load_factor(), 4.0)
        for i in range(44):
            self.assertEqual(t.get(url(i)), i)

    def test_grows_to_smallest_prime_at_least_double(self):
        t = HashTable(capacity=11, max_load=0.75)
        for i in range(9):
            t.put(url(i), i)
        self.assertEqual(t.capacity, 23)
        for i in range(9, 18):
            t.put(url(i), i)
        self.assertEqual(t.capacity, 47)


if __name__ == "__main__":
    unittest.main()
