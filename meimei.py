import asyncio
import discord
import requests
from discord.ext import commands, tasks
from io import BytesIO
from typing import Union, Optional
from petpetgif import petpet as petpetgif
from PIL import Image
from dotenv import load_dotenv
import os
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = commands.Bot(command_prefix="-", intents=discord.Intents.all())

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
credentials = service_account.Credentials.from_service_account_file("google api creds.json", scopes=SCOPES)
googleService = build("sheets", "v4", credentials=credentials)
SUGGESTION_CHANNEL1 = int(os.getenv("SUGGESTION_CHANNEL1"))
SUGGESTION_SHEET1 = os.getenv("SUGGESTION_SHEET1")
SUGGESTION_CHANNEL2 = int(os.getenv("SUGGESTION_CHANNEL2"))
SUGGESTION_SHEET2 = os.getenv("SUGGESTION_SHEET2")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")

async def main():
    async with bot:
        await bot.start(BOT_TOKEN)

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if message.content.lower().startswith("suggestion"):
        await logSuggestion(message)
    await bot.process_commands(message)
    
@bot.event
async def on_ready():
    print(f"I'm ready for you Onii-chan!")
    now_live.start()
async def schedule(ctx):
    await ctx.send(content="Meimei's weekly schedule!", file=discord.File("schedule.png"))

@bot.command()
async def info(ctx):
    embed2 = discord.Embed(
        color=discord.Color.from_str("#fdf4f8"),
        title="Meimei's Links!",
        description=(
            "[Pomf](https://pomf.tv/stream/meimeimei)\n"
            "[Throne](https://throne.com/meimeiva)\n"
            "[Soundgasm](https://soundgasm.net/u/meimeibear/)\n"
            "[ATF Streamer Thread](https://www.allthefallen.moe/forum/index.php?threads/new-streamer-mei-mei-reporting-for-duty.64173/)\n"
            "[Alternative Social Media](https://baraag.net/@meimeich)\n"
        )
    )
    embed2.set_thumbnail(url="https://cdn.discordapp.com/avatars/1197656323781836931/336c79e1cc8391166cb7db1d400895c9.png")
    schedule_file2 = discord.File("schedule.png", filename="schedule2.png")
    embed2.set_image(url="attachment://schedule2.png")

    await ctx.send(file=schedule_file2, embed=embed2)

def getAvatarUrl(member):
    avatar = member.guild_avatar
    if not avatar:
        avatar = member.avatar
    if not avatar:
        avatar = member.default_avatar
    return avatar

def makeSquish(image, result):
    victim = Image.open(image)

    # scale largest dimension to be 500
    w,h = victim.size
    scale = 500 / max(w,h)
    w,h = int(w*scale),int(h*scale)
    victim = victim.resize((w,h))

    # center in a blank image of the right size
    base = Image.new('RGBA',(716,716),(0,0,0,0))
    x = (716 - w) // 2
    y = (716 - h) // 2
    try: # attempt to use transparency
        temp = victim.convert('RGBA')
        base.paste(temp, (x,y), temp)
    except:
        base.paste(temp, (x,y))

    # add the template
    hand = Image.open('squish3.png')
    base.paste(hand, (0,0), hand)
    base.save(result, 'PNG')

async def getImage(ctx, image):
    result = None
    if type(image) == discord.PartialEmoji:
        result = await image.read() # retrieve the image bytes
    elif type(image) == discord.member.Member:
        avatar = getAvatarUrl(image)
        result = await avatar.read() # retrieve the image bytes
    elif ctx.message.reference:
        message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        avatar = getAvatarUrl(message.author)
        result = await avatar.read()
    elif len(ctx.message.attachments) > 0:
        result = await ctx.message.attachments[0].read()
    return result

@bot.command()
async def pet(ctx, image: Optional[Union[discord.PartialEmoji, discord.member.Member]]):
    image = await getImage(ctx, image)
    if image == None:
        await ctx.reply('Please use a custom emoji or tag a member to petpet their avatar.')
        return
    source = BytesIO(image) # file-like container to hold the emoji in memory
    dest = BytesIO() # container to store the petpet gif in memory
    petpetgif.make(source, dest)
    dest.seek(0) # set the file pointer back to the beginning so it doesn't upload a blank file.
    await ctx.send(file=discord.File(dest, filename=f"{image[0]}-petpet.gif"))

@bot.command()
async def squish(ctx, image: Optional[Union[discord.PartialEmoji, discord.member.Member]]):
    image = await getImage(ctx, image)
    if image == None:
        await ctx.reply('Please use a custom emoji or tag a member to squish their avatar.')
        return
    source = BytesIO(image) # file-like container to hold the emoji in memory
    dest = BytesIO() # container to store the petpet gif in memory
    makeSquish(source, dest)
    dest.seek(0) # set the file pointer back to the beginning so it doesn't upload a blank file.
    await ctx.send(file=discord.File(dest, filename=f"{image[0]}-squish.png"))

if __name__ == "__main__":
    asyncio.run(main())
