<script setup>
import { ref, useId } from 'vue'
import { Info } from 'lucide-vue-next'
defineProps({ text: { type:String, required:true }, label: { type:String, default:'Mais informações' } })
const id=useId(),visible=ref(false),position=ref({}),trigger=ref(null)
function show() {
  const rect=trigger.value.getBoundingClientRect()
  const width=Math.min(280,window.innerWidth-24)
  position.value={left:`${Math.max(12,Math.min(rect.left,window.innerWidth-width-12))}px`,top:`${rect.bottom+125>window.innerHeight?Math.max(12,rect.top-120):rect.bottom+9}px`,width:`${width}px`}
  visible.value=true
}
function hide() {visible.value=false}
</script>
<template><button ref="trigger" type="button" class="info-tooltip-trigger" :aria-label="label" :aria-describedby="visible?id:undefined" @mouseenter="show" @mouseleave="hide" @focus="show" @blur="hide" @click.stop.prevent="show" @keydown.esc.stop="hide"><Info :size="14"/></button><Teleport to="body"><div v-if="visible" :id="id" class="info-tooltip-content" role="tooltip" :style="position">{{text}}</div></Teleport></template>
