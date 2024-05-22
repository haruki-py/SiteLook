import discord
from discord.ext import commands
import asyncio

# ------------------------ COGS ------------------------ #  

class ExecCog(commands.Cog, name="exec command"):
    def __init__(self, bot):
        self.bot = bot

# ------------------------------------------------------ #  

    @commands.command(name="exec")
    async def exec(self, ctx, *, command: str = None):
        if ctx.author.id not in adminid or ctx.author.id != ownerid:
            return
        # Check if a command was provided
        if command is None:
            embed = discord.Embed(title='Error', description='Please provide a command to execute. Example: up!exec ls -la', color=0xff0000)
            embed.set_footer(text='up!exec')
            await ctx.send(embed=embed)
            return

        # Remove single backticks and triple backticks with language identifiers
        command = command.strip('`').strip('```').split('\n', 1)[-1] if command.startswith('```') else command

        # Execute the command in the shell
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        # Check if the output exceeds the Discord character limit for embeds
        if stdout or stderr:
            if len(stdout) + len(stderr) > 1010:  # Discord's limit for embeds is 6000 characters
                # Write output to a temporary file
                with open('output.txt', 'w') as file:
                    file.write(stdout.decode() + '\n' + stderr.decode())
                # Send the file
                await ctx.send(file=discord.File('output.txt'))
                # Delete the file
                os.remove('output.txt')
            else:
                # Prepare the response message
                response = discord.Embed(title='Command Executed', color=0x00ff00)
                if stdout:
                    response.add_field(name='Output', value=f'```\n{stdout.decode()}\n```', inline=False)
                if stderr:
                    response.add_field(name='Error and/or warning', value=f'```\n{stderr.decode()}\n```', inline=False)
                response.set_footer(text='up!exec')
                await ctx.send(embed=response)
        else:
            # Send a message indicating that the command was executed without output
            embed = discord.Embed(title='Command Executed', description='The command was executed successfully, but there was no output.', color=0x00ff00)
            embed.set_footer(text='up!exec')
            await ctx.send(embed=embed)

# ------------------------ BOT ------------------------ #  

def setup(client):
    client.add_cog(ExecCog(client))