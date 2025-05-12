import asyncio
import json
import random
import logging
from typing import List
from playwright.async_api import async_playwright
import aiomysql
from datetime import datetime

# 配置日志，输出到 log.txt 文件
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("log.txt", encoding="utf-8"),  # 将日志输出到 log.txt
        logging.StreamHandler()  # 同时在终端打印日志
    ]
)

# 处理 cookie 的过期时间和 SameSite
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

# 创建数据库连接池
async def create_db_pool():
    return await aiomysql.create_pool(
        host='localhost',
        user='user',
        password='yourpassword',  # 修改为你的数据库密码
        db='jd_spider',
        charset='utf8mb4',
        autocommit=True
    )

# 插入商品数据（批量插入）
async def insert_batch_to_db(pool, products):
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            try:
                await cursor.executemany(
                    "INSERT INTO jd_products (title, price, shop, date) VALUES (%s, %s, %s, %s)",
                    products
                )
                logging.info(f"成功插入 {len(products)} 条商品数据")
            except Exception as e:
                logging.error(f"插入商品数据失败: {e}")
                raise

# 安全的页面加载函数，带重试机制
async def safe_navigate(page, url, retries=3, delay=2):
    for _ in range(retries):
        try:
            await page.goto(url)
            return
        except Exception as e:
            logging.warning(f"尝试访问 {url} 时出错：{e}")
            await asyncio.sleep(delay)
    raise Exception(f"无法访问 {url}，请检查网络连接或页面状态")

# 搜索京东商品
async def search_jd(pool, keyword: str, include_keywords: List[str], must_include_shop: str = None):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, slow_mo=random.randint(80, 150))
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

        await safe_navigate(page, "https://item.jd.com/", retries=3)

        await page.wait_for_selector("input#key", timeout=30000)

        search_input = page.locator("input#key")
        for char in keyword:
            await search_input.type(char)
            await asyncio.sleep(random.uniform(0.1, 0.3))
        await asyncio.sleep(random.uniform(0.3, 0.7))
        await search_input.press("Enter")

        await page.wait_for_selector(".gl-item", timeout=20000)

        products = []
        for _ in range(random.randint(5, 8)):
            await page.mouse.wheel(0, random.randint(600, 1000))
            await asyncio.sleep(random.uniform(0.5, 1.0))

        items = await page.locator(".gl-item").all()

        logging.info(f"\n🔍 关键词：{keyword}")
        logging.info(f"筛选条件：标题包含 {include_keywords}" + (f"，店铺包含『{must_include_shop}』" if must_include_shop else ""))
        logging.info("————————————————————————")

        found = False
        for item in items:
            try:
                title = await item.locator(".p-name").inner_text()
                price = await item.locator(".p-price i").first.inner_text()
                shop = await item.locator("a.curr-shop.hd-shopname").inner_text()

                if all(k in title for k in include_keywords) and (must_include_shop in shop if must_include_shop else True):
                    found = True
                    current_date = datetime.now().strftime("%Y-%m-%d")
                    products.append((title.strip(), price.strip(), shop.strip(), current_date))
                    logging.info(f"✅ 商品标题：{title.strip()}")
                    logging.info(f"🏬 店铺名称：{shop.strip()}")
                    logging.info(f"💰 商品价格：￥{price.strip()}")
                    logging.info("——————")
            except Exception as e:
                logging.error(f"处理商品时出错：{e}")
                continue

        if not found:
            logging.info("❌ 未找到符合条件的商品")

        # 批量插入商品数据
        if products:
            await insert_batch_to_db(pool, products)

        await browser.close()

# 主函数，执行所有任务
async def main():
    pool = await create_db_pool()

    tasks = [
        ("5070ti显卡", ["5070", "16G"], "自营"),
        ("5070显卡", ["5070", "12G"], "自营"),
        ("4060TI显卡", ["4060", "16G"], "自营"),
        ("9070XT显卡", ["9070", "16G"], "自营"),
    ]
    
    # 执行任务
    for keyword, conditions, *shop in tasks:
        try:
            await search_jd(pool, keyword, conditions, shop[0] if shop else None)
        except Exception as e:
            logging.error(f"任务 {keyword} 执行失败: {e}")

    pool.close()
    await pool.wait_closed()

# 执行主函数
asyncio.run(main())
