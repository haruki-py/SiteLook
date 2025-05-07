import discord
from discord.ext import commands

class ShutdownCog(commands.Cog, name="shutdown command"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def shutdown(self, ctx):
        if ctx.author.id != self.bot.ownerid and ctx.author.id not in self.bot.adminid:
            return
  
        embed = discord.Embed(title='Shutdown', description='Shutting down the bot...', color=0xff0000)
        await ctx.send(embed=embed)
        await self.bot.close()

async def setup(bot):
    await bot.add_cog(ShutdownCog(bot))
