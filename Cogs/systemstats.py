import discord
from discord.ext import commands
import psutil
import GPUtil
import platform
import subprocess

class SystemstatsCog(commands.Cog, name="systemstats command"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='systemstats')
    async def systemstats(self, ctx):
        if ctx.author.id not in self.bot.adminid or ctx.author.id != self.bot.ownerid:
            return

        cpu_freq = psutil.cpu_freq()
        virtual_memory = psutil.virtual_memory()
        disk_usage = psutil.disk_usage('/')
        
        os_info = platform.uname()
        os_name = platform.system()
        os_version = platform.release()
        
        if os_info.system == "Windows":
            cpu_model = platform.processor()
        else:
            cpu_model = subprocess.getoutput("cat /proc/cpuinfo | grep 'model name' | head -1 | cut -d ':' -f 2").strip()
        
        try:
            GPUs = GPUtil.getGPUs()
            if GPUs:
                gpu_info = ', '.join([gpu.name for gpu in GPUs])
            else:
                gpu_info = 'No GPU found or unable to retrieve GPU information'
        except Exception as e:
            gpu_info = f'Error retrieving GPU information: {str(e)}'

        embed = discord.Embed(title='System Stats', color=0x00ff00)
        embed.add_field(name='OS', value=os_name, inline=True)
        embed.add_field(name='OS Version', value=os_version, inline=True)
        embed.add_field(name='Python Version', value=platform.python_version(), inline=True)
        embed.add_field(name='CPU Model', value=cpu_model, inline=True)
        embed.add_field(name='CPU Cores', value=f'{psutil.cpu_count(logical=False)} physical, {psutil.cpu_count(logical=True)} total', inline=True)
        embed.add_field(name='CPU Clock Speed', value=f'{cpu_freq.current:.2f} MHz', inline=True)
        embed.add_field(name='CPU Usage', value=f'{psutil.cpu_percent()}%', inline=True)
        embed.add_field(name='Total RAM', value=f'{virtual_memory.total / (1024 ** 3):.2f} GB', inline=True)
        embed.add_field(name='Used RAM', value=f'{virtual_memory.used / (1024 ** 3):.2f} GB ({virtual_memory.percent}%)', inline=True)
        embed.add_field(name='Total Disk Space', value=f'{disk_usage.total / (1024 ** 3):.2f} GB', inline=True)
        embed.add_field(name='Used Disk Space', value=f'{disk_usage.used / (1024 ** 3):.2f} GB ({disk_usage.percent}%)', inline=True)
        embed.add_field(name='GPU', value=gpu_info, inline=True)

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(SystemstatsCog(bot))
