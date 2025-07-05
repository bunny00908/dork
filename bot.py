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
            await asyncio.sleep(random.uniform(0.5, 1.2))
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
            await asyncio.sleep(random.uniform(0.5, 1.2))
    return list(results)

async def yahoo_search(query, max_results=100):
    results, page = set(), 0
    async with aiohttp.ClientSession() as session:
        while len(results) < max_results:
            start = page * 10 + 1
            search_url = f"https://search.yahoo.com/search?p={query.replace(' ', '+')}&b={start}"
            proxy = random.choice(PROXIES)
            html = await fetch(session, search_url, proxy)
            if not html:
                break
            soup = BeautifulSoup(html, 'html.parser')
            links = [a['href'] for a in soup.select('div#web h3.title a') if a.get('href')]
            if not links:
                break
            results.update(links)
            page += 1
            await asyncio.sleep(random.uniform(0.5, 1.2))
    return list(results)

async def mojeek_search(query, max_results=100):
    results, page = set(), 0
    async with aiohttp.ClientSession() as session:
        while len(results) < max_results:
            search_url = f"https://www.mojeek.com/search?q={query.replace(' ', '+')}&s={page*10}"
            proxy = random.choice(PROXIES)
            html = await fetch(session, search_url, proxy)
            if not html:
                break
            soup = BeautifulSoup(html, 'html.parser')
            links = [a['href'] for a in soup.select('ol.results li div.result > h2 > a') if a.get('href')]
            if not links:
                break
            results.update(links)
            page += 1
            await asyncio.sleep(random.uniform(0.5, 1.2))
    return list(results)

async def filter_by_gateway(urls, gateway_keyword):
    # FAST: fetch all URLs concurrently and filter on content
    filtered = []
    semaphore = asyncio.Semaphore(20)  # avoid overloading proxies

    async def check_url(url):
        async with semaphore:
            async with aiohttp.ClientSession(headers={'User-Agent': ua.random}) as session:
                html = await fetch(session, url, proxy=random.choice(PROXIES))
                if html and gateway_keyword.lower() in html.lower():
                    filtered.append(url)

    await asyncio.gather(*(check_url(url) for url in urls))
    return filtered

async def start(update, context):
    await update.message.reply_text(
        "🤖 Use /dork <keyword> for all URLs (e.g. /dork t-shirt)\n"
        "or /dork <keyword> gateway <word> to filter by a payment system or brand (e.g. /dork t-shirt gateway shopify)"
    )

async def handle_dork(update, context):
    if context.args:
        args = context.args
        # Parse "gateway" logic
        if "gateway" in args:
            gateway_index = args.index("gateway")
            search_terms = args[:gateway_index]
            filter_gateway = ' '.join(args[gateway_index+1:]).lower()
        else:
            search_terms = args
            filter_gateway = None

        query = ' '.join(search_terms)
        msg = await update.message.reply_text(f"🔍 Searching all engines for: {query}")

        # Start all scraping tasks at once (concurrent for speed!)
        ddg_task = duckduckgo_search(query, max_results=100)
        bing_task = bing_search(query, max_results=100)
        yahoo_task = yahoo_search(query, max_results=100)
        mojeek_task = mojeek_search(query, max_results=100)
        results = await asyncio.gather(ddg_task, bing_task, yahoo_task, mojeek_task)
        all_urls = set()
        for engine_urls in results:
            all_urls.update(engine_urls)
        all_urls = list(all_urls)
        await msg.edit_text(f"🔍 Found {len(all_urls)} URLs. {'Filtering by gateway...' if filter_gateway else 'Sending file...'}")

        if filter_gateway:
            all_urls = await filter_by_gateway(all_urls, filter_gateway)

        filename = f'dork_results_{int(time.time())}.txt'
        with open(filename, 'w', encoding='utf-8') as f:
            for url in all_urls:
                f.write(url + '\n')
        with open(filename, 'rb') as f:
            await update.message.reply_document(document=f, filename=filename)
        os.remove(filename)

        await msg.edit_text(f"✅ Completed search for: {query} "
                            f"{'(filtered for gateway: '+filter_gateway+')' if filter_gateway else ''} "
                            f"({len(all_urls)} results in file)")
    else:
        await update.message.reply_text("❗ Use the command like: /dork t-shirt or /dork t-shirt gateway shopify")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('dork', handle_dork))
    print('🔧 Super Dork Scanner Bot running...')
    app.run_polling()
