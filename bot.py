import os, re, time, random, requests
import datetime, calendar
import discord
from discord.ext import tasks

client = discord.Client()

@client.event
async def on_ready():
    print('We have logged in as: ' + str(client.user))
    talk_in_voice_chats.start()
    check_for_events_ending.start()   

@client.event
async def on_message(message):
    # Don't respond to any messages we've sent
    if message.author == client.user:
        return

    # Respond with Sandy image if someone says yeet
    if re.compile('\\b(yeet)\\b', re.IGNORECASE).match(message.content):
        img_file = discord.File(fp=open('imgs/sandy.png', 'rb'), filename='yeet.png')
        await message.channel.send(file=img_file)

@tasks.loop(seconds=5.0)
async def talk_in_voice_chats():
    for guild in client.guilds:

        topmost_voice_channel = guild.voice_channels[0]
        try:
            voice_client = await topmost_voice_channel.connect()
        except discord.ClientException:
            voice_client = guild.voice_client

        # 10% change to start playing (if we're not already)
        if random.random() < 0.1 and (not voice_client.is_playing()):
            audio_files = os.listdir('audio')
            selected_audio_source = 'audio/' + random.choice(audio_files)

            if len(voice_client.channel.members) <= 1:
                while selected_audio_source == 'audio/communism.ogg':
                    selected_audio_source = 'audio/' + random.choice(audio_files)

            audio_source = discord.FFmpegPCMAudio(source=selected_audio_source, executable=os.getenv('FFMPEG_LOCATION', 'ffmpeg.exe'))
            voice_client.play(audio_source)

@tasks.loop(hours=1)
async def check_for_events_ending():
    events_text = requests.get('https://azurlane.koumakan.jp/Azur_Lane_Wiki').text
    events_text = events_text[events_text.index('English Server News'):]
    events_text = events_text[:events_text.index('Chinese/Japanese Server News')]

    while events_text.find('class="azl_news_title') > -1:
        events_text = events_text[events_text.index('class="azl_news_title') + 1:]
        events_text = events_text[events_text.index('<a') + 1:]
        events_text = events_text[events_text.index('>') + 1:]

        cur_event_name = events_text[:events_text.index('</a>')]
        cur_event_name = cur_event_name.replace('[ONGOING]', '').strip()

        events_text = events_text[events_text.index('class="azl_news_message') + 1:]
        events_text = events_text[events_text.index('<a') + 1:]
        events_text = events_text[events_text.index('>') + 1:]

        cur_event_message = events_text[:events_text.index('</a>')].strip()
        if cur_event_message.startswith('('):
            cur_event_date_range = cur_event_message[1:cur_event_message.index(')')]
            cur_event_end_date = cur_event_date_range[cur_event_date_range.index('-') + 1:].strip()

            cur_event_end_month = cur_event_end_date[:cur_event_end_date.index(' ')]
            cur_event_end_day = cur_event_end_date[cur_event_end_date.index(' ') + 1:]
            cur_event_end_day = cur_event_end_day.replace('st', '').replace('nd', '').replace('rd', '').replace('th', '')
            cur_event_end_day = int(cur_event_end_day)

            server_datetime = datetime.datetime.now() - datetime.timedelta(hours=7)

            if (calendar.month_name[server_datetime.month] == cur_event_end_month) and (server_datetime.day == cur_event_end_day):
                if server_datetime.hour == 12:
                    for guild in client.guilds:
                        for text_channel in guild.text_channels:
                            if text_channel.name == 'azur-lane-chat':
                                await text_channel.send(content='*' + cur_event_name + '* ends today')


client.run(os.getenv('DISCORD_TOKEN'))