# -*- coding: utf-8 -*-
"""
04 — Junta o LONGITUDINAL (02b) com as FEATURES do CENSO (03).

Entrada:  gustavo/saida/etapas/02b_tx_rend_longitudinal.parquet  (30 col)
          gustavo/saida/etapas/03_censo_features.parquet         (19 col)
Saída:    gustavo/saida/etapas/04_base_com_censo.parquet
          gustavo/saida/base_atual.parquet            (cópia)
Relatório: gustavo/saida/relatorios/merge_features.txt

Merge: LEFT a partir do longitudinal (todas as escolas com tx_rend mantidas,
NaN onde o Censo não cobriu). Chave: (ANO, CO_ENTIDADE).

Uso:  python programas/04_merge_features.py
"""
import shutil
import sys
from pathlib import Path

import pandas as pd

# ------------------------------------------------------------------
# Descoberta das pastas
# ------------------------------------------------------------------
def achar_base_projeto():
    here = Path(__file__).resolve().parent
    for p in [here, *here.parents]:
        for nome in ("abandono-escolar", "abandono_escolar"):
            cand = p / nome
            if cand.is_dir() and (cand / "dados").is_dir():
                return cand
    for p in [here, *here.parents]:
        for nome in ("abandono-escolar", "abandono_escolar"):
            cand = p.parent / nome
            if cand.is_dir() and (cand / "dados").is_dir():
                return cand
    return None


BASE_PROJETO = achar_base_projeto()
if BASE_PROJETO is None:
    raise SystemExit("[ERRO] não achei 'abandono-escolar/dados/'")

GUSTAVO = Path(__file__).resolve().parent.parent
SAIDA_ETAPAS = GUSTAVO / "saida" / "etapas"
SAIDA_REL = GUSTAVO / "saida" / "relatorios"
SAIDA_BASE = GUSTAVO / "saida" / "base_atual.parquet"

IN_LONG = SAIDA_ETAPAS / "02b_tx_rend_longitudinal.parquet"
IN_CENSO = SAIDA_ETAPAS / "03_censo_features.parquet"
OUT = SAIDA_ETAPAS / "04_base_com_censo.parquet"
OUT_REL = SAIDA_REL / "merge_features.txt"

CHAVE = ["ANO", "CO_ENTIDADE"]


def main():
    print("=" * 78)
    print("04 — MERGE longitudinal + censo")
    print(f"BASE_PROJETO: {BASE_PROJETO}")
    print("=" * 78)

    if not IN_LONG.exists():
        print(f"[ERRO] não achei {IN_LONG} — rode 02 antes")
        sys.exit(1)
    if not IN_CENSO.exists():
        print(f"[ERRO] não achei {IN_CENSO} — rode 03 antes")
        sys.exit(1)

    lon = pd.read_parquet(IN_LONG)
    censo = pd.read_parquet(IN_CENSO)
    print(f"\nlongitudinal: {lon.shape[0]} × {lon.shape[1]}")
    print(f"censo:        {censo.shape[0]} × {censo.shape[1]}")

    # Normaliza chaves para string
    for df in (lon, censo):
        df["CO_ENTIDADE"] = df["CO_ENTIDADE"].astype(str).str.strip()

    # Merge
    antes = len(lon)
    base = lon.merge(censo, on=CHAVE, how="left", validate="1:1")
    print(f"\nMerge: {antes} → {len(base)} linhas (LEFT, sem perda)")
    print(f"Base:  {base.shape[0]} × {base.shape[1]} colunas")

    # Cobertura das features do Censo
    vars_mussato = [c for c in base.columns
                    if c.startswith(("IIB_", "IDA_", "IDP_", "IEP_"))]
    print(f"\nCobertura das {len(vars_mussato)} features do Censo:")
    linhas = [
        "MERGE — 02b + 03",
        "=" * 60,
        f"longitudinal: {lon.shape[0]} × {lon.shape[1]}",
        f"censo:        {censo.shape[0]} × {censo.shape[1]}",
        f"base final:   {base.shape[0]} × {base.shape[1]}",
        "",
        f"Cobertura das {len(vars_mussato)} features do Censo (por ano):",
        f"{'ano':>5}{'n':>7}{'cobertura_media':>20}",
    ]
    for ano in sorted(base["ANO"].unique()):
        sub = base[base["ANO"] == ano]
        cob = round(sub[vars_mussato].notna().mean().mean() * 100, 1)
        print(f"  {ano}: n={len(sub)}, cobertura={cob}%")
        linhas.append(f"{ano:>5}{len(sub):>7}{cob:>20}")

    # Salva
    base.to_parquet(OUT, index=False)
    print(f"\n>>> {OUT}")

    shutil.copy2(OUT, SAIDA_BASE)
    print(f">>> {SAIDA_BASE} (cópia)")

    OUT_REL.write_text("\n".join(linhas), encoding="utf-8")
    print(f">>> Relatório: {OUT_REL}")


if __name__ == "__main__":
    main()