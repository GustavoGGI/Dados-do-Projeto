# Relatório técnico 03 — Reorganização do pipeline e consolidação da base estendida

**Projeto:** Risco de abandono escolar em Roraima (PIBIC/UERR + Mineração de Dados)
**Autor:** Gustavo (discente responsável pela análise de dados)
**Data:** 2026-10-09
**Escopo:** reorganização completa da pasta `gustavo/` em pipeline sequencial, correção dos pontos deixados em aberto nos relatórios 01 e 02, e consolidação final da base pronta para o modelo.
**Documentos anteriores:** `relatorio_01_diagnostico_e_bruto.md`, `relatorio_02_selecao_e_longitudinal.md`

---

## 0. Sumário executivo

Os relatórios 01 e 02 deixaram a base estendida **funcionalmente pronta**, mas com dois problemas estruturais: a pasta `gustavo/` estava desorganizada (scripts e parquets misturados, caches dentro de `saida/`, nomes que sugeriam "versão final" quando eram só mais uma etapa) e as correções apontadas no relatório 02 ainda não tinham sido incorporadas.

Esta etapa fechou os dois:

- **Pipeline sequencial** `01 → 02 → 03 → 04` com `99_pipeline.py` para reexecução completa.
- **Parquets numerados** em `saida/etapas/` refletindo a ordem de construção.
- **Cache fora de `saida/`** (é técnico, não é produto).
- **29 checks automatizados** rodando com 0 falhas.
- **Base final consolidada**: `saida/base_atual.parquet` — 12.597 × 47 (30 do tx_rend longitudinal + 17 features do Censo, chaves compartilhadas).

Com isso, o pipeline está pronto para consumo pelo modelo. A única decisão em aberto é o **escopo do primeiro modelo** (só `tx_rend` vs `tx_rend + Censo` vs incluir TDI/ATU/IED antes).

---

## 1. Motivação da reorganização

Após os relatórios 01 e 02, a pasta `gustavo/` tinha:

- Scripts na raiz misturados com scripts de diagnóstico
- Parquets em `saida/` sem hierarquia
- Dois caches dentro de `saida/` (`saida/cache/` e `saida/cache_censo/`)
- Nomes como `base_completa.parquet` que sugeriam "versão final", quando era apenas mais uma etapa intermediária
- Testes e programas no mesmo nível
- Relatórios em markdown numa pasta chamada `Relatórios em Markdown/` (espaços, maiúsculas, acento)

Isso não impedia o funcionamento, mas **impedia a reprodução e a auditoria** por terceiros (orientador, colega de grupo, banca). A base funciona, mas quem chega depois não consegue navegar.

A decisão foi: **refazer a estrutura antes de avançar para o modelo**. Reorganizar custa 1 dia; refazer modelo contaminado por falta de rastreabilidade custa semanas.

---

## 2. Arquitetura final

```
gustavo/
├── README.md                       ← guia geral do projeto
├── COMO_RODAR.md                   ← ordem de execução + flags
│
├── programas/
│   ├── 01_tx_rend_bruto.py
│   ├── 02_tx_rend_selecionado_longitudinal.py
│   ├── 03_censo_features.py
│   ├── 04_merge_features.py
│   ├── 99_pipeline.py              ← roda 01→04 em ordem
│   └── diagnostico/                ← scripts pontuais (não entram no pipeline)
│       ├── explorar_colunas_censo.py
│       └── inspecionar_zips_antigos.py
│
├── testes/
│   └── 01_validar_base.py          ← 29 checks
│
├── docs/                           ← relatórios narrativos em markdown
│   ├── relatorio_01_diagnostico_e_bruto.md
│   ├── relatorio_02_selecao_e_longitudinal.md
│   └── relatorio_03_reorganizacao.md (este documento)
│
├── cache/                          ← técnico, apagável, fora de saida/
│   ├── tx_rend/{ano}.parquet       (19 arquivos)
│   └── censo/{ano}.parquet         (19 arquivos)
│
└── saida/
    ├── README.md                   ← descrição de cada parquet
    ├── etapas/
    │   ├── 01_tx_rend_bruto.parquet                 (12.597 × 238)
    │   ├── 02a_tx_rend_selecionado.parquet          (12.597 × 19)
    │   ├── 02b_tx_rend_longitudinal.parquet         (12.597 × 30)
    │   ├── 03_censo_features.parquet                (16.449 × 19)
    │   └── 04_base_com_censo.parquet                (12.597 × 47)
    ├── relatorios/
    │   ├── diagnostico_bruto.txt
    │   ├── validacao_longitudinal.txt
    │   ├── diagnostico_features_censo.txt
    │   ├── merge_features.txt
    │   └── validacao_base.txt
    └── base_atual.parquet         ← cópia do 04 (consumido pelo modelo)
```

**Princípio organizador:** a ordem numérica reflete a ordem de execução. `01_*` só depende dos zips do INEP; `02_*` depende do `01`; `03_*` só depende dos zips do Censo; `04_*` depende de `02` e `03`. Nenhum ciclo, ordem topológica trivial.

---

## 3. Decisões de design

### 3.1 Quatro scripts de produção, não cinco

O relatório 02 já tinha decidido que a lógica `P009/P014` (armadilha de nomes técnicos trocados em 2019–2020) precisa ler o cache anual e travar contra o rótulo humano do cabeçalho. Isso é uma **única operação** — separar em dois scripts exigiria duplicar a lógica ou gravar parquet intermediário que perderia a informação de posição.

Mantido como um script (`02_*`) que gera **dois produtos**: `02a` (base limpa) e `02b` (base com `LAG1`/`DELTA1`/`T1`). Nomes com sufixo a/b refletem que saem do mesmo script, evitando a confusão de "um script, dois produtos" sem hierarquia visível.

### 3.2 Cache fora de `saida/`

Cache é **otimização técnica**, não produto. Apagar `cache/` e rodar de novo deve reconstruir tudo (em ~10 min, porque reprocessa os zips). Produto em `saida/` deve ser algo que você levaria para uma banca. Isso motivou a separação.

### 3.3 `base_atual.parquet` na raiz de `saida/`

É o arquivo que o notebook de modelo vai consumir. Para testar com uma etapa diferente (só `tx_rend`, por exemplo), basta copiar `etapas/02b_...` por cima de `base_atual.parquet`. Sem editar notebook, sem mudar código.

### 3.4 Nomes descritivos sem "final" ou "completa"

`base_completa.parquet` (nome antigo) sugeria versão final. Mas quando TDI/ATU/IED forem adicionados, ela deixa de ser completa. O nome novo é `04_base_com_censo.parquet` — descreve o que tem (`base com censo`), e o prefixo `04_` mostra em que ponto da cadeia ela está.

### 3.5 `docs/` separado de `saida/relatorios/`

- `docs/` — narrativa em markdown, escrita à mão, não regenerável. É o "diário de bordo" do trabalho.
- `saida/relatorios/` — saída de script, `.txt`, regenerável.

Separação porque são coisas diferentes: uma é o "porquê", a outra é "o que rodou".

---

## 4. O que cada script faz

| Script | Lê de | Escreve em | Tempo (cache quente) |
|---|---|---|---|
| `01_tx_rend_bruto.py` | zips INEP (`dados/origem/indicadores/`) | `etapas/01_...parquet` (238 col) + `cache/tx_rend/` | 2,3 s |
| `02_tx_rend_selecionado_longitudinal.py` | `cache/tx_rend/` + `01` | `etapas/02a_*.parquet` (19 col) + `etapas/02b_*.parquet` (30 col) | 3,2 s |
| `03_censo_features.py` | zips Censo (`dados/bruto/censo/`, `dados/origem/censo/`) | `etapas/03_...parquet` (19 col) + `cache/censo/` | 1,3 s |
| `04_merge_features.py` | `02b` + `03` | `etapas/04_...parquet` + `base_atual.parquet` | 1,1 s |
| `99_pipeline.py` | — | chama os 4 em ordem | 7,9 s total |

Do zero (com cache apagado): ~10 min, dominado pela leitura dos `.xls` de 130 MB em 01 e dos CSVs grandes em 03.

---

## 5. Correções aplicadas neste dia

### 5.1 README de `saida/`

Três pontos estavam desatualizados em relação ao estado real:

1. `04_base_com_censo.parquet` dizia **36 colunas** — o correto é **47** (30 do longitudinal + 17 do Censo).
2. Mencionava `validacao_bruto.txt` como se estivesse em `saida/relatorios/` — esse arquivo **não existe mais** (era do script antigo `validar_bruto_vs_oficial.py`, removido na reorganização).
3. Mencionava `relatorio_colunas_censo.csv` como se estivesse em `saida/relatorios/` — na verdade ele fica na raiz de `saida/`.

Adicionadas duas seções que faltavam:

- **"Por que 02 gera dois parquets"** — explica a lógica `P009/P014` e por que não separar em dois scripts.
- **"Sobre `base_atual.parquet`"** — de onde vem, quando é atualizado, como trocar.

### 5.2 `COMO_RODAR.md`

Adicionada seção **"Etapas 02 e 04 (não aceitam flag)"** com o motivo de cada uma:

- `02` só trabalha em cima do cache (que já é o produto final do `01`). Regenerar é sempre barato (~3 s).
- `04` só faz merge; não tem cache próprio. Se `02b` ou `03` estiverem desatualizados, o `04` reflete isso.

Também documentado `--force-year` (do `01`) e `--from` (do `99_pipeline.py`).

### 5.3 `README.md` raiz

Reescrito por completo. O antigo listava nomes de parquets que não existem mais (`tx_rend_rr_2007_2025_bruto.parquet` etc.), dizia `base_atual.parquet` com 36 colunas, e mencionava **33 checks** quando o teste atual roda **29**.

O novo reflete:

- Estrutura real (com `cache/` fora de `saida/`).
- Tabela do pipeline em 4 etapas com dependências.
- Estado atual (12.597 × 47, 29 checks, 0 falhas).
- Validação contra a base da Gabi (4.733 linhas em comum, zero diferenças).
- Pendências (2007 com 4 features vazias; out of memory em 2010; TDI/ATU/IED).

---

## 6. Validações que passaram

`testes/01_validar_base.py` roda **29 checks** em 13 seções:

| Seção | O que verifica | Resultado |
|---|---|---|
| 0. Carregamento | Shapes de 02a, 02b, 03, 04, base_atual | ✅ |
| 1. Tipagem | `CO_ENTIDADE`/`CO_MUNICIPIO` string, `ANO` int16, taxas Float64 nullable | ✅ |
| 2. Chave | `(ANO, CO_ENTIDADE)` única em todos os parquets | ✅ |
| 3. `'--'` residual | Nenhum `'--'` nas taxas | ✅ |
| 4. Cobertura | Linhas == escolas únicas; 19 anos | ✅ |
| 5. Taxas em [0,100] | Todas as 12 taxas | ✅ |
| 6. Curva temporal | 2020 < 2019; 2022 > 2021 | ✅ |
| 7. LAG1 coerente | 4.326 linhas conferem | ✅ |
| 8. DELTA1 coerente | 4.240 linhas conferem | ✅ |
| 9. T1 coerente | 4.349 linhas conferem | ✅ |
| 10. ANO_ALVO | 687 sem alvo (último ano); 452 confirmadas ausentes em t+1 | ✅ |
| 11. Censo binário | 17 features, só 0/1 | ✅ |
| 12. Cobertura do Censo | 18/19 anos > 99% (só 2007 em 76,5%) | ✅ |
| 13. base_atual = 04 | Idênticos | ✅ |

**Resumo:** 29 OK, 0 warnings, 0 falhas.

### 6.1 Comparação contra a base da Gabi (2019–2025)

- 4.733 linhas em comum
- Zero diferenças de valor em todas as colunas comparadas
- Zero divergência de ausência, exceto `ANO_ALVO` em 25 linhas — esperado, universos diferentes (a base da Gabi tem 1.321 escolas a mais por incluir escolas que não reportam rendimento)

Essa comparação já tinha sido feita no relatório 02 e continua válida. Serve como **validação cruzada**: se algo tivesse quebrado na reorganização, apareceria aqui.

---

## 7. Pendências e limitações

### 7.1 Documentadas (não bloqueiam)

- **2007 tem 4 features do Censo 100% vazias** — `IDA_despensa`, `IDA_secretaria`, `IDA_refeitorio`, `IDP_patio_coberto`. É lacuna real do INEP (colunas existem no schema, mas não foram coletadas em 2007 no Brasil inteiro). Decisão: manter 2007, decidir depois se remove do treino ou trata como limitação de período.
- **`out of memory` em 2010 quando o cache é apagado** — não diagnosticado. Rodou na segunda tentativa porque leu do cache. Se o cache for apagado, o pipeline pode falhar. Investigar antes de reconstruir do zero.
- **TDI, ATU, IED não construídos** — os zips existem e são legíveis (relatório 01, seção 5), mas o processamento é trabalho separado. Decisão do orientador se prioriza antes do modelo.
- **17 vs 18 variáveis do artigo (Almeida & Mussato)** — falta `IDP_patio_descoberto`. O artigo trata "pátio coberto ou descoberto" como uma variável só; temos só o "coberto".

### 7.2 Encontradas nesta etapa, ainda abertas

- **Dois scripts em `programas/diagnostico/` têm caminhos quebrados.** `explorar_colunas_censo.py` e `inspecionar_zips_antigos.py` calculam `saida/` e `dados/` como `Path(__file__).parent.parent`, o que funcionava quando estavam em `programas/`, mas ficou errado quando foram movidos para `programas/diagnostico/` (precisaria de `.parent.parent.parent`). Não afeta o pipeline, mas afeta quem rodar esses scripts avulsos.
- **`02b` valida contra `01` só em contagem de linhas**, não em conjunto de `CO_ENTIDADE`. Se um bug de filtro fizer os dois divergirem em *quais* escolas entram (não em *quantas*), o teste passa. Melhoria possível: comparar os conjuntos por ano.
- **`testes/01_validar_base.py` não valida o `01_tx_rend_bruto.parquet`** diretamente. O `01` fica coberto indiretamente (o `02` compara com ele em contagem), mas não há um check de "o `01` tem 12.597 linhas e `ANO` sem nulos".

Nenhuma dessas pendências bloqueia o modelo. São travas adicionais que valem para a próxima rodada de manutenção.

---

## 8. Comparação de estado

| Métrica | Antes (relatório 02) | Depois (hoje) |
|---|---|---|
| Estrutura de pastas | mista | sequencial e numerada |
| Cache | dentro de `saida/` (2 pastas) | fora, em `cache/` (2 subpastas) |
| Nomes de parquets | descritivos, sem ordem | prefixo numérico = ordem de execução |
| "Base final" | `base_completa.parquet` | `base_atual.parquet` (cópia do `04`) |
| Scripts | 4 na raiz + avulsos | 4 em `programas/` + 99 + diagnóstico |
| Testes | 1 em `testes/` | 1 em `testes/` (29 checks, 0 falhas) |
| Documentação | `diagnostico_bruto.txt` etc. | 3 markdowns em `docs/` + README em `saida/` |
| Reexecução | manual, script por script | `python programas/99_pipeline.py` |
| Tempo do pipeline | ~15 min (estimado) | 7,9 s (cache quente) / ~10 min (do zero) |

---

## 9. Próximo passo proposto — modelo A/B

Com o pipeline estável, o próximo passo é o **modelo A/B** para responder à pergunta científica central:

> As 17 features do Censo (Almeida & Mussato, 2023) melhoram a previsão de abandono escolar em Roraima?

**Configuração:**

| Config | Features |
|---|---|
| A (baseline) | só `tx_rend` (12 taxas + 3 `LAG1` + 2 `DELTA1`) |
| B (enriquecido) | `tx_rend` + 17 features do Censo |

Mesmo walk-forward, mesmos modelos, mesmos folds. Comparar R²/MAE por ano.

**Duas opções de implementação:**

1. `programas/05_modelo.py` — script Python puro, versionável, controlável, não mexe no notebook original.
2. `notebooks/modelo.ipynb` — adapta o `v1_corrigido` da Gabi para ler `base_atual.parquet`, mantém `permutation importance` e análise de erro.

**Sugestão:** opção 1 agora. É mais rápida, mais limpa, mais fácil de explicar ao professor. Se ele pedir o notebook completo, adapta depois.

**Decisões ainda pendentes do orientador:**

1. Modelos a comparar (Ridge, RandomForest, HistGradientBoosting? Só um? Qual conjunto?).
2. Walk-forward: quantos folds? Sugestão — 2022→2023, 2023→2024, 2024→2025 (3 folds, anos recentes, evita treinar com pandemia nos primeiros).
3. Escopo de features do Censo no modelo B: 17 features diretas, ou 4 escores agregados (`IIB`/`IDA`/`IDP`/`IEP`), ou ambos?
4. Ordem: modelo A/B antes ou depois de construir TDI/ATU/IED?

---

## 10. Arquivos relevantes para o professor

- `gustavo/README.md` — visão geral
- `gustavo/COMO_RODAR.md` — pipeline passo a passo
- `gustavo/saida/README.md` — descrição de cada parquet
- `gustavo/saida/relatorios/validacao_base.txt` — prova de que a base está íntegra (29 checks)
- `gustavo/saida/relatorios/validacao_longitudinal.txt` — comparação contra a base da Gabi
- `gustavo/docs/relatorio_01_diagnostico_e_bruto.md` — diagnóstico dos 3 bugs do `x.py`
- `gustavo/docs/relatorio_02_selecao_e_longitudinal.md` — armadilha P009/P014 e correções
- `gustavo/docs/relatorio_03_reorganizacao.md` — este documento

---

## 11. Aprendizados documentáveis

1. **Reorganizar antes de avançar.** O custo de reorganizar depois é proporcional ao tamanho do código. Reorganizar 4 scripts custou 1 dia; reorganizar 8 custaria 3.

2. **Nomes devem descrever, não julgar.** `base_completa.parquet` mente quando outra etapa é adicionada. `04_base_com_censo.parquet` continua verdadeiro independente do que vier depois.

3. **Cache é técnico, produto é narrativo.** Misturar os dois torna impossível "apagar e refazer do zero" — você nunca sabe o que é seguro apagar.

4. **Um README, não três.** Cada arquivo extra de documentação é mais um lugar que vai divergir do estado real. Concentrar num único lugar força a atualização.

5. **Prefixo numérico é contrato.** `01_*` sempre roda primeiro. Qualquer pessoa que chega entende a ordem sem ler nenhuma linha de código.

---

*Fim do relatório 03.*