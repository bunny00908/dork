import asyncio
import aiohttp
import random
import sqlite3
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from telegram.ext import ApplicationBuilder, CommandHandler
import time
import os

TOKEN = '8108454538:AAE4ZlhpoaN5Sej3M5kukwKaIIWbTr82-lY'
PROXIES = [
    "http://PP_D4F1YGPKC1-country-US:omf4xz27@evo-pro.porterproxies.com:61236",
    "http://PP_D4F1YGPKC1-country-IN:omf4xz27@evo-pro.porterproxies.com:61236"
]
GATE_KEYWORDS = [
    "shopify", "shopify pay", "stripe", "paypal", "square", "authorize.net", "klarna", "afterpay"
]
ua = UserAgent()

def init_db():
    conn = sqlite3.connect('scraped_results.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS results (query TEXT, url TEXT UNIQUE, title TEXT, gateway TEXT)''')
    conn.commit()
    conn.close()

async def fetch(session, url, proxy=None):
    headers = {'User-Agent': ua.random}
    try:
        async with session.get(url, headers=headers, proxy=proxy, timeout=15) as response:
            return await response.text()
    except Exception as e:
        print(f"Fetch error: {e}")
        return None

async def duckduckgo_search(query, max_results=100):
    results, page = set(), 0
    async with aiohttp.ClientSession() as session:
        while len(results) < max_results:
            search_url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}&s={page * 50}"
            proxy = random.choice(PROXIES)
            html = await fetch(session, search_url, proxy)
            if not html:
                break
            soup = BeautifulSoup(html, 'html.parser')
            new_links = [a['href'] for a in soup.select('.result__url') if a.get('href')]
            if not new_links:
                break
            results.update(new_links)
            page += 1
            await asyncio.sleep(random.uniform(1, 2))
    return list(results)

async def bing_search(query, max_results=100):
    results, page = set(), 0
    async with aiohttp.ClientSession() as session:
        while len(results) < max_results:
            search_url = f"https://www.bing.com/search?q={query.replace(' ', '+')}&first={page*10+1}"
            proxy = random.choice(PROXIES)
            html = await fetch(session, search_url, proxy)
            if not html:
                break
            soup = BeautifulSoup(html, 'html.parser')
            links = [a['href'] for a in soup.select('li.b_algo h2 a') if a.get('href')]
            if not links:
                break
            results.update(links)
            page += 1
            await asyncio.sleep(random.uniform(1, 2))
    return list(results)

def detect_gateway(html):
    html_lower = html.lower()
    # Priority: Shopify!
    if "shopify" in html_lower or "shopify pay" in html_lower:
        return "shopify"
    for gw in GATE_KEYWORDS:
        if gw in html_lower:
            return gw
    return "Unknown"

async def extract_info(url, session):
    html = await fetch(session, url, proxy=random.choice(PROXIES))
    if not html:
        return None
    soup = BeautifulSoup(html, 'html.parser')
    title = soup.title.string.strip() if soup.title else 'No Title'
    gateway = detect_gateway(html)
    return {'url': url, 'title': title, 'gateway': gateway}

async def save_to_db(query, results):
    conn = sqlite3.connect('scraped_results.db')
    cursor = conn.cursor()
    for r in results:
        try:
            cursor.execute("INSERT OR IGNORE INTO results (query, url, title, gateway) VALUES (?, ?, ?, ?)",
                           (query, r['url'], r['title'], r['gateway']))
        except Exception as e:
            print(f"DB Error: {e}")
    conn.commit()
    conn.close()

async def start(update, context):
    await update.message.reply_text("🤖 Send your query using /dork <query>")

async def handle_dork(update, context):
    if context.args:
        query = ' '.join(context.args)
        msg = await update.message.reply_text(f"🔍 Searching DuckDuckGo & Bing for: {query}")

        ddg_urls = await duckduckgo_search(query, max_results=100)
        bing_urls = await bing_search(query, max_results=100)
        all_urls = list(set(ddg_urls + bing_urls))

        await msg.edit_text(f"🔍 Found {len(all_urls)} URLs. Analyzing...")

        async with aiohttp.ClientSession(headers={'User-Agent': ua.random}) as session:
            tasks = [extract_info(url, session) for url in all_urls]
            results = await asyncio.gather(*tasks)

        clean_results = [r for r in results if r]
        await save_to_db(query, clean_results)

        # Only send text file, not individual messages!
        filename = f'dork_results_{int(time.time())}.txt'
        with open(filename, 'w', encoding='utf-8') as f:
            for item in clean_results:
                f.write(f"{item['url']}\n{item['title']}\n{item['gateway']}\n---\n")
        with open(filename, 'rb') as f:
            await update.message.reply_document(document=f, filename=filename)
        os.remove(filename)

        await msg.edit_text(f"✅ Completed scanning for: {query} ({len(clean_results)} results in file)")
    else:
        await update.message.reply_text("❗ Use the command like: /dork intext:\"shopify\" inurl:\"donation\"")

if __name__ == '__main__':
    init_db()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('dork', handle_dork))
    print('🔧 Advanced Dork Scanner Bot running...')
    app.run_polling()
