import discord

client = discord.Client()

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

    channel = client.get_channel.send("Here is the lates AVAX wallet cluster and top trader analysis...")

    #run with token
    client.run('YOUR_DISCORD_TOKEN')