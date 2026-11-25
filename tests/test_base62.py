import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from base62 import ALPHABET, decode, encode  # noqa: E402


class EncodeTests(unittest.TestCase):
    def test_zero_is_the_digit_zero_not_empty(self):
        self.assertEqual(encode(0), "0")

    def test_alphabet_order_is_digits_lower_upper(self):
        self.assertEqual(ALPHABET[:10], "0123456789")
        self.assertEqual(encode(9), "9")
        self.assertEqual(encode(10), "a")
        self.assertEqual(encode(35), "z")
        self.assertEqual(encode(36), "A")
        self.assertEqual(encode(61), "Z")

    def test_carry_to_second_digit(self):
        self.assertEqual(encode(62), "10")
        self.assertEqual(encode(62 * 62 - 1), "ZZ")
        self.assertEqual(encode(62 * 62), "100")

    def test_large_number(self):
        self.assertEqual(encode(62 ** 10), "1" + "0" * 10)

    def test_negative_is_rejected(self):
        with self.assertRaises(ValueError):
            encode(-1)

    def test_non_integers_are_rejected(self):
        for bad in (1.0, "1", None, True):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    encode(bad)


class DecodeTests(unittest.TestCase):
    def test_single_digits(self):
        self.assertEqual(decode("0"), 0)
        self.assertEqual(decode("a"), 10)
        self.assertEqual(decode("Z"), 61)

    def test_case_matters(self):
        self.assertNotEqual(decode("a"), decode("A"))

    def test_round_trip(self):
        for n in list(range(0, 5000)) + [62 ** 5 - 1, 62 ** 5, 123456789]:
            with self.subTest(n=n):
                self.assertEqual(decode(encode(n)), n)

    def test_empty_is_rejected(self):
        with self.assertRaises(ValueError):
            decode("")

    def test_characters_outside_alphabet_are_rejected(self):
        for bad in ("-", "a b", "abc!", "한글", "a/b", "_"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    decode(bad)

    def test_leading_zero_is_rejected(self):
        for bad in ("00", "01", "0a"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    decode(bad)

    def test_non_strings_are_rejected(self):
        with self.assertRaises(TypeError):
            decode(10)


if __name__ == "__main__":
    unittest.main()
