from fastapi import FastAPI, Request, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import discord
from discord.ext import commands
from dependencies import config, discordPath, discord_channels
import logger # Using your existing logger
import uvicorn
from router import webpage
from router.api import ws, data
import sys
import asyncio
import os

sys.path.insert(1, '/*')
sys.path.insert(1, '.')

intents = discord.Intents.all()
bot = commands.Bot(command_prefix = 'k.', intents=intents)
bot.remove_command("help")

no_permission_embed=discord.Embed(title="等等..你是管理員嗎 這個是管理員才能用的喔\n請放心，我不會讓管理員知道的!",color=0xff0000)
admin = config['discord']['admin_users']

@bot.event
async def on_ready():
    print("bot is ready")
    global discord_channels
    discord_channels.clear()
    for i in config["discord"]["data_channels"]:
        discord_channels.append(bot.get_channel(i))

    channel = bot.get_channel(config['discord']['admin_channel'])
    await channel.send(">> Bot is online <<") # type: ignore

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

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting Discord bot...")
    asyncio.create_task(bot.start(config['discord']['token']))
    
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
    uvicorn.run("main:app",host="0.0.0.0", port=8001, reload=False)
