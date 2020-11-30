import os, re, time, random
import discord
from discord.ext import tasks

client = discord.Client()

@client.event
async def on_ready():
    print('We have logged in as: ' + str(client.user))
    talk_in_voice_chats.start()   

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
            audio_source = discord.FFmpegPCMAudio(source='audio/' + random.choice(audio_files), executable=os.getenv('FFMPEG_LOCATION', 'ffmpeg.exe'))
            voice_client.play(audio_source)


client.run(os.getenv('DISCORD_TOKEN'))