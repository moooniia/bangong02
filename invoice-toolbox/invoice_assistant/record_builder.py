from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
import re
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
    _normalize_party_names(completed_records)
    _enrich_exact_duplicate_fields(completed_records)
    _enrich_consistent_party_fields(completed_records)
    _enrich_dominant_batch_fields(completed_records)
    _validate_final_records(completed_records)
    return completed_records


def _normalize_party_names(records: List[InvoiceRecord]) -> None:
    for record in records:
        for field_name in ("buyer_name", "seller_name"):
            value = getattr(record, field_name).strip()
            cleaned = _clean_party_name_value(value)
            if cleaned != value:
                setattr(record, field_name, cleaned)


def _clean_party_name_value(value: str) -> str:
    value = re.sub(r"\s+", "", value or "")
    value = re.sub(
        r"^(?:购买方|购方|销售方|销方)?(?:名称|名|称|桥|社|祢|林|抬头)\s*[：:]+",
        "",
        value,
    )
    generic_label = re.match(r"^[\u4e00-\u9fff]{1,3}[：:]+(.+)$", value)
    if generic_label and _looks_like_party_name_after_label(generic_label.group(1)):
        value = generic_label.group(1)
    if not re.search(r"[（(]个体工商户[）)]$", value):
        value = re.sub(r"[（(][^）)]*[）)]$", "", value)
    return value.strip("：:，,。 ")


def _looks_like_party_name_after_label(value: str) -> bool:
    return bool(
        re.search(
            r"(?:有限责任公司|股份有限公司|有限公司|研究院|勘察院|分院|中心|银行|学校|单位|个体工商户|商行|店|厂)$",
            value.strip(),
        )
    )


def _enrich_exact_duplicate_fields(records: List[InvoiceRecord]) -> None:
    grouped = {}
    for record in records:
        key = _duplicate_key(record)
        if key:
            grouped.setdefault(key, []).append(record)

    fields = (
        "buyer_name",
        "buyer_tax",
        "seller_name",
        "seller_tax",
        "invoice_date",
        "pretax_amount",
        "tax_amount",
        "total_amount",
        "tax_rate",
        "invoice_type",
        "invoice_no",
        "line_items",
    )
    for group in grouped.values():
        if len(group) < 2:
            continue
        field_values = {}
        for field_name in fields:
            values = [
                getattr(record, field_name).strip()
                for record in group
                if _is_reliable_field_value(record, field_name)
            ]
            if not values:
                continue
            value, count = Counter(values).most_common(1)[0]
            if count == len(values):
                field_values[field_name] = value
        if not field_values:
            continue
        for record in group:
            for field_name, value in field_values.items():
                current = getattr(record, field_name).strip()
                if not current or field_name in record.fields_needing_review:
                    setattr(record, field_name, value)
                    _clear_review(record, field_name)


def _duplicate_key(record: InvoiceRecord) -> str:
    invoice_no = record.invoice_no.strip()
    if not invoice_no:
        return ""
    date = record.invoice_date.strip()
    amount = record.total_amount.strip()
    if date and amount:
        return f"{invoice_no}|{date}|{amount}"
    return invoice_no


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
            if name and name in unique_tax and (
                not tax or not is_valid_uscc(tax) or tax != unique_tax[name]
            ):
                setattr(record, tax_field, unique_tax[name])
                _clear_review(record, tax_field)
            elif tax and not name and tax in unique_name:
                setattr(record, name_field, unique_name[tax])
                _clear_review(record, name_field)


def _enrich_dominant_batch_fields(records: List[InvoiceRecord]) -> None:
    buyer_pair = _dominant_buyer_pair(records)
    if buyer_pair:
        buyer_name, buyer_tax = buyer_pair
        for record in records:
            if not record.buyer_name.strip() or "buyer_name" in record.fields_needing_review:
                record.buyer_name = buyer_name
                _clear_review(record, "buyer_name")
            if not record.buyer_tax.strip() or "buyer_tax" in record.fields_needing_review:
                record.buyer_tax = buyer_tax
                _clear_review(record, "buyer_tax")

    seller_pairs_by_context = _dominant_seller_pairs_by_context(records)
    for record in records:
        key = _seller_context_key(record)
        pair = seller_pairs_by_context.get(key)
        if not pair:
            continue
        seller_name, seller_tax = pair
        if not record.seller_name.strip() or "seller_name" in record.fields_needing_review:
            record.seller_name = seller_name
            _clear_review(record, "seller_name")
        if not record.seller_tax.strip() or "seller_tax" in record.fields_needing_review:
            record.seller_tax = seller_tax
            _clear_review(record, "seller_tax")


def _dominant_buyer_pair(records: List[InvoiceRecord]) -> tuple[str, str] | None:
    pairs = Counter()
    for record in records:
        name = record.buyer_name.strip()
        tax = record.buyer_tax.strip().upper()
        if name and tax and not _is_suspicious_party_name(name) and (tax == "个人无税号" or is_valid_uscc(tax)):
            pairs[(name, tax)] += 1
    if not pairs:
        return None
    pair, count = pairs.most_common(1)[0]
    if count >= 3 and count / max(sum(pairs.values()), 1) >= 0.5:
        return pair
    return None


def _dominant_seller_pairs_by_context(records: List[InvoiceRecord]) -> dict[tuple[str, str, str], tuple[str, str]]:
    grouped: dict[tuple[str, str, str], Counter] = {}
    for record in records:
        key = _seller_context_key(record)
        if not all(key):
            continue
        name = record.seller_name.strip()
        tax = record.seller_tax.strip().upper()
        if name and tax and not _is_suspicious_party_name(name) and is_valid_uscc(tax):
            grouped.setdefault(key, Counter())[(name, tax)] += 1
    result = {}
    for key, counts in grouped.items():
        pair, count = counts.most_common(1)[0]
        total = sum(counts.values())
        if count >= 3 and count / max(total, 1) >= 0.85:
            result[key] = pair
    return result


def _seller_context_key(record: InvoiceRecord) -> tuple[str, str, str]:
    buyer = record.buyer_tax.strip().upper() or record.buyer_name.strip()
    return (buyer, record.invoice_type.strip(), record.tax_rate.strip())


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
    dominant_buyer_name = _dominant_value(records, "buyer_name")
    dominant_buyer_tax = _dominant_value(records, "buyer_tax")
    for record in records:
        _normalize_party_names([record])
        for field_name, reason in required.items():
            if not getattr(record, field_name).strip() and field_name not in record.fields_needing_review:
                record.add_review(field_name, reason)
        _clear_stale_reviews_for_valid_values(record)
        _validate_party_quality(record)
        _validate_party_position(record, dominant_buyer_name, dominant_buyer_tax)
        record.status = "需人工确认" if record.fields_needing_review else "已确认"


def _clear_review(record: InvoiceRecord, field_name: str) -> None:
    record.fields_needing_review.discard(field_name)
    record.review_reasons.pop(field_name, None)


def _mark_review_once(record: InvoiceRecord, field_name: str, reason: str) -> None:
    if field_name in record.fields_needing_review:
        reasons = record.review_reasons.setdefault(field_name, [])
        if reason not in reasons:
            reasons.append(reason)
        return
    record.add_review(field_name, reason)


def _clear_stale_reviews_for_valid_values(record: InvoiceRecord) -> None:
    for field_name in list(record.fields_needing_review):
        if not _is_reliable_field_value(record, field_name):
            continue
        reasons = record.review_reasons.get(field_name, [])
        if reasons and all(_is_stale_review_reason(reason) for reason in reasons):
            _clear_review(record, field_name)


def _is_stale_review_reason(reason: str) -> bool:
    return any(
        token in reason
        for token in (
            "未能明确识别",
            "为空",
            "由同批次记录补全",
            "疑似误填",
            "未通过校验",
        )
    )


def _is_reliable_field_value(record: InvoiceRecord, field_name: str) -> bool:
    value = getattr(record, field_name, "")
    if value is None:
        return False
    value = str(value).strip()
    if not value or value == "待确认":
        return False
    if field_name in {"buyer_name", "seller_name"}:
        return not _is_suspicious_party_name(value)
    if field_name in {"buyer_tax", "seller_tax"}:
        return value == "个人无税号" or is_valid_uscc(value.upper())
    if field_name == "tax_rate":
        return value == "免税" or bool(re.fullmatch(r"\d{1,2}%", value))
    return True


def _dominant_value(records: List[InvoiceRecord], field_name: str) -> str:
    values = [
        getattr(record, field_name).strip()
        for record in records
        if getattr(record, field_name).strip()
    ]
    if not values:
        return ""
    value, count = Counter(values).most_common(1)[0]
    return value if count >= 3 and count / max(len(values), 1) >= 0.35 else ""


def _validate_party_position(record: InvoiceRecord, dominant_buyer_name: str, dominant_buyer_tax: str) -> None:
    if dominant_buyer_tax and record.seller_tax.strip().upper() == dominant_buyer_tax.upper() and record.buyer_tax.strip().upper() != dominant_buyer_tax.upper():
        _mark_review_once(record, "buyer_name", "最终复查：疑似购销方位置反写，请核对购买方名称")
        _mark_review_once(record, "buyer_tax", "最终复查：疑似购销方位置反写，请核对购买方税号")
        _mark_review_once(record, "seller_name", "最终复查：疑似购销方位置反写，请核对销售方名称")
        _mark_review_once(record, "seller_tax", "最终复查：疑似购销方位置反写，请核对销售方税号")
    if dominant_buyer_name and record.seller_name.strip() == dominant_buyer_name and record.buyer_name.strip() != dominant_buyer_name:
        _mark_review_once(record, "buyer_name", "最终复查：常见购买方名称出现在销售方列，请核对")
        _mark_review_once(record, "seller_name", "最终复查：常见购买方名称出现在销售方列，请核对")


def _validate_party_quality(record: InvoiceRecord) -> None:
    for field_name, title in (("buyer_name", "购买方名称"), ("seller_name", "销售方名称")):
        value = getattr(record, field_name).strip()
        if value and _is_suspicious_party_name(value):
            _mark_review_once(record, field_name, f"最终复查：{title}疑似识别到了标签、银行账户或残缺文本")
    for field_name, title in (("buyer_tax", "购买方税号"), ("seller_tax", "销售方税号")):
        value = getattr(record, field_name).strip().upper()
        if value and value != "个人无税号" and not is_valid_uscc(value):
            _mark_review_once(record, field_name, f"最终复查：{title}未通过统一社会信用代码校验")
    if record.buyer_name and record.seller_name and record.buyer_name.strip() == record.seller_name.strip():
        _mark_review_once(record, "buyer_name", "最终复查：购销方名称相同，请核对")
        _mark_review_once(record, "seller_name", "最终复查：购销方名称相同，请核对")


def _is_suspicious_party_name(value: str) -> bool:
    compact = re.sub(r"\s+", "", value)
    if compact == "个人":
        return False
    if len(compact) < 3:
        return True
    if compact.startswith(("名称", "称：", "称:", "桥：", "桥:", "社：", "社:", "祢：", "祢:", "林：", "林:", "机店号", "税号", "纳税人识别号", "供货单位")):
        return True
    if re.fullmatch(r"[\dA-Z]+", compact, re.I):
        return True
    label_tokens = (
        "统一社会信用", "纳税人识别", "开户银行", "开户行", "银行账号", "地址电话",
        "机器编号", "校验码", "发票号码", "发票代码", "项目名称", "规格型号",
        "收款人", "复核人", "开票人", "销方开户", "供货单位", "购买方信息", "销售方信息",
    )
    if any(token in compact for token in label_tokens):
        return True
    if compact.endswith("银行") and len(compact) <= 8:
        return True
    return sum("\u4e00" <= char <= "\u9fff" for char in compact) < 2


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
