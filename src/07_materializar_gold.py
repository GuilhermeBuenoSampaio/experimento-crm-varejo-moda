"""Materializa dimensão de grupo e fato de respostas em Parquet.

Uso: python src/07_materializar_gold.py --silver-run-id SILVER01 --ab-run-id AB01 --gold-run-id GOLD01
     python src/07_materializar_gold.py --silver-run-id SILVER01 --ab-run-id AB01 --gold-run-id GOLD01 --execute
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GROUPS = ((0, "Sem e-mail", False), (1, "E-mail masculino", True), (2, "E-mail feminino", True))
GROUP_IDS = {name: key for key, name, _ in GROUPS}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--silver-run-id", required=True)
    parser.add_argument("--ab-run-id", required=True)
    parser.add_argument("--gold-run-id", required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if any(not value.isalnum() for value in (args.silver_run_id, args.ab_run_id, args.gold_run_id)):
        parser.error("IDs só podem conter letras e números")
    silver = json.loads((ROOT / "quality/runs" / args.silver_run_id / "validacao_silver.json").read_text(encoding="utf-8"))
    ab = json.loads((ROOT / "quality/runs" / args.ab_run_id / "validacao_ab.json").read_text(encoding="utf-8"))
    source = ROOT / silver["parquet_relative_path"]
    if (silver["validation"] != "approved" or silver["silver_run_id"] != args.silver_run_id or
            ab["technical_validation"] != "approved" or ab["silver_run_id"] != args.silver_run_id or
            ab["ab_run_id"] != args.ab_run_id or ab["silver_parquet_sha256"] != silver["parquet_sha256"] or
            digest(source) != silver["parquet_sha256"]):
        raise ValueError("Auditorias ou SHA-256 Silver/AB incompatíveis")
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise SystemExit("Instale as dependências: python -m pip install -r requirements.txt") from exc
    table = pq.read_table(source)
    if table.num_rows != silver["silver_records"]:
        raise ValueError("Quantidade da Silver divergente")
    expected_columns = {
        "hash_arquivo_fonte", "numero_linha_fonte", "meses_desde_ultima_compra",
        "faixa_gasto_12_meses_usd", "gasto_12_meses_usd", "comprou_masculino_12_meses",
        "comprou_feminino_12_meses", "zona_localizacao", "cliente_novo_12_meses",
        "canal_compra_historico", "grupo_experimental", "visitou_site_14_dias",
        "comprou_14_dias", "gasto_14_dias_usd",
    }
    if set(table.column_names) != expected_columns or any(column.null_count for column in table.columns):
        raise ValueError("Esquema ou valores nulos inesperados na Silver")
    rows = table.to_pylist()
    if any(row["grupo_experimental"] not in GROUP_IDS for row in rows):
        raise ValueError("Grupo experimental sem dimensão")
    facts = [{**{key: value for key, value in row.items() if key != "grupo_experimental"},
              "id_grupo_experimental": GROUP_IDS[row["grupo_experimental"]]} for row in rows]
    if len({(row["hash_arquivo_fonte"], row["numero_linha_fonte"]) for row in facts}) != len(facts):
        raise ValueError("Chave técnica repetida na Gold")
    totals = defaultdict(lambda: {"n": 0, "visits": 0, "purchases": 0, "spend": Decimal("0")})
    for row in facts:
        item = totals[row["id_grupo_experimental"]]
        item["n"] += 1
        item["visits"] += row["visitou_site_14_dias"]
        item["purchases"] += row["comprou_14_dias"]
        item["spend"] += row["gasto_14_dias_usd"]
    for key, name, _ in GROUPS:
        item, reference = totals[key], ab["groups"][name]
        if (item["n"] != reference["n"] or item["visits"] != reference["visits"] or
                item["purchases"] != reference["purchases"] or
                item["spend"] != Decimal(reference["spend_usd"])):
            raise ValueError(f"Gold não reconcilia com AB01 no grupo {name}")
    dimension_schema = pa.schema([
        pa.field("id_grupo_experimental", pa.int8(), nullable=False),
        pa.field("grupo_experimental", pa.string(), nullable=False),
        pa.field("recebeu_email", pa.bool_(), nullable=False),
    ])
    dim = pa.Table.from_pylist([dict(zip(("id_grupo_experimental", "grupo_experimental", "recebeu_email"), group))
                                for group in GROUPS], schema=dimension_schema)
    fact_schema = pa.schema([field for field in table.schema if field.name != "grupo_experimental"] +
                            [pa.field("id_grupo_experimental", pa.int8(), nullable=False)])
    fact = pa.Table.from_pylist(facts, schema=fact_schema)
    summary = {"gold_run_id": args.gold_run_id, "silver_run_id": args.silver_run_id,
               "ab_run_id": args.ab_run_id, "source_sha256": silver["parquet_sha256"],
               "created_utc": datetime.now(timezone.utc).isoformat(),
               "technical_validation": "approved", "analytic_review": ab["analytic_review"],
               "fact_records": fact.num_rows, "dimension_records": dim.num_rows,
               "grain": "um registro experimental por linha; não é um ID de pessoa",
               "group_reconciliation": {name: {"n": totals[key]["n"], "visits": totals[key]["visits"],
                                                "purchases": totals[key]["purchases"],
                                                "spend_usd": str(totals[key]["spend"])}
                                        for key, name, _ in GROUPS}}
    if not args.execute:
        print(json.dumps({**summary, "mode": "validate_only"}, indent=2, ensure_ascii=False))
        return
    output = ROOT / "data/03_gold" / args.gold_run_id
    audit = ROOT / "quality/runs" / args.gold_run_id / "validacao_gold.json"
    report = ROOT / "docs/execucoes" / args.gold_run_id / "07_gold_validacao.md"
    if output.exists() or audit.exists() or report.exists():
        raise FileExistsError("ID Gold já existe; não sobrescrever")
    output.mkdir(parents=True)
    audit.parent.mkdir(parents=True)
    report.parent.mkdir(parents=True)
    paths = {"dim_grupo_experimental": output / "dim_grupo_experimental.parquet",
             "fato_resposta_experimental": output / "fato_resposta_experimental.parquet"}
    pq.write_table(dim, paths["dim_grupo_experimental"], compression="zstd")
    pq.write_table(fact, paths["fato_resposta_experimental"], compression="zstd")
    for name, expected in (("dim_grupo_experimental", dim), ("fato_resposta_experimental", fact)):
        check = pq.read_table(paths[name])
        if check.num_rows != expected.num_rows or check.schema != expected.schema:
            raise RuntimeError(f"Falha na leitura de conferência: {name}")
    summary["files"] = {name: {"relative_path": str(path.relative_to(ROOT)).replace("\\", "/"),
                               "sha256": digest(path), "records": pq.read_metadata(path).num_rows}
                        for name, path in paths.items()}
    audit.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report.write_text(
        f"# Gold {args.gold_run_id} — validação\n\n"
        f"- Silver: `{args.silver_run_id}`; análise A/B: `{args.ab_run_id}`.\n"
        f"- Dimensão: 3 grupos; fato: {fact.num_rows:,} registros experimentais.\n"
        "- Chave da fato: (hash_arquivo_fonte, numero_linha_fonte). Não é ID de pessoa.\n"
        "- Chave estrangeira: id_grupo_experimental. Todas as linhas conciliadas com a análise A/B.\n"
        "- Arquivos e hashes SHA-256 estão em quality/runs/" + args.gold_run_id + "/validacao_gold.json.\n"
        "- Regras de métricas: compras e visitas / COUNT(*) do grupo; gasto / COUNT(*) do grupo.\n",
        encoding="utf-8")
    print(json.dumps({"technical_validation": "approved", "report": str(report),
                      "audit": str(audit), "files": summary["files"]}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
