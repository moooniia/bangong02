import unittest
from pathlib import Path

from invoice_assistant.field_parser import build_record_from_ocr_lines
from invoice_assistant.ocr import OcrLine


class FieldParserTest(unittest.TestCase):
    def test_accepts_clear_date_when_ocr_reads_day_marker_as_box(self):
        record = build_record_from_ocr_lines(
            1,
            Path("date.pdf"),
            [OcrLine("开整日期：2026年03月06口", 0.74, 0.85, 0.18, 0.02)],
        )

        self.assertEqual(record.invoice_date, "2026-03-06")

    def test_joins_right_side_branch_without_turning_it_into_buyer(self):
        record = build_record_from_ocr_lines(
            1,
            Path("telecom.pdf"),
            [
                OcrLine("江西地质工程勘察院上海分院", 0.08, 0.72, 0.28, 0.03),
                OcrLine("913101097590284041", 0.26, 0.65, 0.18, 0.03),
                OcrLine("中国电信股份有限公司", 0.55, 0.72, 0.20, 0.03),
                OcrLine("上海分公司", 0.76, 0.72, 0.10, 0.03),
                OcrLine("91310115671143758E", 0.72, 0.65, 0.20, 0.03),
            ],
        )

        self.assertEqual(record.buyer_name, "江西地质工程勘察院上海分院")
        self.assertEqual(record.seller_name, "中国电信股份有限公司上海分公司")
        self.assertEqual(record.seller_tax, "91310115671143758E")

    def test_uses_pdf_word_coordinates_instead_of_merged_block_order(self):
        record = build_record_from_ocr_lines(
            1,
            Path("25317000002224327183.pdf"),
            [
                OcrLine("江西省勘察设计研究院上海分院", 0.117, 0.733, 0.184, 0.02),
                OcrLine("913101097590284041", 0.294, 0.664, 0.142, 0.02),
                OcrLine("上海圆迈贸易有限公司", 0.585, 0.733, 0.131, 0.02),
                OcrLine("91310114666025597Y", 0.761, 0.664, 0.142, 0.02),
                OcrLine("上海圆迈贸易有限公司 江西省勘察设计研究院上海分院", 0.117, 0.732, 0.599, 0.02),
                OcrLine("91310114666025597Y 913101097590284041", 0.294, 0.664, 0.609, 0.02),
            ],
        )

        self.assertEqual(record.buyer_name, "江西省勘察设计研究院上海分院")
        self.assertEqual(record.buyer_tax, "913101097590284041")
        self.assertEqual(record.seller_name, "上海圆迈贸易有限公司")
        self.assertEqual(record.seller_tax, "91310114666025597Y")

    def test_does_not_use_seller_bank_note_as_seller_name(self):
        record = build_record_from_ocr_lines(
            1,
            Path("25322000000553138831.pdf"),
            [
                OcrLine("江西省勘察设计研究院上海分院", 0.095, 0.736, 0.212, 0.02),
                OcrLine("913101097590284041", 0.257, 0.655, 0.218, 0.03),
                OcrLine("睢宁县厚润家具店（个体工商户）", 0.571, 0.736, 0.227, 0.02),
                OcrLine("92320324MA1X0CUM25", 0.736, 0.655, 0.218, 0.03),
                OcrLine("销方开户银行:中国工商银行宿迁市徐淮路支行; 银行账号:6222021116014882677", 0.053, 0.207, 0.60, 0.04),
            ],
        )

        self.assertEqual(record.seller_name, "睢宁县厚润家具店（个体工商户）")
        self.assertNotIn("中国工商银行", record.seller_name)

    def test_standard_two_column_invoice_keeps_full_buyer_branch_name(self):
        record = build_record_from_ocr_lines(
            1,
            Path("25332000000525940737.pdf"),
            [
                OcrLine("购买方信息", 0.0325, 0.72, 0.03, 0.08),
                OcrLine("销售方信息", 0.5075, 0.72, 0.03, 0.08),
                OcrLine("江西省勘察设计研究院上海分院", 0.099, 0.67, 0.28, 0.03),
                OcrLine("金华市金东区简约工艺品厂", 0.58, 0.67, 0.25, 0.03),
                OcrLine("913101097590284041", 0.26, 0.63, 0.18, 0.03),
                OcrLine("92330703MA2E816H7J", 0.70, 0.63, 0.20, 0.03),
                OcrLine("江西省勘察设计研究院上海分院 金华市金东区简约工艺品厂", 0.099, 0.67, 0.70, 0.03),
                OcrLine("913101097590284041 92330703MA2E816H7J", 0.2608, 0.63, 0.48, 0.03),
                OcrLine("开票日期：2025年11月19日", 0.74, 0.88, 0.20, 0.02),
                OcrLine("（小写）¥234.32", 0.70, 0.28, 0.15, 0.02),
            ],
        )

        self.assertEqual(record.buyer_name, "江西省勘察设计研究院上海分院")
        self.assertEqual(record.buyer_tax, "913101097590284041")
        self.assertEqual(record.seller_name, "金华市金东区简约工艺品厂")
        self.assertEqual(record.seller_tax, "92330703MA2E816H7J")

    def test_keeps_left_buyer_and_right_seller_on_standard_digital_invoice(self):
        record = build_record_from_ocr_lines(
            1,
            Path("25317000000004086103.pdf"),
            [
                OcrLine("江西省勘察设计研究院有限公司", 0.095, 0.736, 0.212, 0.023),
                OcrLine("91360000158286715E", 0.255, 0.653, 0.218, 0.034),
                OcrLine("上海建科检验有限公司", 0.571, 0.736, 0.151, 0.023),
                OcrLine("91310112666068482G", 0.733, 0.653, 0.218, 0.034),
                OcrLine("电子发票（增值税专用发票） 发票号码：25317000000004086103", 0.272, 0.892, 0.69, 0.05),
                OcrLine("开票日期：2025年07月09日", 0.736, 0.854, 0.18, 0.023),
                OcrLine("（小写）￥1700.00", 0.68, 0.274, 0.18, 0.03),
            ],
        )

        self.assertEqual(record.buyer_name, "江西省勘察设计研究院有限公司")
        self.assertEqual(record.buyer_tax, "91360000158286715E")
        self.assertEqual(record.seller_name, "上海建科检验有限公司")
        self.assertEqual(record.seller_tax, "91310112666068482G")

    def test_strips_damaged_name_label_prefixes_from_party_names(self):
        record = build_record_from_ocr_lines(
            1,
            Path("photo.jpg"),
            [
                OcrLine("林：江西省勘察设计研究院有限公司", 0.095, 0.736, 0.24, 0.023),
                OcrLine("统一社会信用代码/纳税人识别号：91360000158286715E", 0.055, 0.653, 0.38, 0.034),
                OcrLine("桥：上海浦东华海加油站有限公司", 0.571, 0.736, 0.22, 0.023),
                OcrLine("统一社会信用代码/纳税人识别号：91310115133504376H", 0.733, 0.653, 0.22, 0.034),
                OcrLine("开票日期：2022年06月14日", 0.736, 0.854, 0.18, 0.023),
                OcrLine("（小写）￥253.31", 0.68, 0.274, 0.18, 0.03),
            ],
        )

        self.assertEqual(record.buyer_name, "江西省勘察设计研究院有限公司")
        self.assertEqual(record.seller_name, "上海浦东华海加油站有限公司")
        self.assertNotIn("林：", record.buyer_name)
        self.assertNotIn("桥：", record.seller_name)

    def test_identifies_ordinary_vat_invoice_type(self):
        record = build_record_from_ocr_lines(
            1,
            Path("ordinary.pdf"),
            [OcrLine("上海增值税普通发票", 0.30, 0.90, 0.30, 0.03)],
        )

        self.assertEqual(record.invoice_type, "增值税普通发票")

    def test_infers_common_tax_rate_from_clear_amounts(self):
        record = build_record_from_ocr_lines(
            1,
            Path("legacy.pdf"),
            [
                OcrLine("￥1081.08", 0.60, 0.45, 0.10, 0.02),
                OcrLine("￥137.90", 0.75, 0.45, 0.10, 0.02),
                OcrLine("￥1218.98", 0.70, 0.25, 0.10, 0.02),
            ],
        )

        self.assertEqual(record.tax_rate, "13%")

    def test_marks_star_tax_invoice_as_exempt_instead_of_blank(self):
        record = build_record_from_ocr_lines(
            1,
            Path("telecom.pdf"),
            [
                OcrLine("电子发票（普通发票）", 0.30, 0.90, 0.35, 0.03),
                OcrLine("￥147.00", 0.60, 0.45, 0.10, 0.02),
                OcrLine("*", 0.75, 0.45, 0.02, 0.02),
                OcrLine("*", 0.85, 0.45, 0.02, 0.02),
                OcrLine("（小写）￥147.00", 0.70, 0.25, 0.15, 0.02),
            ],
        )

        self.assertEqual(record.tax_rate, "免税")
        self.assertEqual(record.tax_amount, "0.00")
        self.assertEqual(record.pretax_amount, "147.00")

    def test_personal_buyer_tax_is_explicitly_not_applicable(self):
        record = build_record_from_ocr_lines(
            1,
            Path("personal.pdf"),
            [OcrLine("名称：个人", 0.08, 0.72, 0.12, 0.02)],
        )

        self.assertEqual(record.buyer_tax, "个人无税号")
        self.assertNotIn("buyer_tax", record.fields_needing_review)

    def test_splits_paired_digital_invoice_tax_numbers(self):
        record = build_record_from_ocr_lines(
            1,
            Path("digital.pdf"),
            [
                OcrLine("北京京东工业品贸易有限公司 江西省勘察设计研究院上海分院", 0.12, 0.74, 0.70, 0.02),
                OcrLine("91110400MA029M4P80 913101097590284041", 0.29, 0.66, 0.50, 0.02),
                OcrLine("开票日期：2025年10月29日", 0.75, 0.87, 0.20, 0.02),
                OcrLine("（小写）¥747.00", 0.29, 0.28, 0.20, 0.02),
            ],
        )

        self.assertEqual(record.seller_tax, "91110400MA029M4P80")
        self.assertEqual(record.buyer_tax, "913101097590284041")
        self.assertNotIn("seller_tax", record.fields_needing_review)

    def test_preserves_parentheses_inside_company_name(self):
        record = build_record_from_ocr_lines(
            1,
            Path("taxi.pdf"),
            [
                OcrLine("名称：江西省勘察设计研究院上海分院", 0.05, 0.78, 0.42, 0.02),
                OcrLine("名称：享道出行（上海）科技股份有限公司", 0.53, 0.78, 0.42, 0.02),
                OcrLine("913101097590284041 91310115MA1K427762", 0.05, 0.74, 0.85, 0.02),
                OcrLine("开票日期：2025年12月05日", 0.74, 0.88, 0.20, 0.02),
                OcrLine("（小写）¥21.71", 0.09, 0.20, 0.20, 0.02),
            ],
        )

        self.assertEqual(record.seller_name, "享道出行（上海）科技股份有限公司")
        self.assertNotIn("seller_name", record.fields_needing_review)

    def test_accepts_standard_invoice_item_with_two_stars(self):
        record = build_record_from_ocr_lines(
            1,
            Path("good.jpg"),
            [
                OcrLine("*生产生活服务*计量校准", 0.03, 0.65, 0.14, 0.02),
                OcrLine("名称：江西省勘察设计研究院有限公司", 0.07, 0.71, 0.22, 0.01),
                OcrLine("统一社会信用代码/纳税人识别号：91360000158286715E", 0.06, 0.68, 0.37, 0.02),
                OcrLine("名称：上海建科检验检测认证有限公司", 0.49, 0.70, 0.23, 0.02),
                OcrLine("统一社会信用代码/纳税人识别号：91310112666068482G", 0.49, 0.67, 0.39, 0.02),
                OcrLine("（小写）￥700.00", 0.62, 0.54, 0.11, 0.01),
            ],
        )

        self.assertEqual(record.line_items, "*生产生活服务*计量校准")
        self.assertNotIn("line_items", record.fields_needing_review)

    def test_distorted_buyer_area_keeps_buyer_blank_but_uses_clear_seller(self):
        record = build_record_from_ocr_lines(
            1,
            Path("distorted.jpg"),
            [
                OcrLine("发票号码：23312000000019893895", 0.76, 0.71, 0.18, 0.05),
                OcrLine("开票日期：2023年05月22日", 0.76, 0.69, 0.15, 0.04),
                OcrLine("以西省勘察设计研究院有限公司（旦|每部之坊）", 0.19, 0.67, 0.28, 0.03),
                OcrLine("，一社会信用代码/夠税人识别号：91360000158286715B", 0.16, 0.60, 0.37, 0.05),
                OcrLine("名称：上海国际招标有限公司", 0.58, 0.62, 0.17, 0.05),
                OcrLine("统一社会信用代码/纳税人识别号：913101011322226179", 0.58, 0.53, 0.35, 0.07),
                OcrLine("（小写）¥5000.00", 0.70, 0.24, 0.10, 0.02),
                OcrLine("¥283.02", 0.90, 0.27, 0.04, 0.01),
            ],
        )

        self.assertEqual(record.seller_name, "上海国际招标有限公司")
        self.assertEqual(record.seller_tax, "913101011322226179")
        self.assertEqual(record.invoice_date, "2023-05-22")
        self.assertEqual(record.total_amount, "5000.00")
        self.assertEqual(record.tax_amount, "283.02")
        self.assertEqual(record.pretax_amount, "4716.98")
        self.assertEqual(record.line_items, "")
        self.assertEqual(record.buyer_name, "")
        self.assertEqual(record.buyer_tax, "")
        self.assertIn("buyer_name", record.fields_needing_review)
        self.assertIn("buyer_tax", record.fields_needing_review)
        self.assertNotIn("line_items", record.fields_needing_review)


if __name__ == "__main__":
    unittest.main()
