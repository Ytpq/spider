import asyncio
import json
import random
from typing import List
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

async def search_jd(keyword: str, include_keywords: List[str], must_include_shop: str = None):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=random.randint(80, 150))
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)...",
            locale="zh-CN",
            viewport={"width": 1280, "height": 1024},
            timezone_id="Asia/Shanghai",
            java_script_enabled=True,
            bypass_csp=True,
            permissions=["geolocation"],
            geolocation={"longitude": 116.397128, "latitude": 39.916527},
        )

        page = await context.new_page()
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        with open("cookies.json", "r", encoding="utf-8") as f:
            cookies = json.load(f)
        cookies = fix_same_site(convert_expiration_date(cookies))
        await context.add_cookies(cookies)

        await page.goto("https://item.jd.com/", wait_until="load")
        await page.wait_for_selector("input#key", timeout=30000)

        search_input = page.locator("input#key")
        for char in keyword:
            await search_input.type(char)
            await asyncio.sleep(random.uniform(0.1, 0.3))
        await asyncio.sleep(random.uniform(0.3, 0.7))
        await search_input.press("Enter")

        await page.wait_for_selector(".gl-item", timeout=20000)

        for _ in range(random.randint(5, 8)):
            await page.mouse.wheel(0, random.randint(600, 1000))
            await asyncio.sleep(random.uniform(0.5, 1.0))

        items = await page.locator(".gl-item").all()

        print(f"\n🔍 关键词：{keyword}")
        print(f"筛选条件：标题包含 {include_keywords}" + (f"，店铺包含『{must_include_shop}』" if must_include_shop else ""))
        print("————————————————————————")

        found = False
        for item in items:
            try:
                title = await item.locator(".p-name").inner_text()
                price = await item.locator(".p-price i").first.inner_text()
                shop = await item.locator("a.curr-shop.hd-shopname").inner_text()

                if all(k in title for k in include_keywords) and (must_include_shop in shop if must_include_shop else True):
                    found = True
                    print(f"✅ 商品标题：{title.strip()}")
                    print(f"🏬 店铺名称：{shop.strip()}")
                    print(f"💰 商品价格：￥{price.strip()}")
                    print("——————")
            except Exception:
                continue

        if not found:
            print("❌ 未找到符合条件的商品")

        await browser.close()


async def main():
    tasks = [
        ("5070ti显卡", ["5070", "16G"], "自营"),
        ("Ryzen 7600", ["Ryzen", "7600", "盒装"], "自营"),
        ("DDR5 6000", ["DDR5", "6000"], "自营"),
    ]
    for keyword, conditions, *shop in tasks:
        await search_jd(keyword, conditions, shop[0] if shop else None)

asyncio.run(main())
