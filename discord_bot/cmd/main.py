import discord
from discord import ButtonStyle
from discord.ui import Button,View
from discord.ext import commands
from core.classes import Cog_Extension
import asyncio
import time

class Main(Cog_Extension):
    @commands.command()
    async def help(self, ctx):
        muddesbutton = time.time()
        embed=discord.Embed(title="🤖指令集🤖 *此欄位將在1分鐘後關閉*", description="指令前綴是「k.」\n提示中\n[ ]代表必須輸入\n( )代表可打可不打", color=0x00ff04)
        embed.add_field(name="help", value="查看指令", inline=True)
        embed.add_field(name="`==金錢系統==`", value="** **", inline=False)
        embed.add_field(name="money (@某人)", value="查看銀行", inline=True)
        embed.add_field(name="work", value="工作賺錢", inline=True)
        embed.add_field(name="`==mud遊戲==(開發中)`", value="** **", inline=False)
        #embed.add_field(name="m", value="進入mud遊戲", inline=True)
        embed.add_field(name="mds", value="mud遊戲介紹", inline=True)
        embed.add_field(name="mex", value="查看mud遊戲經驗", inline=True)
        embed.add_field(name="mp", value="遊玩", inline=True)

        buttons = Button(label="關閉",style=ButtonStyle.red)
        async def close_callback(interaction):
            if str(interaction.user) == str(ctx.message.author):
                embed1 = discord.Embed(title="已關閉指令查詢", color=0x00ff00)
                view=View()
                await interaction.response.edit_message(embed=embed1,view=view)
        buttons.callback = close_callback
        view = View(timeout=0)
        view.add_item(buttons)
        await ctx.send(embed=embed,view=view)
        #
        #embed1 = discord.Embed(title="已關閉指令查詢", color=0x00ff00)
        #components= [{"components":[{"type": 2,"label":"關閉", "style":4, "custom_id":"help"+str(muddesbutton)}]}]
        
    #@commands.command()
    #async def btest(self,ctx):
    #    buttons = Button(label="完成",style=ButtonStyle.red)
    #    async def close_callback(interaction):
    #        await interaction.response.send_message("ok")
    #    buttons.callback = close_callback
    #    view = View(timeout=0)
    #    view.add_item(buttons)
    #    embed = discord.Embed(title="測試",description="Never gonna give u up",color=0xff0000)
    #    await ctx.send(embed=embed,view=view)
        
        #try:
        #    await self.bot.wait_for("button_click", check=lambda i:i.custom_id == "help"+str(muddesbutton),timeout=60)
        #except:
        #    pass
        #finally:
        #    await message.edit(embed=embed1)

    @commands.command()
    async def clear(self, ctx, *,num:int=None):
        user = str(ctx.message.author)
        if user in admin:
            if num == None:
                await ctx.channel.purge(limit=101) 
            else:
                await ctx.channel.purge(limit=num+1)
        else:
            embed = discord.Embed(title="你沒有管理權限",color=0xff0000)
            await ctx.send(embed=embed)

    @commands.command()
    async def md(self,ctx,member:discord.Member=None,item:str=None ,amount:int=None):
        user = str(ctx.message.author)
        if member != None and item != None and amount != None:
            if user in admin:
                if member == None:
                    user = str(ctx.message.author)
                else:
                    user = str(member)
                data = read(user)
                if item in datatype:
                    data[item] = amount
                    embed = discord.Embed(title=f"已將{user}的{item}設為{amount}!", color=0x00ff00)
                    save(user,data)
                else:
                    embed = discord.Embed(title=f"找不到項目{item}", color=0x00ff00)
                
            else:
                embed = discord.Embed(title=f"你沒有管理權限", color=0xff0000)
        else:
            embed = discord.Embed(title="指令錯誤，md[人][物品][數量]",color=0xff0000)
        await ctx.send(embed=embed)

    @commands.command()
    async def backup(self,ctx):
        loctime = time.localtime(time.time())
        tm = (f"{loctime.tm_year}.{loctime.tm_mon}.{loctime.tm_mday}.{loctime.tm_hour}.{loctime.tm_min}.{loctime.tm_sec}")
        #tm = str(tm)
        for Filename in os.listdir('./userdata'):
            if Filename.endswith('.json'):
                print(f"loading {Filename}")
                with open(f"userdata\\{Filename}","r",encoding="UTF-8") as d:
                    data = json.load(d)
                    with open(f"backupddata\\{tm}.txt","a") as f:
                        f.write(f"{Filename[:-5]}:{str(data)}\n")
                print("done")
        await ctx.send("已成功備分")

    @commands.command()
    async def status(self,ctx):
        file_size = 0
        player_count = 0
        for Filename in os.listdir("./userdata"):
            file_size += os.path.getsize(f"userdata\\{Filename}")
            player_count+=1
        embed=discord.Embed(title="📊機器人狀態   ✅線上",color=0x00ff00)
        embed.add_field(name="📄MUD Bot版本",value="1.0.1",inline=True)
        embed.add_field(name="📄Python版本",value=platform.python_version(),inline=True)
        embed.add_field(name="⏱延遲",value=f"{round(self.bot.latency*1000)} (ms)",inline=True)
        embed.add_field(name="📋儲存空間",value=f"{file_size}B/1GB",inline=True)
        embed.add_field(name="🎎已服務玩家",value=player_count,inline=True)
        embed.add_field(name="🛠CPU中央處理器",value=f"{psutil.cpu_percent()}/100%",inline=True)
        embed.add_field(name="📃RAM記憶體",value=f"{psutil.virtual_memory().percent}/100%",inline=True)
        await ctx.send(embed=embed)

    @commands.command()
    async def myid(self,ctx):
        await ctx.send(f"你的id是{ctx.message.author.id}")
        admins = self.bot.get_user(949607058993455104)
        await admins.send("test")

async def setup(bot):
    await bot.add_cog(Main(bot))
