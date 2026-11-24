# Decisões da Equipe 007 - Licensa para Executar

Diário Emocional Inteligênte | 06/11/2026 | Versão 1.0

No PDF e no LaTeX, os itens entre colchetes aparecem em vermelho.

As perguntas abaixo são o roteiro de discussão. Cada item em vermelho deve ser substituído por uma decisão registrada quando houver acordo. As prioridades indicam dependências, não uma aprovação prévia das alternativas. O registro mínimo de resposta é: escolha, justificativa, responsável, data e requisitos afetados.

### 20.1. Decisões que desbloqueiam rede e RAG

[DEC-04 - Taxonomia: quais são exatamente os temas gerais? Serão oito? Como diferenciar Família, Relacionamentos e Interação social? Haverá outros e não identificado? Produzir definições e exemplos de fronteira.]

[DEC-05 - Quantidade de temas: cada entrada recebe um tema principal, até dois ou até três? Qual unidade será classificada: diário inteiro ou trecho? Como tratar ambiguidade e nenhum tema suficientemente sustentado?]

[DEC-06 - Dados: qual base, versão e licença serão usadas? Quais classes e quantidades existem? Usaremos apenas sintéticos nesta etapa? Como separar grupos semelhantes entre treino, validação e teste?]

[DEC-07 - Referências: quem ou o que produz os rótulos? Haverá alguma revisão independente? Como resolver desacordo e registrar supervisão fraca sem apresentar suas métricas como validação real?]

[DEC-08 - Construção do zero: o que os mentores exigem implementar manualmente? NumPy será permitido? Precisamos demonstrar derivadas e gradientes, treinamento completo ou apenas arquitetura e experimento inicial nesta entrega?]

[DEC-09 - Experimentos neurais: TF-IDF ou embedding? Quais tamanhos, camadas, perda, otimizador e regra de parada? Qual baseline? Aprovar uma configuração inicial e uma comparação pequena, alterando fatores controladamente.]

[DEC-12 - Base RAG: quais perguntas profissionais queremos responder? Quais documentos completos e materiais metodológicos serão admitidos? Quem verifica origem, atualidade e direitos de uso? Qual é o uso estritamente informativo de materiais de TCC?]

[DEC-13 - Recuperação: quais baselines e embedding comparar? Qual tamanho de trecho, sobreposição, top-k e regra de insuficiência? Graphify ficará fora do primeiro experimento ou terá hipótese e orçamento definidos?]

[DEC-21 - Avaliação: quais métricas e limites determinam sucesso? Qual conjunto ficará reservado? Quantas repetições? Onde usar verificações por código, revisão humana ou LLM juiz? Como registrar incerteza e resultados parciais?]

[DEC-23 - Entrega: o que precisa estar executável em 13/11/2026? Quais demonstrações, pesquisa, dados, treino e testes serão apresentados? Quem confirma os critérios acadêmicos sobre agentes, API e resource?]

### 20.2. Decisões de funcionamento do produto

**DEC-10 (decidido):** adotar dois agentes. O Agente 1 organiza subtemas e evidências; o Agente 2 calcula a síntese longitudinal e, no modo briefing, consulta fontes autorizadas. A colaboração será demonstrada pela troca de documentos tipados e validados pelo barramento.

[DEC-11 - Execução: quais modelos e ferramentas de orquestração/rastreamento? Tudo local ou algum serviço externo explicitamente escolhido? Qual comportamento sem internet, sem modelo ou com memória insuficiente?]

[DEC-14 - Subtemas: qual recorrência e janela justificam criação automática? Como renomear, unir e rejeitar? Como preservar correções em reprocessamentos? Qual é a unidade das contagens e o efeito sobre gráficos antigos?]

[DEC-15 - Tempo: qual data e fuso comandam os filtros? Qual período inicial? Como tratar data desconhecida e expressões como recentemente? Quem marca assunto como encerrado e o que muda nas buscas?]

[DEC-16 - Autonomia: quais leituras, organizações e gravações são automáticas? Quais precisam de confirmação ou desfazer? Quais limites de passos, tentativas, tempo e custo? O que fazer se apenas parte de uma tarefa for concluída?]

[DEC-17 - Ambiente: aplicativo desktop ou outra forma de entrega? Quais sistemas operacionais? Como serão pastas, banco, índice, formatos, limites de anexos e sincronização? Quais arquivos a profissional poderá editar fora do app?]

[DEC-18 - Proteção e ciclo de vida: como autenticar acesso, proteger dados e backups, restaurar, reter e excluir? Quais logs são permitidos? Quais avaliações profissionais e jurídicas serão necessárias antes de trabalhar com dados reais?]

[DEC-19 - Voz e imagem: quais formatos e serviços de transcrição/OCR? Como sinalizar incerteza e revisar texto extraído? Por quanto tempo conservar áudios e imagens? Qual parte entra já no MVP?]

[DEC-20 - Qualidade: qual equipamento de referência, volume de registros, tempo de resposta e taxa de sucesso esperados? Como avaliar redução de esforço e acessibilidade com tarefas observáveis?]

[DEC-22 - Dashboard: pizza por tema principal, distribuição de atribuições ou barras para múltiplos temas? Como apresentar denominadores, fontes, origem automática e edição? Quais critérios de responsividade e acessibilidade?]

### 20.3. Identidade, participantes e governança

[DEC-01 - Identidade: qual será o nome definitivo de [AGENT-NAME]? Qual linguagem e identidade visual representam a Equipe 007 sem prometer competências que o produto não possui?]

[DEC-02 - Público: para qual perfil de profissional e faixa etária dos pacientes o produto será desenhado? Qual contexto de atendimento e quais limites do piloto?]

[DEC-03 - Entrada do paciente: como o diário será enviado? Haverá interface própria? O que o paciente poderá consultar, editar ou excluir, além de não ter acesso aos temas profissionais?]

[DEC-24 - Equipe: quais integrantes assumem dados, rede, RAG, interface, integração e avaliação? Quem aprova requisitos? Onde registrar decisões e como fechar a versão validada deste documento?]

