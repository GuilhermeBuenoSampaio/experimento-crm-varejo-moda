"""Publica a Gold aprovada no contêiner Azure, verifica bytes e registra recibo.

Uso: python src/08_publicar_gold_azure.py --gold-run-id GOLD01
     python src/08_publicar_gold_azure.py --gold-run-id GOLD01 --execute
Requer Azure CLI autenticada (az login) e permissão de dados no contêiner.
Nunca sobrescreve blobs. Uma execução interrompida pode ser retomada.
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


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def az(*args: str) -> dict:
    executable = shutil.which("az.cmd") or shutil.which("az.exe") or shutil.which("az")
    if not executable:
        raise RuntimeError("Azure CLI não localizada; verifique 'az version' e o login no terminal")
    proc = subprocess.run([executable, *args, "--output", "json"], text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if proc.returncode:
        raise RuntimeError(f"Azure CLI falhou ({' '.join(args[:3])}): {proc.stderr.strip()}")
    return json.loads(proc.stdout)


def blob_args(remote: str) -> list[str]:
    return ["--account-name", ACCOUNT, "--container-name", CONTAINER,
            "--auth-mode", "login", "--name", remote]


def verify_remote(local: Path, remote: str) -> None:
    props = az("storage", "blob", "show", *blob_args(remote))
    if props.get("properties", {}).get("contentLength") != local.stat().st_size:
        raise RuntimeError(f"Tamanho Azure diferente do arquivo local: {remote}")
    with tempfile.TemporaryDirectory() as tmp:
        downloaded = Path(tmp) / "conferencia"
        az("storage", "blob", "download", *blob_args(remote), "--file", str(downloaded))
        if digest(downloaded) != digest(local):
            raise RuntimeError(f"SHA-256 Azure diferente do arquivo local: {remote}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold-run-id", required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not args.gold_run_id.isalnum():
        parser.error("ID Gold deve conter somente letras e números")
    audit_path = ROOT / "quality/runs" / args.gold_run_id / "validacao_gold.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if audit["gold_run_id"] != args.gold_run_id or audit["technical_validation"] != "approved":
        raise ValueError("Gold não aprovada ou ID divergente")
    ab = json.loads((ROOT / "quality/runs" / audit["ab_run_id"] / "validacao_ab.json").read_text(encoding="utf-8"))
    if (ab["technical_validation"] != "approved" or ab["silver_parquet_sha256"] != audit["source_sha256"] or
            audit["fact_records"] != sum(item["n"] for item in ab["groups"].values()) or
            audit["dimension_records"] != 3):
        raise ValueError("Auditoria Gold não reconcilia com a análise A/B")
    base = []
    for name in ("dim_grupo_experimental", "fato_resposta_experimental"):
        entry = audit["files"][name]
        local = (ROOT / entry["relative_path"]).resolve()
        if not local.is_relative_to(ROOT.resolve()) or not local.is_file() or digest(local) != entry["sha256"]:
            raise ValueError(f"Arquivo Gold ausente, fora do projeto ou com hash divergente: {name}")
        base.append((local, f"03_gold/{args.gold_run_id}/{local.name}"))
    report = ROOT / "docs/execucoes" / args.gold_run_id / "07_gold_validacao.md"
    for local, remote in ((audit_path, f"quality/runs/{args.gold_run_id}/validacao_gold.json"),
                          (report, f"docs/execucoes/{args.gold_run_id}/07_gold_validacao.md")):
        if not local.is_file():
            raise FileNotFoundError(local)
        base.append((local, remote))
    print(json.dumps({"account": ACCOUNT, "container": CONTAINER,
                      "mode": "execute" if args.execute else "plan_only",
                      "files": [{"local": str(local.relative_to(ROOT)).replace("\\", "/"),
                                 "remote": remote, "bytes": local.stat().st_size, "sha256": digest(local)}
                                for local, remote in base]}, indent=2, ensure_ascii=False))
    if not args.execute:
        return
    container = az("storage", "container", "show", "--account-name", ACCOUNT,
                   "--name", CONTAINER, "--auth-mode", "login")
    if container.get("name") != CONTAINER:
        raise ValueError("Contêiner Azure inesperado")
    receipt = ROOT / "docs/execucoes" / args.gold_run_id / "publicacao_azure_gold.json"
    if receipt.exists():
        record = json.loads(receipt.read_text(encoding="utf-8"))
        if record.get("gold_run_id") != args.gold_run_id or record.get("account") != ACCOUNT or record.get("container") != CONTAINER:
            raise ValueError("Recibo existente não corresponde à execução")
        if record.get("status") == "approved":
            raise FileExistsError("Publicação Gold já aprovada; não repetir nem sobrescrever")
        if record.get("status") != "in_progress":
            raise ValueError("Status inesperado no recibo existente")
    else:
        record = {"created_utc": datetime.now(timezone.utc).isoformat(), "account": ACCOUNT,
                  "container": CONTAINER, "gold_run_id": args.gold_run_id,
                  "status": "in_progress", "files": []}
        receipt.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    planned = {remote for _, remote in base}
    if any(item.get("path") not in planned or not item.get("verified") for item in record["files"]):
        raise ValueError("Recibo parcial contém arquivo inesperado ou não verificado")
    for local, remote in base:
        exists = az("storage", "blob", "exists", *blob_args(remote)).get("exists")
        if exists:
            verify_remote(local, remote)
        else:
            az("storage", "blob", "upload", *blob_args(remote), "--file", str(local), "--overwrite", "false")
            verify_remote(local, remote)
        record["files"] = [item for item in record["files"] if item["path"] != remote]
        record["files"].append({"path": remote, "bytes": local.stat().st_size,
                                "sha256": digest(local), "verified": True})
        receipt.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if len(record["files"]) != len(base):
        raise RuntimeError("Quantidade de arquivos no recibo não confere")
    record["status"] = "approved"
    record["finished_utc"] = datetime.now(timezone.utc).isoformat()
    receipt.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "approved", "files_verified": len(base),
                      "receipt": str(receipt)}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
