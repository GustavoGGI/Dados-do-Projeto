# -*- coding: utf-8 -*-
"""
Extrai as 18 variáveis do Censo Escolar (Almeida & Mussato) para RR,
2007-2025, e junta com o tx_rend selecionado.

- Coalesce dinâmico: se uma variável tem 2 candidatas (ex: IN_BANHEIRO_DENTRO_PREDIO
  e IN_BANHEIRO), pega o primeiro valor não-nulo por linha/ano.
- Cache por ano em gustavo/saida/cache_censo/{ano}.parquet.
- Merge final: LEFT a partir do tx_rend (todas as escolas com rendimento,
  com NaN onde o Censo não cobriu).

Saída:
    gustavo/saida/censo_rr_2007_2025_features.parquet
    gustavo/saida/base_completa.parquet
    gustavo/saida/diagnostico_features_censo.txt
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
# Descoberta
# ------------------------------------------------------------------
def achar_base_projeto():
    here = Path(__file__).resolve().parent
    for p in [here, *here.parents]:
        for nome in ("abandono-escolar", "abandono_escolar"):
            cand = p / nome
            if cand.is_dir() and (cand / "dados").is_dir():
                return cand
    return None


BASE_PROJETO = achar_base_projeto()
if BASE_PROJETO is None:
    raise SystemExit("[ERRO] não achei 'abandono-escolar/dados/'")

DADOS = BASE_PROJETO / "dados"
CENSO_BRUTO = DADOS / "bruto" / "censo"
CENSO_ORIGEM = DADOS / "origem" / "censo"
GUSTAVO = Path(__file__).resolve().parent.parent
SAIDA = GUSTAVO / "saida"
CACHE = SAIDA / "cache_censo"
SAIDA.mkdir(exist_ok=True, parents=True)
CACHE.mkdir(exist_ok=True, parents=True)

TX_REND_PATH = SAIDA / "tx_rend_rr_2007_2025_selecionado.parquet"

ANO_MINIMO = 2007
ANOS = list(range(2007, 2026))
CHUNKSIZE = 500_000

COL_UF_CANDIDATOS = ("SG_UF", "UF", "SG_UF_ESCOLA")
CO_UF_CANDIDATOS = ("CO_UF", "COD_UF", "CODIGO_UF", "CO_UF_ESCOLA")
COL_ID_CANDIDATOS = ("CO_ENTIDADE", "COD_ESCOLA", "CO_ESCOLA")

# ------------------------------------------------------------------
# Dicionário com as 18 variáveis + candidatas (ordem = prioridade)
# ------------------------------------------------------------------
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
# Descoberta de arquivos
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

    # Quais candidatas existem neste ano
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

    # Ler em chunks e filtrar RR
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

    # Coalesce: pega primeiro não-nulo entre candidatas
    out = pd.DataFrame({
        "ANO": ano,
        "CO_ENTIDADE": df[col_id].astype(str).str.strip(),
    })
    stats = {}
    for var, existentes in candidatos_por_var.items():
        if not existentes:
            out[var] = pd.NA
            stats[var] = ("(sem coluna)", 0.0)
            continue
        sub = df[existentes].apply(pd.to_numeric, errors="coerce")
        coalescida = sub.bfill(axis=1).iloc[:, 0]
        out[var] = coalescida
        pct = round(100 * coalescida.notna().mean(), 1) if len(coalescida) else 0.0
        stats[var] = ("|".join(existentes), pct)

    # Cache
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
    print("FEATURES DO CENSO (18 do Almeida & Mussato) — RR 2007-2025")
    print("=" * 78)

    arquivos = listar_arquivos()
    print(f"Arquivos: {len(arquivos)}")

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

    # Salva features puras
    features_path = SAIDA / "censo_rr_2007_2025_features.parquet"
    censo.to_parquet(features_path, index=False)
    print(f">>> {features_path}")

    # Merge com tx_rend
    if not TX_REND_PATH.exists():
        print(f"\n[!] Não achei {TX_REND_PATH} — salvando só as features.")
        return

    tx = pd.read_parquet(TX_REND_PATH)
    tx["CO_ENTIDADE"] = tx["CO_ENTIDADE"].astype(str).str.strip()
    censo["CO_ENTIDADE"] = censo["CO_ENTIDADE"].astype(str).str.strip()

    base = tx.merge(censo, on=["ANO", "CO_ENTIDADE"], how="left",
                    suffixes=("", "_censo"))
    print(f"\n>>> Base completa: {base.shape[0]} linhas × "
          f"{base.shape[1]} colunas")

    # Diagnóstico
    print("\nCobertura das features por ano:")
    vars_mussato = list(VARIAVEIS.keys())
    diag = []
    for ano in sorted(base["ANO"].unique()):
        sub = base[base["ANO"] == ano]
        n_escolas = len(sub)
        coberturas = [f"{v}:{100*sub[v].notna().mean():.0f}%"
                      for v in vars_mussato]
        media_geral = round(sub[vars_mussato].notna().mean().mean() * 100, 1)
        print(f"  {ano}: n={n_escolas}, cobertura_media={media_geral}%")
        diag.append(f"{ano}: n={n_escolas}, cobertura_media={media_geral}%")

    out_path = SAIDA / "base_completa.parquet"
    base.to_parquet(out_path, index=False)
    print(f"\n>>> {out_path}")

    diag_path = SAIDA / "diagnostico_features_censo.txt"
    linhas = [
        "FEATURES DO CENSO — RR 2007-2025",
        "=" * 60,
        f"Linhas: {base.shape[0]}",
        f"Colunas: {base.shape[1]}",
        "",
        "Colunas do Censo (18):",
    ] + [f"  - {v}" for v in vars_mussato] + [
        "",
        "Cobertura por ano (escolas com tx_rend):",
    ] + [f"  {d}" for d in diag]
    diag_path.write_text("\n".join(linhas), encoding="utf-8")
    print(f">>> {diag_path}")


if __name__ == "__main__":
    main()