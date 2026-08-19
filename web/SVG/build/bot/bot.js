const puppeteer = require("puppeteer");

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function main() {
  const targetUrl = process.argv[2];
  if (!targetUrl) {
    throw new Error("usage: node bot.js <target-url>");
  }

  const username = process.env.BOT_USERNAME || "23a9d8d2de1df569";
  const password = process.env.BOT_PASSWORD || "9f4df8f4849e26e7";
  const executablePath = process.env.BOT_BROWSER_PATH || "/usr/bin/chromium";

  const browser = await puppeteer.launch({
    headless: true,
    executablePath,
    args: [
      "--no-sandbox",
      "--disable-setuid-sandbox",
      "--disable-dev-shm-usage"
    ]
  });

  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1440, height: 980 });
    await page.goto(targetUrl, { waitUntil: "networkidle2", timeout: 30000 });
    await page.waitForSelector("#uname", { timeout: 10000 });
    await page.type("#uname", username, { delay: 45 });
    await page.type("#passwd", password, { delay: 45 });
    await sleep(2500);
    await Promise.allSettled([
      page.click('button[type="submit"]'),
      page.waitForNavigation({ waitUntil: "networkidle2", timeout: 15000 })
    ]);
    await sleep(1000);
    console.log("Completed!");
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error && error.stack ? error.stack : String(error));
  process.exit(1);
});
