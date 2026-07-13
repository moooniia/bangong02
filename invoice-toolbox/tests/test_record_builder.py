import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from invoice_assistant.models import InvoiceRecord
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
        self.assertIn("seller_name", missing_name.fields_needing_review)
        self.assertIn("seller_tax", missing_tax.fields_needing_review)

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

        _enrich_exact_duplicate_fields([clean, photo])
        _validate_final_records([clean, photo])

        self.assertEqual(photo.seller_name, "上海浦东华海加油站有限公司")
        self.assertEqual(photo.seller_tax, "91310115133504376H")
        self.assertNotIn("seller_name", photo.fields_needing_review)
        self.assertNotIn("seller_tax", photo.fields_needing_review)
        self.assertEqual(photo.status, "已确认")

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
            total_amount="100.00",
            invoice_type="增值税电子发票",
            invoice_no="26310000000000000001",
            status="已确认",
        )

        _validate_final_records([record])

        self.assertIn("seller_name", record.fields_needing_review)
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


if __name__ == "__main__":
    unittest.main()
