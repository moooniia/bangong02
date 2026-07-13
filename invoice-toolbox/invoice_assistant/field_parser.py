import re
from pathlib import Path
from typing import Iterable, List, Optional

from .models import InvoiceRecord
from .ocr import OcrLine
from .uscc import is_valid_uscc

TAX_RE = re.compile(r"([0-9A-Z]{18})", re.I)
MONEY_RE = re.compile(r"(?:¥|￥)?\s*(\d{1,8}(?:,\d{3})*\.\d{2})")


def build_record_from_ocr_lines(row_id: int, path: Path, ocr_lines: Iterable[OcrLine]) -> InvoiceRecord:
    lines = list(ocr_lines)
    record = InvoiceRecord(row_id=row_id, original_path=str(path), original_name=path.name)

    _fill_party_fields(record, lines)
    _fill_basic_fields(record, lines)
    _mark_missing_key_fields(record)
    if not record.fields_needing_review:
        record.status = "已确认"
    return record


def _fill_party_fields(record: InvoiceRecord, lines: List[OcrLine]) -> None:
    analysis_lines = _merge_split_labels(lines)
    standard_two_column = _has_standard_two_column_party_labels(analysis_lines)
    buyer_name = _first_name_in_region(analysis_lines, "buyer")
    seller_name = _first_name_in_region(analysis_lines, "seller")
    buyer_tax = _first_tax_in_region(analysis_lines, "buyer")
    seller_tax = _first_tax_in_region(analysis_lines, "seller")
    if Path(record.original_path).suffix.lower() == ".pdf":
        # Digital invoices commonly place seller and buyer values in one text
        # block. In that layout the left value is the seller and the right
        # value is the buyer, so a single block coordinate is not sufficient.
        for candidate in analysis_lines:
            codes = [
                match.group(1).upper()
                for match in TAX_RE.finditer(candidate.text.upper())
                if is_valid_uscc(match.group(1).upper())
            ]
            if len(codes) >= 2 and (not buyer_tax or not seller_tax):
                if standard_two_column:
                    continue
                if candidate.x < 0.15:
                    buyer_tax = codes[0]
                    seller_tax = codes[-1]
                else:
                    seller_tax = codes[0]
                    buyer_tax = codes[-1]
                break
        if not buyer_name or not seller_name:
            for candidate in analysis_lines:
                name = _clean_name(candidate.text)
                name = re.split(r"[0-9A-Z]{18}", name, maxsplit=1, flags=re.I)[0].strip()
                chunks = _company_name_chunks(name)
                if len(chunks) >= 2:
                    if standard_two_column:
                        continue
                    else:
                        seller_name = seller_name or chunks[0]
                        buyer_name = buyer_name or chunks[-1]
                    continue
                if not _is_company_like(name):
                    continue
                if candidate.y >= 0.65 and _in_party_region(candidate, "buyer") and not buyer_name:
                    buyer_name = name
                elif candidate.y >= 0.65 and _in_party_region(candidate, "seller") and not seller_name:
                    seller_name = name
                elif candidate.y < 0.5 and candidate.x < 0.5 and not seller_name:
                    seller_name = name
        if not standard_two_column:
            for code, y in _tax_candidates(analysis_lines):
                if y >= 0.5 and not buyer_tax:
                    buyer_tax = code
                elif y < 0.5 and not seller_tax:
                    seller_tax = code

    if buyer_name:
        record.buyer_name = buyer_name
    if seller_name:
        record.seller_name = seller_name
    if buyer_tax:
        record.buyer_tax = buyer_tax
    if seller_tax:
        record.seller_tax = seller_tax

    if record.buyer_tax and record.seller_tax and record.buyer_tax == record.seller_tax:
        record.seller_tax = ""
        record.add_review("seller_tax", "销售方税号与购买方税号相同，疑似误填，已留空")
    if record.buyer_name and record.seller_name and record.buyer_name == record.seller_name:
        record.seller_name = ""
        record.add_review("seller_name", "销售方名称与购买方名称相同，疑似误填，已留空")
    if record.seller_tax and not is_valid_uscc(record.seller_tax):
        record.add_review("seller_tax", "销售方税号 OCR 结果未通过校验，请人工核对")
    if record.buyer_tax and not is_valid_uscc(record.buyer_tax):
        record.add_review("buyer_tax", "购买方税号 OCR 结果未通过校验，请人工核对")


def _merge_split_labels(lines: List[OcrLine]) -> List[OcrLine]:
    merged = []
    index = 0
    while index < len(lines):
        current = lines[index]
        if index + 1 < len(lines) and current.text.strip() in {"名", "名称"}:
            following = lines[index + 1]
            if abs(current.y - following.y) < 0.04 and following.x >= current.x:
                following_text = following.text.lstrip("：:")
                if following_text.startswith("称"):
                    following_text = following_text[1:].lstrip("：:")
                merged.append(
                    OcrLine(
                        text="名称：" + following_text,
                        x=min(current.x, following.x),
                        y=min(current.y, following.y),
                        width=max(current.x + current.width, following.x + following.width) - min(current.x, following.x),
                        height=max(current.y + current.height, following.y + following.height) - min(current.y, following.y),
                    )
                )
                index += 2
                continue
        merged.append(current)
        index += 1
    return merged


def _fill_basic_fields(record: InvoiceRecord, lines: List[OcrLine]) -> None:
    full = "\n".join(line.text for line in lines)
    date_match = re.search(r"(20\d{2})年\s*(\d{1,2})月\s*(\d{1,2})(?:日|口|曰)?", full)
    if not date_match:
        for line in lines:
            date_match = re.search(
                r"\b(20\d{2})\s+(0?[1-9]|1[0-2])\s+(0?[1-9]|[12]\d|3[01])\b",
                line.text,
            )
            if date_match:
                break
    if date_match:
        record.invoice_date = f"{date_match.group(1)}-{date_match.group(2).zfill(2)}-{date_match.group(3).zfill(2)}"

    invoice_no = re.search(r"发票号码[：:]\s*(\d{8,24})", full)
    if not invoice_no:
        number_candidates = []
        for line in lines:
            if 0.86 < line.y < 0.98:
                match = re.search(r"(?<!\d)(\d{8,24})(?!\d)", line.text)
                if match:
                    number_candidates.append((abs(line.y - 0.90), match))
        if number_candidates:
            invoice_no = min(number_candidates, key=lambda item: item[0])[1]
    if invoice_no:
        record.invoice_no = invoice_no.group(1)

    # Current all-digital invoices use a long invoice number even when the
    # title itself is missed by OCR.
    if not record.invoice_type and len(record.invoice_no) >= 20:
        record.invoice_type = "增值税电子发票"

    if "电子发票" in full:
        record.invoice_type = "增值税电子发票"
    if re.search(r"专用|支用|索用", full):
        record.invoice_type = "增值税专用发票"
    elif re.search(r"普通发票|普票", full):
        record.invoice_type = "增值税普通发票"
    elif "增值税" in full and not record.invoice_type:
        record.invoice_type = "增值税普通发票"

    rate = re.search(r"(\d{1,2})\s*%", full)
    if rate:
        record.tax_rate = f"{rate.group(1)}%"

    record.total_amount = _amount_near_keyword(lines, "小写") or _amount_near_keyword(lines, "价税合计")
    amounts = _all_amounts(lines)
    if amounts:
        if not record.total_amount:
            record.total_amount = f"{max(amounts):.2f}"
        tax_candidates = [amount for amount in amounts if 0 < amount < max(amounts) * 0.2]
        if tax_candidates:
            record.tax_amount = f"{max(tax_candidates):.2f}"
        if record.total_amount and record.tax_amount:
            try:
                record.pretax_amount = f"{float(record.total_amount) - float(record.tax_amount):.2f}"
            except ValueError:
                pass

    exact_stars = sum(1 for line in lines if line.text.strip() == "*")
    if not record.tax_rate and exact_stars >= 2 and record.total_amount:
        record.tax_rate = "免税"
        record.tax_amount = "0.00"
        record.pretax_amount = record.total_amount
    elif not record.tax_rate and record.pretax_amount and record.tax_amount:
        try:
            inferred = float(record.tax_amount) / float(record.pretax_amount) * 100
            common_rate = min((1, 3, 6, 9, 13), key=lambda value: abs(value - inferred))
            if abs(common_rate - inferred) <= 0.6:
                record.tax_rate = f"{common_rate}%"
        except (ValueError, ZeroDivisionError):
            pass

    item = _guess_line_item(lines)
    if item:
        record.line_items = item


def _mark_missing_key_fields(record: InvoiceRecord) -> None:
    reasons = {
        "buyer_name": "未能明确识别购买方名称",
        "buyer_tax": "未能明确识别购买方税号，或税号校验未通过",
        "seller_name": "未能明确识别销售方名称",
        "seller_tax": "未能明确识别销售方税号，或税号校验未通过",
        "invoice_date": "未能明确识别开票日期",
        "total_amount": "未能明确识别价税合计",
    }
    for field_name, reason in reasons.items():
        if field_name == "buyer_tax" and record.buyer_name == "个人":
            record.buyer_tax = "个人无税号"
            continue
        if not getattr(record, field_name):
            record.add_review(field_name, reason)


def _first_name_in_region(lines: List[OcrLine], region: str) -> str:
    candidates: List[tuple[float, float, str]] = []
    for line in lines:
        if not _in_party_region(line, region):
            continue
        match = re.search(r"名称[：:]\s*(.+)", line.text)
        source = match.group(1) if match else line.text
        if _is_low_confidence_text(source):
            continue
        name = _clean_name(source)
        name = re.sub(r"[0-9A-Z]{18,}$", "", name, flags=re.I).strip()
        has_nearby_label = any(
            _in_party_region(other, region)
            and re.sub(r"\s+", "", other.text).rstrip("：:") == "名称"
            and abs(other.y - line.y) < 0.05
            for other in lines
        )
        if name == "个人":
            candidates.append((line.x, line.y, name))
            continue
        if (match or has_nearby_label) and _is_plausible_party_name(name):
            candidates.append((line.x, line.y, name))
            continue
        chunks = _company_name_chunks(name)
        if chunks:
            name = "".join(chunks)
            chunks = [name]
        if len(chunks) == 1:
            name = chunks[0]
        if _is_company_like(name) and len(chunks) <= 1:
            candidates.append((line.x, line.y, name))
    if not candidates:
        return ""
    base_x, base_y, base = max(candidates, key=lambda item: len(item[2]))
    branches = [
        item for item in candidates
        if item[2] != base and re.fullmatch(r"[^，,;；]{0,12}(?:分公司|分院)", item[2])
        and abs(item[1] - base_y) < 0.05 and item[0] >= base_x
    ]
    for _, _, branch in sorted(branches):
        if branch not in base:
            base += branch
    return base


def _first_tax_in_region(lines: List[OcrLine], region: str) -> str:
    for line in lines:
        if not _in_party_region(line, region):
            continue
        if "发票号码" in line.text or "发票代码" in line.text:
            continue
        match = TAX_RE.search(line.text.upper())
        if not match:
            continue
        code = match.group(1).upper()
        if is_valid_uscc(code):
            return code
    return ""


def _labelled_name_candidates(lines: List[OcrLine]) -> List[tuple[str, float]]:
    candidates = []
    for line in lines:
        match = re.search(r"名称[：:]\s*(.+)", line.text)
        if not match:
            continue
        name = _clean_name(match.group(1))
        if _is_company_like(name) and all(name != candidate[0] for candidate in candidates):
            candidates.append((name, line.y))
    return candidates


def _tax_candidates(lines: List[OcrLine]) -> List[tuple[str, float]]:
    candidates = []
    for line in lines:
        if "发票号码" in line.text or "发票代码" in line.text:
            continue
        for match in TAX_RE.finditer(line.text.upper()):
            code = match.group(1).upper()
            if all(code != candidate[0] for candidate in candidates):
                candidates.append((code, line.y))
    return candidates


def _in_party_region(line: OcrLine, region: str) -> bool:
    if line.y < 0.5 or line.y > 0.91:
        return False
    if region == "buyer":
        return line.x < 0.46 and line.x + line.width <= 0.52
    return line.x >= 0.48


def _has_standard_two_column_party_labels(lines: List[OcrLine]) -> bool:
    buyer_label = any(re.sub(r"\s+", "", line.text).startswith(("购买方信息", "购买方")) and line.x < 0.45 for line in lines)
    seller_label = any(re.sub(r"\s+", "", line.text).startswith(("销售方信息", "销售方")) and line.x >= 0.45 for line in lines)
    return buyer_label and seller_label


def _amount_near_keyword(lines: List[OcrLine], keyword: str) -> str:
    for line in lines:
        if keyword not in line.text:
            continue
        amounts = [float(value.replace(",", "")) for value in MONEY_RE.findall(line.text)]
        if amounts:
            return f"{max(amounts):.2f}"
        nearby = [
            other
            for other in lines
            if abs(other.y - line.y) < 0.04 and other.x > line.x
        ]
        values = _all_amounts(nearby)
        if values:
            return f"{max(values):.2f}"
    return ""


def _all_amounts(lines: Iterable[OcrLine]) -> List[float]:
    values = []
    for line in lines:
        for value in MONEY_RE.findall(line.text):
            try:
                amount = float(value.replace(",", ""))
            except ValueError:
                continue
            if amount > 0:
                values.append(amount)
    return values


def _guess_line_item(lines: List[OcrLine]) -> str:
    for line in lines:
        text = line.text.strip()
        if "*" in text and len(text) > 4:
            text = _clean_line_item(text)
            if _is_low_confidence_text(text):
                return ""
            return text
    return ""


def _clean_name(value: str) -> str:
    value = re.sub(r"\s+", "", value)
    if not re.search(r"[（(]个体工商户[）)]$", value):
        value = re.sub(r"[（(][^）)]*[）)]$", "", value)
    return value.strip("：:，,。 ")


def _is_company_like(value: Optional[str]) -> bool:
    if not value or len(value) < 4:
        return False
    if value in {"公司", "有限公司", "有限责任公司", "股份有限公司", "研究院", "分院", "中心", "银行", "学校", "单位"}:
        return False
    if re.fullmatch(r"[\dA-Z]+", value, re.I):
        return False
    if any(token in value for token in ("开户银行", "银行账号", "收款人", "复核人")):
        return False
    return any(token in value for token in ("公司", "研究院", "勘察院", "中心", "银行", "学校", "单位", "个体工商户", "商行", "店", "厂"))


def _is_plausible_party_name(value: str) -> bool:
    if len(value) < 3 or len(value) > 80:
        return False
    if any(token in value for token in ("统一社会信用", "纳税人识别", "开户银行", "银行账号", "项目名称")):
        return False
    return sum("\u4e00" <= char <= "\u9fff" for char in value) >= 3


def _company_name_chunks(value: str) -> List[str]:
    suffix = r"(?:有限责任公司|股份有限公司|有限公司|分公司|(?:研究院|勘察院)(?![^，,;；]{0,12}(?:分院|有限公司|有限责任公司|股份有限公司))|分院|商行|中心|银行|学校|单位|店(?:[（(]个体工商户[）)])?|厂)"
    chunks = re.findall(rf"[^，,;；]+?{suffix}", value)
    return [chunk.strip() for chunk in chunks if _is_company_like(chunk)]


def _clean_line_item(value: str) -> str:
    value = value.strip()
    value = value.lstrip("<《〈「『([（ ")
    value = re.sub(r"\s+", "", value)
    return value


def _is_low_confidence_text(value: str) -> bool:
    suspicious_chars = set("語泡夠註柔訂订後颔漿")
    if "|" in value or any(char in suspicious_chars for char in value):
        return True
    return False
