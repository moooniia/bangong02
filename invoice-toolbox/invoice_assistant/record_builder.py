from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
from typing import Callable, Iterable, List, Optional

from .field_parser import build_record_from_ocr_lines as build_ocr_record
from .models import InvoiceRecord
from .ocr import recognize_image
from .safe_party_parser import parse_party_fields
from .uscc import is_valid_uscc

SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".tif", ".tiff", ".pdf"}


def scan_invoice_files(
    folder: Path,
    progress: Optional[Callable[[int, int, Path, InvoiceRecord], None]] = None,
    max_workers: int = 3,
    exclude_roots: Optional[Iterable[Path]] = None,
) -> List[InvoiceRecord]:
    excluded = []
    for root in exclude_roots or []:
        try:
            excluded.append(Path(root).resolve())
        except (OSError, RuntimeError):
            continue
    files = [
        path
        for path in folder.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES and not _is_under_any(path, excluded)
    ]
    ordered_files = sorted(files)
    records: List[Optional[InvoiceRecord]] = [None] * len(ordered_files)
    if not ordered_files:
        return []
    with ThreadPoolExecutor(max_workers=max(1, min(max_workers, len(ordered_files)))) as executor:
        futures = {
            executor.submit(build_record, path, index): (index - 1, path)
            for index, path in enumerate(ordered_files, 1)
        }
        completed = 0
        for future in as_completed(futures):
            index, path = futures[future]
            records[index] = future.result()
            completed += 1
            if progress:
                progress(completed, len(ordered_files), path, records[index])
    completed_records = [record for record in records if record is not None]
    _enrich_consistent_party_fields(completed_records)
    _validate_final_records(completed_records)
    return completed_records


def _enrich_consistent_party_fields(records: List[InvoiceRecord]) -> None:
    for name_field, tax_field in (("buyer_name", "buyer_tax"), ("seller_name", "seller_tax")):
        name_to_taxes = {}
        tax_to_names = {}
        for record in records:
            name = getattr(record, name_field).strip()
            tax = getattr(record, tax_field).strip().upper()
            if not name or not tax:
                continue
            name_to_taxes.setdefault(name, set()).add(tax)
            tax_to_names.setdefault(tax, set()).add(name)
        unique_tax = _dominant_mapping(records, name_field, tax_field)
        unique_name = _dominant_mapping(records, tax_field, name_field)
        for record in records:
            name = getattr(record, name_field).strip()
            tax = getattr(record, tax_field).strip().upper()
            if name and name in unique_tax and (not tax or not is_valid_uscc(tax)):
                setattr(record, tax_field, unique_tax[name])
                _clear_review(record, tax_field)
            elif tax and not name and tax in unique_name:
                setattr(record, name_field, unique_name[tax])
                _clear_review(record, name_field)
    for record in records:
        if not record.fields_needing_review:
            record.status = "已确认"


def _validate_final_records(records: List[InvoiceRecord]) -> None:
    """Recheck final values after batch enrichment so empty fields cannot be hidden."""
    required = {
        "buyer_name": "最终复查：购买方名称为空",
        "buyer_tax": "最终复查：购买方税号为空",
        "seller_name": "最终复查：销售方名称为空",
        "seller_tax": "最终复查：销售方税号为空",
        "invoice_date": "最终复查：开票日期为空",
        "total_amount": "最终复查：价税合计为空",
        "invoice_type": "最终复查：发票类型为空",
        "invoice_no": "最终复查：发票号码为空",
        "tax_rate": "最终复查：税率或征收方式为空",
    }
    for record in records:
        for field_name, reason in required.items():
            if not getattr(record, field_name).strip() and field_name not in record.fields_needing_review:
                record.add_review(field_name, reason)
        record.status = "需人工确认" if record.fields_needing_review else "已确认"


def _clear_review(record: InvoiceRecord, field_name: str) -> None:
    record.fields_needing_review.discard(field_name)
    record.review_reasons.pop(field_name, None)


def _dominant_mapping(records: List[InvoiceRecord], source_field: str, target_field: str) -> dict:
    grouped = {}
    for record in records:
        source = getattr(record, source_field).strip()
        target = getattr(record, target_field).strip()
        if source and target:
            grouped.setdefault(source, Counter())[target] += 1
    result = {}
    for source, counts in grouped.items():
        target, count = counts.most_common(1)[0]
        total = sum(counts.values())
        if len(counts) == 1 or (count >= 2 and count / total >= 0.8):
            result[source] = target
    return result


def build_record(path: Path, row_id: int) -> InvoiceRecord:
    try:
        return build_ocr_record(row_id, path, recognize_image(path))
    except Exception as exc:
        record = build_empty_record(row_id, path)
        record.add_review("status", f"OCR 失败：{exc}")
        return record


def _is_under_any(path: Path, roots: Iterable[Path]) -> bool:
    try:
        resolved = path.resolve()
    except (OSError, RuntimeError):
        return False
    for root in roots:
        try:
            resolved.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def build_empty_record(row_id: int, path: Path) -> InvoiceRecord:
    record = InvoiceRecord(
        row_id=row_id,
        original_path=str(path),
        original_name=path.name,
    )
    for field_name, reason in {
        "buyer_name": "尚未识别或确认购买方名称",
        "buyer_tax": "尚未识别或确认购买方税号",
        "seller_name": "尚未识别或确认销售方名称",
        "seller_tax": "尚未识别或确认销售方税号",
        "invoice_date": "尚未识别或确认开票日期",
        "total_amount": "尚未识别或确认价税合计",
    }.items():
        record.add_review(field_name, reason)
    return record


def build_record_from_ocr_lines(row_id: int, path: Path, text_lines: Iterable[str]) -> InvoiceRecord:
    record = build_empty_record(row_id, path)
    party_fields = parse_party_fields(list(text_lines))
    mapping = {
        "buyer_name": "buyer_name",
        "buyer_tax": "buyer_tax",
        "seller_name": "seller_name",
        "seller_tax": "seller_tax",
    }
    for source, target in mapping.items():
        value = getattr(party_fields, source) or ""
        setattr(record, target, value)
        if value and target in record.fields_needing_review:
            record.fields_needing_review.remove(target)
            record.review_reasons.pop(target, None)

    for field_name in party_fields.fields_needing_review:
        record.add_review(field_name, "; ".join(party_fields.review_reasons.get(field_name, [])))

    if not record.fields_needing_review:
        record.status = "已确认"
    return record
