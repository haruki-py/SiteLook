import discord
from discord.ext import commands
import json

# ------------------------ COGS ------------------------ #  

class StatsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

# ------------------------------------------------------ #  

    @commands.command()
    async def stats(self, ctx):
        with open('websites.json', 'r') as f:
            websites = json.load(f)
        user_websites = websites.get(str(ctx.author.id), [])
        if not user_websites:
            embed = discord.Embed(title='Error', description='You have not added any websites to monitor', color=0xff0000)
            embed.set_footer(text='up!stats')
            await ctx.send(embed=embed)
            return
        stats_message = ''
        count = 1
        for website in user_websites:
            url = website['url']
            method = website['method']
            last_ping_time = website.get('last_ping_time', 'N/A')
            response_status = website.get('response_status', 'N/A')
            stats_message += f'{count}. {url}, {method}, last pinged on {last_ping_time} (IST), response status: {response_status}\n'
            count += 1
        embed = discord.Embed(title='Stats', description=stats_message, color=0x00ff00)
        embed.set_footer(text='up!stats')
        await ctx.author.send(embed=embed)
        if not isinstance(ctx.channel, discord.channel.DMChannel):
            await ctx.send(f'{ctx.author.mention} Check your DMs!')

# ------------------------ BOT ------------------------ #  

async def setup(bot):
    await bot.add_cog(StatsCog(bot))