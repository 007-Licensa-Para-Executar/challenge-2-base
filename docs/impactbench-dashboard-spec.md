# 10 - Especificação da Interface do Psicólogo e UX Inspirada no MIT ImpactBench

> **Estado da especificação:** esta página define a interface pretendida.
> A implementação visual ainda não existe no repositório. Trechos de UI, dados e
> gráficos abaixo são exemplos de produto, não resultados atuais.

## 1. Visão Geral da Interface e Filosofia de Design

A interface da nossa ferramenta foi concebida para atender à necessidade expressa de aproximar a experiência visual e analítica daquela consolidada na plataforma **MIT ImpactBench (`impactbench.media.mit.edu/explore`)**.

No ImpactBench, os avaliadores navegam em múltiplos níveis concêntricos:
1. **Métricas de Alto Nível:** Visão panorâmica dos domínios (Psicológico, Físico, Social).
2. **Desdobramento Granular:** Subáreas e indicadores pontuais de florescimento ou vulnerabilidade.
3. **Rastreabilidade até as Transcrições Primárias:** Capacidade de clicar em qualquer métrica e inspecionar os turnos de fala e palavras exatas que deram origem ao score.

Transpondo essa filosofia para o consultório de psicologia:
- O paciente desabafa no seu **Diário Multimodal** (texto, áudio ou foto) ao longo da semana.
- A **Rede Neural MLP (com SBERT)** e os dois agentes locais processam os relatos em segundo plano, identificando e atribuindo percentuais (`%`) aos **6 Temas Clínicos**.
- O psicólogo abre a tela do paciente no **Dashboard Clínico (`/explore`)**, visualiza os **6 Temas Clínicos** (`Autopercepção`, `Vínculos`, `Desempenho`, `Físico`, `Rupturas`, `Outros`), clica no tema desejado para desdobrar os **Subtemas** e, ao clicar em qualquer subtema, abre um painel de evidência literal.

---

## 2. As Duas Extremidades da Experiência (UX)

```
┌────────────────────────────────────────────────────────┐
│            EXPERIÊNCIA DO PACIENTE (DIÁRIO)            │
│  "Desabafo Autêntico Sem Julgamento de Robôs"         │
├────────────────────────────────────────────────────────┤
│ • Escrever relato livre de texto                       │
│ • Gravar mensagem de áudio (desabafo espontâneo)       │
│ • Anexar foto ou desenho expressivo                    │
│ • Ausência de conselhos de IA imediata                 │
│ • Aviso claro: "Este relato subsidiará sua consulta"   │
└────────────────────────────────────────────────────────┘
                           │
             [ Processamento Neural & Multiagente ]
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│           EXPERIÊNCIA DO PSICÓLOGO (/EXPLORE)          │
│   "Navegação Hierárquica Inspirada no ImpactBench"     │
├────────────────────────────────────────────────────────┤
│ Nível 1: Visão Panorâmica & 6 Temas Clínicos Padrão   │
│ Nível 2: Expansão Interativa em Subtemas Específicos   │
│ Nível 3: Pop-up de Rastreabilidade e Evidência Literal │
│ Nível 4: Briefing Normativo Citado pelo Agente 2 (RAG)│
└────────────────────────────────────────────────────────┘
```

---

## 3. Arquitetura da Tela do Psicólogo (`/explore`)

### 3.1 Faixa Superior: Metadados do Paciente e Indicadores de Bem-Estar
Inspirada nos cartões do ImpactBench, a faixa superior exibe:
- **Identificação Pseudonimizada:** Paciente `#PAC-8419` | Última consulta: 02/11/2026.
- **Seletor de Janela Temporal:** [Últimos 7 dias (Padrão)] | [Últimos 14 dias] | [Últimos 30 dias].
- **Frequência de Registros:** 6 desabafos registrados (4 textos, 2 áudios).
- **Resumo Afetivo da Janela:** Frequências ou combinações de sentimentos observadas no período.
- **Card de Risco Sintático:** Status descritivo com sinalizador (Verde: *Sem termos de alerta* | Âmbar: *Indício textual de desespero/desesperança para averiguação em sessão*).

---

### 3.2 O Grid dos 6 Temas Clínicos Padrão
O corpo central exibe os **6 Temas** identificados pela Rede Neural MLP (com seus respectivos percentuais `%`) em formato de cartões visuais (*Cards*) ou gráfico radial (*Sunburst/Radar Chart*):

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           PAINEL DOS 6 TEMAS CLÍNICOS                           │
├───────────────────────┬─────────────────────────┬───────────────────────────────┤
│ 🪞 AUTOPERCEPÇÃO (68%)│ 🤝 VÍNCULOS (91%)       │ 💼 DESEMPENHO (84%)           │
│ [2 registros | Culpa] │ [4 registros | Raiva]   │ [3 registros | Ansiedade]     │
│ *Clique para expandir*│ *Clique para expandir*  │ *Clique para expandir*        │
├───────────────────────┼─────────────────────────┼───────────────────────────────┤
│ 🌙 FÍSICO (78%)       │ 🕊️ RUPTURAS (12%)       │ ℹ️ OUTROS (8%)                │
│ [4 registros | Insônia]│ [0 registros na semana]│ [0 registros na semana]       │
│ *Clique para expandir*│ *Clique para expandir*  │ *Clique para expandir*        │
└───────────────────────┴─────────────────────────┴───────────────────────────────┘
```

---

### 3.3 A Interação de Expansão: Do Tema para os Subtemas
Ao clicar em qualquer um dos cartões (por exemplo, no card **Vínculos**):
1. O cartão entra em estado selecionado com destaque cromático.
2. Abre-se logo abaixo ou na lateral uma bandeja de **Subtemas** gerados pelo **Agente 1**:
   - Pílula 1: **`Irmão`** (2 menções | Sentimento: *Raiva/Frustração*)
   - Pílula 2: **`Pai`** (1 menção | Sentimento: *Preocupação financeira*)
   - Pílula 3: **`Cobrança de Expectativas`** (1 menção | Sentimento: *Tristeza*)

---

### 3.4 O Modal Pop-up de Evidência Literal (Ground Truth Traceability)
Ao clicar na pílula **`Irmão`**, dispara-se o **Pop-up Modal de Evidência**, trazendo a máxima transparência e rastreabilidade para o psicólogo:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 🔍 Evidências Clínicas Ancoradas - Subtema: [ Irmão ]                            │
│ Tema: Vínculos (Rede Neural MLP + SBERT - Confiança: 91%)                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│ 📌 Ocorrência 1 de 2 • 05/11/2026 às 22:14 • 🎙️ Áudio de Voz (1m 24s)           │
│                                                                                 │
│   SENTIMENTO DETECTADO: Raiva (Polaridade: -0.74)                               │
│                                                                                 │
│   CITAÇÃO LITERAL DO PACIENTE (TRANSCRIÇÃO EXATA):                              │
│   ┌───────────────────────────────────────────────────────────────────────────┐ │
│   │ "Ontem meu irmão pegou meu carro sem pedir de novo e ainda riu da minha   │ │
│   │ cara quando reclamei. Fiquei com uma raiva insuportável, senti que ninguém │ │
│   │ me respeita nessa casa..."                                                │ │
│   └───────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
│   PLAYER DE ÁUDIO COM RECORTE EXATO:                                            │
│   [ ▶️ Ouvir trecho gravado (00:38 - 01:05) ]  ──●────────────── (00:27)        │
│   *Permite ao terapeuta escutar o tom de voz, choro ou irritação real*          │
│                                                                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│ 📌 Ocorrência 2 de 2 • 03/11/2026 às 19:30 • ✍️ Relato em Texto                  │
│                                                                                 │
│   CITAÇÃO LITERAL:                                                              │
│   "Tive que cancelar meus estudos para cobrir o turno do meu irmão de novo."   │
│                                                                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│ 💡 BRIEFING DO AGENTE 2 (RAG EM FONTES AUTORIZADAS):                           │
│                                                                                 │
│   "O sistema apresenta somente fontes encontradas e citações verificáveis.       │
│   Exemplo: técnicas de limites podem ser apresentadas como referência           │
│   normativa, nunca como diagnóstico ou prescrição ao paciente.                   │
│   [Documento autorizado, seção]."                                               │
│                                                                                 │
│ ┌─────────────────────────────────────────────────────────────────────────────┐ │
│ │ [ Fechar Pop-up ]                      [ Anotar na Pauta da Sessão ]        │ │
│ └─────────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Benefícios Clínicos e Humanização

1. **Economia de Tempo e Foco na Consulta:** O psicólogo não perde os primeiros 20 minutos tentando descobrir o que aconteceu na semana; ele já tem os tópicos e sentimentos mapeados.
2. **Escuta Qualificada de Gravações Reais:** Em vez de confiar em paráfrases frias de IA, o terapeuta pode ouvir diretamente o áudio do paciente nos momentos de maior intensidade afetiva.
3. **Respeito aos Limites Profissionais:** A interface convida o psicólogo à reflexão, sem tentar induzir condutas rígidas.
