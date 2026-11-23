# 08 - Métricas de Desempenho e Framework de Avaliação MIT ImpactBench

> **Estado das metas:** os valores desta página são critérios pretendidos e
> hipóteses de aceite. Exceto onde houver evidência versionada em
> [evaluation-results.md](evaluation-results.md) ou no relatório consolidado,
> nenhum alvo deve ser apresentado como já atingido.

## 1. Visão Geral do Framework de Avaliação

O sistema adota uma matriz de avaliação em dois níveis complementares:
1. **Nível Técnico de Engenharia de IA:** Métricas matemáticas clássicas para avaliar a Rede Neural, o pipeline de RAG e a estabilidade dos agentes.
2. **Nível Centrado no Bem-Estar Humano (MIT ImpactBench):** Métricas e critérios inspirados no benchmark do MIT Media Lab (`https://impactbench.media.mit.edu/explore`), garantindo que o impacto da IA promova o florescimento psicológico e evite danos iatrogênicos.

---

## 2. Métricas Técnicas de Machine Learning e Agentes

### A. Rede Neural de Classificação dos Macrotemas
- **Macro-F1 Score:** métrica candidata para decisão técnica entre versões. Um limiar como $\ge 0.80$ precisa ser validado sobre dados independentes e pelo menos seis macrotemas consolidados.
- **Precisão e Recall por Classe:**
  $$\text{Macro-F1} = \frac{1}{C} \sum_{c=1}^{C} \frac{2 \cdot \text{Precision}_c \cdot \text{Recall}_c}{\text{Precision}_c + \text{Recall}_c}$$
- **Top-2 Accuracy:** métrica adicional candidata apenas se o protocolo conservar múltiplos candidatos; não é parte da política atual de categoria única.
- **Matriz de Confusão:** Monitoramento contínuo para detectar zonas de sobreposição semântica (ex: confusão entre *Relacionamentos* e *Família*).

### B. Extração de Subtemas e Evidências Literais (Agente 1)
- **Taxa de Validade de Esquema (Schema Compliance):** proporção de saídas que passam pelos modelos Pydantic; zero falhas é uma meta, não uma garantia.
- **Precisão de Ancoragem Literal (Span Fidelity):** percentual dos trechos extraídos encontrados literalmente no texto bruto. O alvo é evitar ancoragem inventada, mas o resultado precisa ser medido.
- **Interseção sobre União (IoU) de Spans:** Mede se o recorte textual selecionado cobre o evento psicológico central sem truncar o sentido da frase.

### C. Recuperação de Diretrizes e RAG (Agente 2)
- **HitRate@3 e Recall@3:** proporção de consultas em que fontes relevantes aparecem entre os resultados. Qualquer limiar deve ser definido sobre um corpus autorizado e rotulado.
- **Taxa de Citação Verificável:** proporção de citações que correspondem a documento, seção e trecho existentes no contexto fornecido.
- **Taxa de Abstenção Correta:** taxa sobre casos fora do domínio ou com evidência insuficiente; 100% é objetivo de teste, não resultado comprovado.

### D. Eficiência Computacional e Infraestrutura
- **Latência de Inferência da Rede Neural (CPU):** Mediana $\le 25\text{ ms}$, P95 $\le 50\text{ ms}$.
- **Latência Total do Fluxo Multiagente:** P95 desejável em hardware declarado, com medidas separadas de modelo, banco e recuperação.

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
* **Privacidade e Proteção de Dados Sensíveis:** execução local por Ollama e controles de criptografia/pseudonimização disponíveis devem ser medidos, documentados e separados da conformidade integral da aplicação.
* **Rastreio de Indícios de Risco à Vida:** Identificação sintática de expressões de desesperança aguda para que o psicólogo priorize o contato, sem criar uma falsa sensação de que a máquina gerencia a emergência de forma autônoma.

### 3. Domínio Social e Interpessoal
* **Fortalecimento da Aliança Terapêutica Humana:** O objetivo primário de toda informação gerada é aumentar a profundidade do encontro presencial/teleconsulta entre paciente e profissional humano.
* **Mitigação de Vieses e Não-Estigmatização:** Vocabulário neutro e descritivo; recusa de categorizações pejorativas ou rótulos psiquiátricos precipitados.
