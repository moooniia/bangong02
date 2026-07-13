import re
from typing import Iterable, List, Optional, Sequence, Tuple, Union

from .models import InvoicePartyFields

TextLine = Union[str, Tuple[str, float]]

BUYER_ANCHOR_RE = re.compile(r"^(?:购|买方信息|购买方\s*[：:]?\s*$|购方信息|购货单位|购买方信息)")
SELLER_ANCHOR_RE = re.compile(r"^(?:销|销方信息|售方信息|销售方\s*[：:]?\s*$|销货单位|销售方信息)")
NAME_RE = re.compile(r"(?:名\s*称|名|称|桥|社|祢|林|抬头)\s*[：:]\s*(.+)")
TAX_RE = re.compile(r"(?:纳税人识别号|统一社会信用代码|税号)\s*[：:]\s*([A-Z0-9]{15,20})", re.I)


def parse_party_fields(text_lines: Sequence[TextLine]) -> InvoicePartyFields:
    """Extract buyer/seller fields only when their ownership is clear.

    This parser intentionally favors blanks over guesses. A value is accepted
    for seller fields only when it is directly labelled as seller information
    or found inside an explicit seller section.
    """
    result = InvoicePartyFields()
    lines = _plain_lines(text_lines)
    full_text = "\n".join(lines)

    direct_buyer_name = _first_line_match(r"购买方名称[：:·]?\s*(.+)", lines)
    direct_seller_name = _first_line_match(r"销售方名称[：:·]?\s*(.+)", lines)

    direct_buyer_name = _clean_name(direct_buyer_name)
    direct_seller_name = _clean_name(direct_seller_name)

    if _valid_name(direct_buyer_name):
        result.buyer_name = direct_buyer_name
    if _valid_name(direct_seller_name):
        result.seller_name = direct_seller_name

    section_values = _extract_section_values(lines)
    result.buyer_name = result.buyer_name or section_values.get("buyer_name")
    result.buyer_tax = result.buyer_tax or section_values.get("buyer_tax")
    result.seller_name = result.seller_name or section_values.get("seller_name")
    result.seller_tax = result.seller_tax or section_values.get("seller_tax")

    _assign_direct_tax_numbers(result, full_text)
    _guard_against_cross_fill(result, lines)
    return result


def _plain_lines(text_lines: Sequence[TextLine]) -> List[str]:
    lines = []
    for item in text_lines:
        text = item[0] if isinstance(item, tuple) else item
        text = str(text).strip()
        if text:
            lines.append(text)
    return lines


def _extract_section_values(lines: Iterable[str]) -> dict:
    values = {}
    current_section: Optional[str] = None

    for line in lines:
        if BUYER_ANCHOR_RE.search(line):
            current_section = "buyer"
            continue
        if SELLER_ANCHOR_RE.search(line):
            current_section = "seller"
            continue
        if current_section is None:
            continue

        name_match = NAME_RE.search(line)
        cleaned_name = _clean_name(name_match.group(1) if name_match else None)
        if name_match and _valid_name(cleaned_name):
            values.setdefault(f"{current_section}_name", cleaned_name)

        tax_match = TAX_RE.search(line)
        if tax_match:
            values.setdefault(f"{current_section}_tax", tax_match.group(1).upper())

    return values


def _assign_direct_tax_numbers(result: InvoicePartyFields, full_text: str) -> None:
    lines = full_text.splitlines()
    buyer_tax = _first_line_match(
        r"购买方.*?(?:纳税人识别号|统一社会信用代码|税号)\s*[：:]\s*([A-Z0-9]{15,20})",
        lines,
    )
    seller_tax = _first_line_match(
        r"销售方.*?(?:纳税人识别号|统一社会信用代码|税号)\s*[：:]\s*([A-Z0-9]{15,20})",
        lines,
    )
    if buyer_tax:
        result.buyer_tax = buyer_tax.upper()
    if seller_tax:
        result.seller_tax = seller_tax.upper()


def _guard_against_cross_fill(result: InvoicePartyFields, lines: Sequence[str]) -> None:
    has_seller_anchor = any(SELLER_ANCHOR_RE.search(line) for line in lines)
    has_buyer_anchor = any(BUYER_ANCHOR_RE.search(line) for line in lines)

    if result.seller_name and result.buyer_name and result.seller_name == result.buyer_name:
        result.seller_name = None
        result.add_review("seller_name", "销售方名称与购买方名称相同，疑似误填，已留空")

    if result.seller_tax and result.buyer_tax and result.seller_tax == result.buyer_tax:
        result.seller_tax = None
        result.add_review("seller_tax", "销售方税号与购买方税号相同，疑似误填，已留空")

    if not result.seller_name:
        reason = "未找到明确的销售方名称"
        if not has_seller_anchor and has_buyer_anchor:
            reason = "只找到购买方区域，销售方名称不确定"
        result.add_review("seller_name", reason)

    if not result.seller_tax:
        reason = "未找到明确的销售方税号"
        if not has_seller_anchor and has_buyer_anchor:
            reason = "只找到购买方区域，销售方税号不确定"
        result.add_review("seller_tax", reason)

    if not result.buyer_name:
        result.add_review("buyer_name", "未找到明确的购买方名称")
    if not result.buyer_tax:
        result.add_review("buyer_tax", "未找到明确的购买方税号")


def _first_match(pattern: str, text: str) -> Optional[str]:
    match = re.search(pattern, text, re.I)
    if not match:
        return None
    value = re.sub(r"\s+", " ", match.group(1)).strip()
    return value or None


def _first_line_match(pattern: str, lines: Iterable[str]) -> Optional[str]:
    for line in lines:
        value = _first_match(pattern, line)
        if value:
            return value
    return None


def _valid_name(value: Optional[str]) -> bool:
    if not value:
        return False
    value = value.strip()
    if len(value) < 2:
        return False
    if re.fullmatch(r"[\d\s./\\\-_]+", value):
        return False
    return True


def _clean_name(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    value = re.sub(r"\s+", "", value)
    value = re.sub(
        r"^(?:购买方|购方|销售方|销方)?(?:名称|名|称|桥|社|祢|林|抬头)\s*[：:]+",
        "",
        value,
    )
    return value.strip("：:，,。 ") or None
