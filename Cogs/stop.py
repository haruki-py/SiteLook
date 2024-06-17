import discord
from discord.ext import commands
import json

# ------------------------ COGS ------------------------ #  

class StopCog(commands.Cog, name="stop command"):
    def __init__(self, bot):
        self.bot = bot

# ------------------------------------------------------ # 

    @commands.command()
    async def stop(self, ctx, index: int = None):
        if index is None:
            embed = discord.Embed(title='Error', description='Please include the index of the website to stop. Example: up!stop 1\nIf you do not know the index, use the up!stats command to view your monitored websites.', color=0xff0000)
            embed.set_footer(text='up!stop')
            await ctx.send(embed=embed)
            return
        with open('websites.json', 'r') as f:
            websites = json.load(f)
        user_websites = websites.get(str(ctx.author.id), [])
        if not user_websites:
            embed = discord.Embed(title='Error', description='You have not added any websites to monitor', color=0xff0000)
            embed.set_footer(text='up!stop')
            await ctx.send(embed=embed)
            return
        if index < 1 or index > len(user_websites):
            embed = discord.Embed(title='Error', description=f'Invalid index. Please enter a number between 1 and {len(user_websites)}\nIf you do not know the index, use the up!stats command to view your monitored websites.', color=0xff0000)
            embed.set_footer(text='up!stop')
            await ctx.send(embed=embed)
            return
        website = user_websites[index - 1]
        if 'stopped' not in website or not website['stopped']:
            website['stopped'] = True
            websites[str(ctx.author.id)] = user_websites
            with open('websites.json', 'w') as f:
                json.dump(websites, f)
            embed = discord.Embed(title='Success', description=f'Website {index} stopped', color=0x00ff00)
            embed.set_footer(text='up!stop')
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title='Error', description=f'Website {index} is already stopped', color=0xff0000)
            embed.set_footer(text='up!stop')
            await ctx.send(embed=embed)

# ------------------------ BOT ------------------------ #  

async def setup(bot):
    await bot.add_cog(StopCog(bot))