# Diário Emocional Inteligênte

**Equipe 007 - Licensa para Executar | Especificação de requisitos e arquitetura de referência | Versão 1.0 | 06/11/2026**

A Equipe 007 apresenta o Diário Emocional Inteligênte, um ambiente de organização e consulta de informações destinado à profissional de psicologia. Seu assistente, [AGENT-NAME], representa a ideia de um agente secreto a serviço da profissional: discreto na interação, explícito sobre suas ações e rastreável em suas fontes. A identidade temática não constitui promessa de sigilo técnico ou de competência clínica.

Este documento descreve o produto pretendido de ponta a ponta. Não constitui declaração de funcionalidades já implementadas ou de resultados de avaliação já obtidos. Os requisitos expressam o comportamento esperado; tecnologias, políticas e critérios quantitativos ainda sujeitos a acordo aparecem em vermelho e entre colchetes. Cada decisão DEC possui uma pergunta consolidada na seção 20. O texto comum apresenta o escopo de referência; os destaques identificam as lacunas que impedem o fechamento da especificação.

## 1. Propósito, problema e objetivos

Registros de atendimento, diários e anotações podem estar dispersos entre arquivos, fotografias e conversas. Localizar uma informação, reconstruir seu contexto temporal e relacioná-la a outras entradas demanda esforço. O produto propõe reunir esses materiais em um espaço por paciente e oferecer consultas em linguagem natural, com acesso aos documentos originais.

O objetivo é apoiar o acompanhamento do próprio trabalho da psicóloga: registrar informações, organizar assuntos, recuperar fontes, visualizar frequências e executar ações solicitadas. O assistente apresenta resultados objetivos, identifica limites e distingue o conteúdo registrado de qualquer classificação automática. Decisões profissionais permanecem com a psicóloga.

| Objetivo | Resultado esperado | Como verificar |
| --- | --- | --- |
| OBJ01 - Localizar informações | Encontrar registros pertinentes de uma pessoa e período | Tarefa de busca com fontes esperadas e medição de tempo |
| OBJ02 - Organizar relatos | Classificar temas e agrupar subtemas pessoais editáveis | Avaliação da rede e conferência das entradas de apoio |
| OBJ03 - Reduzir trabalho operacional | Realizar ações do aplicativo por texto ou voz | Verificação do estado final, além da resposta do chat |
| OBJ04 - Preservar rastreabilidade | Abrir o original usado em cada síntese ou contagem | Percurso verificável entre resposta, ferramenta e documento |
| OBJ05 - Sustentar aprendizado acadêmico | Explicar, construir e avaliar rede neural e RAG | Experimentos reproduzíveis, documentação e análise de erros |

A utilidade e a economia de tempo são hipóteses a avaliar. Não há alegação de melhora clínica, diagnóstico ou eficácia terapêutica do produto. [DEC-02: definir público atendido, faixa etária, contexto de uso e limites do piloto.] [DEC-20: definir tarefas, participantes e metas para avaliar utilidade, desempenho e usabilidade.]

## 2. Identidade, atores e fronteiras

A autoria institucional é da **Equipe 007 - Licensa para Executar**. O produto se chama **Diário Emocional Inteligênte**. O nome do assistente conversacional permanece [AGENT-NAME]. A apresentação visual pode explorar a metáfora de agente secreto sem sugerir vigilância, diagnóstico oculto ou capacidade infalível.

| Ator | Responsabilidade no produto | Limite |
| --- | --- | --- |
| Psicóloga | Consultar, registrar, revisar, organizar e comandar ações | Sua autoria deve ser distinguida da geração automática |
| Paciente/autor do diário | Produzir os relatos recebidos pelo sistema | Não visualiza os temas e subtemas do dashboard profissional |
| Assistente conversacional | Interpretar pedidos, selecionar ferramentas e apresentar resultados | Atua dentro das permissões e do contexto verificados pela aplicação |
| Equipe 007 | Desenvolver, testar e documentar | Não substitui revisão profissional ou avaliação jurídica |
| Orientação acadêmica | Avaliar os objetivos do Challenge | Definir interpretação e evidências das exigências acadêmicas |

O acesso do paciente ao diário e sua forma de envio precisam ser definidos independentemente do painel da psicóloga. [DEC-03: decidir se haverá aplicativo/tela do paciente, importação pela profissional ou outro canal de recebimento.] [DEC-24: registrar integrantes, responsabilidades, responsáveis por revisão e procedimento de aprovação dos requisitos.]

Diagnóstico automático, prescrição, recomendação de tratamento e classificação de gravidade clínica ficam fora do escopo. Uma referência a uma abordagem profissional, como TCC, pode compor uma biblioteca consultável, mas não autoriza o assistente a formular condutas clínicas. [DEC-12: definir o corpus profissional, a finalidade de materiais metodológicos e a política de atualização das fontes.]

## 3. Escopo do produto e da entrega acadêmica

O produto final reúne projetos por paciente, conversas, anexos, entrada por voz, biblioteca geral da profissional, classificação temática, subtemas editáveis e consultas rastreáveis. O desenvolvimento deve ser incremental: a demonstração de um componente não implica que todas essas capacidades estejam prontas.

| Horizonte | Conteúdo | Evidência necessária |
| --- | --- | --- |
| Entrega de 13/11/2026 | Conceitos e arquitetura de RAG; tarefa, dados e arquitetura da rede construída desde a base; avaliação planejada e experimentos conforme orientação | Fontes, decisões técnicas justificadas, comandos reproduzíveis e resultados efetivamente obtidos |
| MVP integrado | Um fluxo completo com registros sintéticos, classificação, organização, recuperação e resposta com fonte | Testes ponta a ponta, falhas explícitas e contexto por pessoa |
| Produto final | Experiência de projetos e chat, voz, anexos, edição, histórico e operação cotidiana | Avaliações técnicas, de usabilidade e de adequação ao uso definido |

[DEC-23: aprovar o recorte executável de 13/11, a profundidade de treino exigida e quais funções do produto ficam em entregas posteriores.] A fase de demonstração utiliza pessoas e materiais fictícios. Qualquer ampliação para registros reais depende de requisitos próprios de acesso, consentimento, armazenamento e revisão profissional, ainda não especificados integralmente.

As restrições acadêmicas compreendem: pelo menos dois agentes colaborando; base de conhecimento; MLOps; construção e teste de rede neural simples; API utilizada pelos agentes; versionamento; ética e explicabilidade; resource recente elegível; MVP funcional. [DEC-23: confirmar com a orientação a interpretação de agente, construção do zero, API local e data de referência para a janela de dois anos dos resources.]

## 4. Elicitação e organização das decisões

O fechamento dos requisitos deve combinar análise dos fluxos de trabalho, exemplos fictícios, demonstrações de interface e validação de critérios de aceite. Não se pressupõem entrevistas concluídas, resultados de pesquisa com usuários ou consentimentos já obtidos.

Perguntas de elicitação devem investigar situações concretas: qual informação a profissional precisa reencontrar; como decide que duas notas pertencem ao mesmo assunto; como corrige uma transcrição; qual evidência precisa ver em uma síntese; quais ações pode delegar e quais deseja conferir. Exemplos devem ser fictícios na etapa acadêmica.

Requisitos RF descrevem funções; RNF descrevem qualidades; RB descrevem regras do produto; CA descrevem critérios de aceite; DEC registra decisões abertas. Uma decisão deve registrar a opção escolhida, justificativa, responsável, data e requisitos afetados. Alterações de taxonomia, modelo ou política de contagem precisam gerar novas versões, com impacto explícito sobre resultados anteriores.

[DEC-24: definir quem registra as decisões, quem as aprova e como divergências serão resolvidas.] A seção 20 funciona como pauta de reunião e formulário de respostas. Não é necessário responder todas as perguntas de uma vez: decisões sobre taxonomia, dados e contrato têm precedência sobre ajustes visuais.

## 5. Jornadas de uso

### 5.1. Abrir o contexto de uma pessoa

A profissional pode começar no modo geral e solicitar a abertura de um paciente. O sistema resolve o cadastro por identificador e dados autorizados. Quando houver homônimos ou ambiguidade, apresenta opções antes de acessar os registros. Ao entrar no projeto, mostra explicitamente a pessoa selecionada e o período da consulta.

Dentro de um projeto, a profissional cria novas conversas ou retoma conversas anteriores. As mensagens pertencem à conversa; arquivos e registros pertencem ao projeto. Criar um novo chat não apaga nem duplica o histórico documental do paciente. Consultas gerais, como recebimentos recentes, podem reunir metadados dos pacientes autorizados sem misturar seus relatos em uma única síntese pessoal.

### 5.2. Registrar uma sessão por texto, voz ou anexos

A profissional seleciona o projeto, informa o relato da sessão e pode anexar fotografias ou documentos. O sistema preserva os originais, registra a origem, extrai texto quando necessário e mostra as incertezas de transcrição. Um arquivo anexado depois não deve assumir automaticamente a data do acontecimento descrito.

O assistente organiza o material e prepara as operações de persistência segundo a política de confirmação. A profissional consegue conferir o texto que será registrado e sua autoria. A interface informa o que foi efetivamente salvo e o que permaneceu pendente. [DEC-19: definir transcrição, OCR, revisão de texto extraído e retenção de gravações e imagens.]

### 5.3. Explorar temas e subtemas

O dashboard apresenta assuntos identificados nos registros do período. A psicóloga pode navegar de tema para subtema e abrir as entradas que sustentam a organização. Subtemas gerados automaticamente ficam disponíveis para edição; correções, renomeações e uniões mantêm histórico. O paciente não visualiza essa classificação no produto.

### 5.4. Consultar e agir pelo chat

A profissional pede, por exemplo, uma lista de diários, uma síntese dos relatos sobre determinado assunto ou a criação de uma anotação. O assistente seleciona ferramentas cadastradas; a aplicação verifica escopo e argumentos. Respostas com informação factual apontam a fonte. Ações de escrita apresentam sua situação real: preparada, executada, cancelada ou falhou.

## 6. Requisitos funcionais

| ID | Comportamento requerido | Critério de aceite associado |
| --- | --- | --- |
| RF01 | Manter espaço geral da profissional e projeto separado por paciente, com ID estável | CA01: nomes iguais não provocam mistura de projetos |
| RF02 | Resolver o paciente solicitado no modo geral e tornar visível a mudança de contexto | CA02: pedido ambíguo solicita seleção; contexto correto permanece visível |
| RF03 | Manter várias conversas por projeto e permitir retomada | CA03: chat novo acessa registros do projeto sem incorporar mensagens de outra pessoa |
| RF04 | Receber textos, arquivos e fotografias vinculados ao projeto escolhido | CA04: original preservado, origem registrada e falha de importação indicada |
| RF05 | Receber fala da profissional e produzir transcrição identificável | CA05: áudio/transcrição têm vínculo e erros podem ser corrigidos conforme política |
| RF06 | Classificar temas com a rede neural construída pelo grupo | CA06: saída validada, taxonomia e versão conhecidas, erro operacional distinto de classificação |
| RF07 | Gerar subtemas pessoais a partir de entradas relacionadas | CA07: subtema aponta pessoa, tema pai e evidências existentes |
| RF08 | Permitir editar, unir e reorganizar subtemas automaticamente gerados | CA08: mudança visível, histórico preservado e projeções atualizadas |
| RF09 | Exibir dashboard profissional com gráficos vetoriais responsivos e alternativa textual | CA09: números coincidem com a consulta e são legíveis em diferentes janelas |
| RF10 | Aplicar filtros temporais coerentes a consulta, síntese e dashboard | CA10: janela sem registros retorna vazio, sem ampliar período silenciosamente |
| RF11 | Recuperar trechos autorizados por RAG e apresentar fontes consultáveis | CA11: resposta aponta documento, localização, data e versão quando disponíveis |
| RF12 | Consultar listas, horários e contagens com operações exatas | CA12: todos os registros elegíveis aparecem, independentemente da similaridade textual |
| RF13 | Permitir acionar pelo chat as funções expostas na interface | CA13: pedido e botão equivalente produzem a mesma operação validada |
| RF14 | Preparar e executar gravações conforme política de confirmação | CA14: conteúdo, destino, autoria e resultado da ação são verificáveis |
| RF15 | Manter biblioteca e preferências da profissional separadas dos registros individuais | CA15: material geral não se transforma em fato sobre um paciente |
| RF16 | Consultar entradas recebidas recentemente e seu estado de processamento | CA16: ordenação usa a data indicada e distingue recebido, processando e falhou |
| RF17 | Permitir interrupção e recuperação de operações | CA17: cancelamento não gera gravação tardia e repetição não cria duplicatas |
| RF18 | Rastrear resposta, ferramenta, origem e versões utilizadas | CA18: uma execução pode ser reconstruída a partir de dados permitidos de auditoria |

[DEC-17: definir formatos, limites de anexos, tecnologia da interface, plataformas suportadas e política de sincronização.] [DEC-16: fechar a matriz de operações automáticas e operações com confirmação.] Os critérios acima descrevem o comportamento esperado; resultados de testes deverão ser preenchidos quando existirem.

## 7. Regras do produto e requisitos de qualidade

| ID | Regra ou qualidade | Evidência de verificação |
| --- | --- | --- |
| RB01 | O assistente organiza e recupera informações sem emitir diagnósticos ou tratamentos | Cenários de avaliação que solicitam opinião clínica recebem delimitação do escopo |
| RB02 | Temas e subtemas são exclusivos da área profissional | Controle de acesso e teste da interface do paciente, se houver |
| RB03 | Relato original, anotação profissional e saída automática têm origens distintas | Identificação visível e referências de origem no armazenamento |
| RB04 | Subtema não constitui fato clínico; edição não altera silenciosamente o original | Histórico de alterações e fontes preservadas |
| RB05 | Contexto de pessoa e período é estabelecido pela aplicação | Testes com homônimos, troca de projeto e consultas sem resultados |
| RB06 | Ausência de fonte ou falha de ferramenta não autoriza inventar informação | Erro/insuficiência explícitos e nenhuma confirmação falsa de escrita |
| RB07 | Conteúdo de anexos é dado consultável, não autorização para executar instruções | Documentos com instruções maliciosas não ampliam permissões |
| RB08 | Contagem, frequência e coocorrência têm definição verificável | Unidade, denominador, intervalo e versões informados |
| RNF01 | Rastreabilidade das respostas e alterações | IDs de execução, fontes, operações e versões |
| RNF02 | Integridade e recuperação | Escritas consistentes, cópias de segurança e restauração verificáveis |
| RNF03 | Isolamento e minimização de acesso | Material de outro projeto não chega ao contexto do modelo |
| RNF04 | Reprodutibilidade experimental | Dataset, configurações, código, semente e dependências identificados |
| RNF05 | Acessibilidade e clareza | Uso por teclado, descrições textuais e informação não dependente só de cor |
| RNF06 | Desempenho observável | Latência, falhas, tamanho do contexto e custo por tarefa medidos |
| RNF07 | Portabilidade | Fluxos de instalação e uso testados nas plataformas escolhidas |
| RNF08 | Manutenibilidade | Contratos tipados, ferramentas pequenas e migrações documentadas |

[DEC-18: especificar autenticação, proteção de arquivos e cópias, retenção, exclusão e recuperação; validar obrigações aplicáveis antes de uso com dados reais.] [DEC-20: fixar metas mensuráveis de latência, disponibilidade, acessibilidade e recursos computacionais.] O fato de armazenar dados localmente não comprova proteção suficiente. A confidencialidade depende dos controles adotados e verificados.

## 8. Arquitetura de referência e responsabilidades

O sistema possui dois percursos complementares. Na ingestão, recebe o original, transforma o conteúdo quando necessário, classifica, persiste e atualiza os índices. Na consulta, resolve o contexto, seleciona uma operação, recupera dados e apresenta uma resposta ou ação rastreável. O processamento de um diário não depende de um chat estar aberto.

| Componente lógico | Entrada e responsabilidade | Saída |
| --- | --- | --- |
| Interface profissional | Texto, voz, seleção de projeto e navegação | Pedido com contexto visível |
| Orquestrador [AGENT-NAME] | Interpreta pedido e seleciona ferramentas permitidas | Plano de ações delimitado e resposta sustentada |
| Ingestão | Arquivo, imagem, áudio ou texto | Original preservado, texto derivado e metadados |
| Rede temática | Representação numérica do texto | Categoria(s), pontuações e versões |
| Organizador de subtemas | Registros relacionados da mesma pessoa | Agrupamentos pessoais com evidências |
| Serviço longitudinal | Pessoa, período, categorias e critérios | Estatísticas calculadas e conjunto de entradas selecionadas |
| Recuperador RAG | Consulta e filtros de acesso | Trechos com origem e localização |
| Persistência | Operações validadas | Registros duráveis e histórico de alterações |

A colaboração entre agentes deve ser demonstrável por uma troca de informações tipadas e responsabilidades distintas. Não se deve contar cada função ou chamada de modelo como agente sem justificar seu papel. A arquitetura definida adota dois agentes: o Agente 1 organiza subtemas e evidências; o Agente 2 calcula a síntese longitudinal e consulta fontes autorizadas no modo briefing.

Cálculos estatísticos, renderização, validação de acesso e gravações são serviços controlados. Sua execução não depende de o LLM improvisar fórmulas ou comandos. Uma operação determinística produz o mesmo resultado para os mesmos dados e regras; geração de linguagem pode variar. Temperatura baixa não representa garantia universal de determinismo.

[DEC-11: selecionar LLM, runtime local ou serviço externo, framework de orquestração, limites de contexto e política de disponibilidade.] Modelos e bibliotecas são escolhas de implementação. O requisito é preservar o contrato, as fontes e os limites operacionais quando uma implementação for substituída.

## 9. Ferramentas e controle das ações

A interface por chat deve cobrir as operações do produto sem conceder ao modelo acesso irrestrito ao computador. Ferramentas possuem nome, finalidade, esquema de entrada, retorno, limites, erros e efeito de escrita documentados. Os caminhos autorizados e a identidade do projeto são conferidos pelo backend.

| Família de ferramentas | Exemplos de operações | Controle esperado |
| --- | --- | --- |
| Navegação | Localizar paciente, abrir projeto, listar conversas | Identidade inequívoca e autorização |
| Consulta | Listar diários, recuperar fonte, consultar agenda | Filtros e paginação; SQL parametrizado pelo serviço |
| Organização | Propor subtema, renomear, unir e reclassificar | Registro da versão e preservação do original |
| Registro | Criar anotação, importar arquivo, salvar resumo | Conteúdo e destino verificáveis conforme confirmação |
| Visualização | Calcular frequência, abrir dashboard e exportar | Estatística calculada pelo serviço e proveniência |
| Administração | Backup, restauração e exclusão | Escopo explícito, verificações e tratamento de falhas |

[DEC-16: definir quais operações de organização e escrita podem ser automáticas, quais exigem confirmação e quais exigem possibilidade de desfazer.] Solicitar uma tarefa pode autorizar um conjunto delimitado de passos; não é necessário pedir confirmação para cada leitura. Operações destrutivas ou alteração de registro profissional precisam seguir a política acordada.

Cada execução deve ter limite de passos, tempo e tentativas; operação de escrita deve possuir proteção contra repetição. Cancelamento encerra a ação pendente e a interface não anuncia sucesso sem verificar o estado final. [DEC-16: fixar limites operacionais, tratamento de interrupção, recuperação parcial e orçamento de contexto/custo.]

Arquivos importados podem conter instruções conflitantes. O recuperador deve tratá-las como conteúdo, sem alterar o cadastro de ferramentas, permissões ou instruções da aplicação. Materiais metodológicos só se tornam configuração de comportamento mediante ação explícita da profissional, com versão e alcance definidos.

## 10. Projetos, arquivos e modelo de dados

Cada paciente possui um diretório de projeto na área de trabalho administrada pelo aplicativo. O espaço geral contém materiais da profissional e preferências. Conversas, registros, fontes e derivados mantêm identificadores estáveis, independentemente do nome exibido ou da reorganização de pastas.

[DEC-17: escolher o diretório base, a organização física, os formatos dos registros e a estratégia de banco/índice; definir se haverá sincronização entre dispositivos.] O caminho de um arquivo não substitui a identidade de seu proprietário. Uma fotografia importada deve preservar referência ao original e aos textos extraídos dela.

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

Índices, resumos e gráficos são derivados reconstruíveis. Não substituem os originais. Uma alteração ou exclusão deve invalidar versões derivadas conforme política; resultados antigos não podem continuar aparecendo como atuais. [DEC-18: definir tratamento de backups, índices e trilhas de auditoria ao excluir ou corrigir um registro.]

A trilha de execução registra operações e evidências observáveis, sem exigir acesso ao raciocínio interno privado do modelo. Logs operacionais devem evitar cópias integrais de relatos. [DEC-18: definir conteúdo, acesso e prazo de retenção da auditoria.]

## 11. Rede neural para classificação temática

A tarefa da rede é identificar o assunto tratado no texto. Sentimento e polaridade são dimensões diferentes e não integram automaticamente essa saída. Exemplos de temas são Família e Trabalho. A quantidade e as fronteiras das categorias determinam a preparação dos dados e a avaliação.

[DEC-04: aprovar a taxonomia; há oito categorias gerais na hipótese de trabalho, mas faltam a lista final, definições, exemplos de fronteira e tratamento de outros/não identificado.] [DEC-05: escolher tema principal único ou múltiplos temas, com eventual limite de dois ou três e política de abstenção.]

Tema único admite saída softmax e perda categórica; múltiplos temas admitem sigmoid por categoria e perda binária. Um limite de três não significa três redes, nem obrigação de preencher três categorias. Os rótulos precisam representar a presença efetiva de temas; selecionar as maiores pontuações de um classificador exclusivo não demonstra presença simultânea. Fundamentação: F09.

A construção desde a base deve tornar visíveis as operações de treinamento: inicialização, passagem direta, função de perda, retropropagação e atualização. Utilizar apenas uma rede encapsulada de biblioteca não evidencia a implementação dessas etapas. [DEC-08: confirmar com a orientação quais operações precisam ser implementadas pelo grupo e quais bibliotecas auxiliares são permitidas.]

Uma arquitetura didática candidata utiliza texto representado por TF-IDF, uma camada oculta com ReLU e uma saída por categoria. Um embedding pré-treinado é alternativa de representação; sua utilização deve ser declarada e não equivale à construção dessa rede. [DEC-09: escolher TF-IDF ou embeddings, tamanho de entrada, camadas, unidades, ativação, perda, otimizador, taxa de aprendizado, batch e regra de parada.]

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

[DEC-06: selecionar dataset, fonte, versão, licença, quantidade por classe e uso exclusivo de sintéticos ou inclusão de material público autorizado.] O MuPe apresenta narrativas de vida em português brasileiro e constitui candidato para investigação de domínio; não fornece automaticamente a taxonomia do produto (F07). O MASSIVE atende intenções de assistentes, úteis para outra tarefa, e não é substituto direto de dados temáticos de diário (F08).

[DEC-07: definir como os rótulos serão produzidos, se haverá revisão independente, como discordâncias serão resolvidas e como registrar incerteza.] Rótulos gerados por LLM ou regras são supervisão fraca. Avaliação nesses rótulos mede concordância com essa referência; não deve ser apresentada como acurácia validada em uso real. Um juiz LLM complementar também precisa de rubrica e avaliação de limitações.

Separar treino, validação e teste antes de ajustar representação ou modelos. Variações quase idênticas e relatos do mesmo grupo devem ser controlados para evitar vazamento. [DEC-06: definir proporções, agrupamento, deduplicação e tamanho mínimo de teste por classe.] A seleção da configuração usa validação; o teste final é reservado para o experimento fechado.

Comparar a rede com uma referência simples, como a classe majoritária, e com um baseline textual compatível. Apresentar curvas de treino e validação, matriz de confusão, precisão/recall por tema e macro-F1. Em multirrótulo, medir também temas extras incorretos e temas omitidos. [DEC-21: escolher métricas principais, critérios de aceite, política para classes raras, repetições e reporte de incerteza.]

Baixo desempenho também no treino sugere investigar capacidade, representação, otimização e qualidade dos rótulos. Desempenho alto no treino e inferior na validação sugere investigar generalização. Não ajustar tudo simultaneamente: registrar experimentos com alterações controladas e conservar resultados negativos.

## 13. Subtemas pessoais e análise longitudinal

Subtemas organizam assuntos específicos dentro de temas gerais. Família pode conter Cuidado dos avós; uma pessoa pode abordar esse assunto com diferentes sentimentos. A existência de um subtema não modifica a quantidade de categorias da rede e não exige retreinar o classificador por paciente.

O organizador compara registros da mesma pessoa e propõe nomes descritivos com entradas de apoio. Evita duplicatas e permite edição pela psicóloga. A publicação automática de categorias no dashboard não elimina a necessidade de marcar sua origem automática e oferecer correção.

[DEC-14: definir recorrência mínima, janela, evidências, união de duplicatas, relação entre subtema e tema pai e efeitos retroativos das edições.] Uma menção isolada pode sustentar uma sugestão de assunto, mas não comprova recorrência. Referências a bullying devem ser atribuídas ao relato quando explicitadas; conflito inespecífico não sustenta automaticamente essa categoria.

Frequências e coocorrências são operações sobre registros classificados. A unidade pode ser diário, trecho ou ocorrência; a escolha altera os resultados. [DEC-14: fixar a unidade de análise e como evitar contagem duplicada de um mesmo tema no mesmo registro.] Coocorrência não implica causalidade, diagnóstico ou intensidade emocional.

Caso se adote análise longitudinal, o serviço precisa distinguir mudança de padrão textual, mudança de quantidade de entradas e mudança de versão do classificador. Uma queda de contagem pode decorrer de menos diários enviados, sem representar melhora ou piora da pessoa.

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

[DEC-12: escolher documentos completos, critérios de qualidade, direitos de uso, atualização e perguntas que a biblioteca deve responder.] Uma página geral de periódico não substitui o artigo. O conteúdo publicado sobre determinada população não constitui evidência sobre uma pessoa específica.

[DEC-13: comparar recuperação lexical, vetorial e híbrida; escolher embedding, tamanho de trecho, sobreposição, quantidade recuperada, eventual reranking e regra de insuficiência.] O multilingual-e5-small é candidato: produz vetores de 384 dimensões, limita entradas a 512 tokens e especifica prefixos distintos para consultas e passagens (F11). A dimensão do embedding não é o número de temas. A escolha exige avaliação no corpus do projeto.

Para conjuntos pequenos, uma busca exata pode servir de baseline antes de índices aproximados. A infraestrutura pode compartilhar um índice com isolamento lógico ou manter índices separados; ambos precisam demonstrar controle de acesso. [DEC-17: escolher armazenamento e particionamento do índice.] Filtros por pessoa e autorização são obrigatórios; um tema previsto incorretamente não deve excluir silenciosamente todo conteúdo relevante da busca.

O Graphify permanece uma alternativa experimental de recuperação por relações, sem papel obrigatório. [DEC-13: decidir se haverá experimento com grafo e qual ganho mensurável justificaria sua adoção.] O grafo não substitui os originais, o banco de registros ou os testes de rastreabilidade.

## 15. Tempo, visualização e experiência profissional

Cada registro deve distinguir, quando disponível, data do acontecimento, data de criação e data de recebimento. Datas inferidas precisam ser identificadas como inferidas. O filtro selecionado deve ser aplicado de forma consistente ao dashboard, à lista de evidências e à síntese.

[DEC-15: definir data padrão do filtro, fuso horário, limites inclusivos do intervalo, tratamento de data desconhecida e período inicial.] Um período vazio retorna ausência de registros, sem recorrer automaticamente a entradas antigas. Antigo não significa superado: uma marcação de encerrado precisa de origem e regra explícitas. [DEC-15: definir quem pode marcar um assunto como encerrado e como isso afeta consultas atuais e históricas.]

O dashboard utiliza renderização vetorial adaptável ao tamanho da janela. Ao selecionar um tema ou subtema, a profissional acessa os registros que compõem aquela visão. A alternativa textual deve apresentar as mesmas informações.

[DEC-22: escolher biblioteca visual, comportamento em telas pequenas, navegação por teclado e tipo de gráfico para cada métrica.] Gráfico de pizza pressupõe partes de um total definido. Para temas simultâneos, frequências por diário podem somar mais de 100%; barras ou outra representação podem ser mais claras. Se a pizza apresentar distribuição de atribuições, esse denominador precisa ser informado. Nenhum score da rede deve ser apresentado como proporção da vida ou intensidade de sentimento.

O painel mantém visíveis pessoa, período, quantidade de registros e origem automática ou revisada. Anexos e textos de referência podem aparecer ao lado do chat, permitindo conferência sem perder o contexto. O nome do assistente permanece [AGENT-NAME].

## 16. Evidências de engenharia agêntica e aplicação ao projeto

A pesquisa considera fontes primárias disponíveis até **06/11/2026**. Os trabalhos citados fundamentam critérios de projeto; não certificam este produto nem constituem um padrão único do MIT. Recomendações de engenharia de fornecedores são identificadas como tal, sem pressupor adoção de seus serviços.

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

[DEC-21: fixar conjuntos de avaliação, rubricas, métricas principais, limites de aceite e estratégia de revisão humana ou automatizada.] Um LLM juiz pode complementar testes determinísticos, mas concordância entre modelos não estabelece verdade. Resultados sem referência independente devem ser identificados como preliminares.

| Cenário de aceite | Preparação sintética | Resultado esperado |
| --- | --- | --- |
| CA01/02 - Homônimos | Duas pessoas com nome igual | Nenhum projeto escolhido por suposição |
| CA07/08 - Subtema editado | Categoria automática com entradas de apoio | Edição preserva origem e atualiza visualização de modo consistente |
| CA10 - Período vazio | Registros fora da janela solicitada | Resultado vazio; nenhum empréstimo de período anterior |
| CA11 - Fonte ausente | Pergunta não coberta pelo corpus | Insuficiência explícita, sem citação inventada |
| CA11 - Fonte conflitante | Duas versões divergentes | Datas e divergência apresentadas; escolha não é escondida |
| CA14 - Falha de escrita | Erro de persistência após proposta | Nenhuma confirmação falsa nem duplicação na retomada |
| CA17 - Cancelamento | Interrupção durante processamento | Nenhuma escrita tardia após cancelamento confirmado |
| RB07 - Instrução em anexo | Documento manda acessar outro paciente | Permissões e contexto não se alteram |
| CA05 - OCR/transcrição incerta | Imagem ou áudio parcialmente ilegível | Trechos incertos identificados e original acessível |
| CA09 - Tema múltiplo | Uma entrada com duas categorias | Contagem e denominador corretos, sem equivalência com intensidade |

A demonstração inicial utiliza pelo menos dois perfis fictícios para testar isolamento. [DEC-21: definir quantidade de cenários, repetições, falhas toleráveis e critério de bloqueio de versão.] Uma execução bem-sucedida isolada não é suficiente para declarar confiabilidade do sistema.

## 18. MLOps, versionamento e evolução

Cada experimento deve registrar commit de código, versão/hash dos dados, taxonomia, forma de divisão, configuração, modelo, métricas e artefatos. A reprodução deve distinguir ambiente, dependências, semente e limitações de determinismo do hardware e runtime.

[DEC-11: escolher ferramenta de rastreamento e formato dos artefatos.] [DEC-21: definir critérios de promoção, comparação com baseline, rollback e monitoramento de regressões.] Um modelo treinado não deve ser considerado promovido apenas porque seus arquivos foram salvos. A promoção exige evidência de avaliação conforme os critérios acordados.

Mudanças no contrato afetam classificador, persistência, subtemas, RAG, dashboard e testes. A taxonomia deve possuir versão, e resultados históricos devem indicar qual versão foi utilizada. Reprocessamento precisa ser uma operação explícita e auditável. [DEC-14: definir como correções e novas versões afetam estatísticas históricas.]

Documentos e índices também têm ciclo de vida: ingestão, validação, disponibilidade, atualização e remoção. Monitorar registros que não foram indexados e índices desatualizados. O chat deve comunicar quando uma resposta usa um conjunto ainda incompleto.

## 19. Rastreabilidade acadêmica, riscos e validação

| Restrição/necessidade | Requisitos relacionados | Evidência esperada |
| --- | --- | --- |
| Dois agentes colaborando | RF07, RF11, RF13; DEC-10 | Responsabilidades distintas e troca de dados demonstradas |
| Base de conhecimento | RF11, RF15 | Corpus com fontes, ingestão e recuperação |
| Rede neural própria | RF06; DEC-04 a DEC-09 | Código de treino, operações explicadas e avaliação |
| MLOps | RNF04; seção 18 | Execução rastreável e artefatos reproduzíveis |
| API por agentes | RF13; DEC-23 | Chamada efetiva com tratamento de falhas |
| Ética e explicabilidade | RB01 a RB08, RNF01 a RNF03 | Limites, isolamento, fontes e autoria verificáveis |
| Resource recente | F01/F02 e DEC-23 | Data elegível e contribuição explícita |
| MVP e versionamento | RF01 a RF18, RNF07/08 | Recorte integrado acordado, testes e histórico de alterações |

As referências de 2026 F01 e F02 são candidatas recentes para fundamentação. Referências históricas explicam métodos, mas não substituem automaticamente a exigência temporal. A aceitação e a data de corte dependem da orientação.

| Risco | Consequência | Tratamento |
| --- | --- | --- |
| Taxonomia indefinida | Dataset e interfaces incompatíveis | Resolver DEC-04/05 antes de rotular e treinar |
| Referências geradas tratadas como verdade | Qualidade superestimada | Registrar origem e limites; resolver DEC-07/21 |
| Mistura de projeto ou período | Informação incorreta ou acesso indevido | Validar contexto antes da recuperação e testar casos negativos |
| Classificação automática persistida como fato | Interpretação confundida com autoria profissional | Preservar origem e histórico de edição |
| OCR, resumo ou índice desatualizado | Fonte omitida ou alterada na resposta | Conferência do original e ciclo de atualização |
| Autonomia excessiva de ferramentas | Alteração indevida ou repetida | Contratos, limites e política DEC-16 |
| Escopo maior que o prazo | Entregas parciais sem integração | Acordar DEC-23 e medir um fluxo completo |

A validação do documento deve registrar respostas às decisões abertas e revisar sua repercussão nos requisitos. Não é necessário congelar toda a visão de produto para experimentar RAG e rede, mas o experimento precisa declarar suas próprias fronteiras.

## 20. Perguntas para decisão da Equipe 007

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

## 21. Referências e critérios de uso

Data de consulta da pesquisa: 06/11/2026. As fontes a seguir fundamentam conceitos e decisões de engenharia. A inclusão bibliográfica não significa adoção de ferramenta, licença para redistribuir seu conteúdo ou validação do produto.

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

F12. GRAPHIFY LABS. Graphify, documentação do projeto. https://github.com/Graphify-Labs/graphify . Contribuição: alternativa exploratória de recuperação por grafo, sem desempenho comprovado no corpus do produto.

A versão validada deverá registrar a resolução das decisões DEC, os critérios de aceite finais e as evidências efetivamente produzidas. Requisitos, implementação e avaliação devem permanecer vinculados por seus identificadores.
