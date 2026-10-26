# Ponytail no desenvolvimento

Fonte revisada: https://github.com/DietrichGebert/ponytail
Commit: `09c434ab73ca43761c5d8b0c5d341926c2fba710`.
Manifesto Codex revisado: versão `5.3.2`, licença MIT.

A skill foi instalada no escopo do projeto em `.agents/skills/ponytail` com o instalador de
skills e referência fixada no commit acima. Estará disponível no próximo turno que descobrir
skills desse projeto. Nenhum AGENTS.md existente foi substituído. O Ponytail é orientação de
desenvolvimento/revisão, não um orquestrador de agentes do produto nem dependência Python.

## Skill instalada versus plugin com hooks

O CLI antigo em `/opt/homebrew/bin/codex` não respondeu corretamente aos comandos de plugins;
o binário nativo encerrou com sinal 9. Uma instalação portátil de CLI recente foi tentada sem
alterar a instalação global. A descoberta/ativação do plugin completo não deve ser presumida
pelo simples download da skill.

O adaptador Codex do autor declara hooks para **SessionStart**, **SubagentStart** e
**UserPromptSubmit**. Eles podem escrever estado em PLUGIN_DATA, ler fontes para gerar mapa
de código e injetar instruções no contexto. O texto de instalação menciona dois hooks, mas o
manifesto revisado contém três eventos. Nenhum desses hooks foi executado ou considerado
confiável automaticamente nesta instalação da skill.

Quando um CLI compatível estiver disponível, os comandos documentados pelo autor são:

```sh
codex plugin marketplace add DietrichGebert/ponytail
codex plugin add ponytail@ponytail
```

Verificar a versão/manifestações que serão instaladas e revisar os hooks em `/hooks` antes
de ativá-los. O autor orienta iniciar novo chat e reiniciar o desktop. Os comandos `/plugin
marketplace add` e `/plugin install` enviados originalmente pertencem ao fluxo Claude Code.

Referências:
- https://github.com/DietrichGebert/ponytail/blob/09c434ab73ca43761c5d8b0c5d341926c2fba710/INSTALL.md
- https://github.com/DietrichGebert/ponytail/blob/09c434ab73ca43761c5d8b0c5d341926c2fba710/hooks/claude-codex-hooks.json
