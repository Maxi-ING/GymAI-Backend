import { defineConfig, devices } from '@playwright/test';
import path from 'node:path';
const root = path.resolve(import.meta.dirname, '../..');
export default defineConfig({
  testDir: '.',
  testMatch: '*.spec.mjs',
  workers: 1,
  retries: 1,
  timeout: 45000,
  use: { baseURL: 'http://localhost:4173', timezoneId: 'America/Lima', trace: 'retain-on-failure' },
  projects: [
    { name: 'desktop', use: devices['Desktop Chrome'] },
    { name: 'mobile', use: devices['Pixel 7'] },
  ],
  webServer: [
    { command: 'python -m uvicorn app.main:app --host 127.0.0.1 --port 8000', cwd: root, url: 'http://127.0.0.1:8000/health', reuseExistingServer: false },
    { command: 'npm run dev -- --host 127.0.0.1 --port 4173', cwd: path.join(root, 'frontend'), url: 'http://localhost:4173', reuseExistingServer: false },
  ],
});
