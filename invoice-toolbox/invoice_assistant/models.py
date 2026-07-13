from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass
class InvoicePartyFields:
    buyer_name: Optional[str] = None
    buyer_tax: Optional[str] = None
    seller_name: Optional[str] = None
    seller_tax: Optional[str] = None
    fields_needing_review: Set[str] = field(default_factory=set)
    review_reasons: Dict[str, List[str]] = field(default_factory=dict)

    def add_review(self, field_name: str, reason: str) -> None:
        self.fields_needing_review.add(field_name)
        self.review_reasons.setdefault(field_name, []).append(reason)

    def as_dict(self) -> Dict[str, object]:
        return {
            "buyer_name": self.buyer_name or "",
            "buyer_tax": self.buyer_tax or "",
            "seller_name": self.seller_name or "",
            "seller_tax": self.seller_tax or "",
            "fields_needing_review": sorted(self.fields_needing_review),
            "review_reasons": self.review_reasons,
        }


@dataclass
class InvoiceRecord:
    row_id: int
    original_path: str
    original_name: str
    buyer_name: str = ""
    buyer_tax: str = ""
    seller_name: str = ""
    seller_tax: str = ""
    invoice_date: str = ""
    pretax_amount: str = ""
    tax_amount: str = ""
    total_amount: str = ""
    tax_rate: str = ""
    invoice_type: str = ""
    invoice_no: str = ""
    category: str = "（未分类）"
    line_items: str = ""
    archived_path: str = ""
    status: str = "需人工确认"
    fields_needing_review: Set[str] = field(default_factory=set)
    review_reasons: Dict[str, List[str]] = field(default_factory=dict)

    def add_review(self, field_name: str, reason: str) -> None:
        self.fields_needing_review.add(field_name)
        self.review_reasons.setdefault(field_name, []).append(reason)
        self.status = "需人工确认"

    def as_dict(self) -> Dict[str, object]:
        return {
            "row_id": self.row_id,
            "original_path": self.original_path,
            "original_name": self.original_name,
            "buyer_name": self.buyer_name,
            "buyer_tax": self.buyer_tax,
            "seller_name": self.seller_name,
            "seller_tax": self.seller_tax,
            "invoice_date": self.invoice_date,
            "pretax_amount": self.pretax_amount,
            "tax_amount": self.tax_amount,
            "total_amount": self.total_amount,
            "tax_rate": self.tax_rate,
            "invoice_type": self.invoice_type,
            "invoice_no": self.invoice_no,
            "category": self.category,
            "line_items": self.line_items,
            "archived_path": self.archived_path,
            "status": self.status,
            "fields_needing_review": sorted(self.fields_needing_review),
            "review_reasons": self.review_reasons,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "InvoiceRecord":
        record = cls(
            row_id=int(data.get("row_id", 0)),
            original_path=str(data.get("original_path", "")),
            original_name=str(data.get("original_name", "")),
            buyer_name=str(data.get("buyer_name", "")),
            buyer_tax=str(data.get("buyer_tax", "")),
            seller_name=str(data.get("seller_name", "")),
            seller_tax=str(data.get("seller_tax", "")),
            invoice_date=str(data.get("invoice_date", "")),
            pretax_amount=str(data.get("pretax_amount", "")),
            tax_amount=str(data.get("tax_amount", "")),
            total_amount=str(data.get("total_amount", "")),
            tax_rate=str(data.get("tax_rate", "")),
            invoice_type=str(data.get("invoice_type", "")),
            invoice_no=str(data.get("invoice_no", "")),
            category=str(data.get("category", "（未分类）")),
            line_items=str(data.get("line_items", "")),
            archived_path=str(data.get("archived_path", "")),
            status=str(data.get("status", "需人工确认")),
        )
        record.fields_needing_review = set(data.get("fields_needing_review", []))
        reasons = data.get("review_reasons", {})
        if isinstance(reasons, dict):
            record.review_reasons = {
                str(key): [str(item) for item in value]
                for key, value in reasons.items()
                if isinstance(value, list)
            }
        return record
