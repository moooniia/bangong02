import unittest

from invoice_assistant.uscc import is_valid_uscc


class UsccTest(unittest.TestCase):
    def test_validates_known_codes(self):
        self.assertTrue(is_valid_uscc("91360000158286715E"))
        self.assertTrue(is_valid_uscc("913101011322226179"))
        self.assertTrue(is_valid_uscc("91310112666068482G"))

    def test_rejects_ocr_misread_check_digit(self):
        self.assertFalse(is_valid_uscc("91360000158286715B"))


if __name__ == "__main__":
    unittest.main()

