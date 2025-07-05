import asyncio
import aiohttp
import random
import sqlite3
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

TOKEN = '8108454538:AAE4ZlhpoaN5Sej3M5kukwKaIIWbTr82-lY'
PROXIES = [
    "http://PP_D4F1YGPKC1-country-US:omf4xz27@evo-pro.porterproxies.com:61236",
    "http://PP_D4F1YGPKC1-country-IN:omf4xz27@evo-pro.porterproxies.com:61236"
]
GATE_KEYWORDS = ["stripe", "paypal", "square", "authorize.net", "shopify pay", "klarna", "afterpay"]

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
    except:
        return None

async def duckduckgo_search(query, max_results=50):
    results, page = set(), 0
    connector = aiohttp.TCPConnector(limit=10)
    async with aiohttp.ClientSession(connector=connector) as session:
        while len(results) < max_results:
            search_url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}&s={page * 50}"
            proxy = random.choice(PROXIES)
            try:
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
            except Exception as e:
                print(f"Search Error: {e}")
                await asyncio.sleep(3)
    return list(results)

async def extract_info(url, session):
    html = await fetch(session, url, proxy=random.choice(PROXIES))
    if not html:
        return None
    soup = BeautifulSoup(html, 'html.parser')
    title = soup.title.string.strip() if soup.title else 'No Title'
    gateway = next((g for g in GATE_KEYWORDS if g in html.lower()), 'Unknown')
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
        msg = await update.message.reply_text(f"🔍 Searching for: {query}")

        urls = await duckduckgo_search(query)
        await msg.edit_text(f"🔍 Found {len(urls)} URLs. Analyzing...")

        async with aiohttp.ClientSession(headers={'User-Agent': ua.random}) as session:
            tasks = [extract_info(url, session) for url in urls]
            results = await asyncio.gather(*tasks)

        clean_results = [r for r in results if r]
        await save_to_db(query, clean_results)

        for item in clean_results[:10]:  # limit to 10 to avoid spam
            text = f"🔗 {item['url']}\n📛 {item['title']}\n💳 Gateway: {item['gateway']}"
            await update.message.reply_text(text, reply_to_message_id=update.message.message_id)

        await msg.edit_text(f"✅ Completed scanning for: {query}")
    else:
        await update.message.reply_text("❗ Use the command like: /dork intext:\"shopify\" inurl:\"donation\"")

if __name__ == '__main__':
    init_db()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('dork', handle_dork))
    print('🔧 Advanced Dork Scanner Bot running...')
    app.run_polling()
