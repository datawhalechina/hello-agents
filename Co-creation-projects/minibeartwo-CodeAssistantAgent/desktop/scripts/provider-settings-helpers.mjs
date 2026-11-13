/** Enter a custom API address through the same popup used by the client. */
export async function chooseCustomProvider(page, address) {
  const provider = page.getByRole('combobox', { name: 'API 服务商', exact: true });
  if ((await provider.inputValue()) === 'custom')
    await page.getByRole('button', { name: '编辑地址', exact: true }).click();
  else await provider.selectOption('custom');
  const popup = page.getByRole('dialog', { name: '自定义服务商', exact: true });
  await popup.waitFor();
  await popup.locator('input[name="base_url"]').fill(address);
  await popup.getByRole('button', { name: '使用此地址', exact: true }).click();
  await popup.waitFor({ state: 'hidden' });
}
