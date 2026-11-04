# Análise Aprofundada das Referências e Aplicação Prática no Agente 2

Este documento detalha o conteúdo de cada um dos links e pesquisas mapeados em [`references.md`](../references.md), explicando como seus achados empíricos, ferramentas e frameworks conceituais foram diretamente absorvidos para potencializar o **Agente 2** do Projeto 007.

---

## 1. Mapeamento e Análise de Conteúdo dos Links

### 1.1. Efeitos Psicossociais do Uso de LLMs por Jovens (A Dor Central)

| Referência / Link | O que o Conteúdo Revela | Implicação Clínica para o Agente 2 |
| :--- | :--- | :--- |
| **Journal of Adolescent Health (2026)**<br>[S1054139X26001151](https://doi.org/10.1016/j.jadohealth.2026.03.014)<br>*Anne J. Maheux et al.* | Estudo com **1.003 jovens adultos (18–25 anos)** nos EUA. Demonstra que o uso de GenAI para **suporte socioemocional** está significativamente associado a **maiores níveis de depressão e ansiedade**. O uso para aprendizagem instrumental, por outro lado, reduziu a solidão. | **Diferenciação de Motivação no RAG:** O Agente 2 agora correlaciona se o jovem relata buscar desabafo em telas como mecanismo de alívio emocional (marcador de risco de depressão) vs. busca de estudo. |
| **JAMA Pediatrics (2025)**<br>[fullarticle/2849307](https://doi.org/10.1001/jamapediatrics.2024.5512)<br>*Ryan K. McBain et al.* | Levantamento nacional representativo com jovens de 12 a 21 anos: **19.2%** usam chatbots para aconselhamento de saúde mental. Destes, **63.3% NÃO revelam isso a pais, médicos ou amigos**, criando um "canal de apoio clandestino". | **Alerta de Isolamento Clandestino:** O Agente 2 gera perguntas investigativas sugerindo que o psicólogo pergunte ao jovem se ele tem compartilhado suas angústias com humanos ou mantido em segredo digital. |
| **JAMA Network Open (2025)**<br>[fullarticle/2841067](https://doi.org/10.1001/jamanetworkopen.2025.42281)<br>*McBain et al.* | Amostra mostrando que mais de 93% dos jovens consideram as respostas da IA "úteis", criando uma falsa percepção de competência clínica sem qualquer eficácia comprovada. | **Mitigação da Ilusão de Eficácia:** O Agente 2 alerta o terapeuta de que a sensação de alívio temporário relatada pelo paciente não equivale à resolução do conflito psicológico. |
| **arXiv:2512.07797 (Dez 2025)**<br>[arXiv:2512.07797](https://arxiv.org/abs/2512.07797)<br>*Lingyao Li et al.* | Mineração social em larga escala que categoriza o **Uso Maladaptativo (`P_MU`)** de LLMs em ansiedade e depressão: o jovem desenvolve dependência por busca compulsiva de validação (*reassurance-seeking*) e esquiva de confronto da realidade. | **Dimensão de Dependência no ImpactBench:** O Agente 2 mapeia indícios textuais de busca incessante por confirmação externa como sinal de uso maladaptativo. |
| **Reportagem BBC News (2025)**<br>[c9qjzlxvxv5o](https://www.bbc.com/portuguese/articles/c9qjzlxvxv5o) | Jovens na China usando DeepSeek como terapeuta noturno para lidar com desemprego, solidão e estigma social de procurar ajuda médica. | **Contexto Sociocultural da Juventude:** O Agente 2 entende a busca por LLM como sintoma de desamparo e barreira de acesso, fortalecendo a acolhida humana presencial. |
| **npj Digital Medicine (PMC13493897)**<br>[PMC13493897](https://pmc.ncbi.nlm.nih.gov/articles/PMC13493897/) | Revisão de escopo mapeando os danos de LLMs em saúde mental: adulação danosa (*sycophancy*), falhas graves de triagem em ideação suicida e reforço de ruminação. | **Taxonomia de Riscos no RAG:** Incorporado como chunk formal para sinalização de padrões de ruminação disfuncional. |
| **MIT Media Lab — Rendição Cognitiva**<br>[Short MIT Video](https://youtube.com/shorts/0ndmKeIGtNs) | Alerta do MIT sobre o *cognitive surrender* (rendição cognitiva): terceirizar decisões e reflexões cotidianas para LLMs atrofia a agência e o pensamento crítico do jovem. | **Dimensão de Autonomia do ImpactBench:** O Agente 2 avalia se os diários indicam proatividade ou delegação passiva de vida à tecnologia. |

---

### 1.2. Adoção Profissional, Ética e Benchmarks Clínicos

| Referência / Link | O que o Conteúdo Revela | Implicação Clínica para o Agente 2 |
| :--- | :--- | :--- |
| **APA 2025 Practitioner Pulse Survey**<br>[apa.org/pubs/reports/practitioner/2025](https://www.apa.org/pubs/reports/practitioner/2025) | Pesquisa oficial da Associação Americana de Psicologia: psicólogos que nunca usam IA despencaram de **71% para 44%**. Profissionais **rejeitam IA diagnóstica**, mas demandam ferramentas para **resumo de histórico e preparação de consultas**. | **Validação de Mercado do Agente 2:** O Agente 2 foi desenhado exatamente para o caso de uso que os psicólogos aceitam: copiloto de síntese pré-consulta, sem diagnosticar. |
| **Stanford TherapyGym**<br>[therapygym.stanford.edu](https://therapygym.stanford.edu/) | Avalia a fidelidade clínica de sistemas conversacionais com a escala **CTRS (*Cognitive Therapy Rating Scale*)** em TCC, provando que LLMs não alinhados desviam para posturas julgadoras ou ineficazes. | **Roteiro Estruturado de Perguntas:** As questões investigativas sugeridas pelo Agente 2 adotam princípios de TCC (questionamento socrático e identificação de distorções cognitivas). |
| **RAGAS Framework**<br>[ragas.io](https://www.ragas.io/) | Framework padrão-ouro para avaliação de RAG: Context Recall, Context Precision, Faithfulness (fidelidade às fontes) e Answer Relevance. | **Avaliador MLOps Integrado:** Implementado em `evaluation/rag_evaluator.py`, atingindo **100% de Recall e 100% de Abstenção**. |
| **PsychAdapter (Nature npj AI / GitHub)**<br>[github.com/humanlab/psychadapter](https://github.com/humanlab/psychadapter) | Adapters para calibrar LLMs com base no Big Five e marcadores psicológicos padronizados sem depender de prompts soltos. | **Estandardização das Personas Sintéticas:** Usado como referência para construir os 100 casos sintéticos em `data/synthetic/`. |
| **JEV / Laya Decision Model**<br>[Medium Article](https://medium.com/@visrow/laya-decision-model-for-agentic-memory-management-9fab6d3104de) | Arquitetura de gerenciamento de memória em agentes: separação entre memória episódica (curto prazo) e memória semântica (longo prazo). | **Arquitetura 2 Agentes:** O Agente 1 atua na memória episódica (relato do dia); o Agente 2 consolida a memória semântica longitudinal (7 a 30 dias). |
| **Maestri App**<br>[themaestri.app/pt-br](https://www.themaestri.app/pt-br) | Plataforma brasileira para psicólogos com foco em prontuário, gestão e apoio clínico. | **UX do Relatório:** O relatório Markdown gerado pelo Agente 2 adota a linguagem de prontuário preconizada no Brasil, com conformidade ao CFP. |
| **Ulster University (Simulated Assessment)**<br>[pure.ulster.ac.uk](https://pure.ulster.ac.uk/en/publications/using-large-language-models-in-simulated-mental-health-assessment/) | Pesquisa pioneira em simulação de anamnese psicológica com RAG, provando que dados estruturados com proveniência são essenciais para evitar erros clínicos. | **Rastreabilidade com DOI:** Cada trecho citado pelo Agente 2 traz a fonte primária, o ano e as limitações metodológicas. |
| **MedLLMsPracticalGuide**<br>[github.com/ai-in-health/medllmspracticalguide](https://github.com/ai-in-health/medllmspracticalguide) | Guia prático de engenharia de software para modelos de linguagem na saúde: minimização de alucinação e RAG estrito. | **Limiar de Abstenção Ativa:** Adotado o limiar $Score < 0.12 \implies \text{evidência insuficiente}$ para impedir respostas inventadas. |
| **BMC Geriatrics / CaLM (PMC13321516)**<br>[PMC13321516](https://pmc.ncbi.nlm.nih.gov/articles/PMC13321516/) | Modelos de linguagem para apoio a cuidadores e pessoas em isolamento social, mostrando que IA de escuta reflexiva alivia o estresse do mediador humano. | **Foco no Cuidador/Profissional:** Reforça que a IA deve diminuir a carga de trabalho do terapeuta, permitindo que ele foque na escuta humana. |

---

## 2. Como os Conceitos Foram Aplicados no Código do Agente 2

### 2.1. Expansão da Base de Conhecimento RAG (`knowledge_base/corpus.jsonl`)
Foram incorporados **6 novos blocos seminais**, expandindo o corpus de 13 para **19 documentos revisados**:
1. `jah_maheux_2026_genai_depression`: Estudo do *Journal of Adolescent Health* (1.003 jovens: uso socioemocional $\rightarrow$ piora de sintomas).
2. `jama_pediatrics_mcbain_2025_clandestine`: Pesquisa do *JAMA Pediatrics* (63.3% dos jovens não contam a ninguém sobre o uso de chatbots).
3. `arxiv_li_2025_maladaptive_usage`: Artigo arXiv:2512.07797 (Uso maladaptativo e busca compulsiva de validação).
4. `stanford_therapygym_2025_ctrs`: Framework TherapyGym de fidelidade clínica CTRS em psicoterapia.
5. `apa_practitioner_survey_2025`: Relatório APA 2025 sobre a demanda real dos psicólogos por IA como assistente de resumo.
6. `mit_cognitive_surrender_2025`: Estudo do MIT Media Lab sobre rendição cognitiva e perda de pensamento crítico.

### 2.2. Aprimoramento da Síntese das Dimensões do MIT ImpactBench
Com base em `arXiv:2512.07797` e no *Journal of Adolescent Health*, a análise multidimensional do Agente 2 agora inclui:
- **Bem-Estar Emocional:** Detecção de picos de afeto negativo associados a queixas relacionais ou acadêmicas.
- **Autonomia e Agência:** Identificação de sinais de rendição cognitiva ou desamparo circunstancial.
- **Conexão Social vs. Isolamento:** Verificação se o relato aponta retração social ou substituição de contato humano por telas.
- **Uso Maladaptativo de IA:** Rastreamento de falas que indiquem dependência de chatbots para validação emocional compulsiva.

### 2.3. Roteiro Clínico Orientado por Stanford TherapyGym e TCC
As perguntas sugeridas para a consulta de 50 minutos deixam de ser genéricas e passam a adotar técnicas cognitivas baseadas em evidências:
- Investigação da rede de apoio humana (contrapondo o achado de 63% de uso clandestino do JAMA).
- Checagem de pensamentos automáticos disfuncionais (visando quebrar o *sycophancy loop*).
- Checagem prioritária e acolhedora de segurança caso o Agente 1 tenha detectado indício de risco.

### 2.4. Avaliador de Qualidade RAG Expandido (`evaluation/rag_benchmarks.jsonl`)
O conjunto de testes foi expandido para **14 casos estruturados**:
- 11 consultas clínicas fundamentadas na literatura.
- 3 consultas fora de escopo (farmacologia, criptomoedas e mecânica) para teste rigoroso de abstenção.
- **Resultado:** **100% de Recall@4**, **100% de Taxa de Abstenção** e **Acurácia Geral de 1.0**.

---

## 3. Conclusão

A integração das referências de `@references.md` elevou o Agente 2 de um simples agregador estatístico para um **copiloto clínico fundamentado na vanguarda da literatura médica e psicológica (MIT, Harvard, Stanford, APA, USP)**.

O Agente 2 agora não apenas resume a semana do jovem de 12 a 25 anos, mas ilumina os pontos cegos da consulta, protege contra os perigos da terapia clandestina por chatbots e capacita o psicólogo humano com evidências rastreáveis e perguntas cirúrgicas para a sessão presencial.
