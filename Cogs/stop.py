import discord
import sqlite3
from discord.ext import commands

class StopCog(commands.Cog, name="stop command"):
    def __init__(self, bot):
        self.bot = bot

    def atomic_db_write(self, query, params=()):
        """Execute atomic database operation with rollback"""
        conn = None
        try:
            conn = sqlite3.connect('monitoring.db')
            c = conn.cursor()
            c.execute(query, params)
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Database error: {str(e)}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

    async def get_ordered_indexes(self, user_id):
        """Get website indexes in creation order"""
        conn = sqlite3.connect('monitoring.db')
        try:
            c = conn.cursor()
            c.execute('''SELECT website_index FROM websites 
                        WHERE user_id = ? 
                        ORDER BY rowid ASC''', (user_id,))
            return [row[0] for row in c.fetchall()]
        finally:
            conn.close()

    @commands.command()
    async def stop(self, ctx, index: str = None):
        """Pause monitoring for a website"""
        user_id = str(ctx.author.id)
        
        if not index:
            embed = discord.Embed(
                title='Error',
                description='Please include an index. Example: `up!stop 1`\nUse `up!stats` to view your websites.',
                color=0xff0000
            )
            embed.set_footer(text='up!stop')
            await ctx.send(embed=embed)
            return

        if not index.isdigit():
            embed = discord.Embed(
                title='Error',
                description='Index must be a positive number',
                color=0xff0000
            )
            embed.set_footer(text='up!stop')
            await ctx.send(embed=embed)
            return

        try:
            position = int(index)
            indexes = await self.get_ordered_indexes(user_id)
            
            if not indexes:
                raise ValueError("You have no websites to stop")
                
            if position < 1 or position > len(indexes):
                raise ValueError(f"Invalid index (1-{len(indexes)})")
                
            website_index = indexes[position - 1]
            
            conn = sqlite3.connect('monitoring.db')
            c = conn.cursor()
            c.execute('''SELECT stopped FROM websites 
                        WHERE user_id = ? AND website_index = ?''',
                     (user_id, website_index))
            result = c.fetchone()
            
            if not result:
                raise ValueError("Website not found")
                
            if result[0]:
                embed = discord.Embed(
                    title='Error',
                    description=f'Website #{position} is already paused',
                    color=0xff0000
                )
                embed.set_footer(text='up!stop')
                await ctx.send(embed=embed)
                return

            success = self.atomic_db_write(
                '''UPDATE websites SET stopped = 1 
                   WHERE user_id = ? AND website_index = ?''',
                (user_id, website_index)
            )
            
            if not success:
                raise RuntimeError("Failed to update database")

            embed = discord.Embed(
                title='Success',
                description=f'Paused monitoring for website #{position}',
                color=0x00ff00
            )
            embed.set_footer(text='up!stop')
            await ctx.send(embed=embed)

        except ValueError as e:
            error_msg = str(e)
            if "no websites" in error_msg.lower():
                description = 'You have no websites to pause'
            else:
                description = error_msg
                
            embed = discord.Embed(
                title='Error',
                description=description,
                color=0xff0000
            )
            embed.set_footer(text='up!stop')
            await ctx.send(embed=embed)
            
        except Exception as e:
            print(f"Stop command error: {str(e)}")
            embed = discord.Embed(
                title='Error',
                description='Failed to pause monitoring',
                color=0xff0000
            )
            embed.set_footer(text='up!stop')
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(StopCog(bot))