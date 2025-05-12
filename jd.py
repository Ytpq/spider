import asyncio
import json
import random
from playwright.async_api import async_playwright

def convert_expiration_date(cookies):
    for cookie in cookies:
        if "expirationDate" in cookie:
            cookie["expires"] = int(cookie["expirationDate"])
            del cookie["expirationDate"]
    return cookies

def fix_same_site(cookies):
    for cookie in cookies:
        if "sameSite" not in cookie or cookie["sameSite"] not in ["Strict", "Lax", "None"]:
            cookie["sameSite"] = "Lax"
    return cookies

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # 可设置为 True 启用无头
            slow_mo=random.randint(80, 150)  # 模拟更自然的用户延迟
        )

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
            locale="zh-CN",
            viewport={"width": 1280, "height": 1024},
            timezone_id="Asia/Shanghai",
            java_script_enabled=True,
            bypass_csp=True,
            permissions=["geolocation"],
            geolocation={"longitude": 116.397128, "latitude": 39.916527},  # 北京中心
        )

        # 屏蔽部分检测机制
        page = await context.new_page()
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        with open("cookies.json", "r", encoding="utf-8") as f:
            cookies = json.load(f)

        cookies = fix_same_site(convert_expiration_date(cookies))
        await context.add_cookies(cookies)

        await page.goto("https://item.jd.com/", wait_until="load")
        await page.wait_for_selector("input#key", timeout=30000)

        search_input = page.locator("input#key")
        for char in "5070显卡":
            await search_input.type(char)
            await asyncio.sleep(random.uniform(0.1, 0.4))
        await asyncio.sleep(random.uniform(0.4, 1.0))
        await search_input.press("Enter")

        await page.wait_for_selector(".gl-item", timeout=20000)

        # 模拟人类滑动行为
        for _ in range(random.randint(5, 8)):
            await page.mouse.wheel(0, random.randint(600, 1000))
            await asyncio.sleep(random.uniform(0.5, 1.2))

        items = await page.locator(".gl-item").all()

        for item in items:
            try:
                title = await item.locator(".p-name").inner_text()
                price = await item.locator(".p-price i").first.inner_text()
                shop = await item.locator("a.curr-shop.hd-shopname").inner_text()

                if "5070" in title and "12G" in title and "自营" in shop:
                    print(f"商品标题：{title.strip()}")
                    print(f"店铺名称：{shop.strip()}")
                    print(f"商品价格：￥{price.strip()}")
            except Exception:
                continue

        await browser.close()

asyncio.run(run())