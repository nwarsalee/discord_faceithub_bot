import discord
from discord.ext import commands
from discord.utils import get
import requests
import json

# Faceit API information
url = "https://open.faceit.com/data/v4/"
# Headers for GET request to the Faceit API

#server_config stores all information on discord servers, registered faceit hubs, registered players.
server_config = {}
# Hub information for hub id
hub_id = ""

#reads the discord bot's token from a file called token.txt
def read_token():
    with open("token.txt", "r") as f:
        lines = f.readlines()
        return lines[0].strip()

# Reads the faceit API token from a file called faceitAPI.txt
def read_api_token():
    with open("faceitAPI.txt", "r") as f:
        lines = f.readlines()
        return lines[0].strip()

# Discord Bot token and Faceit API token 
token = read_token()
headers = {"Authorization" : f"Bearer {read_api_token()}", "content-type":"json"}


# Function that loads the server config text file
def load_config():
    global server_config
    try:
        with open('server_config.txt') as json_file:
            server_config = json.load(json_file)
            print(f"Succesfully loaded server config files...")
    except IOError:
        print("Error reading file, may not exist...")

# Function to check whether a discord server is registered in the server_config dict
def check_server(ctx):
    global server_config
    # Checking if current discord server is registered in the dictionary
    if (str(ctx.guild.id) in server_config):
        return
    
    # If it's not registered, it creates a new entry for that discord server
    server_config[str(ctx.guild.id)] = { 'hub' : {'hub_id' : '', 'hub_name' : ''}, 'players' : {}}

    print(f'Created new entry for discord server with ID: {ctx.guild.id}')

# Method to save the config file that holds settings for different servers
def save_config():
    try:
        with open('server_config.txt', 'w') as outfile:
            json.dump(server_config, outfile)
            print("Saved config file...")
    except IOError:
        print("Error reading file...")


load_config()

#key to issue commands with the bot??
client = commands.Bot(command_prefix = "!")

#Checks if the bot is ready and if it is it prints Bot is ready
@client.event
async def on_ready():
   print("Bot is ready")

# Command to delete a specified amount of messages
@client.command()
async def purge(ctx, num = 1):
    await ctx.channel.purge(limit = num+1)
    print(f"{num} messages have been deleted from {ctx.channel}")

# move command that moves a person to a targeted discord voice channel
async def move(ctx, name, target):
    await name.move_to(target)


# Command for registering a faceit user in relation to their discord id
@client.command(aliases = ["reg", "r"])
async def register(ctx, faceit: str):
    # Taking note of the user's discord name
    discord = ctx.message.author

    # Making sure the server is registered
    check_server(ctx)

    # Checking if the faceit name is present in the dictionary
    if faceit in server_config[str(ctx.guild.id)]['players'].values():
        await ctx.send(f"faceit user, {faceit}, has already been registered.")
        print("tried registering an already previously registered user")
    else:
        server_config[str(ctx.guild.id)]['players'][discord.id] = faceit # Creating entry into the players dictionary for the new player
        save_config()

# Command for registering a faceit hub
@client.command(aliases = ["registerhub", "rh"])
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
    
    # Checking if a hub wasn't found
    if (len(hub_id) == 0):
        print(f"Could not find a hub associated with {hub_name}")
        await ctx.send(f"Could not find a hub named {hub_name}. Please verify the name and try again...")
        return

    # Checking to make sure the current server is registered...
    check_server(ctx)

    # Saving the hub information to the dictionary
    server_config[str(ctx.guild.id)]['hub']['hub_id'] = hub_id
    server_config[str(ctx.guild.id)]['hub']['hub_name'] = hub_name

    # Saving the server_config dict in a file
    save_config()

    # Printing the success statements
    print(f"Succesfully registered hub {hub_name} with id {hub_id}...")
    await ctx.send(f"Succesfully registered hub {hub_name} as the primary hub for this bot.")


# Command for moving players to their respective team's voice channel for a CS 10 Man
@client.command(aliases = ["START"])
async def start(ctx):
    # Building the request url and query parameters
    my_param = {"offset":"0", "limit":"3"}
    req_url = url + "hubs/" + server_config[str(ctx.guild.id)]['hub']['hub_id'] + "/matches"

    print(f"Searching for matches in hub {server_config[str(ctx.guild.id)]['hub']['hub_id']} using url {req_url}")

    # Searching for the hub requested...
    res = requests.get(req_url, headers=headers, params=my_param)

    # Checking if the get request worked
    if (res.status_code != 200):
        print("Error requesting hub matches...")
        await ctx.send(f"There was an error searching for the current match.")
        return

    # Taking note of the first match in the list
    match_data = res.json()['items'][0]

    # Checking if the match status is READY or ONGOING
    if (match_data['status'] != 'READY' and match_data['status'] != 'ONGOING'):
        print("There is no match that is READY or ONGOING...")
        await ctx.send(f"There is no match that is READY or is ONGOING. Please try again when match is starting...")
        return

    # Looping through the members in the voice channel
    channel_members = ctx.message.author.voice.channel.members

    # Two lists that will hold the information for both teams
    t1 = get_player_names(match_data['teams']['faction1']['roster'])
    t2 = get_player_names(match_data['teams']['faction2']['roster'])

    print("T1 info")
    print(t1)

    print("T2 info")
    print(t2)

    print("Printing the members of this channel")
    # Traversing the list of members in the voice channel
    for member in channel_members:
        print(f"User: {member.name} | ID: {member.id}")

        # Making sure current member is registered
        if str(member.id) in server_config[str(ctx.guild.id)]['players']:
            continue

        # Checking if they are in team 1
        if server_config[str(ctx.guild.id)]['players'][str(member.id)] in t1:
            await move(ctx, member, get(ctx.guild.voice_channels, name = "CSGO"))
            print(f"Moving {member.name} to team 1 channel")
        elif server_config[str(ctx.guild.id)]['players'][str(member.id)] in t2:
            await move(ctx, member, get(ctx.guild.voice_channels, name = "CSGO II"))
            print(f"Moving {member.name} to team 2 channel")
        else:
            print(f"Player {member.name} is not part of current match")
    
# Function that filters out all the other faceit player information and only makes a list of names
def get_player_names(team):
    player_list = []
    for p in team:
        player_list.append(p['nickname'])
    return player_list

# Command used to display the list of all registered players
@client.command(aliases = ["pl"])
async def playersList(ctx):
    global server_config

    players = server_config[str(ctx.guild.id)]['players']

    print(f"Printing all players in the list of players")
    for key in players:
        await ctx.send(f"Discord ID: {key}\t\tFaceit Username: {players[key]}")
        print(f"Discord ID: {key}\t\tFaceit Username: {players[key]}")
    print(f"Finished printing all players in the list of players")

# Command used to gather information from faceit api regarding a specified player
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

# Command used to move all teams back to one voice channel upon the end of a CS 10 man game
@client.command(aliases = ["END"])
async def end(ctx):
    # move members in team1 chat back to voice channel when game is done
    for member in get(ctx.guild.voice_channels, name = "CSGO").members:
        await move(ctx, member, get(ctx.guild.voice_channels, name = "Voice Chat"))

    # move members in team 2 chat back to voice channel when game is done
    for member in get(ctx.guild.voice_channels, name = "CSGO II").members:
        await move(ctx, member, get(ctx.guild.voice_channels, name = "Voice Chat"))

client.run(token)
