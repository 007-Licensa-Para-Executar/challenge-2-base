# Decisões consolidadas e validações pendentes - Equipe 007

Diário Emocional Inteligênte | 19/11/2026 | Versão 2.1

No PDF e no LaTeX, os itens entre colchetes aparecem em vermelho.


### 20.1. Definições adotadas na especificação v2.1

- Público inicial: profissionais de psicologia e pacientes jovens-adultos; adesão voluntária e transparência sobre o uso dos dados.
- Entrada: texto de até 2.400 caracteres, campos TCC opcionais, seleção de humor e status de tarefas; áudio transcrito localmente em memória e descartado após a transcrição.
- Privacidade: identificadores diretos removidos por regras locais; nomes, locais e instituições pseudonimizados consistentemente; UUID e tabela de associação cifrada mantida separada.
- Organização: seis macrotemas revisáveis, humor visual independente, extração ABC literal e subtemas com evidências localizáveis.
- Agentes: dois agentes locais — Agente 1 Extrator e Agente 2 Analista Longitudinal & Copiloto RAG — apoiados por cálculos determinísticos.
- Acesso: registro do paciente, análise privada da psicóloga e prontuário oficial em três camadas; sem compartilhamento ou resumo automático a terceiros.
- Limites: nenhuma saída diagnóstica, prescritiva, prognóstica, causal ou terapêutica; marcador textual passivo sem alerta externo.
- Consulta: janelas de 7, 14 e 30 dias; RAG híbrido BM25 + e5-small com RRF, citação documento/seção e abstenção abaixo do score especificado.

### 20.2. Validações técnicas e operacionais ainda necessárias

[Selecionar dataset, licença, processo de anotação e divisão de grupos; estabelecer baseline, métricas e critérios de aceite do classificador.]

[Definir versão exata do SBERT e dos LLMs locais, arquitetura e hiperparâmetros do MLP, runtime, hardware mínimo e plano de indisponibilidade.]

[Validar tamanho de trechos, implementação e calibração do limiar RAG, cobertura do corpus e testes de abstenção.]

[Formalizar autenticação, consentimento, permissões para compartilhar cada registro, retenção, backup, restauração e exclusão antes de qualquer piloto com dados reais.]

[Definir rubricas, perfis e tarefas de usabilidade, repetições, tolerância a falhas e metas mensuráveis de qualidade e desempenho.]

[Registrar responsáveis, aprovação de requisitos e evidências produzidas para cada versão do MVP.]

[Validar acompanhamento longitudinal sem diagnóstico ou tratamento automático entre sessões.]

[Avaliar mudanças temporais e comorbidades sem confundir diagnósticos ou alterar condutas clínicas.]

[Construir ou selecionar dados culturalmente nativos em português e auditar modelos abertos quanto a licença, proveniência e viés.]

[Testar diversidade de transtornos e abordagens terapêuticas, incluindo referências a DBT e terapia humanista, sem prescrição automatizada.]

