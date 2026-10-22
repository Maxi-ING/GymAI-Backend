import { test, expect } from '@playwright/test';
async function nav(page, name) {
  const button = page.locator('.topbar button[aria-controls="sidebar-navigation"]');
  await expect(button).toBeVisible();
  if (await button.getAttribute('aria-label') === 'Abrir menú') await button.click();
  await page.getByRole('navigation', { name: 'Navegación principal' }).getByRole('link', { name, exact: true }).click();
}
async function login(page, email, password) {
  await page.goto('/');
  await page.getByLabel('Correo electrónico').fill(email);
  await page.getByLabel('Contraseña').fill(password);
  await page.getByRole('button', { name: 'Entrar a mi espacio' }).click();
}
test.beforeEach(async ({ page }) => {
  await page.route('https://fonts.googleapis.com/**', r => r.abort());
});
test('el frontend registra perfil y sesiones reales y consulta una predicción persistente', async ({ page, request }) => {
  const email = 'browser-' + Date.now() + '@example.com';
  const password = 'Browser-Member-Testing-123';
  await page.goto('/');
  await page.getByRole('button', { name: 'Crear cuenta', exact: true }).click();
  await page.getByLabel('Nombre', { exact: true }).fill('Max Backend');
  await page.getByLabel('Correo electrónico').fill(email);
  await page.getByLabel('Contraseña').fill(password);
  await page.getByRole('button', { name: 'Crear mi cuenta' }).click();
  await expect(page.getByText('Tu cuenta fue creada. Inicia sesión para completar tu perfil.')).toBeVisible();
  await login(page, email, password);
  const dialog = page.getByRole('dialog');
  await expect(dialog).toBeVisible();
  await dialog.getByLabel('Edad', { exact: true }).fill('24');
  await dialog.getByLabel('Talla (m)').fill('1.75');
  await dialog.getByLabel('Peso actual (kg)').fill('80');
  await dialog.getByLabel('Objetivo', { exact: true }).selectOption('Ganar fuerza');
  await dialog.getByRole('button', { name: 'Guardar perfil' }).click();
  await expect(dialog).not.toBeVisible();
  await expect(page.getByRole('heading', { name: 'Inicio, Max.' })).toBeVisible();
  await nav(page, 'Entrenamiento');
  await page.getByLabel('Ejercicio 1', { exact: true }).selectOption('1');
  await page.getByLabel('Carga (kg)', { exact: true }).fill('40');
  await page.getByRole('button', { name: 'Guardar sesión' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Sesión guardada' })).toBeVisible();
  await page.getByText('Ver ejercicios (1)', { exact: true }).click();
  await expect(page.locator('.session-exercises li').filter({ hasText: '3 series × 8 rep. × 40 kg' })).toBeVisible();
  const tokenResponse = await request.post('http://localhost:8000/auth/login', { data: { correo: email, clave: password } });
  const { access_token } = await tokenResponse.json();
  const headers = { Authorization: 'Bearer ' + access_token };
  const current = await page.getByLabel('Fecha del entrenamiento').inputValue();
  for (let i = 0; i < 4; i++) {
    const date = new Date(current + 'T12:00:00Z');
    date.setUTCDate(date.getUTCDate() - (4 - i) * 7);
    const response = await request.post('http://localhost:8000/sesiones', { headers, data: { fecha: date.toISOString().slice(0, 10), registros: [{ ejercicio_id: 1, series: 3, repeticiones: 8, carga_kg: 32 + i * 2 }] } });
    expect(response.status()).toBe(201);
  }
  await nav(page, 'Inicio');
  await expect(page.locator('.calendar-trained')).not.toHaveCount(0);
  await nav(page, 'Análisis');
  await page.getByLabel('Ejercicio para analizar').selectOption('1');
  await expect(page.getByLabel('Repeticiones comparadas')).toHaveValue('8');
  await expect(page.getByText('5 semanas comparables disponibles', { exact: true })).toBeVisible();
  await page.getByText('Definir o revisar una meta', { exact: true }).click();
  await page.getByLabel('Carga objetivo (kg)').fill('50');
  const [savedGoal] = await Promise.all([
    page.waitForResponse(response => response.url().endsWith('/metas') && response.request().method() === 'POST'),
    page.getByRole('button', { name: 'Guardar meta' }).click(),
  ]);
  expect(savedGoal.status()).toBe(201);
  const goal = await savedGoal.json();
  await expect(page.getByLabel('Meta del análisis')).toHaveValue(String(goal.id));
  expect(goal.repeticiones_objetivo).toBe(8);
  await expect(page.getByLabel('Repeticiones comparadas')).toBeDisabled();
  const [analysisResponse] = await Promise.all([
    page.waitForResponse(response => response.url().endsWith('/analisis') && response.request().method() === 'POST'),
    page.getByRole('button', { name: 'Analizar mi progreso', exact: true }).click(),
  ]);
  expect(analysisResponse.status()).toBe(200);
  const analysis = await analysisResponse.json();
  expect(analysis.modelo_version).toBe('lineal_comparable_v2');
  expect(analysis.repeticiones_analizadas).toBe(8);
  expect(analysis.error_mae_kg).toBe(0);
  expect(analysis.validaciones_temporales).toBe(3);
  await expect(page.getByRole('heading', { name: '2. Historial y predicción disponible' })).toBeVisible();
  await expect(page.getByText('42 kg', { exact: true })).toBeVisible();
  await page.reload();
  await nav(page, 'Inicio');
  await expect(page.getByText(/Último análisis · Press de banca/)).toBeVisible();
  const sessions = await request.get('http://localhost:8000/sesiones', { headers });
  expect((await sessions.json()).length).toBe(5);
});
test('el administrador gestiona catálogo y cuentas mediante la API real', async ({ page }) => {
  await login(page, 'browser-admin@example.com', 'Browser-Testing-Only-123');
  await expect(page.getByRole('heading', { name: 'Resumen del gimnasio' })).toBeVisible();
  await nav(page, 'Usuarios');
  await expect(page.getByRole('link', { name: 'Gestionar Admin', exact: true })).toBeVisible();
  await nav(page, 'Ejercicios');
  await page.getByLabel('Nombre del ejercicio').fill('Remo de prueba ' + Date.now());
  await page.getByRole('button', { name: 'Agregar al catálogo' }).click();
  await expect(page.getByRole('cell').filter({ hasText: 'Remo de prueba' }).last()).toBeVisible();
  await page.getByRole('link', { name: 'Mi perfil desde la cuenta' }).click();
  await expect(page.getByRole('heading', { name: 'Perfil de administrador' })).toBeVisible();
});
