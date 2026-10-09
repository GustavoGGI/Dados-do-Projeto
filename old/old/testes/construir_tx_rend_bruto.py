# -*- coding: utf-8 -*-
"""
Constrói o parquet BRUTO de tx_rend (taxa de rendimento escolar) para
Roraima, 2007-2025, lendo direto dos zips em dados/origem/indicadores/.

v4:
  - Detecção da coluna de ID por ANO (corrige "0 escolas" em 2007-2014).
  - Log do ID usado em cada ano no diagnóstico.
  - Nota sobre múltiplas abas em 2007-2011.

Flags:
  --force           refaz TUDO ignorando cache
  --force-year N    refaz só o ano N (pode repetir)

Uso:
  python gustavo/construir_tx_rend_bruto.py
  python gustavo/construir_tx_rend_bruto.py --force
  python gustavo/construir_tx_rend_bruto.py --force-year 2007
"""
import argparse
import io
import os
import re
import warnings
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")

BASE = Path(__file__).resolve().parent.parent
DADOS = BASE / "dados"
INDICADORES = DADOS / "origem" / "indicadores"
SAIDA = Path(__file__).resolve().parent / "saida"
CACHE = SAIDA / "cache"
SAIDA.mkdir(exist_ok=True)
CACHE.mkdir(exist_ok=True)

ANOS = list(range(2007, 2026))
MAX_WORKERS = min(4, (os.cpu_count() or 4))

UFS_BR = {"AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG",
          "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR",
          "RS", "SC", "SE", "SP", "TO"}

# Ordem importa: primeiro os nomes novos (2015+), depois os antigos.
CANDIDATOS_ID = (
    "CO_ENTIDADE",
    "Código da Escola",
    "COD_ESCOLA",
    "CO_ESCOLA",
    "CODIGO_ESCOLA",
)


# ------------------------------------------------------------------
# Descoberta dos zips
# ------------------------------------------------------------------
def mapear_zips_escola():
    if not INDICADORES.exists():
        raise FileNotFoundError(f"Pasta não encontrada: {INDICADORES}")
    mapa = {}
    for z in sorted(INDICADORES.glob("*.zip")):
        nome = z.name.lower()
        if not ("tx_rend" in nome or "taxa_rend" in nome):
            continue
        if "escola" not in nome:
            continue
        if "brasil" in nome or "municipio" in nome:
            continue
        m = re.findall(r"20\d{2}", nome)
        if not m:
            continue
        ano = int(m[0])
        if ano not in ANOS or ano in mapa:
            continue
        mapa[ano] = z
    return mapa


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def dedup_cols(df):
    seen, novas = {}, []
    for c in df.columns:
        c = str(c)
        if c in seen:
            seen[c] += 1
            novas.append(f"{c}__{seen[c]}")
        else:
            seen[c] = 0
            novas.append(c)
    df.columns = novas
    return df


def fixar_tipos_parquet(df):
    """Converte colunas object com tipos misturados para string (pyarrow)."""
    for c in df.columns:
        if df[c].dtype != object:
            continue
        s = df[c].dropna()
        if len(s) == 0:
            continue
        sample = s if len(s) <= 5000 else s.sample(5000, random_state=1)
        tipos = set(type(v).__name__ for v in sample)
        if len(tipos) > 1:
            df[c] = df[c].astype(str).replace({"nan": None, "None": None, "": None})
    return df


def detectar_cabecalho(df_raw, max_rows=30):
    """
    Detecta geração e retorna (linha_inicio_cabecalho, n_linhas_cabecalho).
    - Nova/intermediária: 1 linha técnica (tap_/1_CAT_/NU_ANO_CENSO).
    - Antiga (2007-2014): 2 linhas combinadas.
    """
    padroes_tecnicos = (
        "tap_", "tre_", "tab_",
        "1_cat_", "2_cat_", "3_cat_",
        "nu_ano_censo", "co_entidade",
    )

    for i in range(min(max_rows, len(df_raw))):
        vals = [str(v).strip().lower() for v in df_raw.iloc[i] if pd.notna(v)]
        if len(vals) < 40:
            continue
        n_tec = sum(1 for p in padroes_tecnicos if any(p in v for v in vals))
        if n_tec >= 2:
            return i, 1

    for i in range(min(max_rows - 1, len(df_raw) - 1)):
        vals1 = [v for v in df_raw.iloc[i] if pd.notna(v)]
        if len(vals1) < 10:
            continue
        prim = str(vals1[0]).strip().lower()
        if prim in ("ano", "nu_ano_censo"):
            prox = [v for v in df_raw.iloc[i + 1] if pd.notna(v)]
            if len(prox) >= 40:
                return i, 2

    return None, 0


def construir_colunas(df_raw, linha, n_linhas):
    l1 = df_raw.iloc[linha].tolist()
    if n_linhas == 1:
        return [str(v).strip() if pd.notna(v) else f"_col_{j}"
                for j, v in enumerate(l1)]

    l2 = df_raw.iloc[linha + 1].tolist()
    cols = []
    for j, v1 in enumerate(l1):
        s1 = str(v1).strip() if pd.notna(v1) else ""
        s2 = ""
        if j < len(l2) and pd.notna(l2[j]):
            s2 = str(l2[j]).strip()
        if s1 in ("·", "--", "-", "nan"):
            s1 = ""
        if s2 in ("·", "--", "-", "nan"):
            s2 = ""
        if s1 and s2:
            cols.append(f"{s1} - {s2}")
        elif s1:
            cols.append(s1)
        elif s2:
            cols.append(s2)
        else:
            cols.append(f"_col_{j}")
    return cols


def ler_planilhas_do_zip(zip_path):
    with zipfile.ZipFile(zip_path) as zf:
        arquivos = [i for i in zf.infolist() if not i.is_dir()]
        xlsx = sorted([i for i in arquivos if i.filename.lower().endswith(".xlsx")],
                      key=lambda i: -i.file_size)
        xls = sorted([i for i in arquivos
                      if i.filename.lower().endswith(".xls")
                      and not i.filename.lower().endswith(".xlsx")],
                     key=lambda i: -i.file_size)
        if xlsx:
            escolhido = xlsx[0]
        elif xls:
            escolhido = xls[0]
        else:
            raise ValueError(f"Nenhum xls/xlsx em {zip_path.name}")
        conteudo = zf.read(escolhido.filename)
        nome_interno = escolhido.filename

    engine = "xlrd" if nome_interno.lower().endswith(".xls") else "openpyxl"
    try:
        sheets = pd.read_excel(io.BytesIO(conteudo), sheet_name=None,
                               header=None, engine=engine)
    except Exception as e:
        raise RuntimeError(f"Falha ao abrir {nome_interno}: {e}") from e

    resultados = []
    for nome_sheet, df_raw in sheets.items():
        linha, n_linhas = detectar_cabecalho(df_raw)
        if linha is None:
            continue
        colunas = construir_colunas(df_raw, linha, n_linhas)
        primeira_dado = linha + n_linhas
        while primeira_dado < len(df_raw) and df_raw.iloc[primeira_dado].notna().sum() == 0:
            primeira_dado += 1
        if primeira_dado >= len(df_raw):
            continue
        dados = df_raw.iloc[primeira_dado:].copy()
        dados.columns = colunas
        dados = dados.dropna(how="all")
        if len(dados) == 0:
            continue
        dados = dedup_cols(dados)
        resultados.append((nome_sheet, dados, linha, len(colunas)))
    return resultados, nome_interno


def achar_coluna_uf(df, min_ufs=5):
    melhor, score = None, 0
    for c in df.columns:
        s = df[c].astype(str).str.strip().str.upper()
        unicos = set(s.dropna().unique())
        if not unicos or len(unicos) > 40:
            continue
        n_ufs = len(unicos & UFS_BR)
        if n_ufs >= min_ufs and n_ufs > score:
            score = n_ufs
            melhor = c
    return melhor


def filtrar_rr(df):
    info = {"metodo": None, "coluna": None, "n": 0, "valores_col": None}
    col_uf = achar_coluna_uf(df)
    if col_uf is not None:
        s = df[col_uf].astype(str).str.strip().str.upper()
        mask = s == "RR"
        n = int(mask.sum())
        if n >= 3:
            info.update(metodo="uf_sigla", coluna=col_uf, n=n,
                        valores_col=sorted(set(s.unique()) & UFS_BR))
            return df[mask].copy(), info
    for c in df.columns:
        if str(c).upper() in ("CO_UF", "COD_UF", "CO_UF_ESCOLA", "CODIGO_UF"):
            v = pd.to_numeric(df[c], errors="coerce")
            mask = v == 14
            n = int(mask.sum())
            if n >= 3:
                info.update(metodo="co_uf==14", coluna=c, n=n)
                return df[mask].copy(), info
    best_col, best_n, best_mask = None, 0, None
    for c in df.columns:
        s = df[c].astype(str).str.upper()
        mask = s.str.contains("RORAIMA", na=False)
        n = int(mask.sum())
        if n > best_n:
            best_n, best_col, best_mask = n, c, mask
    if best_col and best_n >= 3:
        info.update(metodo="contains_RORAIMA", coluna=best_col, n=best_n)
        return df[best_mask].copy(), info
    info["metodo"] = "NENHUM"
    return df.iloc[0:0].copy(), info


def detectar_coluna_id(sub):
    """
    [FIX v4] Detecta a coluna de ID DENTRO deste subconjunto (ano).
    Não basta estar presente — precisa ter pelo menos 1 valor não-nulo,
    senão a coluna existe globalmente mas está vazia neste ano.
    """
    for c in CANDIDATOS_ID:
        if c in sub.columns and sub[c].notna().sum() > 0:
            return c
    return None


# ------------------------------------------------------------------
# Processamento de 1 ano (com cache)
# ------------------------------------------------------------------
def processar_ano(ano, zip_path, force=False):
    cache_path = CACHE / f"{ano}.parquet"

    if not force and cache_path.exists():
        try:
            df = pd.read_parquet(cache_path)
            return ano, df, f"{ano}: [cache] {len(df):,} linhas", None
        except Exception:
            pass

    try:
        planilhas, nome_interno = ler_planilhas_do_zip(zip_path)
    except Exception as e:
        return ano, None, f"{ano}: ERRO ao abrir -> {e}", str(e)

    partes, total, sheet_infos = [], 0, []
    info_geral = None

    for nome_sheet, df, _, n_cols in planilhas:
        total += len(df)
        df_rr, info = filtrar_rr(df)
        if info_geral is None and info["n"] > 0:
            info_geral = info
        sheet_infos.append(f"{nome_sheet}[{n_cols}c/{len(df)}r→{len(df_rr)}rr]")
        if len(df_rr) > 0:
            df_rr = df_rr.copy()
            df_rr["ANO"] = ano
            partes.append(df_rr)

    if not partes:
        diag = (f"{ano}: interno={nome_interno} | sheets={sheet_infos} | "
                f"total={total} | RR=0 | filtro=NENHUM")
        return ano, None, diag, None

    df_ano = pd.concat(partes, ignore_index=True, sort=False)
    df_ano = dedup_cols(df_ano)
    df_ano = fixar_tipos_parquet(df_ano)

    try:
        df_ano.to_parquet(cache_path, index=False)
    except Exception as e:
        return ano, df_ano, f"{ano}: cache falhou -> {e}", None

    metodo = info_geral["metodo"] if info_geral else "?"
    coluna = info_geral["coluna"] if info_geral else "?"
    vals = info_geral.get("valores_col") if info_geral else None
    vals_str = f" vals={vals}" if vals else ""
    n_sheets = len(planilhas)
    sheets_str = f" n_sheets={n_sheets}" if n_sheets > 1 else ""
    diag = (f"{ano}: interno={nome_interno}{sheets_str} | "
            f"total={total} | RR={len(df_ano)} | "
            f"filtro={metodo} (col={coluna}){vals_str}")
    return ano, df_ano, diag, None


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--force-year", type=int, action="append", default=[])
    args = parser.parse_args()

    force_years = set(args.force_year)

    print("=" * 80)
    print("CONSTRUÇÃO DO PARQUET BRUTO — tx_rend RR 2007-2025")
    print(f"Threads: {MAX_WORKERS}   Cache: {CACHE}")
    if args.force:
        print("Modo: --force (ignora todo o cache)")
    elif force_years:
        print(f"Modo: --force-year {sorted(force_years)}")
    print("=" * 80)

    mapa = mapear_zips_escola()
    print(f"\nZips encontrados: {len(mapa)}\n")

    resultados, diags, erros = {}, [], []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = {}
        for ano in ANOS:
            if ano not in mapa:
                continue
            force = args.force or ano in force_years
            futs[ex.submit(processar_ano, ano, mapa[ano], force)] = ano
        for fut in as_completed(futs):
            a, df, diag, err = fut.result()
            print(f"  {diag}")
            diags.append(diag)
            if err:
                erros.append(f"{a}: {err}")
            if df is not None:
                resultados[a] = df

    for ano in ANOS:
        if ano not in mapa:
            diags.append(f"{ano}: SEM ZIP")

    if not resultados:
        print("\n[!] Nada coletado. Abortando.")
        return

    todas_cols, vistos = [], set()
    for a in sorted(resultados):
        for c in resultados[a].columns:
            if c not in vistos:
                vistos.add(c)
                todas_cols.append(c)

    frames = [resultados[a].reindex(columns=todas_cols)
              for a in sorted(resultados)]
    df_final = pd.concat(frames, ignore_index=True)
    df_final = dedup_cols(df_final)
    df_final = fixar_tipos_parquet(df_final)

    print(f"\n>>> Consolidado: {df_final.shape[0]:,} linhas × "
          f"{df_final.shape[1]} colunas")

    # -------- Diagnóstico por ano (ID detectado dentro de cada sub) --------
    print("\nLinhas / escolas únicas por ano:")
    dup_linhas = []
    for ano in sorted(df_final["ANO"].unique()):
        sub = df_final[df_final["ANO"] == ano]
        col_id_ano = detectar_coluna_id(sub)
        if col_id_ano:
            n_escolas = sub[col_id_ano].nunique()
            n_dup = len(sub) - n_escolas
            extra = f" ({n_dup} duplicatas)" if n_dup else ""
            linha = (f"  {ano}: {len(sub):>4} linhas, {n_escolas:>4} escolas"
                     f"{extra} [id={col_id_ano}]")
        else:
            linha = (f"  {ano}: {len(sub):>4} linhas "
                     f"(coluna de ID não identificada)")
        print(linha)
        dup_linhas.append(linha)

    # -------- Amostra de duplicatas (primeiro ano com dup) --------
    amostra_dup = []
    for ano in sorted(df_final["ANO"].unique()):
        sub = df_final[df_final["ANO"] == ano]
        col_id_ano = detectar_coluna_id(sub)
        if not col_id_ano:
            continue
        contagem = sub[col_id_ano].value_counts()
        tops = contagem[contagem > 1].head(3)
        if len(tops) > 0:
            amostra_dup.append(
                f"\nAmostra de duplicatas em {ano} (id={col_id_ano}):"
            )
            for cod, n in tops.items():
                sub_dup = sub[sub[col_id_ano] == cod]
                info_extra = []
                for c2 in sub_dup.columns:
                    if c2 in (col_id_ano, "ANO"):
                        continue
                    vals = sub_dup[c2].dropna().unique()
                    if len(vals) > 1:
                        info_extra.append(f"{c2}={list(vals)[:2]}")
                    if len(info_extra) >= 3:
                        break
                amostra_dup.append(
                    f"  {col_id_ano}={cod}: {n} linhas | varia em: {info_extra}"
                )
            if len(amostra_dup) > 15:
                break

    # -------- Salva parquet final --------
    out_parquet = SAIDA / "tx_rend_rr_2007_2025_bruto.parquet"
    df_final.to_parquet(out_parquet, index=False)
    print(f"\n>>> Parquet: {out_parquet}")

    # -------- Diagnóstico em arquivo --------
    out_diag = SAIDA / "diagnostico_bruto.txt"
    linhas = [
        "DIAGNÓSTICO — tx_rend RR 2007-2025 (bruto)",
        "=" * 60,
        f"Total de linhas: {len(df_final):,}",
        f"Total de colunas: {df_final.shape[1]}",
        "",
        "Nota sobre gerações de layout:",
        "  - 2007-2011: cabeçalho em 2 linhas, planilha dividida em 6 abas",
        "    (uma por região do Brasil). Filtro RR aplicado por aba.",
        "  - 2012-2014: cabeçalho em 2 linhas, aba única 'ESCOLAS'.",
        "  - 2015-2020: cabeçalho técnico em 1 linha, nomes tap_/tre_/tab_.",
        "  - 2021-2025: cabeçalho técnico em 1 linha, nomes 1_CAT_/2_CAT_/3_CAT_.",
        "",
        "Por ano (escolas únicas detectadas por coluna de ID interna):",
    ] + dup_linhas + [""]
    if amostra_dup:
        linhas += ["", "Amostra de duplicatas (escolas que aparecem >1x no mesmo ano):"]
        linhas += amostra_dup
    linhas += ["", "Colunas (todas):"]
    for c in df_final.columns:
        linhas.append(f"  - {c}")
    linhas += ["", "Detalhes por zip:"]
    for d in diags:
        linhas.append(f"  {d}")
    if erros:
        linhas += ["", "Erros:"]
        for e in erros:
            linhas.append(f"  {e}")
    out_diag.write_text("\n".join(linhas), encoding="utf-8")
    print(f">>> Diagnóstico: {out_diag}")


if __name__ == "__main__":
    main()