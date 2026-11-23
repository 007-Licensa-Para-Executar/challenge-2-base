# Guia de Engenharia de Dados: Síntese de Personas e Relatos Clínicos (PsychAdapter & Ulster)

> **Estado atual:** este documento descreve um gerador sintético local. Os dados,
> personas e rótulos não foram validados clinicamente e não representam pacientes
> reais. Referências externas inspiram a pesquisa, mas não demonstram reprodução
> integral de suas metodologias.

## 1. Identificação e Propósito
* **Arquivo no Código:** `data/synthetic_generator.py` e `data/personas.json`
* **Objetivo Primário:** Produzir datasets sintéticos para treinamento, testes e demonstrações da Rede Neural MLP e da suíte de agentes, sem usar dados reais.
* **Por que este componente existe?** A geração sintética reduz exposição a dados pessoais, mas não elimina riscos de viés, estereotipia ou representatividade inadequada. A adoção de modelos como Ollama e referencias como [**PsychAdapter**](https://github.com/humanlab/psychadapter) não substitui validação clínica.

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

GENERATOR_PROMPT = """Você é um simulador de diários íntimos de saúde mental.
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

O script `data/split.py` realiza divisão por grupos e pode produzir treino,
validação e teste. A proporção exata depende do número de grupos e da distribuição
das classes.

- **Treino:** ajuste dos pesos da Rede Neural MLP.
- **Validação:** seleção de configuração e checkpoints.
- **Teste:** avaliação final reservada.

Variações do mesmo template ou persona devem permanecer no mesmo grupo. O arquivo
versionado não comprova que o modelo generalizará para relatos reais.

---

## 5. Referências Científicas
1. **PsychAdapter (Nature Portfolio / npj AI & arXiv 2024/2025):** [https://github.com/humanlab/psychadapter](https://github.com/humanlab/psychadapter).
2. **Ulster University (2024–2026):** *Using Large Language Models in Simulated Mental Health Assessment* (Mallon, Ennis et al.).
