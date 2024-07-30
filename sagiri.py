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
import urllib.parse
import re as regex

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

THRONE_USERNAME = os.getenv("THRONE_USERNAME")
THRONE_CHANNEL = int(os.getenv("THRONE_CHANNEL"))

ANNOUNCEMENT_CHANNEL = 1250333968935555202
MEIMEI_UID = 1197656323781836931

async def main():
    async with bot:
        await bot.start(BOT_TOKEN)

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if message.channel.id == ANNOUNCEMENT_CHANNEL and message.author.id == 1197656323781836931 and "schedule" in message.content.lower():
        await message.attachments[0].save(fp="assets/schedule.png")
    if message.content.lower().startswith("suggestion"):
        await logSuggestion(message)
    await bot.process_commands(message)
    
@bot.event
async def on_ready():
    print(f"I'm ready for you Onii-chan!")
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, custom_throne_integration.watchThrone, THRONE_USERNAME, onThroneContribution, onThroneGift, onThroneWishlistUpdate)

@bot.event
async def on_member_join(member):
    if datetime.datetime.now(datetime.timezone.utc) - member.created_at < datetime.timedelta(days=30):
        print("in here")
        gatekeep_role = member.guild.get_role(1246240396074422333)
        await member.add_roles(gatekeep_role)
        return

@bot.command()
async def matrix(ctx):
    embed = discord.Embed(
        title = "How do I join the matrix?",
        color = discord.Color.from_str("#fdf4f8")
    )
    embed.add_field(name = "Step 1", value = "Talk in the Discord until you have 150 messages.", inline=False)
    embed.add_field(name = "Step 2", value = "Make a cutefunny.art account if you haven't already. Feel free to ask a mod if you encounter any issues with this step.\nhttps://cutefunny.art/posts/matrixstart/", inline=False)
    embed.add_field(name = "Step 3", value = "DM your matrix username to a <@&1225328554624024667> and ask for an invite!", inline=False)
    await ctx.send(embed = embed)

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
            "[Matrix](https://discord.com/channels/1225136839006879874/1225136839006879877/1257765920454217791)\n"
            "[VTuber Wiki](https://virtualyoutuber.fandom.com/wiki/Mei-Mei)"
            "[ATF Streamer Thread](https://www.allthefallen.moe/forum/index.php?threads/new-streamer-mei-mei-reporting-for-duty.64173/)\n"
            "[VOD Archive](https://gofile.io/d/H11r46)\n"
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

@bot.command(aliases=["pat"])
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

class Button(discord.ui.View):
    def __init__(self, url, label):
        super().__init__()
        self.add_item(discord.ui.Button(label=label, url=url))

def onThroneGift(gift):
    print("GIFT")
    print(gift)
    channel = bot.get_channel(THRONE_CHANNEL)
    messageTitle = "New gift on Throne"
    crowd = gift["isCrowdfunded"]
    if crowd:
        messageTitle = "Item fully funded"
    price = f'${round(gift["price"]//100)}.{round(gift["price"]%100):02d} {gift["currency"]}'
    if crowd:
        price = "a total of " + price
    gifters = gift["customizations"]["customers"]
    gifterNames = ""
    customMessage = ""
    for gifter in gifters:
        if gifter.get("customerUsername") and len(gifter.get("customerUsername")) > 0:
            if len(gifterNames) > 0:
                gifterNames += ", "
            gifterNames += gifter["customerUsername"]
        if gifter.get("customerMessage") and len(gifter.get("customerMessage")) > 0:
            if crowd:
                username = "Anon"
                if gifter.get("customerUsername") and len(gifter.get("customerUsername")) > 0:
                    username = gifter.get("customerUsername")
                customMessage += f'{username}: "{gifter["customerMessage"]}"\n'
            else:
                customMessage += f'"{gifter["customerMessage"]}"\n'
    embed = discord.Embed(
        title=messageTitle,
        description=(
            (f'**{gifterNames}** ' if len(gifterNames) > 0 else "**Anon** ") + f'gifted *{gift["name"]}* for {price}!\n' +
            (f"{customMessage}\n" if len(customMessage) > 0 else "\n") +
            "Thank you so much for your cumtribution, mister!\n"
        ),
        color=discord.Color.from_str("#fdf4f8")
    )
    if gift.get("imageSrc"):
        parsed = urllib.parse.urlparse(gift["imageSrc"])
        if (len(parsed.scheme) > 0 and len(parsed.netloc) > 0):
            embed.set_image(url=gift["imageSrc"])
    bot.loop.create_task(channel.send(embed=embed))

def onThroneContribution(dono):
    print("CONTRIBUTION")
    print(dono)
    channel = bot.get_channel(THRONE_CHANNEL)
    funding = 0
    fundingBar = ""
    customMessage = dono.get("message") if dono.get("message") else ""
    messageTitle = "Contribution to a gift"
    verb = "contributed to"
    if dono.get("formattedContributionAmount") and len(dono["formattedContributionAmount"]) > 0:
        verb = f'contributed {dono["formattedContributionAmount"]} to'
    itemId = ""
    # the donation alert doesn't have the item id, but if there's an image the id is usually in the url
    if dono.get("itemImage"):
        m = regex.search("[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", dono["itemImage"])
        if m:
            itemId = m.group(0)
    item = custom_throne_integration.fetchItem(THRONE_USERNAME, dono["itemName"], itemId)
##    if item:
##        funding = item["fundingPercentage"]
##        fundingBar = "`|" + "█" * int(funding/2.5) + "-" * (40-int(funding/2.5)) + "|`"
    name = dono["itemName"]
    if item and item.get("name") and len(item["name"]) > 0:
        name = item["name"]
    embed = discord.Embed(
        title=messageTitle,
        description=(
            (f'**{dono["gifterUsername"]}** ' if len(dono["gifterUsername"]) > 0 else "**Anon**") + f'{verb} *{name}*!\n' +
            (f"{fundingBar} {funding}%\n" if len(fundingBar) > 0 else "") +
            (f"\"{customMessage}\"\n\n" if len(customMessage) > 0 else "\n") +
            "Thank you so much for your cumtribution, mister!\n"
        ),
        color=discord.Color.from_str("#fdf4f8")
    )
    if dono.get("itemImage"):
        parsed = urllib.parse.urlparse(dono["itemImage"])
        if (len(parsed.scheme) > 0 and len(parsed.netloc) > 0):
            embed.set_image(url=dono["itemImage"])
    bot.loop.create_task(channel.send(embed=embed))

def onThroneWishlistUpdate(item):
    #print(item)
    channel = bot.get_channel(THRONE_CHANNEL)
    customMessage = item.get("description") if item.get("description") else ""
    itemUrl = f'https://throne.com/{THRONE_USERNAME}/item/{item["id"]}'
    embed = discord.Embed(
        url=itemUrl,
        title="New item added on Throne!",
        description=(
            f'**{item["name"]} | ${round(item["price"]//100)}.{round(item["price"]%100):02d} {item["currency"]}**\n' +
            (f"\"{customMessage}\"\n" if len(customMessage) > 0 else "")
        ),
        color=discord.Color.from_str("#fdf4f8")
    )
    if item.get("imgLink"):
        parsed = urllib.parse.urlparse(item["imgLink"])
        if (len(parsed.scheme) > 0 and len(parsed.netloc) > 0):
            embed.set_image(url=item["imgLink"])
    bot.loop.create_task(sendEmbedWithButton(channel, embed, "View on Throne", itemUrl))

async def sendEmbedWithButton(channel, embed, buttonLabel, buttonUrl):
    await channel.send(embed=embed, view=Button(label=buttonLabel, url=buttonUrl))

if __name__ == "__main__":
    asyncio.run(main())
