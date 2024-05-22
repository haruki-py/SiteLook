import discord
from discord.ext import commands
import time
import os

# ------------------------ COGS ------------------------ #  

class PingCog(commands.Cog, name="ping command"):
    def __init__(self, bot):
        self.bot = bot

# ------------------------------------------------------ #  

    @commands.command()
    async def ping(self, ctx):
        # Measure host ping by sending a message and timing how long it takes
        start_time = time.perf_counter()
        message = await ctx.send("Calculating Ping...")
        end_time = time.perf_counter()
        host_ping = float("{:.2f}".format((end_time - start_time) * 1000)) # Host ping in milliseconds with decimal
    
        # Measure API latency
        api_latency = float("{:.2f}".format(self.bot.latency * 1000))  # API latency in milliseconds with decimal

        # Measure bot latency
        bot_ping = api_latency + host_ping # Bot latency in milliseconds

        # Create the embed with latency information
        embed = discord.Embed(title='Ping', description=f'Bot Ping: {bot_ping} ms\nAPI Latency: {api_latency} ms\nHost Ping : {host_ping} ms', color=0x00ff00)
        embed.set_footer(text='up!ping')
        await message.edit(content="", embed=embed)

# ------------------------ BOT ------------------------ #  

def setup(client):
    client.add_cog(PingCog(client))