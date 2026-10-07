# 00 — LEIA PRIMEIRO

Este é o mapa do projeto. Lista os documentos, o que cada um cobre,
em que ordem devem ser lidos, e onde encontrar cada coisa.

---

## Sobre o projeto

- **Título:** Risco de abandono escolar em Roraima
- **Tipo:** PIBIC/UERR (Edital 35/2026) + artigo da disciplina de Mineração de Dados
- **Orientador:** Prof. Bruno Cesar Barreto Figueiredo
- **Instituição:** Universidade Estadual de Roraima (UERR)
- **Repositório:** https://github.com/gabsma25/abandonoescolar

### Pergunta de pesquisa

> Com os indicadores educacionais de uma escola de Roraima no ano `t`,
> é possível estimar a taxa de abandono esperada no ano `t+1` — nos
> anos finais do ensino fundamental e no ensino médio — para apoiar
> ações preventivas de gestão?

- **Unidade de análise:** escola-ano. Não prevê alunos individuais.
- **Uso do resultado:** priorizar escolas para diagnóstico. Nunca
  ranquear ou punir escolas.

---

## Arquivos deste pacote

| Arquivo | Cobre |
|---|---|
| `00_LEIA_PRIMEIRO.md` | Este mapa. |
| `01_PROJETO.md` | Contexto, pergunta, escopo, pessoas, estado atual, glossário. |
| `02_DADOS.md` | Fontes INEP, repositório, base longitudinal, qualidade, enriquecimento. |
| `03_METODOLOGIA.md` | Desenho t→t+1, variáveis, pipeline, validação, métricas. |
| `04_EXPERIMENTOS.md` | Smoke test, v1_old, v1_atual, crítica, achados. |
| `05_REFERENCIAS.md` | Ames Housing, caracterização das escolas, bibliografia. |
| `06_DECISOES_PROBLEMAS_PERGUNTAS.md` | Decisões tomadas, problemas conhecidos, perguntas em aberto. |
| `07_PLANOS.md` | Próximas fases: pipeline limpo, enriquecimento, classificação. |

**PDFs originais** das referências ficam na mesma pasta com prefixo
`A` (A1, A2, ...). Cada PDF tem sua anotação em `05_REFERENCIAS.md`.

---

## Ordem de leitura

### Para uma IA com acesso ao pacote completo

Ler em ordem numérica: 00 → 01 → 02 → 03 → 04 → 05 → 06 → 07.

Cada arquivo pressupõe o anterior. O bloco 02 assume que você já
conhece o projeto (01). O bloco 03 assume que você já conhece os
dados (02). E assim por diante.

### Para uma IA com limite de arquivos

Ordem mínima para entender o projeto:

1. `00_LEIA_PRIMEIRO.md`
2. `01_PROJETO.md`
3. `02_DADOS.md`
4. `03_METODOLOGIA.md`
5. `06_DECISOES_PROBLEMAS_PERGUNTAS.md`

Com esses cinco, uma IA tem contexto, dados, método, decisões e
pendências. É suficiente para responder perguntas sobre o projeto.

`04_EXPERIMENTOS.md` e `05_REFERENCIAS.md` são consulta — úteis mas
não essenciais para entender o estado atual.

`07_PLANOS.md` é forward-looking — útil para saber "o que fazer
agora".

---

## Sobre os PDFs das referências

Os artigos originais ficam em **PDF**, com prefixo `A`. Cada PDF tem
um `.md` correspondente em `05_REFERENCIAS.md` com anotação (o que
aproveitar, o que descartar, o que citar).

**Não converta PDF para markdown.** Perde fórmula, figura, tabela, e
a referência bibliográfica correta. O PDF é o original; o `.md` é a
anotação.

---

## Estado do pacote

- [x] `00_LEIA_PRIMEIRO.md`
- [x] `01_PROJETO.md`
- [x] `02_DADOS.md`
- [x] `03_METODOLOGIA.md`
- [x] `04_EXPERIMENTOS.md`
- [x] `05_REFERENCIAS.md`
- [x] `06_DECISOES_PROBLEMAS_PERGUNTAS.md`
- [x] `07_PLANOS.md`