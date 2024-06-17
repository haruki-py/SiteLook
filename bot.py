# from webapp import keep_alive
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
from datetime import datetime
from croniter import croniter
import os
from pytz import timezone
import asyncio
from discord import Intents
from discord.ext import commands

ownerid = 920850442425102367
adminid = [1139406664584409159, 920850442425102367]

intents = discord.Intents.all()
# intents.message_content = True
# intents.members = True
client = commands.Bot(command_prefix='up!', intents=intents)
client.activity = discord.Activity (type=discord.ActivityType.watching, name="Websites")

#  keep_alive()

# Define a function to ping a website with a given method and time interval
async def ping_website(url, method, time_interval, ping_count, user_id, website):
    # Load the last_status value from the ls.json file
    with open('ls.json', 'r') as f:
        ls_data = json.load(f)
    user_ls_data = ls_data.get(str(user_id), {})
    monitor_ls_data = user_ls_data.get(website['index'], {})
    last_status = monitor_ls_data.get('last_status', None)

    # Load the error_count and ping_count values from the an_data.json file
    with open('an_data.json', 'r') as f:
        an_data = json.load(f)
    user_an_data = an_data.get(str(user_id), {})
    monitor_an_data = user_an_data.get(website['index'], {})
    error_count = monitor_an_data.get('error_count', 0)
    ping_count = monitor_an_data.get('ping_count', 0)

    # Set the time_interval attribute on the current task
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

                # Update the analytics data for this monitor
                with open('analytics.json', 'r') as f:
                    analytics = json.load(f)
                user_analytics = analytics.get(str(user_id), {})
                monitor_analytics = user_analytics.get(website['index'], {})
                response_times = monitor_analytics.get('response_times', [])
                response_times.append(response_time)
                if len(response_times) > 15:
                    response_times.pop(0)
                average_response_time = round(sum(response_times) / len(response_times), 2)
                monitor_analytics['average_response_time'] = average_response_time
                error_rate = round(error_count / ping_count * 100, 2)
                monitor_analytics['error_rate'] = f'{error_rate}%'
                uptime_percentage = round((ping_count - error_count) / ping_count * 100, 2)
                monitor_analytics['uptime_percentage'] = f'{uptime_percentage}%'
                user_analytics[website['index']] = monitor_analytics
                analytics[str(user_id)] = user_analytics
                with open('analytics.json', 'w') as f:
                    json.dump(analytics, f)

                # Update the ls.json file with the last ping status
                status = 'UP' if response.status == 200 else 'DOWN'
                user_ls_data = ls_data.setdefault(str(user_id), {})
                monitor_ls_data = user_ls_data.setdefault(website['index'], {})
                monitor_ls_data['last_status'] = status
                with open('ls.json', 'w') as f:
                    json.dump(ls_data, f)

                # Check if the status of the website has changed
                if status != last_status and last_status is not None:
                    # Check if alerts are turned on for this website
                    with open('alerts.json', 'r') as f:
                        alerts = json.load(f)
                    user_alerts = alerts.get(str(user_id), {})
                    alerts_on = user_alerts.get(website['index'], True)
                    if alerts_on:
                        user = client.get_user(int(user_id))
                        if status == 'UP':
                            embed = discord.Embed(title='WEBSITE UP', description=f'Website {website["index"]} is up.', color=0x00ff00)
                            embed.set_footer(text='Website up reminder || SiteLook alert system')
                            await user.send(embed=embed)
                        else:
                            embed = discord.Embed(title='WEBSITE DOWN', description=f'Website {website["index"]} is down.', color=0xff0000)
                            embed.set_footer(text='Website down reminder || SiteLook alert system')
                            await user.send(embed=embed)
                            error_count += 1
                    last_status = status

                # Store information about the monitor status change in the history.json file
                with open('history.json', 'r') as f:
                    history = json.load(f)
                user_history = history.get(str(user_id), {})
                monitor_history = user_history.get(website['index'], [])
                monitor_history.append({'time': date_time, 'status': status})
                if len(monitor_history) > 15:
                    monitor_history.pop(0)
                user_history[website['index']] = monitor_history
                history[str(user_id)] = user_history
                with open('history.json', 'w') as f:
                    json.dump(history, f)

                # Store the last ping time and response status in the websites.json file
                with open('websites.json', 'r') as f:
                    websites = json.load(f)
                    for user_id, user_websites in websites.items():
                        for website in user_websites:
                            if website['url'] == url:
                                website['last_ping_time'] = date_time
                                website['response_status'] = f'{response.status} {response.reason}'
                                break
                with open('websites.json', 'w') as f:
                    json.dump(websites, f)

                # Save the error_count and ping_count values to the an_data.json file
                monitor_an_data['error_count'] = error_count
                monitor_an_data['ping_count'] = ping_count
                user_an_data[website['index']] = monitor_an_data
                an_data[str(user_id)] = user_an_data
                with open('an_data.json', 'w') as f:
                    json.dump(an_data, f)

            except Exception as e:
                print(f'Error pinging {url}: {e}')

            # Wait for the time interval before pinging again
            await asyncio.sleep(time_interval)

async def send_requests():
    ping_count = {}

    # Create a dictionary to store the tasks for each website
    tasks = {}

    while True:

        # Check if there are any new websites added or removed from the file
        with open('websites.json', 'r') as f:
            websites = json.load(f)

            # Loop through the websites for each user
            for user_id, user_websites in websites.items():

                # Loop through the websites for each user
                for website in user_websites:

                    # Get the url, method and time interval of the website
                    url = website['url']
                    method = website['method']
                    time_interval = website['time_interval']

                    # Check if the monitor is scheduled to run
                    with open('schedules.json', 'r') as f:
                        schedules = json.load(f)
                    user_schedules = schedules.get(user_id, {})
                    schedule = user_schedules.get(website.get('index', None))
                    if schedule:
                        now = datetime.now(timezone('Asia/Kolkata'))
                        iter = croniter(schedule, now)
                        next_run = iter.get_next(datetime)
                        if now < next_run:
                            continue

                    # If the website is stopped, cancel its task if it exists
                    if 'stopped' in website and website['stopped']:
                        if url in tasks:
                            tasks[url].cancel()
                            del tasks[url]
                        continue

                    # If the url is not in the tasks dictionary, create a new task for it
                    if url not in tasks:
                        tasks[url] = asyncio.create_task(ping_website(url, method, time_interval, ping_count, user_id, website))

                    # If the url is in the tasks dictionary, but the time interval has changed, cancel the old task and create a new one
                    elif tasks[url].time_interval != time_interval:
                        tasks[url].cancel()
                        tasks[url] = asyncio.create_task(ping_website(url, method, time_interval, ping_count, user_id, website))

            # Loop through the tasks dictionary and cancel any task that is not in the file anymore
            for url, task in list(tasks.items()):
                if not any(url == website['url'] for user_websites in websites.values() for website in user_websites):
                    task.cancel()
                    del tasks[url]

        # Wait for 5 seconds before checking the file again
        await asyncio.sleep(5)

client.remove_command('help')

# Load cogs
path = os.path.realpath(__file__)
path = path.replace('\\', '/')
path = path.replace('bot.py', 'Commands')
initial_extensions = os.listdir(path)
try:
    initial_extensions.remove("__pycache__")
except:
    pass
print(initial_extensions)
initial_extensions3 = []
for initial_extensions2 in initial_extensions:
    initial_extensions2 = "Commands." + initial_extensions2
    initial_extensions2 = initial_extensions2.replace(".py", "")
    initial_extensions3.append(initial_extensions2)

if __name__ == '__main__':
    for extension in initial_extensions3:
        try:
            client.load_extension(extension)
            print(f'Loaded extension {extension}.')
        except Exception as e:
            print(f'Failed to load extension {extension}: {e}', file=sys.stderr)

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    await send_requests()

client.run("MTEyMjQ1NzYzOTIyNjQ0MTgyOQ.GsdAei.N23EzluT8iqSxLHhQx2sdLi8dZDRGHTlr5mmh8")