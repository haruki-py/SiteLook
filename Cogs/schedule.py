import discord
import sqlite3
from discord.ext import commands
from croniter import croniter
import asyncio

class ScheduleCog(commands.Cog, name="schedule command"):
    def __init__(self, bot):
        self.bot = bot

    def atomic_db_write(self, query, params=()):
        """Execute atomic database operation"""
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

    async def validate_website_index(self, ctx, user_id, index):
        """Validate website index exists for user"""
        conn = sqlite3.connect('monitoring.db')
        try:
            c = conn.cursor()
            c.execute('''SELECT 1 FROM websites 
                        WHERE user_id = ? AND website_index = ?''',
                     (user_id, index))
            return c.fetchone() is not None
        finally:
            conn.close()

    @commands.command()
    async def schedule(self, ctx, index: str = None, *, schedule: str = None):
        """Set monitoring schedule for a website"""
        user_id = str(ctx.author.id)
        
        if not index:
            embed = discord.Embed(
                title='Index',
                description='Which monitor to schedule? Enter index:',
                color=0x00ff00
            )
            embed.set_footer(text='up!schedule')
            msg = await ctx.send(embed=embed)
            
            try:
                response = await self.bot.wait_for(
                    'message',
                    timeout=30.0,
                    check=lambda m: m.author == ctx.author and 
                                   m.channel == ctx.channel and 
                                   m.content.isdigit()
                )
                index = response.content
            except asyncio.TimeoutError:
                embed = discord.Embed(
                    title='Error',
                    description='Response timed out',
                    color=0xff0000
                )
                embed.set_footer(text='up!schedule')
                await msg.edit(embed=embed)
                return

        if not index.isdigit():
            embed = discord.Embed(
                title='Error',
                description='Index must be a number',
                color=0xff0000
            )
            embed.set_footer(text='up!schedule')
            await ctx.send(embed=embed)
            return
            
        if not await self.validate_website_index(ctx, user_id, index):
            embed = discord.Embed(
                title='Error',
                description='Invalid monitor index',
                color=0xff0000
            )
            embed.set_footer(text='up!schedule')
            await ctx.send(embed=embed)
            return

        if not schedule:
            embed = discord.Embed(
                title='Schedule',
                description='Enter cron schedule (e.g., `*/5 * * * *` for every 5 minutes):',
                color=0x00ff00
            )
            embed.set_footer(text='up!schedule')
            msg = await ctx.send(embed=embed)
            
            try:
                response = await self.bot.wait_for(
                    'message',
                    timeout=30.0,
                    check=lambda m: m.author == ctx.author and 
                                   m.channel == ctx.channel
                )
                schedule = response.content.strip()
            except asyncio.TimeoutError:
                embed = discord.Embed(
                    title='Error',
                    description='Response timed out',
                    color=0xff0000
                )
                embed.set_footer(text='up!schedule')
                await msg.edit(embed=embed)
                return

        if not croniter.is_valid(schedule):
            embed = discord.Embed(
                title='Error',
                description='Invalid cron format. Example: `*/5 * * * *` (every 5 minutes)',
                color=0xff0000
            )
            embed.set_footer(text='up!schedule')
            await ctx.send(embed=embed)
            return

        success = self.atomic_db_write(
            '''INSERT OR REPLACE INTO schedules 
               (user_id, website_index, schedule) 
               VALUES (?, ?, ?)''',
            (user_id, index, schedule)
        )

        if success:
            embed = discord.Embed(
                title='Success',
                description=f'Schedule set for monitor #{index}',
                color=0x00ff00
            )
            embed.add_field(name='Cron Schedule', value=f'`{schedule}`')
            embed.set_footer(text='up!schedule')
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title='Error',
                description='Failed to save schedule',
                color=0xff0000
            )
            embed.set_footer(text='up!schedule')
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(ScheduleCog(bot))