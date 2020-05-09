import discord
from discord.ext import commands
from discord.utils import get
import requests

# Discord Bot token
token = "<Enter your Discord Bot Token Here>"

# Faceit API information
url = "https://open.faceit.com/data/v4/"
# Headers for GET request to the Faceit API
headers = {"Authorization" : "Bearer <Enter the Faceit API Server Token here>", "content-type":"json"}

#Players list: Key's are faceit usernames and values are discord usernames.
players = {}
def playersDict():
    with open("players.txt", "r") as f:
        line = f.readline()
        while line != "":
            faceit = line.split(":")[0]
            discord = line.split(":")[1]
            players[faceit] = discord
            line = f.readline()
playersDict()
        

#key to issue commands with the bot??
client = commands.Bot(command_prefix = "!")

#Checks if the bot is ready and if it is it prints Bot is ready
@client.event
async def on_ready():
   print("Bot is ready")

@client.command()
async def purge(ctx, num = 1):
    await ctx.channel.purge(limit = num+1)
    print(f"{num} messages have been deleted from {ctx.channel}")

@client.command()
async def join(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients)

    if voice and voice.is_connected():
        await voice.move_to(channel)
    else:
        voice = await channel.connect()
    await ctx.send(f'Joined {channel}')
    print(f"GabeN has joined {channel}")

@client.command()
async def leave(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients)
    
    if voice and voice.is_connected:
        await voice.disconnect()
    await ctx.send(f"Left {channel}")
    print(f"GabeN has left {channel}")

@client.command(aliases = ["GabeN", "GABEN", "G", "g"])
async def gaben(ctx):
    url = "https://www.youtube.com/watch?v=1DC6RAr2xcM"

    await ctx.send("Hi im Gabe Newell of Valve Software.")

    #Joining functionality upon gaben call 
    await join(ctx)

    #Code for playing song goes here...


    #Leaving functionality after playing gaben videos
    await leave(ctx)
    
@client.command()
async def move(ctx):
    channelName = ctx.message.author.voice.channel.name
    to = get(ctx.guild.voice_channels, name = "Test")

    if channelName == (to.name):
        to = get(ctx.guild.voice_channels, name = "General")
        await ctx.message.author.move_to(to)
    else:
        await ctx.message.author.move_to(to)

    print(f"{ctx.message.author} has been moved to {to}")

@client.command(aliases = ["ls", "LIST", "l"])
async def list(ctx, channel):
    members = get(ctx.guild.voice_channels, name = channel).members

    print(f"Printing all members in voice channel {get(ctx.guild.voice_channels, name = channel)}")
    for person in members:
        await ctx.send(person)
        print(f"{person}")
    print(f"Finished printing all members in voice channel {get(ctx.guild.voice_channels, name = channel)}")


@client.command(aliases = ["reg", "r"])
async def register(ctx, faceit: str):
    discord = ctx.message.author

    if faceit in players:
        await ctx.send(f"faceit user, {faceit}, has already been registered.")
        print("tried registering an already previously registered user")
    else:
        with open("players.txt", "a") as f:
            f.write(f"{faceit}:{discord}\n")
            players[faceit] = discord
            await ctx.send(f"The faceit user, {faceit}, has been added to the list under {discord.mention}'s discord.")
            print(f"Faceit: {faceit}    Discord: {discord}  has been added to the list of players")

@client.command()
async def reghub(ctx, hub_name: str):
    my_param = {"name":hub_name, "offset":"0", "limit":"3"}
    req_url = url + "search/hubs"

    print(f"Searching for {hub_name}")

    # Searching for the hub requested...
    res = requests.get(req_url, headers=headers, params=my_param)

    # Making sure the status is 200 (OK)
    if (res.status_code != 200):
        print(f"Error, status {res.status} when GET'ing info...")
        await ctx.send(f"There was an error searching for the hub. Verify information and please try again...")
        return

    # Saving the list of search results
    data = res.json()['items']
    hub_id = ""

    # looking through the search results to find the hub
    for result in data:
        if result['name'] == hub_name:
            hub_id = result["competition_id"]
            print("Found hub...")
            break
    
    # Checking if a hub was actually found
    if (len(hub_id) == 0):
        print(f"Could not find a hub associated with {hub_name}")
        await ctx.send(f"Could not find a hub named {hub_name}. Please verify the name and try again...")
        return

    # Making a dictionary that stores the hub_id
    hub_dict = {'hub_id':hub_id}

    # Sending hub id to a file
    with open('hub_id.txt', 'w') as outfile:
        json.dump(hub_dict, outfile)

    # Printing the success statements
    print(f"Succesfully registered hub {hub_name} with id {hub_id}...")
    await ctx.send(f"Succesfully registered hub {hub_name} as the primary hub for this bot.")
    


@client.command(aliases = ["pl"])
async def playersList(ctx):
    global players

    print(f"Printing all players in the list of players")
    for key in players:
        await ctx.send(f"Faceit: {key}         Discord: {players[key]}")
        print(f"Faceit: {key}         Discord: {players[key]}")
    print(f"Finsished printing all players in the list of players")

@client.command(aliases = ["VC"])
async def vc(ctx, name = "new VC"):
        await ctx.guild.create_voice_channel(name)
        print(f"A new voice channel, {name}, has been created.")

@client.command()
async def player(ctx, name: str):
    print(name)
    global headers
    my_param = {"nickname":name, "offset":"0", "limit":"20"}
    req_url = url + "search/players"

    res = requests.get(req_url, headers=headers, params=my_param)
    #Printing the url
    print(res.url)
    # Printing the status
    print(res.status_code)

    # Printing the response to the console
    print(res.json())

    data = res.json()['items'][0]

    # Sending message to Discord text chat
    await ctx.send(f"Faceit user {data['nickname']} has ID {data['player_id']}")
    
client.run(token)
