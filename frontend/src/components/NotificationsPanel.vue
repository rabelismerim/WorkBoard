<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { Bell, X, RotateCcw } from 'lucide-vue-next'
import { api } from '../api'
import { useWorkboard } from '../stores/workboard'
const emit=defineEmits(['open-task'])
const store=useWorkboard(),open=ref(false),notifications=ref([]),deadlines=ref([]),trash=ref([]),trashOpen=ref(false)
let timer
async function refresh() { try {const [n,d]=await Promise.all([api('notifications/'),api('notifications/deadlines/')]);notifications.value=n;deadlines.value=d}catch{} }
onMounted(()=>{refresh();timer=setInterval(refresh,30000)})
onUnmounted(()=>clearInterval(timer))
async function showTrash() {await store.run(async()=>{trash.value=await api('boards/trash/');trashOpen.value=true})}
async function restore(id) {await store.run(async()=>{await store.restoreBoard(id);trash.value=await api('boards/trash/')})}
function go(item) {store.selected=item.board;const task=store.board?.columns.flatMap(c=>c.tasks).find(t=>t.id===(item.task ?? item.id));if(task)emit('open-task',task);open.value=false}
</script>
<template><div class="header-tools"><button aria-label="Quadros excluídos" @click="showTrash"><RotateCcw :size="16"/></button><button class="notification-button" aria-label="Notificações" @click="open=!open;refresh()"><Bell :size="18"/><span v-if="notifications.some(n=>!n.read) || deadlines.length" class="notification-dot"></span></button></div><div v-if="open" class="notification-panel"><div class="modal-heading"><h3>Notificações e prazos</h3><button aria-label="Fechar notificações" @click="open=false"><X :size="18"/></button></div><button class="text-button" @click="api('notifications/read_all/','POST',{}).then(refresh)">Marcar notificações como lidas</button><h4>Prazos próximos e atrasados</h4><button v-for="item in deadlines" :key="item.id" class="notification-item" @click="go(item)"><strong>{{item.title}}</strong><span :class="{overdue:item.overdue}">{{item.overdue?'Atrasada':'Prazo próximo'}} · {{item.due_date}}</span></button><p v-if="!deadlines.length">Nenhuma tarefa com prazo nos próximos dois dias.</p><h4>Atualizações</h4><button v-for="item in notifications" :key="item.id" class="notification-item" :class="{unread:!item.read}" @click="go(item)"><span>{{item.message}}</span><small>{{new Date(item.created_at).toLocaleString('pt-BR')}}</small></button><p v-if="!notifications.length">Nenhuma atualização.</p></div><div v-if="trashOpen" class="modal-backdrop" @click.self="trashOpen=false" @keydown.esc="trashOpen=false"><section v-dialog class="modal" role="dialog" aria-modal="true" aria-labelledby="board-trash-title"><div class="modal-heading"><h2 id="board-trash-title">Quadros excluídos</h2><button aria-label="Fechar" @click="trashOpen=false"><X :size="20"/></button></div><p>Somente quadros dos quais você é dono aparecem aqui.</p><div v-for="board in trash" :key="board.id" class="trash-row"><strong>{{board.title}}</strong><button :disabled="store.busy" @click="restore(board.id)">Restaurar quadro</button></div><p v-if="!trash.length">Nenhum quadro excluído.</p><p v-if="store.error" class="error">{{store.error}}</p></section></div></template>
