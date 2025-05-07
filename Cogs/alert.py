import discord
import sqlite3
from discord.ext import commands
import asyncio

class AlertCog(commands.Cog, name="alert "):
    def __init__(self, bot):
        self.bot = bot

    def atomic_db_write(self, query, params=()):
        """Helper function for atomic database writes"""
        conn = None
        try:
            conn = sqlite3.connect('monitoring.db')
            c = conn.cursor()
            c.execute(query, params)
            conn.commit()
            return True
        except Exception as e:
            print(f"Database error: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

    @commands.command()
    async def alert(self, ctx):
        conn = sqlite3.connect('monitoring.db')
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM websites WHERE user_id = ?', (str(ctx.author.id),))
        website_count = c.fetchone()[0]
        conn.close()
        
        if website_count == 0:
            embed = discord.Embed(title='Error', 
                                 description='You do not have any websites to monitor.', 
                                 color=0xff0000)
            embed.set_footer(text='up!alert')
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(title='Website', 
                             description='Which website do you want to set an alert for? Reply with your website index. If you don\'t know the index, please use up!stats.', 
                             color=0x00ff00)
        embed.set_footer(text='up!alert')
        await ctx.send(embed=embed)

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()
        
        try:
            response = await self.bot.wait_for('message', check=check, timeout=30.0)
        except asyncio.TimeoutError:
            embed = discord.Embed(title='Error', 
                                 description='Sorry, you took too long to respond.', 
                                 color=0xff0000)
            embed.set_footer(text='up!alert')
            await ctx.send(embed=embed)
            return

        try:
            position = int(response.content)
            if position < 1:
                raise ValueError
        except ValueError:
            embed = discord.Embed(title='Error', 
                                 description='Please enter a valid positive number.', 
                                 color=0xff0000)
            embed.set_footer(text='up!alert')
            await ctx.send(embed=embed)
            return

        conn = sqlite3.connect('monitoring.db')
        c = conn.cursor()
        c.execute('SELECT website_index FROM websites WHERE user_id = ? ORDER BY website_index ASC', 
                  (str(ctx.author.id),))
        indexes = [row[0] for row in c.fetchall()]
        conn.close()

        if position > len(indexes):
            embed = discord.Embed(title='Error', 
                                 description=f'Invalid index. You have {len(indexes)} monitored websites.', 
                                 color=0xff0000)
            embed.set_footer(text='up!alert')
            await ctx.send(embed=embed)
            return

        website_index = indexes[position - 1]

        conn = sqlite3.connect('monitoring.db')
        c = conn.cursor()
        c.execute('SELECT alerts_on FROM alerts WHERE user_id = ? AND website_index = ?', 
                  (str(ctx.author.id), website_index))
        result = c.fetchone()
        alerts_on = result[0] if result else True
        conn.close()

        embed = discord.Embed(title='Alerts', 
                             description=f'Do you want to turn alerts on or off for this website?', 
                             color=0x00ff00)
        embed.set_footer(text='up!alert')
        await ctx.send(embed=embed)

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ['on', 'off']
        
        try:
            response = await self.bot.wait_for('message', check=check, timeout=30.0)
        except asyncio.TimeoutError:
            embed = discord.Embed(title='Error', 
                                 description='Sorry, you took too long to respond.', 
                                 color=0xff0000)
            embed.set_footer(text='up!alert')
            await ctx.send(embed=embed)
            return

        new_setting = response.content.lower() == 'on'

        if new_setting == alerts_on:
            status = "on" if alerts_on else "off"
            embed = discord.Embed(title='Error', 
                                 description=f'Website {position} already has alerts turned {status}.', 
                                 color=0xff0000)
            embed.set_footer(text='up!alert')
            await ctx.send(embed=embed)
            return

        success = self.atomic_db_write(
            '''INSERT OR REPLACE INTO alerts 
               (user_id, website_index, alerts_on) 
               VALUES (?, ?, ?)''',
            (str(ctx.author.id), website_index, new_setting)
        )

        if not success:
            embed = discord.Embed(title='Error', 
                                 description='Failed to update alert settings. Please try again.', 
                                 color=0xff0000)
            embed.set_footer(text='up!alert')
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(title='Success', 
                             description=f'Alerts turned {response.content} for website {position}', 
                             color=0x00ff00)
        embed.set_footer(text='up!alert')
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AlertCog(bot))