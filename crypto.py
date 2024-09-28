import aiohttp
import asyncio
from robot.database import update_crypto_price

async def update_crypto_rates():
    url = 'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,litecoin&vs_currencies=rub'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            btc_price = data['bitcoin']['rub']
            ltc_price = data['litecoin']['rub']

            update_crypto_price('btc', btc_price)
            update_crypto_price('ltc', ltc_price)

async def periodic_crypto_update():
    while True:
        await update_crypto_rates()
        await asyncio.sleep(1600)
