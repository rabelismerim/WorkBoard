import { test, expect } from '@playwright/test'
import { randomBytes } from 'node:crypto'

const password='E2e-strong-pass-942!'
test.beforeEach(async({page})=>{page.on('pageerror',error=>console.error('Browser error:',error.message))})
async function account(context,role='user') {
  const username=`${role}_${randomBytes(5).toString('hex')}`
  await context.request.get('/api/session/')
  const cookies=await context.cookies()
  const csrf=cookies.find(c=>c.name==='csrftoken').value
  const response=await context.request.post('/api/session/',{data:{username,password,register:true},headers:{'X-CSRFToken':csrf}})
  expect(response.ok()).toBeTruthy()
  return username
}
async function mutate(context,path,data,method='PATCH') {
  const boards=(await (await context.request.get('/api/boards/')).json()).results
  const csrf=(await context.cookies()).find(c=>c.name==='csrftoken').value
  const response=await context.request.fetch(`/api/${path}`,{method,data,headers:{'X-CSRFToken':csrf,...(boards[0]?{'If-Match':String(boards[0].revision)}:{})}})
  expect(response.ok()).toBeTruthy()
  return response.status()===204?null:response.json()
}
async function createBoard(page) {
  await page.goto('/')
  await page.getByRole('button',{name:'Criar meu primeiro quadro'}).click()
  await page.getByRole('dialog').getByLabel('Título',{exact:true}).fill('Projeto E2E')
  await page.getByRole('dialog').getByRole('button',{name:'Salvar',exact:true}).click()
  await expect(page.getByRole('dialog')).toBeHidden()
  await expect(page.getByRole('button',{name:'Nova tarefa',exact:true})).toBeVisible()
  return (await (await page.request.get('/api/boards/')).json()).results[0]
}
async function createTask(page,title) {
  await page.getByRole('button',{name:'Nova tarefa',exact:true}).click()
  await page.getByRole('dialog').getByLabel('Título',{exact:true}).fill(title)
  await page.getByRole('dialog').getByRole('button',{name:'Salvar',exact:true}).click()
  await expect(page.getByRole('dialog')).toBeHidden()
  await expect(page.locator('.task').filter({hasText:title})).toBeVisible()
}

test('login, task movement, confirmation, undo and persistence',async({page,context})=>{
  const username=await account(context)
  await createBoard(page)
  await createTask(page,'Validar projeto')
  await page.locator('.task').filter({hasText:'Validar projeto'}).dragTo(page.locator('.column').filter({has:page.getByRole('heading',{name:'Concluído',exact:true})}))
  await expect(page.locator('.column').filter({has:page.getByRole('heading',{name:'Concluído',exact:true})}).locator('.task')).toContainText('Validar projeto')
  await page.reload()
  await page.getByRole('button',{name:'Validar projeto',exact:true}).click()
  await page.getByRole('dialog').getByRole('button',{name:'Excluir',exact:true}).click()
  await page.getByRole('dialog').getByRole('button',{name:'Confirmar exclusão',exact:true}).click()
  await expect(page.getByRole('dialog')).toBeHidden()
  await page.getByRole('button',{name:'Desfazer',exact:true}).click()
  await expect(page.getByRole('button',{name:'Validar projeto',exact:true})).toBeVisible()
  await page.getByRole('button',{name:'Sair da conta',exact:true}).first().click()
  await page.getByLabel('Usuário',{exact:true}).fill(username)
  await page.getByLabel('Senha',{exact:true}).fill(password)
  await page.getByRole('button',{name:'Entrar no WorkBoard',exact:true}).click()
  await expect(page.getByRole('button',{name:'Validar projeto',exact:true})).toBeVisible()
})

test('shared board updates through WebSocket and viewer cannot write',async({page,context,browser})=>{
  await account(context)
  const board=await createBoard(page)
  const other=await browser.newContext({baseURL:'http://127.0.0.1:5174'})
  try{
    const username=await account(other,'viewer')
    await mutate(context,'members/',{board:board.id,username,role:'viewer'},'POST')
    const viewer=await other.newPage()
    await viewer.goto('/')
    await expect(viewer.getByText('Você tem acesso de leitura a este quadro.')).toBeVisible()
    await expect(viewer.getByRole('button',{name:'Nova tarefa',exact:true})).toHaveCount(0)
    await createTask(page,'Mudança em tempo real')
    await expect(viewer.getByRole('button',{name:'Mudança em tempo real',exact:true})).toBeVisible({timeout:8000})
    const task=(await (await other.request.get(`/api/tasks/?board=${board.id}`)).json()).results[0]
    const csrf=(await other.cookies()).find(c=>c.name==='csrftoken').value
    const denied=await other.request.patch(`/api/tasks/${task.id}/`,{data:{title:'Proibido'},headers:{'X-CSRFToken':csrf,'If-Match':String(board.revision)}})
    expect(denied.status()).toBe(403)
  }finally{await other.close()}
})

test('sprint history preserves unfinished tasks after closure',async({page,context})=>{
  await account(context)
  const board=await createBoard(page)
  await createTask(page,'Entrega pendente')
  const sprint=await mutate(context,'sprints/',{board:board.id,title:'Sprint histórica',start_date:'2026-10-14',end_date:'2026-10-28'},'POST')
  const task=(await (await context.request.get(`/api/tasks/?board=${board.id}`)).json()).results[0]
  await mutate(context,`tasks/${task.id}/`,{sprint:sprint.id})
  await mutate(context,`sprints/${sprint.id}/start/`,{},'POST')
  await mutate(context,`sprints/${sprint.id}/complete/`,{},'POST')
  await mutate(context,`tasks/${task.id}/`,{title:'Outra entrega'})
  await page.reload()
  await page.getByRole('button',{name:'Sprints',exact:true}).click()
  await page.getByRole('button',{name:'Histórico de Sprint histórica',exact:true}).click()
  await expect(page.getByRole('dialog')).toContainText('Entrega pendente')
  await expect(page.getByRole('dialog')).toContainText('Pendente')
})

test('account email and recovery screens handle invalid links safely',async({page,context})=>{
  const username=await account(context)
  await page.goto('/')
  await page.getByRole('button',{name:'Minha conta',exact:true}).click()
  await page.getByRole('dialog').getByLabel('E-mail de recuperação').fill(`${username}@example.com`)
  await page.getByRole('dialog').getByLabel('Senha atual').fill(password)
  await page.getByRole('dialog').getByRole('button',{name:'Salvar e-mail',exact:true}).click()
  await expect(page.getByRole('status')).toContainText('E-mail de recuperação salvo.')
  await page.getByRole('dialog').getByRole('button',{name:'Fechar',exact:true}).click()
  await page.getByRole('button',{name:'Sair da conta',exact:true}).first().click()
  await page.getByRole('button',{name:'Esqueci minha senha',exact:true}).click()
  await page.getByLabel('E-mail de recuperação').fill('unknown@example.com')
  await page.getByRole('button',{name:'Enviar instruções',exact:true}).click()
  await expect(page.getByRole('status')).toContainText('Se o e-mail estiver cadastrado')
  await page.goto('/?reset_uid=invalid&reset_token=invalid')
  await page.getByLabel('Nova senha',{exact:true}).fill('Another-strong-password-937!')
  await page.getByLabel('Confirmar nova senha',{exact:true}).fill('Another-strong-password-937!')
  await page.getByRole('button',{name:'Atualizar senha',exact:true}).click()
  await expect(page.getByRole('alert')).toContainText(/inválid|expirado/)
})

test('login rate limit responds with retry information',async({context})=>{
  await context.request.get('/api/session/')
  const csrf=(await context.cookies()).find(c=>c.name==='csrftoken').value
  const username=`missing_${randomBytes(5).toString('hex')}`
  for(let i=0;i<10;i++)expect((await context.request.post('/api/session/',{data:{username,password:'wrong'},headers:{'X-CSRFToken':csrf}})).status()).toBe(400)
  const limited=await context.request.post('/api/session/',{data:{username,password:'wrong'},headers:{'X-CSRFToken':csrf}})
  expect(limited.status()).toBe(429)
  expect(limited.headers()['retry-after']).toBeTruthy()
})

test('column pagination loads more cards without losing them on refresh',async({page,context})=>{
  await account(context,'pages')
  const board=await mutate(context,'boards/',{title:'Quadro paginado'},'POST')
  for(let i=0;i<60;i++)await mutate(context,'tasks/',{column:board.columns[0].id,title:`Cartão paginado ${i}`},'POST')
  await page.goto('/')
  await expect(page.locator('.task')).toHaveCount(50)
  await page.getByRole('button',{name:/^Carregar mais tarefas/}).click()
  await expect(page.locator('.task')).toHaveCount(60)
  const task=(await (await context.request.get(`/api/tasks/?board=${board.id}`)).json()).results[0]
  await mutate(context,`tasks/${task.id}/`,{description:'Atualização em tempo real'})
  await expect(page.locator('.task').filter({hasText:'Atualização em tempo real'})).toBeVisible()
  await expect(page.locator('.task')).toHaveCount(60)
})
