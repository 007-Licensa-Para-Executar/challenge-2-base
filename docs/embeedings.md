# 05 - Estratégia de Representação Vetorial e Embeddings (SBERT)

> **Estado atual:** a rede implementada usa `ClinicalTextEmbedder` com embeddings
> densos de 128 dimensões, em modo gaussiano ou LSA/SVD. O recuperador de RAG
> implementado usa BM25 por padrão e aceita E5 local como backend opcional.
> SQLite-vec, ChromaDB e índice vetorial persistente não são componentes
> verificados desta implementação.

## 1. Visão Geral e Critérios de Projeto

A representação vetorial no sistema atua em dois subsistemas com requisitos complementares:
1. **Camada de Deep Learning (Rede Neural Própria):** Converte o diário do paciente em vetores semânticos densos para que a Rede Neural MLP identifique e atribua percentuais (`%`) aos **6 temas clínicos** (`autopercepcao`, `vinculos`, `desempenho`, `fisico`, `rupturas`, `outros`).
2. **Camada de Recuperação (RAG):** o demonstrador usa recuperação lexical BM25; o backend E5 local é opcional e não exige envio de dados a serviços externos.

---

## 2. Comparativo dos Encoders SBERT Adotados

Abordagens esparsas baseadas em contagem de palavras (como TF-IDF) foram **substituídas** na rede neural temática por embeddings densos de sentença (**SBERT** via `sentence-transformers`), superando a limitação de vocabulário exato:

| Característica | `intfloat/multilingual-e5-small` (Padrão da Rede Neural & E5 RAG) | `paraphrase-multilingual-MiniLM-L12-v2` (Alternativa SBERT) |
| :--- | :--- | :--- |
| **Tipo de Representação** | Densa (Dense Embedding Transformer) | Densa (Sentence-BERT / Transformer) |
| **Dimensão do Vetor** | 384 dimensões | 384 dimensões |
| **Contexto Máximo** | 512 tokens | 128 tokens (configurável) |
| **Prefixo de Texto** | Exige `"query: "` / `"passage: "` (aplicado automaticamente pelo `SBERTEmbedder`) | Não exige |
| **Suporte ao Português** | Excelente (treinado em 100+ línguas) | Muito Bom (alinhamento semântico multilíngue) |
| **Aplicação no Projeto** | **Entrada padrão da Rede Neural MLP (`SBERTEmbedder`) e backend E5 opcional no RAG** | Alternativa leve para a Rede Neural (`--sbert-model`) |

---

## 3. Decisão Arquitetural e Segregação de Papéis

### A. Para a Rede Neural de Classificação Temática (`models/sbert_embedder.py`)
- **Abordagem Adotada:** Embeddings densos de sentença via **`SBERTEmbedder`** (`sentence-transformers`), utilizando por padrão o modelo congelado **`intfloat/multilingual-e5-small`** (384 dimensões, janela de 512 tokens e normalização L2).
- **Por que SBERT ao invés de TF-IDF:**
  1. **Compreensão Semântica:** Relatos psicológicos usam metáforas, gírias e paráfrases. O SBERT aproxima expressões diferentes com o mesmo significado clínico, enquanto o TF-IDF dependia de coincidência exata de n-gramas.
  2. **Zero Vazamento de Dados (*No Data Leakage*):** O encoder SBERT é utilizado com pesos pré-treinados e **congelados** (`fit()` é *no-op*). Ele apenas projeta o texto em um vetor de 384 dimensões; quem aprende as fronteiras de decisão entre os **6 temas** (`autopercepcao`, `vinculos`, `desempenho`, `fisico`, `rupturas`, `outros`) e gera os **percentuais (`%`)** após receber o diário é a Rede Neural MLP (`ClinicalThemeMLP` / `NumpyClinicalMLP`).
  3. **Serialização Enxuta:** O `SBERTEmbedder` salva apenas os metadados de configuração em `dist/theme_embedder.joblib`, recarregando o modelo sob demanda sem duplicar ~470 MB de pesos em disco.

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
