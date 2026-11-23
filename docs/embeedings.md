# 05 - Estratégia de Representação Vetorial e Embeddings

> **Estado atual:** a rede implementada usa `ClinicalTextEmbedder` com embeddings
> densos de 128 dimensões, em modo gaussiano ou LSA/SVD. O recuperador de RAG
> implementado usa BM25 por padrão e aceita E5 local como backend opcional.
> SQLite-vec, ChromaDB e índice vetorial persistente não são componentes
> verificados desta implementação.

## 1. Visão Geral e Critérios de Projeto

A representação vetorial no sistema atua em dois subsistemas com requisitos distintos:
1. **Camada de Deep Learning (Rede Neural Própria):** vetores densos locais de 128 dimensões são usados pelo classificador temático operacional.
2. **Camada de Recuperação (RAG):** o demonstrador usa recuperação lexical BM25; o backend E5 local é opcional e não exige envio de dados a serviços externos.

---

## 2. Comparativo de Modelos Candidatos

| Característica | TF-IDF (Term Frequency-Inverse Document Frequency) | multilingual-e5-small (Intfloat) | paraphrase-multilingual-MiniLM-L12-v2 |
| :--- | :--- | :--- | :--- |
| **Tipo de Representação** | Esparsa (Sparsely Bag-of-Words/N-grams) | Densa (Dense Embedding Transformer) | Densa (Dense Embedding Transformer) |
| **Dimensão do Vetor** | 128 no embedder clínico; TF-IDF legado pode usar outra dimensão | 384 dimensões no modelo candidato E5 | 384 dimensões |
| **Contexto Máximo** | Ilimitado (mas sem contexto sintático) | 512 tokens | 128 a 512 tokens |
| **Suporte ao Português** | Depende de Stemmer (NLTK RSLP) | Excelente (treinado em 100+ línguas) | Muito Bom (alinhamento semântico) |
| **Custo Computacional** | Quase zero (CPU rápida) | Baixo (~130 MB de parâmetros) | Muito Baixo (~120 MB de parâmetros) |
| **Aplicação no Projeto** | Implementado em `models/embedder.py` | Backend E5 opcional no recuperador | Não confirmado como implementação ativa |

---

## 3. Decisão Arquitetural e Segregação de Papéis

### A. Para o Treinamento da Rede Neural de Classificação Temática
- **Abordagem Implementada:** `ClinicalTextEmbedder` cria um vocabulário local, limita os termos configurados e gera vetores densos de 128 dimensões.
- **Inicialização:** Gaussian/Xavier-like por padrão ou projeção LSA/SVD quando há dados suficientes e o modo SVD é selecionado.
- **Tratamento:** stop words, remoção de acentos, pesos IDF opcionais e normalização por documento.
- **Limitação:** o vetor representa o vocabulário e o conjunto de treino observado. Não prova semântica clínica nem calibração do classificador.

### B. Para o RAG (Histórico do Paciente e Diretrizes Clínicas)
- **Modelo Candidato:** `intfloat/multilingual-e5-small`.
- **Estado:** pode ser usado pelo backend `e5` quando o diretório local do modelo é fornecido. Não é baixado automaticamente.
- **Prefixo de Instrução no código atual:**
  - Para indexação de passagens/diários: `"passage: <texto>"`
  - Para perguntas/buscas do psicólogo: `"query: <texto>"`
- **Limitação:** proximidade semântica não comprova relevância clínica, suficiência da fonte ou correção da resposta gerada.

---

## 4. Estratégia de Chunking e Gestão de Contexto

No recuperador atual:
1. Os trechos são divididos em blocos literais de até 600 caracteres por padrão.
2. O limite pode ser configurado no retriever, sem overlap persistente.
3. A evidência conserva `record_id`, `patient_id`, data, título, texto, início e fim no original.
4. Cada consulta é limitada ao conjunto previamente selecionado por paciente e período.
