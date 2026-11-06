# 09 - Ética, Governança de Riscos e Explicabilidade Clínica

## 1. Visão Geral e Atendimento ao Requisito

Este documento estabelece as bases de governança, conformidade legal e princípios éticos para atender integralmente ao **Requisito 7 (Desenvolver uma solução ética e explicável)**.

A aplicação de inteligência artificial em saúde mental lida com a mais íntima das esferas humanas: o sofrimento psíquico. Consequentemente, o projeto rejeita abordagens experimentais negligentes e ancora-se em quatro marcos regulatórios e científicos:
1. **Código de Ética Profissional do Psicólogo (CFP)**.
2. **Lei Geral de Proteção de Dados Pessoais (LGPD - Lei 13.709/2018)**.
3. **NIST AI Risk Management Framework (NIST AI RMF 2026)**.
4. **Evidências Médicas Recentes (JAMA Pediatrics 2026; JAMA Network Open 2025; arXiv:2512.07797)**.

---

## 2. Por que Não Permitir Diálogo Conversacional Direto com o Paciente?

A literatura científica recente adverte vigorosamente contra o uso de chatbots conversacionais generativos como "amigos de desabafo" ou "terapeutas de bolso":

* **Perigo da Sicofania (Sycophancy) e Reforço de Vieses:** LLMs generativos tendem a concordar com o usuário para soar agradáveis. Em saúde mental, um paciente em episódio depressivo ou maníaco com pensamentos distorcidos (ex: *"todos estariam melhor sem mim"* ou *"ninguém no trabalho gosta de mim"*) pode receber validações perniciosas ou complacentes do modelo, agravando a ruminação.
* **Falsa Ilusão de Apoio Terapêutico:** Como apontado por McBain et al. (*JAMA Network Open*, 2025), pacientes jovens confidenciam segredos profundos a robôs, acreditando estar recebendo cuidado clínico, quando na realidade estão apenas gerando tokens probabilísticos desprovidos de empatia ou compromisso deontológico.
* **A Escolha do Diário Multimodal Assíncrono:** Ao estruturar a entrada como um diário (sem réplicas conversacionais imediatas geradas por IA), o sistema preserva o valor terapêutico catártico do ato de escrever/falar, canalizando todo o material para a verdadeira aliança terapêutica humana na próxima consulta.

---

## 3. Conformidade com o Conselho Federal de Psicologia (CFP) e LGPD

### Código de Ética do Psicólogo
- **Artigo 1º (Responsabilidade):** O psicólogo mantém a responsabilidade integral e indelegável pela condução dos atendimentos. O copiloto atua unicamente como assistente analítico.
- **Artigo 9º (Sigilo Profissional):** Garantido por arquitetura técnica:
  - Todo o processamento de texto e transcrição de áudio roda preferencialmente em hardware local (Ollama em loopback local).
  - Nenhum relato de paciente é compartilhado com terceiros para treino de modelos comerciais.
  - Anonimização de registros com uso de identificadores pseudoaleatórios (`patient_id` UUIDv4).

### LGPD (Dados Pessoais Sensíveis)
- Conforme o Artigo 5º, II da LGPD, informações sobre saúde e vida afetiva são dados sensíveis com regime de proteção especial.
- O banco SQLite adota criptografia em repouso e isolamento estrito entre identidades.

---

## 4. Gestão de Risco à Vida e Limitações Explícitas de Autonomia

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           MATRIZ DE RISCO TEXTUAL                               │
├───────────────────────┬─────────────────────────┬───────────────────────────────┤
│ Categoria Detectada   │ Padrão Semântico        │ Ação do Sistema               │
├───────────────────────┼─────────────────────────┼───────────────────────────────┤
│ 'presente'            │ Menções a ideação       │ Destaque visual urgente no    │
│                       │ ativa ou autolesão      │ topo do Dashboard do terapeuta│
├───────────────────────┼─────────────────────────┼───────────────────────────────┤
│ 'indeterminado'       │ Desesperança ambígua,   │ Sinalização para investigação │
│                       │ metáforas de cansaço    │ exploratória em sessão        │
├───────────────────────┼─────────────────────────┼───────────────────────────────┤
│ 'nao_identificado'    │ Ausência de marcadores  │ Processamento temático padrão │
│                       │ lexicais críticos       │ com aviso de responsabilidade │
└───────────────────────┴─────────────────────────┴───────────────────────────────┘
```

> [!WARNING]
> **Isenção de Triagem Emergencial:** O rótulo *"não identificado"* atesta somente a ausência de termos de alerta no texto analisado. Ele **não constitui atestado de ausência de risco real** do indivíduo. O sistema inclui um aviso permanente no rodapé da aplicação reforçando a necessidade do julgamento clínico contínuo do terapeuta.

---

## 5. Explicabilidade: O Fim da Caixa-Preta (Auditoria por Citação Literal)

A principal causa de ceticismo e rejeição de IAs por psicólogos é a falta de transparência nas decisões algorítmicas ("Por que a IA diz que meu paciente está com problemas familiares?").

O sistema resolve esse problema na interface por meio de **Citação Literal Ancorada**:
1. Nenhum subtema ou indicador emocional é exibido sem um link direto para o texto/áudio original.
2. Ao clicar no subtema, o psicólogo vê o **pop-up modal de evidência**, contendo o trecho literal exato que motivou a categorização.
3. Em registros por voz, o psicólogo pode ouvir o trecho exato de 15 segundos do desabafo do paciente, percebendo entonação, pausas, choro ou inflexões de voz que nenhum modelo puramente textual conseguiria capturar.
