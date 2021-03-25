import os, re, time, random, requests
import datetime, calendar
import discord
from discord.ext import tasks

voiceline_folders = {}

client = discord.Client()

@client.event
async def on_ready():
    print('We have logged in as: ' + str(client.user))

    for guild in client.guilds:
        print(await set_ship('San Diego', guild))

    talk_in_voice_chats.start()
    check_for_events_ending.start()   

@client.event
async def on_message(message):
    # Don't respond to any messages we've sent
    if message.author == client.user:
        return

    if message.content.startswith('transform:'):
        new_ship_name = message.content[10:].strip()

        if message.guild.get_member(client.user.id).display_name == new_ship_name:
            await message.channel.send(content='I already am ' + new_ship_name + '!')
        else:
            await message.channel.send(content='Becoming ' + new_ship_name + ', please wait...')
            result = await set_ship(new_ship_name, message.guild)
            await message.channel.send(content=result)

    # Respond with Sandy image if someone says yeet
    if re.compile('\\b(yeet)\\b', re.IGNORECASE).match(message.content):
        img_file = discord.File(fp=open('imgs/sandy.png', 'rb'), filename='yeet.png')
        await message.channel.send(file=img_file)

async def set_ship(ship_name: str, target_guild):
    if not ship_name in voiceline_folders:
        error = await load_voicelines_for_ship(ship_name)
        if error:
            return 'Unable to become ' + ship_name + ': ' + error

    return_value = ''
    warning = await set_profile_picture(ship_name)
    if warning:
        return_value += warning + '\n'

    await target_guild.get_member(client.user.id).edit(nick=ship_name)

    return_value += 'Successfully became ' + ship_name + '!'
    return return_value

async def load_voicelines_for_ship(ship_name: str):
    print('Loading voicelines for ' + ship_name)

    has_any_voicelines = False
    folder_name = str(time.time())
    os.makedirs('voicelines/' + folder_name)

    ship_name_target_string = 'title="' + ship_name + '">' + ship_name + '</a>'
    list_of_ships = requests.get('https://azurlane.koumakan.jp/List_of_Ships').text

    if ship_name_target_string in list_of_ships:
        list_of_ships = list_of_ships[:list_of_ships.index(ship_name_target_string)]
        new_ship_url = list_of_ships[list_of_ships.rindex('<a href="') + 9:]
        new_ship_url = new_ship_url[:new_ship_url.index('"')]
        new_ship_url = 'https://azurlane.koumakan.jp' + new_ship_url + '/Quotes'

        list_of_voicelines = requests.get(new_ship_url).text
        list_of_voicelines = list_of_voicelines[list_of_voicelines.index('<table') : list_of_voicelines.index('</table')]

        voiceline_target_string = '.ogg" title="Play" class="sm2_button">Play</a>'

        file_index = 0
        while voiceline_target_string in list_of_voicelines:
            cur_voiceline_url = list_of_voicelines[:list_of_voicelines.index(voiceline_target_string) + 4]
            cur_voiceline_url = cur_voiceline_url[cur_voiceline_url.rindex('<a href="') + 9:]

            cur_voiceline_bytes = requests.get(cur_voiceline_url).content
            with open('voicelines/' + folder_name + '/voiceline-' + str(file_index) + '.ogg', 'wb') as cur_voiceline_file:
                cur_voiceline_file.write(cur_voiceline_bytes)

            list_of_voicelines = list_of_voicelines[list_of_voicelines.index(voiceline_target_string) + 1:]
            file_index += 1
            has_any_voicelines = True
    else:
        return 'Name not found on the wiki.'
    
    if has_any_voicelines:
        voiceline_folders[ship_name] = folder_name
        return None
    else:
        return 'No voicelines found on the wiki.'

async def set_profile_picture(ship_name: str):
    print('Loading picture for ' + ship_name)

    ship_name_target_string = 'title="' + ship_name + '">' + ship_name + '</a>'
    list_of_ships = requests.get('https://azurlane.koumakan.jp/List_of_Ships').text
    list_of_ships = list_of_ships[:list_of_ships.index(ship_name_target_string)]
    new_ship_url = list_of_ships[list_of_ships.rindex('<a href="') + 9:]
    new_ship_url = new_ship_url[:new_ship_url.index('"')]
    new_ship_url = 'https://azurlane.koumakan.jp' + new_ship_url

    new_ship_image_url = requests.get(new_ship_url).text
    new_ship_image_url = new_ship_image_url[new_ship_image_url.index('<img'):]
    new_ship_image_url = new_ship_image_url[new_ship_image_url.index('src="') + 5:]
    new_ship_image_url = new_ship_image_url[:new_ship_image_url.index('"')]
    new_ship_image_url = 'https://azurlane.koumakan.jp' + new_ship_image_url

    new_ship_image_bytes = requests.get(new_ship_image_url).content
    await client.user.edit(avatar=new_ship_image_bytes)

    return None

@tasks.loop(seconds=20.0)
async def talk_in_voice_chats():
    for guild in client.guilds:

        cur_voiceline_folder = 'voicelines/' + voiceline_folders[guild.get_member(client.user.id).display_name]

        topmost_voice_channel = guild.voice_channels[0]
        try:
            voice_client = await topmost_voice_channel.connect()
        except discord.ClientException:
            voice_client = guild.voice_client

        # 25% change to start playing (if we're not already)
        if random.random() < 0.25 and (not voice_client.is_playing()):
            audio_files = os.listdir(cur_voiceline_folder)
            selected_audio_source = cur_voiceline_folder + '/' + random.choice(audio_files)

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