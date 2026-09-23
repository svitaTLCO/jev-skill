import fs from 'node:fs';
import { test, expect } from '@playwright/test';

fs.mkdirSync('artifacts', { recursive: true });

test('solo race renders, starts, accepts driving, and pauses', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', (error) => pageErrors.push(error.message));
  await page.goto('/');
  await expect(page.getByRole('heading', { name: /CIRCUIT.*SPRINT/i })).toBeVisible();
  await expect(page.locator('canvas')).toBeVisible();
  await page.getByRole('button', { name: /SOLO RACE/ }).click();
  await expect(page.locator('#intro')).toBeHidden();
  await expect(page.locator('.standing')).toHaveCount(4);
  await expect(page.locator('#standings')).toContainText('RIVAL');
  await page.keyboard.down('w');
  await page.waitForTimeout(1200);
  await page.keyboard.up('w');
  await expect(page.locator('#timer')).not.toHaveText('00:00.0');
  await page.getByRole('button', { name: 'PAUSE' }).click();
  await expect(page.getByRole('button', { name: 'RESUME' })).toBeVisible();
  await expect(page.locator('#race-status')).toHaveText('RACE PAUSED');
  await page.screenshot({ path: 'artifacts/racing.png' });
  expect(pageErrors).toEqual([]);
});

test('two-player mode exposes both drivers', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: /TWO PLAYER/ }).click();
  await expect(page.locator('.standing.player')).toHaveCount(2);
  await expect(page.locator('.standing.player')).toContainText(['YOU', 'P2']);
});
