"""Carrega Gold Parquet no SQL Server e reconcilia com a auditoria A/B.

Preparação: executar sql/01_modelo_gold_sql_server.sql no SSMS.
Conexão: variável CRM_SQL_CONNECTION_STRING (nunca gravar credenciais no código).
Uso: python src/09_carregar_gold_sql.py --gold-run-id GOLD01
     python src/09_carregar_gold_sql.py --gold-run-id GOLD01 --execute
Sem --execute, apenas verifica arquivos e conexão. Uma carga concluída pode ser
reverificada sem criar registros duplicados.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATABASE = "ExperimentoCRMVarejoModa"
FACT_COLUMNS = (
    "hash_arquivo_fonte", "numero_linha_fonte", "id_grupo_experimental",
    "meses_desde_ultima_compra", "faixa_gasto_12_meses_usd", "gasto_12_meses_usd",
    "comprou_masculino_12_meses", "comprou_feminino_12_meses", "zona_localizacao",
    "cliente_novo_12_meses", "canal_compra_historico", "visitou_site_14_dias",
    "comprou_14_dias", "gasto_14_dias_usd",
)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def expected_aggregates(audit: dict) -> dict:
    return {name: (item["n"], item["visits"], item["purchases"], Decimal(item["spend_usd"]))
            for name, item in audit["group_reconciliation"].items()}


def sql_aggregates(cursor) -> dict:
    cursor.execute("SELECT grupo_experimental, registros_atribuidos, visitas, compras, gasto_total_usd "
                   "FROM crm.vw_kpis_grupo")
    return {name: (int(n), int(visits), int(purchases), Decimal(str(spend)))
            for name, n, visits, purchases, spend in cursor.fetchall()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold-run-id", required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not args.gold_run_id.isalnum():
        parser.error("ID Gold deve conter somente letras e números")
    try:
        import pyarrow.parquet as pq
        import pyodbc
    except ImportError as exc:
        raise SystemExit("Instale as dependências: python -m pip install pyarrow pyodbc") from exc
    audit = json.loads((ROOT / "quality/runs" / args.gold_run_id / "validacao_gold.json").read_text(encoding="utf-8"))
    receipt = json.loads((ROOT / "docs/execucoes" / args.gold_run_id / "publicacao_azure_gold.json").read_text(encoding="utf-8"))
    if (audit["gold_run_id"] != args.gold_run_id or audit["technical_validation"] != "approved" or
            receipt["gold_run_id"] != args.gold_run_id or receipt["status"] != "approved" or
            len(receipt["files"]) != 4 or not all(item["verified"] for item in receipt["files"])):
        raise ValueError("Gold ou publicação Azure não aprovadas")
    paths = {}
    for name in ("dim_grupo_experimental", "fato_resposta_experimental"):
        item = audit["files"][name]
        local = (ROOT / item["relative_path"]).resolve()
        if not local.is_relative_to(ROOT.resolve()) or digest(local) != item["sha256"]:
            raise ValueError(f"Gold local mudou ou saiu do projeto: {name}")
        if not any(blob["path"] == f"03_gold/{args.gold_run_id}/{local.name}" and
                   blob["sha256"] == item["sha256"] for blob in receipt["files"]):
            raise ValueError(f"Recibo Azure não corresponde ao Parquet: {name}")
        paths[name] = local
    dimension = pq.read_table(paths["dim_grupo_experimental"])
    fact = pq.read_table(paths["fato_resposta_experimental"])
    if (dimension.num_rows != audit["dimension_records"] or fact.num_rows != audit["fact_records"] or
            set(fact.column_names) != set(FACT_COLUMNS) or
            set(dimension.column_names) != {"id_grupo_experimental", "grupo_experimental", "recebeu_email"}):
        raise ValueError("Parquets Gold com esquema ou contagem inesperados")
    connection_string = os.environ.get("CRM_SQL_CONNECTION_STRING")
    if not connection_string:
        raise SystemExit("Configure CRM_SQL_CONNECTION_STRING no terminal; não grave a conexão no repositório")
    conn = pyodbc.connect(connection_string, autocommit=False, timeout=15)
    try:
        cursor = conn.cursor()
        database = cursor.execute("SELECT DB_NAME()").fetchval()
        if database != DATABASE:
            raise ValueError(f"Conexão aponta para {database!r}, esperado {DATABASE!r}")
        if (cursor.execute("SELECT OBJECT_ID(N'crm.dim_grupo_experimental', N'U')").fetchval() is None or
                cursor.execute("SELECT OBJECT_ID(N'crm.fato_resposta_experimental', N'U')").fetchval() is None or
                cursor.execute("SELECT OBJECT_ID(N'crm.vw_kpis_grupo', N'V')").fetchval() is None):
            raise ValueError("Execute primeiro sql/01_modelo_gold_sql_server.sql no SSMS")
        existing_fact = cursor.execute("SELECT COUNT_BIG(*) FROM crm.fato_resposta_experimental").fetchval()
        existing_dim = cursor.execute("SELECT COUNT_BIG(*) FROM crm.dim_grupo_experimental").fetchval()
        if existing_fact or existing_dim:
            if existing_fact != fact.num_rows or existing_dim != dimension.num_rows or sql_aggregates(cursor) != expected_aggregates(audit):
                raise ValueError("Tabelas já contêm dados divergentes; carga bloqueada sem sobrescrever")
            state = "existing_reconciled"
        elif not args.execute:
            state = "ready_to_load"
        else:
            cursor.execute("SET XACT_ABORT ON")
            cursor.executemany(
                "INSERT INTO crm.dim_grupo_experimental "
                "(id_grupo_experimental, grupo_experimental, recebeu_email) VALUES (?,?,?)",
                [(row["id_grupo_experimental"], row["grupo_experimental"], row["recebeu_email"])
                 for row in dimension.to_pylist()],
            )
            placeholders = ",".join("?" for _ in FACT_COLUMNS)
            statement = ("INSERT INTO crm.fato_resposta_experimental (" + ",".join(FACT_COLUMNS) +
                         ") VALUES (" + placeholders + ")")
            rows = fact.to_pylist()
            for start in range(0, len(rows), 1000):
                cursor.executemany(statement, [tuple(row[name] for name in FACT_COLUMNS)
                                               for row in rows[start:start + 1000]])
            if sql_aggregates(cursor) != expected_aggregates(audit):
                raise ValueError("Reconciliação SQL × Gold falhou; transação será desfeita")
            conn.commit()
            state = "loaded_reconciled"
        if state == "ready_to_load":
            print(json.dumps({"status": state, "database": database,
                              "expected_fact_records": fact.num_rows, "expected_dimension_records": dimension.num_rows},
                             indent=2, ensure_ascii=False))
            return
        result = {"gold_run_id": args.gold_run_id, "database": database,
                  "status": state, "fact_records": fact.num_rows, "dimension_records": dimension.num_rows,
                  "group_reconciliation": audit["group_reconciliation"],
                  "validated_utc": datetime.now(timezone.utc).isoformat(),
                  "gold_audit_sha256": digest(ROOT / "quality/runs" / args.gold_run_id / "validacao_gold.json")}
        report = ROOT / "quality/runs" / args.gold_run_id / "reconciliacao_sql.json"
        if report.exists():
            previous = json.loads(report.read_text(encoding="utf-8"))
            if previous["gold_run_id"] != args.gold_run_id or previous["fact_records"] != fact.num_rows:
                raise ValueError("Recibo SQL existente diverge; não sobrescrever")
        else:
            report.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({"status": state, "database": database, "fact_records": fact.num_rows,
                          "dimension_records": dimension.num_rows, "receipt": str(report)},
                         indent=2, ensure_ascii=False))
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
