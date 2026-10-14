import { spawn, spawnSync } from 'node:child_process'
import { existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
const backend=fileURLToPath(new URL('../../backend/',import.meta.url))
const localPython=fileURLToPath(new URL(process.platform==='win32'?'../../.venv/Scripts/python.exe':'../../.venv/bin/python',import.meta.url))
const python=process.env.E2E_PYTHON || (existsSync(localPython)?localPython:'python')
const database=fileURLToPath(new URL(`../../backend/e2e-${process.pid}.sqlite3`,import.meta.url)).replaceAll('\\','/')
const env={...process.env,DJANGO_DEBUG:'true',DATABASE_URL:`sqlite:///${database}`,REDIS_URL:'',AUTH_RATE_LIMIT:'10',EMAIL_BACKEND:'django.core.mail.backends.locmem.EmailBackend',CSRF_TRUSTED_ORIGINS:'http://127.0.0.1:5174'}
const migrated=spawnSync(python,['manage.py','migrate','--noinput'],{cwd:backend,env,stdio:'inherit'})
if(migrated.status!==0)process.exit(migrated.status || 1)
const child=spawn(python,['manage.py','runserver','127.0.0.1:8001','--noreload'],{cwd:backend,env,stdio:'inherit'})
process.on('SIGTERM',()=>child.kill())
process.on('SIGINT',()=>child.kill())
child.on('exit',code=>process.exit(code || 0))
