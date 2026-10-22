# Infraestrutura inicial

Verificação em 22/10/2026.

## Preparado

- Repositório privado na organização `007-Licensa-Para-Executar`.
- Branch principal `main` e .gitignore padrão para Python.
- Oito labels específicas das exigências.
- Diretórios agents, knowledge_base, mlops, models e docs.
- Requisitos rastreáveis, roteiro de oito semanas e template de Pull Request.

## Pendências reais

### Proteção da main

A API do GitHub recusou a consulta de branch protection e de rulesets por limitação do plano no repositório privado. Não há confirmação de proteção ativa.

Para organizações, proteção em repositórios privados requer GitHub Team ou Enterprise. Manter o repositório privado até decisão do proprietário sobre o plano.

Depois de habilitar o recurso, configurar:
- Pull Request obrigatório.
- Uma aprovação de outra pessoa.
- Descartar aprovações obsoletas após novos commits.
- Aplicar as regras também a administradores, sem bypass.
- Bloquear force pushes e deleção da branch.
- Exigir resolução das conversas.
- Acrescentar checks obrigatórios somente depois que um CI real existir.

O scaffolding inicial é a exceção de bootstrap solicitada pelo proprietário. Alterações futuras devem passar por PR.

Referência: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches

### GitHub Project

Na verificação inicial, o PAT recebeu 403 ao listar Projects da organização. Falta autorização de organização **Projects: Read and write**.

Criar Project privado pertencente à organização, associá-lo a este repositório e usar uma visualização Board agrupada pelo campo Status: Todo, In Progress, In Review e Done. Revalidar a API depois da atualização do token.

### Time

Foram observados três usuários com acesso: um administrador e dois com leitura. Confirmar os seis integrantes e conceder permissões de contribuição adequadas antes de distribuir tarefas. Os acessos existentes não foram alterados.

### Aplicação e CI

A ideia e a stack ainda não foram escolhidas. Acrescentar dependências, execução, testes e CI com a primeira implementação. As pastas vazias não representam entrega dos requisitos acadêmicos.
