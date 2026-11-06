# Guia de Engenharia de Dados: Síntese de Personas e Relatos Clínicos (PsychAdapter & Ulster)

## 1. Identificação e Propósito
* **Arquivo no Código:** `data/synthetic_generator.py` e `data/personas.json`
* **Objetivo Primário:** Produzir datasets sintéticos de alta fidelidade psicológica para o treinamento da Rede Neural MLP (classificador dos 8 macrotemas) e para os testes automatizados da suíte de agentes, sem violar leis de privacidade (LGPD) ou o sigilo médico.
* **Por que este componente existe?** Cumpre com rigor a **Constraint 7 (Ética e Explicabilidade)** e a **Constraint 8 (Resources com até 2 anos)**. O uso de relatos de pacientes reais sem consentimento institucional e aprovação de comitê de ética (CEP/CONEP) é ilegal. Adotando a metodologia do [**PsychAdapter**](https://github.com/humanlab/psychadapter) (*npj Artificial Intelligence / Nature Portfolio, 2024/2025*) e as diretrizes de simulação da [**Universidade de Ulster**](https://pure.ulster.ac.uk/en/publications/using-large-language-models-in-simulated-mental-health-assessment/) (2024–2026), sintetizamos personas com perfis controlados de traços de personalidade e queixas clínicas.

---

## 2. Metodologia: O Framework das 4 Personas Clínicas Centrais

O gerador parametriza a linguagem utilizando o modelo **Big Five (OCEAN)** cruzado com arquétipos de sofrimento frequentes na clínica:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      MATRIZ DE PERSONAS SINTÉTICAS (OCEAN)                      │
├───────────────┬────────────────────────────┬────────────────────────────────────┤
│ Arquétipo     │ Traços Big Five Dominantes │ Macrotemas e Dinâmica Expressiva   │
├───────────────┼────────────────────────────┼────────────────────────────────────┤
│ 1. Universitário│ Alto Neuroticismo,         │ 'estudos', 'autoestima', 'sono'    │
│    Ansioso    │ Baixa Conscienciosidade    │ Relatos com autocrítica, pânico de │
│               │                            │ prazos e insônia na madrugada.     │
├───────────────┼────────────────────────────┼────────────────────────────────────┤
│ 2. Cuidador   │ Alta Amabilidade,          │ 'familia', 'financas'              │
│    Familiar   │ Alto Neuroticismo          │ Sentimento de sobrecarga, disputas │
│               │                            │ com irmãos e cansaço domiciliar.   │
├───────────────┼────────────────────────────┼────────────────────────────────────┤
│ 3. Executivo  │ Alta Conscienciosidade,    │ 'trabalho', 'saude_sono'           │
│    Burnout    │ Baixa Extroversão          │ Taquicardia, cinismo no trabalho,  │
│               │                            │ cobrança de chefia e exaustão.     │
├───────────────┼────────────────────────────┼────────────────────────────────────┤
│ 4. Luto e     │ Baixa Extroversão,         │ 'luto', 'relacionamentos'          │
│    Isolamento │ Alto Neuroticismo          │ Sensação de vazio, anedonia,       │
│               │                            │ lembrança de datas e separação.    │
└───────────────┴────────────────────────────┴────────────────────────────────────┘
```

---

## 3. Implementação do Gerador Sintético (`data/synthetic_generator.py`)

```python
import json
import random
import httpx
from typing import List, Dict

PERSONAS_DEFINITIONS = [
    {
        "id": "persona_universitario",
        "nome": "Lucas, 21 anos, estudante de engenharia",
        "tracos": "Alto neuroticismo, autocrítica severa, procrastinador",
        "temas_frequentes": ["estudos", "autoestima", "saude_sono"],
        "estilo_linguagem": "Uso de gírias jovens, frases fragmentadas, desespero por prazos"
    },
    {
        "id": "persona_cuidador",
        "nome": "Mariana, 38 anos, cuida da mãe idosa",
        "tracos": "Alta amabilidade, sobrecarregada, culpa constante",
        "temas_frequentes": ["familia", "financas"],
        "estilo_linguagem": "Tom exausto, relatos de atritos com parentes que não ajudam"
    },
    {
        "id": "persona_burnout",
        "nome": "Roberto, 44 anos, gerente de projetos",
        "tracos": "Perfeccionista, alta conscienciosidade, irritável",
        "temas_frequentes": ["trabalho", "saude_sono"],
        "estilo_linguagem": "Vocabulário corporativo, menção a dores de estômago e taquicardia"
    },
    {
        "id": "persona_luto",
        "nome": "Clara, 29 anos, perdeu o pai recentemente",
        "tracos": "Introspectiva, triste, desapegada da rotina",
        "temas_frequentes": ["luto", "relacionamentos"],
        "estilo_linguagem": "Frases lentas, referências a saudades, fotos antigas e silêncio"
    }
]

GENERATOR_PROMPT = """Você é um simulador de diários íntimos de saúde mental baseado no framework PsychAdapter.
Sua tarefa é redigir um desabafo autêntico em português de 1 a 3 parágrafos, como se fosse a persona descrita abaixo.

PERSONA:
Nome/Perfil: {nome}
Traços Psicológicos: {tracos}
Estilo de Escrita: {estilo_linguagem}
Tema Central Obrigatório: {tema}

DIRETRIZES:
1. Soe como um ser humano real escrevendo no calor do momento (pode ter desabafos crus, pontuação informal, pausas).
2. Não adicione cabeçalhos, metadados ou introduções. Retorne EXCLUSIVAMENTE o texto do diário.
"""

def generate_synthetic_dataset(
    output_path: str = "data/synthetic/synthetic_diaries.json",
    samples_per_theme: int = 40,
    ollama_url: str = "http://localhost:11434",
    model: str = "qwen2.5:3b"
):
    themes = [
        "familia", "trabalho", "relacionamentos", "estudos",
        "saude_sono", "financas", "luto", "autoestima"
    ]
    
    dataset = []
    client = httpx.Client(timeout=30.0)

    for theme in themes:
        print(f"Gerando relatos para o tema: {theme}...")
        for i in range(samples_per_theme):
            persona = random.choice(PERSONAS_DEFINITIONS)
            prompt = GENERATOR_PROMPT.format(
                nome=persona["nome"],
                tracos=persona["tracos"],
                estilo_linguagem=persona["estilo_linguagem"],
                tema=theme
            )
            
            resp = client.post(
                f"{ollama_url}/api/chat",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "options": {"temperature": 0.85}
                }
            )
            text_content = resp.json()["message"]["content"].strip()
            
            dataset.append({
                "id": f"syn_{theme}_{i+1:03d}",
                "persona_id": persona["id"],
                "macro_tema": theme,
                "texto": text_content,
                "modalidade": "texto"
            })

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)
    print(f"Dataset sintético gerado com sucesso em {output_path} ({len(dataset)} registros)!")
```

---

## 4. Divisão e Estratégia de Holdout para MLOps

O arquivo gerado é estruturado com um script de divisão determinística (`data/split.py`):
- **Treino (70%):** Utilizado pelo `models/train.py` para ajuste dos pesos da Rede Neural MLP.
- **Validação (15%):** Utilizado para Early Stopping e controle de overfitting no MLflow.
- **Holdout Test Cego (15%):** Conjunto intocado, utilizado exclusivamente na avaliação final para atestar a generalização do modelo.

---

## 5. Referências Científicas
1. **PsychAdapter (Nature Portfolio / npj AI & arXiv 2024/2025):** [https://github.com/humanlab/psychadapter](https://github.com/humanlab/psychadapter).
2. **Ulster University (2024–2026):** *Using Large Language Models in Simulated Mental Health Assessment* (Mallon, Ennis et al.).
