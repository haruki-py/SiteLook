import discord
import sqlite3
from discord.ext import commands

class StartCog(commands.Cog, name="start command"):
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

    async def get_ordered_website_indexes(self, user_id):
        """Get website indexes in creation order"""
        conn = sqlite3.connect('monitoring.db')
        try:
            c = conn.cursor()
            c.execute('SELECT website_index FROM websites WHERE user_id = ? ORDER BY rowid ASC', 
                     (user_id,))
            return [row[0] for row in c.fetchall()]
        finally:
            conn.close()

    @commands.command()
    async def start(self, ctx, index: str = None):
        """Resume monitoring for a website"""
        user_id = str(ctx.author.id)
        
        if not index:
            embed = discord.Embed(
                title='Error',
                description='Please include an index. Example: `up!start 1`\n'
                            'Use `up!stats` to view your websites.',
                color=0xff0000
            )
            embed.set_footer(text='up!start')
            await ctx.send(embed=embed)
            return

        if not index.isdigit():
            embed = discord.Embed(
                title='Error',
                description='Index must be a number',
                color=0xff0000
            )
            embed.set_footer(text='up!start')
            await ctx.send(embed=embed)
            return

        try:
            position = int(index)
            indexes = await self.get_ordered_website_indexes(user_id)
            
            if not indexes:
                raise ValueError("You have no websites to start")
            if position < 1 or position > len(indexes):
                raise ValueError(f"Invalid index (1-{len(indexes)})")
                
            website_index = indexes[position - 1]
            
            conn = sqlite3.connect('monitoring.db')
            c = conn.cursor()
            c.execute('SELECT stopped FROM websites WHERE user_id = ? AND website_index = ?',
                     (user_id, website_index))
            result = c.fetchone()
            
            if not result:
                raise ValueError("Website not found")
                
            if not result[0]:
                embed = discord.Embed(
                    title='Error',
                    description=f'Website #{position} is already active',
                    color=0xff0000
                )
                embed.set_footer(text='up!start')
                await ctx.send(embed=embed)
                return

            success = self.atomic_db_write(
                'UPDATE websites SET stopped = 0 WHERE user_id = ? AND website_index = ?',
                (user_id, website_index)
            )
            
            if not success:
                raise Exception("Database update failed")

            embed = discord.Embed(
                title='Success',
                description=f'Resumed monitoring for website #{position}',
                color=0x00ff00
            )
            embed.set_footer(text='up!start')
            await ctx.send(embed=embed)

        except ValueError as e:
            error_msg = str(e)
            if "no websites" in error_msg.lower():
                description = 'You have no websites to start'
            else:
                description = error_msg
                
            embed = discord.Embed(
                title='Error',
                description=description,
                color=0xff0000
            )
            embed.set_footer(text='up!start')
            await ctx.send(embed=embed)
            
        except Exception as e:
            print(f"Start error: {str(e)}")
            embed = discord.Embed(
                title='Error',
                description='Failed to start monitoring',
                color=0xff0000
            )
            embed.set_footer(text='up!start')
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(StartCog(bot))