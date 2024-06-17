import discord
from discord.ext import commands
import json

# ------------------------ COGS ------------------------ #  

class MonitorCog(commands.Cog, name="monitor command"):
    def __init__(self, bot):
        self.bot = bot

# ------------------------------------------------------ #  

    @commands.command()
    async def monitor(self, ctx):
        split_message = ctx.message.content.split()
        if len(split_message) < 2:
            embed = discord.Embed(title='Error', description='Please include a website to monitor. Example: up!monitor https://example.com', color=0xff0000)
            embed.set_footer(text='up!monitor')
            await ctx.send(embed=embed)
            return
        website = split_message[1]
        with open('websites.json', 'r') as f:
            websites = json.load(f)
        user_websites = websites.get(str(ctx.author.id), [])
        for user_website in user_websites:
            if user_website['url'] == website:
                embed = discord.Embed(title='Error', description='That website is already being monitored', color=0xff0000)
                embed.set_footer(text='up!monitor')
                await ctx.send(embed=embed)
                return
        embed = discord.Embed(title='Method', description='''Which one? 
    1. HEAD
    2. GET
    3. POST? 
    Reply with the 1, 2 or 3.''', color=0x00ff00)
        embed.set_footer(text='up!monitor')
        await ctx.send(embed=embed)
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content in ['1', '2', '3']
        try:
            response = await self.bot.wait_for('message', check=check, timeout=30.0)
        except asyncio.TimeoutError:
            embed = discord.Embed(title='Error', description='Sorry, you took too long to respond.', color=0xff0000)
            embed.set_footer(text='up!monitor')
            await ctx.send(embed=embed)
            return
        method = ''
        if response.content == '1':
            method = 'HEAD'
        elif response.content == '2':
            method = 'GET'
        elif response.content == '3':
            method = 'POST'

        # Ask the user for the time interval
        embed = discord.Embed(title='Time Interval', description='''How often do you want to ping the website? 
    Enter a number followed by a unit of time. For example: 
    s for seconds
    m for minute
    h for hour
    d for day
    w for week
    You can also use decimal points to specify fractions of a unit. For example:
    0.5m for 30 seconds
    6.9h for 6 hours and 54 minutes
    The minimum interval is 1 minute.''', color=0x00ff00)
        embed.set_footer(text='up!monitor')
        await ctx.send(embed=embed)

        # Use a regular expression to check the format of the time interval
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and re.match(r'\d+(\.\d+)?[smhdw]$', m.content)
        try:
            response = await self.bot.wait_for('message', check=check, timeout=30.0)
        except asyncio.TimeoutError:
            embed = discord.Embed(title='Error', description='Sorry, you took too long to respond.', color=0xff0000)
            embed.set_footer(text='up!monitor')
            await ctx.send(embed=embed)
            return

        # Convert the time interval to seconds and store it in the websites.json file
        time_interval = response.content
        unit = time_interval[-1]
        factor = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400, 'w': 604800}
        try:
            number = float(time_interval[:-1])
            seconds = number * factor[unit]
            if seconds < 60:
                raise ValueError('Minimum time interval is 1 minute. Please try again')
        except ValueError as e:
            embed = discord.Embed(title='Error', description=f'{e}', color=0xff0000)
            embed.set_footer(text='up!monitor')
            await ctx.send(embed=embed)
            return

        # Generate a new index for the website by finding the maximum index of existing websites and adding 1
        max_index = max((int(user_website['index']) for user_website in user_websites), default=0)
        new_index = str(max_index + 1)
        user_websites.append({'url': website, 'method': method, 'time_interval': seconds, 'index': new_index})
        websites[str(ctx.author.id)] = user_websites
        with open('websites.json', 'w') as f:
            json.dump(websites, f)

        # Delete the user's messages if possible
        try:
            await ctx.message.delete()
            await response.delete()
        except discord.Forbidden:
            pass

        # Send a success message
        embed = discord.Embed(title='Success', description='Website added', color=0x00ff00)
        embed.set_footer(text='up!monitor')
        await ctx.send(embed=embed)

# ------------------------ BOT ------------------------ #  

async def setup(bot):
    await bot.add_cog(MonitorCog(bot))