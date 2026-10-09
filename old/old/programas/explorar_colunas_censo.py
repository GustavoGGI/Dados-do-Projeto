# -*- coding: utf-8 -*-
"""
Explora colunas do Censo Escolar para RR, ano a ano.

v3 — correções:
  - Padrão de IDA_secretaria: IN_SECRETARIA (não pega mais VINCULO_SAUDE).
  - Padrão de IIB_banheiro: IN_BANHEIRO_DENTRO_PREDIO com fallback IN_BANHEIRO.
  - Deduplicação por ano: prefere 'bruto/censo/' sobre 'origem/censo/'.
  - Para anos com vários arquivos, prefere o que tem 'escola' no nome e é maior.

Uso:
    python gustavo/programas/explorar_colunas_censo.py
    python gustavo/programas/explorar_colunas_censo.py --verbose
    python gustavo/programas/explorar_colunas_censo.py --anos 2019 2020
    python gustavo/programas/explorar_colunas_censo.py --buscar AGUA PISCINA
"""
import argparse
import io
import re
import warnings
import zipfile
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")

ANO_MINIMO = 2007


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

DADOS = BASE_PROJETO / "dados"
CENSO_BRUTO = DADOS / "bruto" / "censo"
CENSO_ORIGEM = DADOS / "origem" / "censo"
SAIDA = Path(__file__).resolve().parent.parent / "saida"
SAIDA.mkdir(exist_ok=True, parents=True)


# ------------------------------------------------------------------
# As 18 variáveis do Almeida & Mussato (padrões corrigidos)
# ------------------------------------------------------------------
VARIAVEIS_MUSSATO = {
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
    "IEP_projetor": [
        "IN_EQUIP_RETROPROJETOR",
        "IN_EQUIP_MULTIMIDIA",
        "IN_MATERIAL_PED_MULTIMIDIA",
        "IN_EQUIP_DATA_SHOW",
    ],
    "IEP_internet":         ["IN_INTERNET"],
}

COL_UF_CANDIDATOS = ("SG_UF", "UF", "SG_UF_ESCOLA")
CO_UF_CANDIDATOS = ("CO_UF", "COD_UF", "CODIGO_UF", "CO_UF_ESCOLA")
CHUNKSIZE = 500_000


# ------------------------------------------------------------------
# Descoberta de arquivos (com deduplicação)
# ------------------------------------------------------------------
def extrair_ano(nome):
    m = re.findall(r"20\d{2}|19\d{2}", nome)
    return int(m[0]) if m else None


def listar_arquivos():
    candidatos = []  # (ano, path, tipo, tem_escola)

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

    # Agrupa por ano e escolhe 1
    por_ano = {}
    for ano, path, tipo, tem_escola in candidatos:
        por_ano.setdefault(ano, []).append((tipo, path, tem_escola))

    resultado = []
    for ano in sorted(por_ano):
        lista = por_ano[ano]

        # prioridade 1: tem "escola" no nome
        com_escola = [x for x in lista if x[2]]
        if com_escola:
            lista = com_escola

        # prioridade 2: extraído > zip
        exts = [x for x in lista if x[0] == "ext"]
        if exts:
            lista = exts

        # prioridade 3: maior arquivo
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


def encontrar_matches(cols, padroes):
    cols_up = {c.upper().strip(): c for c in cols}
    res = {}
    for p in padroes:
        p_up = p.upper().strip()
        if p_up in cols_up:                      # nome exato → casa só ele
            res[p] = [cols_up[p_up]]
        else:                                    # padrão exploratório → substring
            res[p] = [c for c in cols if p_up in c.upper()]
    return res


def processar_arquivo(ano, arquivo, tipo, padroes):
    fonte, nome_interno = abrir_fonte(arquivo, tipo)
    if fonte is None:
        return {"__erro__": "não abri o CSV"}

    cols, sep = ler_cabecalho(fonte)
    if not cols:
        return {"__erro__": "cabeçalho ilegível"}

    col_uf, modo_uf = detectar_coluna_uf(cols)
    if col_uf is None:
        return {"__erro__": f"sem coluna de UF (1ªs: {cols[:3]})"}

    matches = encontrar_matches(cols, padroes)
    cols_interesse = set()
    for lst in matches.values():
        cols_interesse.update(lst)
    if not cols_interesse:
        return {"__sem_match__": True, "n_cols": len(cols)}

    usecols = sorted(cols_interesse | {col_uf})

    fonte, _ = abrir_fonte(arquivo, tipo)
    contagem = {c: 0 for c in cols_interesse}
    soma = {c: 0.0 for c in cols_interesse}
    n_rr = 0
    try:
        for chunk in pd.read_csv(fonte, sep=sep, encoding="latin1",
                                 usecols=usecols, chunksize=CHUNKSIZE,
                                 low_memory=False):
            if modo_uf == "sigla":
                mask = chunk[col_uf].astype(str).str.upper().str.strip() == "RR"
            else:
                mask = pd.to_numeric(chunk[col_uf], errors="coerce") == 14
            chunk = chunk[mask]
            n_rr += len(chunk)
            for c in cols_interesse:
                contagem[c] += int(chunk[c].notna().sum())
                v = pd.to_numeric(chunk[c], errors="coerce")
                soma[c] += float(v.sum())
    except Exception as e:
        return {"__erro__": f"falha lendo dados: {e}"}

    resultado = {"__n_rr__": n_rr}
    for c in cols_interesse:
        resultado[c] = {
            "n_filled": contagem[c],
            "pct": round(100 * contagem[c] / n_rr, 1) if n_rr else 0.0,
            "media": round(soma[c] / contagem[c], 3)
                     if contagem[c] > 0 else None,
        }
    return resultado


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--buscar", nargs="+", default=None)
    parser.add_argument("--anos", nargs="+", type=int, default=None)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    if args.buscar:
        padroes = list(args.buscar)
        rotulos = {p: p for p in padroes}
    else:
        padroes = []
        rotulos = {}
        for rotulo, lista in VARIAVEIS_MUSSATO.items():
            for p in lista:
                padroes.append(p)
                rotulos[p] = rotulo

    arquivos = listar_arquivos()
    if args.anos:
        arquivos = [x for x in arquivos if x[0] in args.anos]

    if not arquivos:
        print("Nenhum arquivo de Censo >= 2007 encontrado.")
        return

    print("=" * 78)
    print("EXPLORAÇÃO DE COLUNAS DO CENSO — RR")
    print(f"BASE_PROJETO: {BASE_PROJETO}")
    print(f"Padrões: {len(padroes)}  |  Anos: {[a for a, _, _ in arquivos]}")
    print("=" * 78)

    resultados = []

    for ano, arquivo, tipo in arquivos:
        try:
            res = processar_arquivo(ano, arquivo, tipo, padroes)
        except Exception as e:
            print(f"  [{ano}] ERRO: {e}")
            continue

        if res is None:
            continue
        if "__erro__" in res:
            print(f"  [{ano}] {res['__erro__']}")
            continue
        if "__sem_match__" in res:
            print(f"  [{ano}] sem match ({res['n_cols']} colunas)")
            continue

        n_rr = res.pop("__n_rr__")
        por_rotulo = {}
        for col_real, info in res.items():
            padrao_casou = None
            col_up = col_real.upper().strip()
            for p in padroes:
                p_up = p.upper().strip()
                if p_up == col_up or p_up in col_up:
                    padrao_casou = p
                    break
            rotulo = rotulos.get(padrao_casou, padrao_casou or "?")
            por_rotulo.setdefault(rotulo, []).append((col_real, info))
            resultados.append({
                "ANO": ano, "rotulo": rotulo,
                "coluna_real": col_real, "n_rr": n_rr,
                "n_filled": info["n_filled"],
                "pct_filled": info["pct"],
                "media": info["media"],
            })

        encontrados = sum(1 for r in por_rotulo if any(
            i["media"] is not None for _, i in por_rotulo[r]))
        print(f"  [{ano}] n_RR={n_rr:>4}  "
              f"rotulos_com_dado={encontrados:>2}/{len(rotulos)}")

        if args.verbose:
            for rot, cols in sorted(por_rotulo.items()):
                melhores = sorted(cols, key=lambda x: -(x[1]["media"] or -1))[:2]
                for col_real, info in melhores:
                    print(f"      {rot:<22} → {col_real:<40} "
                          f"media={info['media']}")

    if not resultados:
        print("\nNada a salvar.")
        return

    df_out = pd.DataFrame(resultados)
    csv_path = SAIDA / "relatorio_colunas_censo.csv"
    df_out.to_csv(csv_path, index=False)
    print(f"\n>>> CSV detalhado: {csv_path}")

    print("\n" + "=" * 78)
    print("RESUMO POR RÓTULO (anos cobertos)")
    print("=" * 78)
    por_rotulo = (df_out.groupby("rotulo")["ANO"]
                  .nunique().sort_values(ascending=False))
    for rot, n in por_rotulo.items():
        cols_ok = df_out[(df_out["rotulo"] == rot) &
                         (df_out["media"].notna())]["coluna_real"].unique()
        exemplo = cols_ok[0] if len(cols_ok) > 0 else "(sem dado)"
        print(f"  {rot:<22} {n:>2} anos  →  {exemplo}")


if __name__ == "__main__":
    main()