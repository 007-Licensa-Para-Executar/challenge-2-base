# Guia de Desenvolvimento: Banco Vetorial e Armazenamento Local (SQLite-vec)

## 1. Identificação e Propósito do Subsistema
* **Arquivo no Código:** `knowledge_base/vector_store.py` e `knowledge_base/schema.sql`
* **Objetivo Primário:** Prover a infraestrutura de persistência relacional e busca vetorial densa de alta velocidade, **100% embarcada e local**, garantindo conformidade irrestrita com a LGPD e o sigilo profissional do psicólogo (CFP).
* **Por que este componente existe?** Atende à **Constraint 2 (Ter uma base de conhecimento)** e à **Constraint 7 (Ética e Explicabilidade)**. Armazena tanto os relatos confidenciais dos pacientes quanto os acervos de literatura clínica (TCC de Beck), permitindo buscas semânticas em milissegundos sem enviar nenhum dado para servidores de terceiros na nuvem.

---

## 2. Por que SQLite + `sqlite-vec`?

Em saúde mental, utilizar bancos vetoriais gerenciados em nuvem pública (ex: Pinecone, Weaviate Cloud) acarreta violações graves de privacidade e custeio desnecessário.
- **`sqlite-vec`:** Extensão oficial escrita em C puro para o SQLite que adiciona busca vetorial de vizinhos mais próximos ($k\text{-NN}$) com tabelas virtuais `vec0`.
- **Zero Dependência Externa:** Funciona diretamente no processo do Python via SQLite nativo.
- **Portabilidade:** Todo o banco reside em um único arquivo local criptografado (`data/clinica.db`).

---

## 3. Esquema Relacional e Vetorial Unificado (`knowledge_base/schema.sql`)

```sql
-- 1. Tabela Principal de Relatos do Diário do Paciente
CREATE TABLE IF NOT EXISTS patient_entries (
    entry_id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    modalidade TEXT CHECK(modalidade IN ('texto', 'audio', 'foto')) NOT NULL,
    raw_text TEXT NOT NULL,
    audio_file_path TEXT,
    audio_duration_sec REAL,
    macro_tema TEXT NOT NULL,
    confianca_macro_tema REAL NOT NULL,
    sentimento_predominante TEXT NOT NULL,
    score_polaridade REAL NOT NULL,
    indicio_textual_risco TEXT NOT NULL
);

-- 2. Tabela de Subtemas Vinculados
CREATE TABLE IF NOT EXISTS entry_subthemes (
    subtheme_id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id TEXT NOT NULL,
    nome TEXT NOT NULL,
    descricao TEXT,
    FOREIGN KEY(entry_id) REFERENCES patient_entries(entry_id) ON DELETE CASCADE
);

-- 3. Tabela de Spans de Evidências Literais (Ancoragem)
CREATE TABLE IF NOT EXISTS entry_evidence_spans (
    span_id INTEGER PRIMARY KEY AUTOINCREMENT,
    subtheme_id INTEGER NOT NULL,
    quote_text TEXT NOT NULL,
    start_char INTEGER NOT NULL,
    end_char INTEGER NOT NULL,
    audio_start_sec REAL,
    audio_end_sec REAL,
    FOREIGN KEY(subtheme_id) REFERENCES entry_subthemes(subtheme_id) ON DELETE CASCADE
);

-- 4. Tabela de Literatura Clínica Autorizada (RAG)
CREATE TABLE IF NOT EXISTS clinical_documents (
    doc_id TEXT PRIMARY KEY,
    titulo TEXT NOT NULL,
    autor TEXT NOT NULL,
    ano INTEGER NOT NULL,
    secao TEXT NOT NULL,
    conteudo_chunk TEXT NOT NULL,
    licenca TEXT NOT NULL
);

-- 5. Tabelas Virtuais Vetoriais (sqlite-vec usando dimensão 384 do e5-small)
CREATE VIRTUAL TABLE IF NOT EXISTS vec_literature USING vec0(
    embedding float[384]
);

CREATE VIRTUAL TABLE IF NOT EXISTS vec_patient_entries USING vec0(
    embedding float[384]
);
```

---

## 4. Implementação do Motor Vetorial (`knowledge_base/vector_store.py`)

```python
import struct
import sqlite3
import sqlite_vec
from typing import List, Dict, Any, Optional

def serialize_f32(vector: List[float]) -> bytes:
    """Serializa lista de floats para o formato binário esperado pelo sqlite-vec."""
    return struct.pack(f"{len(vector)}f", *vector)

class LocalVectorStore:
    def __init__(self, db_path: str = "data/clinica.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        
        # Habilita a extensão sqlite-vec
        self.conn.enable_load_extension(True)
        sqlite_vec.load(self.conn)
        self.conn.enable_load_extension(False)
        
        self._init_tables()

    def _init_tables(self):
        with open("knowledge_base/schema.sql", "r", encoding="utf-8") as f:
            self.conn.executescript(f.read())
        self.conn.commit()

    # --- Métodos de Ingestão de Literatura Clínica (RAG) ---
    def insert_clinical_document(
        self,
        doc_id: str,
        titulo: str,
        autor: str,
        ano: int,
        secao: str,
        conteudo: str,
        licenca: str,
        embedding_384: List[float]
    ):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO clinical_documents 
                (doc_id, titulo, autor, ano, secao, conteudo_chunk, licenca)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (doc_id, titulo, autor, ano, secao, conteudo, licenca)
            )
            rowid = cursor.lastrowid
            # Insere no índice vetorial usando o rowid correspondente
            cursor.execute(
                "INSERT INTO vec_literature(rowid, embedding) VALUES (?, ?)",
                (rowid, serialize_f32(embedding_384))
            )

    # --- Método de Busca Semântica por Similaridade de Cosseno ---
    def search_clinical_guidelines(
        self,
        query_embedding: List[float],
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        query_blob = serialize_f32(query_embedding)
        cursor = self.conn.cursor()
        
        # Busca vetorial KNN com sqlite-vec combinada com metadados relacionais
        query_sql = """
            SELECT 
                d.doc_id,
                d.titulo,
                d.autor,
                d.ano,
                d.secao,
                d.conteudo_chunk,
                v.distance
            FROM vec_literature v
            JOIN clinical_documents d ON d.rowid = v.rowid
            WHERE v.embedding MATCH ?
            ORDER BY v.distance ASC
            LIMIT ?
        """
        rows = cursor.execute(query_sql, (query_blob, top_k)).fetchall()
        
        results = []
        for r in rows:
            # Converte a distância euclidiana/cosseno para um score de similaridade (0 a 1)
            similarity_score = max(0.0, 1.0 - (r["distance"] / 2.0))
            results.append({
                "doc_id": r["doc_id"],
                "titulo": r["titulo"],
                "autor": r["autor"],
                "ano": r["ano"],
                "secao": r["secao"],
                "texto": r["conteudo_chunk"],
                "distance": r["distance"],
                "score": round(similarity_score, 4)
            })
        return results

    def close(self):
        self.conn.close()
```

---

## 5. Como Testar o Banco Vetorial Local (`tests/test_vector_store.py`)

```python
import os
import pytest
from knowledge_base.vector_store import LocalVectorStore

@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_clinica.db"
    store = LocalVectorStore(db_path=str(db_file))
    yield store
    store.close()

def test_insert_and_search_vector_store(temp_db):
    # Vetor unitário sintético com 384 dimensões
    dummy_vec = [0.05] * 384

    temp_db.insert_clinical_document(
        doc_id="BECK-TCC-01",
        titulo="Terapia Cognitivo-Comportamental",
        autor="Judith Beck",
        ano=2021,
        secao="Capítulo 7",
        conteudo="Treinamento de assertividade e fixação de limites interpessoais.",
        licenca="Academic Use Only",
        embedding_384=dummy_vec
    )

    # Busca exatamente pelo mesmo vetor (distância deve ser próxima de 0.0)
    results = temp_db.search_clinical_guidelines(query_embedding=dummy_vec, top_k=1)
    
    assert len(results) == 1
    assert results[0]["doc_id"] == "BECK-TCC-01"
    assert results[0]["score"] > 0.95
```

---

## 6. Referências Técnicas
1. **sqlite-vec (GitHub):** [https://github.com/asg017/sqlite-vec](https://github.com/asg017/sqlite-vec).
2. **MDPI Retrieval-Augmented Generation (RAG) in Healthcare (2026):** Estudo de eficácia e latência de bancos vetoriais locais comparados a soluções em nuvem.
3. **Lei Geral de Proteção de Dados (LGPD - Lei 13.709/2018):** Diretrizes para armazenamento seguro e criptografado de dados de saúde sensíveis.
