# Guia de Engenharia de Dados: Síntese de Personas e Relatos Clínicos (PsychAdapter & Ulster)

> **Estado atual:** este documento descreve um gerador sintético local. Os dados,
> personas e rótulos não foram validados clinicamente e não representam pacientes
> reais. Referências externas inspiram a pesquisa, mas não demonstram reprodução
> integral de suas metodologias.

## 1. Identificação e Propósito
* **Arquivo no Código:** `data/synthetic_generator.py`, `data/taxonomy.py` e `data/personas.json`
* **Objetivo Primário:** Produzir datasets sintéticos de alta fidelidade psicológica para o treinamento da Rede Neural MLP (classificador dos **6 temas**: `autopercepcao`, `vinculos`, `desempenho`, `fisico`, `rupturas`, `outros`) e para os testes automatizados da suíte de agentes, sem usar dados reais.
* **Por que este componente existe?** A geração sintética reduz exposição a dados pessoais (LGPD), mas não elimina riscos de viés, estereotipia ou representatividade inadequada. Adotando a metodologia do [**PsychAdapter**](https://github.com/humanlab/psychadapter) (*npj Artificial Intelligence / Nature Portfolio, 2024/2025*) e as diretrizes de simulação da [**Universidade de Ulster**](https://pure.ulster.ac.uk/en/publications/using-large-language-models-in-simulated-mental-health-assessment/) (2024–2026), sintetizamos personas com perfis controlados de traços de personalidade e queixas clínicas; isso não substitui validação clínica.

---

## 2. Taxonomia Única de 6 Temas (`data/taxonomy.py`)

Todos os scripts de ingestão (`data/fetch_real_dataset.py`), geração sintética (`data/synthetic_generator.py`), divisão estratificada (`data/split.py`) e treino da rede neural (`models/train.py`) compartilham exclusivamente as **6 classes**:

| Chave | Rótulo | Escopo Semântico |
| :--- | :--- | :--- |
| `autopercepcao` | **Autopercepção** | Autoestima, identidade, imagem corporal e sensação de incapacidade ou inadequação |
| `vinculos` | **Vínculos** | Relacionamentos amorosos, amizades, família, términos, traições e separações |
| `desempenho` | **Desempenho** | Trabalho, estudos e finanças (cobranças, metas, provas, dívidas) |
| `fisico` | **Físico** | Saúde física e mental em sintomas, sono, tratamento médico, dores e sonhos |
| `rupturas` | **Rupturas** | Perdas por morte e luto |
| `outros` | **Outros** | Sem tema clínico claro, relato neutro ou classe de salvaguarda por abstenção |

*(Rótulos legados de versões anteriores são convertidos automaticamente para essas 6 classes por `remap_legacy_label` em `data/taxonomy.py`.)*

---

## 3. Metodologia: O Framework das 4 Personas Clínicas Centrais

O gerador parametriza a linguagem utilizando o modelo **Big Five (OCEAN)** cruzado com arquétipos de sofrimento frequentes na clínica:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      MATRIZ DE PERSONAS SINTÉTICAS (OCEAN)                      │
├───────────────┬────────────────────────────┬────────────────────────────────────┤
│ Arquétipo     │ Traços Big Five Dominantes │ Temas Frequentes e Dinâmica        │
├───────────────┼────────────────────────────┼────────────────────────────────────┤
│ 1. Universitário│ Alto Neuroticismo,         │ 'desempenho', 'autopercepcao',     │
│    Ansioso    │ Baixa Conscienciosidade    │ 'fisico' — autocrítica, prazos e   │
│               │                            │ insônia na madrugada.              │
├───────────────┼────────────────────────────┼────────────────────────────────────┤
│ 2. Cuidador   │ Alta Amabilidade,          │ 'vinculos', 'desempenho'           │
│    Familiar   │ Alto Neuroticismo          │ Sobrecarga, atritos com parentes e │
│               │                            │ pressões financeiras/domésticas.   │
├───────────────┼────────────────────────────┼────────────────────────────────────┤
│ 3. Executivo  │ Alta Conscienciosidade,    │ 'desempenho', 'fisico'             │
│    Burnout    │ Baixa Extroversão          │ Taquicardia, exaustão, cobrança de │
│               │                            │ chefia e sobrecarga laboral.       │
├───────────────┼────────────────────────────┼────────────────────────────────────┤
│ 4. Luto e     │ Baixa Extroversão,         │ 'rupturas', 'vinculos'             │
│    Isolamento │ Alto Neuroticismo          │ Saudade, perda de ente querido,    │
│               │                            │ silêncio e afastamento afetivo.    │
└───────────────┴────────────────────────────┴────────────────────────────────────┘
```

---

## 4. Estrutura do Gerador Sintético (`data/synthetic_generator.py`)

O módulo `data/synthetic_generator.py` importa diretamente `CLASSES`, `CLASS_DESCRIPTIONS` e `SAFEGUARD_CLASS` de `data/taxonomy.py` e gera exemplos sintéticos tanto em modo **offline** (a partir de templates mapeados via `LEGACY_TO_NEW`) quanto via **Ollama** (`--ollama`), atribuindo `group_id` por família de template para evitar vazamento no split:

O gerador implementado possui dois modos:

- **Offline:** combina personas carregadas de `data/personas.json` com templates
  versionados no próprio código.
- **Ollama local:** envia prompts a um modelo instalado localmente e usa
  temperatura configurável. A geração depende do serviço Ollama.

O gerador usa inicialmente oito rótulos operacionais:

- `familia`
- `trabalho`
- `relacionamentos`
- `estudos`
- `saude_sono`
- `financas`
- `luto`
- `autoestima`

A classe `outros_indeterminado` representa relatos neutros ou fora dos oito
rótulos, no modo offline e no dataset gerado. Na taxonomia consolidada v2.1,
esses rótulos podem ser agrupados em seis macrotemas. O mapeamento final ainda
precisa ser implementado e validado; não pode ser assumido apenas pela proximidade
dos nomes.

O trecho abaixo é uma representação didática da interface anterior do gerador. A
implementação atual inclui o modo offline, grupos de origem e validação de arquivos;
use `data/synthetic_generator.py` como referência do comportamento executável.

```python
from data.taxonomy import CLASS_DESCRIPTIONS, CLASSES, SAFEGUARD_CLASS

CLINICAL_CLASSES: list[str] = [c for c in CLASSES if c != SAFEGUARD_CLASS]

DEFAULT_PERSONAS = [
    {
        "id": "persona_universitario",
        "nome": "Lucas, 21 anos, estudante de engenharia",
        "tracos": "Alto neuroticismo, autocrítica severa, procrastinador",
        "temas_frequentes": ["desempenho", "autopercepcao", "fisico"],
        "estilo_linguagem": "Uso de gírias jovens, frases fragmentadas, desespero por prazos",
    },
    {
        "id": "persona_cuidador",
        "nome": "Mariana, 38 anos, cuida da mãe idosa",
        "tracos": "Alta amabilidade, sobrecarregada, culpa constante",
        "temas_frequentes": ["vinculos", "desempenho"],
        "estilo_linguagem": "Tom exausto, relatos de atritos com parentes que não ajudam",
    },
    {
        "id": "persona_burnout",
        "nome": "Roberto, 44 anos, gerente de projetos",
        "tracos": "Perfeccionista, alta conscienciosidade, irritável",
        "temas_frequentes": ["desempenho", "fisico"],
        "estilo_linguagem": "Vocabulário corporativo, menção a dores de estômago e taquicardia",
    },
    {
        "id": "persona_luto",
        "nome": "Clara, 29 anos, perdeu o pai recentemente",
        "tracos": "Introspectiva, triste, desapegada da rotina",
        "temas_frequentes": ["rupturas", "vinculos"],
        "estilo_linguagem": "Frases lentas, referências a saudades, fotos antigas e silêncio",
    },
]
```

---

## 5. Divisão e Estratégia de Holdout para MLOps

O arquivo gerado é dividido de forma determinística por família de origem (`data/split.py`), respeitando as **6 classes** e sem compartilhar `group_id` entre conjuntos:
- **Treino (~70%):** Utilizado pelo `models/train.py` para ajuste dos pesos da Rede Neural MLP sobre os embeddings SBERT (`SBERTEmbedder`).
- **Validação (~15%):** Utilizado para seleção de checkpoint (melhor Macro-F1) e calibração por *Temperature Scaling*.
- **Holdout Test Cego (~15%):** Conjunto intocado, utilizado exclusivamente na avaliação final para atestar a generalização do modelo.

Variações do mesmo template ou persona permanecem no mesmo grupo. O arquivo versionado não comprova que o modelo generalizará para relatos reais.

---

## 6. Referências Científicas
1. **PsychAdapter (Nature Portfolio / npj AI & arXiv 2024/2025):** [https://github.com/humanlab/psychadapter](https://github.com/humanlab/psychadapter).
2. **Ulster University (2024–2026):** *Using Large Language Models in Simulated Mental Health Assessment* (Mallon, Ennis et al.).
