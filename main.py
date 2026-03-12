from fastapi import FastAPI, Request, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import discord
from discord.ext import commands
from dependencies import discordPath, discord_channels, config, mqtt_client
import logger  # Using your existing logger
import uvicorn
from router import webpage
from router.api import ws, data
import sys
import asyncio
import os

sys.path.insert(1, '/*')
sys.path.insert(1, '.')

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='k.', intents=intents)
bot.remove_command("help")

no_permission_embed = discord.Embed(
    title="等等..你是管理員嗎 這個是管理員才能用的喔\n請放心，我不會讓管理員知道的!", color=0xff0000)
admin = config['discord']['admin_users']


@bot.event
async def on_ready():
    print("bot is ready")
    global discord_channels
    discord_channels.clear()
    for i in config["discord"]["data_channels"]:
        discord_channels.append(bot.get_channel(i))

    channel = bot.get_channel(config['discord']['admin_channel'])
    await channel.send(">> Bot is online <<")  # type: ignore


@bot.command()
async def reload(ctx):
    if str(ctx.message.author) in admin:
        discord_channels.clear()
        for i in config["discord"]["data_channels"]:
            discord_channels.append(bot.get_channel(i))
        await ctx.send(f'reloaded channels done.')
    else:
        await ctx.message.delete()
        noperm = await ctx.send(embed=no_permission_embed)
        await asyncio.sleep(3)
        await noperm.delete()


def on_connect(client, userdata, flags, rc, properties=None):
    """
    rc (return code) values:
    0: Connection successful (Authenticated)
    1: Connection refused - incorrect protocol version
    2: Connection refused - invalid client identifier
    3: Connection refused - server unavailable
    4: Connection refused - bad username or password
    5: Connection refused - not authorized
    """
    if rc == 0:
        print("✅ Authentication Successful! Connected to broker.")
    elif rc == 4 or rc == 5:
        print("❌ Authentication Failed: Check username and password.")
    else:
        print(f"❓ Connection failed with code {rc}")


def on_publish(client, userdata, mid, reason_code=None, properties=None):
    print(f"👍 Message {mid} has been successfully published to the broker.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting Discord bot...")
    asyncio.create_task(bot.start(config['discord']['token']))
    # mqtt_client.on_connect = on_connect
    # mqtt_client.on_publish = on_publish
    # print("the username is: "+config["mqtt_client"].get("username", ""))
    mqtt_client.username_pw_set(config["mqtt_client"].get(
        "username", ""), config["mqtt_client"].get("password", ""))
    mqtt_client.connect(config["mqtt_client"].get("host", "localhost"), config["mqtt_client"].get(
        "port", 1883), config["mqtt_client"].get("keepalive", 60))
    print("Starting MQTT client...")
    mqtt_client.loop_start()

    yield  # FastAPI runs here

    # This runs when the server stops
    print("Shutting down...")
    await bot.close()

app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.add_middleware(GZipMiddleware, minimum_size=500, compresslevel=5)
templates = Jinja2Templates(directory="templates")

app.include_router(data.router)
app.include_router(ws.router)
app.include_router(webpage.router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Get the raw body bytes
    body = await request.body()

    # Log the exact data that caused the 422 error
    logger.error(f"422 Validation Error!")
    logger.error(f"Path: {request.url.path}")
    logger.error(f"Raw Body: {body.decode()}")
    logger.error(f"Pydantic Errors: {exc.errors()}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "received_body": body.decode()
        },
    )

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=False)
