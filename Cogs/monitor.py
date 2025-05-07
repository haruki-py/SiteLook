import discord
import sqlite3
import re
from discord.ext import commands

class MonitorCog(commands.Cog, name="monitor command"):
    def __init__(self, bot):
        self.bot = bot
        self.FACTOR = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400, 'w': 604800}

    def atomic_db_write(self, query, params=()):
        """Execute atomic database write operation"""
        conn = None
        try:
            conn = sqlite3.connect('monitoring.db')
            c = conn.cursor()
            c.execute(query, params)
            conn.commit()
            return True
        except Exception as e:
            print(f"Database error: {str(e)}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

    async def get_next_index(self, user_id):
        """Get next available index for user's websites"""
        conn = sqlite3.connect('monitoring.db')
        try:
            c = conn.cursor()
            c.execute('''SELECT MAX(website_index) FROM websites 
                       WHERE user_id = ?''', (user_id,))
            max_index = c.fetchone()[0]
            return (max_index or 0) + 1
        finally:
            conn.close()

    @commands.command()
    async def monitor(self, ctx):
        """Add a new website to monitor"""
        if len(ctx.message.content.split()) < 2:
            embed = discord.Embed(
                title='Error',
                description='Please include a website URL. Example: `up!monitor https://example.com`',
                color=0xff0000
            )
            embed.set_footer(text='up!monitor')
            await ctx.send(embed=embed)
            return

        website = ctx.message.content.split()[1].strip()
        user_id = str(ctx.author.id)

        conn = sqlite3.connect('monitoring.db')
        try:
            c = conn.cursor()
            c.execute('''SELECT 1 FROM websites 
                        WHERE user_id = ? AND url COLLATE NOCASE = ?''',
                     (user_id, website))
            if c.fetchone():
                embed = discord.Embed(
                    title='Error',
                    description='This website is already being monitored',
                    color=0xff0000
                )
                embed.set_footer(text='up!monitor')
                await ctx.send(embed=embed)
                return
        finally:
            conn.close()

        try:
            method = await self.get_http_method(ctx)
            if not method:
                return
        except Exception as e:
            print(f"Method selection error: {str(e)}")
            return

        try:
            seconds = await self.get_time_interval(ctx)
            if not seconds:
                return
        except Exception as e:
            print(f"Interval error: {str(e)}")
            return

        try:
            new_index = await self.get_next_index(user_id)
        except Exception as e:
            print(f"Index error: {str(e)}")
            embed = discord.Embed(
                title='Error',
                description='Failed to generate website index',
                color=0xff0000
            )
            embed.set_footer(text='up!monitor')
            await ctx.send(embed=embed)
            return

        success = self.atomic_db_write(
            '''INSERT INTO websites 
               (user_id, url, method, time_interval, website_index, stopped) 
               VALUES (?, ?, ?, ?, ?, 0)''',
            (user_id, website, method, seconds, new_index)
        )

        if not success:
            embed = discord.Embed(
                title='Error',
                description='Failed to save website configuration',
                color=0xff0000
            )
            embed.set_footer(text='up!monitor')
            await ctx.send(embed=embed)
            return

        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

        embed = discord.Embed(
            title='Success',
            description=f'Now monitoring {website} (#{new_index})',
            color=0x00ff00
        )
        embed.set_footer(text='up!monitor')
        await ctx.send(embed=embed)

    async def get_http_method(self, ctx):
        """Get HTTP method from user"""
        embed = discord.Embed(
            title='Method',
            description='Choose monitoring method:\n1. HEAD\n2. GET\n3. POST',
            color=0x00ff00
        )
        embed.set_footer(text='up!monitor')
        msg = await ctx.send(embed=embed)

        try:
            response = await self.bot.wait_for(
                'message',
                timeout=30.0,
                check=lambda m: m.author == ctx.author and 
                               m.channel == ctx.channel and 
                               m.content in ['1', '2', '3']
            )
            return ['HEAD', 'GET', 'POST'][int(response.content)-1]
        except asyncio.TimeoutError:
            embed = discord.Embed(
                title='Error',
                description='Response timed out',
                color=0xff0000
            )
            embed.set_footer(text='up!monitor')
            await msg.edit(embed=embed)
            return None

    async def get_time_interval(self, ctx):
        """Get and validate time interval"""
        embed = discord.Embed(
            title='Interval',
            description='Enter monitoring interval (e.g., 5m, 1h):\nMinimum 60 seconds',
            color=0x00ff00
        )
        embed.set_footer(text='up!monitor')
        msg = await ctx.send(embed=embed)

        try:
            response = await self.bot.wait_for(
                'message',
                timeout=30.0,
                check=lambda m: m.author == ctx.author and 
                               m.channel == ctx.channel and 
                               re.match(r'^\d+(\.\d+)?[smhdw]$', m.content)
            )
            interval = response.content.strip().lower()
            unit = interval[-1]
            number = float(interval[:-1])
            seconds = number * self.FACTOR[unit]
            
            if seconds < 60:
                raise ValueError('Minimum interval is 1 minute')
                
            return int(seconds)
            
        except ValueError as e:
            embed = discord.Embed(
                title='Error',
                description=str(e),
                color=0xff0000
            )
            embed.set_footer(text='up!monitor')
            await msg.edit(embed=embed)
            return None
        except asyncio.TimeoutError:
            embed = discord.Embed(
                title='Error',
                description='Response timed out',
                color=0xff0000
            )
            embed.set_footer(text='up!monitor')
            await msg.edit(embed=embed)
            return None

async def setup(bot):
    await bot.add_cog(MonitorCog(bot))