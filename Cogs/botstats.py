import discord
from discord.ext import commands

# ------------------------ COGS ------------------------ #  

class BotstatsCog(commands.Cog, name="botstats command"):
    def __init__(self, bot):
        self.bot = bot

# ------------------------------------------------------ #  

    @commands.command(name='botstats')
    # @commands.is_owner()
    async def botstats(self, ctx):
        if ctx.author.id not in self.bot.adminid or ctx.author.id != self.bot.ownerid:
            return
            
        # Create the embed
        embed = discord.Embed(title='Bot Stats', color=0x00ff00)
        embed.add_field(name='Servers', value=f'{len(self.bot.guilds)}', inline=True)
        embed.add_field(name='Total Members', value=f'{len(self.bot.users)}', inline=True)
        embed.set_footer(text='Server count and total member count')

        # Send the embed
        await ctx.send(embed=embed)

# ------------------------ BOT ------------------------ #  

async def setup(bot):
    await bot.add_cog(BotstatsCog(bot))
