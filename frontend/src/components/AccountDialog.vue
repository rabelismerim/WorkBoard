<script setup>
import { ref, onMounted } from 'vue'
import { X } from 'lucide-vue-next'
import { api } from '../api'
import { useWorkboard } from '../stores/workboard'
const emit=defineEmits(['close'])
const store=useWorkboard(),email=ref(''),password=ref(''),saved=ref(false)
onMounted(()=>store.run(async()=>{email.value=(await api('account/')).email}))
async function save() {await store.run(async()=>{await api('account/','POST',{email:email.value,password:password.value});saved.value=true;password.value=''})}
</script>
<template><div class="modal-backdrop" @click.self="!store.busy && emit('close')" @keydown.esc="!store.busy && emit('close')"><section v-dialog class="modal" role="dialog" aria-modal="true" aria-labelledby="account-title"><div class="modal-heading"><h2 id="account-title">Minha conta</h2><button aria-label="Fechar" @click="emit('close')"><X :size="20"/></button></div><p>Cadastre um e-mail para recuperar o acesso caso esqueça sua senha.</p><form @submit.prevent="save"><label>E-mail de recuperação<input v-model="email" type="email" required autocomplete="email"></label><label>Senha atual<input v-model="password" type="password" required autocomplete="current-password"></label><p v-if="store.error" class="error" role="alert">{{store.error}}</p><p v-if="saved" role="status">E-mail de recuperação salvo.</p><button class="primary" :disabled="store.busy">Salvar e-mail</button></form></section></div></template>
