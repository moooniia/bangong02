import re
import filecmp
import shutil
from pathlib import Path
from typing import Iterable, Optional, Sequence

from .models import InvoiceRecord


def archive_records(records: Iterable[InvoiceRecord], output_root: Path, mode: str = "month", name_fields: Optional[Sequence[str]] = None, separator: str = "_") -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    _clear_generated_duplicates(output_root / "重复发票")
    duplicate_counts = {}
    for record in records:
        source = Path(record.original_path)
        if not source.exists() or not source.is_file():
            record.add_review("archived_path", "原文件不存在，无法生成归档文件")
            continue
        identity = _duplicate_identity(record)
        duplicate_index = duplicate_counts.get(identity, 0)
        duplicate_counts[identity] = duplicate_index + 1
        archive_folder = output_root / _archive_folder(record, mode)
        if duplicate_index:
            archive_folder = output_root / "重复发票" / _archive_month(record)
        archive_folder.mkdir(parents=True, exist_ok=True)
        archive_name = _archive_name(record, source, name_fields, separator)
        if duplicate_index:
            name_path = Path(archive_name)
            archive_name = f"{name_path.stem}_重复{duplicate_index}{name_path.suffix}"
        dest = _next_destination(archive_folder, archive_name, source)
        if source.resolve() == dest.resolve():
            record.archived_path = str(dest)
            continue
        if dest.exists() and filecmp.cmp(source, dest, shallow=False):
            record.archived_path = str(dest)
            continue
        shutil.copy2(source, dest)
        record.archived_path = str(dest)


def _archive_folder(record: InvoiceRecord, mode: str) -> Path:
    month = _archive_month(record)
    if mode == "category_month":
        return Path(_safe_filename(record.category or "（未分类）")) / month
    if mode == "seller_month":
        return Path(_safe_filename(record.seller_name or "待确认销售方")) / month
    return Path(month)


def _archive_month(record: InvoiceRecord) -> str:
    if record.invoice_date and len(record.invoice_date) >= 7:
        year, month = record.invoice_date[:7].split("-")
        return f"{year}年{month}月"
    return "待确认月份"


def _duplicate_identity(record: InvoiceRecord) -> str:
    if record.invoice_no:
        return f"invoice:{record.invoice_no}|{record.seller_tax}|{record.total_amount}"
    return f"fallback:{record.seller_tax}|{record.invoice_date}|{record.total_amount}"


def _clear_generated_duplicates(folder: Path) -> None:
    if not folder.exists():
        return
    for path in folder.rglob("*"):
        if path.is_file() and re.search(r"_重复\d+$", path.stem):
            path.unlink()
    for path in sorted((item for item in folder.rglob("*") if item.is_dir()), reverse=True):
        try:
            path.rmdir()
        except OSError:
            pass


def _archive_name(record: InvoiceRecord, source: Path, name_fields: Optional[Sequence[str]] = None, separator: str = "_") -> str:
    party = record.buyer_name or "待确认购买方"
    date = record.invoice_date or "待确认日期"
    amount = record.total_amount or "待确认金额"
    identity = record.invoice_no or source.stem
    if name_fields is None:
        parts = [identity, party, date, f"{amount}元"]
    else:
        values = {
            "invoice_no": identity,
            "buyer_name": party,
            "seller_name": record.seller_name or "待确认销售方",
            "invoice_date": date,
            "total_amount": f"{amount}元",
            "category": record.category or "（未分类）",
        }
        parts = [values[field] for field in name_fields if field in values]
        if not parts:
            parts = [identity]
    raw = f"{separator.join(parts)}{source.suffix.lower()}"
    return _safe_filename(raw)


def _next_destination(folder: Path, filename: str, source: Path) -> Path:
    destination = folder / filename
    if not destination.exists() or filecmp.cmp(source, destination, shallow=False):
        return destination
    stem = destination.stem
    suffix = destination.suffix
    index = 2
    while True:
        candidate = folder / f"{stem}_{index}{suffix}"
        if not candidate.exists() or filecmp.cmp(source, candidate, shallow=False):
            return candidate
        index += 1


def _safe_filename(value: str) -> str:
    value = re.sub(r"[\\/:*?\"<>|]+", "_", value)
    value = re.sub(r"\s+", "", value)
    return value[:180]
