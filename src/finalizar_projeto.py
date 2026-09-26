"""Conferência final somente leitura do experimento CRM.

Uso: python src/finalizar_projeto.py
     python src/finalizar_projeto.py --execute --run-id FINAL01

O modo padrão imprime o resultado sem gravar. --execute cria um recibo privado em
docs/execucoes/<id>/; nunca muda dados, documentos, Git ou Azure.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "Sem e-mail": (21306, 2262, 122, Decimal("13908.33")),
    "E-mail feminino": (21387, 3238, 189, Decimal("23038.11")),
    "E-mail masculino": (21307, 3894, 267, Decimal("30311.69")),
}
PUBLIC = (
    "README.md", "metadata/contrato_analitico.md", "metadata/dicionario_traducao.md",
    "docs/registro_diario.md", "docs/visao_executiva_power_bi.md",
    "docs/visao_executiva_power_bi.png", "docs/relatorio_tecnico_final.md",
    "docs/relatorio_tecnico_final.docx", "docs/relatorio_executivo_final.md",
    "docs/relatorio_executivo_final.docx", "power_bi/medidas_crm.dax",
    "power_bi/experimento_crm_varejo_moda.pbix", "sql/01_modelo_gold_sql_server.sql",
    "sql/02_reconciliar_kpis_power_bi.sql", "src/06_analisar_ab.py",
    "src/07_materializar_gold.py", "src/08_publicar_gold_azure.py",
    "src/09_carregar_gold_sql.py", "src/finalizar_projeto.py",
)
BLOCKED_SUFFIXES = (".csv", ".parquet", ".env", ".xlsx", ".bak")


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run(*command: str) -> str:
    result = subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, check=False)
    if result.returncode:
        raise RuntimeError(f"Comando falhou: {' '.join(command[:2])}")
    return result.stdout.strip()


def check(results: dict, name: str, action) -> None:
    try:
        detail = action()
        results[name] = {"status": "approved", "evidence": detail}
    except (OSError, ValueError, KeyError, RuntimeError, json.JSONDecodeError) as exc:
        results[name] = {"status": "blocked", "reason": str(exc)}


def required_files() -> dict:
    missing = [name for name in PUBLIC if not (ROOT / name).is_file()]
    if missing:
        raise ValueError("Arquivos ausentes: " + ", ".join(missing))
    return {name: {"bytes": (ROOT / name).stat().st_size, "sha256": sha(ROOT / name)} for name in PUBLIC}


def audit(path: str, key: str, expected: str) -> dict:
    data = json.loads((ROOT / path).read_text(encoding="utf-8"))
    if data.get(key) != expected:
        raise ValueError(f"{path}: {key} diferente de {expected}")
    return data


def local_data() -> dict:
    silver = audit("quality/runs/SILVER01/validacao_silver.json", "validation", "approved")
    eda = audit("quality/runs/EDA01/validacao_eda.json", "technical_validation", "approved")
    ab = audit("quality/runs/AB01/validacao_ab.json", "technical_validation", "approved")
    gold = audit("quality/runs/GOLD01/validacao_gold.json", "technical_validation", "approved")
    if (silver.get("silver_records") != 64000 or eda.get("records") != 64000 or
            gold.get("fact_records") != 64000 or gold.get("dimension_records") != 3):
        raise ValueError("Contagens Silver/EDA/Gold divergentes")
    if (ab.get("silver_parquet_sha256") != silver.get("parquet_sha256") or
            eda.get("parquet_sha256") != silver.get("parquet_sha256") or
            gold.get("source_sha256") != silver.get("parquet_sha256")):
        raise ValueError("Hashes entre camadas divergentes")
    source = ROOT / silver["parquet_relative_path"]
    if not source.is_file() or sha(source) != silver["parquet_sha256"]:
        raise ValueError("Silver ausente ou alterada")
    for name in ("dim_grupo_experimental", "fato_resposta_experimental"):
        entry = gold["files"][name]
        path = (ROOT / entry["relative_path"]).resolve()
        if not path.is_relative_to(ROOT.resolve()) or not path.is_file() or sha(path) != entry["sha256"]:
            raise ValueError(f"Gold {name} ausente ou alterada")
    for name, (n, visits, purchases, spend) in EXPECTED.items():
        item = ab["groups"][name]
        if (item["n"], item["visits"], item["purchases"], Decimal(item["spend_usd"])) != (n, visits, purchases, spend):
            raise ValueError(f"Agregados A/B divergentes: {name}")
        if Decimal(str(gold["group_reconciliation"][name]["spend_usd"])) != spend:
            raise ValueError(f"Gasto Gold divergente: {name}")
    return {"silver_sha256": silver["parquet_sha256"], "ab_report": "docs/execucoes/AB01/06_analise_ab.md",
            "gold_files": [gold["files"][name]["relative_path"] for name in gold["files"]]}


def remote_receipts() -> dict:
    candidates = list((ROOT / "docs/execucoes").glob("*/publicacao_azure.json"))
    approved = []
    for path in candidates:
        item = json.loads(path.read_text(encoding="utf-8"))
        if item.get("status") == "approved":
            approved.append(str(path.relative_to(ROOT)))
    if not approved:
        raise ValueError("Nenhum recibo Azure Bronze/Silver aprovado encontrado")
    gold = audit("docs/execucoes/GOLD01/publicacao_azure_gold.json", "status", "approved")
    if not gold.get("files") or not all(f.get("verified") for f in gold["files"]):
        raise ValueError("Recibo Gold sem verificação de todos os blobs")
    return {"bronze_silver_receipt": approved, "gold_receipt": gold.get("status"),
            "gold_remote_paths": [f["path"] for f in gold["files"]]}


def azure_live() -> dict:
    az = shutil.which("az.cmd") or shutil.which("az.exe") or shutil.which("az")
    if not az:
        raise ValueError("Azure CLI indisponível; conferência remota não executada")
    receipt = audit("docs/execucoes/GOLD01/publicacao_azure_gold.json", "status", "approved")
    if receipt.get("account") != "stcustomeranalyticsgb01" or receipt.get("container") != "experimento-crm-varejo-moda":
        raise ValueError("Destino Azure inesperado")
    checked = []
    for item in receipt["files"]:
        path = item["path"]
        output = run(az, "storage", "blob", "show", "--account-name", receipt["account"],
                     "--container-name", receipt["container"], "--auth-mode", "login",
                     "--name", path, "--output", "json")
        props = json.loads(output)
        if props.get("properties", {}).get("contentLength") != item["bytes"]:
            raise ValueError(f"Tamanho remoto diferente: {path}")
        checked.append(path)
    return {"paths_verified_by_size": checked,
            "sha256_remote": "conferido nos recibos de publicação; não recalculado nesta execução"}


def sql_receipt() -> dict:
    data = json.loads((ROOT / "quality/runs/GOLD01/reconciliacao_sql.json").read_text(encoding="utf-8"))
    if data.get("status") not in ("loaded_reconciled", "existing_reconciled") or data.get("fact_records") != 64000:
        raise ValueError("Recibo SQL sem reconciliação aprovada")
    return {"status": data["status"], "database": data.get("database"), "fact_records": 64000,
            "live_query": "não executada; recibo da carga e reconciliação documental"}


def git_check() -> dict:
    tracked = set(run("git", "ls-files", "--cached").splitlines())
    prohibited = [p for p in tracked if p.lower().endswith(BLOCKED_SUFFIXES) or
                  p.startswith(("data/03_exports/", "docs/execucoes/", "quality/runs/", "metadata/runs/"))]
    if prohibited:
        raise ValueError("Caminhos não permitidos versionados: " + ", ".join(prohibited))
    missing = sorted(set(PUBLIC) - tracked)
    if missing:
        raise ValueError("Arquivos finais não rastreados: " + ", ".join(missing))
    if run("git", "branch", "--show-current") != "main":
        raise ValueError("Branch atual diferente de main")
    if run("git", "rev-parse", "HEAD") != run("git", "rev-parse", "origin/main"):
        raise ValueError("HEAD local difere do origin/main local; execute git fetch origin antes da auditoria")
    return {"commit": run("git", "rev-parse", "HEAD"), "tracked_files": len(tracked),
            "note": "origin/main é referência local; visibilidade do GitHub não conferida"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Grava recibo em docs/execucoes/<id>")
    parser.add_argument("--run-id", default="FINAL01")
    args = parser.parse_args()
    if not args.run_id.isalnum():
        parser.error("run-id deve ser alfanumérico")
    dest = ROOT / "docs/execucoes" / args.run_id
    if args.execute and dest.exists():
        parser.error("ID já usado; não sobrescrever")
    results = {}
    for name, action in (("arquivos_finais", required_files), ("dados_e_calculos", local_data),
                         ("recibos_azure", remote_receipts), ("azure_acesso_atual", azure_live),
                         ("sql_recibo", sql_receipt), ("git_local", git_check)):
        check(results, name, action)
    # Não afirmar privacidade ou sincronismo remoto sem API autenticada.
    results["github_visibilidade"] = {"status": "not_verified", "reason": "Revisar visibilidade no GitHub autenticado"}
    overall = "approved_with_limitations" if all(v["status"] == "approved" for k, v in results.items()
                                                   if k != "github_visibilidade") else "blocked"
    result = {"run_id": args.run_id, "checked_utc": datetime.now(timezone.utc).isoformat(),
              "status": overall, "checks": results,
              "scope_decision": "Encerramento neste recorte por suficiência analítica acordada; sem novas análises."}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.execute:
        dest.mkdir(parents=True)
        (dest / "finalizacao.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if overall == "approved_with_limitations" else 1


if __name__ == "__main__":
    sys.exit(main())
