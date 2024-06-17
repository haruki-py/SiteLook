import discord
from discord.ext import commands
import json

# ------------------------ COGS (stolen from MEE6 bypasser github) ------------------------ #  

class AlertCog(commands.Cog, name="alert "):
    def __init__(self, bot):
        self.bot = bot

# ------------------------------------------------------ # 

    @commands.command()
    async def alert(self, ctx):
        # Check if the user has any websites to monitor
        with open('websites.json', 'r') as f:
            websites = json.load(f)
        user_websites = websites.get(str(ctx.author.id), [])
        if not user_websites:
            embed = discord.Embed(title='Error', description='You do not have any websites to monitor.', color=0xff0000)
            embed.set_footer(text='up!alert')
            await ctx.send(embed=embed)
            return

        # Prompt the user to choose a website
        embed = discord.Embed(title='Website', description='Which website do you want to set an alert for? Reply with your website index. If you don\'t know the index, please use up!stats.', color=0x00ff00)
        embed.set_footer(text='up!alert')
        await ctx.send(embed=embed)
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()
        try:
            response = await self.bot.wait_for('message', check=check, timeout=30.0)
        except asyncio.TimeoutError:
            embed = discord.Embed(title='Error', description='Sorry, you took too long to respond.', color=0xff0000)
            embed.set_footer(text='up!alert')
            await ctx.send(embed=embed)
            return
        website_index = int(response.content) - 1
        if not (0 <= website_index < len(user_websites)):
            embed = discord.Embed(title='Error', description=f'Please enter a valid website index.', color=0xff0000)
            embed.set_footer(text='up!alert')
            await ctx.send(embed=embed)
            return
        website = user_websites[website_index]
        
        # Check if alerts are already on or off for this website
        with open('alerts.json', 'r') as f:
            alerts = json.load(f)
        user_alerts = alerts.get(str(ctx.author.id), {})
        alerts_on = user_alerts.get(website['index'], True)

        # Prompt the user to turn alerts on or off
        embed = discord.Embed(title='Alerts', description=f'Do you want to turn alerts on or off for this website?', color=0x00ff00)
        embed.set_footer(text='up!alert')
        await ctx.send(embed=embed)
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content in ['on', 'off']
        try:
            response = await self.bot.wait_for('message', check=check, timeout=30.0)
        except asyncio.TimeoutError:
            embed = discord.Embed(title='Error', description='Sorry, you took too long to respond.', color=0xff0000)
            embed.set_footer(text='up!alert')
            await ctx.send(embed=embed)
            return

        # Check if the user is trying to turn on or off alerts for a website that already has alerts turned on or off, respectively
        if (response.content == 'on' and alerts_on) or (response.content == 'off' and not alerts_on):
            embed = discord.Embed(title='Error', description=f'Website {website["index"]} already has its alerts turned {"on" if alerts_on else "off"}.', color=0xff0000)
            embed.set_footer(text='up!alert')
            await ctx.send(embed=embed)
            return

        # Update the alerts.json file with the new alert setting
        user_alerts[website['index']] = response.content == 'on'
        alerts[str(ctx.author.id)] = user_alerts
        with open('alerts.json', 'w') as f:
            json.dump(alerts, f)

        # Send a success message
        embed = discord.Embed(title='Success', description=f'Alerts turned {response.content} for website {website["index"]}', color=0x00ff00)
        embed.set_footer(text='up!alert')
        await ctx.send(embed=embed)

# ------------------------ BOT ------------------------ #  

async def setup(bot):
    await bot.add_cog(AlertCog(bot))