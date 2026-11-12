# Conformidade LGPD, Governança Ética e Datasets em Português

Este documento consolida as salvaguardas de conformidade com a **Lei Geral de Proteção de Dados (LGPD - Lei 13.709/2018)**, as especificações técnicas da camada de criptografia implementada na branch `feat/security-lgpd-encryption`, e o levantamento de datasets em português recomendados para o treinamento e validação da Rede Neural.

---

## 1. Mapeamento de Datasets em Português para Treinamento e Validação

Para a evolução do classificador neural além dos dados sintéticos parametrizados pelo *PsychAdapter*, foram identificados os seguintes corpora em português (PT-BR) no ecossistema científico e no Hugging Face:

| Dataset / Corpus | Fonte / Autores | Volume e Formato | Domínio Clínico / Afetivo Coberto | Aplicação no Projeto |
| :--- | :--- | :--- | :--- | :--- |
| **`rhaymison/mental-health-pt`** | Hugging Face / Comunidade PLN | > 10.000 amostras (texto em PT-BR) | Relatos de sofrimento, queixas somáticas, consultas e desabafos de saúde mental. | Fine-tuning e validação cruzada dos temas `saude_sono`, `trabalho` e `autoestima`. |
| **`antoniomenezes/go_emotions_ptbr`** | Hugging Face (Google GoEmotions em PT-BR) | ~ 54.000 sentenças rotuladas | 27 emoções refinadas (tristeza, raiva, medo, admiração, afeto, alívio, etc.) + neutro. | Enriquecimento da detecção de polaridade e tom afetivo no Agente 1 e na Rede Neural. |
| **`DepressSet`** | UFMG / UFRGS / ResearchGate (2023–2025) | Amostras anotadas em fóruns e mídias sociais | Postagens depressivas e sofrimento psicológico em português brasileiro. | Benchmark holdout cego para detecção de marcadores sintáticos e validação do fallback de risco. |
| **`brighter-dataset/BRIGHTER-emotion-categories`** | ACL 2024 / Hugging Face | Multi-label humano em PT-BR | Emoções complexas e contextuais em sentenças do cotidiano. | Validação multirrótulo para relatos que misturam múltiplos temas simultâneos. |
| **`AiresPucrs/sentiment-analysis-pt`** | PUCRS | > 80.000 textos | Valência afetiva positiva, negativa e neutra em português brasileiro. | Calibração de polaridade e teste de robustez do classificador contra textos ambíguos. |

> [!NOTE]
> **Estratégia Híbrida Recomendada:** O treinamento inicial do MVP mantém-se em dados sintéticos (*PsychAdapter* + simulações de Ulster) para garantir conformidade estrita de privacidade em demonstrações abertas. Os datasets listados acima servem como conjunto de teste de estresse (*stress testing*) e generalização linguística para a banca examinadora.

---

## 2. Camada de Segurança Criptográfica (LGPD Art. 5º, II e Art. 46)

Conforme o Artigo 5º, inciso II da LGPD, informações sobre saúde mental e vida afetiva constituem **dados pessoais sensíveis**. A arquitetura introduz uma camada técnica de isolamento e proteção criptográfica em repouso:

### 2.1 Especificação do Algoritmo (`security/encryption.py`)
- **Criptografia Simétrica Autenticada:** Implementada via padrão **Fernet** (especificação criptográfica baseada em **AES-128-CBC** com preenchimento PKCS7 e autenticação de integridade **HMAC-SHA256**).
- **Inviolabilidade:** O texto do relato nunca é armazenado em claro quando a criptografia estiver ativa; o banco SQLite armazena unicamente o *ciphertext* precedido pelo prefixo `ENC:`.
- **Suporte a Rotação de Chaves (Zero-Downtime):** Suporte nativo a `MultiFernet`. Chaves múltiplas separadas por vírgula permitem descriptografar dados históricos com chaves antigas enquanto novas gravações usam a chave primária mais recente (`rotate_diary_text`).
- **Gestão de Chaves:**
  - Prioridade 1: Variável de ambiente `DIARY_ENCRYPTION_KEY` (padrão de 12-factor app para contêineres e nuvem; suporta lista separada por vírgula).
  - Prioridade 2: Arquivo local protegido `.diary_encryption.key` gerado com permissões restritas (`0o600`).
  - Normalização automática: Derivação de chaves via SHA-256 caso a semente fornecida não tenha 32 bytes URL-safe.

### 2.2 Pseudonimização Determinística de Pacientes (Art. 13, § 4º da LGPD)
Para evitar que dados civis (como CPF, nome completo ou número de prontuário) fiquem vinculados aos registros analíticos:
- Método: [`pseudonymize_patient_id(raw_id, length=16)`](file:///c:/Users/BLU8CA/OneDrive%20-%20Bosch%20Group/Desktop/PUC/challenge-2-base/security/encryption.py)
- Mecanismo: Assinatura criptográfica `HMAC-SHA256(chave, raw_id)` formatada em token hexadecimal prefixado (ex: `PAC-B4F1A02E3917DF12`).
- Entropia e Resistência a Colisão: Por padrão utiliza 16 caracteres hexadecimais (64 bits de entropia), eliminando o risco do paradoxo do aniversário em bases de pacientes em escala real.
- Propriedade: Determinístico para o mesmo ambiente (permitindo correlação longitudinal das sessões do mesmo paciente pelo psicólogo), mas irreversível por terceiros desprovidos da chave mestra.

---

## 3. Integração com a Persistência e Direitos dos Titulares (`agents/extractor/storage.py`)

- **Gravação Segura:** [`save_result(..., encrypt=True)`](file:///c:/Users/BLU8CA/OneDrive%20-%20Bosch%20Group/Desktop/PUC/challenge-2-base/agents/extractor/storage.py) cifra o `input_text` antes do comando `INSERT`.
- **Ativação por Ambiente ou CLI:** Definir `ENABLE_DIARY_ENCRYPTION=true` no `.env` ou utilizar a flag `--encrypt` no CLI ativa a proteção em repouso.
- **Recuperação Descriptografada:** [`read_result_text(db_path, run_id)`](file:///c:/Users/BLU8CA/OneDrive%20-%20Bosch%20Group/Desktop/PUC/challenge-2-base/agents/extractor/storage.py) recupera e decifra o texto para o terapeuta autorizado.
- **Direito de Eliminação do Titular (LGPD Art. 18, VI):** Função [`delete_result(db_path, run_id)`](file:///c:/Users/BLU8CA/OneDrive%20-%20Bosch%20Group/Desktop/PUC/challenge-2-base/agents/extractor/storage.py) permite excluir de forma atômica e definitiva os registros solicitados pelo titular.
- **Política de Retenção e Expiração de Dados (LGPD Art. 16):** Função [`purge_records(db_path, older_than_days=N)`](file:///c:/Users/BLU8CA/OneDrive%20-%20Bosch%20Group/Desktop/PUC/challenge-2-base/agents/extractor/storage.py) automatiza a exclusão periódica de relatos que excederam o ciclo de vida autorizado.
- **Compatibilidade Retroativa:** Registros anteriores em texto claro continuam legíveis sem erro, viabilizando migrações transparentes.
