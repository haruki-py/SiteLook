import discord
import sqlite3
from discord.ext import commands

class RemoveCog(commands.Cog, name="remove command"):
    def __init__(self, bot):
        self.bot = bot

    def atomic_db_operation(self, queries):
        """Execute multiple SQL queries in a transaction"""
        conn = None
        try:
            conn = sqlite3.connect('monitoring.db')
            c = conn.cursor()
            
            for query, params in queries:
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
                     (str(user_id),))
            return [row[0] for row in c.fetchall()]
        finally:
            conn.close()

    @commands.command()
    async def remove(self, ctx):
        """Remove a monitored website"""
        if len(ctx.message.content.split()) < 2:
            embed = discord.Embed(
                title='Error',
                description='Please include an index to remove. Example: `up!remove 1`\n'
                            'Use `up!stats` to view your monitored websites.',
                color=0xff0000
            )
            embed.set_footer(text='up!remove')
            await ctx.send(embed=embed)
            return

        user_id = str(ctx.author.id)
        arg = ctx.message.content.split()[1]
        
        if not arg.isdigit():
            embed = discord.Embed(
                title='Error',
                description='Index must be a number. Example: `up!remove 1`',
                color=0xff0000
            )
            embed.set_footer(text='up!remove')
            await ctx.send(embed=embed)
            return

        try:
            position = int(arg)
            indexes = await self.get_ordered_website_indexes(user_id)
            
            if not indexes:
                raise ValueError("No websites to remove")
            if position < 1 or position > len(indexes):
                raise ValueError(f"Invalid index (1-{len(indexes)})")
                
            website_index = indexes[position - 1]
            
            cleanup_queries = [
                ('DELETE FROM websites WHERE user_id = ? AND website_index = ?', (user_id, website_index)),
                ('DELETE FROM alerts WHERE user_id = ? AND website_index = ?', (user_id, website_index)),
                ('DELETE FROM analytics WHERE user_id = ? AND website_index = ?', (user_id, website_index)),
                ('DELETE FROM history WHERE user_id = ? AND website_index = ?', (user_id, website_index)),
                ('DELETE FROM schedules WHERE user_id = ? AND website_index = ?', (user_id, website_index)),
                ('DELETE FROM last_status WHERE user_id = ? AND website_index = ?', (user_id, website_index))
            ]
            
            success = self.atomic_db_operation(cleanup_queries)
            
            if not success:
                raise Exception("Failed to complete database operations")

            if not isinstance(ctx.channel, discord.channel.DMChannel):
                try:
                    await ctx.message.delete()
                except discord.Forbidden:
                    pass

            embed = discord.Embed(
                title='Success',
                description=f'Removed website #{position}',
                color=0x00ff00
            )
            embed.set_footer(text='up!remove')
            await ctx.send(embed=embed)

        except ValueError as e:
            error_msg = str(e)
            if "No websites" in error_msg:
                description = 'You have no websites to remove'
            else:
                description = f'Invalid index: {error_msg}'
                
            embed = discord.Embed(
                title='Error',
                description=description,
                color=0xff0000
            )
            embed.set_footer(text='up!remove')
            await ctx.send(embed=embed)

        except Exception as e:
            print(f"Remove error: {str(e)}")
            embed = discord.Embed(
                title='Error',
                description='Failed to remove website. Please try again.',
                color=0xff0000
            )
            embed.set_footer(text='up!remove')
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(RemoveCog(bot))