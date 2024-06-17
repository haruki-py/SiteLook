import discord
from discord.ext import commands
import json

# ------------------------ COGS ------------------------ #  

class ScheduleCog(commands.Cog, name="schedule command"):
    def __init__(self, bot):
        self.bot = bot

# ------------------------------------------------------ #  

    @commands.command()
    async def schedule(self, ctx, index=None, *, schedule=None):
        # If the index argument is not provided, prompt the user for it
        if index is None:
            embed = discord.Embed(title='Index', description='Which monitor do you want to set a schedule for? Please enter the index of the monitor.', color=0x00ff00)
            embed.set_footer(text='up!schedule')
            await ctx.send(embed=embed)
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()
            try:
                response = await self.bot.wait_for('message', check=check, timeout=30.0)
            except asyncio.TimeoutError:
                embed = discord.Embed(title='Error', description='Sorry, you took too long to respond.', color=0xff0000)
                embed.set_footer(text='up!schedule')
                await ctx.send(embed=embed)
                return
            index = response.content

        # If the schedule argument is not provided, prompt the user for it
        if schedule is None:
            embed = discord.Embed(title='Schedule', description='What schedule do you want to set for the monitor? Please enter a cron expression.', color=0x00ff00)
            embed.set_footer(text='up!schedule')
            await ctx.send(embed=embed)
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel
            try:
                response = await self.bot.wait_for('message', check=check, timeout=30.0)
            except asyncio.TimeoutError:
                embed = discord.Embed(title='Error', description='Sorry, you took too long to respond.', color=0xff0000)
                embed.set_footer(text='up!schedule')
                await ctx.send(embed=embed)
                return
            schedule = response.content

        # Update the schedules.json file with the new schedule
        with open('schedules.json', 'r') as f:
            schedules = json.load(f)
        user_schedules = schedules.get(str(ctx.author.id), {})
        user_schedules[index] = schedule
        schedules[str(ctx.author.id)] = user_schedules
        with open('schedules.json', 'w') as f:
            json.dump(schedules, f)

        # Send a success message
        await ctx.send(f'Schedule set for monitor {index}')

# ------------------------ BOT ------------------------ #  

async def setup(bot):
    await bot.add_cog(ScheduleCog(bot))