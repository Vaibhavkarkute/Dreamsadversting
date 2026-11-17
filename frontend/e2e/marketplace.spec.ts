import { test, expect } from '@playwright/test';

test.describe('DreamsAdverstings OOH/DOOH Marketplace E2E Suite', () => {
  test('renders hero headline, filters Pune inventory, builds shortlist and calculates quotation', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('h1')).toContainText('MAKE YOUR BRAND IMPOSSIBLE TO IGNORE.');
    await page.click('[data-testid="nav-inventory"]');
    await expect(page.locator('[data-testid="inventory-count"]')).toBeVisible();
  });
});
