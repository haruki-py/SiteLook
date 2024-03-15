# from webapp import keep_alive
import time
import discord
import json
import aiohttp
# import traceback
import re
from datetime import datetime
from croniter import croniter
# import os
from pytz import timezone
import asyncio
# from discord import Intents
from discord.ext import commands
import motor.motor_asyncio

# MongoDB connection
mongo_client = motor.motor_asyncio.AsyncIOMotorClient('mongodb://Haruki:Athulkrishna11@pnode2.danbot.host:7650')
db = mongo_client['sitelook']
alerts_collection = db['alerts']
an_data_collection = db['an_data']
analytics_collection = db['analytics']
history_collection = db['history']
ls_collection = db['ls']
schedules_collection = db['schedules']
websites_collection = db['websites']


intents = discord.Intents.all()
# intents.messages = True
# intents.members = True
client = commands.Bot(command_prefix='up!', intents=intents)
client.activity = discord.Activity(type=discord.ActivityType.watching, name="Websites")

#  keep_alive()

# Define a function to ping a website with a given method and time interval
async def ping_website(url, method, time_interval, ping_count, user_id, website):
    # Retrieve last_status, error_count, and ping_count from MongoDB
    async with aiohttp.ClientSession() as session:
        user_ls_data = await ls_collection.find_one({"_id": user_id})
        monitor_ls_data = user_ls_data.get(website["index"], {})
        last_status = monitor_ls_data.get("last_status", None)

        user_an_data = await an_data_collection.find_one({"_id": user_id})
        monitor_an_data = user_an_data.get(website["index"], {})
        error_count = monitor_an_data.get("error_count", 0)
        ping_count = monitor_an_data.get("ping_count", 0)

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
                async with client.session.begin() as session:
                    user_analytics = await analytics_collection.find_one({"_id": user_id})
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
                    await analytics_collection.replace_one({"_id": user_id}, user_analytics)

                # Update the last ping status in MongoDB
                status = 'UP' if response.status == 200 else 'DOWN'
                await ls_collection.update_one({"_id": user_id}, {"$set": {website["index"]+".last_status": status}})

                # Check if the status has changed and send alerts
                if status != last_status and last_status is not None:
                    user_alerts = await alerts_collection.find_one({"_id": user_id})
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

                # Store information about the monitor status change in history.json (replace with MongoDB)
                async with client.session.begin() as session:
                    user_history = await history_collection.find_one({"_id": user_id})
                    monitor_history = user_history.get(website['index'], [])
                    monitor_history.append({'time': date_time, 'status': status})
                    if len(monitor_history) > 15:
                        monitor_history.pop(0)
                    user_history[website['index']] = monitor_history
                    await history_collection.replace_one({"_id": user_id}, user_history)

                # Store the last ping time and response status in websites.json (replace with MongoDB)
                async with client.session.begin() as session:
                    website_data = await websites_collection.find_one({"_id": user_id})
                    for website in website_data.get(str(user_id), []):
                        if website['url'] == url:
                            website['last_ping_time'] = date_time
                            website['response_status'] = f'{response.status} {response.reason}'
                            await websites_collection.replace_one({"_id": user_id}, website_data)
                            break

                # Update the error_count and ping_count values in MongoDB
                await an_data_collection.update_one({"_id": user_id}, {"$set": {website["index"]+".error_count": error_count, website["index"]+".ping_count": ping_count}})

            except Exception as e:
                print(f'Error pinging {url}: {e}')

            # Wait for the time interval before pinging again
            await asyncio.sleep(time_interval)

async def send_requests():
    ping_count = {}
    tasks = {}

    while True:
        # Get all websites from MongoDB
        async with aiohttp.ClientSession() as session:
            websites = await websites_collection.find().to_list(length=None)

        # Loop through websites for each user
        for user_id in set(website["_id"] for website in websites):
            user_websites = [website for website in websites if website["_id"] == user_id]

            # Get user's schedules from MongoDB
            user_schedules = await schedules_collection.find_one({"_id": user_id})

            for website in user_websites:
                url = website.get('url', None)
                method = website.get('method', None)
                time_interval = website.get('time_interval', None)

                # Check if the monitor is scheduled to run
                if user_schedules:
                    schedule = user_schedules.get(website.get('index', None))
                    if schedule:
                        now = datetime.now(timezone('Asia/Kolkata'))
                        iter = croniter(schedule, now)
                        next_run = iter.get_next(datetime)
                        if now < next_run:
                            continue

                # Check if website is stopped, cancel existing task
                if 'stopped' in website and website['stopped']:
                    if url in tasks:
                        tasks[url].cancel()
                        del tasks[url]
                    continue

                # Create or update task for the website
                if url not in tasks or tasks[url].time_interval != time_interval:
                    if url in tasks:
                        tasks[url].cancel()
                    tasks[url] = asyncio.create_task(ping_website(url, method, time_interval, ping_count, user_id, website))

        # Remove tasks for websites not found in MongoDB
        for url, task in list(tasks.items()):
            website_exists = await websites_collection.find_one({"url": url})
            if not website_exists:
                task.cancel()
                del tasks[url]

        # Wait before checking again
        await asyncio.sleep(5)

client.remove_command('help')

@client.command()
async def help(ctx, command=None):
    # If no command is specified, send the general help message
    if command is None:
        embed = discord.Embed(title='Help', description='This is a bot that monitors websites and sends requests to them periodically.', color=0x00ff00)
        embed.add_field(name='up!monitor <website>', value='Add a website to monitor. You will be asked to choose a method (HEAD, GET or POST) and a time interval for pinging the website.', inline=False)
        embed.add_field(name='up!remove <index>', value='Remove a website from monitoring by its index. Use up!stats to view your monitored websites and their indices.', inline=False)
        embed.add_field(name='up!start <index>', value='Start monitoring a website that was stopped. You need to provide the index of the website. Use up!stats to view your monitored websites and their indices.', inline=False)
        embed.add_field(name='up!stop <index>', value='Stop monitoring a website. You need to provide the index of the website. Use up!stats to view your monitored websites and their indices.', inline=False)
        embed.add_field(name='up!stats', value='View the statistics of your monitored websites, such as the last ping time and response status. The statistics will be sent to your DMs.', inline=False)
        embed.add_field(name='up!alert', value='Turn alerts on or off for a specific website. You will be asked to choose a website by its index and whether you want to turn alerts on or off.', inline=False)
        embed.add_field(name='up!schedule <index> <schedule>', value='Set a schedule for a specific monitor using a cron expression. You need to provide the index of the monitor and the cron expression.', inline=False)
        embed.add_field(name='up!history <index>', value='View the history of a specific monitor. You need to provide the index of the monitor.', inline=False)
        embed.add_field(name='up!analytics <index>', value='View the analytics of a specific monitor, such as response times, error rate, and uptime percentage. You need to provide the index of the monitor.', inline=False)
        embed.add_field(name='up!help [command]', value='Get help on how to use this bot or a specific command.', inline=False)
        embed.set_footer(text='up!help')
        await ctx.send(embed=embed)

    # If a command is specified, send the help message for that command
    else:
        # Check if the command is valid
        if command in ['monitor', 'remove', 'start', 'stop', 'stats', 'alert', 'schedule', 'history', 'analytics', 'help']:
            # Send the help message for the monitor command
            if command == 'monitor':
                embed = discord.Embed(title='Help: monitor', description='Add a website to monitor. You will be asked to choose a method (HEAD, GET or POST) and a time interval for pinging the website (minimum 1 minute).', color=0x00ff00)
                embed.add_field(name='Usage', value='up!monitor <website>', inline=False)
                embed.add_field(name='Example', value='up!monitor https://example.com', inline=False)
                embed.set_footer(text='up!help monitor')
                await ctx.send(embed=embed)

            # Send the help message for the remove command
            elif command == 'remove':
                embed = discord.Embed(title='Help: remove', description='Remove a website from monitoring by its index. Use up!stats to view your monitored websites and their indices.', color=0x00ff00)
                embed.add_field(name='Usage', value='up!remove <index>', inline=False)
                embed.add_field(name='Example', value='up!remove 1', inline=False)
                embed.set_footer(text='up!help remove')
                await ctx.send(embed=embed)

            # Send the help message for the start command
            elif command == 'start':
                embed = discord.Embed(title='Help: start', description='Start monitoring a website that was stopped. You need to provide the index of the website. Use up!stats to view your monitored websites and their indices.', color=0x00ff00)
                embed.add_field(name='Usage', value='up!start <index>', inline=False)
                embed.add_field(name='Example', value='up!start 1', inline=False)
                embed.set_footer(text='up!help start')
                await ctx.send(embed=embed)

            # Send the help message for the stop command
            elif command == 'stop':
                embed = discord.Embed(title='Help: stop', description='Stop monitoring a website. You need to provide the index of the website. Use up!stats to view your monitored websites and their indices.', color=0x00ff00)
                embed.add_field(name='Usage', value='up!stop <index>', inline=False)
                embed.add_field(name='Example', value='up!stop 1', inline=False)
                embed.set_footer(text='up!help stop')
                await ctx.send(embed=embed)

            # Send the help message for the stats command
            elif command == 'stats':
                embed = discord.Embed(title='Help: stats', description='View the statistics of your monitored websites, such as the last ping time and response status. The statistics will be sent to your DMs.', color=0x00ff00)
                embed.add_field(name='Usage', value='up!stats', inline=False)
                embed.set_footer(text='up!help stats')
                await ctx.send(embed=embed)

            # Send the help message for the alert command
            elif command == 'alert':
                embed = discord.Embed(title='Help: alert', description='Turn alerts on or off for a specific website. You will be asked to choose a website by its index and whether you want to turn alerts on or off.', color=0x00ff00)
                embed.add_field(name='Usage', value='up!alert', inline=False)
                embed.set_footer(text='up!help alert')
                await ctx.send(embed=embed)

            # Send the help message for the schedule command
            elif command == 'schedule':
                embed = discord.Embed(title='Help: schedule', description='Set a schedule for a specific monitor using a cron expression. You need to provide the index of the monitor and the cron expression.', color=0x00ff00)
                embed.add_field(name='Usage', value='up!schedule <index> <schedule>', inline=False)
                embed.add_field(name='Example', value='up!schedule 1 */5 * * * *', inline=False)
                embed.set_footer(text='up!help schedule')
                await ctx.send(embed=embed)

            # Send the help message for the history command
            elif command == 'history':
                embed = discord.Embed(title='Help: history', description='View the history of a specific monitor. You need to provide the index of the monitor.', color=0x00ff00)
                embed.add_field(name='Usage', value='up!history <index>', inline=False)
                embed.add_field(name='Example', value='up!history 1', inline=False)
                embed.set_footer(text='up!help history')
                await ctx.send(embed=embed)

            # Send the help message for the analytics command
            elif command == 'analytics':
                embed = discord.Embed(title='Help: analytics', description='View the analytics of a specific monitor, such as response times, error rate, and uptime percentage. You need to provide the index of the monitor.', color=0x00ff00)
                embed.add_field(name='Usage', value='up!analytics <index>', inline=False)
                embed.add_field(name='Example', value='up!analytics 1', inline=False)
                embed.set_footer(text='up!help analytics')
                await ctx.send(embed=embed)

            # Send the help message for the help command
            elif command == 'help':
                embed = discord.Embed(title='Help: help', description='Get help on how to use this bot or a specific command.', color=0x00ff00)
                embed.add_field(name='Usage', value='up!help [command]', inline=False)
                embed.add_field(name='Example', value='up!help monitor', inline=False)
                embed.set_footer(text='up!help help')
                await ctx.send(embed=embed)

        # If the command is not valid, send an error message
        else:
            embed = discord.Embed(title='Error', description=f'Invalid command: {command}', color=0xff0000)
            embed.set_footer(text='up!help')
            await ctx.send(embed=embed)

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    await send_requests()

@client.command()
async def start(ctx, index: int = None):
    if index is None:
        embed = discord.Embed(title='Error', description='Please include the index of the website to start. Example: up!start 1\nIf you do not know the index, use the up!stats command to view your monitored websites.', color=0xff0000)
        embed.set_footer(text='up!start')
        await ctx.send(embed=embed)
        return

    # Get user's websites from MongoDB
    async with client.session.begin() as session:
        user_websites = await websites_collection.find_one({"_id": ctx.author.id})
        if not user_websites:
            embed = discord.Embed(title='Error', description='You have not added any websites to monitor', color=0xff0000)
            embed.set_footer(text='up!start')
            await ctx.send(embed=embed)
            return

    # Validate website index
    if index < 1 or index > len(user_websites.get("websites", [])):
        embed = discord.Embed(title='Error', description=f'Invalid index. Please enter a number between 1 and {len(user_websites.get("websites", []))}\nIf you do not know the index, use the up!stats command to view your monitored websites.', color=0xff0000)
        embed.set_footer(text='up!start')
        await ctx.send(embed=embed)
        return

    website_index = index - 1
    website = user_websites["websites"][website_index]

    # Update website status in MongoDB
    if 'stopped' in website and website['stopped']:
        website['stopped'] = False
        await websites_collection.update_one({"_id": ctx.author.id}, {"$set": {"websites."+str(website_index): website}})
        embed = discord.Embed(title='Success', description=f'Website {index} started', color=0x00ff00)
        embed.set_footer(text='up!start')
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title='Error', description=f'Website {index} is already started', color=0xff0000)
        embed.set_footer(text='up!start')
        await ctx.send(embed=embed)

@client.command()
async def stop(ctx, index: int = None):
    if index is None:
        embed = discord.Embed(title='Error', description='Please include the index of the website to stop. Example: up!stop 1\nIf you do not know the index, use the up!stats command to view your monitored websites.', color=0xff0000)
        embed.set_footer(text='up!stop')
        await ctx.send(embed=embed)
        return

    # Get user's websites from MongoDB
    async with client.session.begin() as session:
        user_websites = await websites_collection.find_one({"_id": ctx.author.id})
        if not user_websites:
            embed = discord.Embed(title='Error', description='You have not added any websites to monitor', color=0xff0000)
            embed.set_footer(text='up!stop')
            await ctx.send(embed=embed)
            return

    # Validate website index
    if index < 1 or index > len(user_websites.get("websites", [])):
        embed = discord.Embed(title='Error', description=f'Invalid index. Please enter a number between 1 and {len(user_websites.get("websites", []))}\nIf you do not know the index, use the up!stats command to view your monitored websites.', color=0xff0000)
        embed.set_footer(text='up!stop')
        await ctx.send(embed=embed)
        return

    website_index = index - 1
    website = user_websites["websites"][website_index]

    # Update website status in MongoDB
    if 'stopped' not in website or not website['stopped']:
        website['stopped'] = True
        await websites_collection.update_one({"_id": ctx.author.id}, {"$set": {"websites."+str(website_index): website}})
        embed = discord.Embed(title='Success', description=f'Website {index} stopped', color=0x00ff00)
        embed.set_footer(text='up!stop')
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title='Error', description=f'Website {index} is already stopped', color=0xff0000)
        embed.set_footer(text='up!stop')
        await ctx.send(embed=embed)

@client.command()
async def alert(ctx):
    # Check if the user has any websites to monitor
    async with client.session.begin() as session:
        user_websites = await websites_collection.find_one({"_id": ctx.author.id})
        if not user_websites:
            embed = discord.Embed(title='Error', description='You do not have any websites to monitor.', color=0xff0000)
            embed.set_footer(text='up!alert')
            await ctx.send(embed=embed)
            return

    # Prompt the user to choose a website
    embed = discord.Embed(title='Website', description='Which website do you want to set an alert for? Reply with your website index. If you don\'t know the index, please use up!stats.', color=0x00ff00)
    embed.set_footer(text='up!alert')
    await ctx.send(embed=embed)

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()

    try:
        response = await client.wait_for('message', check=check, timeout=30.0)
    except asyncio.TimeoutError:
        embed = discord.Embed(title='Error', description='Sorry, you took too long to respond.', color=0xff0000)
        embed.set_footer(text='up!alert')
        await ctx.send(embed=embed)
        return
    website_index = int(response.content) - 1

    # Validate website index
    if not (0 <= website_index < len(user_websites.get("websites", []))):
        embed = discord.Embed(title='Error', description=f'Please enter a valid website index.', color=0xff0000)
        embed.set_footer(text='up!alert')
        await ctx.send(embed=embed)
        return

    website = user_websites["websites"][website_index]

    # Check user's alerts document in MongoDB
    user_alerts = await alerts_collection.find_one({"_id": ctx.author.id})
    alerts_on = user_alerts.get(str(website_index), True) if user_alerts else True

    # Prompt the user to turn alerts on or off
    embed = discord.Embed(title='Alerts', description=f'Do you want to turn alerts on or off for this website?', color=0x00ff00)
    embed.set_footer(text='up!alert')
    await ctx.send(embed=embed)

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content in ['on', 'off']

    try:
        response = await client.wait_for('message', check=check, timeout=30.0)
    except asyncio.TimeoutError:
        embed = discord.Embed(title='Error', description='Sorry, you took too long to respond.', color=0xff0000)
        embed.set_footer(text='up!alert')
        await ctx.send(embed=embed)
        return

    # Check if user is trying to turn alerts on/off for a website with matching state
    if (response.content == 'on' and alerts_on) or (response.content == 'off' and not alerts_on):
        embed = discord.Embed(title='Error', description=f'Website {website["index"]} already has its alerts turned {"on" if alerts_on else "off"}.', color=0xff0000)
        embed.set_footer(text='up!alert')
        await ctx.send(embed=embed)
        return

    # Update alerts in MongoDB for the specific website
    if not user_alerts:
        user_alerts = {"_id": ctx.author.id}
    user_alerts[str(website_index)] = response.content == 'on'
    await alerts_collection.update_one({"_id": ctx.author.id}, {"$set": user_alerts}, upsert=True)

    # Send a success message
    embed = discord.Embed(title='Success', description=f'Alerts turned {response.content} for website {website["index"]}', color=0x00ff00)
    embed

@client.command()
async def schedule(ctx, index=None, *, schedule=None):
    # Prompt for index if not provided
    if index is None:
        embed = discord.Embed(title='Index', description='Which monitor do you want to set a schedule for? Please enter the index of the monitor.', color=0x00ff00)
        embed.set_footer(text='up!schedule')
        await ctx.send(embed=embed)
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()
        try:
            response = await client.wait_for('message', check=check, timeout=30.0)
        except asyncio.TimeoutError:
            embed = discord.Embed(title='Error', description='Sorry, you took too long to respond.', color=0xff0000)
            embed.set_footer(text='up!schedule')
            await ctx.send(embed=embed)
            return
        index = int(response.content)

    # Prompt for schedule if not provided
    if schedule is None:
        embed = discord.Embed(title='Schedule', description='What schedule do you want to set for the monitor? Please enter a cron expression.', color=0x00ff00)
        embed.set_footer(text='up!schedule')
        await ctx.send(embed=embed)
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        try:
            response = await client.wait_for('message', check=check, timeout=30.0)
        except asyncio.TimeoutError:
            embed = discord.Embed(title='Error', description='Sorry, you took too long to respond.', color=0xff0000)
            embed.set_footer(text='up!schedule')
            await ctx.send(embed=embed)
            return
        schedule = response.content

    # Update user's schedule in MongoDB
    async with client.session.begin() as session:
        user_schedules = await schedules_collection.find_one({"_id": ctx.author.id})
        if not user_schedules:
            user_schedules = {"_id": ctx.author.id}
        user_schedules["websites"] = user_schedules.get("websites", [])  # Ensure websites key exists
        user_schedules["websites"][index - 1] = schedule
        await schedules_collection.update_one({"_id": ctx.author.id}, {"$set": user_schedules}, upsert=True)

    # Send a success message
    await ctx.send(f'Schedule set for monitor {index}')

@client.command()
async def history(ctx, index=None):
    # Prompt for index if not provided
    if index is None:
        embed = discord.Embed(title='Index', description='Which monitor do you want to view the history for? Please enter the index of the monitor.', color=0x00ff00)
        embed.set_footer(text='up!history')
        await ctx.send(embed=embed)
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()
        try:
            response = await client.wait_for('message', check=check, timeout=30.0)
        except asyncio.TimeoutError:
            embed = discord.Embed(title='Error', description='Sorry, you took too long to respond.', color=0xff0000)
            embed.set_footer(text='up!history')
            await ctx.send(embed=embed)
            return
        index = int(response.content)

    # Get user's history from MongoDB
    async with client.session.begin() as session:
        user_history = await history_collection.find_one({"_id": ctx.author.id})
        if not user_history:
            embed = discord.Embed(title='History', description=f'No history found for monitor {index}', color=0x00ff00)
            embed.set_footer(text='up!history')
            await ctx.send(embed=embed)
            return
        monitor_history = user_history.get("websites", {}).get(str(index - 1), [])

    # Check if history exists for the website
    if not monitor_history:
        embed = discord.Embed(title='History', description=f'No history found for monitor {index}', color=0x00ff00)
        embed.set_footer(text='up!history')
        await ctx.send(embed=embed)
        return

    # Format and send the history message in an embed
    history_message = ''
    for entry in monitor_history:
        history_message += f'{entry["time"]}: {entry["status"]}\n'
    embed = discord.Embed(title='History', description=history_message, color=0x00ff00)
    embed.set_footer(text='up!history')
    await ctx.send(embed=embed)

@client.command()
async def analytics(ctx, index=None):
    # Prompt for index if not provided
    if index is None:
        embed = discord.Embed(title='Index', description='Which monitor do you want to view the analytics for? Please enter the index of the monitor.', color=0x00ff00)
        embed.set_footer(text='up!analytics')
        await ctx.send(embed=embed)
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()
        try:
            response = await client.wait_for('message', check=check, timeout=30.0)
        except asyncio.TimeoutError:
            embed = discord.Embed(title='Error', description='Sorry, you took too long to respond.', color=0xff0000)
            embed.set_footer(text='up!analytics')
            await ctx.send(embed=embed)
            return
        index = int(response.content)

    # Get user's analytics from MongoDB
    async with client.session.begin() as session:
        user_analytics = await analytics_collection.find_one({"_id": ctx.author.id})
        if not user_analytics:
            embed = discord.Embed(title='Analytics', description=f'No analytics found for monitor {index}', color=0x00ff00)
            embed.set_footer(text='up!analytics')
            await ctx.send(embed=embed)
            return
        monitor_analytics = user_analytics.get("websites", {}).get(str(index - 1), {})

    # Check if analytics exists for the website
    if not monitor_analytics:
        embed = discord.Embed(title='Analytics', description=f'No analytics found for monitor {index}', color=0x00ff00)
        embed.set_footer(text='up!analytics')
        await ctx.send(embed=embed)
        return

    # Format and send the analytics message in an embed
    response_times = monitor_analytics.get('average_response_time', [])
    error_rate = monitor_analytics.get('error_rate', 0)
    uptime_percentage = monitor_analytics.get('uptime_percentage', 0)
    analytics_message = f'Average response time: {response_times}ms\nError rate: {error_rate}\nUptime percentage: {uptime_percentage}'
    embed = discord.Embed(title='Analytics', description=analytics_message, color=0x00ff00)
    embed.set_footer(text='up!analytics')
    await ctx.send(embed=embed)

@client.command()
async def monitor(ctx):
    split_message = ctx.message.content.split()
    if len(split_message) < 2:
        embed = discord.Embed(title='Error', description='Please include a website to monitor. Example: up!monitor https://example.com', color=0xff0000)
        embed.set_footer(text='up!monitor')
        await ctx.send(embed=embed)
        return
    website = split_message[1]

    # Check if website is already being monitored
    async with client.session.begin() as session:
        user_websites = await websites_collection.find_one({"_id": ctx.author.id})
        if user_websites and any(website_data['url'] == website for website_data in user_websites.get("websites", [])):
            embed = discord.Embed(title='Error', description='That website is already being monitored', color=0xff0000)
            embed.set_footer(text='up!monitor')
            await ctx.send(embed=embed)
            return

    # Prompt for method
    embed = discord.Embed(title='Method', description='''Which one? 
1. HEAD
2. GET
3. POST? 
Reply with the 1, 2 or 3.''', color=0x00ff00)
    embed.set_footer(text='up!monitor')
    await ctx.send(embed=embed)

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content in ['1', '2', '3']
    try:
        response = await client.wait_for('message', check=check, timeout=30.0)
    except asyncio.TimeoutError:
        embed = discord.Embed(title='Error', description='Sorry, you took too long to respond.', color=0xff0000)
        embed.set_footer(text='up!monitor')
        await ctx.send(embed=embed)
        return
    method = ''
    if response.content == '1':
        method = 'HEAD'
    elif response.content == '2':
        method = 'GET'
    elif response.content == '3':
        method = 'POST'

    # Ask for time interval
    embed = discord.Embed(title='Time Interval', description='''How often do you want to ping the website? 
Enter a number followed by a unit of time. For example: 
s for seconds
m for minute
h for hour
d for day
w for week
You can also use decimal points to specify fractions of a unit. For example:
0.5m for 30 seconds
6.9h for 6 hours and 54 minutes
The minimum interval is 1 minute.''', color=0x00ff00)
    embed.set_footer(text='up!monitor')
    await ctx.send(embed=embed)

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and re.match(r'\d+(\.\d+)?[smhdw]$', m.content)
    try:
        response = await client.wait_for('message', check=check, timeout=30.0)
    except asyncio.TimeoutError:
        embed = discord.Embed(title='Error', description='Sorry, you took too long to respond.', color=0xff0000)
        embed.set_footer(text='up!monitor')
        await ctx.send(embed=embed)
        return

    # Convert time interval to seconds
    time_interval = response.content
    unit = time_interval[-1]
    factor = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400, 'w': 604800}
    try:
        number = float(time_interval[:-1])
        seconds = number * factor[unit]
        if seconds < 60:
            raise ValueError('Minimum time interval is 1 minute. Please try again')
    except ValueError as e:
        embed = discord.Embed(title='Error', description=f'{e}', color=0xff0000)
        embed.set_footer(text='up!monitor')
        await ctx.send(embed=embed)
        return

    # Generate a new website ID
    async with client.session.begin() as session:
        # Find the maximum website ID for the user
        user_websites = await websites_collection.find_one({"_id": ctx.author.id})
        max_website_id = 0
        if user_websites:
            max_website_id = max(website_data['_id'] for website_data in user_websites.get("websites", []))

    new_website_id = max_website_id + 1

    # Add website data to user's websites in MongoDB
    website_data = {
        "_id": new_website_id,
        "url": website,
        "method": method,
        "time_interval": seconds,
    }
    async with client.session.begin() as session:
        user_websites = await websites_collection.find_one_and_update({"_id": ctx.author.id}, {"$push": {"websites": website_data}}, upsert=True)

    # Delete the user's messages if possible
    try:
        await ctx.message.delete()
        await response.delete()
    except discord.Forbidden:
        pass

    # Send a success message
    embed = discord.Embed(title='Success', description='Website added', color=0x00ff00)
    embed.set_footer(text='up!monitor')
    await ctx.send(embed=embed)


@client.command()
async def remove(ctx):
    split_message = ctx.message.content.split()
    if len(split_message) < 2:
        embed = discord.Embed(title='Error', description='Please include an index to remove. Example: up!remove 1\nIf you do not know the index, use the up!stats command to view your monitored websites.', color=0xff0000)
        embed.set_footer(text='up!remove')
        await ctx.send(embed=embed)
        return
    argument = split_message[1]

    # Check if the argument is an index
    if argument.isdigit():
        index = int(argument) - 1

        # Remove website from user's websites in MongoDB
        async with client.session.begin() as session:
            user_websites = await websites_collection.find_one_and_update({"_id": ctx.author.id}, {"$pull": {"websites": {"_id": index}}}, upsert=False)
            if not user_websites:
                # Existing error message preserved here
                embed = discord.Embed(title='Error', description=f'Invalid index. Please enter a number between 1 and {len(user_websites)}\nIf you do not know the index, use the up!stats command to view your monitored websites.', color=0xff0000)
                embed.set_footer(text='up!remove')
                await ctx.send(embed=embed)
                return

        # Delete successful, send confirmation message
        if not isinstance(ctx.channel, discord.channel.DMChannel):
            try:
                await ctx.message.delete()
            except discord.Forbidden:
                pass
        embed = discord.Embed(title='Success', description='Website removed', color=0x00ff00)
        embed.set_footer(text='up!remove')
        await ctx.send(embed=embed)

    # Invalid argument, send error message
    else:
        embed = discord.Embed(title='Error', description=f'Invalid argument. Please enter an index to remove. Example: up!remove 1\nIf you do not know the index, use the up!stats command to view your monitored websites.', color=0xff0000)
        embed.set_footer(text='up!remove')
        await ctx.send(embed=embed)

@client.command()
async def stats(ctx):
    # Find user's websites in MongoDB
    async with client.session.begin() as session:
        user_websites = await websites_collection.find_one({"_id": ctx.author.id})

    if not user_websites or not user_websites.get("websites", []):
        embed = discord.Embed(title='Error', description='You have not added any websites to monitor', color=0xff0000)
        embed.set_footer(text='up!stats')
        await ctx.send(embed=embed)
        return

    stats_message = ''
    count = 1
    for website_data in user_websites["websites"]:
        url = website_data["url"]
        method = website_data["method"]
        last_ping_time = website_data.get('last_ping_time', 'N/A')
        response_status = website_data.get('response_status', 'N/A')
        stats_message += f'{count}. {url}, {method}, last pinged on {last_ping_time} (IST), response status: {response_status}\n'
        count += 1

    embed = discord.Embed(title='Stats', description=stats_message, color=0x00ff00)
    embed.set_footer(text='up!stats')
    await ctx.author.send(embed=embed)
    if not isinstance(ctx.channel, discord.channel.DMChannel):
        await ctx.send(f'{ctx.author.mention} Check your DMs!')

@client.command(name='botstats')
# @commands.is_owner()
async def botstats(ctx):
    if ctx.author.id not in [920850442425102367, 1139406664584409159]:
        return
        
    # Create the embed
    embed = discord.Embed(title='Bot Stats', color=0x00ff00)
    embed.add_field(name='Servers', value=f'{len(client.guilds)}', inline=True)
    embed.add_field(name='Total Members', value=f'{len(client.users)}', inline=True)
    embed.set_footer(text='Server count and total member count')

    # Send the embed
    await ctx.send(embed=embed)

client.run("MTEyMjQ1NzYzOTIyNjQ0MTgyOQ.GuqaiK.fpbVPiALpa4amONNuZj6T_Ax-T2wAz-K75UPF8")
