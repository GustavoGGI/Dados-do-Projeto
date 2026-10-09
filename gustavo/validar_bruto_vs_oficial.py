# -*- coding: utf-8 -*-
"""
Valida o parquet bruto (tx_rend_rr_2007_2025_bruto.parquet) contra os
parquets oficiais do pipeline (dados/interim/indicadores_rr/tx_rend_AAAA.parquet).

Para cada ano em comum:
  - Compara conjuntos de CO_ENTIDADE.
  - Compara valores das taxas (aproximação por nome exato OU chave semântica).
  - Reporta quantas colunas foram EFETIVAMENTE comparadas.

Saída:
    gustavo/saida/validacao_bruto.txt

Uso:
    python gustavo/validar_bruto_vs_oficial.py
"""
import re
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent.parent
BRUTO_PATH = Path(__file__).resolve().parent / "saida" / "tx_rend_rr_2007_2025_bruto.parquet"
OFICIAL_DIR = BASE / "dados" / "interim" / "indicadores_rr"
SAIDA = Path(__file__).resolve().parent / "saida" / "validacao_bruto.txt"

ANOS_OFICIAIS = list(range(2019, 2026))
TOL = 0.01


def detectar_coluna_id(df):
    for c in ("CO_ENTIDADE", "Código da Escola", "COD_ESCOLA", "CO_ESCOLA"):
        if c in df.columns and df[c].notna().sum() > 0:
            return c
    return None


def normalizar_id(serie):
    s = pd.to_numeric(serie, errors="coerce")
    s = s.dropna().astype("Int64").astype("string")
    return s


def extrair_colunas_taxa(df):
    cols = []
    for c in df.columns:
        cs = str(c)
        cl = cs.lower()
        if cs.startswith(("tap_", "tre_", "tab_")):
            cols.append(cs)
        elif re.match(r"^[123]_CAT_", cs):
            cols.append(cs)
        elif cl.startswith(("taxa de ", "aprovação na ", "reprovação na ",
                            "abandono na ", "aprovação - ", "reprovação - ",
                            "abandono - ")):
            cols.append(cs)
    return cols


def extrair_chave(nome):
    """Reduz nome de coluna a uma chave semântica tipo TAP_FUN_AF."""
    s = str(nome)

    m = re.match(r"^([123])_CAT_(.+)$", s)
    if m:
        prefixo = {"1": "TAP", "2": "TRE", "3": "TAB"}[m.group(1)]
        return f"{prefixo}_{m.group(2)}"

    m = re.match(r"^(tap|tre|tab)_(.+)$", s, re.IGNORECASE)
    if m:
        return f"{m.group(1).upper()}_{m.group(2)}"

    sl = s.lower()
    for p, sig in (("aprova", "TAP"), ("reprova", "TRE"), ("abandon", "TAB")):
        if sl.startswith(p) or sl.startswith(f"taxa de {p}"):
            if "anos finais" in sl or "_af" in sl:
                return f"{sig}_FUN_AF"
            if "anos iniciais" in sl or "_ai" in sl:
                return f"{sig}_FUN_AI"
            if "médio" in sl or "medio" in sl:
                m2 = re.search(r"_med(?:io)?_?(\d{2})?", sl)
                if m2 and m2.group(1):
                    return f"{sig}_MED_{m2.group(1)}"
                return f"{sig}_MED"
    return None


def mapear_colunas(meu_cols, oficial_cols):
    """
    Mapeia colunas do oficial para colunas do bruto.
    Prioridade:
      1) Nome exato (ex: '1_CAT_FUN' em ambos) — evita pegar coluna vazia.
      2) Chave semântica (ex: '1_CAT_FUN' → 'tap_FUN' quando bruto só tem a antiga).
    Retorna {coluna_oficial: coluna_meu}.
    """
    chaves_meu = {c: extrair_chave(c) for c in meu_cols}

    # {chave_semantica: primeira coluna_meu que casa}
    inv_meu = {}
    for c, k in chaves_meu.items():
        if k and k not in inv_meu:
            inv_meu[k] = c

    mapeamento = {}
    for c_of in oficial_cols:
        if c_of in meu_cols:
            # 1) match exato
            mapeamento[c_of] = c_of
        else:
            # 2) fallback semântico
            k = extrair_chave(c_of)
            if k and k in inv_meu:
                mapeamento[c_of] = inv_meu[k]
    return mapeamento


def main():
    if not BRUTO_PATH.exists():
        print(f"[ERRO] não encontrei {BRUTO_PATH}")
        return

    bruto = pd.read_parquet(BRUTO_PATH)
    col_id_bruto = detectar_coluna_id(bruto)
    print(f"Bruto: {len(bruto):,} linhas × {bruto.shape[1]} colunas")
    print(f"Coluna de ID detectada: {col_id_bruto}")
    print(f"Anos no bruto: {sorted(bruto['ANO'].unique().tolist())}\n")

    linhas_saida = [
        "VALIDAÇÃO — bruto (Gustavo) vs oficial (pipeline da Gabi)",
        "=" * 70,
        f"Bruto: {len(bruto):,} linhas × {bruto.shape[1]} colunas",
        f"Coluna de ID: {col_id_bruto}",
        "",
    ]

    for ano in ANOS_OFICIAIS:
        path_of = OFICIAL_DIR / f"tx_rend_{ano}.parquet"
        if not path_of.exists():
            msg = f"[{ano}] oficial não encontrado em {path_of}"
            print(msg)
            linhas_saida.append(msg)
            continue

        oficial = pd.read_parquet(path_of)
        col_id_of = detectar_coluna_id(oficial)

        meu = bruto[bruto["ANO"] == ano].copy()

        ids_meu = set(normalizar_id(meu[col_id_bruto]).dropna().tolist())
        ids_of = set(normalizar_id(oficial[col_id_of]).dropna().tolist())

        so_meu = ids_meu - ids_of
        so_of = ids_of - ids_meu
        comuns = ids_meu & ids_of

        cabecalho = (f"\n[{ano}] bruto={len(meu)} linhas | "
                     f"oficial={len(oficial)} linhas | comuns={len(comuns)}")
        print(cabecalho)
        print(f"  Só no meu:     {len(so_meu):>4}")
        print(f"  Só no oficial: {len(so_of):>4}")
        linhas_saida.append(cabecalho)
        linhas_saida.append(f"  Só no meu:     {len(so_meu):>4}")
        linhas_saida.append(f"  Só no oficial: {len(so_of):>4}")

        if so_meu:
            linhas_saida.append(f"    exemplos: {sorted(so_meu)[:5]}")
        if so_of:
            linhas_saida.append(f"    exemplos: {sorted(so_of)[:5]}")

        if not comuns:
            linhas_saida.append("  (sem escolas em comum — nada a comparar)")
            continue

        cols_of_taxa = extrair_colunas_taxa(oficial)
        cols_meu_taxa = extrair_colunas_taxa(meu)
        mapeamento = mapear_colunas(cols_meu_taxa, cols_of_taxa)

        if not mapeamento:
            linhas_saida.append("  (nenhuma coluna de taxa mapeável)")
            linhas_saida.append(f"    cols oficial: {cols_of_taxa[:5]}...")
            linhas_saida.append(f"    cols meu:     {cols_meu_taxa[:5]}...")
            continue

        linhas_saida.append(f"  Colunas de taxa mapeadas: {len(mapeamento)}")
        # Mostra 3 exemplos do mapa para conferência
        exemplos = list(mapeamento.items())[:3]
        linhas_saida.append(f"    exemplo de mapa: {exemplos}")

        # Merge nos IDs comuns
        meu_ren = meu[[col_id_bruto] + list(mapeamento.values())].copy()
        meu_ren = meu_ren.rename(columns={col_id_bruto: "_id"})
        meu_ren["_id"] = normalizar_id(meu_ren["_id"])

        of_ren = oficial[[col_id_of] + list(mapeamento.keys())].copy()
        of_ren = of_ren.rename(columns={col_id_of: "_id"})
        of_ren["_id"] = normalizar_id(of_ren["_id"])

        # Renomeia colunas do meu para o nome oficial correspondente
        inv_map = {v: k for k, v in mapeamento.items()}
        meu_ren = meu_ren.rename(columns=inv_map)

        m = meu_ren.merge(of_ren, on="_id", how="inner",
                          suffixes=("_meu", "_of"))

        n_cols_comp = 0        # colunas com pelo menos 1 par não-nulo
        n_cols_diff = 0        # colunas com alguma diferença > TOL
        n_dif_total = 0

        for c in mapeamento.keys():
            vb = pd.to_numeric(
                m[f"{c}_meu"].replace("--", pd.NA).replace("·", pd.NA),
                errors="coerce"
            )
            vo = pd.to_numeric(
                m[f"{c}_of"].replace("--", pd.NA).replace("·", pd.NA),
                errors="coerce"
            )
            mask = vb.notna() & vo.notna()
            if mask.sum() == 0:
                continue
            n_cols_comp += 1
            diff = (vb[mask] - vo[mask]).abs()
            n_diff = int((diff > TOL).sum())
            if n_diff > 0:
                n_cols_diff += 1
                n_dif_total += n_diff
                msg = f"    {c}: {n_diff} difs (max {diff.max():.3f})"
                print(msg)
                linhas_saida.append(msg)

        msg = f"  Colunas efetivamente comparadas: {n_cols_comp}"
        print(msg)
        linhas_saida.append(msg)

        if n_cols_diff == 0:
            msg = "  ✅ TODAS as taxas comparadas batem (dentro de 0.01)"
        else:
            msg = (f"  ⚠️  {n_cols_diff} colunas com diferença "
                   f"({n_dif_total} valores no total)")
        print(msg)
        linhas_saida.append(msg)

    linhas_saida.append("")
    linhas_saida.append("=" * 70)
    linhas_saida.append("FIM DA VALIDAÇÃO")
    SAIDA.write_text("\n".join(linhas_saida), encoding="utf-8")
    print(f"\n>>> Salvo em: {SAIDA}")


if __name__ == "__main__":
    main()