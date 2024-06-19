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
import datetime
import custom_throne_integration

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

THRONE_ID = os.getenv("THRONE_ID")
THRONE_CHANNEL = int(os.getenv("THRONE_CHANNEL"))

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
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, custom_throne_integration.watchThrone, THRONE_ID, onThroneUpdate)

@bot.event
async def on_member_join(member):
    if datetime.datetime.now(datetime.timezone.utc) - member.created_at < datetime.timedelta(days=30):
        print("in here")
        gatekeep_role = member.guild.get_role(1246240396074422333)
        await member.add_roles(gatekeep_role)
        return

@bot.command()
async def schedule(ctx):
    await ctx.send(content="Meimei's weekly schedule!", file=discord.File("assets/schedule.png"))

@bot.command()
async def info(ctx):
    embed = discord.Embed(
        color=discord.Color.from_str("#fdf4f8"),
        title="Meimei's Links!",
        description=(
            "[Pomf](https://pomf.tv/stream/meimeimei)\n"
            "[Throne](https://throne.com/meimeiva)\n"
            "[Soundgasm](https://soundgasm.net/u/meimeibear/)\n"
            "[Twitter](https://twitter.com/meimeitwt)\n"
            "[ATF Streamer Thread](https://www.allthefallen.moe/forum/index.php?threads/new-streamer-mei-mei-reporting-for-duty.64173/)\n"
            "[Alternative Social Media](https://baraag.net/@meimeich)\n"
        )
    )
    embed.set_thumbnail(url="https://cdn.discordapp.com/avatars/1197656323781836931/336c79e1cc8391166cb7db1d400895c9.png")
    schedule_file = discord.File("assets/schedule.png", filename="schedule.png")
    embed.set_image(url="attachment://schedule.png")

    await ctx.send(file=schedule_file, embed=embed)

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
    hand = Image.open('assets/squish3.png')
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

@commands.is_owner()
@bot.command()
async def update_schedule(ctx):
    if ctx.author.id != 623396579960946690:
        return
    await ctx.message.attachments[0].save(fp="assets/schedule.png")
    await ctx.send("schedule updated")

@bot.event
async def on_command_error(ctx, e):
    print(e)

@bot.event
async def on_error(e):
    print(e)

async def logSuggestion(message):
    sheet = ""
    if message.channel.id == SUGGESTION_CHANNEL1:
        sheet = SUGGESTION_SHEET1
    elif message.channel.id == SUGGESTION_CHANNEL2:
        sheet = SUGGESTION_SHEET2
    else:
        return
    
    text = message.content
    for a in message.attachments:
        text += a.url
    result = googleService.spreadsheets().values().append(
        range=sheet + "!A1", spreadsheetId=SPREADSHEET_ID, valueInputOption="RAW", body={"values":[[text, message.jump_url]]}
    ).execute()
    if result['updates']['updatedCells'] > 0:
        await message.add_reaction("👍")
        await message.add_reaction("👎")
        reply = await message.reply("Thank you for the suggestion mister!")
    await asyncio.sleep(5)
    await reply.delete()

def onThroneUpdate(dono):
    print(dono)
    channel = bot.get_channel(THRONE_CHANNEL)
    alertType = dono["type"]
    messageTitle = ""
    verb = ""
    customMessage = dono.get("message") if dono.get("message") else ""
    if alertType == "item-purchased-stream-alert":
        messageTitle = "New gift on Throne"
        verb = "gifted"
    elif alertType == "crowdfunding-contribution-stream-alert":
        messageTitle = "Contribution to a gift"
        verb = "contributed to"
    elif alertType == "item-fully-funded-stream-alert":
        messageTitle = "Item fully funded"
        verb = "funded"
    else:
        return
    embed = discord.Embed(
        title=messageTitle,
        description=(
            f'{dono["gifterUsername"]} {verb} {dono["itemName"]}!\n' +
            (f"They said: \"{customMessage}\"\n\n" if len(customMessage) > 0 else "") +
            "Thanks mister~ Your findom daughter-wife loves all her pay piggies!\n"
        )
    )
    embed.set_image(url=dono["itemImage"])
    bot.loop.create_task(channel.send(embed=embed))

if __name__ == "__main__":
    asyncio.run(main())
