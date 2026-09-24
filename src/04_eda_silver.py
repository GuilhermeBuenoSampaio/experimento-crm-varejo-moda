"""EDA reprodutível da Silver aprovada, com auditoria e relatório automáticos.

Uso: python src/04_eda_silver.py --silver-run-id SILVER01 --eda-run-id EDA01
     python src/04_eda_silver.py --silver-run-id SILVER01 --eda-run-id EDA01 --execute

Sem --execute, valida e mostra somente um resumo. A análise A/B por grupo é
uma etapa posterior e usa o contrato analítico versionado.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from statistics import mean, stdev

ROOT = Path(__file__).resolve().parents[1]
GROUP = "grupo_experimental"
CONTROL = "Sem e-mail"
TREATMENTS = ("E-mail masculino", "E-mail feminino")
NUMERIC = ("meses_desde_ultima_compra", "gasto_12_meses_usd")
BINARY = ("comprou_masculino_12_meses", "comprou_feminino_12_meses", "cliente_novo_12_meses")
CATEGORICAL = ("faixa_gasto_12_meses_usd", "zona_localizacao", "canal_compra_historico")
OUTCOMES = ("visitou_site_14_dias", "comprou_14_dias", "gasto_14_dias_usd")


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def percentile(values: list[Decimal], fraction: str) -> Decimal:
    ordered = sorted(values)
    position = Decimal(len(ordered) - 1) * Decimal(fraction)
    lo = int(position)
    weight = position - lo
    return ordered[lo] * (1 - weight) + ordered[min(lo + 1, len(ordered) - 1)] * weight


def distribution(values: list[int | Decimal]) -> dict:
    numbers = [Decimal(str(value)) for value in values]
    return {
        "min": str(min(numbers)), "q1": str(percentile(numbers, "0.25")),
        "median": str(percentile(numbers, "0.5")), "mean": str(sum(numbers) / len(numbers)),
        "q3": str(percentile(numbers, "0.75")), "p95": str(percentile(numbers, "0.95")),
        "p99": str(percentile(numbers, "0.99")), "max": str(max(numbers)),
        "zeros": sum(value == 0 for value in numbers),
    }


def smd(treatment: list[float], control: list[float]) -> float | None:
    """Diferença padronizada descritiva; valor absoluto, sem teste de hipótese."""
    avg_t, avg_c = mean(treatment), mean(control)
    variance_t = stdev(treatment) ** 2 if len(treatment) > 1 else 0.0
    variance_c = stdev(control) ** 2 if len(control) > 1 else 0.0
    scale = math.sqrt((variance_t + variance_c) / 2)
    return round(abs(avg_t - avg_c) / scale, 6) if scale else (0.0 if avg_t == avg_c else None)


def markdown(result: dict) -> str:
    lines = [
        "# EDA da Silver — validação", "",
        f"- Execução: `{result['eda_run_id']}`; Silver: `{result['silver_run_id']}`.",
        f"- Registros: **{result['records']:,}**; chaves técnicas distintas: **{result['unique_keys']:,}**.",
        f"- SHA-256 do Parquet: `{result['parquet_sha256']}`.",
        "- Granularidade: registro experimental, sem ID de cliente. Linhas com atributos iguais foram preservadas.",
        "", "## Grupos sorteados", "", "| Grupo | Registros | Participação |", "|---|---:|---:|",
    ]
    for group, n in result["groups"].items():
        lines.append(f"| {group} | {n:,} | {n / result['records']:.2%} |")
    lines += ["", "## Distribuições gerais", "", "| Variável | Mínimo | Q1 | Mediana | Média | Q3 | P95 | P99 | Máximo | Zeros |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for name, stats in result["numeric_distributions"].items():
        lines.append("| " + name + " | " + " | ".join(str(stats[k]) for k in
                     ("min", "q1", "median", "mean", "q3", "p95", "p99", "max", "zeros")) + " |")
    lines += ["", "## Equilíbrio descritivo antes da campanha", "",
              "Diferença padronizada absoluta (SMD) dos atributos históricos em cada e-mail versus controle. "
              "Ela descreve diferenças observáveis; não comprova o mecanismo de sorteio nem substitui a análise causal.", "",
              "| Atributo | E-mail masculino | E-mail feminino |", "|---|---:|---:|"]
    for name, values in result["baseline_smd"].items():
        lines.append(f"| {name} | {values[TREATMENTS[0]]} | {values[TREATMENTS[1]]} |")
    lines += ["", "Distribuições categóricas e ausências por coluna estão no JSON da execução.", "",
              "## Resultados observados no conjunto completo", "",
              "Estas são descrições agregadas de todos os grupos; o efeito de cada campanha será calculado "
              "na etapa A/B com os denominadores e testes do contrato analítico.", ""]
    overall = result["outcomes_overall"]
    lines += [f"- Visitas: {overall['visits']:,} ({overall['visits'] / result['records']:.2%}).",
              f"- Compras: {overall['conversions']:,} ({overall['conversions'] / result['records']:.2%}).",
              f"- Gasto total: US$ {Decimal(overall['spend_usd']):,.2f}.", "",
              "## Limitações", "",
              "Não existem ID de cliente, abertura, clique, custo de campanha ou margem. "
              "Não estimar essas variáveis nem deduplicar registros sem evidência adicional.", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--silver-run-id", required=True)
    parser.add_argument("--eda-run-id", required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not args.silver_run_id.isalnum() or not args.eda_run_id.isalnum():
        parser.error("IDs devem conter apenas letras e números")
    audit_path = ROOT / "quality/runs" / args.silver_run_id / "validacao_silver.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if audit["validation"] != "approved" or audit["silver_run_id"] != args.silver_run_id:
        raise ValueError("Silver sem aprovação correspondente")
    parquet = ROOT / audit["parquet_relative_path"]
    if digest(parquet) != audit["parquet_sha256"]:
        raise ValueError("Hash do Parquet diferente da auditoria Silver")
    contract = ROOT / "metadata/contrato_analitico.md"
    if not contract.is_file():
        raise FileNotFoundError("Contrato analítico ausente")
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise SystemExit("Instale as dependências: python -m pip install -r requirements.txt") from exc
    table = pq.read_table(parquet)
    expected = {GROUP, "hash_arquivo_fonte", "numero_linha_fonte", *NUMERIC, *BINARY, *CATEGORICAL, *OUTCOMES}
    if set(table.column_names) != expected:
        raise ValueError("Colunas da Silver divergentes do contrato conhecido")
    rows = table.to_pylist()
    if not rows or len(rows) != audit["silver_records"] or len(rows) != audit["bronze_records"]:
        raise ValueError("Contagem da Silver divergente da auditoria")
    nulls = {name: table[name].null_count for name in table.column_names}
    if any(nulls.values()):
        raise ValueError(f"Silver contém valores nulos: {nulls}")
    if any(row[name] not in (0, 1) for row in rows for name in (*BINARY, "visitou_site_14_dias", "comprou_14_dias")):
        raise ValueError("Indicador binário fora de 0/1")
    if any(row[name] < 0 for row in rows for name in ("gasto_12_meses_usd", "gasto_14_dias_usd")):
        raise ValueError("Gasto negativo na Silver")
    keys = {(row["hash_arquivo_fonte"], row["numero_linha_fonte"]) for row in rows}
    if len(keys) != len(rows) or any(row["hash_arquivo_fonte"] != audit["source_sha256"] for row in rows):
        raise ValueError("Chaves técnicas ou hash da fonte divergentes")
    groups = dict(sorted(Counter(row[GROUP] for row in rows).items()))
    if groups != audit["groups"] or set(groups) != {CONTROL, *TREATMENTS}:
        raise ValueError("Grupos experimentais divergentes da Silver aprovada")
    if any(row["comprou_14_dias"] > row["visitou_site_14_dias"] or
           (row["comprou_14_dias"] == 0 and row["gasto_14_dias_usd"] != 0) or
           (row["comprou_14_dias"] == 1 and row["gasto_14_dias_usd"] <= 0) for row in rows):
        raise ValueError("Resultado de visita, compra e gasto inconsistente")
    by_group = {name: [row for row in rows if row[GROUP] == name] for name in (CONTROL, *TREATMENTS)}
    numeric = {name: distribution([row[name] for row in rows]) for name in (*NUMERIC, "gasto_14_dias_usd")}
    categories = {name: {group: dict(sorted(Counter(row[name] for row in sample).items()))
                         for group, sample in by_group.items()} for name in CATEGORICAL}
    baseline_smd = {name: {group: smd([float(row[name]) for row in by_group[group]],
                                         [float(row[name]) for row in by_group[CONTROL]])
                           for group in TREATMENTS} for name in (*NUMERIC, *BINARY)}
    result = {
        "eda_run_id": args.eda_run_id, "silver_run_id": args.silver_run_id,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "technical_validation": "approved", "analytic_review": "pending", "records": len(rows), "unique_keys": len(keys),
        "parquet_relative_path": audit["parquet_relative_path"],
        "parquet_sha256": audit["parquet_sha256"], "contract_sha256": digest(contract),
        "groups": groups, "nulls": nulls, "numeric_distributions": numeric,
        "categorical_distributions_by_group": categories,
        "baseline_smd": baseline_smd,
        "outcomes_overall": {
            "visits": sum(row["visitou_site_14_dias"] for row in rows),
            "conversions": sum(row["comprou_14_dias"] for row in rows),
            "spend_usd": str(sum((row["gasto_14_dias_usd"] for row in rows), Decimal("0"))),
        },
    }
    if not args.execute:
        print(json.dumps({"mode": "validate_only", "technical_validation": result["technical_validation"], "records": result["records"],
                          "groups": groups, "nulls": nulls}, indent=2, ensure_ascii=False))
        return
    report_dir = ROOT / "docs/execucoes" / args.eda_run_id
    quality_dir = ROOT / "quality/runs" / args.eda_run_id
    if report_dir.exists() or quality_dir.exists():
        raise FileExistsError("ID da EDA já utilizado; não sobrescrever execução")
    report_dir.mkdir(parents=True)
    quality_dir.mkdir(parents=True)
    (quality_dir / "validacao_eda.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (report_dir / "04_eda_silver.md").write_text(markdown(result), encoding="utf-8")
    print(json.dumps({"technical_validation": "approved", "analytic_review": "pending", "eda_run_id": args.eda_run_id,
                      "report": str(report_dir / "04_eda_silver.md"),
                      "audit": str(quality_dir / "validacao_eda.json")}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
