import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from invoice_assistant.field_parser import _amounts_from_pdf_table
from invoice_assistant.models import InvoiceRecord
from invoice_assistant.ocr import OcrLine
from invoice_assistant.record_builder import (
    _enrich_consistent_party_fields,
    _enrich_exact_duplicate_fields,
    _validate_final_records,
    scan_invoice_files,
)


class RecordBuilderScanTest(unittest.TestCase):
    def test_fills_only_unambiguous_party_values_learned_in_same_batch(self):
        known = InvoiceRecord(row_id=1, original_path="1.pdf", original_name="1.pdf", seller_name="示例销售有限公司", seller_tax="91310115MA1234567X")
        missing_name = InvoiceRecord(row_id=2, original_path="2.pdf", original_name="2.pdf", seller_tax="91310115MA1234567X")
        missing_name.add_review("seller_name", "missing")
        missing_tax = InvoiceRecord(row_id=3, original_path="3.pdf", original_name="3.pdf", seller_name="示例销售有限公司")
        missing_tax.add_review("seller_tax", "missing")

        _enrich_consistent_party_fields([known, missing_name, missing_tax])

        self.assertEqual(missing_name.seller_name, "示例销售有限公司")
        self.assertEqual(missing_tax.seller_tax, "91310115MA1234567X")
        self.assertNotIn("seller_name", missing_name.fields_needing_review)
        self.assertNotIn("seller_tax", missing_tax.fields_needing_review)

    def test_exact_duplicate_clears_missing_review_after_reliable_fill(self):
        clean = InvoiceRecord(
            row_id=1,
            original_path="clean.pdf",
            original_name="clean.pdf",
            buyer_name="江西省勘察设计研究院上海分院",
            buyer_tax="913101097590284041",
            seller_name="上海浦东华海加油站有限公司",
            seller_tax="91310115133504376H",
            invoice_date="2022-01-29",
            pretax_amount="198.54",
            tax_amount="25.81",
            total_amount="224.35",
            tax_rate="13%",
            invoice_type="增值税专用发票",
            invoice_no="53846199",
            status="已确认",
        )
        photo = InvoiceRecord(
            row_id=2,
            original_path="photo.jpg",
            original_name="photo.jpg",
            buyer_name="江西省勘察设计研究院上海分院",
            buyer_tax="913101097590284041",
            invoice_date="2022-01-29",
            total_amount="224.35",
            tax_rate="13%",
            invoice_type="增值税专用发票",
            invoice_no="53846199",
        )
        photo.add_review("seller_name", "未能明确识别销售方名称")
        photo.add_review("seller_tax", "最终复查：销售方税号为空")
        photo.add_review("pretax_amount", "最终复查：不含税金额为空")
        photo.add_review("tax_amount", "最终复查：税额为空")

        _enrich_exact_duplicate_fields([clean, photo])
        _validate_final_records([clean, photo])

        self.assertEqual(photo.seller_name, "上海浦东华海加油站有限公司")
        self.assertEqual(photo.seller_tax, "91310115133504376H")
        self.assertEqual(photo.pretax_amount, "198.54")
        self.assertEqual(photo.tax_amount, "25.81")
        self.assertNotIn("seller_name", photo.fields_needing_review)
        self.assertNotIn("seller_tax", photo.fields_needing_review)
        self.assertNotIn("pretax_amount", photo.fields_needing_review)
        self.assertNotIn("tax_amount", photo.fields_needing_review)
        self.assertEqual(photo.status, "已确认")

    def test_photo_amount_formula_conflict_blanks_suspect_numbers(self):
        record = InvoiceRecord(
            row_id=1,
            original_path="hard-photo.jpg",
            original_name="hard-photo.jpg",
            buyer_name="江西省勘察设计研究院上海分院",
            buyer_tax="913101097590284041",
            seller_name="上海浦东华海加油站有限公司",
            seller_tax="91310115133504376H",
            invoice_date="2022-01-29",
            pretax_amount="168.15",
            tax_amount="30.39",
            total_amount="198.54",
            tax_rate="13%",
            invoice_type="增值税专用发票",
            invoice_no="53846199",
        )

        _validate_final_records([record])

        self.assertEqual(record.pretax_amount, "")
        self.assertEqual(record.tax_amount, "")
        self.assertEqual(record.total_amount, "")
        self.assertEqual(record.tax_rate, "")
        self.assertIn("pretax_amount", record.fields_needing_review)
        self.assertIn("tax_amount", record.fields_needing_review)
        self.assertIn("total_amount", record.fields_needing_review)
        self.assertIn("tax_rate", record.fields_needing_review)
        self.assertEqual(record.status, "需人工确认")

    def test_final_validation_never_confirms_an_empty_required_field(self):
        record = InvoiceRecord(
            row_id=1,
            original_path="1.pdf",
            original_name="1.pdf",
            buyer_name="测试购买方",
            buyer_tax="91310115MA1234567X",
            seller_name="",
            seller_tax="91310115MA7654321X",
            invoice_date="2026-07-12",
            pretax_amount="88.50",
            tax_amount="11.50",
            total_amount="100.00",
            tax_rate="13%",
            invoice_type="增值税电子发票",
            invoice_no="26310000000000000001",
            status="已确认",
        )

        _validate_final_records([record])

        self.assertIn("seller_name", record.fields_needing_review)
        self.assertEqual(record.status, "需人工确认")

    def test_final_validation_never_confirms_empty_amount_fields(self):
        record = InvoiceRecord(
            row_id=1,
            original_path="1.pdf",
            original_name="1.pdf",
            buyer_name="江西省勘察设计研究院有限公司",
            buyer_tax="91360000158286715E",
            seller_name="上海建科检验有限公司",
            seller_tax="91310112666068482G",
            invoice_date="2026-07-12",
            total_amount="113.00",
            tax_rate="13%",
            invoice_type="增值税电子发票",
            invoice_no="26310000000000000001",
            status="已确认",
        )

        _validate_final_records([record])

        self.assertIn("pretax_amount", record.fields_needing_review)
        self.assertIn("tax_amount", record.fields_needing_review)
        self.assertEqual(record.status, "需人工确认")

    def test_final_validation_confirms_complete_consistent_amounts(self):
        record = InvoiceRecord(
            row_id=1,
            original_path="1.pdf",
            original_name="1.pdf",
            buyer_name="江西省勘察设计研究院有限公司",
            buyer_tax="91360000158286715E",
            seller_name="上海建科检验有限公司",
            seller_tax="91310112666068482G",
            invoice_date="2026-07-12",
            pretax_amount="100.00",
            tax_amount="13.00",
            total_amount="113.00",
            tax_rate="13%",
            invoice_type="增值税电子发票",
            invoice_no="26310000000000000001",
            status="需人工确认",
        )

        _validate_final_records([record])

        self.assertEqual(record.fields_needing_review, set())
        self.assertEqual(record.status, "已确认")

    def test_final_validation_flags_amount_formula_mismatch(self):
        record = InvoiceRecord(
            row_id=1,
            original_path="1.pdf",
            original_name="1.pdf",
            buyer_name="江西省勘察设计研究院有限公司",
            buyer_tax="91360000158286715E",
            seller_name="上海建科检验有限公司",
            seller_tax="91310112666068482G",
            invoice_date="2026-07-12",
            pretax_amount="100.00",
            tax_amount="12.00",
            total_amount="113.00",
            tax_rate="13%",
            invoice_type="增值税电子发票",
            invoice_no="26310000000000000001",
            status="已确认",
        )

        _validate_final_records([record])

        self.assertIn("tax_amount", record.fields_needing_review)
        self.assertIn("tax_rate", record.fields_needing_review)
        self.assertEqual(record.status, "需人工确认")

    def test_final_validation_flags_uncommon_tax_rate(self):
        record = InvoiceRecord(
            row_id=1,
            original_path="1.pdf",
            original_name="1.pdf",
            buyer_name="江西省勘察设计研究院有限公司",
            buyer_tax="91360000158286715E",
            seller_name="上海建科检验有限公司",
            seller_tax="91310112666068482G",
            invoice_date="2026-07-12",
            pretax_amount="100.00",
            tax_amount="7.00",
            total_amount="107.00",
            tax_rate="7%",
            invoice_type="增值税电子发票",
            invoice_no="26310000000000000001",
            status="已确认",
        )

        _validate_final_records([record])

        self.assertIn("tax_rate", record.fields_needing_review)
        self.assertEqual(record.status, "需人工确认")

    def test_final_validation_flags_negative_amount(self):
        record = InvoiceRecord(
            row_id=1,
            original_path="1.pdf",
            original_name="1.pdf",
            buyer_name="江西省勘察设计研究院有限公司",
            buyer_tax="91360000158286715E",
            seller_name="上海建科检验有限公司",
            seller_tax="91310112666068482G",
            invoice_date="2026-07-12",
            pretax_amount="-100.00",
            tax_amount="13.00",
            total_amount="113.00",
            tax_rate="13%",
            invoice_type="增值税电子发票",
            invoice_no="26310000000000000001",
            status="已确认",
        )

        _validate_final_records([record])

        self.assertIn("pretax_amount", record.fields_needing_review)
        self.assertEqual(record.status, "需人工确认")

    def test_final_validation_flags_suspicious_party_names(self):
        record = InvoiceRecord(
            row_id=1,
            original_path="1.pdf",
            original_name="1.pdf",
            buyer_name="机店号：661712147754",
            buyer_tax="91310115MA1234567X",
            seller_name="中国工商银行",
            seller_tax="91310115MA7654321X",
            invoice_date="2026-07-12",
            pretax_amount="88.50",
            tax_amount="11.50",
            total_amount="100.00",
            invoice_type="增值税电子发票",
            invoice_no="26310000000000000001",
            tax_rate="13%",
            status="已确认",
        )

        _validate_final_records([record])

        self.assertIn("buyer_name", record.fields_needing_review)
        self.assertIn("seller_name", record.fields_needing_review)
        self.assertEqual(record.status, "需人工确认")

    def test_final_validation_flags_common_buyer_written_as_seller(self):
        records = [
            InvoiceRecord(row_id=i, original_path=f"{i}.pdf", original_name=f"{i}.pdf", buyer_name="江西省勘察设计研究院上海分院", buyer_tax="913101097590284041", seller_name=f"销售方{i}有限公司", seller_tax="91310115MA1234567X", invoice_date="2026-07-12", total_amount="100.00", invoice_type="增值税电子发票", invoice_no=f"2631000000000000000{i}", tax_rate="13%")
            for i in range(1, 4)
        ]
        swapped = InvoiceRecord(row_id=4, original_path="4.pdf", original_name="4.pdf", buyer_name="外部公司", buyer_tax="91310115MA7654321X", seller_name="江西省勘察设计研究院上海分院", seller_tax="913101097590284041", invoice_date="2026-07-12", total_amount="100.00", invoice_type="增值税电子发票", invoice_no="26310000000000000004", tax_rate="13%")
        records.append(swapped)

        _validate_final_records(records)

        self.assertIn("buyer_name", swapped.fields_needing_review)
        self.assertIn("seller_tax", swapped.fields_needing_review)

    @patch("invoice_assistant.record_builder.build_record")
    def test_scans_nested_folders_but_excludes_selected_archive_root(self, build_record):
        build_record.side_effect = lambda path, row_id: InvoiceRecord(row_id=row_id, original_path=str(path), original_name=path.name)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            nested = root / "客户资料" / "2025年11月"
            archive = root / "归档文件夹"
            nested.mkdir(parents=True)
            archive.mkdir()
            (root / "top.pdf").write_bytes(b"pdf")
            (nested / "nested.pdf").write_bytes(b"pdf")
            (archive / "archived.pdf").write_bytes(b"pdf")

            records = scan_invoice_files(root, max_workers=1, exclude_roots=[archive])

        self.assertEqual({record.original_name for record in records}, {"top.pdf", "nested.pdf"})

    def test_pdf_amount_columns_do_not_mix_total_with_pretax(self):
        lines = [
            OcrLine(text="165.29", x=0.681, y=0.315, width=0.049, height=0.021),
            OcrLine(text="¥21.49", x=0.934, y=0.315, width=0.042, height=0.021),
            OcrLine(text="（小写）¥186.78", x=0.674, y=0.272, width=0.114, height=0.026),
            OcrLine(text="13%", x=0.777, y=0.569, width=0.022, height=0.023),
        ]

        amounts = _amounts_from_pdf_table(lines)

        self.assertEqual(amounts["pretax_amount"], "165.29")
        self.assertEqual(amounts["tax_amount"], "21.49")
        self.assertEqual(amounts["total_amount"], "186.78")
        self.assertEqual(amounts["tax_rate"], "13%")

    def test_pdf_amount_columns_support_compact_and_low_summary_layouts(self):
        compact = _amounts_from_pdf_table([
            OcrLine(text="21.08", x=0.656, y=0.666, width=0.038, height=0.017),
            OcrLine(text="3%", x=0.745, y=0.666, width=0.015, height=0.017),
            OcrLine(text="0.63", x=0.947, y=0.666, width=0.030, height=0.017),
            OcrLine(text="¥21.08", x=0.671, y=0.465, width=0.045, height=0.018),
            OcrLine(text="¥0.63", x=0.940, y=0.465, width=0.037, height=0.018),
            OcrLine(text="（小写）¥21.71", x=0.656, y=0.206, width=0.106, height=0.018),
        ])
        low_summary = _amounts_from_pdf_table([
            OcrLine(text="¥1303.53", x=0.669, y=0.192, width=0.054, height=0.010),
            OcrLine(text="¥169.47", x=0.928, y=0.192, width=0.047, height=0.010),
            OcrLine(text="¥1473.00", x=0.737, y=0.128, width=0.060, height=0.011),
            OcrLine(text="13%", x=0.805, y=0.790, width=0.023, height=0.011),
        ])

        self.assertEqual(compact["pretax_amount"], "21.08")
        self.assertEqual(compact["tax_amount"], "0.63")
        self.assertEqual(compact["total_amount"], "21.71")
        self.assertEqual(low_summary["pretax_amount"], "1303.53")
        self.assertEqual(low_summary["tax_amount"], "169.47")
        self.assertEqual(low_summary["total_amount"], "1473.00")


if __name__ == "__main__":
    unittest.main()
