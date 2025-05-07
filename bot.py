import platform
import psutil
import GPUtil
import sys
import subprocess
import time
import discord
import json
import aiohttp
import traceback
import re
import sqlite3
from datetime import datetime
from croniter import croniter
import os
from pytz import timezone
import asyncio
from discord import Intents
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

def init_db():
    conn = sqlite3.connect('monitoring.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS websites
                 (user_id TEXT, url TEXT, method TEXT, time_interval INTEGER, 
                  website_index INTEGER, stopped INTEGER, last_ping_time TEXT, 
                  response_status TEXT, PRIMARY KEY (user_id, url))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS last_status
                 (user_id TEXT, website_index TEXT, last_status TEXT, 
                  PRIMARY KEY (user_id, website_index))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS analytics_data
                 (user_id TEXT, website_index TEXT, error_count INTEGER, 
                  ping_count INTEGER, PRIMARY KEY (user_id, website_index))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS analytics
                 (user_id TEXT, website_index TEXT, response_times TEXT, 
                  average_response_time REAL, error_rate TEXT, uptime_percentage TEXT,
                  PRIMARY KEY (user_id, website_index))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS alerts
                 (user_id TEXT, website_index TEXT, alerts_on INTEGER,
                  PRIMARY KEY (user_id, website_index))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS history
                 (user_id TEXT, website_index TEXT, history TEXT,
                  PRIMARY KEY (user_id, website_index))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS schedules
                 (user_id TEXT, website_index TEXT, schedule TEXT,
                  PRIMARY KEY (user_id, website_index))''')
    
    conn.commit()
    conn.close()

init_db()

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='up!', intents=intents)
bot.activity = discord.Activity(type=discord.ActivityType.watching, name="Websites")
bot.ownerid = 920850442425102367
bot.adminid = {1139406664584409159, 920850442425102367}

def atomic_db_write(query, params=()):
    """Helper function for atomic database writes"""
    conn = None
    try:
        conn = sqlite3.connect('monitoring.db')
        c = conn.cursor()
        c.execute(query, params)
        conn.commit()
    except Exception as e:
        print(f"Database error: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

async def ping_website(url, method, time_interval, ping_count, user_id, website):
    conn = sqlite3.connect('monitoring.db')
    c = conn.cursor()
    c.execute('SELECT last_status FROM last_status WHERE user_id=? AND website_index=?', 
              (str(user_id), website['website_index']))
    last_status = c.fetchone()
    last_status = last_status[0] if last_status else None
    
    c.execute('SELECT error_count, ping_count FROM analytics_data WHERE user_id=? AND website_index=?',
              (str(user_id), website['website_index']))
    an_data = c.fetchone()
    error_count = an_data[0] if an_data else 0
    ping_count = an_data[1] if an_data else 0
    conn.close()

    asyncio.current_task().time_interval = time_interval

    async with aiohttp.ClientSession() as session:
        while True:
            start_time = time.time()
            try:
                if method == 'HEAD':
                    response = await session.head(url)
                elif method == 'GET':
                    response = await session.get(url)
                elif method == 'POST':
                    response = await session.post(url)
                
                response_time = round((time.time() - start_time) * 1000)
                now = datetime.now(timezone('Asia/Kolkata'))
                date_time = now.strftime("%d/%m/%y @ %I:%M %p")
                ping_count += 1
                log = f'{url}: {response.status} | Pinged on {date_time} (IST) | Ping count: {ping_count} | Response time: {response_time}ms'
                print(log)

                conn = sqlite3.connect('monitoring.db')
                c = conn.cursor()
                
                c.execute('SELECT response_times FROM analytics WHERE user_id=? AND website_index=?',
                          (str(user_id), website['website_index']))
                result = c.fetchone()
                response_times = json.loads(result[0]) if result and result[0] else []
                
                response_times.append(response_time)
                if len(response_times) > 15:
                    response_times.pop(0)
                average_response_time = round(sum(response_times) / len(response_times), 2)
                error_rate = round(error_count / ping_count * 100, 2)
                uptime_percentage = round((ping_count - error_count) / ping_count * 100, 2)
                
                atomic_db_write(
                    '''INSERT OR REPLACE INTO analytics 
                    (user_id, website_index, response_times, average_response_time, error_rate, uptime_percentage)
                    VALUES (?, ?, ?, ?, ?, ?)''',
                    (str(user_id), website['website_index'], json.dumps(response_times), 
                     average_response_time, f'{error_rate}%', f'{uptime_percentage}%'))
                
                status = 'UP' if response.status == 200 else 'DOWN'
                atomic_db_write(
                    '''INSERT OR REPLACE INTO last_status 
                    (user_id, website_index, last_status)
                    VALUES (?, ?, ?)''',
                    (str(user_id), website['website_index'], status))
                
                if status != last_status and last_status is not None:
                    c.execute('SELECT alerts_on FROM alerts WHERE user_id=? AND website_index=?',
                            (str(user_id), website['website_index']))
                    alert_setting = c.fetchone()
                    alerts_on = alert_setting[0] if alert_setting else True
                    
                    if alerts_on:
                        user = bot.get_user(int(user_id))
                        if status == 'UP':
                            embed = discord.Embed(title='WEBSITE UP', description=f'Website {website["website_index"]} is up.', color=0x00ff00)
                            embed.set_footer(text='Website up reminder || SiteLook alert system')
                            await user.send(embed=embed)
                        else:
                            embed = discord.Embed(title='WEBSITE DOWN', description=f'Website {website["website_index"]} is down.', color=0xff0000)
                            embed.set_footer(text='Website down reminder || SiteLook alert system')
                            await user.send(embed=embed)
                            error_count += 1
                    last_status = status
                
                c.execute('SELECT history FROM history WHERE user_id=? AND website_index=?',
                          (str(user_id), website['website_index']))
                result = c.fetchone()
                history = json.loads(result[0]) if result and result[0] else []
                
                history.append({'time': date_time, 'status': status})
                if len(history) > 15:
                    history.pop(0)
                
                atomic_db_write(
                    '''INSERT OR REPLACE INTO history 
                    (user_id, website_index, history)
                    VALUES (?, ?, ?)''',
                    (str(user_id), website['website_index'], json.dumps(history)))
                
                atomic_db_write(
                    '''UPDATE websites SET last_ping_time=?, response_status=?
                    WHERE user_id=? AND url=?''',
                    (date_time, f'{response.status} {response.reason}', str(user_id), url))
                
                atomic_db_write(
                    '''INSERT OR REPLACE INTO analytics_data 
                    (user_id, website_index, error_count, ping_count)
                    VALUES (?, ?, ?, ?)''',
                    (str(user_id), website['website_index'], error_count, ping_count))
                
                conn.close()

            except Exception as e:
                print(f'Error pinging {url}: {e}')
                if 'conn' in locals():
                    conn.close()

            await asyncio.sleep(time_interval)

async def send_requests():
    tasks = {}

    while True:
        conn = sqlite3.connect('monitoring.db')
        c = conn.cursor()
        c.execute('SELECT user_id, url, method, time_interval, website_index, stopped FROM websites')
        websites_data = c.fetchall()
        conn.close()
        
        websites = {}
        for user_id, url, method, time_interval, website_index, stopped in websites_data:
            if user_id not in websites:
                websites[user_id] = []
            websites[user_id].append({
                'url': url,
                'method': method,
                'time_interval': time_interval,
                'website_index': website_index,
                'stopped': stopped
            })

        for user_id, user_websites in websites.items():
            for website in user_websites:
                url = website['url']
                method = website['method']
                time_interval = website['time_interval']

                conn = sqlite3.connect('monitoring.db')
                c = conn.cursor()
                c.execute('SELECT schedule FROM schedules WHERE user_id=? AND website_index=?',
                         (user_id, website['website_index']))
                schedule = c.fetchone()
                conn.close()
                
                if schedule:
                    schedule = schedule[0]
                    now = datetime.now(timezone('Asia/Kolkata'))
                    iter = croniter(schedule, now)
                    next_run = iter.get_next(datetime)
                    if now < next_run:
                        continue

                if website.get('stopped'):
                    if url in tasks:
                        tasks[url].cancel()
                        del tasks[url]
                    continue

                if url not in tasks:
                    tasks[url] = asyncio.create_task(
                        ping_website(url, method, time_interval, 0, user_id, website))
                elif tasks[url].time_interval != time_interval:
                    tasks[url].cancel()
                    tasks[url] = asyncio.create_task(
                        ping_website(url, method, time_interval, 0, user_id, website))

        current_urls = {w['url'] for user_websites in websites.values() for w in user_websites}
        for url, task in list(tasks.items()):
            if url not in current_urls:
                task.cancel()
                del tasks[url]

        await asyncio.sleep(5)

bot.remove_command('help')

async def LoadCogs():
    for cog in os.listdir('Cogs'):
        cog_path = os.path.join('Cogs', cog)
        if os.path.isdir(cog_path) or not cog.endswith('.py'):
            continue
        try:
            await bot.load_extension(f'Cogs.{cog[:-3]}')
            print(f'Loaded extension {cog[:-3]}')
        except Exception as e:
            print(f'Failed to load {cog[:-3]}: {e}')

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    await LoadCogs()
    await send_requests()

bot.run(os.getenv("TOKEN"))