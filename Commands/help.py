import discord
from discord.ext import commands

# ------------------------ COGS ------------------------ #  

class HelpCog(commands.Cog, name="Help command"):
    def __init__(self, bot):
        self.bot = bot

# ------------------------------------------------------ #  

    @commands.command()
    async def help(self, ctx, command=None):
        # If no command is specified, send the general help message
        if command is None:
            embed = discord.Embed(title='Help', description='This is a bot that monitors websites and sends requests to them periodically.', color=0x00ff00)
            embed.add_field(name='up!monitor <website>', value='Add a website to monitor. You will be asked to choose a method (HEAD, GET or POST) and a time interval for pinging the website.', inline=False)
            embed.add_field(name='up!remove <index>', value='Remove a website from monitoring by its index. Use up!stats to view your monitored websites and their indices.', inline=False)
            embed.add_field(name='up!start <index>', value='Start monitoring a website that was stopped. You need to provide the index of the website. Use up!stats to view your monitored websites and their indices.', inline=False)
            embed.add_field(name='up!stop <index>', value='Stop monitoring a website. You need to provide the index of the website. Use up!stats to view your monitored websites and their indices.', inline=False)
            embed.add_field(name='up!stats', value='View the statistics of your monitored websites, such as the last ping time and response status. The statistics will be sent to your DMs.', inline=False)
            embed.add_field(name='up!alert', value='Turn alerts on or off for a specific website. You will be asked to choose a website by its index and whether you want to turn alerts on or off.', inline=False)
            embed.add_field(name='up!schedule <index> <schedule>', value='Set a schedule for a specific monitor using a cron expression. You need to provide the index of the monitor and the cron expression.', inline=False)
            embed.add_field(name='up!history <index>', value='View the history of a specific monitor. You need to provide the index of the monitor.', inline=False)
            embed.add_field(name='up!analytics <index>', value='View the analytics of a specific monitor, such as response times, error rate, and uptime percentage. You need to provide the index of the monitor.', inline=False)
            embed.add_field(name='up!help [command]', value='Get help on how to use this bot or a specific command.', inline=False)
            await ctx.send(embed=embed)

        # If a command is specified, send the help message for that command
        else:
            # Check if the command is valid
            if command in ['monitor', 'remove', 'start', 'stop', 'stats', 'alert', 'schedule', 'history', 'analytics', 'help']:
                # Send the help message for the monitor command
                if command == 'monitor':
                    embed = discord.Embed(title='Help: monitor', description='Add a website to monitor. You will be asked to choose a method (HEAD, GET or POST) and a time interval for pinging the website (minimum 1 minute).', color=0x00ff00)
                    embed.add_field(name='Usage', value='up!monitor <website>', inline=False)
                    embed.add_field(name='Example', value='up!monitor https://example.com', inline=False)
                    embed.set_footer(text='up!help monitor')
                    await ctx.send(embed=embed)

                # Send the help message for the remove command
                elif command == 'remove':
                    embed = discord.Embed(title='Help: remove', description='Remove a website from monitoring by its index. Use up!stats to view your monitored websites and their indices.', color=0x00ff00)
                    embed.add_field(name='Usage', value='up!remove <index>', inline=False)
                    embed.add_field(name='Example', value='up!remove 1', inline=False)
                    embed.set_footer(text='up!help remove')
                    await ctx.send(embed=embed)

                # Send the help message for the start command
                elif command == 'start':
                    embed = discord.Embed(title='Help: start', description='Start monitoring a website that was stopped. You need to provide the index of the website. Use up!stats to view your monitored websites and their indices.', color=0x00ff00)
                    embed.add_field(name='Usage', value='up!start <index>', inline=False)
                    embed.add_field(name='Example', value='up!start 1', inline=False)
                    embed.set_footer(text='up!help start')
                    await ctx.send(embed=embed)

                # Send the help message for the stop command
                elif command == 'stop':
                    embed = discord.Embed(title='Help: stop', description='Stop monitoring a website. You need to provide the index of the website. Use up!stats to view your monitored websites and their indices.', color=0x00ff00)
                    embed.add_field(name='Usage', value='up!stop <index>', inline=False)
                    embed.add_field(name='Example', value='up!stop 1', inline=False)
                    embed.set_footer(text='up!help stop')
                    await ctx.send(embed=embed)

                # Send the help message for the stats command
                elif command == 'stats':
                    embed = discord.Embed(title='Help: stats', description='View the statistics of your monitored websites, such as the last ping time and response status. The statistics will be sent to your DMs.', color=0x00ff00)
                    embed.add_field(name='Usage', value='up!stats', inline=False)
                    embed.set_footer(text='up!help stats')
                    await ctx.send(embed=embed)

                # Send the help message for the alert command
                elif command == 'alert':
                    embed = discord.Embed(title='Help: alert', description='Turn alerts on or off for a specific website. You will be asked to choose a website by its index and whether you want to turn alerts on or off.', color=0x00ff00)
                    embed.add_field(name='Usage', value='up!alert', inline=False)
                    embed.set_footer(text='up!help alert')
                    await ctx.send(embed=embed)

                # Send the help message for the schedule command
                elif command == 'schedule':
                    embed = discord.Embed(title='Help: schedule', description='Set a schedule for a specific monitor using a cron expression. You need to provide the index of the monitor and the cron expression.', color=0x00ff00)
                    embed.add_field(name='Usage', value='up!schedule <index> <schedule>', inline=False)
                    embed.add_field(name='Example', value='up!schedule 1 */5 * * * *', inline=False)
                    embed.set_footer(text='up!help schedule')
                    await ctx.send(embed=embed)

                # Send the help message for the history command
                elif command == 'history':
                    embed = discord.Embed(title='Help: history', description='View the history of a specific monitor. You need to provide the index of the monitor.', color=0x00ff00)
                    embed.add_field(name='Usage', value='up!history <index>', inline=False)
                    embed.add_field(name='Example', value='up!history 1', inline=False)
                    embed.set_footer(text='up!help history')
                    await ctx.send(embed=embed)

                # Send the help message for the analytics command
                elif command == 'analytics':
                    embed = discord.Embed(title='Help: analytics', description='View the analytics of a specific monitor, such as response times, error rate, and uptime percentage. You need to provide the index of the monitor.', color=0x00ff00)
                    embed.add_field(name='Usage', value='up!analytics <index>', inline=False)
                    embed.add_field(name='Example', value='up!analytics 1', inline=False)
                    embed.set_footer(text='up!help analytics')
                    await ctx.send(embed=embed)

                # Send the help message for the help command
                elif command == 'help':
                    embed = discord.Embed(title='Help: help', description='Get help on how to use this bot or a specific command.', color=0x00ff00)
                    embed.add_field(name='Usage', value='up!help [command]', inline=False)
                    embed.add_field(name='Example', value='up!help monitor', inline=False)
                    embed.set_footer(text='up!help help')
                    await ctx.send(embed=embed)

            # If the command is not valid, send an error message
            else:
                embed = discord.Embed(title='Error', description=f'Invalid command: {command}', color=0xff0000)
                embed.set_footer(text='up!help')
                await ctx.send(embed=embed)

# ------------------------ BOT ------------------------ #  

def setup(client):
    client.add_cog(HelpCog(client))