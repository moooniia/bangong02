import unittest

from invoice_assistant.safe_party_parser import parse_party_fields


class SafePartyParserTest(unittest.TestCase):
    def test_leaves_seller_blank_when_only_buyer_area_is_clear(self):
        parsed = parse_party_fields(
            [
                "购买方信息",
                "名称：上海测试科技有限公司",
                "统一社会信用代码：91310000MA1TEST001",
                "销方信息",
                "名 称：",  # Distorted or unreadable seller name.
            ]
        )

        self.assertEqual(parsed.buyer_name, "上海测试科技有限公司")
        self.assertEqual(parsed.buyer_tax, "91310000MA1TEST001")
        self.assertIsNone(parsed.seller_name)
        self.assertIn("seller_name", parsed.fields_needing_review)

    def test_empty_seller_area_does_not_reuse_buyer_value(self):
        parsed = parse_party_fields(
            [
                "购买方信息",
                "名称：上海测试科技有限公司",
                "纳税人识别号：91310000MA1TEST001",
                "销售方信息",
                "名称：",
                "纳税人识别号：",
            ]
        )

        self.assertEqual(parsed.buyer_name, "上海测试科技有限公司")
        self.assertIsNone(parsed.seller_name)
        self.assertIsNone(parsed.seller_tax)
        self.assertIn("seller_name", parsed.fields_needing_review)
        self.assertIn("seller_tax", parsed.fields_needing_review)

    def test_accepts_seller_only_from_explicit_seller_section(self):
        parsed = parse_party_fields(
            [
                "购买方信息",
                "名称：上海测试科技有限公司",
                "纳税人识别号：91310000MA1TEST001",
                "销售方信息",
                "名称：北京开票服务有限公司",
                "纳税人识别号：91110000MA1SELL001",
            ]
        )

        self.assertEqual(parsed.buyer_name, "上海测试科技有限公司")
        self.assertEqual(parsed.seller_name, "北京开票服务有限公司")
        self.assertEqual(parsed.seller_tax, "91110000MA1SELL001")
        self.assertNotIn("seller_name", parsed.fields_needing_review)

    def test_clears_seller_when_it_matches_buyer(self):
        parsed = parse_party_fields(
            [
                "购买方名称：上海测试科技有限公司",
                "销售方名称：上海测试科技有限公司",
                "购买方统一社会信用代码：91310000MA1TEST001",
                "销售方统一社会信用代码：91310000MA1TEST001",
            ]
        )

        self.assertEqual(parsed.buyer_name, "上海测试科技有限公司")
        self.assertIsNone(parsed.seller_name)
        self.assertIsNone(parsed.seller_tax)
        self.assertIn("seller_name", parsed.fields_needing_review)
        self.assertIn("seller_tax", parsed.fields_needing_review)

    def test_does_not_invent_seller_from_unowned_name(self):
        parsed = parse_party_fields(
            [
                "名称：上海测试科技有限公司",
                "纳税人识别号：91310000MA1TEST001",
                "金额：100.00",
            ]
        )

        self.assertIsNone(parsed.buyer_name)
        self.assertIsNone(parsed.seller_name)
        self.assertIn("buyer_name", parsed.fields_needing_review)
        self.assertIn("seller_name", parsed.fields_needing_review)


if __name__ == "__main__":
    unittest.main()
