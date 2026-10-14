import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import { subscribeWorkspace } from '../realtime'
import { api } from '../api'
export const useWorkboard = defineStore('workboard', () => {
  const user = ref(null), boards = ref([]), selected = ref(null), error = ref(''), busy = ref(false)
  const board = computed(() => {const selectedBoard=boards.value.find(b=>b.id===selected.value);return selectedBoard?.columns?selectedBoard:undefined})
  const details=ref({}),boardsNext=ref(null),taskFilters=ref({})
  let boardPages=1
  const columnPages={}
  let loadGeneration=0
  function localPath(url) {return url ? url.replace(/^https?:\/\/[^/]+\/api\//,'') : null}
  async function loadColumn(col,append=false) {
    const query=new URLSearchParams({column:col.id,...taskFilters.value})
    const path=append?col.next:`tasks/?${query}`
    if(!path)return
    const page=await api(path)
    col.tasks=append?[...col.tasks,...page.results.filter(t=>!col.tasks.some(old=>old.id===t.id))]:page.results
    col.next=localPath(page.next);col.filtered_count=page.count
    if(!append)for(let i=1;i<(columnPages[col.id] || 1) && col.next;i++)await loadColumn(col,true)
  }
  async function fetchTask(id) {const task=await api(`tasks/${id}/`);details.value[id]=task;return task}
  async function applyFilters(filters) {
    const normalized=Object.fromEntries(Object.entries(filters).filter(([,value])=>value!=='' && value!=='all'))
    if(JSON.stringify(normalized)===JSON.stringify(taskFilters.value))return
    taskFilters.value=normalized
    for(const key of Object.keys(columnPages))delete columnPages[key]
    await load()
  }
  async function moreTasks(col) {await run(async()=>{loadGeneration++;await loadColumn(col,true);columnPages[col.id]=(columnPages[col.id] || 1)+1})}
  async function moreBoards() {await run(async()=>{loadGeneration++;const page=await api(boardsNext.value);boards.value.push(...page.results);boardsNext.value=localPath(page.next);boardPages++})}
  const connection=ref('offline'),eventTick=ref(0)
  let unsubscribe,refreshDebounce
  function scheduleRefresh() {clearTimeout(refreshDebounce);refreshDebounce=setTimeout(async()=>{if(busy.value){scheduleRefresh();return}try{await load();eventTick.value++}catch{}},100)}
  watch(()=>user.value?.username,username=>{unsubscribe?.();clearTimeout(refreshDebounce);connection.value='offline';if(username)unsubscribe=subscribeWorkspace(scheduleRefresh,status=>connection.value=status)})
  const canWrite = computed(() => ['owner','admin','editor'].includes(board.value?.role) && !board.value?.archived)
  const canManage = computed(() => ['owner','admin'].includes(board.value?.role))
  const undo = ref(null), notice = ref(''),lastUndo=ref(null)
  let undoTimer,undoBoardId,undoContext
  function offerUndo(message, action) { clearTimeout(undoTimer); notice.value=message; undo.value=action;undoBoardId=board.value?.id;undoTimer=setTimeout(() => {undo.value=null;notice.value=''},30000) }
  async function undoLast() { await run(async () => {undoContext=undoBoardId;const previousRevision=boards.value.find(b=>b.id===undoContext)?.revision;try{await undo.value?.();lastUndo.value={board:undoContext,previousRevision,revision:boards.value.find(b=>b.id===undoContext)?.revision}; undo.value=null;notice.value='';clearTimeout(undoTimer)}finally{undoContext=null} }) }
  async function load() {
    const requestedSelection=selected.value,generation=++loadGeneration,page=await api('boards/')
    let list=page.results
    let next=localPath(page.next)
    for(let i=1;i<boardPages && next;i++){const more=await api(next);list.push(...more.results);next=localPath(more.next)}
    if(selected.value && !list.some(b=>b.id===selected.value)) {
      try{const selectedBoard=await api(`boards/${selected.value}/`);list.push(selectedBoard)}catch(e){if(e.status!==404)throw e}
    }
    const id=list.some(b=>b.id===selected.value)?selected.value:list[0]?.id ?? null
    if(id) {
      const workspace=await api(`boards/${id}/`)
      await Promise.all(workspace.columns.map(col=>loadColumn(col)))
      list=list.map(b=>b.id===id?workspace:b)
    }
    if(generation!==loadGeneration || (selected.value!==requestedSelection && selected.value!==id))return
    boards.value=list;boardsNext.value=next;selected.value=id
    for(const id of Object.keys(details.value)) {try{await fetchTask(id)}catch(e){if(e.status===404)delete details.value[id]}}
  }
  watch(selected,async(id,previous)=>{if(id && id!==previous && !board.value?.columns){taskFilters.value={};try{await load()}catch(e){error.value=e.message}}})
  async function run(action) { if (busy.value) return; busy.value = true; error.value = ''; try { await action();return true } catch (e) { error.value = e instanceof Error ? e.message : 'Ocorreu um erro.'; if(e.status===409) { try { await load() } catch {} } return false } finally { busy.value = false } }
  async function init() { await run(async () => { user.value = (await api('session/')).user; if (user.value) await load() }) }
  async function auth(username, password, register, email='') { await run(async () => { user.value = (await api('session/', 'POST', {username,password,register,email})).user; await load() }) }
  async function signOut() { await run(async () => { await api('session/', 'DELETE'); user.value = null; boards.value = []; selected.value = null;undo.value=null;notice.value='';clearTimeout(undoTimer) }) }
  function targetBoard(path,data) {
    const [resource,id]=path.split('/'),number=Number(id)
    if(resource==='boards' && number)return boards.value.find(b=>b.id===number)
    if(data?.board)return boards.value.find(b=>b.id===data.board)
    const taskId=data instanceof FormData ? Number(data.get('task')) : data?.task
    for(const candidate of boards.value) {
      if(resource==='columns' && candidate.columns?.some(c=>c.id===(number || data?.column)))return candidate
      if(resource==='sprints' && candidate.sprints?.some(s=>s.id===number))return candidate
      if(resource==='members' && candidate.members?.some(m=>m.id===number && number))return candidate
      if(resource==='labels' && candidate.labels?.some(l=>l.id===number))return candidate
      if(resource==='retro-notes' && candidate.sprints?.some(s=>s.notes.some(n=>n.id===number)))return candidate
      if(data?.sprint && candidate.sprints?.some(s=>s.id===data.sprint))return candidate
      for(const col of candidate.columns ?? []) {
        if(data?.column===col.id)return candidate
        for(const task of col.tasks) {
          if(task.id===taskId || resource==='tasks' && task.id===number)return candidate
          if(['checklist','comments','attachments'].includes(resource) && details.value[task.id]?.[resource].some(item=>item.id===number))return candidate
        }
      }
    }
    return boards.value.find(b=>b.id===undoContext) ?? board.value
  }
  async function mutate(path, method, data, revision) { const result=await api(path, method, data,revision ?? targetBoard(path,data)?.revision); await load();return result }
  async function restoreBoard(id) { const trash=await api('boards/trash/'); const target=trash.find(b => b.id===id); await mutate(`boards/${id}/restore/`,'POST',{},target?.revision); selected.value=id }
  return {user,boards,selected,board,error,busy,run,init,auth,signOut,mutate,load,canWrite,canManage,undo,notice,offerUndo,undoLast,restoreBoard,lastUndo,connection,eventTick,details,fetchTask,applyFilters,moreTasks,moreBoards,boardsNext,taskFilters}
})
