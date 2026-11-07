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

Conforme o Artigo 5º, inciso II da LGPD, informações sobre saúde mental e vida afetiva constituem **dados pessoais sensíveis**. A branch `feat/security-lgpd-encryption` introduz uma camada técnica de isolamento e proteção criptográfica em repouso:

### 2.1 Especificação do Algoritmo (`security/encryption.py`)
- **Criptografia Simétrica Autenticada:** Implementada via padrão **Fernet** (especificação criptográfica baseada em **AES-128-CBC** com preenchimento PKCS7 e autenticação de integridade **HMAC-SHA256**).
- **Inviolabilidade:** O texto do relato nunca é armazenado em claro quando a criptografia estiver ativa; o banco SQLite armazena unicamente o *ciphertext* precedido pelo prefixo `ENC:`.
- **Gestão de Chaves:**
  - Prioridade 1: Variável de ambiente `DIARY_ENCRYPTION_KEY` (padrão de 12-factor app para contêineres e nuvem).
  - Prioridade 2: Arquivo local protegido `.diary_encryption.key` gerado com permissões restritas do sistema operacional (`0o600` - somente leitura/escrita pelo proprietário do processo).
  - Normalização automática: Derivação de chaves via SHA-256 caso a semente fornecida não tenha 32 bytes URL-safe.

### 2.2 Pseudonimização Determinística de Pacientes (Art. 13, § 4º da LGPD)
Para evitar que dados civis (como CPF, nome completo ou número de prontuário) fiquem vinculados aos registros analíticos:
- Método: [`pseudonymize_patient_id(raw_id)`](file:///c:/Users/BLU8CA/OneDrive%20-%20Bosch%20Group/Desktop/PUC/challenge-2-base/security/encryption.py#L130-L150)
- Mecanismo: Assinatura criptográfica `HMAC-SHA256(chave, raw_id)` truncada em token hexadecimal prefixado (ex: `PAC-B4F1A02E`).
- Propriedade: É determinístico para o mesmo ambiente (permitindo correlação longitudinal das sessões do mesmo paciente pelo psicólogo), mas irreversível por terceiros desprovidos da chave mestra.

---

## 3. Integração com a Persistência de Dados (`agents/extractor/storage.py`)

- **Gravação Segura:** [`save_result(..., encrypt=True)`](file:///c:/Users/BLU8CA/OneDrive%20-%20Bosch%20Group/Desktop/PUC/challenge-2-base/agents/extractor/storage.py#L18-L95) cifra o `input_text` antes do comando `INSERT`.
- **Ativação por Ambiente:** Definir `ENABLE_DIARY_ENCRYPTION=true` no arquivo `.env` ativa a criptografia globalmente e de forma transparente.
- **Recuperação Descriptografada:** [`read_result_text(db_path, run_id)`](file:///c:/Users/BLU8CA/OneDrive%20-%20Bosch%20Group/Desktop/PUC/challenge-2-base/agents/extractor/storage.py#L108-L128) recupera e decifra o texto para o terapeuta autorizado.
- **Compatibilidade Retroativa:** Registros anteriores em texto claro são lidos sem erro, garantindo migração suave sem perda de dados.
