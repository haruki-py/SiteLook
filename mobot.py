from webapp import keep_alive
import time
import discord
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
from pymongo import MongoClient

# MongoDB connection string
mongo_url = "mongodb://Haruki:Athulkrishna@11@pnode2.danbot.host:7650"
client = MongoClient(mongo_url)
db = client['sldb']  # Replace with your database name

intents = discord.Intents.default()
intents.messages = True
intents.members = True
bot = commands.Bot(command_prefix='up!', intents=intents)
bot.activity = discord.Activity(type=discord.ActivityType.watching, name="Websites")

# Define a function to ping a website with a given method and time interval
async def ping_website(url, method, time_interval, ping_count, user_id, website):
    # Retrieve the last_status value from MongoDB
    last_status = db.status.find_one({"user_id": user_id, "website_index": website['index']})

    # Retrieve the error_count and ping_count values from MongoDB
    analytics_data = db.analytics.find_one({"user_id": user_id, "website_index": website['index']})
    error_count = analytics_data['error_count'] if analytics_data else 0
    ping_count = analytics_data['ping_count'] if analytics_data else 0

    # Set the time_interval attribute on the current task
    asyncio.current_task().time_interval = time_interval

    async with aiohttp.ClientSession() as session:
        while True:
            start_time = time.time()
            try:
                # Send the request based on the specified method
                response = await getattr(session, method.lower())(url)
                response_time = round((time.time() - start_time) * 1000)
                now = datetime.now(timezone('Asia/Kolkata'))
                date_time = now.strftime("%d/%m/%y @ %I:%M %p")
                ping_count += 1
                log = f'{url}: {response.status} | Pinged on {date_time} (IST) | Ping count: {ping_count} | Response time: {response_time}ms'
                print(log)

                # Update the analytics data for this monitor in MongoDB
                response_times = analytics_data.get('response_times', [])
                response_times.append(response_time)
                if len(response_times) > 15:
                    response_times.pop(0)
                average_response_time = round(sum(response_times) / len(response_times), 2)
                error_rate = round(error_count / ping_count * 100, 2)
                uptime_percentage = round((ping_count - error_count) / ping_count * 100, 2)
                db.analytics.update_one(
                    {"user_id": user_id, "website_index": website['index']},
                    {"$push": {"response_times": response_time},
                     "$set": {
                         "average_response_time": average_response_time,
                         "error_rate": f'{error_rate}%',
                         "uptime_percentage": f'{uptime_percentage}%'
                     }},
                    upsert=True
                )

                # Update the last ping status in MongoDB
                status = 'UP' if response.status == 200 else 'DOWN'
                db.status.update_one(
                    {"user_id": user_id, "website_index": website['index']},
                    {"$set": {"last_status": status}},
                    upsert=True
                )

                # Check if the status of the website has changed
                if status != last_status and last_status is not None:
                    # Check if alerts are turned on for this website
                    alert_setting = db.alerts.find_one({"user_id": user_id, "website_index": website['index']})
                    alerts_on = alert_setting['alerts_on'] if alert_setting else True
                    if alerts_on:
                        user = bot.get_user(int(user_id))
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

                # Store information about the monitor status change in MongoDB
                db.history.update_one(
                    {"user_id": user_id, "website_index": website['index']},
                    {"$push": {"history": {'time': date_time, 'status': status}}},
                    upsert=True
                )

                # Store the last ping time and response status in MongoDB
                db.websites.update_one(
                    {"user_id": user_id, "website_index": website['index']},
                    {"$set": {
                        "last_ping_time": date_time,
                        "response_status": f'{response.status} {response.reason}'
                    }},
                    upsert=True
                )

                # Save the error_count and ping_count values to MongoDB
                db.analytics.update_one(
                    {"user_id": user_id, "website_index": website['index']},
                    {"$set": {
                        "error_count": error_count,
                        "ping_count": ping_count
                    }},
                    upsert=True
                )

            except Exception as e:
                print(f'Error pinging {url}: {e}')

            # Wait for the time interval before pinging again
            await asyncio.sleep(time_interval)


async def send_requests():
    ping_count = {}

    # Create a dictionary to store the tasks for each website
    tasks = {}

    while True:

        # Fetch the websites from MongoDB
        websites = db.websites.find()

        # Loop through the websites for each user
        for website in websites:

            # Get the user_id, url, method and time interval of the website
            user_id = website['user_id']
            url = website['url']
            method = website['method']
            time_interval = website['time_interval']

            # Check if the monitor is scheduled to run
            schedule = db.schedules.find_one({"user_id": user_id, "website_index": website['index']})
            if schedule:
                now = datetime.now(timezone('Asia/Kolkata'))
                iter = croniter(schedule['schedule'], now)
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

        # Loop through the tasks dictionary and cancel any task that is not in MongoDB anymore
        for url, task in list(tasks.items()):
            if not db.websites.find_one({"url": url}):
                task.cancel()
                del tasks[url]

        # Wait for 5 seconds before fetching the websites again
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

    # Check if the user has added any websites to monitor
    if db.websites.count_documents({"user_id": str(ctx.author.id)}) == 0:
        embed = discord.Embed(title='Error', description='You have not added any websites to monitor', color=0xff0000)
        embed.set_footer(text='up!start')
        await ctx.send(embed=embed)
        return

    # Fetch the website to start from MongoDB using the index
    website = db.websites.find_one({"user_id": str(ctx.author.id), "index": index})

    if not website:
        user_websites_count = db.websites.count_documents({"user_id": str(ctx.author.id)})
        embed = discord.Embed(title='Error', description=f'Invalid index. Please enter a number between 1 and {user_websites_count}\nIf you do not know the index, use the up!stats command to view your monitored websites.', color=0xff0000)
        embed.set_footer(text='up!start')
        await ctx.send(embed=embed)
        return

    if 'stopped' in website and website['stopped']:
        # Update the 'stopped' field to False in MongoDB
        db.websites.update_one({"user_id": str(ctx.author.id), "index": index}, {"$set": {"stopped": False}})
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

    # Check if the user has added any websites to monitor
    if db.websites.count_documents({"user_id": str(ctx.author.id)}) == 0:
        embed = discord.Embed(title='Error', description='You have not added any websites to monitor', color=0xff0000)
        embed.set_footer(text='up!stop')
        await ctx.send(embed=embed)
        return

    # Fetch the website to stop from MongoDB using the index
    website = db.websites.find_one({"user_id": str(ctx.author.id), "index": index})

    if not website:
        user_websites_count = db.websites.count_documents({"user_id": str(ctx.author.id)})
        embed = discord.Embed(title='Error', description=f'Invalid index. Please enter a number between 1 and {user_websites_count}\nIf you do not know the index, use the up!stats command to view your monitored websites.', color=0xff0000)
        embed.set_footer(text='up!stop')
        await ctx.send(embed=embed)
        return

    if 'stopped' not in website or not website['stopped']:
        # Update the 'stopped' field to True in MongoDB
        db.websites.update_one({"user_id": str(ctx.author.id), "index": index}, {"$set": {"stopped": True}})
        embed = discord.Embed(title='Success', description=f'Website {index} stopped', color=0x00ff00)
        embed.set_footer(text='up!stop')
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title='Error', description=f'Website {index} is already stopped', color=0xff0000)
        embed.set_footer(text='up!stop')
        await ctx.send(embed=embed)


@client.command()
async def alert(ctx):
    # Fetch the user's monitored websites from MongoDB
    user_websites = list(db.websites.find({"user_id": str(ctx.author.id)}))

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

    website_index = int(response.content)
    website = db.websites.find_one({"user_id": str(ctx.author.id), "index": website_index})

    if not website:
        embed = discord.Embed(title='Error', description=f'Please enter a valid website index.', color=0xff0000)
        embed.set_footer(text='up!alert')
        await ctx.send(embed=embed)
        return

    # Check if alerts are already on or off for this website
    alert_setting = db.alerts.find_one({"user_id": str(ctx.author.id), "website_index": website_index})
    alerts_on = alert_setting['alerts_on'] if alert_setting else True

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

    # Check if the user is trying to turn on or off alerts for a website that already has alerts turned on or off, respectively
    if (response.content == 'on' and alerts_on) or (response.content == 'off' and not alerts_on):
        embed = discord.Embed(title='Error', description=f'Website {website_index} already has its alerts turned {"on" if alerts_on else "off"}.', color=0xff0000)
        embed.set_footer(text='up!alert')
        await ctx.send(embed=embed)
        return

    # Update the alert setting in MongoDB
    db.alerts.update_one(
        {"user_id": str(ctx.author.id), "website_index": website_index},
        {"$set": {"alerts_on": response.content == 'on'}},
        upsert=True
    )

    # Send a success message
    embed = discord.Embed(title='Success', description=f'Alerts turned {response.content} for website {website_index}', color=0x00ff00)
    embed.set_footer(text='up!alert')
    await ctx.send(embed=embed)

@client.command()
async def schedule(ctx, index=None, *, schedule=None):
    # If the index argument is not provided, prompt the user for it
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

    # If the schedule argument is not provided, prompt the user for it
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

    # Update the schedule in MongoDB
    result = db.schedules.update_one(
        {"user_id": str(ctx.author.id), "index": index},
        {"$set": {"schedule": schedule}},
        upsert=True
    )

    # Check if the update was successful
    if result.matched_count > 0 or result.upserted_id is not None:
        embed = discord.Embed(
            title='Schedule Set',
            description=f'The schedule for monitor {index} has been successfully set.',
            color=0x00ff00
        )
        embed.set_footer(text='up!schedule')
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title='Schedule Not Set',
            description=f'Failed to set the schedule for monitor {index}. Please try again.',
            color=0xff0000
        )
        embed.set_footer(text='up!schedule')
        await ctx.send(embed=embed)

@client.command()
async def history(ctx, index=None):
    # If the index argument is not provided, prompt the user for it
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

    # Fetch the history for the specified monitor from MongoDB
    monitor_history = list(db.history.find({"user_id": str(ctx.author.id), "index": index}))

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
    # If the index argument is not provided, prompt the user for it
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
        index = response.content

    # Fetch the analytics for the specified monitor from MongoDB
    monitor_analytics = db.analytics.find_one({"user_id": str(ctx.author.id), "index": index})

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

    # Check if the website is already being monitored
    if db.websites.find_one({"user_id": str(ctx.author.id), "url": website}):
        embed = discord.Embed(title='Error', description='That website is already being monitored', color=0xff0000)
        embed.set_footer(text='up!monitor')
        await ctx.send(embed=embed)
        return

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

    # Ask the user for the time interval
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

    # Generate a new index for the website
    max_index = db.websites.find({"user_id": str(ctx.author.id)}).sort("index", -1).limit(1)
    new_index = str(max_index['index'] + 1 if max_index else 1)

    # Insert the new website monitor into MongoDB
    db.websites.insert_one({
        'user_id': str(ctx.author.id),
        'url': website,
        'method': method,
        'time_interval': seconds,
        'index': new_index
    })

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

    # Check if the argument is an index and convert it to an integer
    if argument.isdigit():
        index = int(argument)

        # Attempt to remove the website using the index
        result = db.websites.delete_one({"user_id": str(ctx.author.id), "index": index})

        # Check if a website was removed
        if result.deleted_count == 0:
            embed = discord.Embed(title='Error', description=f'Invalid index. Please enter a number that corresponds to a monitored website.\nIf you do not know the index, use the up!stats command to view your monitored websites.', color=0xff0000)
            embed.set_footer(text='up!remove')
            await ctx.send(embed=embed)
            return

        # Send a success message
        embed = discord.Embed(title='Success', description='Website removed', color=0x00ff00)
        embed.set_footer(text='up!remove')
        await ctx.send(embed=embed)

        # Delete the user's messages if possible
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

    # If the argument is not an index, send an error message
    else:
        embed = discord.Embed(title='Error', description=f'Invalid argument. Please enter an index to remove. Example: up!remove 1\nIf you do not know the index, use the up!stats command to view your monitored websites.', color=0xff0000)
        embed.set_footer(text='up!remove')
        await ctx.send(embed=embed)

@client.command()
async def stats(ctx):
    # Fetch the user's monitored websites from MongoDB
    user_websites = list(db.websites.find({"user_id": str(ctx.author.id)}))

    if not user_websites:
        embed = discord.Embed(title='Error', description='You have not added any websites to monitor', color=0xff0000)
        embed.set_footer(text='up!stats')
        await ctx.send(embed=embed)
        return

    stats_message = ''
    for website in user_websites:
        url = website['url']
        method = website['method']
        last_ping_time = website.get('last_ping_time', 'N/A')
        response_status = website.get('response_status', 'N/A')
        index = website['index']
        stats_message += f'{index}. {url}, {method}, last pinged on {last_ping_time} (IST), response status: {response_status}\n'

    embed = discord.Embed(title='Stats', description=stats_message, color=0x00ff00)
    embed.set_footer(text='up!stats')
    await ctx.author.send(embed=embed)
    if not isinstance(ctx.channel, discord.channel.DMChannel):
        await ctx.send(f'{ctx.author.mention} Check your DMs!')


client.run("MTEyMjQ1NzYzOTIyNjQ0MTgyOQ.G_Ax2P.oPyfxddQXqU3nFBHlqMpJvNECmyef5Ji5e24qM")