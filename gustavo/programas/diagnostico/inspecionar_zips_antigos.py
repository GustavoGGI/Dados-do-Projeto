# -*- coding: utf-8 -*-
"""
Inspeciona o CONTEÚDO dos zips antigos do INEP (2007-2015) para descobrir
por que o pipeline só conseguiu ler a partir de 2012.

Não modifica nada em dados/. Apenas lê e imprime.

Uso (de qualquer diretório):
    python gustavo/inspecionar_zips_antigos.py

Saída:
    - resumo na tela
    - gustavo/saida_inspecao.txt  (para levar ao professor)
"""
import io
import zipfile
from pathlib import Path

# gustavo/ está ao lado de dados/
BASE = Path(__file__).resolve().parent.parent
DADOS = BASE / "dados"
INDICADORES = DADOS / "origem" / "indicadores"
SAIDA = Path(__file__).resolve().parent / "saida_inspecao.txt"

# ------------------------------------------------------------------
# Coleta: todos os zips em dados/origem/indicadores/ que são de
# 2007-2015 e não foram reconhecidos como legíveis antes.
# ------------------------------------------------------------------
ZIPS_ALVO = [
    # tx_rend (alvo) 2007-2015
    "tx_rendimento_escolas_2007.zip",
    "tx_rendimento_escola_2008.zip",
    "tx_rendimento_escola_2009.zip",
    "tx_rendimento_escolas_2010_19082011.zip",
    "tx_rendimento_escolas_2011_2.zip",
    "tx_rendimento_escolas_2012.zip",
    "tx_rendimento_escolas_2013.zip",
    "tx_rendimento_escolas_2014.zip",
    "tx_rendimento_escolas_2015.zip",
    # TDI / ATU / IED / HAD 2007-2015 (podem ter os mesmos problemas)
    "TDI_2007.zip", "TDI_2008.zip", "TDI_2009.zip",
    "TDI_2010.zip", "TDI_2011.zip", "TDI_2012.zip",
    "TDI_2013.zip", "TDI_2014.zip", "TDI_2015.zip",
    "ATU_2007.zip", "ATU_2008.zip", "ATU_2009.zip",
    "ATU_2010.zip", "ATU_2011.zip", "ATU_2012.zip",
    "ATU_2013.zip", "ATU_2014.zip", "ATU_2015.zip",
    "IED_2007.zip", "IED_2008.zip", "IED_2009.zip",
    "IED_2010.zip", "IED_2011.zip", "IED_2012.zip",
    "IED_2013.zip", "IED_2014.zip", "IED_2015.zip",
    "HAD_2007.zip", "HAD_2008.zip", "HAD_2009.zip",
    "HAD_2010.zip", "HAD_2011.zip", "HAD_2012.zip",
    "HAD_2013.zip", "HAD_2014.zip", "HAD_2015.zip",
]


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def extensao(nome):
    """Retorna extensão em lowercase, com ponto, ou '' se não tiver."""
    return Path(nome).suffix.lower()


def tentar_ler_xls(conteudo):
    """Tenta ler .xls antigo. Retorna (ok, mensagem)."""
    try:
        import xlrd  # noqa
    except ImportError:
        return False, "xlrd NÃO instalado (não dá pra ler .xls ainda)"
    try:
        import pandas as pd
        df = pd.read_excel(io.BytesIO(conteudo), header=None, nrows=5)
        return True, f"xls OK — {df.shape[1]} colunas nas 5 primeiras linhas"
    except Exception as e:
        return False, f"xlrd presente mas falhou: {e}"


def tentar_ler_xlsx(conteudo):
    """Tenta ler .xlsx. Retorna (ok, mensagem)."""
    try:
        import pandas as pd
        df = pd.read_excel(io.BytesIO(conteudo), header=None, nrows=20)
        # procura linha de cabeçalho (mesma heurística do projeto)
        melhor, contagem = None, 0
        for i, row in df.iterrows():
            preenchidas = sum(1 for v in row if pd.notna(v))
            if preenchidas > contagem and preenchidas >= 5:
                contagem = preenchidas
                melhor = i
        if melhor is None:
            return False, "xlsx sem linha de cabeçalho detectável"
        return True, f"xlsx OK — cabeçalho na linha {melhor} ({contagem} cols)"
    except Exception as e:
        return False, f"xlsx falhou: {e}"


def tentar_ler_ods(conteudo):
    """Tenta ler .ods."""
    try:
        import pandas as pd
        df = pd.read_excel(io.BytesIO(conteudo), engine="odf",
                           header=None, nrows=20)
        return True, f"ods OK — {df.shape[1]} colunas"
    except Exception as e:
        return False, f"ods falhou: {e}"


def tentar_ler_csv(conteudo):
    """Tenta ler CSV (latin1, ;)."""
    try:
        import pandas as pd
        df = pd.read_csv(io.BytesIO(conteudo), sep=";", encoding="latin1",
                         nrows=3)
        return True, f"csv OK — {df.shape[1]} colunas"
    except Exception as e:
        return False, f"csv falhou: {e}"


def tentar_ler_pdf(conteudo):
    return False, "PDF — não utilizável para dados tabulares neste projeto"


LEITORES = {
    ".xlsx": tentar_ler_xlsx,
    ".xls":  tentar_ler_xls,
    ".ods":  tentar_ler_ods,
    ".csv":  tentar_ler_csv,
    ".pdf":  tentar_ler_pdf,
}


# ------------------------------------------------------------------
# Inspeção de um zip
# ------------------------------------------------------------------
def inspecionar(zip_path):
    linhas = []
    linhas.append("=" * 90)
    linhas.append(f"ZIP: {zip_path.name}")
    linhas.append("=" * 90)

    if not zip_path.exists():
        linhas.append("  [não encontrado]")
        return linhas

    try:
        zf = zipfile.ZipFile(zip_path)
    except Exception as e:
        linhas.append(f"  [não é zip válido: {e}]")
        return linhas

    with zf:
        infos = zf.infolist()
        linhas.append(f"  Total de arquivos internos: {len(infos)}")

        if not infos:
            linhas.append("  [zip vazio]")
            return linhas

        # 1) Lista tudo com tamanho e extensão
        linhas.append("")
        linhas.append("  Conteúdo bruto:")
        por_ext = {}
        for info in infos:
            ext = extensao(info.filename)
            por_ext[ext] = por_ext.get(ext, 0) + 1
            linhas.append(
                f"    {info.file_size:>12,} bytes  {info.filename}"
            )

        linhas.append("")
        linhas.append(f"  Extensões presentes: {por_ext}")

        # 2) Para cada arquivo legível, tenta abrir e reportar
        linhas.append("")
        linhas.append("  Teste de leitura:")
        algum_legivel = False
        for info in infos:
            nome = info.filename
            ext = extensao(nome)
            if ext not in LEITORES:
                continue
            try:
                conteudo = zf.read(nome)
            except Exception as e:
                linhas.append(f"    [{nome}] erro ao ler bytes: {e}")
                continue

            ok, msg = LEITORES[ext](conteudo)
            status = "OK  " if ok else "FALHA"
            linhas.append(f"    [{status}] {nome}  →  {msg}")
            if ok:
                algum_legivel = True

        # 3) Veredito
        linhas.append("")
        if algum_legivel:
            linhas.append("  VEREDITO: ✅ utilizável (pelo menos 1 arquivo lido)")
        else:
            linhas.append("  VEREDITO: ❌ NÃO utilizável neste momento")

    return linhas


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
def main():
    if not INDICADORES.exists():
        print(f"[ERRO] pasta não encontrada: {INDICADORES}")
        return

    todas = []
    for nome in ZIPS_ALVO:
        z = INDICADORES / nome
        todas.extend(inspecionar(z))
        todas.append("")

    # Resumo final
    todas.append("=" * 90)
    todas.append("RESUMO POR ZIP")
    todas.append("=" * 90)

    resumo = []
    for nome in ZIPS_ALVO:
        z = INDICADORES / nome
        if not z.exists():
            resumo.append(f"  {nome:<50} [ausente]")
            continue
        try:
            with zipfile.ZipFile(z) as zf:
                infos = zf.infolist()
                if not infos:
                    resumo.append(f"  {nome:<50} [vazio]")
                    continue
                exts = sorted({extensao(i.filename) or "(sem ext)"
                               for i in infos})
                legiveis = [e for e in exts if e in LEITORES]
                if legiveis:
                    resumo.append(
                        f"  {nome:<50} ✅ exts={exts}  legíveis={legiveis}"
                    )
                else:
                    resumo.append(
                        f"  {nome:<50} ❌ exts={exts}  (nada legível)"
                    )
        except Exception as e:
            resumo.append(f"  {nome:<50} [erro: {e}]")

    todas.extend(resumo)

    # Imprime e salva
    texto = "\n".join(todas)
    print(texto)
    SAIDA.write_text(texto, encoding="utf-8")
    print(f"\n>>> Salvo em: {SAIDA}")


if __name__ == "__main__":
    main()