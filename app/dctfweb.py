from __future__ import annotations

import hashlib
import json
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from app.models import Batch, BatchItem, Receipt


class DCTFWebService:
    def __init__(self, db_path: str = "data/batches.json", receipts_dir: str = "receipts") -> None:
        self.db_path = Path(db_path)
        self.receipts_dir = Path(receipts_dir)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.receipts_dir.mkdir(parents=True, exist_ok=True)

    def _read_db(self) -> dict:
        if not self.db_path.exists():
            return {"batches": []}
        return json.loads(self.db_path.read_text())

    def _write_db(self, payload: dict) -> None:
        self.db_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))

    def create_batch(self, competencia: str, cnpjs: list[str], created_by: str) -> Batch:
        payload = self._read_db()
        batch = Batch(
            batch_id=str(uuid.uuid4()),
            competencia=competencia,
            created_by=created_by,
            items=[BatchItem(cnpj=cnpj) for cnpj in cnpjs],
        )
        payload["batches"].append(batch.to_dict())
        self._write_db(payload)
        return batch

    def list_batches(self) -> list[Batch]:
        payload = self._read_db()
        return [Batch.from_dict(item) for item in payload.get("batches", [])]

    def get_batch(self, batch_id: str) -> Batch:
        for batch in self.list_batches():
            if batch.batch_id == batch_id:
                return batch
        raise ValueError(f"Batch {batch_id} não encontrado")

    def process_batch(self, batch_id: str, user: str) -> Batch:
        payload = self._read_db()
        updated: dict | None = None
        for index, batch_data in enumerate(payload.get("batches", [])):
            if batch_data["batch_id"] != batch_id:
                continue

            batch = Batch.from_dict(batch_data)
            for item in batch.items:
                if item.status == "completed":
                    continue

                item.status = "sent"
                if self._simulate_failure(item.cnpj, batch.competencia):
                    item.status = "error"
                    item.error_message = "Falha de transmissão simulada. Reprocessar item."
                    continue

                receipt = self._build_receipt(
                    cnpj=item.cnpj,
                    competencia=batch.competencia,
                    user=user,
                )
                self._persist_receipt(receipt)
                item.status = "completed"
                item.error_message = None
                item.receipt = receipt

            updated = batch.to_dict()
            payload["batches"][index] = updated
            break

        if updated is None:
            raise ValueError(f"Batch {batch_id} não encontrado")

        self._write_db(payload)
        return Batch.from_dict(updated)

    def reprocess_errors(self, batch_id: str, user: str) -> Batch:
        payload = self._read_db()
        updated: dict | None = None

        for index, batch_data in enumerate(payload.get("batches", [])):
            if batch_data["batch_id"] != batch_id:
                continue

            batch = Batch.from_dict(batch_data)
            for item in batch.items:
                if item.status != "error":
                    continue

                receipt = self._build_receipt(item.cnpj, batch.competencia, user)
                self._persist_receipt(receipt)
                item.status = "completed"
                item.error_message = None
                item.receipt = receipt

            updated = batch.to_dict()
            payload["batches"][index] = updated
            break

        if updated is None:
            raise ValueError(f"Batch {batch_id} não encontrado")

        self._write_db(payload)
        return Batch.from_dict(updated)

    def export_receipts_zip(self, batch_id: str, output_file: str | None = None) -> Path:
        batch = self.get_batch(batch_id)
        output_path = Path(output_file or f"receipts/{batch.competencia}_{batch.batch_id}.zip")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for item in batch.items:
                if not item.receipt:
                    continue
                receipt_name = f"{item.receipt.cnpj}_{item.receipt.competencia}_{item.receipt.protocolo}.json"
                receipt_file = self.receipts_dir / receipt_name
                if receipt_file.exists():
                    archive.write(receipt_file, arcname=receipt_name)

        return output_path

    def _build_receipt(self, cnpj: str, competencia: str, user: str) -> Receipt:
        now = datetime.now(timezone.utc).isoformat()
        seed = f"{cnpj}:{competencia}:{now}"
        protocolo = hashlib.sha256(seed.encode()).hexdigest()[:16].upper()
        file_id = hashlib.md5(seed.encode()).hexdigest()  # noqa: S324
        return Receipt(
            cnpj=cnpj,
            competencia=competencia,
            protocolo=protocolo,
            transmitted_at=now,
            user=user,
            file_id=file_id,
        )

    def _persist_receipt(self, receipt: Receipt) -> None:
        filename = f"{receipt.cnpj}_{receipt.competencia}_{receipt.protocolo}.json"
        target = self.receipts_dir / filename
        target.write_text(json.dumps(receipt.to_dict(), ensure_ascii=False, indent=2))

    @staticmethod
    def _simulate_failure(cnpj: str, competencia: str) -> bool:
        key = f"{cnpj}{competencia}"
        checksum = sum(ord(ch) for ch in key)
        return checksum % 5 == 0
