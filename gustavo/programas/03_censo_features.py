# -*- coding: utf-8 -*-
"""
03 — Extrai as 17 features de infraestrutura do Censo Escolar (Almeida &
Mussato, 2023) para RR, 2007-2025.

Entrada:  abandono-escolar/dados/{bruto,origem}/censo/
Saída:    gustavo/saida/etapas/03_censo_features.parquet
Cache:    gustavo/cache/censo/{ano}.parquet
Relatório: gustavo/saida/relatorios/diagnostico_features_censo.txt

Coalesce dinâmico: se uma variável tem 2 candidatas (ex: IN_BANHEIRO_DENTRO_PREDIO
e IN_BANHEIRO), pega o primeiro valor não-nulo por linha/ano.

Nota: 2007 tem 4 features 100% vazias no Brasil inteiro (lacuna real do
INEP): IDA_despensa, IDA_secretaria, IDA_refeitorio, IDP_patio_coberto.

Uso:  python programas/03_censo_features.py [--force]
"""
import argparse
import io
import re
import warnings
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")

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
DADOS = BASE_PROJETO / "dados"
CENSO_BRUTO = DADOS / "bruto" / "censo"
CENSO_ORIGEM = DADOS / "origem" / "censo"
SAIDA_ETAPAS = GUSTAVO / "saida" / "etapas"
SAIDA_REL = GUSTAVO / "saida" / "relatorios"
CACHE = GUSTAVO / "cache" / "censo"

SAIDA_ETAPAS.mkdir(parents=True, exist_ok=True)
SAIDA_REL.mkdir(parents=True, exist_ok=True)
CACHE.mkdir(parents=True, exist_ok=True)

OUT = SAIDA_ETAPAS / "03_censo_features.parquet"
OUT_REL = SAIDA_REL / "diagnostico_features_censo.txt"

ANO_MINIMO = 2007
CHUNKSIZE = 500_000

COL_UF_CANDIDATOS = ("SG_UF", "UF", "SG_UF_ESCOLA")
CO_UF_CANDIDATOS = ("CO_UF", "COD_UF", "CODIGO_UF", "CO_UF_ESCOLA")
COL_ID_CANDIDATOS = ("CO_ENTIDADE", "COD_ESCOLA", "CO_ESCOLA")

# 17 features do Almeida & Mussato (valor = lista de candidatas, em ordem)
VARIAVEIS = {
    "IIB_agua_potavel":     ["IN_AGUA_FILTRADA", "IN_AGUA_POTAVEL"],
    "IIB_energia_rede":     ["IN_ENERGIA_REDE_PUBLICA"],
    "IIB_coleta_lixo":      ["IN_LIXO_SERVICO_COLETA"],
    "IIB_banheiro":         ["IN_BANHEIRO_DENTRO_PREDIO", "IN_BANHEIRO"],
    "IDA_despensa":         ["IN_DESPENSA"],
    "IDA_refeitorio":       ["IN_REFEITORIO"],
    "IDA_sala_diretoria":   ["IN_SALA_DIRETORIA"],
    "IDA_sala_professor":   ["IN_SALA_PROFESSOR"],
    "IDA_secretaria":       ["IN_SECRETARIA"],
    "IDP_biblioteca":       ["IN_BIBLIOTECA_SALA_LEITURA", "IN_BIBLIOTECA"],
    "IDP_lab_informatica":  ["IN_LABORATORIO_INFORMATICA"],
    "IDP_patio_coberto":    ["IN_PATIO_COBERTO"],
    "IDP_quadra_esportes":  ["IN_QUADRA_ESPORTES"],
    "IEP_computador":       ["IN_COMPUTADOR"],
    "IEP_impressora":       ["IN_EQUIP_IMPRESSORA"],
    "IEP_projetor":         ["IN_EQUIP_RETROPROJETOR",
                             "IN_EQUIP_MULTIMIDIA",
                             "IN_MATERIAL_PED_MULTIMIDIA",
                             "IN_EQUIP_DATA_SHOW"],
    "IEP_internet":         ["IN_INTERNET"],
}


# ------------------------------------------------------------------
# Descoberta de arquivos (com deduplicação por ano)
# ------------------------------------------------------------------
def extrair_ano(nome):
    m = re.findall(r"20\d{2}|19\d{2}", nome)
    return int(m[0]) if m else None


def listar_arquivos():
    candidatos = []
    if CENSO_BRUTO.exists():
        for f in sorted(CENSO_BRUTO.iterdir()):
            if f.is_file() and f.suffix.lower() == ".csv":
                ano = extrair_ano(f.name)
                if ano and ano >= ANO_MINIMO:
                    candidatos.append((ano, f, "ext", "escola" in f.name.lower()))
    if CENSO_ORIGEM.exists():
        for f in sorted(CENSO_ORIGEM.glob("*.zip")):
            ano = extrair_ano(f.name)
            if ano and ano >= ANO_MINIMO:
                candidatos.append((ano, f, "zip", "escola" in f.name.lower()))

    por_ano = {}
    for ano, path, tipo, tem_escola in candidatos:
        por_ano.setdefault(ano, []).append((tipo, path, tem_escola))

    resultado = []
    for ano in sorted(por_ano):
        lista = por_ano[ano]
        com_escola = [x for x in lista if x[2]]
        if com_escola:
            lista = com_escola
        exts = [x for x in lista if x[0] == "ext"]
        if exts:
            lista = exts
        escolhido = max(lista, key=lambda x: x[1].stat().st_size)
        resultado.append((ano, escolhido[1], escolhido[0]))
    return resultado


def abrir_fonte(arquivo, tipo):
    if tipo == "zip":
        try:
            zf = zipfile.ZipFile(arquivo)
        except Exception:
            return None, None
        csvs = [i for i in zf.infolist()
                if i.filename.lower().endswith(".csv")]
        if not csvs:
            zf.close()
            return None, None
        maior = max(csvs, key=lambda i: i.file_size)
        conteudo = zf.read(maior.filename)
        zf.close()
        return io.BytesIO(conteudo), maior.filename
    return arquivo, arquivo.name


def ler_cabecalho(fonte):
    for sep in (";", ",", "|"):
        try:
            if hasattr(fonte, "seek"):
                fonte.seek(0)
            cols = list(pd.read_csv(fonte, sep=sep, encoding="latin1",
                                    nrows=0).columns)
            if len(cols) >= 5:
                return cols, sep
        except Exception:
            continue
    return [], None


def detectar_coluna_uf(cols):
    for c in cols:
        if c.upper() in [x.upper() for x in COL_UF_CANDIDATOS]:
            return c, "sigla"
    for c in cols:
        if c.upper() in [x.upper() for x in CO_UF_CANDIDATOS]:
            return c, "codigo"
    return None, None


def detectar_coluna_id(cols):
    for c in cols:
        if c.upper() in [x.upper() for x in COL_ID_CANDIDATOS]:
            return c
    return None


# ------------------------------------------------------------------
# Processar 1 ano
# ------------------------------------------------------------------
def processar_ano(ano, arquivo, tipo, force=False):
    cache_path = CACHE / f"{ano}.parquet"
    if not force and cache_path.exists():
        try:
            return ano, pd.read_parquet(cache_path), f"[cache] {ano}"
        except Exception:
            pass

    fonte, _ = abrir_fonte(arquivo, tipo)
    cols, sep = ler_cabecalho(fonte)
    if not cols:
        return ano, None, f"{ano}: cabeçalho ilegível"

    col_uf, modo_uf = detectar_coluna_uf(cols)
    if col_uf is None:
        return ano, None, f"{ano}: sem coluna UF"

    col_id = detectar_coluna_id(cols)
    if col_id is None:
        return ano, None, f"{ano}: sem coluna de ID"

    cols_up = {c.upper().strip(): c for c in cols}
    candidatos_por_var = {}
    todas_candidatas = set()
    for var, lista in VARIAVEIS.items():
        existentes = []
        for cand in lista:
            if cand.upper() in cols_up:
                existentes.append(cols_up[cand.upper()])
        candidatos_por_var[var] = existentes
        todas_candidatas.update(existentes)

    if not todas_candidatas:
        return ano, None, f"{ano}: nenhuma candidata presente"

    usecols = sorted(todas_candidatas | {col_uf, col_id})

    fonte, _ = abrir_fonte(arquivo, tipo)
    partes = []
    n_total = n_rr = 0
    try:
        for chunk in pd.read_csv(fonte, sep=sep, encoding="latin1",
                                 usecols=usecols, chunksize=CHUNKSIZE,
                                 low_memory=False):
            n_total += len(chunk)
            if modo_uf == "sigla":
                mask = chunk[col_uf].astype(str).str.upper().str.strip() == "RR"
            else:
                mask = pd.to_numeric(chunk[col_uf], errors="coerce") == 14
            chunk = chunk[mask]
            n_rr += len(chunk)
            if len(chunk) == 0:
                continue
            partes.append(chunk)
    except Exception as e:
        return ano, None, f"{ano}: falha lendo dados ({e})"

    if not partes:
        return ano, None, f"{ano}: nenhuma linha RR"

    df = pd.concat(partes, ignore_index=True)

    out = pd.DataFrame({
        "ANO": ano,
        "CO_ENTIDADE": df[col_id].astype(str).str.strip(),
    })
    for var, existentes in candidatos_por_var.items():
        if not existentes:
            out[var] = pd.NA
            continue
        sub = df[existentes].apply(pd.to_numeric, errors="coerce")
        out[var] = sub.bfill(axis=1).iloc[:, 0]

    try:
        out.to_parquet(cache_path, index=False)
    except Exception as e:
        return ano, None, f"{ano}: cache falhou ({e})"

    return ano, out, f"{ano}: n_RR={len(out)} ({len(candidatos_por_var)} vars)"


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    print("=" * 78)
    print("03 — CENSO FEATURES (17 do Almeida & Mussato) — RR 2007-2025")
    print(f"BASE_PROJETO: {BASE_PROJETO}")
    print(f"Cache:        {CACHE}")
    if args.force:
        print("Modo: --force (ignora cache)")
    print("=" * 78)

    arquivos = listar_arquivos()
    print(f"Arquivos: {len(arquivos)}\n")

    resultados = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(processar_ano, a, f, t, args.force): a
                for a, f, t in arquivos}
        for fut in as_completed(futs):
            ano, df, msg = fut.result()
            print(f"  {msg}")
            if df is not None:
                resultados.append((ano, df))

    if not resultados:
        print("[!] Nada processado.")
        return

    resultados.sort(key=lambda x: x[0])
    censo = pd.concat([df for _, df in resultados], ignore_index=True)
    print(f"\n>>> Censo features: {censo.shape[0]} linhas × "
          f"{censo.shape[1]} colunas")

    censo.to_parquet(OUT, index=False)
    print(f">>> {OUT}")

    # Relatório
    vars_mussato = list(VARIAVEIS.keys())
    linhas = [
        "FEATURES DO CENSO — RR 2007-2025",
        "=" * 60,
        f"Linhas: {censo.shape[0]}",
        f"Colunas: {censo.shape[1]}",
        "",
        "Colunas (17):",
    ] + [f"  - {v}" for v in vars_mussato] + [
        "",
        "Cobertura por ano (escolas do Censo, não do tx_rend):",
        f"{'ano':>5}{'n':>7}{'cobertura_media':>20}",
    ]
    for ano in sorted(censo["ANO"].unique()):
        sub = censo[censo["ANO"] == ano]
        cob = round(sub[vars_mussato].notna().mean().mean() * 100, 1)
        linhas.append(f"{ano:>5}{len(sub):>7}{cob:>20}")

    linhas += [
        "",
        "Nota: 2007 tem 4 features 100% vazias no Brasil inteiro (lacuna real",
        "do INEP): IDA_despensa, IDA_secretaria, IDA_refeitorio, IDP_patio_coberto.",
    ]
    OUT_REL.write_text("\n".join(linhas), encoding="utf-8")
    print(f">>> Relatório: {OUT_REL}")


if __name__ == "__main__":
    main()