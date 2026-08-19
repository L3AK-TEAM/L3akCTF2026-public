const puppeteer = require("puppeteer");
const { ADMIN_PASSWORD } = require("./db");

const APP_URL = "http://localhost:3000";
let busy = false;

async function visitPage(pagePath) {
  if (busy) {
    return { success: false, error: "Bot is busy, try again later" };
  }

  if (!pagePath.startsWith("/pages/") || pagePath.includes("..")) {
    return { success: false, error: "Invalid page path" };
  }

  busy = true;
  let browser;

  try {
    browser = await puppeteer.launch({
      headless: "new",
      args: [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
      ],
    });

    const page = await browser.newPage();

    await page.goto(`${APP_URL}/login`, {
      waitUntil: "networkidle2",
      timeout: 10000,
    });

    await page.type('input[name="username"]', "admin");
    await page.type('input[name="password"]', ADMIN_PASSWORD);
    await Promise.all([
      page.waitForNavigation({ waitUntil: "networkidle2", timeout: 10000 }),
      page.click('button[type="submit"]'),
    ]);

    await page.goto(`${APP_URL}${pagePath}`, {
      waitUntil: "networkidle2",
      timeout: 10000,
    });
    await new Promise((r) => setTimeout(r, 5000));

    return { success: true };
  } catch {
    return { success: false, error: "Bot encountered an error" };
  } finally {
    if (browser) await browser.close().catch(() => {});
    busy = false;
  }
}

module.exports = { visitPage };
