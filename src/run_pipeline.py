"""Orquestra Bronze -> Silver com validação e documentação obrigatórias.

Exemplos:
  python src/run_pipeline.py --bronze-run-id 20260923T232601Z --silver-run-id SILVER01
  python src/run_pipeline.py --bronze-run-id BRONZE02 --silver-run-id SILVER02 --create-bronze

Reaproveita saídas existentes somente após conferir manifesto, hash e auditoria.
Não faz upload ao Azure, carga SQL, EDA nem cálculo de KPIs nesta versão.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_new(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as f:
        f.write(content)


def run_script(args: list[str], log: Path) -> None:
    result = subprocess.run([sys.executable, *args], cwd=ROOT, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    save_new(log, result.stdout)
    if result.returncode:
        raise RuntimeError(f"Script falhou (código {result.returncode}); veja {log.relative_to(ROOT)}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bronze-run-id", required=True)
    p.add_argument("--silver-run-id", required=True)
    p.add_argument("--create-bronze", action="store_true", help="cria nova Bronze a partir da Landing")
    args = p.parse_args()
    if not args.bronze_run_id.isalnum() or not args.silver_run_id.isalnum():
        p.error("IDs devem conter apenas letras e números")
    if args.bronze_run_id == args.silver_run_id:
        p.error("Use identificadores diferentes para Bronze e Silver")

    execution_id = datetime.now(timezone.utc).strftime("PIPE%Y%m%dT%H%M%S%fZ")
    trace_dir = ROOT / "docs/execucoes" / execution_id
    trace_dir.mkdir(parents=True, exist_ok=False)
    status_path = trace_dir / "status.json"
    status = {"execution_id": execution_id, "started_utc": now(),
              "bronze_run_id": args.bronze_run_id, "silver_run_id": args.silver_run_id,
              "stages": {"bronze": "pending", "silver": "pending"},
              "final_status": "running", "azure_upload": "not_executed",
              "sql_load": "not_executed", "kpis": "not_executed"}

    def persist() -> None:
        status_path.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    persist()
    try:
        manifest_path = ROOT / "metadata/runs" / args.bronze_run_id / "manifest.json"
        profile_path = ROOT / "quality/runs" / args.bronze_run_id / "perfil_fonte.json"
        if args.create_bronze:
            if manifest_path.exists() or profile_path.exists():
                raise FileExistsError("Bronze já existe; não sobrescrever uma execução anterior")
            run_script([str(ROOT / "src/01_perfil_fonte.py"), "--run-id", args.bronze_run_id], trace_dir / "01_bronze.log")
        manifest, profile = read_json(manifest_path), read_json(profile_path)
        bronze = ROOT / manifest["bronze_relative_path"]
        if digest(bronze) != manifest["source_sha256"] or profile["source_sha256"] != manifest["source_sha256"]:
            raise ValueError("Bronze/manifesto/perfil têm hashes diferentes")
        if profile["record_count"] != manifest["record_count"] or sum(profile["group_counts"].values()) != manifest["record_count"]:
            raise ValueError("Contagens da Bronze não reconciliam")
        bronze_doc = trace_dir / "01_bronze_validacao.md"
        save_new(bronze_doc, "# Bronze — validação da execução\n\n"
                 f"- Fonte: `{manifest['source_filename']}`\n"
                 f"- SHA-256: `{manifest['source_sha256']}`\n"
                 f"- Registros: {manifest['record_count']}\n"
                 f"- Grupos: {json.dumps(profile['group_counts'], ensure_ascii=False)}\n"
                 f"- Vazios por coluna: {json.dumps(profile['empty_values'], ensure_ascii=False)}\n"
                 f"- Linhas integralmente iguais além da primeira: {profile['identical_row_occurrences_beyond_first']}; preservadas.\n"
                 "- Limitação: não há identificador individual de cliente.\n"
                 "- Resultado: manifesto, cópia e perfil reconciliados.\n")
        status["stages"]["bronze"] = "approved_documented"
        persist()

        audit_path = ROOT / "quality/runs" / args.silver_run_id / "validacao_silver.json"
        if not audit_path.exists():
            run_script([str(ROOT / "src/02_materializar_silver.py"), "--bronze-run-id", args.bronze_run_id,
                        "--silver-run-id", args.silver_run_id], trace_dir / "02_silver.log")
        audit = read_json(audit_path)
        silver = ROOT / audit["parquet_relative_path"]
        if (audit["validation"] != "approved" or audit["bronze_run_id"] != args.bronze_run_id
            or audit["source_sha256"] != manifest["source_sha256"]
            or audit["bronze_records"] != manifest["record_count"]
            or audit["silver_records"] != manifest["record_count"]
            or audit["unique_technical_keys"] != manifest["record_count"]
            or digest(silver) != audit["parquet_sha256"]):
            raise ValueError("Auditoria Silver não reconcilia com Bronze ou Parquet")
        import pyarrow.parquet as pq
        if pq.read_metadata(silver).num_rows != manifest["record_count"]:
            raise ValueError("Número de linhas do Parquet não confere")
        silver_doc = trace_dir / "02_silver_validacao.md"
        save_new(silver_doc, "# Silver — validação da execução\n\n"
                 f"- Bronze usada: `{args.bronze_run_id}`\n"
                 f"- Parquet: `{audit['parquet_relative_path']}`\n"
                 f"- Registros de entrada e saída: {audit['bronze_records']} / {audit['silver_records']}\n"
                 f"- Chaves técnicas distintas: {audit['unique_technical_keys']}\n"
                 f"- Grupos: {json.dumps(audit['groups'], ensure_ascii=False)}\n"
                 f"- SHA-256 do Parquet: `{audit['parquet_sha256']}`\n"
                 "- Transformações: nomes e categorias em português, tipos definidos e chave técnica.\n"
                 "- Limitações: a chave identifica registros desta fonte, não pessoas entre arquivos.\n"
                 "- Resultado: auditoria, arquivo e contagens reconciliados.\n")
        save_new(trace_dir / "resumo_execucao.md", "# Resumo da execução\n\n"
                 f"- Execução: `{execution_id}`\n"
                 "- Bronze: aprovada e documentada.\n- Silver: aprovada e documentada.\n"
                 "- Azure, Gold, SQL, Power BI e KPIs: ainda não executados nesta versão.\n"
                 "- Conclusão de negócio e relatório executivo: aguardam análise aprovada.\n")
        status["stages"]["silver"] = "approved_documented"
        status["final_status"] = "bronze_silver_approved"
        status["finished_utc"] = now()
        persist()
        print(json.dumps({"execution_id": execution_id, "status": status["final_status"],
                          "documentation": str(trace_dir)}, ensure_ascii=False, indent=2))
    except Exception as exc:
        status["final_status"] = "failed"
        status["error"] = f"{type(exc).__name__}: {exc}"
        status["finished_utc"] = now()
        persist()
        save_new(trace_dir / "falha.md", f"# Execução interrompida\n\n- Etapa Bronze: {status['stages']['bronze']}\n"
                 f"- Etapa Silver: {status['stages']['silver']}\n- Motivo: {status['error']}\n"
                 "- Etapas seguintes: bloqueadas.\n")
        raise


if __name__ == "__main__":
    main()
