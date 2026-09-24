"""Publica uma execução Bronze/Silver aprovada no ADLS Gen2 via Azure CLI.

Padrão: apenas mostra o plano. Adicione --execute para enviar. Não sobrescreve
objetos existentes. Usa login Entra ID (`az login`), sem chaves no código.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACCOUNT = "stcustomeranalyticsgb01"
CONTAINER = "experimento-crm-varejo-moda"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def az(*args: str) -> dict:
    # No Windows, o comando encontrado no PowerShell costuma ser az.cmd.
    # subprocess com shell=False precisa receber o caminho do arquivo .cmd.
    executable = shutil.which("az.cmd") or shutil.which("az.exe") or shutil.which("az")
    if executable is None:
        raise RuntimeError("Azure CLI não encontrada no PATH do Python. Reinicie o terminal do VS Code e confira 'Get-Command az'.")
    proc = subprocess.run([executable, *args, "--output", "json"], text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if proc.returncode:
        raise RuntimeError(f"Azure CLI falhou: {' '.join(args[:3])}: {proc.stderr.strip()}")
    return json.loads(proc.stdout)


def blob_args(name: str) -> list[str]:
    return ["--account-name", ACCOUNT, "--container-name", CONTAINER,
            "--auth-mode", "login", "--name", name]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bronze-run-id", required=True)
    p.add_argument("--silver-run-id", required=True)
    p.add_argument("--pipeline-execution-id", required=True)
    p.add_argument("--execute", action="store_true")
    args = p.parse_args()
    if any(not s.isalnum() for s in (args.bronze_run_id, args.silver_run_id, args.pipeline_execution_id)):
        p.error("IDs devem conter apenas letras e números")
    manifest = json.loads((ROOT / "metadata/runs" / args.bronze_run_id / "manifest.json").read_text(encoding="utf-8"))
    audit = json.loads((ROOT / "quality/runs" / args.silver_run_id / "validacao_silver.json").read_text(encoding="utf-8"))
    trace = ROOT / "docs/execucoes" / args.pipeline_execution_id
    status = json.loads((trace / "status.json").read_text(encoding="utf-8"))
    if (status["final_status"] != "bronze_silver_approved" or
        status["bronze_run_id"] != args.bronze_run_id or status["silver_run_id"] != args.silver_run_id or
        audit["validation"] != "approved" or audit["source_sha256"] != manifest["source_sha256"] or
        audit["silver_records"] != manifest["record_count"]):
        raise ValueError("Bronze/Silver não estão aprovadas ou IDs não correspondem")
    source = ROOT / "data/00_landing" / manifest["source_filename"]
    bronze = ROOT / manifest["bronze_relative_path"]
    silver = ROOT / audit["parquet_relative_path"]
    if sha(source) != manifest["source_sha256"] or sha(bronze) != manifest["source_sha256"] or sha(silver) != audit["parquet_sha256"]:
        raise ValueError("Hash local diverge dos registros aprovados")
    base = [
        (source, f"00_landing/{manifest['source_sha256']}/{source.name}"),
        (bronze, f"01_bronze_raw/{args.bronze_run_id}/{bronze.name}"),
        (silver, f"02_silver/{args.silver_run_id}/{silver.name}"),
        (ROOT / "metadata/runs" / args.bronze_run_id / "manifest.json", f"metadata/runs/{args.bronze_run_id}/manifest.json"),
        (ROOT / "quality/runs" / args.bronze_run_id / "perfil_fonte.json", f"quality/runs/{args.bronze_run_id}/perfil_fonte.json"),
        (ROOT / "quality/runs" / args.silver_run_id / "validacao_silver.json", f"quality/runs/{args.silver_run_id}/validacao_silver.json"),
        (ROOT / "metadata/dicionario_traducao.md", "metadata/contratos/dicionario_traducao_v01.md"),
        (ROOT / "metadata/contrato_analitico.md", "metadata/contratos/contrato_analitico_v01.md"),
    ]
    for filename in ("status.json", "01_bronze_validacao.md", "02_silver_validacao.md", "resumo_execucao.md"):
        base.append((trace / filename, f"docs/execucoes/{args.pipeline_execution_id}/{filename}"))
    for local, _ in base:
        if not local.is_file():
            raise FileNotFoundError(local)
    print(json.dumps({"account": ACCOUNT, "container": CONTAINER, "mode": "execute" if args.execute else "plan_only",
                      "files": [{"local": str(local.relative_to(ROOT)).replace("\\", "/"), "remote": remote,
                                 "bytes": local.stat().st_size, "sha256": sha(local)} for local, remote in base]},
                     indent=2, ensure_ascii=False))
    if not args.execute:
        return
    if not (shutil.which("az.cmd") or shutil.which("az.exe") or shutil.which("az")):
        raise RuntimeError("Azure CLI não encontrada. Instale-a e execute `az login` antes do envio")
    container = az("storage", "container", "show", "--account-name", ACCOUNT,
                   "--name", CONTAINER, "--auth-mode", "login")
    if container.get("name") != CONTAINER:
        raise ValueError("Contêiner inesperado")
    record = {"created_utc": datetime.now(timezone.utc).isoformat(), "account": ACCOUNT,
              "container": CONTAINER, "pipeline_execution_id": args.pipeline_execution_id,
              "files": [], "status": "in_progress"}
    receipt = trace / "publicacao_azure.json"
    if receipt.exists():
        raise FileExistsError("Já existe um recibo para esta execução; não sobrescrever")
    for local, remote in base:
        exists = az("storage", "blob", "exists", *blob_args(remote))
        if exists.get("exists"):
            raise FileExistsError(f"Destino já existe: {remote}. Publicação interrompida sem sobrescrita")
        az("storage", "blob", "upload", *blob_args(remote), "--file", str(local), "--overwrite", "false")
        props = az("storage", "blob", "show", *blob_args(remote))
        remote_size = props.get("properties", {}).get("contentLength")
        if remote_size != local.stat().st_size:
            raise RuntimeError(f"Tamanho remoto divergente: {remote}")
        with tempfile.TemporaryDirectory() as tmp:
            check = Path(tmp) / "arquivo"
            az("storage", "blob", "download", *blob_args(remote), "--file", str(check))
            if sha(check) != sha(local):
                raise RuntimeError(f"Hash remoto divergente: {remote}")
        record["files"].append({"path": remote, "bytes": local.stat().st_size, "sha256": sha(local), "verified": True})
        receipt.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    record["status"] = "approved"
    record["finished_utc"] = datetime.now(timezone.utc).isoformat()
    receipt.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Publicação aprovada: {len(base)} arquivos; recibo: {receipt}")


if __name__ == "__main__":
    main()
