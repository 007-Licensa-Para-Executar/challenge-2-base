"""Gerador de relatos fictícios por perfis e templates locais (taxonomia de 6 classes).

Rótulos e conteúdo são sintéticos e não revisados; não há validação clínica
nem reprodução demonstrada de um framework científico externo.

Os templates offline ainda usam as chaves antigas de tema. A ligação com as
classes novas é feita por LEGACY_TO_NEW (ver data/taxonomy.py), sem reescrever textos.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import random
from pathlib import Path
from typing import Any

from data.taxonomy import (
    CLASS_DESCRIPTIONS,
    CLASSES,
    LEGACY_TO_NEW,
    SAFEGUARD_CLASS,
    remap_legacy_label,
)

try:  # httpx só é necessário com --ollama
    import httpx
except ImportError:  # pragma: no cover
    httpx = None

logger = logging.getLogger(__name__)

DEFAULT_PERSONAS_PATH = Path(__file__).resolve().parent / "personas.json"

CLINICAL_CLASSES: list[str] = [c for c in CLASSES if c != SAFEGUARD_CLASS]

DEFAULT_PERSONAS: list[dict[str, Any]] = [
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

GENERATOR_PROMPT_TEMPLATE = """Você produz relatos inteiramente fictícios para testes de classificação temática.
Sua tarefa é redigir um desabafo fictício em português de 1 a 3 parágrafos, como se fosse a persona descrita abaixo.

PERSONA:
Nome/Perfil: {nome}
Traços Psicológicos: {tracos}
Estilo de Escrita: {estilo_linguagem}
Tema Central Obrigatório: {tema}

DIRETRIZES:
1. Soe como um ser humano real escrevendo no calor do momento (desabafo cru, pontuação informal, pausas reflexivas).
2. Não adicione cabeçalhos, metadados, títulos ou introduções.
3. Retorne EXCLUSIVAMENTE o texto puro do diário.
"""

# Pool de templates offline (não revisados). Chaves = temas antigos, mapeados em LEGACY_TO_NEW.
_OFFLINE_TEMPLATES: dict[str, dict[str, list[str]]] = {
    "persona_universitario": {
        "estudos": [
            "Não aguento mais olhar pra essa tela de Cálculo. A entrega é amanhã às 8h e travei na metade dos exercícios. Fico me sabotando, abrindo rede social a cada dez minutos e depois bate aquele pânico absurdo no peito. Parece que todo mundo da turma tá voando e só eu sou uma fraude completa que não devia estar aqui.",
            "Semana de provas e sinto que meu cérebro fritou de vez. Não consigo reter uma linha de Mecânica dos Sólidos. Se eu reprovar de novo nessa matéria meu pai vai cortar minha ajuda de custo. Tô num desespero tão grande que nem almoçar consigo direito.",
            "Passei a madrugada inteira tentando terminar o relatório do laboratório. O grupo jogou tudo nas minhas costas e eu, covarde como sempre, não tive coragem de dizer não. Agora estou aqui com três xícaras de café na cabeça, tremendo e com medo de tirar nota baixa.",
        ],
        "autoestima": [
            "Me sinto o sujeito mais incapaz do mundo quando olho meus colegas conseguindo estágio em multinacional e eu nem passo da primeira triagem de currículo. Acho que sou burro mesmo, sem talento nenhum pra essa área.",
            "Não sei por que insisto em tentar agradar todo mundo. Me olho no espelho e sinto vergonha da minha postura, das minhas olheiras e dessa sensação de que estou sempre dez passos atrás de qualquer jovem da minha idade.",
            "A sensação de insuficiência tá me corroendo hoje. Parece que qualquer coisa que eu faço fica medíocre. Não consigo ter orgulho de nada do que produzo ultimamente.",
        ],
        "saude_sono": [
            "São quatro da manhã e o teto do quarto é meu único companheiro de novo. Minha cabeça parece uma turbina de avião que não desliga nunca. Quando fecho o olho, vêm os prazos e as cobranças.",
            "Tô com uma dor de cabeça tensional absurda que desce até a nuca. Fico virando de um lado pro outro na cama, o alarme toca em duas horas e eu simplesmente esqueci como é dormir uma noite inteira sem acordar assustado.",
            "Tomo remédio pra dormir mas acordo parecendo que tomei uma surra. O corpo pesado, olhos ardendo e essa fadiga crônica que não passa com café nenhum.",
        ],
        "familia": [
            "Meu pai ligou só pra cobrar as notas da faculdade e comparar com o filho do vizinho. Desliguei o telefone com vontade de sumir do mapa, eles nunca perguntam como eu tô me sentindo por dentro.",
            "Mais um almoço de domingo em que tive que ouvir gracinhas sobre quando vou me formar e começar a dar retorno pro dinheiro investido. Eles não fazem ideia da pressão diária que eu vivo.",
        ],
        "trabalho": [
            "O estágio de suporte tá drenando toda a minha energia vital. Ganho uma bolsa ridícula pra ouvir desaforo de usuário o dia inteiro e ainda tenho que chegar em casa e estudar até a madrugada.",
            "Cobrança sem fim no estágio por metas que nem os contratados sêniores batem. Sinto que estou me desdobrando em mil e sendo visto como descartável.",
        ],
        "relacionamentos": [
            "Ela não me respondeu desde ontem à tarde. Sei que é paranoia minha, mas fico achando que fiz ou falei alguma besteira e que logo logo ela vai cansar de mim.",
            "Me sinto tão solitário aqui nessa república. Passo os fins de semana trancado no quarto estudando enquanto parece que o resto do mundo tem amigos e vida social de verdade.",
        ],
        "financas": [
            "A conta de luz veio um absurdo e o vale-alimentação não vai dar nem até o dia 20. Fiquei meia hora escolhendo o miojo mais barato no mercado pra conseguir fechar o mês.",
            "Não sei como vou pagar a xerox e o transporte este mês. Qualquer gasto imprevisto de cinquenta reais já me desmonta o orçamento inteiro.",
        ],
        "luto": [
            "Lembrei hoje do meu avô me ensinando a andar de bicicleta quando eu era moleque. Dá uma saudade pesada, um vazio no peito que parece que nunca vai cicatrizar.",
            "Passou um ano desde que perdi meu melhor amigo num acidente e ainda parece surreal que nunca mais vou receber uma mensagem dele zoando sobre a faculdade.",
        ],
    },
    "persona_cuidador": {
        "familia": [
            "Minha mãe teve outro episódio de desorientação hoje de manhã. Fiquei com ela até o almoço sem conseguir respirar, e quando liguei pedindo pro meu irmão vir revezar no fim de semana, ele disse que tinha compromisso inadiável. Toda a responsabilidade sempre sobra pra mim.",
            "Não aguento mais a hipocrisia da minha família. Meus tios só aparecem pra opinar sobre os remédios da minha mãe e me criticar, mas na hora de passar uma tarde dando banho e trocando fralda ninguém aparece.",
            "Cheguei ao meu limite hoje. Minha mãe gritou comigo porque não me reconheceu, e depois chorei escondida no banheiro pra ela não ver. Me sinto uma filha horrível por ter sentido raiva naquele segundo.",
        ],
        "financas": [
            "A farmácia levou metade do meu salário antes do dia 10. As fraldas geriátricas e os três remédios contínuos aumentaram de preço de novo e não sobrou quase nada pras despesas da casa.",
            "Tive que escolher entre pagar meu plano de saúde ou garantir o tratamento fisioterápico da minha mãe. É claro que escolhi o dela, mas me sinto desamparada se acontecer algo comigo.",
            "Pedi pros meus irmãos ajudarem com uma cota mensal pros remédios e virou uma discussão horrível no grupo de família, com indiretas e cobranças antigas.",
        ],
        "saude_sono": [
            "Faz meses que não durmo mais de três horas seguidas. Ao menor ruído no quarto da minha mãe eu acordo em sobressalto com medo de que ela tenha tentado levantar e caído no chão.",
            "Minha coluna tá destruída de carregar peso e fazer transferência da cama pra cadeira de rodas. Sinto uma dor lombar cortante e não tenho tempo nem de ir ao médico me consultar.",
            "O cansaço físico já virou uma névoa mental constante. Esqueço as coisas simples, me sinto fraca e esgotada o dia todo.",
        ],
        "trabalho": [
            "Tive que pedir pra sair mais cedo duas vezes esta semana pra levar minha mãe na geriatra. Minha coordenadora me olhou torto e disse que a equipe precisa de pessoas mais comprometidas.",
            "Não consigo focar no trabalho sabendo que deixei minha mãe sozinha com uma cuidadora temporária que mal conheço. O medo de receber uma ligação de emergência não me abandona.",
        ],
        "relacionamentos": [
            "Meu casamento tá por um fio. Meu marido reclama com razão que a gente não sai mais, que a nossa casa virou um hospital e que não sobra espaço pra nossa vida a dois.",
            "Perdi contato com todas as minhas amigas dos últimos anos. Não dá pra marcar um café sem ter que planejar uma logística de guerra com horas de antecedência.",
        ],
        "estudos": [
            "Tranquei minha pós-graduação porque era desumano tentar ler artigos acadêmicos depois de passar a noite trocando lençol e administrando medicação.",
            "Vejo meus antigos colegas concluindo doutorado e me sinto estagnada no tempo, como se minha própria carreira tivesse sido pausada pra sempre.",
        ],
        "autoestima": [
            "Me olho no espelho e vejo uma mulher envelhecida vinte anos em cinco. Não tenho vontade de passar um batom, de arrumar o cabelo ou de comprar uma roupa nova.",
            "Sinto que me transformei apenas numa função: a filha que cuida. Mariana, a pessoa que tinha sonhos e gostava de dançar, parece ter deixado de existir.",
        ],
        "luto": [
            "O luto antecipatório é uma tortura diária. Ver a pessoa que me criou e era tão lúcida definhar dia após dia me faz chorar antes mesmo de ela partir.",
            "A cada memória que ela perde, é como se eu perdesse um pedaço da minha infância junto. É uma despedida em câmera lenta que consome a alma.",
        ],
    },
    "persona_burnout": {
        "trabalho": [
            "Acabei de sair de uma reunião de alinhamento com a diretoria e minha mão ainda tá tremendo de raiva. Jogaram a meta do trimestre pra cima de novo e disseram que o orçamento foi congelado. Estão esperando milagre com a equipe pela metade.",
            "Mais um domingo à tarde arruinado pela musiquinha do Fantástico e pelo pânico de abrir o Teams na segunda-feira. Sinto uma taquicardia real no peito só de lembrar da quantidade de e-mails não lidos me esperando.",
            "Trabalho 14 horas por dia, atendo cliente aos sábados e ainda recebo feedback cínico dizendo que falta 'senso de dono'. Se eu me doar mais um pouco nisso eu caio duro enfartado na sala de reunião.",
        ],
        "saude_sono": [
            "Essa queimação no estômago virou uma gastrite violenta que nem omeprazol tá aliviando mais. O médico avisou que minha pressão arterial tá alta e que preciso desacelerar urgente.",
            "Acordo às 3h30 da manhã repassando mentalmente o cronograma da entrega e os riscos do projeto. Fico suando frio no escuro sem conseguir voltar a dormir de jeito nenhum.",
            "Sinto taquicardia do nada enquanto tomo café da manhã antes de ligar o notebook. Meu corpo tá claramente dando sinais de colapso físico.",
        ],
        "familia": [
            "Não vi meus filhos acordados em quase todos os dias dessa semana. Chego quando já dormiram e saio antes de acordarem. Minha esposa mal fala comigo porque estou sempre ausente mesmo estando fisicamente ali.",
            "Estava no jantar de aniversário do meu filho e tive que me afastar pra atender um telefonema urgente de crise de produção. Me senti o pior pai do planeta terra.",
        ],
        "autoestima": [
            "Passei vinte anos construindo essa carreira pra chegar num ponto em que sinto que sou só uma engrenagem descartável num moedor de carne corporativo. Cadê o propósito daquilo que faço?",
            "Mesmo entregando tudo com nota máxima e batendo metas, me sinto uma fraude e tenho pavor de descobrirem que estou à beira de um colapso nervoso.",
        ],
        "financas": [
            "Ganho um salário considerado bom pro mercado, mas o custo de vida pra manter as aparências e as escolas particulares me mantém preso nessa gaiola de ouro sem conseguir pedir demissão.",
            "Fico refém dos bônus anuais pra pagar o financiamento e as despesas altas, o que me impede de dar um passo atrás e procurar um trabalho mais tranquilo.",
        ],
        "relacionamentos": [
            "Estou tão irritadiço e sem paciência que qualquer comentário do meu parceiro vira motivo pra eu estourar e ser agressivo sem necessidade. Me tornei alguém intragável de conviver.",
            "Não tenho mais amigos fora do trabalho. Todas as minhas conversas giram em torno de política da empresa, metas e processos, o que me dá um vazio existencial profundo.",
        ],
        "estudos": [
            "Comprei uma certificação caríssima de gestão ágil há seis meses e não consegui abrir nem o primeiro módulo. A exaustão mental no fim do dia bloqueia qualquer capacidade de aprender algo novo.",
            "Tento ler artigos sobre novas tecnologias de liderança mas não consigo absorver nada. A cabeça parece pesada, lenta e totalmente embotada.",
        ],
        "luto": [
            "Perdi um grande colega de equipe pra um AVC fulminante mês passado. O RH fez um minuto de silêncio na segunda-feira e na terça já tinha vaga aberta substituindo o cara. Aquilo me deu uma tristeza sem fim.",
            "A ficha caiu de que a vida tá passando rápido demais e estou trocando meus melhores anos por prazos irrelevantes de empresas que me esquecerão no dia seguinte.",
        ],
    },
    "persona_luto": {
        "luto": [
            "Faz seis meses que o papai se foi e a sensação de vazio ao entrar na casa dele ainda me derruba no chão. O cheiro do perfume dele no casaco pendurado atrás da porta me fez chorar convulsivamente a tarde inteira.",
            "Hoje seria o aniversário de 60 anos dele. Comprei o bolo que ele mais gostava mas não tive coragem nem de cortar. Fiquei sentada no chão da sala olhando as fotos antigas e perguntando por que teve que ser tão cedo.",
            "Tem dias em que parece que a dor diminui um pouco, mas aí vejo alguém na rua com o mesmo jeito de andar que ele e a ferida se abre inteira de novo com a mesma intensidade do primeiro dia.",
        ],
        "relacionamentos": [
            "Meus amigos dizem que preciso sair, conhecer gente nova e 'seguir em frente', mas eu não consigo fingir alegria quando meu peito tá em pedaços. Prefiro ficar quieta no meu canto sem ver ninguém.",
            "Terminei meu namoro semana passada. Não tinha mais energia emocional pra investir na relação, me sentia incapaz de retribuir carinho ou de pensar no futuro a dois.",
            "Sinto uma desconexão imensa quando estou no meio de conversas alegres. Parece que estou assistindo ao mundo por trás de uma vidraça embaçada.",
        ],
        "autoestima": [
            "Não consigo cuidar de mim. Passo dias com a mesma camiseta larga, o cabelo desgrenhado, me sentindo um fantasma invisível andando pela casa.",
            "Sinto culpa até quando dou um sorriso ou dou risada de alguma piada boba. Uma voz na minha cabeça diz que é errado eu sentir qualquer alegria enquanto ele não está mais aqui.",
        ],
        "saude_sono": [
            "O silêncio da noite é insuportável. Acordo com a impressão nítida de ter ouvido a voz dele me chamando pelo apelido de infância, e quando percebo que foi sonho o choro vem sem freio.",
            "Perdi totalmente o apetite. A comida não tem sabor nenhum, como apenas o suficiente pra não desmaiar de fraqueza física.",
        ],
        "familia": [
            "Minha mãe tá tão abalada quanto eu, mas a gente não consegue conversar sobre ele sem que as duas desabem em lágrimas. Ficamos num silêncio doloroso na mesa de jantar.",
            "Tivemos que começar a mexer no inventário e nas coisas que ele deixou. Ver as pessoas discutindo sobre bens materiais enquanto a presença dele faz tanta falta me dá um enjoo profundo.",
        ],
        "trabalho": [
            "Voltei da licença do trabalho mas meu corpo tá presente e minha cabeça tá em outro planeta. Não me importo a mínima se o projeto atrasar ou se o cliente reclamar, tudo parece tão insignificante agora.",
            "Minha chefe veio perguntar se eu já estou pronta pra reassumir os clientes difíceis. Dei uma resposta monossilábica e me tranquei no banheiro pra chorar.",
        ],
        "estudos": [
            "Abro o material da faculdade e as palavras dançam na página sem fazer sentido nenhum. Perdi todo o sentido de urgência e dedicação acadêmica que eu tinha antes.",
            "Não vejo mais motivo pra continuar estudando com tanto afinco se a pessoa que mais se orgulhava das minhas conquistas não vai estar na formatura pra me aplaudir.",
        ],
        "financas": [
            "As custas do inventário e as taxas do cartório consumiram toda a poupança que eu guardava pra emergências. Mais uma preocupação pesada em cima de um coração já despedaçado.",
            "Não consigo me organizar financeiramente agora. Deixo contas vencerem porque a energia mental pra abrir o aplicativo do banco e fazer contas simplesmente acabou.",
        ],
    },
}

_SAFEGUARD_TEMPLATES: list[str] = [
    "Hoje foi um dia relativamente neutro, acordei no horário normal, peguei o ônibus e o tempo estava nublado sem novidades relevantes.",
    "Comprei alguns pães na padaria da esquina e voltei para casa para arrumar as prateleiras da sala.",
    "Tarde tranquila lendo notícias de ciência e ouvindo o barulho suave da chuva na janela da cozinha.",
    "Hoje é quarta-feira normal, fiz algumas anotações na agenda sobre compras domésticas.",
    "Organizei algumas pastas antigas no computador e deletei arquivos temporários sem pressa.",
    "Dia sem grandes acontecimentos, o clima ameno permitiu caminhar no parque no fim da tarde.",
    "Apenas registrando a rotina: café pela manhã, leitura breve e almoço simples em casa.",
    "Não aconteceu nada fora do habitual hoje, mantive o dia calmo e preparei o jantar mais cedo.",
    "Passei no mercado para comprar frutas, arroz e café e depois reguei as plantas da varanda.",
    "Assisti a um documentário sobre astronomia antes de desligar a televisão e descansar.",
    "Limpei a mesa da cozinha, troquei a lâmpada do corredor e separei roupas para doação.",
    "Hoje o trânsito estava tranquilo e aproveitei para ouvir um podcast sobre história no caminho.",
    "Misturei os ingredientes de uma receita simples de bolo de cenoura para o lanche da tarde.",
    "Aproveitei o sábado para lavar o quintal, passear com o cachorro e ouvir música instrumental.",
    "Fui ao correio enviar uma encomenda, depois passei na farmácia comprar protetor solar e voltei a pé.",
    "Troquei os lençóis da cama, coloquei a roupa na máquina de lavar e preparei um suco de laranja.",
    "Assisti à previsão do tempo na televisão e separei um guarda-chuva antes de sair de casa.",
    "Limpei a caixa de entrada de e-mails promocionais e atualizei a lista de compras da geladeira.",
    "Hoje almocei arroz, feijão e salada de tomate, depois li vinte páginas de um romance policial.",
    "Reguei o jardim no fim da tarde, conferi a correspondência na portaria e fiz um chá de camomila.",
    "Comprei ração para o cachorro, varri a garagem e deixei as chaves penduradas na entrada.",
    "Fiz uma lista dos filmes que quero assistir no próximo mês e reservei um livro na biblioteca.",
    "Está tudo bem tranquilo por aqui hoje, aproveitei o feriado para descansar em paz sem preocupações.",
    "Tive um dia sereno e leve, sem conflitos nem aborrecimentos para anotar no diário.",
]

_INTROS: tuple[str, ...] = (
    "",
    "Preciso desabafar isso antes de tentar dormir: ",
    "Mais um dia difícil. ",
    "Escrevendo aqui só pra tirar esse peso do peito: ",
    "Hoje acordei com um aperto estranho no peito. ",
    "Não contei isso pra ninguém hoje, mas: ",
)
_CONCLUSIONS: tuple[str, ...] = (
    "",
    " Amanhã preciso achar um jeito de respirar fundo e continuar.",
    " Só queria uma trégua de tudo isso por alguns dias.",
    " Espero que amanhã seja um pouco menos pesado.",
    " Não sei até quando consigo sustentar esse ritmo.",
    " Enfim, vamos ver como vai ser amanhã.",
)

# Classe nova -> chaves antigas dos templates que a alimentam.
_LEGACY_KEYS_BY_CLASS: dict[str, list[str]] = {
    cls: [old for old, new in LEGACY_TO_NEW.items() if new == cls] for cls in CLASSES
}

# Bases de template ordenadas por tamanho (desc) e texto, para casamento determinístico:
# a base mais longa contida no texto define a família. Calculado uma única vez.
_TEMPLATE_BASES: tuple[str, ...] = tuple(
    sorted(
        {t for pool in _OFFLINE_TEMPLATES.values() for texts in pool.values() for t in texts}
        | set(_SAFEGUARD_TEMPLATES),
        key=lambda s: (-len(s), s),
    )
)

# Erros esperados ao usar o Ollama; caímos no gerador offline quando ocorrem.
_OLLAMA_ERRORS: tuple[type[BaseException], ...] = (OSError, RuntimeError, ValueError, KeyError) + (
    (httpx.HTTPError,) if httpx is not None else ()
)


def load_personas(personas_path: Path | str | None = None) -> list[dict[str, Any]]:
    """Carrega as definições de personas de JSON ou usa o fallback embutido."""
    path = Path(personas_path) if personas_path else DEFAULT_PERSONAS_PATH
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list) and data:
                return data
        except (OSError, json.JSONDecodeError, ValueError) as err:
            logger.warning("Falha ao carregar %s (%s). Usando personas padrão.", path, err)
    return DEFAULT_PERSONAS


def infer_template_group(text: str) -> str:
    """Identifica a família de template; textos desconhecidos são agrupados pelo conteúdo exato.

    Não descobre paráfrases arbitrárias de corpora externos ou gerados por LLM;
    esses corpora devem fornecer seu próprio group_id.
    """
    canonical = next((base for base in _TEMPLATE_BASES if base in text), None)
    if canonical is None:
        canonical = " ".join(text.split())
    return "template_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]


def _theme_templates(persona_id: str, theme: str) -> list[str]:
    """Textos de uma classe para a persona; se vazio, usa o pool de qualquer persona."""
    keys = _LEGACY_KEYS_BY_CLASS.get(theme, [])
    own = _OFFLINE_TEMPLATES.get(persona_id, {})
    texts = [t for k in keys for t in own.get(k, [])]
    if not texts:
        texts = [t for pool in _OFFLINE_TEMPLATES.values() for k in keys for t in pool.get(k, [])]
    return texts


def generate_single_report_offline(
    persona: dict[str, Any],
    theme: str,
    random_state: random.Random | None = None,
) -> str:
    """Gera um relato fictício offline; não representa uma pessoa real."""
    rng = random_state or random.Random()
    if theme == SAFEGUARD_CLASS:
        return rng.choice(_SAFEGUARD_TEMPLATES)

    pool = _theme_templates(persona.get("id", ""), theme)
    if pool:
        base_text = rng.choice(pool)
    else:
        base_text = f"Hoje refleti muito sobre {CLASS_DESCRIPTIONS[theme]}. Tem sido difícil lidar com tudo isso."

    intro = rng.choice(_INTROS)
    conclusion = rng.choice(_CONCLUSIONS)
    return f"{intro}{base_text}{conclusion}".strip()


def _is_valid_report(text: str) -> bool:
    """Rejeita respostas vazias ou que vazaram o próprio prompt."""
    return len(text) >= 40 and "PERSONA:" not in text and "DIRETRIZES" not in text


def generate_single_report_ollama(
    persona: dict[str, Any],
    theme: str,
    client: httpx.Client,
    model: str = "qwen2.5:3b",
) -> str:
    """Gera um relato pelo endpoint local do Ollama, reutilizando um cliente HTTP."""
    prompt = GENERATOR_PROMPT_TEMPLATE.format(
        nome=persona["nome"],
        tracos=persona["tracos"],
        estilo_linguagem=persona["estilo_linguagem"],
        tema=CLASS_DESCRIPTIONS[theme],
    )
    resp = client.post(
        "/api/chat",
        json={
            "model": model,
            "stream": False,
            "messages": [{"role": "user", "content": prompt}],
            "options": {"temperature": 0.85},
        },
    )
    resp.raise_for_status()
    content = resp.json()["message"]["content"].strip()
    if not _is_valid_report(content):
        raise ValueError("Resposta do Ollama vazia ou fora do formato esperado")
    return content


def generate_synthetic_dataset(
    output_path: str = "data/synthetic/synthetic_diaries.json",
    samples_per_class: int = 40,
    include_safeguard: bool = True,
    use_ollama: bool = False,
    ollama_url: str = "http://localhost:11434",
    model: str = "qwen2.5:3b",
    personas_path: str | None = None,
    seed: int = 42,
) -> list[dict[str, Any]]:
    """Gera o dataset sintético com os rótulos da taxonomia de 6 classes."""
    if use_ollama and httpx is None:
        raise RuntimeError("--ollama requer o pacote httpx instalado")

    rng = random.Random(seed)
    personas = load_personas(personas_path)
    classes = list(CLINICAL_CLASSES) + ([SAFEGUARD_CLASS] if include_safeguard else [])
    client = httpx.Client(base_url=ollama_url.rstrip("/"), timeout=30.0) if use_ollama else None

    dataset: list[dict[str, Any]] = []
    try:
        for cls in classes:
            logger.info("Gerando %d relatos para a classe: %s", samples_per_class, cls)
            for i in range(samples_per_class):
                persona = rng.choice(personas)
                text: str | None = None
                method = "offline_template"

                if client is not None:
                    try:
                        text = generate_single_report_ollama(persona, cls, client, model)
                        method = "ollama"
                    except _OLLAMA_ERRORS as err:
                        logger.warning("Ollama falhou (%s). Usando gerador offline.", err)

                if text is None:
                    text = generate_single_report_offline(persona, cls, rng)

                family = infer_template_group(text)
                dataset.append(
                    {
                        "id": f"syn_{cls}_{i + 1:03d}",
                        "persona_id": persona["id"],
                        "macro_tema": cls,
                        "texto": text,
                        "modalidade": "texto",
                        "group_id": family,
                        "template_id": family,
                        "label_origin": "synthetic_requested_class_unreviewed",
                        "generation_method": method,
                        "taxonomia": "v6",
                    }
                )
    finally:
        if client is not None:
            client.close()

    _write_json(dataset, output_path)
    logger.info("Dataset sintético salvo em %s (%d registros).", output_path, len(dataset))
    return dataset


def remap_legacy_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Reclassifica registros sintéticos antigos. O texto não muda; só o rótulo."""
    out = []
    for rec in records:
        new = dict(rec)
        new["macro_tema_anterior"] = rec.get("macro_tema")
        new["macro_tema"] = remap_legacy_label(rec["macro_tema"])
        new["taxonomia"] = "v6"
        out.append(new)
    return out


def _write_json(data: Any, path: str | Path) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Gerador de dataset sintético (6 classes)")
    parser.add_argument("--output", "-o", default="data/synthetic/synthetic_diaries.json")
    parser.add_argument(
        "--samples-per-class", "--samples-per-theme", "-s", type=int, default=40,
        help="Quantidade de amostras por classe",
    )
    parser.add_argument("--ollama", action="store_true", help="Gera via Ollama (requer serviço ativo)")
    parser.add_argument("--ollama-url", default="http://localhost:11434")
    parser.add_argument("--model", default="qwen2.5:3b")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--personas", default=None, help="Caminho para personas.json customizado")
    parser.add_argument(
        "--remap-legacy", metavar="JSON", default=None,
        help="Apenas reclassifica um JSON sintético antigo (9 classes) para as 6 novas",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    if args.remap_legacy:
        records = json.loads(Path(args.remap_legacy).read_text(encoding="utf-8"))
        _write_json(remap_legacy_records(records), args.output)
        return

    generate_synthetic_dataset(
        output_path=args.output,
        samples_per_class=args.samples_per_class,
        use_ollama=args.ollama,
        ollama_url=args.ollama_url,
        model=args.model,
        personas_path=args.personas,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
