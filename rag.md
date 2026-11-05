# 007 - Referências para o RAG do Agente 2

## 1. Contexto do projeto

O **007** é um copiloto de apoio ao profissional. A proposta não é criar um chatbot que atue como psicólogo, diagnostique pessoas ou prescreva condutas. O sistema deve organizar informações, recuperar evidências, explicitar limitações e oferecer perguntas para revisão humana.

### Papel do Agente 2

O Agente 2 recebe a análise estruturada produzida pelo Agente 1 e deve:

1. Recuperar fontes relevantes da base de conhecimento usando RAG.
2. Diferenciar **evidência publicada**, **interpretação do sistema** e **hipótese ainda não validada**.
3. Relacionar achados a dimensões de bem-estar, como autonomia, saúde psicológica, conexão social, pensamento crítico e possível dependência.
4. Resumir resultados com população, método, limitações e contexto.
5. Produzir referências rastreáveis para que o profissional confira a fonte original.
6. Sinalizar quando a base não contém evidência suficiente, em vez de completar lacunas com suposições.

**O Agente 2 não deve:** diagnosticar, estimar risco clínico individual como se fosse instrumento validado, recomendar tratamento ou apresentar correlação como causalidade.

---

## 2. Fontes prioritárias

As fontes estão agrupadas por função. Páginas institucionais são boas portas de entrada, mas, quando possível, indexem o artigo, relatório ou documento integral - não apenas a página de divulgação.

### 2.1. Métricas e estrutura de impacto

#### A. MIT Media Lab - ImpactBench

- **Link:** https://impactbench.media.mit.edu/explore
- **Página de métricas:** https://impactbench.media.mit.edu/metrics
- **Visão geral:** https://www.media.mit.edu/projects/impactbench/overview/
- **Tipo:** benchmark/estrutura de métricas.
- **Por que usar:** referência para organizar possíveis impactos positivos e negativos da IA sobre o bem-estar. Ajuda a pensar em dimensões e métricas, em vez de reduzir “bem-estar” a uma única pontuação.
- **Como aplicar no RAG:** extrair categorias, definições, métricas, descrições operacionais e referências associadas. Use essas categorias para classificar evidências e organizar o relatório do Agente 2.
- **Cuidados:** o ImpactBench é uma referência metodológica; suas categorias não são, por si só, escalas clínicas nem provas de que determinado sistema causa um efeito.
- **Prioridade:** muito alta.

#### B. MIT Media Lab - AI and Human Psychology

- **Link:** https://www.media.mit.edu/projects/ai-and-human-psychology/overview/
- **Tipo:** projeto de pesquisa/visão geral institucional.
- **Por que usar:** contexto de pesquisa sobre a interação entre IA e psicologia humana.
- **Como aplicar no RAG:** usar para descobrir publicações, hipóteses e linhas de pesquisa relacionadas a efeitos psicológicos e comportamentais. Sempre que possível, indexar também as publicações originais citadas.
- **Cuidados:** a página de projeto não substitui a leitura dos estudos individuais nem garante que todos os achados se apliquem ao público brasileiro.
- **Prioridade:** alta.

#### C. MIT - estudo longitudinal controlado sobre uso de chatbots

- **Link:** https://www.media.mit.edu/publications/how-ai-and-human-behaviors-shape-psychosocial-effects-of-chatbot-use-a-longitudinal-controlled-study/
- **Tipo:** publicação de pesquisa.
- **Por que usar:** investiga relações entre uso prolongado de chatbots e efeitos psicossociais.
- **Como aplicar no RAG:** recuperar o desenho do estudo, a amostra, as condições comparadas, os resultados e as limitações para evitar resumos simplistas sobre “IA faz bem” ou “IA faz mal”.
- **Cuidados:** diferencie os resultados das condições experimentais das associações observadas entre padrões voluntários de uso e resultados. Associação não demonstra causalidade. Confira os detalhes no texto integral antes de registrar números ou conclusões.
- **Prioridade:** muito alta.

#### C.1. MIT Media Lab - Simulação de riscos psicológicos em interações Humano-IA

- **Link:** https://arxiv.org/abs/2511.08880 (PDF: https://arxiv.org/pdf/2511.08880)
- **Título:** *Simulating Psychological Risks in Human-AI Interactions: Real-Case Informed Modeling of AI-Induced Addiction, Anorexia, Depression, Homicide, Psychosis, and Suicide*.
- **Autores / Laboratório:** Pataranutaporn, P., Picard, R., Maes, P. et al. (MIT Media Lab / Advancing Humans with AI).
- **Tipo:** modelagem e simulação computacional informada por casos reais.
- **Por que usar:** detalha os mecanismos de risco de jovens utilizando LLMs como terapeutas (sycophancy, reforço de ideações depressivas, dependência afetiva parassocial e quebra de mediação humana).
- **Como aplicar no RAG:** compor a base de taxonomias de risco para fundamentar as hipóteses investigativas geradas para o psicólogo.
- **Cuidados:** simulação e modelagem conceitual/qualitativa de riscos extremos; não deve ser usada como métrica estatística de prevalência clínica.
- **Prioridade:** muito alta.

### 2.2. Evidências empíricas e revisões sobre IA e saúde mental

#### D. Journal of Adolescent Health - uso de IA generativa e bem-estar socioemocional

- **Referência de busca:** https://www.sciencedirect.com/journal/journal-of-adolescent-health
- **Tipo:** artigo científico; localizar e registrar o artigo exato usado pelo grupo.
- **Por que usar:** pesquisas nessa área têm examinado diferenças entre usos socioemocionais e usos voltados à aprendizagem, incluindo associações com indicadores de saúde mental em jovens adultos.
- **Como aplicar no RAG:** indexar o artigo completo e extrair população, faixa etária, definição de uso, instrumentos, resultados e limitações.
- **Cuidados:** a associação relatada em estudo observacional transversal não prova que o uso de IA causou sintomas. Não extrapolar resultados de uma população para todos os adolescentes, adultos ou usuários brasileiros.
- **Prioridade:** alta.
- **Nota de desenvolvimento:** não ingiram a página genérica do periódico como se fosse o estudo. Confirmem título, autores, ano e DOI do artigo específico antes de incluí-lo no corpus.

#### E. JAMA Pediatrics - pesquisa sobre uso de chatbots para aconselhamento de saúde mental

- **Referência de busca:** https://jamanetwork.com/journals/jamapediatrics
- **Tipo:** artigo científico/levantamento.
- **Por que usar:** pode ajudar a compreender frequência de uso, percepção de utilidade e se jovens contam a outras pessoas que usam chatbots para aconselhamento.
- **Como aplicar no RAG:** registrar exatamente país, amostra, faixa etária, período, perguntas do levantamento e resultados.
- **Cuidados:** percepção de utilidade não equivale a eficácia clínica ou segurança. Resultados de uma pesquisa nos Estados Unidos não devem ser apresentados como estimativa para o Brasil. Confirmar a referência bibliográfica exata antes de indexar.
- **Prioridade:** alta.

#### F. npj Digital Medicine - revisão de escopo sobre danos de chatbots de LLM em saúde mental

- **Referência de busca:** https://www.nature.com/npjdigitalmed/
- **Tipo:** revisão de escopo.
- **Por que usar:** oferece uma visão organizada de riscos relatados na literatura, incluindo dimensões psicológicas, relacionais/comportamentais, cognitivas, falhas nas respostas e governança.
- **Como aplicar no RAG:** criar uma taxonomia de riscos com definição, mecanismo proposto, evidência, gravidade descrita pelos autores, contexto e limitações.
- **Cuidados:** revisão de escopo não significa que todos os riscos ocorram em todos os sistemas ou usuários. A qualidade dos estudos incluídos pode variar. Confirme título, autores, ano e DOI da revisão antes de incorporá-la.
- **Prioridade:** muito alta.

### 2.3. Pesquisa brasileira e contexto local

#### G. USP - dissertação sobre soluções tecnológicas inclusivas em saúde mental

- **Link:** https://teses.usp.br/teses/disponiveis/27/27163/tde-31032025-122629/pt-br.html
- **Título:** _Desenvolvimento de soluções tecnológicas inclusivas em saúde mental: a interseção entre ciência da informação, inteligência artificial ética e neurodiversidade_.
- **Tipo:** dissertação acadêmica.
- **Por que usar:** aproxima o tema de inclusão, ética, tecnologia e saúde mental no contexto de pesquisa brasileiro.
- **Como aplicar no RAG:** extrair problema de pesquisa, público, conceitos, metodologia, recomendações e limitações. Marcar claramente quais conclusões são da dissertação e quais são achados de fontes citadas por ela.
- **Cuidados:** dissertação não equivale automaticamente a evidência clínica validada; verificar método, banca, data e acesso ao texto integral.
- **Prioridade:** alta.

#### H. USP - dissertação sobre detecção de sinais relacionados à saúde mental em publicações de redes sociais

- **Link:** https://teses.usp.br/teses/disponiveis/100/100131/tde-26112024-115052/pt-br.html
- **Título:** _Detecção precoce de transtornos de saúde mental a partir de publicações em redes sociais_.
- **Tipo:** dissertação acadêmica.
- **Por que usar:** referência brasileira para discutir processamento de linguagem, classificação e limites de inferências a partir de texto.
- **Como aplicar no RAG:** identificar dados utilizados, rótulos, modelos, métricas, validação, limitações e riscos de falsos positivos/falsos negativos.
- **Cuidados:** detecção computacional de padrões em textos não equivale a diagnóstico. Não transportar o modelo ou seus resultados para relatos clínicos sem validação independente.
- **Prioridade:** alta.

#### I. USP/ICMC - pesquisa sobre identificação de sinais de depressão em redes sociais

- **Link:** https://www.icmc.usp.br/noticias/5556-sistema-criado-na-usp-identifica-sinais-de-depressao-nas-redes-sociais
- **Tipo:** notícia institucional sobre pesquisa.
- **Por que usar:** ponto de partida para localizar trabalho acadêmico brasileiro sobre análise de linguagem e sinais relacionados à saúde mental.
- **Como aplicar no RAG:** usar a notícia para encontrar a publicação original; priorizar artigo, tese, dados metodológicos e avaliação do modelo no corpus final.
- **Cuidados:** não usar uma notícia como única evidência de desempenho ou validade. O sistema do PontePsi não deve diagnosticar a partir de linguagem.
- **Prioridade:** média.

### 2.4. Ética, privacidade e governança

#### J. American Psychological Association (APA) - orientação ética sobre IA na prática da psicologia

- **Link:** https://www.apa.org/topics/artificial-intelligence-machine-learning/ethical-guidance-ai-professional-practice
- **Tipo:** orientação profissional.
- **Por que usar:** oferece princípios para avaliar o uso de IA na prática psicológica, incluindo responsabilidades profissionais e necessidade de avaliação crítica.
- **Como aplicar no RAG:** transformar orientações em uma lista de verificação para transparência, supervisão humana, competência profissional, privacidade e avaliação de riscos.
- **Cuidados:** é orientação de uma associação dos Estados Unidos, não substitui as regras do Conselho Federal de Psicologia nem a legislação brasileira.
- **Prioridade:** muito alta.

#### K. APA - alerta sobre chatbots generativos e aplicativos de bem-estar

- **Link:** https://www.apa.org/topics/artificial-intelligence-machine-learning/health-advisory-chatbots-wellness-apps
- **Tipo:** alerta/orientação de saúde pública profissional.
- **Por que usar:** ajuda a identificar riscos e perguntas críticas sobre produtos que oferecem apoio emocional ou alegações de bem-estar.
- **Como aplicar no RAG:** recuperar recomendações de cautela e usá-las para compor a seção de riscos e salvaguardas do relatório.
- **Cuidados:** conferir a data e eventuais atualizações da orientação. Não tratar o documento como avaliação de cada produto específico.
- **Prioridade:** alta.

#### L. Organização Mundial da Saúde (OMS/WHO) - ética e governança de IA para a saúde

- **Link:** https://www.who.int/publications/i/item/9789240029200
- **Tipo:** relatório de orientação global.
- **Por que usar:** oferece princípios de ética e governança aplicáveis à discussão de IA em saúde.
- **Como aplicar no RAG:** estruturar critérios para autonomia, segurança, transparência, responsabilidade, inclusão e governança.
- **Cuidados:** publicação de 2021; procurar orientações mais recentes que a complementem. É uma referência de governança, não uma validação do sistema PontePsi.
- **Prioridade:** muito alta.

#### M. Brasil - LGPD e dados pessoais sensíveis

- **Fonte oficial:** https://www.gov.br/esporte/pt-br/acesso-a-informacao/lgpd
- **Tipo:** legislação e material institucional brasileiro.
- **Por que usar:** dados referentes à saúde são dados pessoais sensíveis sob a LGPD. O desenho do MVP precisa minimizar coleta, acesso, retenção e exposição.
- **Como aplicar no RAG:** manter legislação e orientações oficiais em uma coleção de governança separada, com data de vigência/consulta e identificação dos artigos relevantes.
- **Cuidados:** validar o texto legal e as orientações aplicáveis com a equipe responsável. A página institucional é uma porta de entrada; a fonte normativa principal é a Lei nº 13.709/2018 no portal oficial da legislação.
- **Prioridade:** muito alta.

#### N. Conselho Federal de Psicologia (CFP) - normas profissionais

- **Portal:** https://site.cfp.org.br/
- **Tipo:** órgão regulador profissional; localizar resoluções e orientações vigentes.
- **Por que usar:** o projeto precisa respeitar as regras brasileiras da prática psicológica, incluindo a Resolução CFP nº 9/2024, após confirmar o texto oficial e sua aplicabilidade ao caso.
- **Como aplicar no RAG:** indexar a resolução oficial e documentos complementares, registrar número, data, vigência, artigos pertinentes e URL oficial.
- **Cuidados:** não se deve inferir obrigações jurídicas a partir de resumos de terceiros. Confirmar no portal oficial se houve alterações, revogações ou normas posteriores.
- **Prioridade:** muito alta.

### 2.5. Benchmark de avaliação de respostas de IA em saúde mental

#### O. OpenAI - MentalHealthBench

- **Link:** https://openai.com/index/introducing-mentalhealthbench/
- **Tipo:** benchmark divulgado em setembro de 2026.
- **Por que usar:** pode servir de referência para pensar em avaliação estruturada de respostas de IA em conversas relacionadas à saúde mental, incluindo avaliação especializada.
- **Como aplicar no RAG:** estudar a descrição metodológica pública para inspirar critérios de avaliação, rubricas de revisão e cenários de teste do PontePsi.
- **Cuidados:** não assumir que o benchmark é de código aberto, que seus dados estão disponíveis ou que o PontePsi pode reutilizá-los. Verificar licença, acesso, metodologia e condições de uso. Não tratar o benchmark como evidência de eficácia clínica do PontePsi.
- **Prioridade:** alta.

---

## 3. Organização recomendada do corpus

Mantenham coleções lógicas separadas. Isso evita que uma orientação ética seja recuperada como se fosse um resultado empírico, ou que uma hipótese seja apresentada como fato.

| Coleção                    | Conteúdo                                                          | Uso principal                                        |
| -------------------------- | ----------------------------------------------------------------- | ---------------------------------------------------- |
| `impacto_ia_bem_estar`     | MIT ImpactBench e trabalhos sobre impactos psicossociais          | Organizar dimensões e métricas de impacto            |
| `evidencias_psicossociais` | Estudos empíricos e revisões sobre chatbots, relações e bem-estar | Recuperar achados, métodos e limitações              |
| `pesquisa_brasil`          | Teses, dissertações e estudos brasileiros                         | Contextualizar métodos, inclusão e limitações locais |
| `etica_governanca`         | APA, OMS, LGPD, CFP e normas oficiais                             | Verificar princípios, obrigações e salvaguardas      |
| `benchmarks_avaliacao`     | Benchmarks e protocolos de avaliação de sistemas de IA            | Construir testes e rubricas de avaliação             |

**Importante:** o RAG deve recuperar a fonte e seus trechos de apoio. Não use apenas resumos gerados por outro modelo como base definitiva se o texto original estiver disponível.

---

## 4. Metadados mínimos por documento

Para cada fonte, armazenem os seguintes campos. Eles ajudam o retriever a filtrar por tipo de evidência, ano, público e jurisdição.

```json
{
  "document_id": "mit_chatbot_longitudinal_2025",
  "title": "Título oficial da publicação",
  "authors": ["Autor 1", "Autor 2"],
  "institution": "MIT Media Lab",
  "year": 2025,
  "source_type": "estudo_empirico",
  "country_or_context": "conforme descrito na fonte",
  "population": "descrição exata da amostra",
  "methodology": "ensaio, estudo transversal, revisão etc.",
  "topic_tags": ["bem_estar", "uso_de_chatbot"],
  "claims": [
    {
      "claim": "Resumo fiel de um achado",
      "evidence_type": "resultado_observado",
      "limitations": "Limitações descritas pelos autores",
      "source_location": "página, seção, tabela ou DOI"
    }
  ],
  "url": "URL oficial ou DOI",
  "access_date": "AAAA-MM-DD",
  "license_or_usage_terms": "verificado / pendente",
  "full_text_available": false,
  "corpus_version": "0.1"
}
```

Não preencham campos ausentes com suposições. Usem `null`, `"não informado"` ou `"pendente de verificação"` quando necessário.

### Rótulos de evidência recomendados

- `resultado_observado`: resultado diretamente relatado no estudo.
- `associacao`: relação observada sem estabelecer causalidade.
- `causalidade_testada`: usar apenas quando o desenho e a análise permitirem essa interpretação, descrevendo as condições.
- `recomendacao_normativa`: orientação de uma norma ou entidade.
- `hipotese`: possibilidade ainda não validada.
- `limitacao`: ressalva importante sobre a fonte.
- `metric_definition`: definição de métrica ou dimensão de impacto.

---

## 5. Pipeline RAG sugerido

1. **Descoberta:** localizar a publicação original a partir da lista inicial.
2. **Verificação:** conferir título, autores, ano, DOI/URL, metodologia, versão, licença e acesso.
3. **Ingestão:** baixar apenas documentos cujo acesso e uso sejam permitidos.
4. **Extração:** preservar títulos, seções, tabelas e referências; registrar páginas quando possível.
5. **Chunking:** dividir por seção ou subtítulo, em vez de cortar texto arbitrariamente. Como ponto inicial, testar blocos de 400–800 tokens com sobreposição de 60–100 tokens e ajustar com avaliação.
6. **Metadados:** associar cada bloco ao documento, seção, página, ano, tipo de fonte, população e tags.
7. **Embeddings:** gerar vetores com um modelo documentado e versionado.
8. **Armazenamento vetorial:** por exemplo, PostgreSQL + pgvector; manter os arquivos originais e metadados em armazenamento separado.
9. **Recuperação:** combinar similaridade semântica com filtros por tipo de fonte, ano, contexto e tópico. Considerar busca híbrida lexical + vetorial.
10. **Reranking (opcional):** reordenar trechos recuperados por relevância.
11. **Geração:** pedir ao Agente 2 uma síntese limitada aos trechos recuperados, com citações, ressalvas e nível de confiança qualitativo.
12. **Validação:** testar se as afirmações estão apoiadas nas fontes, se as citações apontam para o trecho correto e se o sistema sabe dizer “não há evidência suficiente”.
13. **Revisão humana:** permitir que o profissional abra a fonte e corrija ou rejeite a síntese.

### Instrução-base sugerida para o Agente 2

```text
Você é um agente de síntese de evidências para apoiar profissionais, não para
diagnosticar ou recomendar tratamento.

Use somente as fontes recuperadas para afirmações sobre evidências. Para cada
achado relevante, informe:
- o que a fonte observou ou recomenda;
- tipo de fonte e metodologia;
- população e contexto;
- limitações e incertezas;
- citação rastreável para o documento e trecho.

Diferencie explicitamente resultado observado, associação, recomendação normativa
e hipótese. Não transforme associação em causalidade. Não generalize resultados
de outro país para o Brasil sem ressalva. Se as fontes não sustentarem uma
conclusão, diga que a evidência disponível é insuficiente.

Não forneça diagnóstico, prescrição, avaliação clínica automatizada ou decisão
sobre o paciente. Apresente pontos para revisão do profissional e deixe claro
que a saída exige validação humana.
```

---

## 6. Como o RAG se conecta aos dois agentes

### Agente 1 - organização do relato

- Recebe um cenário sintético no MVP.
- Extrai tópicos, contexto de uso e percepções expressas no relato.
- Não atribui diagnóstico nem infere estados clínicos não declarados.
- Retorna uma estrutura JSON com trechos de origem e incertezas.

### Agente 2 - evidências e interpretação responsável

- Recebe a estrutura do Agente 1.
- Consulta o RAG nas coleções relevantes.
- Compara o caso descrito com evidências publicadas, sem afirmar que o indivíduo apresenta o mesmo efeito.
- Entrega síntese, fontes, limitações, riscos possíveis e perguntas para discussão humana.

### Exemplo de saída estruturada

```json
{
  "summary": "Síntese descritiva do padrão relatado, sem diagnóstico.",
  "reported_patterns": [
    {
      "pattern": "O usuário relata recorrer ao chatbot para apoio emocional",
      "evidence_in_input": "trecho literal ou referência ao trecho",
      "confidence": "alta"
    }
  ],
  "related_evidence": [
    {
      "claim": "Resumo fiel do achado da fonte",
      "evidence_type": "associacao",
      "source_id": "id_da_fonte",
      "source_location": "seção/página",
      "limitations": "Limitação pertinente"
    }
  ],
  "evidence_gaps": ["O que as fontes não permitem concluir"],
  "questions_for_professional_review": [
    "Que papel a ferramenta ocupa em relação às fontes de apoio humano?"
  ],
  "human_review_required": true
}
```

O campo `confidence` não deve ser apresentado como probabilidade clínica. Se utilizado, descreva-o como confiança na extração textual e valide sua calibração.

---

## 7. Avaliação: como saber se o RAG está funcionando

Criem um conjunto de cenários sintéticos e perguntas de referência revisadas pelo grupo. Não usem conversas reais de pacientes no protótipo inicial.

### Testes mínimos

1. **Recall@k:** a fonte correta aparece entre os `k` trechos recuperados?
2. **Precisão das citações:** cada afirmação pode ser confirmada no trecho citado?
3. **Fidelidade:** a síntese não acrescenta fatos que não aparecem nas fontes?
4. **Tratamento da incerteza:** o agente admite quando a evidência é insuficiente?
5. **Distinção entre evidência e hipótese:** o agente identifica corretamente associações e limitações?
6. **Cobertura equilibrada:** o sistema recupera evidências de possíveis benefícios e danos, sem procurar apenas um lado?
7. **Consistência:** perguntas equivalentes produzem respostas compatíveis?
8. **Segurança:** o sistema evita diagnóstico, prescrição e conclusões clínicas automatizadas?
9. **Utilidade para o profissional:** revisores conseguem verificar e contestar a síntese com facilidade?

### Métricas sugeridas

- `Recall@5` ou `Recall@10` para recuperação.
- Percentual de afirmações factuais com fonte verificável.
- Percentual de citações corretas.
- Taxa de afirmações sem sustentação.
- Taxa de abstenção adequada quando não há evidência.
- Concordância entre avaliadores humanos em uma rubrica definida.
- Tempo necessário para revisar e confirmar uma síntese.

Definam metas após estabelecer uma linha de base. Não apresentem uma meta escolhida pelo grupo como resultado já alcançado ou como validação clínica.

---

## 8. Ética, privacidade e segurança

- Comecem com cenários sintéticos, sem nomes, contatos ou transcrições reais.
- Não coletem dados sensíveis desnecessários. Dados de saúde são dados pessoais sensíveis sob a LGPD.
- Definam acesso por perfil, retenção mínima, exclusão, logs seguros e proteção de segredos.
- Não enviem dados identificáveis a APIs externas. Verifiquem termos, retenção e uso dos dados do fornecedor antes de qualquer integração.
- Não usem o sistema para diagnóstico, triagem clínica autônoma, prescrição ou decisões automatizadas sobre pessoas.
- Mostrem fonte, limitações, versão do corpus e data de atualização.
- Garantam que o profissional possa revisar, editar, rejeitar ou ignorar o resultado.
- Testem vieses e diferenças de desempenho entre linguagem informal, variedades linguísticas e grupos representados nos dados.
- Criem um fluxo de interrupção/encaminhamento definido por profissionais para conteúdos que indiquem necessidade de ajuda urgente; o modelo não deve improvisar protocolos clínicos.
- Antes de qualquer piloto com pessoas ou dados reais, façam revisão ética, jurídica, de segurança e das normas profissionais aplicáveis.

Este documento é uma referência técnica para o protótipo, não aconselhamento jurídico ou clínico.

---

## 9. Versionamento e MLOps

Versionem o corpus e a configuração do RAG junto com o código. Uma alteração em documentos, embeddings, prompts ou modelo pode mudar o resultado.

Registrem em cada execução:

- versão do código;
- versão do corpus;
- modelo e versão dos embeddings;
- configuração de chunking e recuperação;
- modelo de linguagem e versão;
- prompt do Agente 2;
- data da execução;
- fontes e trechos recuperados;
- resultado da avaliação automatizada e revisão humana.

Não comitem PDFs ou dados protegidos sem verificar a licença. No Git, prefiram manter os metadados, IDs e scripts de ingestão, e armazenar os documentos em local autorizado. Registrem o hash ou identificador da versão do arquivo original quando apropriado.

---

## 10. Plano de execução para o grupo

### Etapa 1 - Curadoria

- [ ] Confirmar os dados bibliográficos das fontes prioritárias.
- [ ] Localizar textos integrais e verificar licença/termos.
- [ ] Separar fontes primárias de notícias e páginas institucionais.
- [ ] Registrar metadados e limitações.

### Etapa 2 - Corpus inicial

- [ ] Começar com 8–15 documentos bem verificados, não centenas de páginas pouco confiáveis.
- [ ] Incluir fontes de impacto, evidência empírica, contexto brasileiro e governança.
- [ ] Fazer ingestão e chunking com preservação de páginas/seções.
- [ ] Gerar embeddings e armazenar metadados.

### Etapa 3 - Recuperação

- [ ] Criar 20–30 perguntas de teste com fontes esperadas.
- [ ] Medir Recall@k e ajustar chunking, filtros e busca híbrida.
- [ ] Testar perguntas ambíguas e perguntas sem resposta no corpus.

### Etapa 4 - Agente 2

- [ ] Implementar respostas com referências rastreáveis.
- [ ] Separar achados, limitações, hipóteses e recomendações normativas.
- [ ] Implementar abstenção quando a evidência for insuficiente.
- [ ] Adicionar revisão humana.

### Etapa 5 - Validação e demonstração

- [ ] Testar com cenários sintéticos positivos, negativos e ambíguos.
- [ ] Medir fidelidade das citações, afirmações sem suporte e utilidade para revisores.
- [ ] Demonstrar como o profissional abre a fonte e revisa o relatório.
- [ ] Documentar limitações e próximos passos.

---

## 11. Lista de verificação antes de colocar uma fonte no RAG

Para cada documento, respondam:

- [ ] A referência bibliográfica está confirmada?
- [ ] O texto integral foi consultado?
- [ ] É pesquisa primária, revisão, orientação, legislação ou divulgação?
- [ ] Qual é a população e o contexto?
- [ ] Qual é o desenho metodológico?
- [ ] O que a fonte permite afirmar?
- [ ] O que ela não permite afirmar?
- [ ] Há limitações ou conflitos de interesse?
- [ ] O texto pode ser armazenado e processado segundo sua licença/termos?
- [ ] As citações podem apontar para seção, página ou DOI?
- [ ] O conteúdo está atualizado e não foi substituído por uma norma mais recente?
- [ ] A fonte está identificada como evidência, orientação normativa ou hipótese?

---

## 12. Referências e portais para começar

### MIT

- ImpactBench - explorar: https://impactbench.media.mit.edu/explore
- ImpactBench - métricas: https://impactbench.media.mit.edu/metrics
- ImpactBench - visão geral: https://www.media.mit.edu/projects/impactbench/overview/
- AI and Human Psychology: https://www.media.mit.edu/projects/ai-and-human-psychology/overview/
- Estudo longitudinal sobre efeitos psicossociais de chatbots: https://www.media.mit.edu/publications/how-ai-and-human-behaviors-shape-psychosocial-effects-of-chatbot-use-a-longitudinal-controlled-study/

### Pesquisa brasileira / USP

- Dissertação sobre tecnologia inclusiva e saúde mental: https://teses.usp.br/teses/disponiveis/27/27163/tde-31032025-122629/pt-br.html
- Dissertação sobre detecção de sinais em redes sociais: https://teses.usp.br/teses/disponiveis/100/100131/tde-26112024-115052/pt-br.html
- Pesquisa do ICMC/USP sobre sinais de depressão em redes sociais: https://www.icmc.usp.br/noticias/5556-sistema-criado-na-usp-identifica-sinais-de-depressao-nas-redes-sociais

### Ética e governança

- APA - orientação ética sobre IA na psicologia: https://www.apa.org/topics/artificial-intelligence-machine-learning/ethical-guidance-ai-professional-practice
- APA - alerta sobre chatbots e apps de bem-estar: https://www.apa.org/topics/artificial-intelligence-machine-learning/health-advisory-chatbots-wellness-apps
- OMS - ética e governança de IA para saúde: https://www.who.int/publications/i/item/9789240029200
- CFP - portal oficial: https://site.cfp.org.br/
- Portal institucional brasileiro sobre LGPD: https://www.gov.br/esporte/pt-br/acesso-a-informacao/lgpd

### Benchmarks

- OpenAI - MentalHealthBench: https://openai.com/index/introducing-mentalhealthbench/

### Periódicos para localizar os artigos exatos

- Journal of Adolescent Health: https://www.sciencedirect.com/journal/journal-of-adolescent-health
- JAMA Pediatrics: https://jamanetwork.com/journals/jamapediatrics
- npj Digital Medicine: https://www.nature.com/npjdigitalmed/

**Nota bibliográfica importante:** os portais de periódicos acima são pontos de partida para localizar os estudos mencionados. Antes de usar um estudo como evidência, preencham título, autores, ano, DOI, desenho metodológico e limitações a partir da publicação original. Não citem a página geral do periódico como se fosse um artigo específico.

---

### Documentação Complementar do Agente 2
Para aprofundamento da arquitetura, RAG, impacto clínico e tarefas do Agente 2, consulte os documentos dedicados em docs/:
- [Concepção e Arquitetura do Agente 2](docs/agente-2-concepcao-e-arquitetura.md)
- [Estratégia de RAG e Base de Conhecimento](docs/agente-2-rag-estrategia-e-dados.md)
- [Valor Agregado, Impacto Clínico e Governança Ética](docs/agente-2-valor-agregado-e-impacto.md)
- [Roadmap e Backlog de Tarefas do Agente 2](docs/agente-2-roadmap-e-tasks.md)

## 13. Resultado esperado do MVP

Ao final do MVP, o Agente 2 deve conseguir responder a uma pergunta como:

> “Que evidências publicadas ajudam a contextualizar este padrão de uso de IA relatado, quais dimensões de bem-estar podem ser relevantes, quais são as limitações dessas evidências e o que deve ser revisado por um profissional?”

A resposta ideal:

- resume o padrão relatado sem rotular a pessoa;
- apresenta achados relevantes com citações verificáveis;
- mostra benefícios possíveis e riscos possíveis, sem forçar falsa equivalência;
- diferencia associação, causalidade, orientação normativa e hipótese;
- identifica lacunas e incertezas;
- sugere perguntas para reflexão profissional, não decisões clínicas;
- permite abrir e conferir cada fonte.

**Princípio central:** o RAG deve tornar o Agente 2 mais rastreável e verificável - não apenas mais convincente.
