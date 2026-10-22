# Colaboração

Cada tarefa deve ter objetivo, responsável, critério de aceite e evidência verificável. Dividir tarefas entre as seis pessoas após confirmar os integrantes e seus acessos.

1. Criar uma branch curta, por exemplo `feature/nome-da-tarefa`.
2. Fazer commits pequenos sem credenciais ou dados pessoais.
3. Abrir um Pull Request para `main`, relacionando a tarefa.
4. Pedir revisão de outra pessoa e obter uma aprovação antes do merge.
5. Resolver comentários e anexar a validação aplicável.
6. Após o merge, atualizar a tarefa e remover a branch quando apropriado.

Fluxo planejado do quadro: **Todo → In Progress → In Review → Done**.
Done exige critérios atendidos e evidências anexadas.

## Situação da proteção

A regra de uma aprovação é um acordo do time enquanto o bloqueio de plano descrito em [infraestrutura](docs/infrastructure.md) existir. Este documento e o template de PR não impedem tecnicamente pushes diretos.

## Primeira implementação

Definir versão de Python, dependências e lockfile, comando de execução, testes significativos e CI que execute essas verificações. Escolher ferramentas de agentes e MLOps após definir a proposta.
