import asyncio
import aiohttp
import random
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from telegram.ext import ApplicationBuilder, CommandHandler
import time
import os

TOKEN = '8108454538:AAE4ZlhpoaN5Sej3M5kukwKaIIWbTr82-lY'
PROXIES = [
    "http://PP_D4F1YGPKC1-country-UK:omf4xz27@evo-pro.porterproxies.com:61236",
    "http://PP_D4F1YGPKC1-country-SG:omf4xz27@evo-pro.porterproxies.com:61236",
    "http://PP_D4F1YGPKC1-country-TH:omf4xz27@evo-pro.porterproxies.com:61236",
    "http://PP_D4F1YGPKC1-country-PH:omf4xz27@evo-pro.porterproxies.com:61236",
    "http://PP_D4F1YGPKC1-country-MY:omf4xz27@evo-pro.porterproxies.com:61236",
    "http://PP_D4F1YGPKC1-country-MX:omf4xz27@evo-pro.porterproxies.com:61236",
    "http://PP_D4F1YGPKC1-country-JP:omf4xz27@evo-pro.porterproxies.com:61236",
    "http://PP_D4F1YGPKC1-country-EU:omf4xz27@evo-pro.porterproxies.com:61236",
]
ua = UserAgent()

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
            dork = f'inurl:myshopify {query}'
            search_url = f"https://html.duckduckgo.com/html/?q={dork.replace(' ', '+')}&s={page * 50}"
            proxy = random.choice(PROXIES)
            html = await fetch(session, search_url, proxy)
            if not html: break
            soup = BeautifulSoup(html, 'html.parser')
            links = [a['href'] for a in soup.select('.result__url') if a.get('href')]
            if not links: break
            results.update(links)
            page += 1
            await asyncio.sleep(random.uniform(0.5, 1.2))
    return list(results)

async def bing_search(query, max_results=100):
    results, page = set(), 0
    async with aiohttp.ClientSession() as session:
        while len(results) < max_results:
            dork = f'inurl:myshopify {query}'
            search_url = f"https://www.bing.com/search?q={dork.replace(' ', '+')}&first={page*10+1}"
            proxy = random.choice(PROXIES)
            html = await fetch(session, search_url, proxy)
            if not html: break
            soup = BeautifulSoup(html, 'html.parser')
            links = [a['href'] for a in soup.select('li.b_algo h2 a') if a.get('href')]
            if not links: break
            results.update(links)
            page += 1
            await asyncio.sleep(random.uniform(0.5, 1.2))
    return list(results)

def is_shopify_site(url, html):
    return "myshopify.com" in url.lower() or (html and "shopify" in html.lower())

def has_shop_pay(html):
    return html and ("shop pay" in html.lower() or "shoppay" in html.lower())

async def filter_by_shopify_and_shoppay(urls, keywords):
    matched = []
    sem = asyncio.Semaphore(25)
    keywords = [k.lower() for k in keywords]

    async def check_url(url):
        async with sem:
            async with aiohttp.ClientSession(headers={'User-Agent': ua.random}) as session:
                html = await fetch(session, url, proxy=random.choice(PROXIES))
                if not html: return
                if not is_shopify_site(url, html): return
                if not has_shop_pay(html): return
                if not all(k in html.lower() for k in keywords): return
                matched.append(url.strip())
    await asyncio.gather(*(check_url(url) for url in urls))
    return matched

async def start(update, context):
    await update.message.reply_text(
        "🤖 /dork <keyword(s)> — finds Shopify sites with Shop Pay. Example: /dork t-shirt"
    )

async def handle_dork(update, context):
    if context.args:
        keywords = context.args
        query = ' '.join(keywords)
        msg = await update.message.reply_text(f"🔍 Searching Shopify for: {query} + Shop Pay")

        # Get results from DuckDuckGo and Bing
        tasks = [
            duckduckgo_search(query, 120),
            bing_search(query, 120),
        ]
        results = await asyncio.gather(*tasks)
        all_urls = set()
        for res in results:
            all_urls.update(res)
        all_urls = list(all_urls)
        await msg.edit_text(f"🌐 Found {len(all_urls)} Shopify candidate URLs, checking Shop Pay...")

        filtered_urls = await filter_by_shopify_and_shoppay(all_urls, keywords)

        filename = f'shopify_shoppay_{int(time.time())}.txt'
        with open(filename, 'w', encoding='utf-8') as f:
            for url in filtered_urls:
                f.write(url + '\n')
        with open(filename, 'rb') as f:
            await update.message.reply_document(document=f, filename=filename)
        os.remove(filename)

        await msg.edit_text(f"✅ Done! {len(filtered_urls)} Shopify + Shop Pay sites found.")
    else:
        await update.message.reply_text("❗ Use the command like: /dork t-shirt")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('dork', handle_dork))
    print('🛒 Shopify+ShopPay Finder Bot running...')
    app.run_polling()
