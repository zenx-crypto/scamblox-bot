import discord  
import re  
import aiohttp  
import asyncio  
from discord.ext import commands  
from datetime import datetime  
  
intents = discord.Intents.default()  
intents.message_content = True  
  
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)  
  
# ====================== CONFIG ======================  
CHANNEL_ID = 1500270252666388550   # ← YOUR ALERT CHANNEL ID  
YOUR_NAME = "ScamBlox"            # Change as needed  
SCAN_INTERVAL = 300               # Seconds (5 minutes recommended)  
# ===================================================  
  
seen_scripts = set()  # To avoid duplicate alerts  
  
def find_webhooks(lua_code: str):  
    pattern = r'https?://(?:discord(?:app)?\.com|discord\.gg)/api/webhooks/(\d+)/([a-zA-Z0-9_-]+)'  
    matches = re.findall(pattern, lua_code, re.IGNORECASE)  
    return [f"https://discord.com/api/webhooks/{wid}/{token}" for wid, token in matches]  
  
async def fetch_latest_scripts(limit=10):  
    """Fetch newest scripts from ScriptBlox"""  
    url = f"https://scriptblox.com/api/script/fetch?limit={limit}&sort=latest"  
    async with aiohttp.ClientSession() as session:  
        async with session.get(url) as resp:  
            if resp.status == 200:  
                data = await resp.json()  
                return data.get("result", [])  
    return []  
  
async def check_script(script):  
    script_id = script.get("_id") or script.get("id")  
    if script_id in seen_scripts:  
        return  
    seen_scripts.add(script_id)  
  
    title = script.get("title", "Unknown")  
    script_url = f"https://scriptblox.com/script/{script.get('slug', '')}"  
      
    # Get raw script code  
    raw_url = f"https://scriptblox.com/api/script/raw/{script_id}"  
    async with aiohttp.ClientSession() as session:  
        async with session.get(raw_url) as resp:  
            if resp.status != 200:  
                return  
            lua_code = await resp.text()  
  
    detected = find_webhooks(lua_code)  
      
    if detected:  
        channel = bot.get_channel(CHANNEL_ID)  
        if channel:  
            timestamp = datetime.now().strftime("%I:%M %p")  
            for webhook_url in detected[:3]:  # Limit to 3 per script  
                embed = discord.Embed(  
                    title="⚠️ Logger Detected",  
                    description="A script with a discord webhook has been detected.",  
                    color=0xff0000,  
                    timestamp=datetime.now()  
                )  
                embed.add_field(name="Webhook Urls", value=webhook_url, inline=False)  
                embed.add_field(name="Script Url", value=script_url, inline=False)  
                embed.add_field(name="Found By", value=f"Auto Scanner (@{YOUR_NAME})", inline=False)  
                embed.set_footer(text=f"Project {YOUR_NAME} | Today at {timestamp}")  
                  
                await channel.send(embed=embed)  
          
        print(f"🚨 Logger found in: {title}")  
  
@bot.event  
async def on_ready():  
    print(f"✅ Bot is online as {bot.user}")  
    print("Starting auto scanner...")  
    bot.loop.create_task(auto_scanner())  
  
async def auto_scanner():  
    await bot.wait_until_ready()  
    while True:  
        try:  
            print("🔄 Scanning latest scripts...")  
            scripts = await fetch_latest_scripts(limit=15)  
              
            for script in scripts:  
                await check_script(script)  
                await asyncio.sleep(1)  # Be gentle with API  
                  
        except Exception as e:  
            print(f"Error in scanner: {e}")  
          
        await asyncio.sleep(SCAN_INTERVAL)  
  
# Manual scan command (kept from before)  
@bot.command(name="scan")  
async def manual_scan(ctx, *, code_or_link: str = None):  
    if not code_or_link:  
        await ctx.send("Usage: `!scan <code or pastebin>`")  
        return  
    # ... (same as previous version)  
    await ctx.send("Manual scan feature works the same as before.")  
  
@bot.command()  
async def ping(ctx):  
    await ctx.send(f"Pong! {round(bot.latency * 1000)}ms")  
  
# ====================== RUN ======================  
if __name__ == "__main__":  
    TOKEN = "MTQ5OTYyODY3NzEyMDUyNDM0OA.GlGJA_.hYCIhf_V6K8X957ocBIEfg3GqqINjN6bFCZkwI"  
    bot.run(TOKEN)  
