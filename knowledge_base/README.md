# Base de Conhecimento RAG do Agente 2

Este diretório contém os documentos curados para a recuperação aumentada por geração (RAG) do **Agente 2** do Projeto 007.

## Estrutura do Corpus

O arquivo [`corpus.jsonl`](corpus.jsonl) contém 13 blocos semânticos densos, divididos nas 5 coleções prioritárias:

1. `impacto_ia_bem_estar`: MIT Media Lab - ImpactBench (arXiv:2610.20690) e Resonance (AHs 2025).
2. `evidencias_psicossociais`: MIT Media Lab - Riscos de Interações Humano-IA (arXiv:2511.08880), JAMA Pediatrics, JMIR AI (Leung et al., 2026).
3. `digital_psychiatry_harvard`: Harvard Medical School / BIDMC (Dr. John Torous) sobre monitoramento inter-sessão e psiquiatria digital.
4. `pesquisa_brasil_usp`: ICMC-USP (PLN em saúde mental / SetembroBR) e Dissertação USP de tecnologias inclusivas.
5. `etica_governanca_cfp`: Resolução CFP nº 09/2024 e Lei Geral de Proteção de Dados (LGPD - Arts. 11 e 14).

## Metadados por Documento

Cada linha de `corpus.jsonl` segue a estrutura:
- `chunk_id`: Identificador único do trecho.
- `document_id`: Identificador do trabalho original.
- `collection`: Coleção lógica de pertinência temática.
- `title`: Título oficial.
- `authors`: Lista de autores.
- `institution`: Instituição de pesquisa / órgão regulador.
- `year`: Ano de publicação.
- `source_type`: Tipo de documento (benchmark, ensaio empírico, normativa, tese).
- `evidence_tier`: Nível epistêmico (`resultado_empirico_observado`, `associacao_sem_causalidade`, `recomendacao_normativa`, `modelo_de_risco_simulado`, `framework_conceitual`).
- `target_age_group`: Faixa etária alvo (ex.: `12-25` ou `geral`).
- `dimension_tags`: Tags temáticas associadas às dimensões do MIT ImpactBench.
- `methodology`: Resumo do método científico utilizado.
- `country_context`: País / contexto de aplicação.
- `section`: Seção de onde o fragmento foi extraído.
- `doi_or_url`: Link ou DOI oficial rastreável.
- `text`: Texto integral do bloco.
- `limitations`: Limitações expressas pelos autores.

## Princípios de Manutenção

- Nunca adicionar resumos de blogs ou fontes secundárias sem validação no texto original.
- Qualquer afirmação empírica deve conter suas respectivas limitações anexadas no mesmo chunk.
- Não incluir dados identificáveis de pacientes reais nesta base.
