import { defineConfig, devices } from '@playwright/test'
export default defineConfig({
  testDir:'./tests/e2e',
  fullyParallel:false,
  workers:1,
  timeout:45000,
  retries:process.env.CI?1:0,
  reporter:process.env.CI?'github':'list',
  use:{baseURL:'http://127.0.0.1:5174',trace:'retain-on-failure',screenshot:'only-on-failure'},
  projects:[{name:'chromium',use:{...devices['Desktop Chrome'],...(process.env.PLAYWRIGHT_CHANNEL?{channel:process.env.PLAYWRIGHT_CHANNEL}:{})}}],
  webServer:[
    {command:'node tests/start-backend.mjs',url:'http://127.0.0.1:8001/api/session/',timeout:60000,reuseExistingServer:false},
    {command:'npm run dev -- --port 5174 --strictPort',url:'http://127.0.0.1:5174',env:{BACKEND_URL:'http://127.0.0.1:8001'},reuseExistingServer:false},
  ],
})
