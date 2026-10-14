import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import './style.css'
import { dialogDirective } from './dialog'
createApp(App).use(createPinia()).directive('dialog',dialogDirective).mount('#app')
