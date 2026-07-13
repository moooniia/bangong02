import tempfile
import unittest
from pathlib import Path

from invoice_assistant.archive import archive_records
from invoice_assistant.models import InvoiceRecord


class ArchiveTest(unittest.TestCase):
    def test_places_later_duplicate_in_dedicated_duplicate_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first_source = root / "first.pdf"
            second_source = root / "second.pdf"
            first_source.write_bytes(b"first")
            second_source.write_bytes(b"second")
            records = [
                InvoiceRecord(row_id=1, original_path=str(first_source), original_name=first_source.name, invoice_no="12345678", seller_tax="91310115MA1234567X", total_amount="100.00", invoice_date="2026-07-01"),
                InvoiceRecord(row_id=2, original_path=str(second_source), original_name=second_source.name, invoice_no="12345678", seller_tax="91310115MA1234567X", total_amount="100.00", invoice_date="2026-07-01"),
            ]

            archive_records(records, root / "out")

            self.assertEqual(Path(records[0].archived_path).parent.name, "2026年07月")
            self.assertEqual(Path(records[1].archived_path).parent.parent.name, "重复发票")
            self.assertIn("重复1", Path(records[1].archived_path).stem)

    def test_same_number_with_different_amount_is_not_a_duplicate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first_source = root / "first.pdf"
            second_source = root / "second.pdf"
            first_source.write_bytes(b"first")
            second_source.write_bytes(b"second")
            records = [
                InvoiceRecord(row_id=1, original_path=str(first_source), original_name=first_source.name, invoice_no="031002500111", seller_tax="91310115MA1234567X", total_amount="11.00", invoice_date="2026-07-01"),
                InvoiceRecord(row_id=2, original_path=str(second_source), original_name=second_source.name, invoice_no="031002500111", seller_tax="91310115MA1234567X", total_amount="29.00", invoice_date="2026-07-01"),
            ]

            archive_records(records, root / "out")

            self.assertNotIn("重复发票", Path(records[1].archived_path).parts)

    def test_archives_to_month_folder_with_invoice_identity_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.jpg"
            source.write_bytes(b"image")
            record = InvoiceRecord(
                row_id=1,
                original_path=str(source),
                original_name=source.name,
                buyer_name="江西省勘察设计研究院有限公司",
                invoice_no="12345678",
                invoice_date="2026-07-01",
                total_amount="700.00",
            )

            archive_records([record], root / "out")

            archived = Path(record.archived_path)
            self.assertTrue(archived.exists())
            self.assertEqual(archived.parent.name, "2026年07月")
            self.assertEqual(archived.name, "12345678_江西省勘察设计研究院有限公司_2026-07-01_700.00元.jpg")

    def test_uses_pending_tokens_when_fields_need_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.jpg"
            source.write_bytes(b"image")
            record = InvoiceRecord(row_id=1, original_path=str(source), original_name=source.name)

            archive_records([record], root / "out")

            archived = Path(record.archived_path)
            self.assertTrue(archived.exists())
            self.assertEqual(archived.parent.name, "待确认月份")
            self.assertIn("待确认购买方", archived.name)

    def test_rearchiving_same_source_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.jpg"
            source.write_bytes(b"image")
            record = InvoiceRecord(row_id=1, original_path=str(source), original_name=source.name)

            archive_records([record], root / "out")
            first_path = Path(record.archived_path)
            archive_records([record], root / "out")

            self.assertEqual(Path(record.archived_path), first_path)
            self.assertEqual(len(list(first_path.parent.glob("*"))), 1)

    def test_can_archive_by_category_then_month(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.jpg"
            source.write_bytes(b"image")
            record = InvoiceRecord(
                row_id=1,
                original_path=str(source),
                original_name=source.name,
                buyer_name="江西省勘察设计研究院有限公司",
                invoice_date="2026-07-01",
                total_amount="700.00",
                category="检测服务",
            )

            archive_records([record], root / "out", mode="category_month")

            archived = Path(record.archived_path)
            self.assertTrue(archived.exists())
            self.assertEqual(archived.parent.name, "2026年07月")
            self.assertEqual(archived.parent.parent.name, "检测服务")

    def test_uses_selected_filename_fields_and_separator(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.pdf"
            source.write_bytes(b"pdf")
            record = InvoiceRecord(
                row_id=1,
                original_path=str(source),
                original_name=source.name,
                seller_name="测试销售方",
                invoice_no="87654321",
                invoice_date="2026-07-02",
            )

            archive_records(
                [record],
                root / "out",
                name_fields=["seller_name", "invoice_date"],
                separator="-",
            )

            self.assertEqual(Path(record.archived_path).name, "测试销售方-2026-07-02.pdf")


if __name__ == "__main__":
    unittest.main()
