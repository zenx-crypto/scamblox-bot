import discord
import re
import aiohttp
import asyncio
from discord.ext import commands
from datetime import datetime
from dotenv import load_dotenv
import os

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# ====================== CONFIG ======================
CHANNEL_ID = 1500270252666388550
YOUR_NAME = "ScamBlox"
SCAN_INTERVAL = 300
# ===================================================

seen_scripts = set()

def find_webhooks(lua_code: str):
    pattern = r'https?://(?:discord(?:app)?\.com|discord\.gg)/api/webhooks/(\d+)/([a-zA-Z0-9_-]+)'
    matches = re.findall(pattern, lua_code, re.IGNORECASE)
    return [f"https://discord.com/api/webhooks/{wid}/{token}" for wid, token in matches]

async def send_logger_alert(channel, webhook_urls, script_url="unavailable"):
    timestamp = datetime.now().strftime("%I:%M %p")
    for webhook_url in webhook_urls:
        embed = discord.Embed(
            title="⚠️ Logger Detected",
            description="A script with a discord webhook has been detected.",
            color=0xff0000,
            timestamp=datetime.now()
        )
        embed.add_field(name="Webhook Urls", value=webhook_url, inline=False)
        embed.add_field(name="Script Url", value=script_url, inline=False)
        embed.add_field(name="Found By", value=f"Auto Scanner ({YOUR_NAME})", inline=False)
        embed.set_footer(text=f"Project {YOUR_NAME} | Today at {timestamp}")
        await channel.send(embed=embed)

async def fetch_latest_scripts(limit=10):
    url = f"https://scriptblox.com/api/script/fetch?limit={limit}&sort=latest"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("result", [])
    return []

async def check_script(script):
    script_id = script.get("_id") or script.get("id")
    if script_id in seen_scripts: return
    seen_scripts.add(script_id)

    script_url = f"https://scriptblox.com/script/{script.get('slug', '')}"
    
    raw_url = f"https://scriptblox.com/api/script/raw/{script_id}"
    async with aiohttp.ClientSession() as session:
        async with session.get(raw_url) as resp:
            if resp.status != 200: return
            lua_code = await resp.text()

    detected = find_webhooks(lua_code)
    if detected:
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            await send_logger_alert(channel, detected, script_url)
        print(f"🚨 Logger found!")

async def auto_scanner():
    await bot.wait_until_ready()
    while True:
        try:
            print("🔄 Scanning latest scripts...")
            scripts = await fetch_latest_scripts(15)
            for script in scripts:
                await check_script(script)
                await asyncio.sleep(1)
        except Exception as e:
            print(f"Scanner error: {e}")
        await asyncio.sleep(SCAN_INTERVAL)

@bot.event
async def on_ready():
    print(f"✅ Bot is online as {bot.user}")
    bot.loop.create_task(auto_scanner())

@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! {round(bot.latency * 1000)}ms")

if __name__ == "__main__":
    load_dotenv()
    TOKEN = os.getenv("TOKEN")
    if not TOKEN:
        print("❌ TOKEN not found in .env!")
        exit(1)
    print("✅ Token loaded from .env!")
    bot.run(TOKEN)
