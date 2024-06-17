import discord
from discord.ext import commands
import json

# ------------------------ COGS ------------------------ #  

class HistoryCog(commands.Cog, name="history command"):
    def __init__(self, bot):
        self.bot = bot

# ------------------------------------------------------ #  

    @commands.command()
    async def history(self, ctx, index=None):
        # If the index argument is not provided, prompt the user for it
        if index is None:
            embed = discord.Embed(title='Index', description='Which monitor do you want to view the history for? Please enter the index of the monitor.', color=0x00ff00)
            embed.set_footer(text='up!history')
            await ctx.send(embed=embed)
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()
            try:
                response = await self.bot.wait_for('message', check=check, timeout=30.0)
            except asyncio.TimeoutError:
                embed = discord.Embed(title='Error', description='Sorry, you took too long to respond.', color=0xff0000)
                embed.set_footer(text='up!history')
                await ctx.send(embed=embed)
                return
            index = response.content

        # Load the history.json file and get the history for the specified monitor
        with open('history.json', 'r') as f:
            history = json.load(f)
        user_history = history.get(str(ctx.author.id), {})
        monitor_history = user_history.get(index, [])
        if not monitor_history:
            embed = discord.Embed(title='History', description=f'No history found for monitor {index}', color=0x00ff00)
            embed.set_footer(text='up!history')
            await ctx.send(embed=embed)
            return

        # Format and send the history message in an embed
        history_message = ''
        for entry in monitor_history:
            history_message += f'{entry["time"]}: {entry["status"]}\n'
        embed = discord.Embed(title='History', description=history_message, color=0x00ff00)
        embed.set_footer(text='up!history')
        await ctx.send(embed=embed)

# ------------------------ BOT ------------------------ #  

async def setup(bot):
    await bot.add_cog(HistoryCog(bot))