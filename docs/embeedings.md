# 05 - Estratégia de Representação Vetorial e Embeddings (SBERT)

## 1. Visão Geral e Critérios de Projeto

A representação vetorial no sistema atua em dois subsistemas com requisitos complementares:
1. **Camada de Deep Learning (Rede Neural Própria):** Converte o diário do paciente em vetores semânticos densos para que a Rede Neural MLP identifique e atribua percentuais (`%`) aos **6 temas clínicos** (`autopercepcao`, `vinculos`, `desempenho`, `fisico`, `rupturas`, `outros`).
2. **Camada de Recuperação Semântica (Banco Vetorial & RAG):** Indexa diretrizes clínicas e histórico para busca híbrida capaz de capturar nuances semânticas e relações conceituais em português brasileiro.

---

## 2. Comparativo dos Encoders SBERT Adotados

Abordagens esparsas baseadas em contagem de palavras (como TF-IDF) foram **substituídas** por embeddings densos de sentença (**SBERT** via `sentence-transformers`), superando a limitação de vocabulário exato:

| Característica | `intfloat/multilingual-e5-small` (Padrão da Rede Neural & RAG) | `paraphrase-multilingual-MiniLM-L12-v2` (Alternativa SBERT) |
| :--- | :--- | :--- |
| **Tipo de Representação** | Densa (Dense Embedding Transformer) | Densa (Sentence-BERT / Transformer) |
| **Dimensão do Vetor** | 384 dimensões | 384 dimensões |
| **Contexto Máximo** | 512 tokens | 128 tokens (configurável) |
| **Prefixo de Texto** | Exige `"query: "` / `"passage: "` (aplicado automaticamente pelo `SBERTEmbedder`) | Não exige |
| **Suporte ao Português** | Excelente (treinado em 100+ línguas) | Muito Bom (alinhamento semântico multilíngue) |
| **Aplicação no Projeto** | **Entrada padrão da Rede Neural MLP (`SBERTEmbedder`) e indexação no Banco Vetorial / RAG** | Alternativa leve para a Rede Neural (`--sbert-model`) |

---

## 3. Decisão Arquitetural e Segregação de Papéis

### A. Para a Rede Neural de Classificação Temática (`models/sbert_embedder.py`)
- **Abordagem Adotada:** Embeddings densos de sentença via **`SBERTEmbedder`** (`sentence-transformers`), utilizando por padrão o modelo congelado **`intfloat/multilingual-e5-small`** (384 dimensões, janela de 512 tokens e normalização L2).
- **Por que SBERT ao invés de TF-IDF:**
  1. **Compreensão Semântica:** Relatos psicológicos usam metáforas, gírias e paráfrases. O SBERT aproxima expressões diferentes com o mesmo significado clínico, enquanto o TF-IDF dependia de coincidência exata de n-gramas.
  2. **Zero Vazamento de Dados (*No Data Leakage*):** O encoder SBERT é utilizado com pesos pré-treinados e **congelados** (`fit()` é *no-op*). Ele apenas projeta o texto em um vetor de 384 dimensões; quem aprende as fronteiras de decisão entre os **6 temas** (`autopercepcao`, `vinculos`, `desempenho`, `fisico`, `rupturas`, `outros`) e gera os **percentuais (`%`)** após receber o diário é a Rede Neural MLP (`ClinicalThemeMLP` / `NumpyClinicalMLP`).
  3. **Serialização Enxuta:** O `SBERTEmbedder` salva apenas os metadados de configuração em `dist/theme_embedder.joblib`, recarregando o modelo sob demanda sem duplicar ~470 MB de pesos em disco.

### B. Para o Banco Vetorial e RAG (Histórico do Paciente e Diretrizes Clínicas)
- **Modelo Adotado:** `intfloat/multilingual-e5-small` (384 dimensões).
- **Prefixo de Instrução:**
  - Para indexação de passagens/diários: `"passage: <texto>"`
  - Para perguntas/buscas do psicólogo: `"query: <texto>"`
- **Vantagens Clínicas:** Aproxima expressões coloquiais de desabafo de conceitos técnicos indexados nas diretrizes clínicas, superando a barreira lexical.

---

## 4. Estratégia de Chunking e Gestão de Contexto

Para evitar a perda de contexto psicológico em textos extensos:
1. **Diários Curtos (< 300 palavras):** O relato é indexado como um único chunk integral, preservando a coerência narrativa e a progressão dos afetos.
2. **Relatos Longos (> 300 palavras):** Divisão com janela deslizante de 250 tokens e **sobreposição (*overlap*) de 50 tokens**, garantindo que conectivos e causas de sofrimento não sejam cortados entre blocos.
3. **Metadados Anexados ao Vetor:** Todo vetor carrega metadados estruturados: `patient_id`, `data_registro`, `modalidade` (texto/áudio), `macrotema_previsto` (entre os 6 temas) e `subtemas_associados`.
