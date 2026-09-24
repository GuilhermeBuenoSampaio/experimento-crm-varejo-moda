"""Primeira etapa: preservação e perfil da fonte, sem deduplicar nem calcular desempenho.

Entrada: CSV original MineThatData em data/00_landing.
Saídas: cópia Bronze, manifesto, perfil JSON/Markdown.
Granularidade: uma linha recebida = um registro experimental; não há cliente_id.
Chave técnica futura: (source_sha256, source_row_number), com numeração de dados iniciada em 1.
Limite: linhas iguais podem representar pessoas diferentes; não eliminar por DISTINCT.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = ["recency", "history_segment", "history", "mens", "womens", "zip_code", "newbie", "channel", "segment", "visit", "conversion", "spend"]
SOURCE_NAME = "Kevin_Hillstrom_MineThatData_E-MailAnalytics_DataMiningChallenge_2008.03.20.csv"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "data/00_landing" / SOURCE_NAME)
    parser.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    args = parser.parse_args()
    source = args.source.resolve()
    if not source.is_file():
        parser.error(f"Arquivo não encontrado: {source}")
    if not args.run_id.isalnum():
        parser.error("run-id deve conter apenas letras e números")

    with source.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != EXPECTED:
            raise ValueError(f"Cabeçalho inesperado: {reader.fieldnames}")
        rows = list(reader)
    if not rows:
        raise ValueError("Arquivo sem registros")

    fingerprint = sha256(source)
    group_counts = Counter(row["segment"] for row in rows)
    cardinality = {column: len({row[column] for row in rows}) for column in EXPECTED}
    missing = {column: sum(not row[column].strip() for row in rows) for column in EXPECTED}
    row_patterns = Counter(tuple(row[column] for column in EXPECTED) for row in rows)
    profile = {
        "run_id": args.run_id,
        "source_sha256": fingerprint,
        "record_count": len(rows),
        "columns": EXPECTED,
        "group_counts": dict(sorted(group_counts.items())),
        "cardinality": cardinality,
        "empty_values": missing,
        "identical_row_occurrences_beyond_first": sum(n - 1 for n in row_patterns.values()),
        "identical_rows_are_not_proven_duplicate_customers": True,
        "technical_key": ["source_sha256", "source_row_number"],
        "source_row_number_range": [1, len(rows)],
        "source_has_customer_id": False,
        "zip_code_categories_as_received": dict(sorted(Counter(row["zip_code"] for row in rows).items())),
    }
    manifest = {
        "run_id": args.run_id,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "origin": "Kevin Hillstrom / MineThatData, 2008",
        "origin_url": "https://blog.minethatdata.com/2008/03/minethatdata-e-mail-analytics-and-data.html",
        "source_filename": source.name,
        "source_sha256": fingerprint,
        "source_size_bytes": source.stat().st_size,
        "record_count": len(rows),
        "bronze_byte_identical": True,
    }
    bronze = ROOT / "data/01_bronze_raw" / args.run_id / source.name
    manifest_path = ROOT / "metadata/runs" / args.run_id / "manifest.json"
    profile_path = ROOT / "quality/runs" / args.run_id / "perfil_fonte.json"
    report_path = ROOT / "quality/runs" / args.run_id / "perfil_fonte.md"
    targets = (bronze, manifest_path, profile_path, report_path)
    if any(path.exists() for path in targets):
        raise FileExistsError("Essa execução já possui saídas; use outro --run-id")
    for path in targets:
        path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, bronze)
    if sha256(bronze) != fingerprint:
        bronze.unlink()
        raise RuntimeError("A cópia Bronze divergiu da fonte")
    manifest["bronze_relative_path"] = str(bronze.relative_to(ROOT)).replace("\\", "/")
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    profile_path.write_text(json.dumps(profile, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = ["# Perfil da fonte", "", f"Execução: `{args.run_id}`", f"Registros: **{len(rows):,}**", f"SHA-256: `{fingerprint}`", "", "## Grupos", ""]
    lines += [f"- {name}: {count:,}" for name, count in sorted(group_counts.items())]
    lines += ["", "## Cardinalidade e vazios", "", "| Coluna | Distintos | Vazios |", "|---|---:|---:|"]
    lines += [f"| {column} | {cardinality[column]:,} | {missing[column]:,} |" for column in EXPECTED]
    lines += ["", f"Linhas idênticas além da primeira: **{profile['identical_row_occurrences_beyond_first']:,}**. Não deduplicar sem identificador individual e evidência adicional.", "", "Chave técnica proposta: `(source_sha256, source_row_number)`. A posição da linha identifica registro, não pessoa.", "", "`zip_code` mantém a grafia recebida nesta etapa; qualquer padronização será decidida na Silver.", ""]
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"run_id": args.run_id, "records": len(rows), "groups": profile["group_counts"], "sha256": fingerprint, "report": str(report_path)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
