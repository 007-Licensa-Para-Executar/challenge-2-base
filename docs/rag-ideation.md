# 03 - Pipeline de RAG: Recuperação Híbrida e Síntese Clínica Citada

## 1. Visão Geral do Subsistema de RAG

O subsistema de **Geração Aumentada por Recuperação (RAG)** capacita o **Agente 3 (Copiloto Clínico)** a subsidiar o psicólogo com embasamento teórico estrito, conectando os subtemas identificados nos diários às melhores práticas documentadas na literatura de psicologia clínica.

O princípio fundacional do nosso RAG é a **explicabilidade e ancoragem documental**: a IA nunca gera conselhos de "senso comum" ou da "memória paramétrica" do modelo; cada sugestão apresentada ao terapeuta deve ser formalmente rastreável até um capítulo, protocolo ou diretriz da base autorizada.

---

## 2. Pipeline Técnico de Recuperação Híbrida

Para contornar as limitações de vocabulário da busca lexical e as imprecisões contextuais da busca densa pura, o sistema adota um pipeline de **Recuperação Híbrida** combinando **BM25** e **Busca Vetorial Densa**:

```
[ Consulta do Psicólogo / Subtema Clínico Identificado ]
                      │
        ┌─────────────┴─────────────┐
        ▼                           ▼
[ Busca Lexical: BM25 ]      [ Busca Vetorial Densa: e5-small ]
(Correspondência exata       (Similaridade semântica
 de sintomas e termos)        de conceitos e afetos)
        │                           │
        └─────────────┬─────────────┘
                      ▼
[ Fusão de Ranks: Reciprocal Rank Fusion (RRF) ]
                      │
                      ▼
[ Filtro de Limiar de Relevância (Threshold >= 0.70) ]
       │                                     │
       ├─ (Abaixo do limiar)                 └─ (Acima do limiar)
       ▼                                                ▼
[ Abstenção Segura ]                         [ Injeção no Prompt do Agente 3 ]
("Sem diretrizes autorizadas")                          │
                                                        ▼
                                             [ Síntese Clínica Citada com [Doc_ID] ]
```

### Algoritmo de Fusão de Ranks (RRF)
Para unificar os resultados das duas fontes de busca de maneira não paramétrica e robusta:
$$RRF\_Score(d) = \sum_{m \in \{\text{BM25}, \text{Dense}\}} \frac{1}{k + \text{rank}_m(d)}$$
Onde $k = 60$ é uma constante padrão que equilibra a importância de itens bem ranqueados em ambos os motores.

---

## 3. Política Rígida de Abstenção (Anti-Alucinação)

Em contextos clínicos de saúde mental, a alucinação de diretrizes representa risco ético severo. Para eliminar esse risco:
1. **Limiar Mínimo de Similaridade ($\tau = 0.70$):** Se nenhum trecho da base clínica atingir a pontuação de relevância mínima, o sistema interrompe o fluxo de geração.
2. **Resposta Padrão de Abstenção:**
   > *"O sistema não encontrou diretrizes clínicas autorizadas indexadas na base de conhecimento para o subtema especificado. Nenhuma sugestão interventiva será gerada automaticamente."*
3. **Proibição de Inferência Especulativa:** O prompt do sistema proíbe categoricamente o LLM de utilizar conhecimentos externos não presentes no contexto recuperado.

---

## 4. Prompt de Síntese Citada (Agente 3)

```markdown
Você é o Copiloto Clínico de Apoio ao Terapeuta. Sua função exclusiva é correlacionar o relato estruturado do paciente com as diretrizes clínicas recuperadas abaixo.

DIRETRIZES CLÍNICAS RECUPERADAS:
{contextos_recuperados}

SUBTEMA SELECIONADO PELO PSICÓLOGO:
{subtema_nome} - {subtema_descricao}

EVIDÊNCIA LITERAL DO PACIENTE:
"{quote_text}"

INSTRUÇÕES ESTRITAS:
1. Responda única e exclusivamente com base nas DIRETRIZES CLÍNICAS fornecidas.
2. NÃO elabore hipóteses diagnósticas e NÃO faça julgamento moral do paciente.
3. Para cada sugestão de pergunta reflexiva ou técnica de manejo, insira obrigatoriamente a citação do identificador entre colchetes, no formato [Doc_ID, Capítulo/Seção].
4. Se o contexto recuperado não trouxer informações suficientes sobre o tópico, declare explicitamente: "Informações insuficientes na base clínica autorizada."
```
