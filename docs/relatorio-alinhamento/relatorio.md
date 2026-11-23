# Diário Emocional Inteligênte

**Equipe 007 - Licensa para Executar | Especificação de requisitos, conformidade ético-legal e arquitetura de referência | Versão 2.1 | 19/11/2026**

A Equipe 007 apresenta o Diário Emocional Inteligênte, uma aplicação de apoio à captação e organização de relatos entre sessões para profissionais de psicologia, com foco inicial em pacientes jovens-adultos. O produto combina registros do paciente, análise privada da psicóloga e prontuário oficial em camadas separadas. A identidade visual não constitui promessa de sigilo técnico ou de competência clínica.

Esta versão consolida a Especificação de Requisitos v2.1 e o documento “Diário Emocional Inteligente — Insights Clínicos e Evolução da Arquitetura de Agentes”, além das decisões de produto neles registradas. Ela descreve o comportamento pretendido e não declara funcionalidades implementadas nem resultados de avaliação já obtidos. Requisitos definidos pelas fontes são apresentados como referência; escolhas técnicas ainda não fechadas e critérios quantitativos a validar aparecem em vermelho e entre colchetes.

## 1. Propósito, problema e objetivos

O acompanhamento entre sessões chega ao consultório de forma fragmentada: datas, horários, acontecimentos fora da rotina e combinados podem se perder, e o paciente pode lembrar de situações importantes apenas na sessão seguinte. O produto propõe captar relatos voluntários de jovens-adultos, organizá-los em um workspace isolado por paciente e período e apoiar a preparação de pautas descritivas com acesso ao texto original.

O sistema facilita a consulta longitudinal, a organização de temas e subtemas, o acompanhamento de tarefas combinadas entre sessões e a recuperação de fontes normativas autorizadas. Saídas automatizadas são sugestões descritivas revisáveis; interpretação e decisão clínica permanecem exclusivamente com a psicóloga.

| Objetivo | Resultado esperado | Como verificar |
| --- | --- | --- |
| OBJ01 - Captar e localizar relatos | Reunir registros entre sessões em workspace isolado por paciente e período | Busca nos intervalos de 7, 14 e 30 dias, com acesso ao texto original |
| OBJ02 - Estruturar registros | Organizar relatos em seis macrotemas, subtemas, modelo ABC e humor por cores | Esquema válido, trechos literais localizados e revisão humana preservada |
| OBJ03 - Apoiar acompanhamento longitudinal | Comparar janelas temporais, acompanhar tarefas e produzir pauta descritiva | Cálculos determinísticos, coocorrências factuais e validação profissional |
| OBJ04 - Proteger e rastrear informações | Separar camadas documentais e ancorar consultas em fontes autorizadas | Isolamento por camada, pseudonimização e citações verificáveis |
| OBJ05 - Sustentar rigor acadêmico | Construir e avaliar classificador, RAG e dois agentes locais | Experimentos reproduzíveis e rastreabilidade MLOps |

A pesquisa de campo reportada nas fontes de requisitos reúne seis profissionais de psicologia (R1 a R6); seus achados orientam a concepção, mas não demonstram eficácia. A leitura profissional em menos de dois minutos é um objetivo de UX a validar. Não há alegação de melhora clínica, diagnóstico ou eficácia terapêutica do produto.

## 2. Identidade, atores e fronteiras

A autoria institucional é da **Equipe 007 - Licensa para Executar**. O produto se chama **Diário Emocional Inteligênte**. A aplicação destina-se à psicóloga e a pacientes jovens-adultos, com adesão voluntária e transparência sobre o tratamento dos dados.

| Ator | Responsabilidade no produto | Limite |
| --- | --- | --- |
| Psicóloga | Consultar relatos, revisar sugestões, registrar notas privadas e validar evolução de prontuário | Única responsável pela interpretação clínica; autoria humana sempre identificada |
| Paciente jovem-adulto | Registrar relatos voluntários, escolher o que compartilhar, informar humor e acompanhar tarefas | Não vê a análise privada nem temas/subtemas internos; pode acessar o prontuário oficial conforme as regras aplicáveis |
| Agente 1 — Extrator | Estruturar cada relato com evidências literais | Não conversa com o paciente, não interpreta função de comportamento e não diagnostica |
| Agente 2 — Analista longitudinal e copiloto RAG | Produzir sínteses factuais, rascunhos revisáveis e briefings normativos | Não estabelece causalidade, não diagnostica e não fala com o paciente |
| Equipe 007 e orientação | Desenvolver, avaliar e validar requisitos acadêmicos | Não substituem revisão profissional nem análise jurídica |

O paciente controla voluntariamente quais registros compartilha com a psicóloga. O acesso a registros originais, análises privadas e prontuário oficial segue as três camadas descritas na seção 10; não há envio ou resumo automático para terceiros.

É vedada a emissão automatizada de diagnóstico, prognóstico, prescrição, recomendação terapêutica ou inferência clínica. O sistema não envia alertas externos autônomos. Materiais de TCC podem ser consultados apenas para apoio informativo autorizado; não autorizam o agente a formular condutas clínicas. As fontes ético-profissionais e legais de referência estão listadas na seção 21 (F14–F18).

## 3. Escopo do produto e da entrega acadêmica

O escopo consolidado reúne diário voluntário com texto livre (limite de 2.400 caracteres), campos TCC opcionais, seleção de humor, tarefas combinadas, pseudonimização local, seis macrotemas, extração ABC, análise longitudinal e consulta RAG normativa. As capacidades são requisitos-alvo; sua menção não afirma que estejam implementadas.

| Horizonte | Conteúdo | Evidência necessária |
| --- | --- | --- |
| Especificação v2.1 | Requisitos, limites ético-legais, arquitetura de dois agentes locais e camadas documentais | Rastreabilidade entre fontes, requisitos e critérios de aceite |
| MVP integrado | Fluxo local com pseudonimização, registro, extração, classificação, tarefas e consulta longitudinal/RAG | Testes ponta a ponta com dados fictícios, isolamento e falhas explícitas |
| Evolução do produto | Interface acessível, leitura pré-consulta rápida, edição e prontuário validado | Avaliações técnicas, de usabilidade e revisão profissional |

As demonstrações acadêmicas devem utilizar dados fictícios. O uso de dados reais depende de controles de segurança, consentimento informado e revisão profissional e jurídica antes de qualquer piloto.

As restrições acadêmicas compreendem dois agentes colaborando, base de conhecimento, MLOps, rede neural construída e avaliada, API utilizada pelos agentes, versionamento, ética, explicabilidade e MVP funcional. A demonstração deve distinguir requisito, implementação e evidência obtida.

## 4. Elicitação e organização das decisões

Os requisitos incorporam a pesquisa qualitativa reportada com seis psicólogos e um parecer técnico-regulatório descrito nas fontes. Esses materiais orientam o desenho, mas não substituem validação contínua com profissionais, análise jurídica ou consentimento informado.

Os pontos ainda sujeitos a validação são a escolha exata de modelos e versões, dataset e licença, metas de avaliação, limites de segurança operacional e fluxos de consentimento e acesso. Exemplos de desenvolvimento devem ser fictícios.

Requisitos RF descrevem funções; RNF descrevem qualidades; RB descrevem regras de negócio; CA descrevem critérios de aceite. Alterações de taxonomia, modelo ou política de contagem devem gerar novas versões e indicar o impacto em resultados anteriores.

As escolhas consolidadas e as validações restantes estão resumidas na seção 20.

## 5. Jornadas de uso

### 5.1. Abrir o contexto de uma pessoa

A profissional pode começar no modo geral e solicitar a abertura de um paciente. O sistema resolve o cadastro por identificador e dados autorizados. Quando houver homônimos ou ambiguidade, apresenta opções antes de acessar os registros. Ao entrar no projeto, mostra explicitamente a pessoa selecionada e o período da consulta.

Dentro de um projeto, a profissional cria novas conversas ou retoma conversas anteriores. As mensagens pertencem à conversa; arquivos e registros pertencem ao projeto. Criar um novo chat não apaga nem duplica o histórico documental do paciente. Consultas gerais, como recebimentos recentes, podem reunir metadados dos pacientes autorizados sem misturar seus relatos em uma única síntese pessoal.

### 5.2. Registrar um relato por texto ou voz

A paciente registra voluntariamente um relato de até 2.400 caracteres, pode preencher campos estruturados opcionais inspirados em TCC, selecionar uma cor de humor e marcar tarefas combinadas. Entradas maiores são recusadas explicitamente, sem truncamento silencioso. O paciente decide quais entradas compartilhar.

Microperguntas opcionais podem ajudar a iniciar o relato sem induzir respostas nem exigir preenchimento de campos estruturados.

Para áudio, a transcrição ocorre localmente em memória e o arquivo de voz é descartado após o processamento. Texto original permanece preservado; a IA não o sobrescreve. A camada de processamento cria uma cópia pseudonimizada antes de encaminhar conteúdo aos modelos locais. Falhas e incertezas devem ser explícitas.

### 5.3. Explorar temas e subtemas

O dashboard apresenta assuntos identificados nos registros do período. A psicóloga pode navegar de tema para subtema e abrir as entradas que sustentam a organização. Subtemas gerados automaticamente ficam disponíveis para edição; correções, renomeações e uniões mantêm histórico. O paciente não visualiza essa classificação no produto.

### 5.4. Consultar e agir pelo chat

A psicóloga consulta registros em janelas de 7, 14 ou 30 dias, acompanha tarefas e solicita sínteses factuais ou briefings normativos. O Agente 2 aponta trechos e fontes, abstém-se quando a evidência é insuficiente e nunca converte coocorrência em causalidade. Rascunhos de evolução só passam ao prontuário oficial após revisão, edição e validação explícita da psicóloga.

## 6. Requisitos funcionais

| ID | Comportamento requerido | Critério de aceite associado |
| --- | --- | --- |
| RF01 | Manter workspace isolado por paciente, com UUID estável e anamnese restrita fora do pipeline de IA | CA01: homônimos não se misturam e dados de anamnese não chegam aos prompts |
| RF02 | Receber relato de até 2.400 caracteres, campos TCC opcionais e cor de humor, aplicando pseudonimização local | CA02: excesso é recusado sem truncamento; Regex/NER substituem identificadores localmente |
| RF03 | Sugerir seis macrotemas com MLP próprio e representar humor em dimensão visual separada | CA03: tema é sugestão revisável; humor não aparece como macrotema |
| RF04 | Extrair situação, pensamento, sentimento, comportamento e consequência (ABC), de 1 a 6 subtemas, polaridade e indícios textuais de atenção com citação literal | CA04: toda citação corresponde ao original e toda saída inválida é rejeitada |
| RF05 | Gerenciar status de tarefas combinadas e timeline por janelas temporais | CA05: estado e contagens são determinísticos nas janelas de 7, 14 e 30 dias |
| RF06 | Produzir sínteses longitudinais, rascunhos de evolução e briefings RAG com o Agente 2 | CA06: sem causalidade/diagnóstico; fonte com score mínimo de 0,70 citada por documento e seção, ou abstenção |
| RF07 | Isolar registro do paciente, análise privada da psicóloga e prontuário oficial em três camadas | CA07: análise e rascunhos não validados nunca aparecem no prontuário |
| RF08 | Oferecer interface acessível, escaneável e com leitura profissional pré-consulta em menos de dois minutos | CA08: teclado, alto contraste e tipografia ampliada disponíveis; identidade visual personalizável |

Os critérios são requisitos de aceite, não resultados já obtidos. O desenho prevê adesão voluntária, seleção dos registros compartilhados e ausência de módulo de envio ou resumo automático para terceiros.

## 7. Regras do produto e requisitos de qualidade

| ID | Regra ou qualidade | Evidência de verificação |
| --- | --- | --- |
| RB01 | Vedação a diagnóstico, prognóstico, prescrição, recomendação terapêutica ou inferência clínica automatizada | Pedidos dessa natureza recebem delimitação de escopo e resposta descritiva |
| RB02 | Registros do paciente, análise privada e prontuário oficial permanecem em três camadas sem compartilhamento externo automático | Testes de autorização confirmam isolamento e revisão humana antes de validação do prontuário |
| RB03 | Relato original, anotação profissional e sugestão da IA têm autoria visualmente distinta | Metadados de autoria presentes; edição de tema não altera o original |
| RB04 | Sinalização de atenção é passiva, apresenta estado e trecho literal e não aciona terceiros | Nenhuma comunicação automática; sinalização limitada a presente, indeterminado ou não identificado |
| RB05 | Coocorrência temporal não significa causalidade clínica | Sínteses usam descrições factuais, sem concluir causa, evolução clínica ou diagnóstico |
| RNF01 | Processamento dos dados clínicos local e offline, sem envio a APIs externas | Testes de rede e de prompt injection; nenhum tráfego clínico externo |
| RNF02 | Rastreabilidade e reprodutibilidade | Versões, digest, latência e execução registrados sem texto bruto em logs |
| RNF03 | Isolamento por paciente, camada e finalidade | Dados de outra pessoa e anamnese não chegam ao contexto dos agentes |
| RNF04 | Integridade e recuperação | Escritas, backup e restauração verificáveis; políticas ainda exigem validação |
| RNF05 | Acessibilidade e clareza | Teclado, alto contraste, fontes ampliadas e leitura que não depende apenas de cor |
| RNF06 | Desempenho e qualidade observáveis | Latência, falhas, recursos e tarefas medidos com critérios publicados |
| RNF07 | Reprodutibilidade experimental | Dados, licença, divisões, sementes, configurações e dependências identificados |

Processamento local reduz exposição a serviços externos, mas não comprova segurança ou conformidade por si só. Controles de autenticação, proteção de arquivos, backup, retenção e exclusão precisam ser implementados e verificados antes do uso com dados reais.

## 8. Arquitetura de referência e responsabilidades

O sistema possui dois percursos complementares. Na ingestão, recebe o original, transforma o conteúdo quando necessário, classifica, persiste e atualiza os índices. Na consulta, resolve o contexto, seleciona uma operação, recupera dados e apresenta uma resposta ou ação rastreável. O processamento de um diário não depende de um chat estar aberto.

| Componente lógico | Responsabilidade | Saída/controle |
| --- | --- | --- |
| Camada determinística | Ingestão, pseudonimização, validação, cálculos, persistência e visualização | Operações reproduzíveis em Python/SQL, sem depender de geração de linguagem |
| Classificador temático | MLP próprio sobre embeddings SBERT | Sugestão de um macrotema, pontuação e versão |
| Agente 1 — Extrator | Processar cada novo relato em esquema fechado | ABC, subtemas, sentimento/polaridade e marcador passivo com evidências |
| Agente 2 — Analista longitudinal e copiloto RAG | Analisar janelas e responder consultas normativas autorizadas | Sínteses, rascunhos revisáveis ou briefing citado/abstenção |
| Interface e camadas documentais | Controlar contexto, consentimento e visualização por perfil | Acesso separado a registro, análise privada e prontuário |

A arquitetura adota estritamente dois agentes locais. O Agente 1 é acionado por registro e opera com temperatura zero, semente fixa e esquema fechado; extrai situação, pensamento, sentimento, comportamento e consequência apenas quando sustentados pelo texto. O Agente 2 reúne análise longitudinal e RAG, sem criar um terceiro agente para cada função. A colaboração ocorre por dados tipados e evidências validadas.

Operações críticas de privacidade, cálculo, validação e escrita são determinísticas. Os agentes executam localmente por Ollama; nenhuma API externa recebe dados clínicos. Modelos candidatos incluem Qwen 2.5, Qwen3 4B e Gemma 3 4B; a versão final e seus requisitos de hardware ainda precisam de decisão. Temperatura zero e semente fixa são parâmetros de execução, não garantia universal de determinismo.

## 9. Ferramentas e controle das ações

A interface expõe aos agentes apenas operações locais delimitadas, com esquemas fechados, validação de argumentos e identidade de paciente verificada. Nenhum agente tem acesso irrestrito ao computador, à rede externa ou a operações de compartilhamento.

| Família | Exemplos | Controle |
| --- | --- | --- |
| Privacidade | Detectar identificadores, pseudonimizar e resolver tokens autorizados | Execução local; tabela de associação cifrada e fora dos prompts |
| Extração | Validar esquema ABC, subtemas, polaridade e marcadores | Pydantic e validação exata das citações no original |
| Histórico | Filtrar janelas, contar entradas, cores e tarefas | Python/SQL determinístico com paciente e período explícitos |
| RAG | Recuperar normas e técnicas autorizadas | Busca híbrida, referência de documento/seção e abstenção |
| Prontuário | Preparar rascunho de evolução | Migração apenas após revisão e validação explícita da psicóloga |

O texto do paciente e documentos recuperados são dados, nunca instruções capazes de alterar permissões ou o contrato dos agentes. Pedidos diagnósticos e marcadores de atenção não iniciam ações externas nem substituem avaliação humana.

## 10. Projetos, arquivos e modelo de dados

Na entrada, regras locais detectam CPF, RG, telefones, e-mails, endereços e dados bancários e os substituem por marcadores neutros. NER local pseudonimiza nomes, locais e instituições com tokens consistentes por paciente. A proposta cita `validate-docbr`, Microsoft Presidio com spaCy (`pt_core_news_lg`) ou BERTimbau NER; são alternativas técnicas a validar, não componentes já implantados.

Os registros são vinculados a um UUID estável por paciente. A anamnese e a tabela que relaciona identidade real a pseudônimos ficam fora do pipeline de IA; a tabela de associação deve ser cifrada, com AES-256 como referência e gestão de chaves separada, e acessível somente no ambiente autenticado da psicóloga. A arquitetura separa dados por finalidade e camada:

| Camada | Conteúdo | Acesso e regra |
| --- | --- | --- |
| 1. Registro do paciente | Texto original, campos TCC opcionais, cor de humor e tarefas | Paciente e psicóloga conforme compartilhamento; original nunca é sobrescrito pela IA |
| 2. Análise da psicóloga | ABC extraído, temas, subtemas, marcadores, sínteses, briefings RAG e notas privadas | Acesso exclusivo da psicóloga; saída automática é sugestão editável |
| 3. Prontuário oficial | Registro documental e rascunhos de evolução revisados | Paciente tem acesso conforme regra aplicável; nada migra sem edição e validação explícita da psicóloga |

Não há quarta camada de compartilhamento externo nem resumo automático para terceiros. A estrutura física, banco e política de backup ainda devem ser definidos sem comprometer esse isolamento.

| Entidade | Conteúdo mínimo | Relações |
| --- | --- | --- |
| Profissional | ID e configurações autorizadas | Projetos e biblioteca geral |
| Projeto de paciente | ID, identificação e estado | Conversas, registros e anexos |
| Conversa | ID, escopo geral ou projeto, mensagens | Fontes consultadas e execuções |
| Registro | ID, autor/origem, texto e datas | Anexos, classificações e versões |
| Arquivo | ID, caminho controlado, tipo, hash e origem | Páginas, áudio ou extração de texto |
| Classificação | Registro, taxonomia, versão de modelo e saída | Temas e eventuais correções |
| Subtema | ID, projeto, tema pai, nome e estado | Entradas de apoio e histórico de edição |
| Trecho recuperável | Fonte, versão, localização e conteúdo | Índice lexical/vetorial |
| Execução de ferramenta | ID, contexto, operação, resultado e estado | Alterações e fontes utilizadas |

Índices, resumos e gráficos são derivados reconstruíveis; não substituem o original. Alterações devem manter histórico e invalidar derivados incompatíveis. A tabela de associação entre pseudônimos e identidades deve permanecer cifrada e separada dos dados enviados aos agentes.

A trilha registra versões de modelo e taxonomia, digest e latência, sem guardar texto bruto do paciente em logs. A política de retenção, backup e recuperação ainda precisa ser formalizada antes do uso com dados reais.

## 11. Rede neural para classificação temática

A rede classifica o assunto do relato em uma categoria principal entre seis macrotemas. Humor, sentimento e polaridade são dimensões distintas, não classes temáticas. A psicóloga pode revisar a sugestão.

| Macrotema | Escopo descritivo |
| --- | --- |
| Autoestima e Identidade | Autopercepção, inseguranças e posicionamento pessoal |
| Relacionamentos e Família | Vínculos amorosos, amizades e dinâmicas familiares |
| Trabalho, Estudos e Finanças | Pressões e realizações profissionais, acadêmicas e materiais |
| Saúde, Sono e Rotina | Condição física, sono, medicações e eventos fora da rotina |
| Perdas, Luto e Rupturas | Falecimentos, términos, demissões e mudanças bruscas |
| Outros / Indeterminado | Classe residual quando nenhuma categoria temática supera o limiar definido |

O MLP usa embeddings SBERT como representação e sugere uma categoria quando a confiança é de pelo menos 0,50; abaixo disso, retorna Outros / Indeterminado. Humor é atributo separado, selecionado pelo paciente e apresentado em escala visual com opções como calma, alegria, tristeza, medo, preocupação, frustração e raiva; não deve ser inferido como macrotema. A classificação de uma categoria principal segue o enquadramento multiclasse, não multilabel (F09).

O requisito acadêmico é construir e treinar o MLP do projeto, documentando camadas, inicialização, passagem direta, perda, retropropagação e atualização de pesos. O uso de SBERT como representação pré-treinada não substitui a implementação e avaliação da rede classificadora. [Escolher o modelo SBERT, dimensões, configuração do MLP, otimizador, taxa de aprendizado, batch e regra de parada.]

Com V atributos de entrada, H unidades ocultas e C categorias, uma rede densa de uma camada oculta possui V vezes H + H + H vezes C + C parâmetros treináveis. O vocabulário deve ser ajustado somente no treino. Pesos são aprendidos; hiperparâmetros são escolhidos na validação. A implementação deve incluir verificação numérica de gradientes ou outra evidência de correção da retropropagação antes de interpretar resultados semânticos. Referência didática: F10.

## 12. Dataset, anotação e experimentos da rede

O conjunto de treinamento precisa conter textos e referências compatíveis com a taxonomia. Tamanho, idioma e presença de uma coluna de categoria não bastam para selecionar uma base. Devem ser avaliados domínio, licença, possibilidade de uso, distribuição das classes, ambiguidade e proximidade entre exemplos.

| Campo proposto | Finalidade | Uso no aprendizado |
| --- | --- | --- |
| id | Identificar o exemplo | Metadado |
| texto | Conteúdo do relato ou trecho | Entrada, após representação |
| tema(s) | Categoria(s) esperada(s) | Alvo supervisionado |
| grupo_origem | Pessoa, entrevista ou família de templates | Separação dos conjuntos; não é pista de classificação |
| origem_rotulo | Humano, regra ou modelo, com versão | Qualidade e interpretação das referências |
| split | Treino, validação ou teste | Controle do experimento |
| origem/licença | Proveniência e condições de uso | Auditoria de dados |

[Selecionar dataset, fonte, versão, licença, quantidade por classe e uso de dados sintéticos ou públicos autorizados.] O conjunto deve corresponder aos seis macrotemas, excluir identificadores e documentar origem e licença. O MuPe pode ser explorado como corpus narrativo, mas não contém automaticamente a taxonomia do produto (F07); o MASSIVE trata de intenções de assistentes e não é substituto direto de relatos temáticos (F08). Qualquer adaptação exige justificativa e controle de vazamento entre pessoas ou templates.

Definir anotação, revisão independente e tratamento de desacordo. Rótulos gerados por LLM ou regras são supervisão fraca: métricas sobre eles medem concordância com a referência, não validade clínica nem desempenho em uso real.

Separar treino, validação e teste antes de ajustar representação ou modelos. Variações quase idênticas e relatos do mesmo grupo devem ser controlados para evitar vazamento. As proporções, critérios de agrupamento, deduplicação e tamanho mínimo de teste por classe permanecem por definir; a seleção da configuração usa validação e o teste final fica reservado.

Comparar a rede com uma referência simples, como a classe majoritária, e com um baseline textual compatível. Apresentar curvas de treino e validação, matriz de confusão, precisão/recall por macrotema e macro-F1. Definir limiares de aceite, tratamento de classes raras, repetições e reporte de incerteza antes de interpretar resultados.

Baixo desempenho também no treino sugere investigar capacidade, representação, otimização e qualidade dos rótulos. Desempenho alto no treino e inferior na validação sugere investigar generalização. Não ajustar tudo simultaneamente: registrar experimentos com alterações controladas e conservar resultados negativos.

## 13. Subtemas pessoais e análise longitudinal

Subtemas organizam assuntos específicos dentro dos seis macrotemas e não alteram a taxonomia do classificador. O Agente 1 propõe de um a seis subtemas por relato, sempre ancorados em trecho literal e posições inicial/final verificáveis.

O Agente 2 compara registros da mesma pessoa em janelas de 7, 14 e 30 dias. Cálculos de contagem, distribuição de humor/polaridade, timeline e tarefas são executados em Python/SQL. Sínteses podem apontar coocorrências e sequência temporal em linguagem factual (por exemplo, “ocorreu antes de” ou “coincidiu com”), sem afirmar causalidade, melhora, piora ou intensidade clínica.

O status das tarefas é determinístico (feita/não feita) e aparece na timeline. Toda síntese informa janela e conjunto de registros. Variação de contagens pode refletir frequência de envio ou mudança de versão do classificador, não uma mudança clínica.

## 14. RAG, memória e conhecimento profissional

RAG combina recuperação de informações externas com geração de resposta. A memória persistente é o conjunto de registros; o RAG seleciona partes pertinentes desse conjunto para uma consulta. Não é necessário retreinar o LLM quando um arquivo é adicionado ao índice. A formulação original é referência técnica histórica, não um resource recente da entrega (F06).

| Coleção | Conteúdo | Regra de uso |
| --- | --- | --- |
| Instruções da aplicação | Papel, limites e ferramentas permitidas | Aplicadas diretamente; não dependem de busca por similaridade |
| Espaço geral profissional | Materiais, preferências e metodologias autorizadas | Contextualização da profissional, sem virar fato sobre pacientes |
| Registros por paciente | Diários, notas, anexos e transcrições | Recuperação com identidade e autorização obrigatórias |
| Histórico de conversa | Mensagens do chat e contexto recente | Continuidade; não equivale a registro profissional confirmado |
| Biblioteca publicada | Documentos externos com autoria e condições de uso | Citação e distinção entre evidência publicada e relato individual |

Na ingestão: preservar o arquivo; extrair texto; identificar documento, página ou intervalo; dividir em trechos quando necessário; indexar; verificar disponibilidade. Na consulta: resolver escopo; aplicar filtros; recuperar candidatos; selecionar contexto; gerar resposta; verificar referências e apresentar limitações.

O corpus normativo/técnico autorizado inclui Código de Ética Profissional, Resolução CFP nº 001/2009, notas CFP/CRP-SP de 2025 e técnicas aprovadas. Uma norma ou publicação contextualiza o trabalho profissional, mas não é evidência sobre um paciente. Fonte incompleta, não autorizada ou não pertinente não deve ser citada como suporte.

O desenho de referência usa busca híbrida BM25 + embeddings e5-small, fusão por Reciprocal Rank Fusion (RRF) e limiar de score de pelo menos 0,70. O multilingual-e5-small é uma opção documentada, sujeita à validação no corpus (F11). O briefing cita documento e seção; abaixo do limiar ou sem fonte sustentadora, o agente declara abstenção. Os parâmetros precisam ser avaliados no corpus autorizado antes de serem tratados como desempenho comprovado.

Filtros de autorização e escopo são aplicados antes da recuperação. O classificador temático não pode excluir silenciosamente registros relevantes. Um erro de recuperação deve resultar em fonte insuficiente ou abstenção, não em conteúdo inventado.

## 15. Tempo, visualização e experiência profissional

O dashboard e a análise profissional devem ser escaneáveis em menos de dois minutos, com fontes ampliadas e fluxo simplificado para acessibilidade, inclusive para pessoas com menor familiaridade digital. As janelas de referência são 7, 14 e 30 dias. Pessoa, período, número de registros e origem automática/revisada permanecem visíveis.

O humor selecionado pelo paciente é mostrado por cores como dimensão separada dos temas, com legenda textual acessível. Uma cor não deve representar gravidade nem intensidade clínica. A interface prevê navegação por teclado, alto contraste e identidade visual personalizável. As métricas devem permitir abrir as entradas de origem.

## 16. Evidências de engenharia agêntica e aplicação ao projeto

A pesquisa bibliográfica deste relatório considera fontes até **19/11/2026**. Os trabalhos citados fundamentam critérios de projeto; não certificam este produto nem constituem um padrão único do MIT. Recomendações de engenharia de fornecedores são identificadas como tal, sem pressupor adoção de seus serviços. Requisitos clínico-regulatórios e de UX também incorporam os dois documentos de produto listados na seção 21.

| Fonte | Achado relevante | Aplicação ao produto |
| --- | --- | --- |
| F01 - AI Agent Index, MIT, artigo de 2026 | Identifica lacunas de transparência na documentação de agentes implantados | Documentar ferramentas, autonomia, limites, modelos e resultados de testes |
| F02 - ImpactBench, 2026 | Propõe avaliação de comportamentos ligados a impacto humano, usando simulações, juiz LLM e revisão especializada | Avaliar autonomia da profissional, clareza de limites e possibilidade de conferir fontes; não presumir benefício clínico |
| F03 - Building effective agents, 2024 | Distingue fluxos previsíveis de decisões dinâmicas por modelos e recomenda complexidade justificada | Usar código para cálculos e persistência; justificar cada papel agêntico |
| F04 - Writing effective tools, 2025 | Enfatiza ferramentas bem descritas, retornos úteis e avaliação | Contratos tipados, escopo claro, erros explícitos e retornos suficientes |
| F05 - Demystifying evals, 2026 | Distingue resposta do agente, trajetória de ações e estado final | Verificar o que foi realmente gravado, lido ou alterado; repetir cenários |

O AI Agent Index descreve sistemas e sua transparência; não fornece certificação de segurança para uma implementação particular. O ImpactBench é um preprint e infraestrutura de avaliação em evolução. Seu uso de revisão especializada impede interpretar a presença de um juiz LLM como prova de que revisão humana é dispensável. A aplicação desses trabalhos ao produto é uma decisão de engenharia da Equipe 007.

A avaliação deve cobrir tanto componentes quanto o fluxo integrado. Um modelo que classifica corretamente pode estar conectado à pessoa errada; uma resposta bem escrita pode citar uma fonte que não a sustenta; uma mensagem de sucesso pode ocultar falha de gravação. Por isso, o teste precisa observar dados, operações e resultado final.

## 17. Plano de avaliação e critérios de aceite

| Camada | Evidência de avaliação | Condição de reporte |
| --- | --- | --- |
| Rede temática | Macro-F1, precisão/recall por classe, matriz e curvas | Taxonomia, divisão de dados e origem dos rótulos declaradas |
| Subtemas | Aderência de evidências, duplicação, edição e estabilidade | Sem afirmar descoberta de condição clínica |
| Recuperação | Recall@k, HitRate@k e casos sem fonte relevante | Recall e acerto de ao menos um resultado separados |
| Resposta | Fonte correta, suporte factual e reconhecimento de lacuna | ID de fonte existente não basta: trecho precisa sustentar a afirmação |
| Ferramentas | Argumentos, autorização, cancelamento e estado final | Não avaliar apenas a frase de confirmação |
| Usabilidade | Conclusão de tarefas, tempo e correções necessárias | Perfil, amostra e roteiro documentados |
| Operação | Latência, erros, recursos e recuperação | Máquina, versão e limites da medição declarados |

As métricas, rubricas, critérios de aceite e número de repetições precisam ser definidos antes do teste final. Resultados sem referência independente devem ser identificados como preliminares; concordância entre modelos não estabelece verdade.

| Cenário de aceite | Preparação sintética | Resultado esperado |
| --- | --- | --- |
| CA01 - Isolamento | Dois perfis fictícios com nomes iguais e anamneses | Nenhuma mistura; anamnese não chega ao agente |
| CA02 - Limite e pseudonimização | Relatos de 2.400 e 2.401 caracteres com PII sintética | Limite respeitado sem truncamento; identificadores pseudonimizados localmente |
| CA03 - Tema e humor | Um relato com tema e humor informado | Tema revisável e humor apresentado em dimensão distinta |
| CA04 - Citação literal | Citação válida e citação inventada em saída de teste | A primeira é localizada; a segunda invalida a saída |
| CA05 - Tarefas e períodos | Tarefas feitas/não feitas em janelas conhecidas | Timeline e contagens coincidem com cálculo determinístico |
| CA06 - RAG insuficiente | Pergunta sem fonte acima do limiar | Agente se abstém, sem inventar referência ou resposta |
| CA07 - Camadas | Rascunho não validado e análise privada | Nenhum conteúdo migra ou aparece no prontuário oficial |
| CA08 - Acessibilidade | Navegação por teclado, alto contraste e texto ampliado | Funções essenciais permanecem utilizáveis e legíveis |
| RB04 - Marcador passivo | Trecho sintético contém marcador de atenção | Estado e trecho aparecem apenas no painel; nenhum contato externo |
| RB05 - Coocorrência | Eventos em semanas sucessivas | Texto descreve sequência/coocorrência sem atribuir causalidade |

A demonstração inicial utiliza pelo menos dois perfis fictícios para testar isolamento. Uma execução bem-sucedida isolada não é suficiente para declarar confiabilidade do sistema.

## 18. MLOps, versionamento e evolução

Cada experimento deve registrar commit de código, versão/hash dos dados, taxonomia, forma de divisão, configuração, modelo, métricas e artefatos. A reprodução deve distinguir ambiente, dependências, semente e limitações de determinismo do hardware e runtime.

Mudanças no contrato afetam classificador, persistência, subtemas, RAG, dashboard e testes. A taxonomia deve possuir versão, e resultados históricos devem indicar qual versão foi utilizada. Reprocessamento precisa ser uma operação explícita e auditável.

Documentos e índices também têm ciclo de vida: ingestão, validação, disponibilidade, atualização e remoção. Monitorar registros que não foram indexados e índices desatualizados. O chat deve comunicar quando uma resposta usa um conjunto ainda incompleto.

## 19. Rastreabilidade acadêmica, riscos e validação

| Restrição/necessidade | Requisitos relacionados | Evidência esperada |
| --- | --- | --- |
| Dois agentes colaborando | RF04, RF06 | Papéis distintos, execução local e troca de dados estruturados |
| Base de conhecimento | RF06 | Corpus autorizado, ingestão rastreável, recuperação híbrida e citação |
| Rede neural própria | RF03 | MLP próprio, operações de treino e avaliação por macrotema |
| MLOps | RNF02, RNF07; seção 18 | Execução rastreável e artefatos reproduzíveis |
| API por agentes | RF04, RF06 | Integração local com tratamento de falhas e esquema validado |
| Ética, privacidade e explicabilidade | RB01 a RB05, RNF01 a RNF03 | Limites, camadas, origem, pseudonimização e citações verificáveis |
| MVP e versionamento | RF01 a RF08, RNF01 a RNF07 | Fluxo integrado com dados fictícios, testes e histórico de alterações |

Referências acadêmicas e normativas apoiam a especificação, mas não certificam a implementação. Dados reais não devem ser usados antes de validar consentimento, segurança, regras profissionais e requisitos legais pertinentes.

| Risco | Consequência | Tratamento |
| --- | --- | --- |
| Vazamento de identidade | Exposição de dados sensíveis | Pseudonimização local, UUID por paciente, cofre cifrado separado e testes de isolamento |
| Citação inventada ou fora de contexto | Síntese enganosa | Validar trechos literais contra o original e RAG contra documento/seção |
| Marcador de atenção interpretado como diagnóstico | Falso alarme ou decisão clínica indevida | Exibição passiva com trecho literal; nenhuma ação ou comunicação automática |
| Coocorrência interpretada como causalidade | Inferência clínica não sustentada | Linguagem factual, períodos explícitos e revisão da psicóloga |
| Falha de agente ou modelo | Registro inconsistente ou saída inválida | Esquema fechado, validação, falha explícita e preservação do original |
| Mistura entre análise e prontuário | Acesso indevido ou registro não validado | Três camadas isoladas e validação humana antes da migração |

A versão documenta decisões de produto já consolidadas e mantém separadas as escolhas técnicas e de avaliação ainda abertas.

## 20. Decisões consolidadas e validações pendentes

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

## 21. Referências e critérios de uso

Data de corte desta versão: 19/11/2026. As fontes a seguir fundamentam requisitos, limites ético-profissionais e decisões de engenharia. A inclusão bibliográfica não significa adoção de ferramenta, licença para redistribuir seu conteúdo ou validação do produto.

F01. STAUFER, Leon et al. The 2025 AI Agent Index: Documenting Technical and Safety Features of Deployed Agentic AI Systems. Preprint submetido em 19/02/2026; versão 2 de 06/05/2026. Portal hospedado no MIT. https://arxiv.org/abs/2602.17753v2 . Portal: https://aiagentindex.mit.edu/ . Contribuição: documentação de autonomia, ferramentas e avaliação; não prescreve uma arquitetura única.

F02. ARCHIWARANGUPROK, Chayapatr et al. Open Benchmark of AI Impact on Humans (ImpactBench): an expert-guided, open platform for the holistic evaluation of AI impact on humans. Preprint, versão 1, 14/10/2026. https://arxiv.org/abs/2610.20690v1 . Plataforma MIT Media Lab: https://impactbench.media.mit.edu/about . Contribuição: avaliação de comportamentos e impacto humano; inclui limitações de simulação e julgamento automatizado, sem validar este aplicativo.

F03. ANTHROPIC. Building effective agents. 19/12/2024. https://www.anthropic.com/research/building-effective-agents . Contribuição: fluxos, agentes e simplicidade arquitetural. É orientação de engenharia de fornecedor; detalhes de ferramentas evoluem.

F04. ANTHROPIC. Writing effective tools for AI agents. 11/09/2025. https://www.anthropic.com/research/writing-tools-for-agents . Contribuição: descrição, limites, retorno e avaliação das ferramentas.

F05. ANTHROPIC. Demystifying evals for AI agents. 09/01/2026. https://www.anthropic.com/research/demystifying-evals-for-ai-agents . Contribuição: avaliação da execução e do estado final, além do texto produzido.

F06. LEWIS, Patrick et al. Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. NeurIPS, 2020. https://proceedings.neurips.cc/paper/2020/hash/6b493230205f780e1bc26945df7481e5-Abstract.html . Referência histórica do método, fora da janela de dois anos para resource recente.

F07. LEAL, Sidney Evaldo et al. MuPe Life Stories Dataset: Spontaneous Speech in Brazilian Portuguese with a Case Study Evaluation on ASR Bias against Speakers Groups and Topic Modeling. COLING, 2025. https://aclanthology.org/2025.coling-main.407/ . Contribuição: candidato de domínio narrativo; uso e adaptação ainda dependem de decisão.

F08. AMAZON SCIENCE. MASSIVE, documentação do dataset. https://huggingface.co/datasets/AmazonScience/massive . Contribuição: exemplo de classificação de intenções; rótulos não equivalem à taxonomia temática do produto.

F09. SCIKIT-LEARN. Multiclass and multioutput algorithms; multilabel classification. https://scikit-learn.org/stable/modules/multiclass.html . Contribuição: distinção entre categorias exclusivas e simultâneas e representação das referências.

F10. NUMPY COMMUNITY. Deep learning on MNIST. https://numpy.org/numpy-tutorials/tutorial-deep-learning-on-mnist/ . Contribuição: exemplo didático de rede construída com operações NumPy; dados de imagens não substituem o dataset textual do projeto.

F11. INTFLOAT. multilingual-e5-small, model card. https://huggingface.co/intfloat/multilingual-e5-small . Contribuição: candidato de embeddings, limites e preparação das entradas; seleção depende de benchmark próprio.

F12. EQUIPE 007 - LICENSA PARA EXECUTAR. Especificação de Requisitos — Diário Emocional Inteligente, versão 2.1 consolidada, 19/11/2026. https://docs.google.com/document/d/1Vd2MqRL89ZywdTZhE9LsI2x8bMcIKYzP/edit . Fonte-base dos requisitos de produto, público, camadas e critérios de aceite.

F13. EQUIPE 007 - LICENSA PARA EXECUTAR. Diário Emocional Inteligente — Insights Clínicos e Evolução da Arquitetura de Agentes, 2026. https://docs.google.com/document/d/1RXIFI4TdtOksuJmNa12xX5T9e4pUaN4esNH7i80Vsng/edit . Fonte de recomendações sobre pseudonimização, agentes, taxonomia, supervisão e arquitetura documental.

F14. BRASIL. Lei nº 13.709, de 14 de agosto de 2018. Lei Geral de Proteção de Dados Pessoais (LGPD), arts. 5º, 6º, 13 e 46.

F15. CONSELHO FEDERAL DE PSICOLOGIA. Resolução CFP nº 010/2005. Código de Ética Profissional do Psicólogo, arts. 9º e 10º.

F16. CONSELHO FEDERAL DE PSICOLOGIA. Resolução CFP nº 001/2009. Registro documental decorrente da prestação de serviços psicológicos, incluindo art. 6º.

F17. CONSELHO FEDERAL DE PSICOLOGIA. Nota de Posicionamento sobre o Uso de Inteligência Artificial na Prática Psicológica, 2025.

F18. CONSELHO REGIONAL DE PSICOLOGIA DE SÃO PAULO. Nota Orientativa sobre o Uso de Ferramentas de Inteligência Artificial na Psicologia, 2025.

Esta versão alinha requisitos e arquitetura às fontes F12 e F13. Implementação, conformidade e eficácia precisam ser demonstradas por avaliações próprias; a especificação não substitui parecer profissional ou jurídico.
