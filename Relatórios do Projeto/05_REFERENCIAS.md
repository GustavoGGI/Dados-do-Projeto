# 05 — Referências

Anotações dos PDFs originais + bibliografia geral.

---

## 1. Ames Housing (material didático)

### 1.1 O que é

PDF do Prof. Bruno Figueirêdo, setembro/2026. Material didático para
disciplinas de Ciência de Dados. Cobre regressão linear,
regularização (Ridge/Lasso) e Random Forest aplicados à precificação
imobiliária.

### 1.2 Por que está aqui

Serve como **referência de pipeline** — padroniza vocabulário e
estrutura que serão usados no nosso projeto. Não é artigo científico.

### 1.3 O que aproveitar

- **Estrutura de pipeline:** EDA → limpeza → engenharia de atributos →
  modelagem → avaliação.
- **`ColumnTransformer` + `Pipeline`:** exatamente o que precisamos no
  v2.
- **Métricas:** MAE, RMSE, R². Descrição didática, boa para citar.
- **Regressão Linear, Ridge, Lasso, RandomForest:** comparação.
- **Interpretação de coeficientes:** cuidado com multicolinearidade.

### 1.4 O que NÃO aproveitar

- Dataset Ames Housing em si — não tem relação com abandono escolar.
- Valores absolutos de MAE/RMSE em US$ — sem relação com p.p. de
  abandono.
- Comparação "regressão linear venceu RandomForest" — foi porque os
  dados foram construídos linearmente. Não é regra geral.

### 1.5 Citação

> FIGUEIRÊDO, Bruno Cesar Barreto. **Estimação de Preços de Imóveis
> com Machine Learning: Um Estudo Completo com o Dataset Ames
> Housing.** Material didático. UERR, setembro de 2026.

### 1.6 Onde está o PDF

`A1_ames_housing_didatico.pdf`

---

## 2. Caracterização das escolas

### 2.1 O que é

Artigo obtido pela Gabriela. Caracteriza escolas a partir de variáveis
dicotômicas do Censo.

### 2.2 Variáveis analisadas

18 variáveis dicotômicas (presença/ausência), agrupadas em 4
dimensões:

- **Infraestrutura Básica (IIB):** água potável, energia elétrica,
  coleta de lixo, banheiro.
- **Dependências Administrativas (IDA):** despensa, refeitório, sala
  da diretoria, sala dos professores, secretaria.
- **Dependências Pedagógicas (IDP):** biblioteca, laboratório de
  informática, pátio coberto, quadra de esportes.
- **Equipamentos Pedagógicos (IEP):** computador, impressora, projetor
  multimídia, acesso à internet.

### 2.3 Como aproveitar

- **Variáveis candidatas para enriquecimento (Fase 3).** Ver
  `02_DADOS.md` §32.
- **Agrupamentos podem simplificar.** Em vez de 18 features, 4
  índices.
- **Referência para caracterização de infraestrutura** no artigo.

### 2.4 Cuidados

- Muitas variáveis juntas podem inflar o modelo. Começar pelas 4
  dimensões, depois detalhar se valer a pena.
- Presença/ausência não é o mesmo que qualidade da infraestrutura.

### 2.5 Citação

Preencher quando o artigo for formalmente lido e referenciado.

### 2.6 Onde está o PDF

`A2_caracterizacao_escolas.pdf`

---

## 3. Bibliografia geral

Referências que embasam contexto e método. Preencher conforme o
artigo evolui.

### 3.1 Fontes de dados

- INEP — Microdados do Censo Escolar.
- INEP — Indicadores Educacionais (tx_rend, TDI, ATU, IED, HAD).
- INEP — Notas técnicas dos indicadores.

### 3.2 Método

- Breiman (2001) — Random Forests.
- Friedman (2001) — Gradient Boosting.
- Hastie, Tibshirani, Friedman — The Elements of Statistical
  Learning.
- Kuhn & Johnson — Feature Engineering and Selection.

### 3.3 Contexto

- Estudos sobre abandono escolar no Brasil.
- Estudos sobre distorção idade-série.
- Estudos sobre Pé-de-Meia.

### 3.4 Ética

- Harrison & Rubinfeld (1978) — Boston Housing (referência histórica
  do problema ético).
- Discussões sobre viés em dados educacionais.

### 3.5 Como preencher

Cada referência deve ter:
- Citação ABNT.
- Por que importa.
- Onde é usada no artigo.

Ver `05_referencias_03_bibliografia_geral.md` no histórico do projeto
para detalhes adicionais.

---

## 4. Onde estão os PDFs

- `A1_ames_housing_didatico.pdf`
- `A2_caracterizacao_escolas.pdf`
- Outros: a adicionar conforme adquiridos.

**Política:** não converter PDF para markdown. O PDF preserva
fórmula, figura e tabela. A anotação em `.md` (este arquivo) é o que
a IA lê primeiro.