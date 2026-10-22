# Acesso e credenciais

Verificação em 22/10/2026.

## Evidências observadas

- A credencial é um PAT fine-grained, associado à identidade diogobertozi.
- Leitura e escrita de arquivos e labels funcionaram neste repositório privado da organização.
- Após a atualização do PAT, a criação de Projects da organização funcionou.
- A leitura administrativa de colaboradores e de metadados de secrets no repositório pessoal público diogobertozi/diogobertozi recebeu 403. Nenhum valor de secret foi consultado.
- O token informou expiração em 21/12/2026 às 18:58:39, horário de São Paulo.
- A consulta de inventário de PATs da organização não serve para auditar este PAT: esse endpoint aceita somente GitHub Apps.

Os testes são consistentes com o isolamento esperado, mas não constituem uma auditoria exaustiva de todos os endpoints. Confirmar no formulário do token o Resource owner **007-Licensa-Para-Executar**. Um PAT fine-grained tem um único Resource owner. Leitura de repositórios públicos fora desse owner continua possível.

O campo permissions.admin retornado nos metadados de um repositório descreve os direitos do usuário; não comprova que o token tenha autorização para executar uma operação administrativa naquele repositório.

## Permissões para a configuração e o uso cotidiano

O proprietário informou ter habilitado 39 permissões de repositório e 40 da organização. Não é necessário manter todas para as tarefas aqui implementadas. A configuração do PAT não foi alterada pelo agente.

| Área | Permissão | Uso |
| --- | --- | --- |
| Repository | Metadata: Read | Metadados obrigatórios |
| Repository | Contents: Read and write | Código e arquivos |
| Repository | Issues: Read and write | Labels e tarefas |
| Repository | Pull requests: Read and write | Colaboração por PR |
| Repository | Administration: Read and write | Criação/configuração de repositório e proteção de branch; remover do token de rotina se não for administrar |
| Organization | Projects: Read and write | Quadro do time |
| Organization | Members: Read | Inspeção de integrantes, se necessária |
| Repository | Actions: Read | Inspeção de CI, quando houver |
| Repository | Workflows: Read and write | Somente se o agente precisar editar workflows |

Organization Administration: Read pode ser usado para auditoria das configurações privadas da organização; não é necessário manter escrita ampla para este setup.

Para trabalhar somente neste repositório, selecionar **Only select repositories → challenge-2-base**. Para criar ou administrar outros repositórios da mesma organização, avaliar Repository access e as permissões necessárias para essas operações. Não trocar o Resource owner para a conta pessoal.

## Operação segura

- Usar exclusivamente a credencial específica da organização nesta integração.
- Não usar silenciosamente outra sessão global do GitHub CLI como fallback.
- Não incluir o PAT em configurações compartilhadas, prompts, logs ou commits.
- Usar credenciais individuais para os integrantes do time.
- Não ampliar permissões para resolver erros de plano: a proteção da main privada depende do plano da organização.

Referências:
- https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens
- https://docs.github.com/en/rest/orgs/personal-access-tokens
