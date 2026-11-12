# Referências Científicas e Técnicas Verificadas (Janela 2024–2026)

Este documento compila a base bibliográfica e de recursos que fundamentam a arquitetura, as fronteiras éticas e os algoritmos do projeto, em estrito atendimento ao **Requisito 8 (Ter pelo menos 1 resource como base de projeto com até dois anos)**.

Data de referência do projeto: **Novembro de 2026**. Todas as fontes listadas foram publicadas entre 2024 e 2026.

---

## 1. Evidências Médicas e Epidemiológicas de IA em Saúde Mental

### 1.1 Uso e Revelação de Sofrimento Psíquico a Chatbots de IA por Jovens
* **Referência:** McBain, Ryan K. et al. *AI Chatbot Use and Disclosure for Mental Health Among US Adolescents and Young Adults*. **JAMA Pediatrics**, 2026.
* **DOI / Link:** [10.1001/jamapediatrics.2025.5940](https://jamanetwork.com/journals/jamapediatrics/fullarticle/2849307)
* **Contribuição para o Projeto:** Demonstra que adolescentes e jovens adultos recorrem em massa a bots de IA para desabafar sentimentos de dor, ideação e sofrimento que não contam a amigos ou familiares. Justifica a necessidade urgente de um **diário digital assistido** que canalize com segurança esses relatos para psicólogos humanos, em vez de deixar os jovens à mercê de modelos de bate-papo sem supervisão.

### 1.2 Aconselhamento de Saúde Mental por IA Generativa
* **Referência:** McBain, Ryan K. et al. *Use of Generative AI for Mental Health Advice Among US Adolescents and Young Adults*. **JAMA Network Open**, v. 8, e2541067, nov. 2025.
* **DOI / Link:** [10.1001/jamanetworkopen.2025.41067](https://jamanetwork.com/journals/jamanetworkopen/fullarticle/2841067)
* **Contribuição para o Projeto:** Analisa a prevalência de conselhos de saúde mental solicitados à IA, alertando para a heterogeneidade da acurácia e o risco de recomendações inadequadas. Fundamenta nossa decisão arquitetural de **proibir respostas interventivas automáticas ao paciente**, mantendo o sistema como copiloto para o terapeuta.

### 1.3 Telessaúde e Tratamento de Saúde Mental
* **Referência:** Breslau, Joshua; Burnett, Alyssa; Baker, Olesya; McBain, Ryan K. et al. *Telehealth Use for Mental Health Treatment Among US Adolescents*. **Journal of Adolescent Health (ScienceDirect)**, v. 77, n. 2, p. 277–283, ago. 2025.
* **DOI / Link:** [10.1016/j.jadohealth.2025.03.025](https://www.sciencedirect.com/science/article/abs/pii/S1054139X26001151)
* **Contribuição para o Projeto:** Mostra a rápida expansão da telessaúde e de ferramentas digitais como suporte às consultas remotas e presenciais, embasando a viabilidade operacional do nosso painel clínico.

### 1.4 Sentimentos e Valores de Usuários em Conversas de Saúde Mental com LLMs
* **Referência:** Li, Lingyao; Huang, Xiaoshan; Ma, Renkai; Zhang, Ben Zefeng; Wu, Haolun; Yang, Fan; Chen, Chen. *LLM Use for Mental Health: Crowdsourcing Users' Sentiment-based Perspectives and Values from Social Discussions*. **arXiv preprint arXiv:2512.07797**, 2024/2025.
* **DOI / Link:** [arXiv:2512.07797](https://arxiv.org/pdf/2512.07797)
* **Contribuição para o Projeto:** Mapeia empiricamente sentimentos e valores de usuários em comunidades online (Reddit, fóruns de saúde mental) ao interagirem com LLMs (ChatGPT, Pi, Character.ai). Evidencia que o desabafo atende a uma necessidade de catarse imediata, mas a ausência de um profissional acarreta riscos de isolamento e alucinações. Dá sustentação ao princípio de **Value-Sensitive Design (VSD)** incorporado em nossa ferramenta.

---

## 2. Síntese de Personas e Avaliação Psicológica Simulada

### 2.1 PsychAdapter: Adaptação de Transformers para Traços e Saúde Mental
* **Referência:** Human Language Analysis Beings (HLAB). *PsychAdapter: Adapting LLM Transformers to Reflect Traits, Personality and Mental Health*. **npj Artificial Intelligence (Nature Portfolio) / arXiv**, 2024/2025.
* **Repositório:** [https://github.com/humanlab/psychadapter](https://github.com/humanlab/psychadapter)
* **Contribuição para o Projeto:** Apresenta uma metodologia para sintetizar perfis e comportamentos psicológicos realistas controlando os traços do Big Five e indicadores de depressão/ansiedade através de adaptadores e projeções eficientes. É o fundamento técnico para gerarmos os **datasets sintéticos de diários** usados no treino da Rede Neural MLP e no teste dos agentes, contornando qualquer violação de privacidade de pacientes reais.

### 2.2 Modelos de Linguagem em Avaliação Psicológica Simulada
* **Referência:** Mallon, Ciara; Ennis, Edel et al. *Using Large Language Models in Simulated Mental Health Assessment*. **Ulster University Research Portal (Pure) / Conference & Review Series**, 2024–2026.
* **Link:** [Ulster University Pure Portal](https://pure.ulster.ac.uk/en/publications/using-large-language-models-in-simulated-mental-health-assessment/)
* **Contribuição para o Projeto:** Estabelece parâmetros de validação para simulações clínicas e o uso de Retrieval-Augmented Generation (RAG) para modelar históricos longitudinais de pacientes e subsidiar a prática profissional em ambientes seguros.

---

## 3. Interfaces de Avaliação e Eixos de Impacto Humano

### 3.1 MIT ImpactBench: Advancing Humans with AI
* **Referência:** MIT Media Lab (AHA Program), UC Berkeley Haas & USC Marshall. *ImpactBench: Evaluating Generative AI on Human Well-Being*. 2025/2026.
* **Plataforma Interativa:** [https://impactbench.media.mit.edu/explore](https://impactbench.media.mit.edu/explore)
* **Contribuição para o Projeto:** Paradigma visual e conceitual de nossa interface. O ImpactBench substitui benchmarks genéricos de código por métricas holísticas de bem-estar humano divididas nos eixos **Psicológico**, **Físico/Segurança** e **Social**. Adotamos sua filosofia de **rastreabilidade total até as transcrições primárias**, permitindo ao psicólogo navegar dos indicadores de alto nível até a citação literal proferida pelo paciente.

---

## 4. Arquiteturas Multiagente e Diários Assistidos

### 4.1 Resonance: Reflexão Aumentada por Memórias
* **Referência:** Zulfikar, W.; Chiaravalloti, T.; Shen, J.; Picard, Rosalind; Maes, Pattie. *Resonance: Drawing from Memories to Imagine Positive Futures through AI-Augmented Journaling*. **Proceedings of the Augmented Humans International Conference (AHs '25)**, p. 199–215, 2025. DOI: 10.1145/3745900.3746099.
* **Contribuição:** Precedente de sucesso no uso de diários assistidos por IA para resgatar memórias e promover bem-estar emocional reflexivo.

### 4.2 DSM5AgentFlow e Redes Multiagente Explicáveis
* **Referência:** Ozgun, M. C. et al. *Trustworthy AI Psychotherapy: Multi-Agent LLM Workflow for Counseling and Explainable Mental Disorder Diagnosis*. **Preprint**, 2025.
* **Contribuição:** Demonstração da cooperação entre múltiplos agentes para auditoria mútua de passos analíticos, base para a comunicação sequencial entre nosso Agente Extrator e Agente Correlacionador.

### 4.3 Systematic Review de LLMs em Saúde Mental
* **Referência:** Leung, Janni et al. *Generative Large Language Models in Mental Health Care Settings: Systematic Review and Meta-Analysis*. **JMIR AI**, v. 5, e87730, 2026. DOI: 10.2196/87730.
* **Contribuição:** Reitera a importância de tarefas delimitadas, supervisão constante e avaliação rigorosa de modos de falha em aplicações de saúde mental.

---

## 5. Governança e Gestão de Riscos

### 5.1 NIST AI Risk Management Framework (AI RMF)
* **Referência:** National Institute of Standards and Technology. *Artificial Intelligence Risk Management Framework (AI RMF 1.0 / Atualizações 2026)*.
* **Contribuição:** Estruturação dos quatro pilares de governança (Mapear, Medir, Gerenciar e Governar), balizando o tratamento de inputs dos pacientes como dados não-confiáveis e a exigência de explicabilidade e rastreabilidade algorítmica.
