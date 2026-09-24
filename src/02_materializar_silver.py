"""Validar Bronze e materializar Silver em Parquet, sem deduplicação.

Uso: python src/02_materializar_silver.py --bronze-run-id ID --validate-only
     python src/02_materializar_silver.py --bronze-run-id ID --silver-run-id ID

Chave técnica: (hash_arquivo_fonte, numero_linha_fonte). Não identifica uma
pessoa fora desta versão da fonte. O contrato usa categorias e nomes em português.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAMES = {
    "recency": "meses_desde_ultima_compra",
    "history_segment": "faixa_gasto_12_meses_usd",
    "history": "gasto_12_meses_usd",
    "mens": "comprou_masculino_12_meses",
    "womens": "comprou_feminino_12_meses",
    "zip_code": "zona_localizacao",
    "newbie": "cliente_novo_12_meses",
    "channel": "canal_compra_historico",
    "segment": "grupo_experimental",
    "visit": "visitou_site_14_dias",
    "conversion": "comprou_14_dias",
    "spend": "gasto_14_dias_usd",
}
MAPS = {
    "segment": {"Mens E-Mail": "E-mail masculino", "Womens E-Mail": "E-mail feminino", "No E-Mail": "Sem e-mail"},
    "channel": {"Phone": "Telefone", "Web": "Internet", "Multichannel": "Multicanal"},
    "zip_code": {"Rural": "Rural", "Surburban": "Suburbana", "Urban": "Urbana"},
    "history_segment": {
        "1) $0 - $100": "1) US$ 0 - 100",
        "2) $100 - $200": "2) US$ 100 - 200",
        "3) $200 - $350": "3) US$ 200 - 350",
        "4) $350 - $500": "4) US$ 350 - 500",
        "5) $500 - $750": "5) US$ 500 - 750",
        "6) $750 - $1,000": "6) US$ 750 - 1.000",
        "7) $1,000 +": "7) US$ 1.000 ou mais",
    },
}
BOUNDS = [(Decimal("0"), Decimal("100")), (Decimal("100"), Decimal("200")),
          (Decimal("200"), Decimal("350")), (Decimal("350"), Decimal("500")),
          (Decimal("500"), Decimal("750")), (Decimal("750"), Decimal("1000")),
          (Decimal("1000"), None)]


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def decimal_usd(value: str, line: int, column: str) -> Decimal:
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"Linha {line}: {column} inválido: {value!r}") from exc
    if not number.is_finite() or number < 0 or number != number.quantize(Decimal("0.01")):
        raise ValueError(f"Linha {line}: {column} precisa ser não negativo e ter até 2 casas decimais")
    return number


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bronze-run-id", required=True)
    parser.add_argument("--silver-run-id")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    if not args.bronze_run_id.isalnum() or (args.silver_run_id and not args.silver_run_id.isalnum()):
        parser.error("IDs de execução devem conter somente letras e números")
    if not args.validate_only and not args.silver_run_id:
        parser.error("Informe --silver-run-id ou use --validate-only")
    manifest_path = ROOT / "metadata/runs" / args.bronze_run_id / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    bronze = ROOT / manifest["bronze_relative_path"]
    file_hash = digest(bronze)
    if file_hash != manifest["source_sha256"]:
        raise ValueError("Hash da Bronze diverge do manifesto: processamento bloqueado")
    clean = []
    with bronze.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != list(NAMES):
            raise ValueError(f"Cabeçalho inesperado: {reader.fieldnames}")
        for line, source in enumerate(reader, start=1):
            if None in source or any(value is None or not value.strip() for value in source.values()):
                raise ValueError(f"Linha {line}: campo ausente ou vazio")
            record = {"hash_arquivo_fonte": file_hash, "numero_linha_fonte": line}
            recency = int(source["recency"])
            if not 1 <= recency <= 12:
                raise ValueError(f"Linha {line}: recency fora de 1 a 12")
            record[NAMES["recency"]] = recency
            history = decimal_usd(source["history"], line, "history")
            spend = decimal_usd(source["spend"], line, "spend")
            band = source["history_segment"]
            if band not in MAPS["history_segment"]:
                raise ValueError(f"Linha {line}: faixa desconhecida {band!r}")
            band_no = int(band[0]) - 1
            lower, upper = BOUNDS[band_no]
            if history < lower or (upper is not None and history >= upper):
                raise ValueError(f"Linha {line}: history não corresponde à faixa")
            for column in ("mens", "womens", "newbie", "visit", "conversion"):
                if source[column] not in ("0", "1"):
                    raise ValueError(f"Linha {line}: {column} não é 0 ou 1")
                record[NAMES[column]] = int(source[column])
            if source["conversion"] == "1" and (source["visit"] != "1" or spend == 0):
                raise ValueError(f"Linha {line}: compra sem visita ou gasto")
            if source["conversion"] == "0" and spend != 0:
                raise ValueError(f"Linha {line}: gasto sem compra")
            for column in MAPS:
                if source[column] not in MAPS[column]:
                    raise ValueError(f"Linha {line}: {column} tem categoria não mapeada")
                record[NAMES[column]] = MAPS[column][source[column]]
            record[NAMES["history"]] = history
            record[NAMES["spend"]] = spend
            clean.append(record)
    if len(clean) != manifest["record_count"]:
        raise ValueError("Contagem Bronze/Silver divergente")
    if len({(r["hash_arquivo_fonte"], r["numero_linha_fonte"]) for r in clean}) != len(clean):
        raise ValueError("Chave técnica não é única")
    groups = dict(sorted(Counter(r["grupo_experimental"] for r in clean).items()))
    summary = {"bronze_run_id": args.bronze_run_id, "silver_run_id": args.silver_run_id,
               "source_sha256": file_hash, "bronze_records": len(clean), "silver_records": len(clean),
               "unique_technical_keys": len(clean), "groups": groups, "validation": "approved"}
    if args.validate_only:
        print(json.dumps({**summary, "mode": "validate_only"}, indent=2, ensure_ascii=False))
        return
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise SystemExit("pyarrow ausente. No ambiente Python do projeto, execute: python -m pip install -r requirements.txt") from exc
    schema = pa.schema([
        pa.field("hash_arquivo_fonte", pa.string()), pa.field("numero_linha_fonte", pa.int32()),
        pa.field("meses_desde_ultima_compra", pa.int16()),
        pa.field("faixa_gasto_12_meses_usd", pa.string()),
        pa.field("gasto_12_meses_usd", pa.decimal128(12, 2)),
        pa.field("comprou_masculino_12_meses", pa.int8()), pa.field("comprou_feminino_12_meses", pa.int8()),
        pa.field("zona_localizacao", pa.string()), pa.field("cliente_novo_12_meses", pa.int8()),
        pa.field("canal_compra_historico", pa.string()), pa.field("grupo_experimental", pa.string()),
        pa.field("visitou_site_14_dias", pa.int8()), pa.field("comprou_14_dias", pa.int8()),
        pa.field("gasto_14_dias_usd", pa.decimal128(12, 2)),
    ])
    table = pa.Table.from_pylist(clean, schema=schema)
    out = ROOT / "data/02_silver" / args.silver_run_id / "experimento_clientes.parquet"
    audit = ROOT / "quality/runs" / args.silver_run_id / "validacao_silver.json"
    if out.exists() or audit.exists():
        raise FileExistsError("A execução Silver já existe; escolha outro --silver-run-id")
    out.parent.mkdir(parents=True, exist_ok=True)
    audit.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, out, compression="zstd")
    check = pq.read_table(out)
    if check.num_rows != len(clean) or check.schema != schema:
        out.unlink()
        raise RuntimeError("Falha na reconciliação do Parquet gravado")
    summary["parquet_sha256"] = digest(out)
    summary["parquet_relative_path"] = str(out.relative_to(ROOT)).replace("\\", "/")
    audit.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
