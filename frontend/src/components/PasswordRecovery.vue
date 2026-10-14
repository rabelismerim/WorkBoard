<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api'
const props=defineProps({uid:String,token:String})
const emit=defineEmits(['close'])
const email=ref(''),password=ref(''),confirmation=ref(''),error=ref(''),message=ref(''),busy=ref(false)
onMounted(()=>api('session/').catch(()=>{}))
async function submit() {
  if(props.uid && password.value!==confirmation.value){error.value='As senhas não coincidem.';return}
  busy.value=true;error.value=''
  try{const result=await api(props.uid?'password/reset/':'password/recovery/','POST',props.uid?{uid:props.uid,token:props.token,password:password.value}:{email:email.value});message.value=result.detail;password.value='';confirmation.value=''}catch(e){error.value=e.message}finally{busy.value=false}
}
</script>
<template><section class="auth-form"><span class="eyebrow">RECUPERE SEU ESPAÇO</span><h2>{{uid?'Definir nova senha':'Esqueceu a senha?'}}</h2><p>{{uid?'Escolha uma senha forte para voltar aos seus projetos.':'Informe o e-mail de recuperação cadastrado na sua conta.'}}</p><form v-if="!message" @submit.prevent="submit"><template v-if="uid"><label>Nova senha<input v-model="password" required minlength="8" type="password" autocomplete="new-password"></label><label>Confirmar nova senha<input v-model="confirmation" required minlength="8" type="password" autocomplete="new-password"></label></template><label v-else>E-mail de recuperação<input v-model="email" type="email" required autocomplete="email"></label><p v-if="error" class="error" role="alert">{{error}}</p><button class="primary" :disabled="busy">{{busy?'Aguarde…':uid?'Atualizar senha':'Enviar instruções'}}</button></form><p v-else role="status">{{message}}</p><button class="text-button" @click="emit('close')">Voltar ao login</button></section></template>
