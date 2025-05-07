import discord
import sqlite3
from discord.ext import commands
from discord.ext.menus import MenuPages, ListPageSource

class StatsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ITEMS_PER_PAGE = 10

    class StatsMenu(ListPageSource):
        def __init__(self, data, user):
            super().__init__(data, per_page=10)
            self.user = user

        async def format_page(self, menu, entries):
            embed = discord.Embed(title=f"Monitoring Stats ({menu.current_page + 1}/{self.get_max_pages()})", 
                                 color=0x00ff00)
            description = []
            for idx, website in enumerate(entries, start=menu.current_page * self.per_page + 1):
                desc_line = (
                    f"**{idx}.** `{website['method']}` {self.truncate(website['url'], 40)}\n"
                    f"↳ Last ping: {website['last_ping_time'] or 'Never'}\n"
                    f"↳ Status: {website['response_status'] or 'Unknown'}\n"
                )
                description.append(desc_line)
            
            embed.description = '\n'.join(description)
            embed.set_footer(text=f"Requested by {self.user.name} | up!stats")
            return embed

        @staticmethod
        def truncate(text, max_length):
            return (text[:max_length-3] + '...') if len(text) > max_length else text

    def get_db_connection(self):
        """Create and return a database connection with row factory"""
        conn = sqlite3.connect('monitoring.db')
        conn.row_factory = sqlite3.Row
        return conn

    @commands.command()
    async def stats(self, ctx):
        """View your monitored website statistics"""
        user_id = str(ctx.author.id)
        
        try:
            conn = self.get_db_connection()
            c = conn.cursor()
            
            c.execute('''SELECT url, method, last_ping_time, response_status 
                        FROM websites 
                        WHERE user_id = ? 
                        ORDER BY rowid ASC''', (user_id,))
            
            websites = [dict(row) for row in c.fetchall()]
            
            if not websites:
                embed = discord.Embed(title='Error',
                                     description='You have no monitored websites',
                                     color=0xff0000)
                embed.set_footer(text='up!stats')
                await ctx.send(embed=embed)
                return

            pages = MenuPages(source=self.StatsMenu(websites, ctx.author), 
                                   clear_reactions_after=True)
            
            try:
                await pages.start(ctx, channel=ctx.author.dm_channel or await ctx.author.create_dm())
                if not isinstance(ctx.channel, discord.DMChannel):
                    await ctx.send(f"{ctx.author.mention} Check your DMs for monitoring stats!")
            except discord.Forbidden:
                embed = discord.Embed(title='Error',
                                     description="Couldn't send DMs. Please enable DMs and try again.",
                                     color=0xff0000)
                await ctx.send(embed=embed)

        except sqlite3.Error as e:
            print(f"Database error in stats: {str(e)}")
            embed = discord.Embed(title='Error',
                                 description='Failed to retrieve stats. Please try again later.',
                                 color=0xff0000)
            await ctx.send(embed=embed)
        except Exception as e:
            print(f"Unexpected error in stats: {str(e)}")
            embed = discord.Embed(title='Error',
                                 description='An unexpected error occurred.',
                                 color=0xff0000)
            await ctx.send(embed=embed)
        finally:
            conn.close()

async def setup(bot):
    await bot.add_cog(StatsCog(bot))