# -*- coding: utf-8 -*-
"""
99 — Pipeline completo: 01 → 02 → 03 → 04.

Roda os 4 scripts em ordem. Cada um é independente e tem cache próprio.
Se um falhar, o pipeline para e você pode retomar de onde parou (rodando
o script específico).

Uso:
    python programas/99_pipeline.py               # usa cache onde tiver
    python programas/99_pipeline.py --force       # ignora todo cache
    python programas/99_pipeline.py --from 03     # começa do 03
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

PROGRAMAS = Path(__file__).resolve().parent
GUSTAVO = PROGRAMAS.parent

ETAPAS = [
    ("01", "01_tx_rend_bruto.py", []),
    ("02", "02_tx_rend_selecionado_longitudinal.py", []),
    ("03", "03_censo_features.py", ["--force"]),  # aceita --force
    ("04", "04_merge_features.py", []),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true",
                        help="ignora cache em todas as etapas")
    parser.add_argument("--from", dest="from_etapa", default=None,
                        help="começa a partir desta etapa (ex: 03)")
    args = parser.parse_args()

    # Decide em qual etapa começar
    if args.from_etapa:
        try:
            idx = [e[0] for e in ETAPAS].index(args.from_etapa)
        except ValueError:
            print(f"[ERRO] etapa {args.from_etapa!r} não existe. "
                  f"Opções: {[e[0] for e in ETAPAS]}")
            return 1
        etapas = ETAPAS[idx:]
    else:
        etapas = ETAPAS

    print("=" * 78)
    print("PIPELINE — 01 → 02 → 03 → 04")
    print(f"GUSTAVO: {GUSTAVO}")
    if args.force:
        print("Modo: --force (ignora cache)")
    if args.from_etapa:
        print(f"Começando em: {args.from_etapa}")
    print("=" * 78)

    tempo_total = time.time()
    for nome, script, flags_extra in etapas:
        caminho = PROGRAMAS / script
        if not caminho.exists():
            print(f"\n[ERRO] não achei {caminho}")
            return 1

        cmd = [sys.executable, str(caminho)]
        if args.force:
            cmd += flags_extra
            if nome == "01":
                cmd.append("--force")

        print(f"\n{'=' * 78}")
        print(f"ETAPA {nome}: {script}")
        print(f"{'=' * 78}")
        t0 = time.time()
        ret = subprocess.run(cmd, cwd=str(GUSTAVO))
        dt = time.time() - t0
        if ret.returncode != 0:
            print(f"\n[!] Etapa {nome} falhou (código {ret.returncode}). "
                  f"Parei aqui.")
            return ret.returncode
        print(f"\n[ok] Etapa {nome} concluída em {dt:.1f}s")

    print(f"\n{'=' * 78}")
    print(f"PIPELINE COMPLETO em {time.time() - tempo_total:.1f}s")
    print(f"{'=' * 78}")
    print(f"\nBase final: {GUSTAVO / 'saida' / 'base_atual.parquet'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())