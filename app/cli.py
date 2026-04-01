from __future__ import annotations

import argparse
import json

from app.dctfweb import DCTFWebService


def cmd_create(args: argparse.Namespace) -> None:
    service = DCTFWebService()
    batch = service.create_batch(args.competencia, args.cnpjs, args.user)
    print(json.dumps(batch.to_dict(), ensure_ascii=False, indent=2))


def cmd_list(_: argparse.Namespace) -> None:
    service = DCTFWebService()
    payload = [batch.to_dict() for batch in service.list_batches()]
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def cmd_process(args: argparse.Namespace) -> None:
    service = DCTFWebService()
    batch = service.process_batch(args.batch_id, args.user)
    print(json.dumps(batch.to_dict(), ensure_ascii=False, indent=2))


def cmd_reprocess(args: argparse.Namespace) -> None:
    service = DCTFWebService()
    batch = service.reprocess_errors(args.batch_id, args.user)
    print(json.dumps(batch.to_dict(), ensure_ascii=False, indent=2))


def cmd_export(args: argparse.Namespace) -> None:
    service = DCTFWebService()
    target = service.export_receipts_zip(args.batch_id, args.output)
    print(str(target))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MVP DCTFWeb em lote")
    sub = parser.add_subparsers(required=True)

    create = sub.add_parser("create-batch", help="Criar lote para transmissão")
    create.add_argument("--competencia", required=True, help="Formato MM-AAAA")
    create.add_argument("--user", required=True, help="Usuário responsável")
    create.add_argument("--cnpjs", nargs="+", required=True, help="Lista de CNPJs")
    create.set_defaults(func=cmd_create)

    ls_cmd = sub.add_parser("list-batches", help="Listar lotes")
    ls_cmd.set_defaults(func=cmd_list)

    process = sub.add_parser("process-batch", help="Processar transmissão do lote")
    process.add_argument("--batch-id", required=True)
    process.add_argument("--user", required=True)
    process.set_defaults(func=cmd_process)

    reprocess = sub.add_parser("reprocess-errors", help="Reprocessar itens com erro")
    reprocess.add_argument("--batch-id", required=True)
    reprocess.add_argument("--user", required=True)
    reprocess.set_defaults(func=cmd_reprocess)

    export = sub.add_parser("export-receipts", help="Exportar recibos em ZIP")
    export.add_argument("--batch-id", required=True)
    export.add_argument("--output", required=False)
    export.set_defaults(func=cmd_export)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
