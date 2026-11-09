# 08 - Métricas de Desempenho e Framework de Avaliação MIT ImpactBench

## 1. Visão Geral do Framework de Avaliação

O sistema adota uma matriz de avaliação em dois níveis complementares:
1. **Nível Técnico de Engenharia de IA:** Métricas matemáticas clássicas para avaliar a Rede Neural, o pipeline de RAG e a estabilidade dos agentes.
2. **Nível Centrado no Bem-Estar Humano (MIT ImpactBench):** Métricas e critérios inspirados no benchmark do MIT Media Lab (`https://impactbench.media.mit.edu/explore`), garantindo que o impacto da IA promova o florescimento psicológico e evite danos iatrogênicos.

---

## 2. Métricas Técnicas de Machine Learning e Agentes

### A. Rede Neural de Classificação dos 8 Macrotemas
- **Macro-F1 Score:** Métrica de decisão principal ($\ge 0.80$), assegurando que classes com menos exemplos (ex: Luto, Finanças) tenham peso igual às classes mais frequentes (ex: Trabalho, Família).
- **Precisão e Recall por Classe:**
  $$\text{Macro-F1} = \frac{1}{C} \sum_{c=1}^{C} \frac{2 \cdot \text{Precision}_c \cdot \text{Recall}_c}{\text{Precision}_c + \text{Recall}_c}$$
- **Top-2 Accuracy:** Proporção de vezes em que o tema correto esteve entre as duas maiores probabilidades da rede ($\ge 92\%$).
- **Matriz de Confusão:** Monitoramento contínuo para detectar zonas de sobreposição semântica (ex: confusão entre *Relacionamentos* e *Família*).

### B. Extração de Subtemas e Evidências Literais (Agente 1)
- **Taxa de Validade de Esquema (Schema Compliance):** $100\%$ de conformidade com os modelos Pydantic sem erro de parsing JSON.
- **Precisão de Ancoragem Literal (Span Fidelity):** Percentual de caracteres do trecho extraído que coincidem estritamente com o texto bruto do paciente (alvo: $100\%$, zero alucinação de citações).
- **Interseção sobre União (IoU) de Spans:** Mede se o recorte textual selecionado cobre o evento psicológico central sem truncar o sentido da frase.

### C. Recuperação de Diretrizes e RAG (Agente 3)
- **HitRate@3 e Recall@3:** Proporção de consultas onde pelo menos um protocolo clínico relevante foi resgatado entre os 3 primeiros documentos retornados ($\ge 85\%$).
- **Taxa de Citação Verificável:** $100\%$ das asserções geradas pelo Agente 3 devem possuir um identificador de documento correspondente na base de literatura.
- **Taxa de Abstenção Correta:** Quando testado com perguntas desconexas ou fora do domínio clínico, o sistema deve abster-se em $100\%$ dos casos.

### D. Eficiência Computacional e Infraestrutura
- **Latência de Inferência da Rede Neural (CPU):** Mediana $\le 25\text{ ms}$, P95 $\le 50\text{ ms}$.
- **Latência Total do Pipeline Multiagente:** P95 $\le 6.0\text{ s}$ em hardware padrão de desenvolvimento.

---

## 3. Alinhamento com os Domínios do MIT ImpactBench

O painel de exploração do MIT ImpactBench estrutura os efeitos da IA sobre o ser humano em três grandes pilares, os quais balizam o design da nossa ferramenta:

```
                          DOMÍNIOS DO MIT IMPACTBENCH
                                       │
         ┌─────────────────────────────┼─────────────────────────────┐
         ▼                             ▼                             ▼
┌───────────────────────────┐ ┌───────────────────────────┐ ┌───────────────────────────┐
│   1. Domínio Psicológico   │ │ 2. Domínio Físico/Segurança│ │    3. Domínio Social      │
├───────────────────────────┤ ├───────────────────────────┤ ├───────────────────────────┤
│ • Saúde Mental e Emocional│ │ • Privacidade e Sigilo    │ │ • Relação Terapêutica     │
│ • Agência e Autonomia     │ │ • Detecção de Risco       │ │ • Não-Estigmatização      │
│ • Zero Dependência de IA  │ │ • Processamento Local     │ │ • Equidade Cultural       │
└───────────────────────────┘ └───────────────────────────┘ └───────────────────────────┘
```

### 1. Domínio Psicológico
* **Preservação da Agência do Paciente e do Terapeuta:** A IA atua estritamente como ferramenta analítica passiva. O paciente não recebe comandos comportamentais do sistema; o terapeuta mantém autonomia absoluta para seguir ou descartar qualquer sugestão de pauta.
* **Prevenção de Dependência Emocional com a IA:** Ao eliminar o formato de chat interativo de desabafo e substituí-lo pelo diário assíncrono, desestimula-se a formação de vínculos parassociais disfuncionais com a máquina.

### 2. Domínio Físico e de Segurança
* **Privacidade e Proteção de Dados Sensíveis:** Execução local (Ollama em loopback e bancos SQLite criptografados), garantindo que dados de intimidade psicológica nunca sejam transmitidos a provedores externos de nuvem ou usados para retreinar modelos comerciais.
* **Rastreio de Indícios de Risco à Vida:** Identificação sintática de expressões de desesperança aguda para que o psicólogo priorize o contato, sem criar uma falsa sensação de que a máquina gerencia a emergência de forma autônoma.

### 3. Domínio Social e Interpessoal
* **Fortalecimento da Aliança Terapêutica Humana:** O objetivo primário de toda informação gerada é aumentar a profundidade do encontro presencial/teleconsulta entre paciente e profissional humano.
* **Mitigação de Vieses e Não-Estigmatização:** Vocabulário neutro e descritivo; recusa de categorizações pejorativas ou rótulos psiquiátricos precipitados.
