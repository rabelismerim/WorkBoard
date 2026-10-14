import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
const backend=process.env.BACKEND_URL || 'http://127.0.0.1:8000'
export default defineConfig({ plugins: [vue()], server: { proxy: { '/api': backend, '/ws': {target:backend.replace(/^http/,'ws'),ws:true} } } })
