import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '../api'
export const useWorkboard = defineStore('workboard', () => {
  const user = ref(null), boards = ref([]), selected = ref(null), error = ref(''), busy = ref(false)
  const board = computed(() => boards.value.find(b => b.id === selected.value))
  const canWrite = computed(() => ['owner','admin','editor'].includes(board.value?.role) && !board.value?.archived)
  const canManage = computed(() => ['owner','admin'].includes(board.value?.role))
  const undo = ref(null), notice = ref(''),lastUndo=ref(null)
  let undoTimer,undoBoardId,undoContext
  function offerUndo(message, action) { clearTimeout(undoTimer); notice.value=message; undo.value=action;undoBoardId=board.value?.id;undoTimer=setTimeout(() => {undo.value=null;notice.value=''},30000) }
  async function undoLast() { await run(async () => {undoContext=undoBoardId;const previousRevision=boards.value.find(b=>b.id===undoContext)?.revision;try{await undo.value?.();lastUndo.value={board:undoContext,previousRevision,revision:boards.value.find(b=>b.id===undoContext)?.revision}; undo.value=null;notice.value='';clearTimeout(undoTimer)}finally{undoContext=null} }) }
  async function load() { boards.value = await api('boards/'); if (!boards.value.some(b => b.id === selected.value)) selected.value = boards.value[0]?.id ?? null }
  async function run(action) { if (busy.value) return; busy.value = true; error.value = ''; try { await action();return true } catch (e) { error.value = e instanceof Error ? e.message : 'Ocorreu um erro.'; if(e.status===409) { try { await load() } catch {} } return false } finally { busy.value = false } }
  async function init() { await run(async () => { user.value = (await api('session/')).user; if (user.value) await load() }) }
  async function auth(username, password, register) { await run(async () => { user.value = (await api('session/', 'POST', {username,password,register})).user; await load() }) }
  async function signOut() { await run(async () => { await api('session/', 'DELETE'); user.value = null; boards.value = []; selected.value = null;undo.value=null;notice.value='';clearTimeout(undoTimer) }) }
  function targetBoard(path,data) {
    const [resource,id]=path.split('/'),number=Number(id)
    if(resource==='boards' && number)return boards.value.find(b=>b.id===number)
    if(data?.board)return boards.value.find(b=>b.id===data.board)
    const taskId=data instanceof FormData ? Number(data.get('task')) : data?.task
    for(const candidate of boards.value) {
      if(resource==='columns' && candidate.columns.some(c=>c.id===(number || data?.column)))return candidate
      if(resource==='sprints' && candidate.sprints.some(s=>s.id===number))return candidate
      if(resource==='members' && candidate.members.some(m=>m.id===number && number))return candidate
      if(resource==='labels' && candidate.labels.some(l=>l.id===number))return candidate
      if(resource==='retro-notes' && candidate.sprints.some(s=>s.notes.some(n=>n.id===number)))return candidate
      if(data?.sprint && candidate.sprints.some(s=>s.id===data.sprint))return candidate
      for(const col of candidate.columns) {
        if(data?.column===col.id)return candidate
        for(const task of col.tasks) {
          if(task.id===taskId || resource==='tasks' && task.id===number)return candidate
          if(['checklist','comments','attachments'].includes(resource) && task[resource].some(item=>item.id===number))return candidate
        }
      }
    }
    return boards.value.find(b=>b.id===undoContext) ?? board.value
  }
  async function mutate(path, method, data, revision) { const result=await api(path, method, data,revision ?? targetBoard(path,data)?.revision); await load();return result }
  async function restoreBoard(id) { const trash=await api('boards/trash/'); const target=trash.find(b => b.id===id); await mutate(`boards/${id}/restore/`,'POST',{},target?.revision); selected.value=id }
  return {user,boards,selected,board,error,busy,run,init,auth,signOut,mutate,load,canWrite,canManage,undo,notice,offerUndo,undoLast,restoreBoard,lastUndo}
})
