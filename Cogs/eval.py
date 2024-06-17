import discord
from discord.ext import commands

# ------------------------ COGS ------------------------ #  

class EvalCog(commands.Cog, name="eval command"):
    def __init__(self, bot):
        self.bot = bot

# ------------------------------------------------------ #  

    @commands.command(name="eval")
    async def evaluate(self, ctx, *, code: str):
        if ctx.author.id not in adminid or ctx.author.id != ownerid:
            return

        # Remove single or triple backtick code block formatting
        code = code.strip('`')
        if code.startswith(('python', 'py')):
            code = code.split('\n', 1)[1]

        try:
            # Evaluate the provided code
            result = eval(code)
            # Check if the result exceeds the character limit
            if len(str(result)) > 2000:
                # Create a temporary file to store the result
                with open('eval_result.txt', 'w') as f:
                    f.write(str(result))
                # Send the result as an attachment
                await ctx.send(file=discord.File('eval_result.txt'))
                # Delete the temporary file
                os.remove('eval_result.txt')
            else:
                # Send the result as an embed
                embed = discord.Embed(title='Eval Result', description=f'```python\n{result}\n```', color=0x00ff00)
                await ctx.send(embed=embed)
        except Exception as e:
            # Handle any exceptions
            embed = discord.Embed(title='Error', description=f'An error occurred: {str(e)}', color=0xff0000)
            await ctx.send(embed=embed)

# ------------------------ BOT ------------------------ #  

async def setup(bot):
    await bot.add_cog(EvalCog(bot))