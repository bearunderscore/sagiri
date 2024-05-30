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

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = commands.Bot(command_prefix="-", intents=discord.Intents.all())

async def main():
    async with bot:
        await bot.start(BOT_TOKEN)
    
@bot.event
async def on_ready():
    print(f"I'm ready for you Onii-chan!")
    now_live.start()

class NowLive(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.url = "https://pomf.tv/stream/meimeimei"
        self.add_item(discord.ui.Button(label="Watch Now!", url=self.url))

is_streaming = False
@tasks.loop(seconds=10.0)
async def now_live():
    global is_streaming
    channel = await bot.fetch_channel(1225137632346898516)
    r = requests.get("https://pomf.tv/api/streams/getinfo.php?data=streamdata&stream=meimeimei")
    data = r.json()

    if is_streaming == True:
        if data.get("stream_online") == 0:
            is_streaming == False
        return
    
    if data.get("stream_online") == 1:
        embed = discord.Embed(
            color=discord.Colour.red(),
            title=data.get("streamtitle"),
            url="https://pomf.tv/stream/meimeimei"
        )
        embed.description = "Cunny wife is streaming!!!!"
        streambanner = data.get("streambanner")
        embed.set_image(url=f"https://pomf.tv/img/stream/thumb/{streambanner}")
        await channel.send(content="<@&1226405821357756439>",embed=embed, view=NowLive())
        is_streaming = True

@bot.command()
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

@bot.command()
async def getusers(ctx, role: discord.Role, role2: discord.Role):
    s1 = set([m.name for m in role.members])
    s2 = set([m.name for m in role2.members])
    print("users in", role.name, "but not", role2.name)
    print(s1.difference(s2))
    print(len(s1.difference(s2)))
    print("users in", role2.name, "but not", role.name)
    print(s2.difference(s1))
    print(len(s2.difference(s1)))

if __name__ == "__main__":
    asyncio.run(main())