"""Analisa os dois e-mails versus controle usando a Silver aprovada.

Uso: python src/06_analisar_ab.py --silver-run-id SILVER01 --eda-run-id EDA01 --ab-run-id AB01
     python src/06_analisar_ab.py --silver-run-id SILVER01 --eda-run-id EDA01 --ab-run-id AB01 --execute
Sem --execute, apresenta o cálculo sem gravar arquivos.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from statistics import NormalDist

ROOT = Path(__file__).resolve().parents[1]
CONTROL = "Sem e-mail"
TREATMENTS = ("E-mail masculino", "E-mail feminino")
NORMAL = NormalDist()
ALPHA = 0.05
COMPARISONS = len(TREATMENTS)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def compare(treatment: dict, control: dict) -> dict:
    nt, nc = treatment["n"], control["n"]
    xt, xc = treatment["purchases"], control["purchases"]
    if any(value < 5 for value in (xt, xc, nt - xt, nc - xc)):
        raise ValueError("Menos de cinco compras/não compras em algum braço; revisar método de inferência")
    pt, pc = xt / nt, xc / nc
    delta = pt - pc
    pooled = (xt + xc) / (nt + nc)
    se_null = math.sqrt(pooled * (1 - pooled) * (1 / nt + 1 / nc))
    z = delta / se_null
    p_raw = math.erfc(abs(z) / math.sqrt(2))
    se_ci = math.sqrt(pt * (1 - pt) / nt + pc * (1 - pc) / nc)
    critical = NORMAL.inv_cdf(1 - ALPHA / (2 * COMPARISONS))
    return {
        "difference_pp": 100 * delta,
        "relative_uplift_pct": 100 * delta / pc if pc else None,
        "z_pooled": z,
        "p_raw_two_sided": p_raw,
        "p_bonferroni": min(1.0, COMPARISONS * p_raw),
        "ci_97_5_difference_pp": [100 * (delta - critical * se_ci), 100 * (delta + critical * se_ci)],
        "significant_family_5pct": min(1.0, COMPARISONS * p_raw) < ALPHA,
    }


def report(result: dict) -> str:
    lines = ["# Análise A/B — conversão em 14 dias", "",
             f"- Execução: `{result['ab_run_id']}`; Silver: `{result['silver_run_id']}`; EDA: `{result['eda_run_id']}`.",
             "- Unidade: registro sorteado. A chave técnica identifica linha, não pessoa.",
             "- Métrica principal: compras / todos os registros atribuídos a cada grupo.",
             "- Testes bilaterais: z de duas proporções; dois p ajustados por Bonferroni; "
             "intervalos normais de 97,5% para a diferença em pontos percentuais.",
             "", "## Grupos", "", "| Grupo | Registros | Compras | Conversão | Visitas | Taxa de visita | Gasto USD | USD por registro |",
             "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for name in (CONTROL, *TREATMENTS):
        item = result["groups"][name]
        lines.append(f"| {name} | {item['n']:,} | {item['purchases']:,} | {item['conversion_rate']:.3%} "
                     f"| {item['visits']:,} | {item['visit_rate']:.3%} | {Decimal(item['spend_usd']):,.2f} "
                     f"| {Decimal(item['spend_per_assigned_usd']):,.4f} |")
    lines.extend(["", "## Cada e-mail versus controle", "",
                  "| Campanha | Diferença (pp) | Uplift relativo | IC 97,5% (pp) | p bruto | p ajustado | Significativo a 5%? |",
                  "|---|---:|---:|---|---:|---:|---|"])
    for name in TREATMENTS:
        item = result["comparisons"][name]
        uplift = f"{item['relative_uplift_pct']:.2f}%" if item["relative_uplift_pct"] is not None else "Indefinido"
        low, high = item["ci_97_5_difference_pp"]
        lines.append(f"| {name} | {item['difference_pp']:+.4f} | {uplift} | [{low:+.4f}; {high:+.4f}] "
                     f"| {item['p_raw_two_sided']:.6g} | {item['p_bonferroni']:.6g} "
                     f"| {'Sim' if item['significant_family_5pct'] else 'Não'} |")
    lines.extend(["", "## Interpretação e limites", "",
                  "Diferença positiva significa maior conversão observada no e-mail que no controle. "
                  "Significância estatística, quando presente, não demonstra rentabilidade.",
                  "Visitas e receita por registro são indicadores secundários descritivos; não receberam teste nesta versão.",
                  "Não há ID de pessoa para verificar independência de registros, nem abertura, clique, custo ou margem. "
                  "Não deduplicar linhas com atributos iguais.",
                  "A revisão analítica e a recomendação comercial ficam pendentes após a conferência deste relatório.", ""])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--silver-run-id", required=True)
    parser.add_argument("--eda-run-id", required=True)
    parser.add_argument("--ab-run-id", required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if any(not value.isalnum() for value in (args.silver_run_id, args.eda_run_id, args.ab_run_id)):
        parser.error("IDs devem conter somente letras e números")
    audit = json.loads((ROOT / "quality/runs" / args.silver_run_id / "validacao_silver.json").read_text(encoding="utf-8"))
    eda = json.loads((ROOT / "quality/runs" / args.eda_run_id / "validacao_eda.json").read_text(encoding="utf-8"))
    contract = ROOT / "metadata/contrato_analitico.md"
    parquet = ROOT / audit["parquet_relative_path"]
    if audit["validation"] != "approved" or audit["silver_run_id"] != args.silver_run_id:
        raise ValueError("Silver não aprovada")
    if (eda["technical_validation"] != "approved" or eda["silver_run_id"] != args.silver_run_id
            or eda["eda_run_id"] != args.eda_run_id or eda["parquet_sha256"] != audit["parquet_sha256"]):
        raise ValueError("EDA técnica não aprovada ou arquivo divergente")
    if not (ROOT / "docs/execucoes" / args.eda_run_id / "04_eda_silver.md").is_file():
        raise FileNotFoundError("Relatório da EDA não encontrado")
    if digest(parquet) != audit["parquet_sha256"]:
        raise ValueError("SHA-256 do Parquet divergente")
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise SystemExit("Instale as dependências: python -m pip install -r requirements.txt") from exc
    data = pq.read_table(parquet, columns=["grupo_experimental", "visitou_site_14_dias", "comprou_14_dias", "gasto_14_dias_usd"])
    if data.num_rows != audit["silver_records"] or data.num_rows != eda["records"]:
        raise ValueError("Contagem diferente da Silver e EDA")
    groups = defaultdict(lambda: {"n": 0, "purchases": 0, "visits": 0, "spend": Decimal("0")})
    for row in data.to_pylist():
        group = row["grupo_experimental"]
        if group not in (CONTROL, *TREATMENTS):
            raise ValueError(f"Grupo inesperado: {group!r}")
        item = groups[group]
        item["n"] += 1
        item["purchases"] += row["comprou_14_dias"]
        item["visits"] += row["visitou_site_14_dias"]
        item["spend"] += row["gasto_14_dias_usd"]
    if (set(groups) != {CONTROL, *TREATMENTS} or
            {key: value["n"] for key, value in groups.items()} != audit["groups"] or
            sum(item["purchases"] for item in groups.values()) != eda["outcomes_overall"]["conversions"] or
            sum(item["visits"] for item in groups.values()) != eda["outcomes_overall"]["visits"] or
            sum((item["spend"] for item in groups.values()), Decimal("0")) != Decimal(eda["outcomes_overall"]["spend_usd"])):
        raise ValueError("Reconciliação entre grupos, Silver e EDA falhou")
    cleaned = {key: {"n": item["n"], "purchases": item["purchases"], "visits": item["visits"],
                     "conversion_rate": item["purchases"] / item["n"], "visit_rate": item["visits"] / item["n"],
                     "spend_usd": str(item["spend"]), "spend_per_assigned_usd": str(item["spend"] / item["n"])}
               for key, item in groups.items()}
    result = {"ab_run_id": args.ab_run_id, "silver_run_id": args.silver_run_id, "eda_run_id": args.eda_run_id,
              "created_utc": datetime.now(timezone.utc).isoformat(), "technical_validation": "approved",
              "analytic_review": "pending", "silver_parquet_sha256": audit["parquet_sha256"],
              "contract_sha256": digest(contract), "groups": cleaned,
              "comparisons": {name: compare(cleaned[name], cleaned[CONTROL]) for name in TREATMENTS}}
    if not args.execute:
        print(json.dumps({"mode": "validate_only", **result}, indent=2, ensure_ascii=False))
        return
    out = ROOT / "docs/execucoes" / args.ab_run_id
    quality = ROOT / "quality/runs" / args.ab_run_id
    if out.exists() or quality.exists():
        raise FileExistsError("ID A/B já usado; não sobrescrever")
    out.mkdir(parents=True)
    quality.mkdir(parents=True)
    (out / "06_analise_ab.md").write_text(report(result), encoding="utf-8")
    (quality / "validacao_ab.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"technical_validation": "approved", "analytic_review": "pending",
                      "report": str(out / "06_analise_ab.md"), "audit": str(quality / "validacao_ab.json")},
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
