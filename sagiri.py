import asyncio
import discord
import requests
from requests_toolbelt import MultipartEncoder
from discord.ext import commands, tasks
from io import BytesIO
from typing import Union, Optional
from petpetgif import petpet as petpetgif
from PIL import Image, ImageDraw
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
AUDIT_CHANNEL = int(os.getenv("AUDIT_CHANNEL"))

THRONE_USERNAME = os.getenv("THRONE_USERNAME")
THRONE_CHANNEL = int(os.getenv("THRONE_CHANNEL"))

ANNOUNCEMENT_CHANNEL = 1225137052165734513
INFO_CHANNEL = int(os.getenv("INFO_CHANNEL"))
MEIMEI_UID = 1197656323781836931

CATBOX_TOKEN = os.getenv("CATBOX_TOKEN")
GOFILE_API_TOKEN = os.getenv("GOFILE_API_TOKEN")

async def main():
    async with bot:
        await bot.start(BOT_TOKEN)

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    doujin_links = regex.findall("https:\/\/nhentai\.(?:net|com)\/g\/\d+\/?|https:\/\/e[x-]hentai.org\/g\/\d+\/[0-9a-f]+\/?", message.content)
    if doujin_links != []:
        edited_links = "\n".join(doujin_links)
        edited_links = regex.sub("https?:\/\/nhentai\.(?:net|com)\/g\/|https:\/\/e[x-]hentai.org\/g\/", "https://lolicon.store/g/", edited_links)
        for link in edited_links.split("\n"):
            response = requests.get(link, headers={'User-Agent': 'Mozilla/5.0 (compatible; Discordbot/2.0; +https://discordapp.com)'})
            discord_embed_data = regex.search("<meta property=\"og:description\"(?:.|\n)+?>", response.text)[0]
            is_loli_doujin = False
            if "lolicon" in discord_embed_data.lower():
                await message.reply("Please don't post loli doujins >.< (Just send the code)", delete_after=5)
                await message.delete()
                is_loli_doujin = True
        if not is_loli_doujin:
            await message.edit(suppress=True)
            await message.reply(edited_links, mention_author=False)
    if message.channel.id == ANNOUNCEMENT_CHANNEL and message.author.id == MEIMEI_UID and "schedule" in message.content.lower() and len(message.attachments) > 0:
        await message.attachments[0].save(fp="assets/schedule.png")
        
        # get last schedule
        folder_id = "48487a25-3367-4759-8b0e-f14436f7e7c8"
        r = requests.get(
            url = "https://api.gofile.io/contents/search",
            headers = {
                "Authorization": f"Bearer {GOFILE_API_TOKEN}",
            },
            params = {
                "contentId": folder_id,
                "searchedString": "CURRENT SCHEDULE"
            }
        ).json()
        last_schedule_id = list(r["data"].keys())[0]
        last_schedule_updated_name = r["data"][last_schedule_id]["name"].replace(" ----- CURRENT SCHEDULE", "")

        # rename last schedule so it's no longer the current one
        r = requests.put(
            url = f"https://api.gofile.io/contents/{last_schedule_id}/update",
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {GOFILE_API_TOKEN}"
            },
            json = {
                "attribute": "name",
                "attributeValue": last_schedule_updated_name
            }
        )
        
        # https://stackoverflow.com/questions/20413843/is-there-any-kind-of-standard-for-representing-date-ranges
        # upload new schedule
        today = datetime.now()
        start_date = today.isoformat()
        end_date = today + datetime.timedelta(days = 6)
        end_date = end_date.isoformat()
        # necessary because ISO calendar year can have 52 or 53 weeks
        # dec 28 is always in the last iso week of the year 
        total_weeks = datetime.date(today.year, 12, 28).isocalendar().week
        date_range_string = f"{total_weeks - today.isocalendar().week}-{start_date}--{end_date}"
        gofile_server = requests.get("https://api.gofile.io/servers").json()["data"]["servers"][0]["name"]
        r = requests.post(
            url = f"https://{gofile_server}.gofile.io/contents/uploadFile",
            data = {
                "token": GOFILE_API_TOKEN
            },
            files = {
                "file": (f"{date_range_string} ----- CURRENT SCHEDULE", open("assets/schedule.png", "rb"), "text/plain"),
                "folderId": (None, folder_id)
            }
        )

        # add schedule to #info
        info_channel = bot.get_channel(INFO_CHANNEL)
        schedule_message = info_channel.last_message
        embed = get_schedule_embed()
        await schedule_message.edit(embed=embed)

    if message.content.lower().startswith("suggestion"):
        await logSuggestion(message)
    await bot.process_commands(message)

def get_schedule_embed():
    schedule_image_url = requests.post('https://catbox.moe/user/api.php', files={"reqtype": (None, "fileupload"), "fileToUpload": open("assets/schedule.png", "rb")}).text
    embed = discord.Embed(
        title = "Mei-Mei's current schedule!",
        description = "If you would like an archive of all of Mei-Mei's past schedules, click [here](https://gofile.io/d/h158bY)!",
        color = discord.Color.from_str("#fdf4f8")
    )
    embed.set_image(url=schedule_image_url)
    return embed

@bot.command()
async def config_schedule_message(ctx, arg):
    info_channel = bot.get_channel(INFO_CHANNEL)
    embed = get_schedule_embed()
    if arg == "send":
        await info_channel.send(embed=embed)
    elif arg == "edit":
        schedule_message = info_channel.last_message
        await schedule_message.edit(embed=embed)
    else:
        await ctx.send("imagine being retarded")

@bot.event
async def on_ready():
    print(f"I'm ready for you Onii-chan!")
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, custom_throne_integration.watchThrone, THRONE_USERNAME, onThroneContribution, onThroneGift, onThroneWishlistUpdate)

@bot.event
async def on_member_join(member):
    gatekeep_role = member.guild.get_role(1246240396074422333)
    if datetime.datetime.now(datetime.timezone.utc) - member.created_at < datetime.timedelta(days=30):
        print("in here")
        await member.add_roles(gatekeep_role)
    elif gatekeep_role in member.roles:
        member.remove_roles(gatekeep_role)
    channel = bot.get_channel(AUDIT_CHANNEL)
    await channel.send(f"User {member.id} joined")

@bot.event
async def on_raw_member_remove(payload):
    channel = bot.get_channel(AUDIT_CHANNEL)
    await channel.send(f"User {payload.user.id} left")

@bot.command()
async def matrix(ctx):
    embed = discord.Embed(
        title = "How do I join the matrix?",
        color = discord.Color.from_str("#fdf4f8")
    )
    embed.add_field(name = "Step 1", value = "Wait two weeks after joining the server, and talk until you have 150 messages", inline=False)
    embed.add_field(name = "Step 2", value = "Make a cutefunny.art account if you haven't already. Feel free to ask a mod if you encounter any issues with this step.\nhttps://cutefunny.art/posts/matrixstart/", inline=False)
    embed.add_field(name = "Step 3", value = "Request to join in https://discord.com/channels/1225136839006879874/1229183855609774182/1276777753873485857", inline=False)
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
            "[VTuber Wiki](https://virtualyoutuber.fandom.com/wiki/Mei-Mei)\n"
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
            msg = gifter["customerMessage"].replace("\\n", "\n> ")
            if crowd:
                username = "Anon"
                if gifter.get("customerUsername") and len(gifter.get("customerUsername")) > 0:
                    username = gifter.get("customerUsername")
                customMessage += f'> {msg}\n- {username}\n'
            else:
                customMessage += f'> {msg}\n'
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
    customMessage = dono.get("message").replace("\\n", "\n> ") if dono.get("message") else ""
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
            (f"> {customMessage}\n\n" if len(customMessage) > 0 else "\n") +
            "Thank you so much for your cumtribution, mister!\n"
        ),
        color=discord.Color.from_str("#fdf4f8")
    )
    if dono.get("itemImage"):
        parsed = urllib.parse.urlparse(dono["itemImage"])
        if (len(parsed.scheme) > 0 and len(parsed.netloc) > 0):
            embed.set_image(url=dono["itemImage"])
    if item and item.get("id"):
        itemUrl = f'https://throne.com/{THRONE_USERNAME}/item/{item["id"]}'
        bot.loop.create_task(sendEmbedWithButton(channel, embed, "View on Throne", itemUrl))
    else:
        bot.loop.create_task(channel.send(embed=embed))

def onThroneWishlistUpdate(item):
    print(item)
    channel = bot.get_channel(THRONE_CHANNEL)
    customMessage = item.get("description").replace("\\n", "\n> ") if item.get("description") else ""
    itemUrl = f'https://throne.com/{THRONE_USERNAME}/item/{item["id"]}'
    embed = discord.Embed(
        url=itemUrl,
        title="New item added on Throne!",
        description=(
            f'**{item["name"]} | ${round(item["price"]//100)}.{round(item["price"]%100):02d} {item["currency"]}**\n' +
            (f"> {customMessage}\n" if len(customMessage) > 0 else "")
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

@bot.command(aliases=["album-from-thread"])
@commands.has_any_role(1225149408593838180, 1225328554624024667)
async def albumFromThread(ctx, thread: discord.Thread, maxImages: int, includeName: bool):
    numImages = {}
    uploadedImages = []
    async for message in thread.history(limit=None, oldest_first=False):
        for attachment in reversed(message.attachments):
            if attachment.height: #images and videos will have height and width defined
                existingImages = numImages.get(message.author.id, 0)
                if existingImages < maxImages:
                    r = await uploadImageToCatbox(attachment, message.author.display_name, includeName)
                    numImages[message.author.id] = existingImages + 1
                    if r:
                        uploadedImages.append(r)
                else:
                    print("skipping \"", attachment.filename, "\" too many images from user")
            else:
                print("skipping \"", attachment.filename, "\" not an image")
    if len(uploadedImages) == 0:
        await ctx.send("no images found in thread")
        return
    imgIds = []
    for url in uploadedImages:
        imgId = url.split("/")[-1]
        imgIds.append(imgId)
    imgIdString = " ".join(imgIds)
    data={"reqtype": "createalbum",
          "userhash": CATBOX_TOKEN,
          "title": thread.name if len(thread.name)>0 else "title",
          "desc": thread.name if len(thread.name)>0 else "description",
          "files": imgIdString
          }
    r = requests.post("https://catbox.moe/user/api.php", data=data)
    if r.status_code == 200:
        await ctx.send(r.text)
    else:
        await ctx.send("error creating album: " + r.text)

async def uploadImageToCatbox(attachment, name, includeName):
    try:
        print("going to upload", attachment.filename, "from", name, "with nick" if includeName else "without nick")
        image = await attachment.read()
        if image == None:
            print("error reading", attachment.filename)
            return None
        source = BytesIO(image)
        dest = BytesIO()
        if includeName:
            orig = Image.open(source)
            # put name at the top
            w,h = orig.size
            textSize = 50
            base = Image.new('RGBA',(w , int(h + textSize * 1.5)),(0,0,0,0))
            try:
                temp = orig.convert('RGBA')
                base.paste(temp, (0,int(textSize*1.5)), temp)
            except Exception as e:
                print(e)
                base.paste(orig, (0,int(textSize*1.5)))

            # add the text
            draw = ImageDraw.Draw(base)
            draw.text((0,0), name, font_size=textSize, fill="#FFFFFF", stroke_width=2, stroke_fill="#000000")
            base.save(dest, 'PNG')
        else:
            # no edit needed
            dest = source
        dest.seek(0)
        filename = "image.png" if includeName else attachment.filename
        m = MultipartEncoder(fields={"reqtype":"fileupload", "userhash":CATBOX_TOKEN, "fileToUpload":(filename, dest)})
        r = requests.post("https://catbox.moe/user/api.php", data = m, headers = {"Content-Type": m.content_type})
        if r.status_code == 200:
            return r.text
        else:
            print("error uploading file", r.text)
            return None
    except Exception as e:
        print(e)
        return None

if __name__ == "__main__":
    asyncio.run(main())
