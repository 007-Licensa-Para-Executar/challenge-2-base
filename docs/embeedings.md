# 05 - Estratégia de Representação Vetorial e Embeddings

## 1. Visão Geral e Critérios de Projeto

A representação vetorial no sistema atua em dois subsistemas com requisitos distintos:
1. **Camada de Deep Learning (Rede Neural Própria):** Requer representações adequadas para treinar o classificador dos 8 macrotemas clínicos sem violar a restrição de "construir a rede do zero".
2. **Camada de Recuperação Semântica (Banco Vetorial & RAG):** Requer modelos de linguagem densos pré-treinados capazes de capturar nuances semânticas e relações conceituais em português brasileiro.

---

## 2. Comparativo de Modelos Candidatos

| Característica | TF-IDF (Term Frequency-Inverse Document Frequency) | multilingual-e5-small (Intfloat) | paraphrase-multilingual-MiniLM-L12-v2 |
| :--- | :--- | :--- | :--- |
| **Tipo de Representação** | Esparsa (Sparsely Bag-of-Words/N-grams) | Densa (Dense Embedding Transformer) | Densa (Dense Embedding Transformer) |
| **Dimensão do Vetor** | 512 a 1.024 (configurável) | 384 dimensões | 384 dimensões |
| **Contexto Máximo** | Ilimitado (mas sem contexto sintático) | 512 tokens | 128 a 512 tokens |
| **Suporte ao Português** | Depende de Stemmer (NLTK RSLP) | Excelente (treinado em 100+ línguas) | Muito Bom (alinhamento semântico) |
| **Custo Computacional** | Quase zero (CPU rápida) | Baixo (~130 MB de parâmetros) | Muito Baixo (~120 MB de parâmetros) |
| **Aplicação no Projeto** | Entrada para o treino da Rede Neural MLP | Indexação no Banco Vetorial (SQLite-vec / Chroma) | Alternativa leve para ambiente local restrito |

---

## 3. Decisão Arquitetural e Segregação de Papéis

### A. Para o Treinamento da Rede Neural de Classificação Temática
- **Abordagem Adotada:** Vetorização híbrida via **TF-IDF com sub-palavras e n-grams de caracteres (1 a 3-grams)** com vocabulário fixado em 1.024 termos clínicos mais frequentes.
- **Justificativa Ética e de Engenharia:** Permite demonstrar com total clareza matemática que a rede neural (MLP) está efetivamente aprendendo as fronteiras de decisão a partir dos pesos, sem depender de representações "mágicas" de embeddings proprietários.

### B. Para o Banco Vetorial e RAG (Histórico do Paciente e Diretrizes Clínicas)
- **Modelo Adotado:** `intfloat/multilingual-e5-small`.
- **Prefixo de Instrução:**
  - Para indexação de passagens/diários: `"passage: <texto>"`
  - Para perguntas/buscas do psicólogo: `"query: <texto>"`
- **Vantagens Clínicas:** Consegue aproximar expressões colloquiais de desabafo (ex: *"sinto um nó na garganta e não consigo sair da cama"*) de conceitos técnicos de depressão e ansiedade somática indexados nas diretrizes clínicas, superando a barreira lexical do vocabulário estrito.

---

## 4. Estratégia de Chunking e Gestão de Contexto

Para evitar a perda de contexto psicológico decorrente do limite de 512 tokens:
1. **Diários Curtos (< 300 palavras):** O relato é indexado como um único chunk integral, preservando a coerência narrativa e a progressão dos afetos.
2. **Relatos Longos (> 300 palavras):** Divisão com janela deslizante de 250 tokens e **sobreposição (*overlap*) de 50 tokens**, garantindo que conectivos e causas de sofrimento não sejam cortados entre blocos.
3. **Metadados Anexados ao Vetor:** Todo vetor carrega metadados imutáveis: `patient_id`, `data_registro`, `modalidade` (texto/áudio), `macrotema_previsto` e `subtemas_associados`.
