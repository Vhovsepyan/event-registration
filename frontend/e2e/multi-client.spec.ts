import { expect, test } from '@playwright/test'

test('check-in in browser B updates the live dashboard in browser A', async ({ browser, page }) => {
  const unique = `${Date.now()}-${Math.random().toString(16).slice(2)}`

  await page.goto('/')
  await page.getByLabel('Event title').fill(`Live update ${unique}`)
  await page.getByLabel('Description').fill('Two-client Playwright verification')
  await page.getByLabel('Date and time').fill('2035-10-12T14:00')
  await page.getByLabel('Capacity').fill('2')
  await page.getByRole('button', { name: 'Create event' }).click()
  await expect(page).toHaveURL(/\/events\/[^/]+\/organizer$/)
  await expect(page.getByLabel('Checked in: 0')).toBeVisible()

  const eventId = new URL(page.url()).pathname.split('/')[2]
  const browserB = await browser.newContext()
  const participant = await browserB.newPage()
  try {
    await participant.goto(`/events/${eventId}`)
    await participant.getByLabel('Email address').fill(`guest-${unique}@example.com`)
    await participant.getByRole('button', { name: 'Register' }).click()
    await expect(participant.getByRole('heading', { name: 'Your place is secured' })).toBeVisible()
    const ticketCode = (await participant.locator('.ticket-code').textContent())?.trim()
    expect(ticketCode).toBeTruthy()

    await participant.goto('/check-in')
    await participant.getByLabel('Ticket code').fill(ticketCode!)
    await participant.getByRole('button', { name: 'Check in' }).click()
    await expect(participant.getByRole('heading', { name: 'Check-in successful' })).toBeVisible()

    await expect(page.getByLabel('Checked in: 1')).toBeVisible({ timeout: 10_000 })
    await expect(page.getByText('Live', { exact: true })).toBeVisible()
  } finally {
    await browserB.close()
  }
})
