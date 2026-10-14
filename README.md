# WorkBoard

Kanban para projetos pessoais com Django REST Framework, Vue 3, JavaScript e Pinia. Interface em português com identidade visual preta e azul, cadastro, login, quadros, colunas e tarefas persistidas no banco.

![WorkBoard](docs/screenshots/10-arrastar-e-concluir.png)

## Funcionalidades

- Autenticação por sessão, proteção CSRF, limite de tentativas e recuperação de senha.
- Quadros pessoais ou compartilhados com três colunas iniciais.
- Tarefas com descrição, prioridade e prazo; criação, edição e exclusão.
- Arrastar tarefas entre colunas ou mover pelo seletor no editor, inclusive no celular.
- Busca por título e descrição e contador da coluna “Concluído”.
- Testes da API e de interface no CI, além de build e verificações de containers.
- Sprints com objetivo, período, planejamento, início e encerramento manual.
- Tarefas vinculadas a sprints, filtro por ciclo e backlog.
- Retrospectiva por sprint com pontos positivos, melhorias e ações acompanháveis.
- Colaboração por perfis de leitor, editor e administrador; responsáveis pelas tarefas.
- Limites WIP, dependências sem ciclos, motivos de bloqueio e ordenação de cartões.
- Etiquetas editáveis, checklist, anexos privados e comentários com histórico.
- Filtros por sprint, responsável, prioridade, etiqueta, bloqueio e prazo.
- Métricas de entrega e fluxo, notificações internas e alertas de prazo.
- Gestão de quadros/colunas, arquivamento, lixeira, confirmação de exclusão e desfazer.
- Revisão de dados com resposta de conflito em alterações simultâneas; foco controlado nos diálogos.

## Recursos avançados

### Colaboração e acesso

Em **Configurações → Equipe**, adicione o nome de um usuário já cadastrado. O acesso é imediato, sem envio de mensagens externas. Leitores podem consultar quadros, anexos e métricas; editores podem trabalhar em tarefas, sprints e retrospectivas; administradores também gerenciam configurações, membros, etiquetas e colunas. O dono é o único que pode excluir o quadro e nomear/remover administradores. Remover um membro revoga seu acesso e retira suas atribuições naquele quadro.

### Etiquetas e responsáveis

Crie etiquetas em **Configurações → Etiquetas**, com nome e cor. Elas podem ser editadas ou excluídas. No editor da tarefa, selecione etiquetas e um responsável da equipe.

### Limites WIP e tipos de coluna

**WIP** significa *Work in Progress* — trabalho em andamento. O limite impede que uma coluna receba mais tarefas ativas do que sua capacidade. Com limite 3, uma quarta tarefa só entra quando uma das três sair. Deixe o campo vazio para não limitar. O ícone de informação abre essa explicação por mouse, foco de teclado ou toque; Escape fecha o tooltip.

Configure nome, ordem, tipo e capacidade das colunas em **Configurações → Quadro e colunas**. O tipo “Concluída” define a conclusão, mesmo se a coluna for renomeada. Para alterar o tipo ou excluir uma coluna, ela deve estar vazia. O limite também é validado pela API ao criar, mover, desarquivar ou restaurar tarefas.

### Dependências, bloqueios e ordenação

Selecione dependências no cartão e registre um motivo para bloqueios manuais. Uma tarefa bloqueada ou com dependências pendentes não pode entrar em uma coluna de conclusão. A API rejeita dependências de outros quadros e ciclos. Uma tarefa referenciada por outras não pode ser excluída até remover esses vínculos.

Arraste um cartão sobre outro para inseri-lo antes dele, inclusive na mesma coluna. Soltar na área da coluna coloca o cartão no fim. As setas “Subir” e “Descer” oferecem ordenação por teclado e toque. Os filtros mudam a visualização; o limite WIP sempre considera todas as tarefas ativas da coluna.

### Checklist, arquivos, comentários e histórico

Salve o cartão para abrir checklist, anexos e as abas de comentários e histórico. Itens do checklist podem ser adicionados, editados, concluídos e removidos. Anexos têm limite de **10 MB por arquivo** e download protegido por autenticação e acesso ao quadro. Comentários podem ser editados/excluídos pelo autor ou por administradores; ações ficam registradas no histórico.

### Filtros e notificações

Combine busca textual com filtros por sprint, responsável, prioridade, etiqueta, bloqueio e prazo. O sino mostra atribuições, comentários e entrada em um quadro, além de tarefas atrasadas ou com prazo nos próximos dois dias. Os alertas de prazo são calculados na consulta; as outras notificações ficam persistidas e podem ser marcadas como lidas.

### Métricas de fluxo

A aba **Métricas** mostra tarefas ativas, concluídas e bloqueadas, capacidade das colunas, **lead time** (criação até conclusão), **cycle time** (primeira execução até conclusão), entregas por dia e fluxo acumulado nos últimos 14 dias. Os tempos médios usam cartões atualmente concluídos e não arquivados; o histórico de entregas preserva conclusões mesmo após reabrir, arquivar ou excluir, contando uma entrega por tarefa por dia.

O fluxo histórico começa na implantação desse recurso. Para cartões antigos, o estado inicial e a conclusão foram registrados na data da migração; não é possível reconstruir datas de execução que a versão anterior não guardava.

### Arquivamento, exclusão e recuperação

Arquivar uma tarefa a retira do fluxo atual sem apagar seu conteúdo; consulte e desarquive em **Configurações → Arquivados**. Arquivar um quadro deixa seu conteúdo em modo de consulta. A exclusão de tarefas, colunas vazias e quadros exige confirmação e preserva os registros para restauração.

Use **Desfazer** por 30 segundos após as ações que oferecem esse recurso. Para tarefas e colunas, a lixeira permanece disponível depois desse período. Quadros excluídos podem ser restaurados pelo dono pelo ícone de recuperação no cabeçalho. A restauração de tarefas respeita o WIP e exige que a coluna esteja ativa. Exclusões de itens de checklist, comentários, notas e anexos podem ser desfeitas por recriação durante os 30 segundos; esses itens não têm lixeira permanente. Exclusão de sprint planejada exige confirmação e preserva as tarefas no backlog.

### Edições simultâneas

Cada gravação usa a revisão do quadro via `If-Match`. Se outro usuário alterar o quadro antes do salvamento, a API responde **409** e a interface preserva o formulário. No cartão, use “Recarregar dados da tarefa” para conferir a versão mais recente. A proteção é por quadro: alterações em cartões diferentes também podem exigir atualização, evitando sobreposição silenciosa.

## Sprints e retrospectivas

Use as abas **Visão Kanban**, **Sprints** e **Retrospectiva** dentro de cada quadro. Sprints são ciclos opcionais de planejamento; o Kanban continua disponível para acompanhar todo o trabalho.

1. Crie uma sprint com nome, objetivo, data inicial e final. Sprints planejadas podem ser editadas ou excluídas.
2. Abra os cartões no Kanban e selecione a sprint da tarefa. “Backlog — sem sprint” mantém a tarefa fora de um ciclo.
3. Inicie a sprint. Cada quadro permite uma única sprint em andamento. As datas são de planejamento; o sistema não inicia ou encerra automaticamente.
4. Use “Ver tarefas” ou o filtro do Kanban para visualizar o ciclo.
5. Abra a retrospectiva para registrar conquistas, melhorias e ações. As notas podem ser editadas/excluídas; as ações podem ser concluídas e reabertas.
6. Encerre a sprint com confirmação. O sistema registra os totais do ciclo e devolve tarefas pendentes ao backlog, preservando os cartões. A retrospectiva continua editável.

A conclusão usa colunas configuradas com o tipo **Concluída**, independentemente do nome. A coluna inicial “Concluído” já tem esse tipo. Os indicadores de sprints encerradas são um retrato numérico do encerramento; não são recalculados se os cartões mudarem depois. O botão “Histórico da sprint” preserva os participantes e seus dados no encerramento, inclusive tarefas retiradas do ciclo, devolvidas ao backlog ou excluídas depois. O filtro do Kanban mostra apenas os cartões atualmente vinculados. Sprints encerradas não podem receber novas tarefas, ser reabertas, editadas ou excluídas. Ações de retrospectiva são itens de acompanhamento próprios e não criam cartões automaticamente.

## Atualizações em tempo real e histórico

Alterações confirmadas no banco notificam as sessões dos membros por WebSocket. Eventos não transportam dados privados do quadro; o cliente consulta a API novamente, que revalida as permissões. Logout e troca de senha revogam a sessão; o servidor revalida a conexão a cada entrega e heartbeat.

O histórico das sprints guarda participantes, dados dos cartões e retiradas. Os ciclos encerrados preservam esse registro mesmo quando tarefas são alteradas depois. Sprints existentes antes da migração importam apenas os cartões ainda vinculados; participantes removidos anteriormente não podem ser reconstruídos.

![Histórico preservado da sprint](docs/screenshots/58-historico-sprint.png)

## Demonstração visual

### Acesso e organização do projeto

Login e cadastro abrem o espaço do usuário. Quadros recebem as colunas iniciais automaticamente e podem ganhar novas etapas.

![Login](docs/screenshots/01-login.png)

![Cadastro](docs/screenshots/02-cadastro.png)

![Primeiro acesso](docs/screenshots/03-primeiro-acesso.png)

![Criar quadro](docs/screenshots/04-criar-quadro.png)

![Quadro criado](docs/screenshots/05-quadro-criado.png)

![Criar coluna](docs/screenshots/06-criar-coluna.png)

### Fluxo de tarefas

Crie e edite cartões, mova-os entre etapas, busque por texto e acompanhe os dados persistidos. O editor também permite mover tarefas em dispositivos móveis.

![Criar tarefa](docs/screenshots/07-criar-tarefa.png)

![Quadro com tarefas](docs/screenshots/08-quadro-com-tarefas.png)

![Editar e mover tarefa](docs/screenshots/09-editar-e-mover.png)

![Arrastar e concluir](docs/screenshots/10-arrastar-e-concluir.png)

![Buscar tarefas](docs/screenshots/11-buscar-tarefas.png)

![Persistência após recarregar](docs/screenshots/12-persistencia.png)

![Kanban no celular](docs/screenshots/13-mobile.png)

![Excluir tarefa pelo editor](docs/screenshots/14-excluir-tarefa.png)

![Resultado da exclusão](docs/screenshots/15-tarefa-excluida.png)

![Retorno ao login após sair](docs/screenshots/16-logout.png)

### Planejamento de sprints

Defina um objetivo e um período, vincule tarefas e inicie o ciclo. O Kanban pode ser filtrado pela sprint para acompanhar a entrega.

![Criar sprint](docs/screenshots/17-criar-sprint.png)

![Sprint planejada](docs/screenshots/18-sprint-planejada.png)

![Vincular tarefa à sprint](docs/screenshots/19-vincular-tarefa-sprint.png)

![Sprint ativa](docs/screenshots/20-sprint-ativa.png)

![Kanban filtrado por sprint](docs/screenshots/21-filtrar-sprint.png)

### Retrospectiva e encerramento

Registre conquistas, melhorias e ações. O encerramento guarda o resultado do ciclo, e a retrospectiva continua disponível para consulta e evolução.

![Retrospectiva](docs/screenshots/22-retrospectiva.png)

![Ação concluída](docs/screenshots/23-acao-concluida.png)

![Confirmar encerramento](docs/screenshots/24-encerrar-sprint.png)

![Sprint encerrada](docs/screenshots/25-sprint-encerrada.png)

![Retrospectiva histórica](docs/screenshots/26-retrospectiva-historica.png)

![Retrospectiva no celular](docs/screenshots/27-retrospectiva-mobile.png)

### Equipe, etiquetas e capacidade

Configure perfis de acesso, organize etiquetas, escolha responsáveis e defina limites de trabalho em andamento. O tooltip explica WIP com um exemplo.

![Equipe e permissões](docs/screenshots/28-equipe-permissoes.png)

![Acesso de leitura](docs/screenshots/29-acesso-leitor.png)

![Etiquetas](docs/screenshots/30-etiquetas.png)

![Editar etiqueta](docs/screenshots/54-editar-etiqueta.png)

![Colunas e limites WIP](docs/screenshots/31-colunas-wip.png)

![Explicação de WIP](docs/screenshots/55-tooltip-wip.png)

![Responsável e etiqueta na tarefa](docs/screenshots/32-tarefa-responsavel-etiqueta.png)

### Detalhes e acompanhamento

Checklists, anexos, comentários e histórico reúnem o contexto do trabalho. Dependências e bloqueios aparecem nos cartões; a ordem pode ser ajustada por arrastar ou pelos controles de subir/descer.

![Checklist e anexos](docs/screenshots/33-checklist-anexos.png)

![Comentários](docs/screenshots/34-comentarios.png)

![Histórico da tarefa](docs/screenshots/35-historico-tarefa.png)

![Bloqueios e dependências](docs/screenshots/36-bloqueios-dependencias.png)

![Validação do limite WIP](docs/screenshots/37-limite-wip-bloqueando.png)

![Ordenação de cartões](docs/screenshots/38-ordenacao-cartoes.png)

![Filtros avançados](docs/screenshots/39-filtros-avancados.png)

![Notificações e prazos](docs/screenshots/40-notificacoes-prazos.png)

![Métricas de fluxo](docs/screenshots/41-metricas-fluxo.png)

![Histórico do quadro](docs/screenshots/48-historico-quadro.png)

![Filtros no celular](docs/screenshots/50-kanban-avancado-mobile.png)

### Recuperação e gestão do quadro

Arquivamento preserva o conteúdo. Exclusões têm confirmação, opção de desfazer e lixeira para quadros, colunas e tarefas. Edições simultâneas exibem um conflito antes de sobrescrever informações.

![Tarefas arquivadas](docs/screenshots/42-tarefas-arquivadas.png)

![Confirmar exclusão de tarefa](docs/screenshots/43-confirmar-exclusao.png)

![Opção de desfazer](docs/screenshots/44-opcao-desfazer.png)

![Lixeira de itens](docs/screenshots/45-lixeira-itens.png)

![Restaurar tarefa](docs/screenshots/46-restaurar-tarefa.png)

![Conflito de edição](docs/screenshots/47-conflito-edicao.png)

![Editar quadro](docs/screenshots/49-editar-quadro.png)

![Quadro arquivado](docs/screenshots/51-quadro-arquivado.png)

![Lixeira de quadros](docs/screenshots/52-lixeira-quadros.png)

![Quadro restaurado](docs/screenshots/53-quadro-restaurado.png)

![Excluir coluna](docs/screenshots/56-excluir-coluna.png)

![Restaurar coluna](docs/screenshots/57-restaurar-coluna.png)

## Executar

Requisitos: Python 3.13 e Node.js 22. Em dois terminais PowerShell, a partir da raiz:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend/requirements.txt
cd backend
..\.venv\Scripts\python manage.py migrate
..\.venv\Scripts\python manage.py runserver 127.0.0.1:8000
```

```powershell
cd frontend
npm ci
npm run dev
```

Abra http://127.0.0.1:5173 e cadastre sua conta. O Vite encaminha `/api` ao Django na mesma origem. Não há credenciais predefinidas.

## Docker

Com Docker e Docker Compose instalados:

```powershell
docker compose up --build --wait
```

Abra http://localhost:8080. PostgreSQL, Redis, arquivos e recursos estáticos usam volumes persistentes. Essa execução usa um banco separado do SQLite local, portanto contas e quadros precisam ser criados novamente nesse ambiente. Apenas Nginx publica uma porta no host.

Para produção, copie `.env.example` para `.env`, configure os valores e gere uma chave forte:

```powershell
.\.venv\Scripts\python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
docker compose -f compose.yml -f compose.production.yml up --build --wait
```

O perfil de produção exige chave, domínio, origem HTTPS, senha do banco e SMTP. Coloque Nginx atrás de um proxy TLS que substitua os cabeçalhos encaminhados; o backend não publica uma porta direta. Use uma senha de banco compatível com URL. A inicialização aplica migrações e coleta arquivos estáticos; em uma implantação com várias réplicas, execute as migrações em uma etapa única antes de subir as réplicas.

O CI sobe os containers e verifica a rota da API. Docker não estava disponível no ambiente local de implementação; a execução foi confirmada pelo [job de containers](https://github.com/rabelismerim/WorkBoard/actions/runs/38653852010), junto dos testes de backend, interface e build.

## Conta e recuperação de senha

No cadastro pela interface, informe seu e-mail. Contas antigas podem adicioná-lo em **Minha conta**, clicando no nome do usuário no cabeçalho e confirmando a senha atual. A API mantém compatibilidade com contas sem e-mail; elas precisam cadastrar um endereço antes de usar a recuperação.

Use **Esqueci minha senha** no login. O sistema responde com a mesma mensagem para e-mails cadastrados e desconhecidos. O link vale por uma hora, só pode ser usado uma vez e a troca de senha invalida as sessões anteriores.

Login, recuperação, redefinição e alteração de e-mail usam limites persistidos no banco. O padrão é de 10 tentativas por identificação e 30 por IP em 15 minutos; ao atingir o limite, a API responde `429` com `Retry-After`. `AUTH_RATE_LIMIT` ajusta a quantidade. Endereços de proxy só são usados quando explicitamente habilitados; o perfil de produção ativa isso atrás do Nginx, que substitui `X-Real-IP`.

Em desenvolvimento, o backend de e-mail escreve o link no terminal do Django. Em produção, configure SMTP e `PUBLIC_URL` com a origem HTTPS do frontend. A entrega por um provedor externo depende dessas credenciais; os testes usam uma caixa de e-mail em memória.

![Conta e e-mail de recuperação](docs/screenshots/59-conta-email.png)

![Solicitar recuperação de senha](docs/screenshots/60-recuperar-senha.png)

![Definir uma nova senha](docs/screenshots/61-redefinir-senha.png)

## Estrutura e verificações

`backend/config` contém configurações e URLs; `backend/boards`, modelos, serializers, API e testes. `frontend/src` contém a interface, cliente HTTP e store Pinia. A relação é `User → Board → Column → Task`; o acesso do dono e dos membros é validado nas consultas e gravações. `work_views.py` concentra as APIs, `access.py` centraliza permissões, WIP e revisões; `FlowEvent` registra as transições para os gráficos.

```powershell
cd backend
..\.venv\Scripts\python manage.py check
..\.venv\Scripts\python manage.py test
```

```powershell
cd frontend
npm run build
```

Os testes permanentes de interface usam um banco e servidores isolados nas portas 8001 e 5174:

```powershell
cd frontend
npx playwright install chromium
npm run test:e2e
```

Para usar o Edge já instalado no Windows, configure `$env:PLAYWRIGHT_CHANNEL = "msedge"` antes de rodar os testes. O CI instala Chromium e executa os fluxos de login, movimentação, recuperação, colaboração em tempo real, histórico das sprints, conta e segurança. Evidências de falha ficam em uma pasta ignorada pelo Git e podem ser consultadas nos artifacts do CI.

SQLite facilita o desenvolvimento. Para PostgreSQL, exporte `DATABASE_URL` antes das migrações. Veja `backend/.env.example`; ele documenta variáveis e não é carregado automaticamente.

## Produção e próximos passos

O projeto inclui configuração Docker para desenvolvimento e uma sobreposição de produção. O servidor é ASGI (Daphne), com PostgreSQL, Redis e Nginx. Configure HTTPS no proxy de entrada, uma chave secreta forte, hosts/origens, credenciais SMTP e backups antes de publicar.

A atualização principal usa WebSocket autenticado. O navegador reconecta automaticamente; consultas periódicas permanecem como fallback quando a conexão está indisponível. Redis distribui eventos entre processos em produção; o desenvolvimento local pode usar uma camada em memória com um único processo.

As listas de quadros e tarefas usam páginas de 50 registros (limite configurável de até 100 pela API). O frontend pagina os cartões por coluna; filtros e buscas são aplicados no servidor antes da paginação. Checklist, comentários, anexos e histórico são carregados ao abrir o cartão.

Próximas evoluções: agrupamento de eventos para quadros muito grandes e notificações de atividades por e-mail. O envio de e-mail implementado nesta versão atende à recuperação de senha.

Anexos ficam em `backend/media`, não entram no Git e só podem ser baixados por uma rota autenticada. Inclua essa pasta nos backups. A aplicação baixa arquivos como anexos, não como conteúdo executável; não há varredura antivírus integrada.

Referências: [Django](https://docs.djangoproject.com/en/5.2/), [Vue](https://vuejs.org/guide/quick-start.html), [Pinia](https://pinia.vuejs.org/).
