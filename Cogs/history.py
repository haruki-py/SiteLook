import discord
import sqlite3
import json
from discord.ext import commands
import asyncio

class HistoryCog(commands.Cog, name="history command"):
    def __init__(self, bot):
        self.bot = bot
        self.HISTORY_LIMIT = 25 

    def get_db_connection(self):
        """Create and return a database connection with row factory"""
        conn = sqlite3.connect('monitoring.db')
        conn.row_factory = sqlite3.Row
        return conn

    async def validate_user_websites(self, ctx):
        """Check if user has any websites and return count"""
        conn = self.get_db_connection()
        try:
            c = conn.cursor()
            c.execute('SELECT COUNT(*) FROM websites WHERE user_id = ?', (str(ctx.author.id),))
            return c.fetchone()[0]
        finally:
            conn.close()

    @commands.command()
    async def history(self, ctx, index: str = None):
        """Display status history for a monitored website"""
        website_count = await self.validate_user_websites(ctx)
        if website_count == 0:
            embed = discord.Embed(title='Error',
                                description='You have no monitored websites',
                                color=0xff0000)
            embed.set_footer(text='up!history')
            await ctx.send(embed=embed)
            return

        if not index:
            embed = discord.Embed(title='Index',
                                description='Which monitor do you want to view history for? Enter the index:',
                                color=0x00ff00)
            embed.set_footer(text='up!history')
            msg = await ctx.send(embed=embed)

            try:
                response = await self.bot.wait_for('message',
                                                    check=lambda m: m.author == ctx.author and
                                                    m.channel == ctx.channel and
                                                    m.content.isdigit(),
                                                    timeout=30.0)
                index = response.content
            except asyncio.TimeoutError:
                embed = discord.Embed(title='Error',
                                      description='Response timed out',
                                      color=0xff0000)
                embed.set_footer(text='up!history')
                await msg.edit(embed=embed)
                return

        if not index.isdigit():
            embed = discord.Embed(title='Error',
                                description='Index must be a positive number',
                                color=0xff0000)
            embed.set_footer(text='up!history')
            await ctx.send(embed=embed)
            return

        conn = self.get_db_connection()
        try:
            c = conn.cursor()
            
            c.execute('SELECT website_index FROM websites WHERE user_id = ? ORDER BY website_index ASC',
                     (str(ctx.author.id),))
            indexes = [row['website_index'] for row in c.fetchall()]
            
            position = int(index)
            if position < 1 or position > len(indexes):
                embed = discord.Embed(title='Error',
                                    description=f'Invalid index. Use 1-{len(indexes)}',
                                    color=0xff0000)
                embed.set_footer(text='up!history')
                await ctx.send(embed=embed)
                return

            website_index = indexes[position - 1]

            c.execute('SELECT history FROM history WHERE user_id = ? AND website_index = ?',
                     (str(ctx.author.id), website_index))
            result = c.fetchone()
            
            if not result or not result['history']:
                embed = discord.Embed(title='History',
                                      description=f'No history found for monitor {position}',
                                      color=0x00ff00)
                embed.set_footer(text='up!history')
                await ctx.send(embed=embed)
                return

            history_data = json.loads(result['history'])
            
            history_message = []
            for entry in history_data[-self.HISTORY_LIMIT:]: 
                history_message.append(
                    f"{entry.get('time', 'Unknown time')}: {entry.get('status', 'Unknown status')}"
                )

            chunk_size = 15
            for i in range(0, len(history_message), chunk_size):
                chunk = history_message[i:i+chunk_size]
                embed = discord.Embed(
                    title=f'History for Monitor #{position}',
                    description='\n'.join(chunk),
                    color=0x00ff00
                )
                embed.set_footer(text=f'Showing {len(chunk)} of {len(history_message)} entries • up!history')
                await ctx.send(embed=embed)

        except json.JSONDecodeError:
            embed = discord.Embed(title='Error',
                                description='Could not load history data',
                                color=0xff0000)
            embed.set_footer(text='up!history')
            await ctx.send(embed=embed)
        except Exception as e:
            print(f"History command error: {str(e)}")
            embed = discord.Embed(title='Error',
                                description='Failed to retrieve history',
                                color=0xff0000)
            embed.set_footer(text='up!history')
            await ctx.send(embed=embed)
        finally:
            conn.close()

async def setup(bot):
    await bot.add_cog(HistoryCog(bot))