import discord
import sqlite3
import json
from discord.ext import commands
import asyncio

class AnalyticsCog(commands.Cog, name="analytics command"):
    def __init__(self, bot):
        self.bot = bot

    def get_db_connection(self):
        """Create and return a database connection with row factory"""
        conn = sqlite3.connect('monitoring.db')
        conn.row_factory = sqlite3.Row
        return conn

    @commands.command()
    async def analytics(self, ctx, index: str = None):
        """Display analytics for a monitored website"""
        conn = self.get_db_connection()
        try:
            c = conn.cursor()
            c.execute('SELECT COUNT(*) FROM websites WHERE user_id = ?', (str(ctx.author.id),))
            if c.fetchone()[0] == 0:
                embed = discord.Embed(title='Error', 
                                    description='You have no monitored websites', 
                                    color=0xff0000)
                embed.set_footer(text='up!analytics')
                await ctx.send(embed=embed)
                return
        finally:
            conn.close()

        if not index:
            embed = discord.Embed(title='Index', 
                                description='Which monitor do you want to view analytics for? Enter the index:', 
                                color=0x00ff00)
            embed.set_footer(text='up!analytics')
            await ctx.send(embed=embed)

            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()
            
            try:
                response = await self.bot.wait_for('message', check=check, timeout=30.0)
                index = response.content
            except asyncio.TimeoutError:
                embed = discord.Embed(title='Error', 
                                    description='Response timed out', 
                                    color=0xff0000)
                embed.set_footer(text='up!analytics')
                await ctx.send(embed=embed)
                return

        if not index.isdigit():
            embed = discord.Embed(title='Error', 
                                description='Index must be a number', 
                                color=0xff0000)
            embed.set_footer(text='up!analytics')
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
                embed.set_footer(text='up!analytics')
                await ctx.send(embed=embed)
                return
                
            website_index = indexes[position - 1]
            
            c.execute('''SELECT response_times, average_response_time, 
                        error_rate, uptime_percentage 
                        FROM analytics WHERE user_id = ? AND website_index = ?''',
                     (str(ctx.author.id), website_index))
            analytics = c.fetchone()
            
            if not analytics:
                embed = discord.Embed(title='Analytics', 
                                     description=f'No data for monitor {position}', 
                                     color=0x00ff00)
                embed.set_footer(text='up!analytics')
                await ctx.send(embed=embed)
                return

            response_times = json.loads(analytics['response_times']) if analytics['response_times'] else []
            avg_response = analytics['average_response_time'] or 0
            error_rate = analytics['error_rate'] or "0%"
            uptime = analytics['uptime_percentage'] or "100%"

            analytics_msg = (
                f"Average response: {avg_response:.2f}ms\n"
                f"Last 15 responses: {', '.join(map(str, response_times[-15:])) or 'No data'}\n"
                f"Error rate: {error_rate}\n"
                f"Uptime: {uptime}"
            )
            
            embed = discord.Embed(title=f'Analytics for Monitor #{position}', 
                                 description=analytics_msg, 
                                 color=0x00ff00)
            embed.set_footer(text='up!analytics')
            await ctx.send(embed=embed)

        except json.JSONDecodeError:
            embed = discord.Embed(title='Error', 
                                 description='Could not load response data', 
                                 color=0xff0000)
            embed.set_footer(text='up!analytics')
            await ctx.send(embed=embed)
        except Exception as e:
            print(f"Analytics error: {e}")
            embed = discord.Embed(title='Error', 
                                 description='Failed to retrieve analytics', 
                                 color=0xff0000)
            embed.set_footer(text='up!analytics')
            await ctx.send(embed=embed)
        finally:
            conn.close()

async def setup(bot):
    await bot.add_cog(AnalyticsCog(bot))