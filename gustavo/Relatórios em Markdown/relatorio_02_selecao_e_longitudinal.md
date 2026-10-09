# Relatório técnico 02 — Harmonização e estruturação temporal de `tx_rend` (2007–2025)

**Projeto:** Risco de abandono escolar em Roraima (PIBIC/UERR + Mineração de Dados)
**Autor:** Gustavo (discente responsável pela análise de dados)
**Data:** 2026-10-08 (segunda parte do dia)
**Escopo:** transformar o parquet bruto validado no relatório 01 em base utilizável para modelo preditivo.
**Documento anterior:** `relatorio_01_diagnostico_e_bruto.md`

---

## 0. Sumário executivo

Depois do bruto validado (relatório 01), a etapa desta tarde produziu a base pronta para uso:

- `tx_rend_rr_2007_2025_selecionado.parquet` — 12.597 linhas × 19 colunas, 12 taxas com nomes unificados
- `tx_rend_rr_2007_2025_longitudinal.parquet` — 12.597 × 30, com `_LAG1`, `_DELTA1` e `_T1`

Todas as validações passaram. Contra a base da Gabi (2019–2025), as 12 taxas, `DISP_REND`, `REDE_PUBLICA` e os três `_T1` são idênticos.

**Três correções importantes ao relatório 01:**

1. O mapeamento por posição fixa (sugerido no relatório 01, seção 9) **está errado**. A posição das colunas muda entre gerações.
2. A base da Gabi usa **12 taxas**, não 54. O escopo de seleção do relatório 01 estava superdimensionado.
3. A validação 54/54 do relatório 01 **não provou** o mapeamento entre gerações. Provou só que a leitura é fiel em 2019–2025.

**Duas descobertas que afetam o projeto maior:**

1. A base da Gabi tem bug no cálculo de `REDE_PUBLICA`: escolas particulares de 2007–11, 2014 e 2015 estão marcadas como públicas.
2. O Fundamental brasileiro mudou de 8 para 9 anos em 2010. Isso afeta comparabilidade de 2007–2010 com 2011+.

---

## 1. Objetivo desta etapa

O bruto do relatório 01 tem 238 colunas porque é a **união** das três gerações de layout do INEP (2007–2014, 2015–2020, 2021–2025). Cada ano preenche só ~63 colunas; as outras ~175 ficam vazias naquele ano.

O objetivo foi produzir uma base **utilizável por modelo preditivo**: nomes unificados, tipagem correta, `'--'` convertido para ausente, e estrutura temporal (`_LAG1`, `_DELTA1`, `_T1`).

---

## 2. Correções ao relatório 01

### 2.1 O mapeamento por posição fixa está errado

O relatório 01 (seção 9) sugeriu um mapa do tipo:

| posicao | 2007–2014 | 2015–2020 | 2021–2025 | unificado |
|---------|-----------|-----------|-----------|-----------|
| 10 | Taxa de Aprovação - Anos Finais | tap_F04 | 1_CAT_FUN_AF | APROVACAO_FUN_AF |

**Isso não funciona.** A posição da mesma taxa muda entre gerações:

- **2007–2010:** totais ficam no **fim** de cada grupo de séries, não no começo.
- **2015–2017:** `tap_F58` = Anos Finais.
- **2018–2020:** `tap_F04` = Anos Finais; `tap_F58` = 1º ano.

Ou seja, `tap_F58` **muda de significado** entre 2015–17 e 2018–20. Se o mapa fosse fixo por posição, o modelo treinaria com dados trocados de 2018–2020 e o erro seria silencioso.

**Solução aplicada:** o `construir_tx_rend_longitudinal.py` lê o **cabeçalho humano** de cada ano (o rótulo da linha 6/7 nas gerações antigas, a descrição em `docs/presenca_colunas_indicadores.csv` nas novas) para descobrir qual coluna é qual. Se o cabeçalho esperado não bater, **o script para com erro**.

### 2.2 A base da Gabi usa 12 taxas, não 54

O relatório 01 propôs um mapa de 54 colunas. Na prática, a base do orientador usa 12 taxas:

- Aprovação, Reprovação, Abandono × 4 etapas = 12.
- As etapas são: Fundamental total, Anos Iniciais, Anos Finais, Médio.

As outras 42 colunas (séries individuais `_01` a `_09`, `_MNS`, `_F14`, `_F58`) **não entram no modelo atual**. Elas existem no bruto, mas não na base usada para treinar.

**Consequência prática:** o escopo de seleção (Opção A do relatório 01) já estava correto em espírito, mas o número real de taxas era 12, não 15–20.

### 2.3 A validação 54/54 não provou o mapeamento

O relatório 01 (seção 10, Passo 2) descreveu a validação contra o pipeline oficial como prova de que o mapeamento estava correto. Não é.

A validação comparou **colunas de mesmo nome** entre o bruto e o oficial. Se o script tivesse trocado `tap_FUN_AF` por `tap_FUN_AI` no código, a comparação **ainda bateria** — porque o oficial tem ambas as colunas e a comparação seria feita coluna por coluna, sem detectar a troca.

**O que a validação 54/54 realmente provou:** que a leitura das planilhas é fiel ao que o INEP publicou, para 2019–2025. Não provou tradução entre gerações, e não disse nada sobre 2007–2018.

**Correção aplicada:** além da validação por nome, o script verifica que cada total fica entre o mínimo e o máximo das séries que o compõem. Isso pega trocas de coluna que a validação por nome não pegaria.

---

## 3. O que o `construir_tx_rend_longitudinal.py` faz

### 3.1 Fonte de dados

Lê os arquivos em `gustavo/saida/cache/{ano}.parquet`, não o bruto direto. Motivo: o bruto empilha as gerações **pelo nome da coluna**, e isso perde a ordem original das colunas na planilha. Como o mapeamento é por posição e rótulo humano, a ordem importa — e o cache preserva.

### 3.2 Etapas do script

1. **Confere o cabeçalho esperado** para cada uma das 12 taxas em cada ano. Se o cabeçalho humano não bater com o esperado, o script para.
2. **Verifica consistência série→total:** cada total deve estar entre o mínimo e o máximo das séries que o compõem. Isso detecta troca de coluna que o cabeçalho sozinho não pegaria.
3. **Gera dois arquivos:**
   - `_selecionado.parquet`: 12.597 × 19, com nomes unificados e `'--'` convertido em ausente.
   - `_longitudinal.parquet`: 12.597 × 30, com `_LAG1` (ano anterior), `_DELTA1` (variação anual) e `_T1` (ano seguinte).
4. **Ligações temporais por ano exato:** se a escola falta em `t−1` ou `t+1`, fica ausente. Sem pular anos.

### 3.3 Tratamento de dependência administrativa

O script junta "Particular" e "Privada" numa única categoria `Privada`. Motivo: entre 2007–11, 2014 e 2015 o INEP grafou a rede como "Particular"; nos outros anos, como "Privada". Se não unificasse, `REDE_PUBLICA` sairia errado.

---

## 4. Validações que passaram

Todas as travas do script passaram:

| Validação | Escopo | Resultado |
|-----------|--------|-----------|
| Cabeçalho de cada posição, cada ano, cada taxa | 19 × 12 | ✅ |
| Consistência série→total (mín/máx) | 19 × 4 etapas | ✅ |
| Chave composta `ANO+CO_ENTIDADE` única | 12.597 linhas | ✅ |
| Linhas por ano iguais ao bruto | 19 anos | ✅ |
| Aprovação + Reprovação + Abandono ≈ 100 ± 0,2 | 19 × 4 | ✅ |
| 12 taxas, `DISP_REND`, `REDE_PUBLICA`, `_T1` vs base Gabi (2019–2025) | 4.733 linhas | ✅ idênticos |
| `_LAG1` e `_DELTA1` vs base Gabi (2020+) | — | ✅ idênticos |

---

## 5. Diferenças contra a base da Gabi (esperadas, não são erros)

**LAG1 e DELTA1 divergem em 2019.** Na base da Gabi, 2019 não tinha `_LAG1` porque o pipeline começava em 2019. Com a série estendida, 2019 tem `_LAG1` vindo de 2018. Isso **aumenta o treino em ~650 linhas** e é uma mudança no desenho.

**ANO_ALVO difere em 25 linhas.** A base da Gabi inclui escolas que só existem em TDI/ATU (outros indicadores). A nova base só tem escolas de `tx_rend`. O alvo (`_T1`) é idêntico nas escolas comuns.

**Soma das taxas em 100 ± 0,2** — pode haver divergência de 0,2 p.p. por arredondamento do INEP. É esperado e tolerado.

---

## 6. Bug descoberto na base da Gabi: `REDE_PUBLICA`

O INEP usa **dois rótulos** para a mesma rede em `tx_rend`:

- "Privada" — na maioria dos anos
- "Particular" — em 2007–11, 2014 e 2015

A base da Gabi calcula `REDE_PUBLICA` presumindo que a coluna de dependência é homogênea. Resultado: **escolas particulares de 2007–11, 2014 e 2015 foram marcadas como públicas**.

**Impacto:** o `v1_corrigido` filtra `REDE_PUBLICA == 1`. Isso significa que escolas particulares desses anos entraram no treino, contaminando o universo (que deveria ser só escolas públicas).

**Correção aplicada:** o novo script unifica "Particular" e "Privada" na categoria `Privada` antes de calcular `REDE_PUBLICA`.

**Ação recomendada:** avisar a colega de grupo. Esse bug afeta o `v1_corrigido` original e qualquer análise feita com a base dela. Vale rodar de novo depois de corrigido.

---

## 7. Limitação importante: Fundamental 8 vs 9 anos

Antes de 2011, o Ensino Fundamental brasileiro era de 8 anos (1ª a 8ª série). A partir de 2011, passou a 9 anos (1º ao 9º ano), conforme a Lei 11.274/2006.

O mapeamento do script trata "5ª a 8ª série" como Anos Finais e "1ª a 4ª série" como Anos Iniciais, o que é conceitualmente correto. **Mas a composição etária das turmas mudou.** Em 2009, quem cursava 5ª série tinha idade equivalente a quem hoje cursa 6º ano. Escolas diferentes implementaram a transição em anos diferentes (entre 2006 e 2010).

**Consequência:** resultados do modelo em 2007–2010 podem ser sistematicamente diferentes dos de 2011+. Não invalida o dado, mas justifica:

- Nota de limitação em qualquer publicação.
- Recomendação de análise de sensibilidade treinando sem 2007–2010.

---

## 8. Escopo desta base: só `tx_rend`

Esta base **não inclui** TDI, ATU, IED, HAD. Os zips existem e são legíveis (relatório 01, seção 5), mas o processamento é trabalho separado.

**Consequência:** o `v1_corrigido` original usa essas variáveis. Se for rodado com a nova base **sem adaptação**, ele quebra por falta de colunas.

**Duas opções para o professor decidir:**

1. Adaptar o `v1_corrigido` para rodar só com `tx_rend` (12 features em vez de ~31). Muda o desenho, mas é defensável como "modelo mínimo usando só o alvo".
2. Estender a base com TDI/ATU/IED antes de rodar. Mais trabalho (~1–2 dias), mas reproduz o desenho original.

---

## 9. O que ainda falta para o modelo rodar

Se a decisão for rodar com só `tx_rend`:

- ~~Harmonizar colunas~~ (feito)
- ~~Tipagem da regra 6 do CLAUDE.md~~ (feito)
- ~~Converter `'--'` para ausente~~ (feito)
- ~~Estrutura `_LAG1`, `_DELTA1`, `_T1`~~ (feito)
- Adaptar o `v1_corrigido` para ler `_longitudinal.parquet` (2–3 h)

Se a decisão for incluir TDI/ATU/IED:

- Tudo acima, mais:
- Processar TDI 2007–2025 (2–4 h)
- Processar ATU 2007–2025 (2–4 h)
- Processar IED 2013–2025 (2–4 h) — não existe antes de 2013
- (opcional) Processar HAD 2011–2025

---

## 10. Arquivos produzidos
gustavo/
   ├── construir_tx_rend_bruto.py # relatório 01
   ├── construir_tx_rend_longitudinal.py # esta etapa
   ├── inspecionar_zips_antigos.py # relatório 01
   ├── ver_estrutura_planilha.py # relatório 01
   ├── validar_bruto_vs_oficial.py # relatório 01
   └── saida/
   ├── tx_rend_rr_2007_2025_bruto.parquet # relatório 01 (12.597 × 238)
   ├── tx_rend_rr_2007_2025_selecionado.parquet # esta etapa (12.597 × 19)
   ├── tx_rend_rr_2007_2025_longitudinal.parquet # esta etapa (12.597 × 30)
   ├── validacao_bruto.txt # relatório 01
   ├── validacao_longitudinal.txt # esta etapa
   ├── diagnostico_bruto.txt # relatório 01
   └── cache/{ano}.parquet # um por ano

---

## 11. Perguntas em aberto para o orientador

1. **Escopo do primeiro modelo:** rodar só com `tx_rend`, ou estender a base com TDI/ATU/IED antes?
2. **Partição temporal com série longa:** manter D7 (treino 2019–22, validação 2023, teste 2024–25) ou reabrir para walk-forward completo (2015→2016 até 2024→2025)?
3. **Uso de 2007–2010:** incluir no treino, ou tratar como período com limitação (Fund. 8 anos) e deixar para sensibilidade?
4. **Migração para `src/`:** o pipeline em `gustavo/` deve ser integrado ao oficial, ou fica paralelo?
5. **Instalação de `xlrd`:** está no ambiente atual, mas não no `requirements.txt` oficial. Adicionar?
6. **Bug do `REDE_PUBLICA` na base da Gabi:** como ela prefere proceder?

---

## 12. Recomendação

**Parar por aqui.** A base está pronta. As descobertas desta tarde (bug da Gabi, limitação do Fundamental, correções ao relatório 01) precisam ser levadas ao professor antes de continuar.

**Próximo passo:** apresentar os dois parquets (selecionado e longitudinal) + `validacao_longitudinal.txt` ao professor, com as 6 perguntas acima. Decidir o escopo do modelo a partir daí.

---

*Fim do relatório 02.*