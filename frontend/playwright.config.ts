import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'e2e',use:{baseURL:'http://127.0.0.1:8000',launchOptions:{executablePath:'/opt/google/chrome/chrome',args:['--no-sandbox','--disable-dev-shm-usage']}},reporter:'list'});
