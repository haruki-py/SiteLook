import discord
from discord.ext import commands
import json

# ------------------------ COGS ------------------------ #  

class AnalyticsCog(commands.Cog, name="analytics command"):
    def __init__(self, bot):
        self.bot = bot

# ------------------------------------------------------ #  

    @commands.command()
    async def analytics(self, ctx, index=None):
        # If the index argument is not provided, prompt the user for it
        if index is None:
            embed = discord.Embed(title='Index', description='Which monitor do you want to view the analytics for? Please enter the index of the monitor.', color=0x00ff00)
            embed.set_footer(text='up!analytics')
            await ctx.send(embed=embed)
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()
            try:
                response = await self.bot.wait_for('message', check=check, timeout=30.0)
            except asyncio.TimeoutError:
                embed = discord.Embed(title='Error', description='Sorry, you took too long to respond.', color=0xff0000)
                embed.set_footer(text='up!analytics')
                await ctx.send(embed=embed)
                return
            index = response.content

        # Load the analytics.json file and get the analytics for the specified monitor
        with open('analytics.json', 'r') as f:
            analytics = json.load(f)
        user_analytics = analytics.get(str(ctx.author.id), {})
        monitor_analytics = user_analytics.get(index, {})
        if not monitor_analytics:
            embed = discord.Embed(title='Analytics', description=f'No analytics found for monitor {index}', color=0x00ff00)
            embed.set_footer(text='up!analytics')
            await ctx.send(embed=embed)
            return

        # Format and send the analytics message in an embed
        response_times = monitor_analytics.get('average_response_time', [])
        error_rate = monitor_analytics.get('error_rate', 0)
        uptime_percentage = monitor_analytics.get('uptime_percentage', 0)
        analytics_message = f'Average response time: {response_times}ms\nError rate: {error_rate}\nUptime percentage: {uptime_percentage}'
        embed = discord.Embed(title='Analytics', description=analytics_message, color=0x00ff00)
        embed.set_footer(text='up!analytics')
        await ctx.send(embed=embed)

# ------------------------ BOT ------------------------ #  

def setup(client):
    client.add_cog(AnalyticsCog(client))