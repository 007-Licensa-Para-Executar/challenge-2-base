# Guia de Desenvolvimento: Interface do Psicólogo (Estilo MIT ImpactBench)

## 1. Identificação e Propósito do Dashboard
* **Arquivo no Código:** `app/dashboard.py`
* **Tecnologia Adotada:** **Streamlit** (nativo em Python, reativo, com suporte nativo a `st.dialog` para modais pop-up, áudio em HTML5 e gráficos interativos).
* **Objetivo Primário:** Materializar a experiência analítica do **MIT ImpactBench (`impactbench.media.mit.edu/explore`)** para o psicólogo clínico:
  1. Visualização panorâmica dos **8 Temas Padrão** organizados por valência e volume.
  2. Expansão interativa em **Subtemas Específicos** gerados pelo **Agente 1**.
  3. Abertura do **Modal Pop-up de Evidência Literal** ao clicar em qualquer subtema, exibindo as **palavras literais exatas** do paciente, o **player de áudio recortado no carimbo de tempo** e o subsídio teórico do **Agente 3 (RAG)**.
* **Por que este componente existe?** Cumpre com brilho a **Constraint 7 (Solução ética e explicável)** e a **Constraint 9 (MVP funcional)**. Torna o sistema tangível, moderno e diretamente utilizável por psicólogos em ambiente de consultório.

---

## 2. Diagrama de Estados e Interação da Interface

```
┌────────────────────────────────────────────────────────┐
│ 1. TELA PRINCIPAL (/explore)                           │
│    • Termômetro de Afeto Semanal (Positivo/Negativo)   │
│    • Grid dos 8 Cards Temáticos Clínicos               │
└────────────────────────────────────────────────────────┘
                           │
       (Psicólogo clica no Card "FAMÍLIA")
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│ 2. ESTADO EXPANDIDO                                    │
│    • Destaque visual no tema "FAMÍLIA" (Confiança 91%) │
│    • Bandeja de Pílulas de Subtemas:                   │
│      [ Irmão (2) ]  [ Pai (1) ]  [ Herança (1) ]       │
└────────────────────────────────────────────────────────┘
                           │
       (Psicólogo clica na Pílula "[ Irmão ]")
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│ 3. MODAL POP-UP DE EVIDÊNCIAS E AUDITORIA (st.dialog)   │
│    • Citação Literal: "meu irmão pegou meu carro..."   │
│    • Player de Áudio Recortado: [ ▶️ 00:38 - 01:05 ]   │
│    • Sentimento: Raiva (-0.74)                         │
│    • Subsídio do Copiloto (TCC/Beck): [TCC-BECK-CH07]  │
└────────────────────────────────────────────────────────┘
```

---

## 3. Implementação Completa em Streamlit (`app/dashboard.py`)

```python
import streamlit as st
from datetime import date
from agents.extractor.contracts import MacroTema

# Configuração da Página no Padrão Clean & Moderno do ImpactBench
st.set_page_config(
    page_title="Copiloto Clínico | Diário Assistido",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilização CSS Inspirada no MIT Media Lab / ImpactBench
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 16px;
        border-left: 5px solid #4a6fa5;
        margin-bottom: 12px;
    }
    .theme-card-active {
        background-color: #eef4fc;
        border: 2px solid #2b5b84;
        border-radius: 12px;
        padding: 14px;
        text-align: center;
        cursor: pointer;
    }
    .quote-box {
        background-color: #fff8e7;
        border-left: 4px solid #f39c12;
        padding: 12px 16px;
        font-style: italic;
        margin: 10px 0;
        border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)

# 1. Barra Lateral de Navegação e Filtros
st.sidebar.title("🧠 Copiloto Clínico")
st.sidebar.caption("Interface de Apoio ao Terapeuta (Inspirada no MIT ImpactBench)")

paciente_id = st.sidebar.selectbox("Selecionar Paciente:", ["#PAC-8419 (Lucas Silva)", "#PAC-9022 (Mariana Souza)"])
janela_tempo = st.sidebar.radio("Janela Temporal:", ["Últimos 7 dias", "Últimos 14 dias", "Últimos 30 dias"])

st.sidebar.divider()
st.sidebar.info("🛡️ **Conformidade Ética:** Sistema de suporte analítico. Diagnósticos e condutas pertencem ao terapeuta.")

# 2. Faixa Superior de Métricas de Bem-Estar (ImpactBench Overview)
st.title("Panorama Clínico Longitudinal (/explore)")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(label="Total de Relatos", value="6 desabafos", delta="2 áudios / 4 textos")
with col2:
    st.metric(label="Valência Afetiva", value="Predomínio Negativo", delta="-0.58 polaridade", delta_color="inverse")
with col3:
    st.metric(label="Área Crítica", value="Família", delta="91% confiança neural")
with col4:
    st.metric(label="Indicador de Risco Textual", value="Não Identificado", delta="Estável", delta_color="normal")

st.divider()

# 3. Definição dos Dados dos 8 Temas Padrão
temas_info = {
    "familia": {"nome": "👨‍👩‍👧 Família", "qtd": 3, "conf": 0.91, "sent": "Raiva/Frustração", "subtemas": ["Irmão", "Pai", "Cobrança Materna"]},
    "trabalho": {"nome": "💼 Trabalho", "qtd": 2, "conf": 0.84, "sent": "Preocupação", "subtemas": ["Chefe", "Prazos", "Sobrecarga"]},
    "relacionamentos": {"nome": "🤝 Relacionamentos", "qtd": 1, "conf": 0.62, "sent": "Neutro", "subtemas": ["Amigo Distante"]},
    "estudos": {"nome": "📚 Estudos", "qtd": 1, "conf": 0.45, "sent": "Calma", "subtemas": ["TCC"]},
    "saude_sono": {"nome": "🌙 Saúde & Sono", "qtd": 4, "conf": 0.78, "sent": "Insônia", "subtemas": ["Noites em Claro", "Fadiga"]},
    "financas": {"nome": "💰 Finanças", "qtd": 0, "conf": 0.30, "sent": "Sem registros", "subtemas": []},
    "luto": {"nome": "🕊️ Luto", "qtd": 0, "conf": 0.12, "sent": "Sem registros", "subtemas": []},
    "autoestima": {"nome": "🪞 Autoestima", "qtd": 2, "conf": 0.68, "sent": "Tristeza", "subtemas": ["Autocrítica", "Corpo"]}
}

st.subheader("1. Mapa dos 8 Macrotemas Clínicos (Rede Neural MLP)")
cols_row1 = st.columns(4)
cols_row2 = st.columns(4)
todas_colunas = cols_row1 + cols_row2

if "tema_selecionado" not in st.session_state:
    st.session_state.tema_selecionado = "familia"

# Renderização do Grid dos 8 Cartões
for idx, (chave, info) in enumerate(temas_info.items()):
    col = todas_colunas[idx]
    with col:
        estilo = "primary" if st.session_state.tema_selecionado == chave else "secondary"
        if st.button(
            f"{info['nome']}\n\n{info['qtd']} relatos ({int(info['conf']*100)}%)",
            key=f"btn_tema_{chave}",
            use_container_width=True,
            type=estilo
        ):
            st.session_state.tema_selecionado = chave

# 4. Seção Interativa de Subtemas (Desdobramento do Agente 1)
tema_ativo = temas_info[st.session_state.tema_selecionado]
st.write("")
st.subheader(f"2. Subtemas Identificados em '{tema_ativo['nome']}' (Agente 1)")

if not tema_ativo["subtemas"]:
    st.info("Nenhum relato associado a este macrotema na semana selecionada.")
else:
    sub_cols = st.columns(len(tema_ativo["subtemas"]))
    for s_idx, sub in enumerate(tema_ativo["subtemas"]):
        with sub_cols[s_idx]:
            if st.button(f"🔍 Subtema: {sub}", key=f"btn_sub_{sub}", use_container_width=True):
                # Dispara o Modal Pop-up de Evidência Literal
                abrir_modal_evidencia(sub, tema_ativo["nome"])

# 5. Função que Renderiza o Modal Pop-up de Evidências (st.dialog)
@st.dialog("Evidências Literais & Rastreabilidade de Áudio", width="large")
def abrir_modal_evidencia(nome_subtema: str, nome_macro: str):
    st.markdown(f"### Subtema: `{nome_subtema}` (Macrotema: `{nome_macro}`)")
    st.caption("Evidências exatas extraídas pelo Agente 1 e subsídios do Copiloto (RAG)")
    
    st.write("---")
    st.markdown("**📌 Ocorrência 1:** Registrada em 05/11/2026 às 22:14 • 🎙️ **Áudio de Voz (1m 24s)**")
    st.markdown("**Sentimento Detectado:** `Raiva / Frustração` (Polaridade: -0.74)")
    
    st.markdown("**Citação Literal Extraída (Palavras Exatas do Paciente):**")
    st.markdown(
        '<div class="quote-box">"Ontem meu irmão pegou meu carro sem pedir de novo e ainda riu da minha cara quando reclamei. Fiquei com uma raiva insuportável, senti que ninguém me respeita nessa casa..."</div>',
        unsafe_allow_html=True
    )
    
    st.markdown("**Trecho Recortado no Áudio Original (00:38 - 01:05):**")
    # Simulação do player de áudio para o terapeuta ouvir o tom e respiração
    st.audio("https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3", start_time=38)
    st.caption("💡 Permite escutar a entonação de voz, choro ou agressividade verbal real.")

    st.write("---")
    st.markdown("#### 💡 Subsídio Teórico do Copiloto (Agente 3 - RAG TCC/Beck):")
    st.markdown("""
    * **Hipótese Cognitiva:** O relato ativa esquemas de subordinação e crença intermediária de desvalorização familiar.
    * **Perguntas Sugeridas para a Consulta:**
      1. *"O que passou pela sua cabeça no segundo exato em que seu irmão riu de você?"* `[Beck, 2021, Cap. 7 - Pensamentos Automáticos]`
      2. *"Como podemos ensaiar uma resposta assertiva usando o roteiro DEAR MAN da DBT?"* `[Linehan, 2015, Treinamento de Habilidades]`
    """)
    
    if st.button("Fechar Pop-up", use_container_width=True):
        st.rerun()
```

---

## 4. Como Executar a Interface
Basta rodar no terminal com o ambiente ativado:
```bash
uv run streamlit run app/dashboard.py
```

---

## 5. Referências Técnicas
1. **MIT ImpactBench Dashboard:** [https://impactbench.media.mit.edu/explore](https://impactbench.media.mit.edu/explore).
2. **Streamlit Dialog API Reference:** [https://docs.streamlit.io/develop/api-reference/execution-flow/st.dialog](https://docs.streamlit.io/develop/api-reference/execution-flow/st.dialog).
