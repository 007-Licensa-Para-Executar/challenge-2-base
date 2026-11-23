# Armazenamento local e recuperação vetorial

Este documento descreve o armazenamento implementado no demonstrador atual. Ele não
afirma que exista um banco vetorial completo para dados clínicos reais.

## 1. Persistência relacional

O módulo `agents/copilot/storage.py` usa SQLite no arquivo configurado pelo
aplicativo. A tabela `diary_records` mantém identificadores do registro e do
paciente, data e o objeto JSON completo do relato sintético.

Os campos são persistidos localmente e a consulta é limitada por `patient_id` e
intervalo inclusivo de datas. O `patient_id` usado pelo demonstrador é apenas um
contexto de seleção; não representa autenticação nem autorização da psicóloga.

O armazenamento da aplicação principal de extração possui tabelas próprias em
`agents/extractor/storage.py`, com criptografia opcional em repouso implementada
por `security/encryption.py`.

## 2. Recuperação léxica

O módulo `agents/copilot/retriever.py` fragmenta cada relato em trechos literais
e realiza recuperação BM25 local. Os pontos inicial e final são preservados na
evidência, permitindo verificar o trecho no registro original.

O modo BM25 calcula ranqueamento a partir de frequência e presença de termos. O
score é um valor de ranqueamento, não probabilidade de fato, suficiência clínica
ou correção da resposta gerada.

## 3. Recuperação vetorial local opcional

O mesmo recuperador aceita o backend `e5`. Nesse modo, utiliza um diretório local
compatível com Sentence Transformers, como um modelo E5 local. Nenhum modelo é
baixado pelo módulo; o arquivo precisa estar disponível no ambiente.

A recuperação vetorial exige que o texto da pergunta e dos trechos sejam
convertidos em embeddings normalizados. O score é o produto interno entre os
vetores e não substitui validação clínica.

O backend vetorial possui limites explícitos:

- Não possui mecanismo próprio de autorização ou autenticação.
- Não baixa modelos de um provedor externo.
- Não é instalado ou habilitado pela presença deste código.
- Não persiste índices vetoriais separados no SQLite.
- Não demonstra que o modelo E5 é adequado para uso clínico real.

## 4. Integração RAG

O demonstrador recupera somente registros previamente selecionados pelo paciente
e período. Em seguida:

1. Divide o texto em trechos com posições.
2. Recupera candidatos por BM25 ou embeddings E5.
3. Mantém a citação por `record_id`, paciente, data e intervalo de caracteres.
4. Entrega os trechos ao modelo ou retorna o modo extrativo sem inferência.
5. Valida que o modelo devolveu referências pertencentes ao contexto fornecido.

O RAG é usado para demonstrar recuperação no demonstrador sintético. Ainda não
constitui uma base clínica normativa autenticada, indexada e validada.

## 5. Escopo, privacidade e limites

- O banco normal não substitui controle de acesso da aplicação.
- Dados reais exigem autenticação, autorização por paciente e isolamento por
  workspace antes da consulta.
- A pseudonimização e a criptografia implementadas no extrator devem ser
  diferenciadas da criptografia completa do arquivo SQLite.
- O modelo RAG não pode alterar frequências calculadas pelo código nem inventar
  origem para uma citação.
- A avaliação de recuperacao mede ranking e abstenção; não comprova segurança
  clínica ou eficácia terapêutica.

## 6. Arquitetura alvo futura

O uso futuro de um banco vetorial embarcado, como `sqlite-vec`, ou de outro
índice local pode ser considerado para escala e recuperação densa. Essa decisão
depende de:

- Modelo e dimensão validados.
- Índice persistente e versão dos embeddings.
- Política de autorização e isolamento.
- Criptografia de dados em repouso.
- Licenças e proveniência dos documentos.
- Benchmark reprodutível de recuperação e abstenção.

Nenhuma dessas capacidades deve ser descrita como implementada enquanto estiver
apenas no plano de arquitetura.
