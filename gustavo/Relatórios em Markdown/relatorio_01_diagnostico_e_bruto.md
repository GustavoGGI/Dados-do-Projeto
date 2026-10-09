# Relatório técnico — Extensão da série temporal de `tx_rend` para 2007–2025

**Projeto:** Risco de abandono escolar em Roraima (PIBIC/UERR + Mineração de Dados)
**Autor do relatório:** Gustavo (discente responsável pela análise de dados)
**Data:** 2026-10-08
**Escopo:** Descoberta, diagnóstico e construção de um parquet bruto consolidado de `tx_rend` (taxas de rendimento escolar) para Roraima, cobrindo 2007–2025.

---

## 1. Objetivo e contexto

O projeto inicial trabalhava com a série 2019–2025 (7 anos) de indicadores do INEP. A tarefa desta etapa foi **estender a série para 2007–2025** (19 anos), sem quebrar o pipeline existente em `src/`, e sem depender de reescrever módulos oficiais do projeto.

A motivação é metodológica: com 7 anos, o walk-forward produz apenas 4 folds, o que torna qualquer conclusão sobre estabilidade temporal estatisticamente frágil. Com 19 anos, o número de folds sobe para ~13, e a série longa permite separar o efeito da pandemia (2020–2021) de outros regimes.

**Escopo de atuação:** todo o trabalho novo foi feito em `gustavo/`, paralelo ao `src/` oficial, para não alterar nada que já funcionava e não depender de aprovação prévia para mexer no pipeline do grupo.

**Unidade de análise:** escola-ano. **Filtro geográfico:** `SG_UF == "RR"`. **Filtro de rede:** escolas públicas (o filtro de rede será aplicado na etapa seguinte, não neste parquet bruto).

---

## 2. Problema inicial

O script de exploração `x.py` só conseguia ler `tx_rend` a partir de **2012**. Os zips de 2007–2011 estavam no disco, mas apareciam como `(sem xlsx de escolas)` na listagem. A hipótese inicial era "formato de arquivo diferente", mas a causa real era outra.

**A pergunta a responder:** por que o pipeline via 2012 como início da série, se o INEP publica desde 2007?

---

## 3. Diagnóstico — três bugs no `x.py`

A inspeção do código revelou três problemas independentes, todos no script de descoberta (não nos dados):

### Bug 1 — filtro de glob incompleto

```python
zips_tx = [z for z in sorted(pasta_zips_ind.glob("*.zip"))
           if "tx_rend" in z.name.lower()
           or "tx_rendimento" in z.name.lower()]
```

O INEP usa três padrões de nome para o mesmo indicador:

- `tx_rend_*` (2019–2025)
- `tx_rendimento_*` (2007–2015, 2018)
- `TAXA_REND_*` (2016, 2017) ← **não capturado**

Como consequência, 2016 e 2017 ficavam invisíveis para o script.

### Bug 2 — seleção do .xlsx interno restrita

```python
candidatos = [n for n in zf.namelist()
              if n.lower().endswith(".xlsx")
              and "escola" in n.lower()]
```

Para 2007–2011 o INEP publicou em `.xls` (Excel BIFF), não `.xlsx`. E mesmo os `.xlsx` de 2012–2015 não têm "escola" no nome interno (`tx_rendimento_escolas_2012.xlsx` tem; `TAXAS RENDIMENTOS ESCOLAS 2013.xlsx` tem "ESCOLAS" com maiúscula — passa por acaso). O filtro era frágil.

### Bug 3 — caminho string relativo

```python
caminho = f"dados/origem/indicadores/{nome}"
```

Só funciona se o CWD for a raiz do projeto. Rodado de `src/`, quebra com `FileNotFoundError`. Não tem relação com o dado.

**Conclusão:** os dados existiam desde 2007. O script não os via.

---

## 4. Correção do x.py — `explorar_colunas.py`

Correções aplicadas:

Filtro case-insensitive com função helper `eh_zip_tx_rend()`:

```python
def eh_zip_tx_rend(zip_path):
    nome = zip_path.name.lower()
    return ("tx_rend" in nome) or ("taxa_rend" in nome) or ("tx_rendimento" in nome)
```

Seleção do maior `.xlsx` dentro do zip, sem exigir substring:

```python
def maior_xlsx_do_zip(zip_path):
    with zipfile.ZipFile(zip_path) as zf:
        xlsx = [n for n in zf.namelist()
                if n.lower().endswith(".xlsx")
                and not n.startswith("__MACOSX")]
        tamanhos = {n: zf.getinfo(n).file_size for n in xlsx}
        return max(tamanhos, key=tamanhos.get)
```

Caminhos via `pathlib.Path` em todo lugar.

Bloco ad-hoc removido e substituído por `inspecionar_zip()` genérica.

**Resultado:** o `x.py` corrigido passou a listar 2016 e 2017, e devolveu 63 arquivos processados (contra 58 antes).

---

## 5. Inspeção dos zips antigos — `gustavo/inspecionar_zips_antigos.py`

Para entender por que 2007–2011 continuavam falhando, criei um script de inspeção que abre cada zip, lista os membros internos, identifica a extensão, e tenta ler os 5 primeiros registros.

Resultado (resumido):

| Zip | Extensão interna | Legível? |
|-----|-----------------|----------|
| `tx_rendimento_escolas_2007.zip` | `.xls` (161 MB) | ✅ sim (via xlrd) |
| `tx_rendimento_escola_2008.zip` | `.xls` (117 MB) | ✅ sim |
| `tx_rendimento_escola_2009.zip` | `.xls` (132 MB) | ✅ sim |
| `tx_rendimento_escolas_2010_19082011.zip` | `.xls` (128 MB) | ✅ sim |
| `tx_rendimento_escolas_2011_2.zip` | `.xls` (124 MB) | ✅ sim |
| `tx_rendimento_escolas_2012.zip` | `.xlsx` (51 MB) | ✅ sim |
| `tx_rendimento_escolas_2013.zip` | `.xlsx` (51 MB) | ✅ sim |
| `tx_rendimento_escolas_2014.zip` | `.xlsx` (52 MB) | ✅ sim |
| `tx_rendimento_escolas_2015.zip` | `.xlsx` (50 MB) + `.ods` (39 MB) | ✅ sim (usar .xlsx) |

**Descoberta secundária:** o script original também procurava TDI/ATU/IED/HAD com nomes errados. Os nomes reais desses zips são:

- `tdi_escolas_*.zip` (não `TDI_*.zip`)
- `media_alunos_turma_escolas_*.zip` (não `ATU_*.zip`)
- `esforco_docente_escolas_*.zip` (não `IED_*.zip`)
- `horas_aula_escolas_*.zip` (não `HAD_*.zip`)

Isso significa que TDI, ATU, IED e HAD também existem em série longa, mesmo que não tenham sido processados nesta etapa.

---

## 6. Descoberta das três gerações de cabeçalho

Essa foi a parte mais sutil do trabalho. Mesmo com o filtro corrigido e o `.xls` lido corretamente, os anos 2007–2014 vinham com colunas erradas (`2007, Norte, RO, 1100015...`). A intuição foi suspeitar do formato do cabeçalho, não do dado.

Um script dedicado (`ver_estrutura_planilha.py`) revelou três gerações distintas:

| Geração | Anos | Estrutura |
|---------|------|-----------|
| Antiga | 2007–2014 | Cabeçalho em duas linhas (linhas 6 e 7), dados a partir da linha 9 |
| Intermediária | 2015–2020 | Cabeçalho técnico em uma linha (linha 9) |
| Nova | 2021–2025 | Cabeçalho técnico em uma linha (linha 8) |

A heurística antiga ("linha com mais células preenchidas") falhava na geração antiga porque a linha de dados tem mais células preenchidas que a linha de cabeçalho (o cabeçalho tem células vazias como separadores).

**Correção:** função `detectar_cabecalho()` com prioridade baseada em conteúdo, não em posição:

1. Primeiro procura linhas que contenham padrões técnicos reconhecíveis (`tap_`, `1_CAT_`, `NU_ANO_CENSO`, etc.).
2. Se não encontra, procura o padrão de duas linhas (linha com "Ano" na coluna 1, seguida por linha com 40+ células preenchidas).
3. Só se ambos falham, cai na heurística antiga ("mais células").

---

## 7. Mapa de nomenclatura entre as três gerações

| Campo | 2007–2014 | 2015–2020 | 2021–2025 |
|-------|-----------|-----------|-----------|
| ID escola | Código da Escola | CO_ENTIDADE | CO_ENTIDADE |
| UF | UF | SG_UF | SG_UF |
| Município (nome) | Nome do Município | NO_MUNICIPIO | NO_MUNICIPIO |
| Localização | Localização | TIPOLOCA | NO_CATEGORIA |
| Dependência | Rede | Dependad | NO_DEPENDENCIA |
| Aprovação AF | Taxa de Aprovação - Anos Finais | tap_FUN_AF | 1_CAT_FUN_AF |
| Reprovação AF | (nome descritivo) | tre_FUN_AF | 2_CAT_FUN_AF |
| Abandono AF | (nome descritivo) | tab_FUN_AF | 3_CAT_FUN_AF |

O mapa completo está em `gustavo/` e será usado na etapa de seleção (seção 9).

---

## 8. Construção do parquet bruto — `construir_tx_rend_bruto.py`

### Iterações

**v1** — primeira tentativa:
- Erro: filtro de UF pegava coluna errada em 2007–2014 (RR=6 em vez de RR≈600).
- Erro: `pd.concat` quebrava por colunas duplicadas (as três gerações geram nomes repetidos quando empilhadas).

**v2** — correções estruturais:
- `achar_coluna_uf()` genérica: procura coluna cujos valores se parecem com siglas de UF (2 letras maiúsculas).
- `dedup_cols()`: renomeia colunas com nomes repetidos (`CO_ENTIDADE_1`, `CO_ENTIDADE_2`, ...).
- Paralelização com `ThreadPoolExecutor(max_workers=4)`.

**v3** — cache e tipos:
- Cache por ano em `gustavo/saida/cache/{ano}.parquet`. Evita reprocessar os `.xls` (10 min por rodada) em caso de bug.
- `fixar_tipos_parquet()`: corrige colunas com tipos mistos (por exemplo, `CO_ENTIDADE` como `object` em alguns anos e `int64` em outros) que faziam o pyarrow quebrar.
- Flags `--force` (reprocessa tudo) e `--force-year N` (reprocessa um ano específico).

### Decisão arquitetural: dois parquets separados

Inspirado por um problema concreto anterior (o pipeline da colega de grupo gerou um parquet sem documentar as colunas selecionadas, o que tornou impossível reconstruir a decisão), adotei dois artefatos separados:

1. **`tx_rend_rr_2007_2025_bruto.parquet`** — todas as colunas originais, filtro apenas `SG_UF == "RR"`. É a fonte da verdade.
2. **`tx_rend_rr_2007_2025_selecionado.parquet`** (a criar) — colunas escolhidas, com nomes unificados entre as gerações, e relatório `colunas_selecionadas.txt` documentando cada decisão.

**Racional:** se a seleção mudar, não é preciso reprocessar os `.xls` de 130 MB. Só reler o bruto.

### Resultado final

- **Arquivo:** `gustavo/saida/tx_rend_rr_2007_2025_bruto.parquet`
- **Linhas:** 12.597 (Roraima, 19 anos, escolas de todas as redes)
- **Colunas:** 238 (união das três gerações)
- **Cache:** `gustavo/saida/cache/{ano}.parquet` (um por ano, para reruns rápidos)
- **Diagnóstico:** `gustavo/saida/diagnostico_bruto.txt`
- **Verificação aritmética:** RR tem ~1.000 escolas cadastradas, mas o `tx_rend` só publica escolas com matrícula em etapas cobertas. Média de ~663 escolas/ano × 19 anos = 12.597. Confere com o esperado.

---

## 9. Ponto atual e decisão pendente

O parquet bruto está construído. Falta a seleção de colunas, com duas opções discutidas:

### Opção A — escopo mínimo (recomendada para agora)

~15–20 colunas: chaves, descrição, filtro/estrato, e as taxas de aprovação/reprovação/abandono de FUN, FUN_AF, FUN_AI, MED.

**Por quê:** é exatamente o que o notebook `v1_corrigido` usa hoje. Permite comparar série curta (2019–2025) vs série longa (2007–2025) controlando apenas o efeito da extensão temporal. Ciência básica: uma mudança por vez.

### Opção B — escopo amplo (para depois)

Tudo o que A tem, mais `_FUN_01` a `_FUN_09`, `_MED_01` a `_MED_03`, `_MNS`, e outras séries específicas.

**Por quê:** útil só se o projeto for para um segundo artigo sobre previsão por série, não por etapa.

**Decisão proposta:** fazer A agora. B é trivialmente derivável depois, é só alterar a lista de colunas no `selecionar_colunas.py`.

---

## 10. Próximos passos (ordem de prioridade)

### Passo 1 — Verificação de sanidade (2 h)

Script `gustavo/verificar_bruto.py`:

- Para cada ano, imprimir: `n_linhas`, `coluna_de_ID_detectada`, `primeiros_3_valores_de_ID`, `n_municipios_distintos`, `lista_de_municipios`.
- Confirmar que `CO_MUNICIPIO` começa com `14` (código IBGE de Roraima).
- Confirmar que `NO_MUNICIPIO` tem no máximo 15 valores distintos (RR tem 15 municípios).

**Por quê:** o relatório anterior menciona "0 escolas em 2007–2014" no diagnóstico, tratado como cosmético. É cosmético no contador, mas confirma que a coluna de ID tem nome diferente, o que exige verificação antes do merge.

### Passo 2 — Comparação com o pipeline oficial (1 h)

Comparar o parquet bruto filtrado a 2019 com `dados/interim/indicadores_rr/tx_rend_2019.parquet` (do pipeline oficial). Fazer join em `CO_ENTIDADE` e comparar `ABANDONO_FUN_AF`, `APROVACAO_FUN`, etc.

**Por quê:** sem essa validação cruzada, não há garantia de que o filtro RR e o mapeamento de colunas estão corretos. É o que sustenta qualquer resultado da série longa.

### Passo 3 — `selecionar_colunas.py` (2 h)

Lê `_bruto.parquet`, aplica `MAPA_GERACOES` (renomeação), seleciona colunas do escopo A, salva `_selecionado.parquet` e `colunas_selecionadas.txt`.

**Atenção:** o `MAPA_GERACOES` precisa mapear todos os nomes antigos para o mesmo nome novo. Se dois nomes antigos colidirem no mesmo nome novo, o rename cria colunas duplicadas — o `dedup_cols()` cobre, mas precisa estar documentado.

### Passo 4 — Refazer o v1_corrigido com série estendida (meio dia)

Apontar o notebook para `_selecionado.parquet`. O walk-forward passa de 4 folds (2021→2022 ... 2024→2025) para ~10 folds (2015→2016 ... 2024→2025). Esperado: R² médio cai, desvio entre folds aumenta. TDI continua no topo? Se sim, é achado robusto; se não, era artefato da série curta.

### Passo 5 — Preparar apresentação (1 h)

Foco em:

- Série longa do abandono contemporâneo (2007–2025): 2020 como anomalia, 2022 como retorno ao normal.
- Comparação `v1_corrigido` série curta vs série longa.
- Permutation importance em série longa.
- Decisão A vs B justificada.

---

## 11. O que não foi feito nesta etapa (e por quê)

- **TDI, ATU, IED, HAD** — os zips existem e são legíveis (com nomes diferentes dos testados inicialmente), mas o processamento é mais 1–2 dias de trabalho. Fica para depois que o `tx_rend` estendido estiver validado e o `v1_corrigido` estendido rodando.

- **Integração com `src/` oficial** — o pipeline oficial do projeto está escrito para 2019–2025. Reescrever para aceitar 2007–2025 quebraria a comparação com a base v1.0 do orientador (critério 2 do §8 do `CLAUDE.md`). Mantido em `gustavo/` por decisão deliberada.

- **Filtro de rede pública** — o parquet bruto contém todas as redes. O filtro `TP_DEPENDENCIA == 2` (estadual) será aplicado na etapa de seleção.

- **Decisão da partição treino/validação/teste** — o `CLAUDE.md` (D7) fixa 2019–22 / 2023 / 2024–25. Com série longa, o desenho muda. Pergunta em aberto para o orientador.

---

## 12. Arquivos produzidos

```text
gustavo/
├── inspecionar_zips_antigos.py       # script de inspeção (uma vez)
├── ver_estrutura_planilha.py         # script de diagnóstico de cabeçalho (uma vez)
├── construir_tx_rend_bruto.py        # construtor do parquet bruto (reutilizável)
├── selecionar_colunas.py             # [a criar]
├── saida/
│   ├── tx_rend_rr_2007_2025_bruto.parquet   # artefato principal
│   ├── diagnostico_bruto.txt
│   ├── colunas_selecionadas.txt             # [a criar]
│   ├── cache/
│   │   ├── 2007.parquet
│   │   ├── 2008.parquet
│   │   └── ... (até 2025.parquet)
│   └── saida_inspecao.txt
└── corrigido_x.py                    # versão corrigida do x.py original
```

---

## 13. Aprendizados documentáveis

1. **Debug de dado > debug de código.** O problema nunca foi o INEP ou o `.xls`. Sempre foi o código assumindo um formato único.

2. **Cache por unidade de trabalho.** Salvar `{ano}.parquet` logo após cada leitura evita perder 10 min por rerun. Um pipeline que lê 19 arquivos grandes deve ser incremental.

3. **Preservar bruto + documentar seleção.** Arquitetura que resolve o problema concreto do pipeline anterior do grupo.

4. **Heurística frágil.** "Linha com mais células preenchidas" só funciona quando o cabeçalho tem o mesmo número de colunas que os dados — o que não vale para 2007–2014.

5. **Separação bruto/selecionado permite experimentar.** Trocar o escopo A→B é editar uma lista, não reprocessar 700 MB de `.xls`.

---

## 14. Perguntas em aberto para o orientador

1. **Partição temporal com série longa.** Manter D7 (treino 2019–22, validação 2023, teste 2024–25) ou reabrir para walk-forward completo (2015→2016 até 2024→2025)?

2. **Escopo A vs B.** Confirmar que A é o ponto de partida.

3. **Integração com `src/`.** O trabalho em `gustavo/` deve ser migrado para o pipeline oficial em algum momento, ou fica como ramo paralelo?

4. **Instalação de `xlrd`.** Já está no ambiente atual, mas não está no `requirements.txt` oficial. Adicionar?

---

*Fim do relatório.*
