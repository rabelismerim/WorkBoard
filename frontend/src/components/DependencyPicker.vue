<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { api } from '../api'
import { useWorkboard } from '../stores/workboard'
const props=defineProps({modelValue:Array,taskId:Number})
const emit=defineEmits(['update:modelValue'])
const store=useWorkboard(),search=ref(''),options=ref([]),next=ref(null),error=ref('')
let timer,generation=0
async function load(append=false) {
  const ticket=++generation
  try{
    const path=append?next.value:`tasks/?${new URLSearchParams({board:store.selected,archived:'all',search:search.value})}`
    const page=await api(path)
    if(ticket!==generation)return
    options.value=append?[...options.value,...page.results]:page.results
    for(const id of props.modelValue ?? [])if(!options.value.some(t=>t.id===id))options.value.push(await api(`tasks/${id}/`))
    next.value=page.next?.replace(/^https?:\/\/[^/]+\/api\//,'') ?? null
    error.value=''
  }catch(e){error.value=e.message}
}
watch(search,()=>{clearTimeout(timer);timer=setTimeout(()=>load(),250)})
onMounted(()=>load())
onUnmounted(()=>{clearTimeout(timer);generation++})
</script>
<template><div class="dependency-picker"><label>Buscar dependências<input v-model="search" placeholder="Buscar tarefa por título..."></label><label>Dependências<select multiple aria-label="Dependências" size="3" :value="modelValue" :disabled="!store.canWrite" @change="emit('update:modelValue',[...$event.target.selectedOptions].map(o=>Number(o.value)))"><option v-for="t in options.filter(t=>t.id!==taskId)" :key="t.id" :value="t.id">#{{t.id}} · {{t.title}}</option></select><small>Selecione tarefas que devem terminar antes desta.</small></label><button v-if="next" type="button" class="text-button" @click="load(true)">Carregar mais opções</button><p v-if="error" class="error">{{error}}</p></div></template>
