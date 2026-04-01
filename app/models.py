from __future__ import annotations

from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Literal

ItemStatus = Literal["pending", "sent", "error", "completed"]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Receipt:
    cnpj: str
    competencia: str
    protocolo: str
    transmitted_at: str
    user: str
    file_id: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BatchItem:
    cnpj: str
    status: ItemStatus = "pending"
    error_message: str | None = None
    receipt: Receipt | None = None

    def to_dict(self) -> dict:
        data = asdict(self)
        if self.receipt is None:
            data["receipt"] = None
        return data


@dataclass
class Batch:
    batch_id: str
    competencia: str
    created_by: str
    created_at: str = field(default_factory=utc_now_iso)
    items: list[BatchItem] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "batch_id": self.batch_id,
            "competencia": self.competencia,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "items": [item.to_dict() for item in self.items],
        }

    @staticmethod
    def from_dict(data: dict) -> "Batch":
        items: list[BatchItem] = []
        for item_data in data.get("items", []):
            receipt_data = item_data.get("receipt")
            receipt = Receipt(**receipt_data) if receipt_data else None
            items.append(
                BatchItem(
                    cnpj=item_data["cnpj"],
                    status=item_data.get("status", "pending"),
                    error_message=item_data.get("error_message"),
                    receipt=receipt,
                )
            )
        return Batch(
            batch_id=data["batch_id"],
            competencia=data["competencia"],
            created_by=data["created_by"],
            created_at=data.get("created_at", utc_now_iso()),
            items=items,
        )
