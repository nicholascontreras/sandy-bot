import os, re, time
import discord

client = discord.Client()

@client.event
async def on_ready():
    print('We have logged in as: ' + str(client.user))   

@client.event
async def on_message(message):
    # Don't respond to any messages we've sent
    if message.author == client.user:
        return

    # Respond with Sandy if someone says yeet
    if re.compile('\\b(yeet)\\b', re.IGNORECASE).match(message.content):
        img_file = discord.File(fp=open('imgs/sandy.png', 'rb'), filename='yeet.png')

        topmost_voice_channel = message.guild.voice_channels[0]
        voice_client = await topmost_voice_channel.connect()
        voice_client.play(discord.FFmpegPCMAudio(source="audio/test.wav"))

        while voice_client.is_playing():
            time.sleep(.1)

        await voice_client.disconnect()

        # await message.channel.send(file=img_file)

client.run(os.getenv('DISCORD_TOKEN'))