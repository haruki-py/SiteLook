import discord
from discord.ext import commands
import json

# ------------------------ COGS ------------------------ #  

class RemoveCog(commands.Cog, name="remove command"):
    def __init__(self, bot):
        self.bot = bot

# ------------------------------------------------------ #  

    @commands.command()
    async def remove(self, ctx):
        split_message = ctx.message.content.split()
        if len(split_message) < 2:
            embed = discord.Embed(title='Error', description='Please include an index to remove. Example: up!remove 1\nIf you do not know the index, use the up!stats command to view your monitored websites.', color=0xff0000)
            embed.set_footer(text='up!remove')
            await ctx.send(embed=embed)
            return
        argument = split_message[1]
        with open('websites.json', 'r') as f:
            websites = json.load(f)
        user_websites = websites.get(str(ctx.author.id), [])

        # Check if the argument is an index
        if argument.isdigit():
            index = int(argument)
            if index < 1 or index > len(user_websites):
                embed = discord.Embed(title='Error', description=f'Invalid index. Please enter a number between 1 and {len(user_websites)}\nIf you do not know the index, use the up!stats command to view your monitored websites.', color=0xff0000)
                embed.set_footer(text='up!remove')
                await ctx.send(embed=embed)
                return
            del user_websites[index - 1]

            # Update the file and send a success message
            websites[str(ctx.author.id)] = user_websites
            with open('websites.json', 'w') as f:
                json.dump(websites, f)
            if not isinstance(ctx.channel, discord.channel.DMChannel):
                try:
                    await ctx.message.delete()
                except discord.Forbidden:
                    pass
            embed = discord.Embed(title='Success', description='Website removed', color=0x00ff00)
            embed.set_footer(text='up!remove')
            await ctx.send(embed=embed)

        # If the argument is not an index, send an error message
        else:
            embed = discord.Embed(title='Error', description=f'Invalid argument. Please enter an index to remove. Example: up!remove 1\nIf you do not know the index, use the up!stats command to view your monitored websites.', color=0xff0000)
            embed.set_footer(text='up!remove')
            await ctx.send(embed=embed)

# ------------------------ BOT ------------------------ #  

async def setup(bot):
    await bot.add_cog(RemoveCog(bot))