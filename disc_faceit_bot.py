import discord
from discord.ext import commands
from discord.utils import get
import requests
import json
import pymongo
import os

# Faceit API information
url = "https://open.faceit.com/data/v4/"

# Object to database collection
server_config_cl = None

# Discord Bot token and Faceit API token 
token = os.environ.get('DISCORD_TOKEN')

faceit_api_key = os.environ.get('FACEIT_API_KEY')

# Headers for GET request to the Faceit API
headers = {"Authorization" : f"Bearer {faceit_api_key}", "content-type":"json"}

# Function that loads the database information
def load_db():
    mongoDb = os.environ.get('MONGODB_URI')
    global server_config_cl

    # Creating client connection with database
    my_client = pymongo.MongoClient(mongoDb)
    print(f"Client connection info:")
    print(my_client.server_info)

    # Connecting to default database
    db = my_client["heroku_gvrmd9mb"]

    # Connecting to bot_info collection in the database
    server_config_cl = db["bot_info"]

    print(db.list_collection_names())

# Function to check whether a discord server is registered in the server_config dict
def check_server(ctx):
    global server_config_cl

    # Querying database to find discord server with current id
    results = server_config_cl.find_one({"discord_server_id" : str(ctx.guild.id)})
    print(results)

    # Checking if current discord server is registered in the dictionary
    if (results != None):
        print("discord server registered in db, continuing...")
        return
    
    # If it's not registered, it creates a new entry for that discord server
    #server_config[str(ctx.guild.id)] = { 'hub' : {'hub_id' : '', 'hub_name' : ''}, 'players' : {}}
    # Inserts new document for the discord server
    server_config_cl.insert_one({'discord_server_id' : str(ctx.guild.id), 'hub' : {'hub_id' : '', 'hub_name' : ''}, 'players' : {}, "voice_settings" : { "general" : "Voice Chat", "t1" : "CSGO I", "t2" : "CSGO II" }})

    print(f'Created new entry for discord server with ID: {ctx.guild.id}')

#key to issue commands with the bot??
client = commands.Bot(command_prefix = "!")
client.remove_command('help')

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
    
    disc_server = server_config_cl.find_one({"discord_server_id" : str(ctx.guild.id)})

    # Checking if the faceit name is present in the dictionary
    if faceit in disc_server['players'].values():
        await ctx.send(f"faceit user, {faceit}, has already been registered.")
        print("tried registering an already previously registered user")
    else:
        #server_config[str(ctx.guild.id)]['players'][str(discord.id)] = faceit # Creating entry into the players dictionary for the new player
        disc_server['players'][str(discord.id)] = faceit # Creating entry into the players dictionary for the new player
        server_config_cl.update_one({"discord_server_id" : str(ctx.guild.id)}, {"$set":disc_server})
        await ctx.send(f"Faceit user, {faceit}, has been registered under {discord.mention}'s Discord.'")
        #save_config()

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
    discord_server = server_config_cl.find_one({"discord_server_id" : str(ctx.guild.id)})
    print(discord_server)
    discord_server['hub']['hub_id']   = hub_id
    discord_server['hub']['hub_name'] = hub_name

    # Save to database
    server_config_cl.update_one({"discord_server_id" : str(ctx.guild.id)}, {"$set":discord_server})

    # Printing the success statements
    print(f"Successfully registered hub {hub_name} with id {hub_id}...")
    await ctx.send(f"Succesfully registered hub {hub_name} as the primary hub for this bot.")


# Command for moving players to their respective team's voice channel for a CS 10 Man
@client.command(aliases = ["START"])
async def start(ctx):
    # Checking if the server is registered
    check_server(ctx)

    server_info = server_config_cl.find_one({"discord_server_id" : str(ctx.guild.id)})
    print(f"t1: {server_info['voice_settings']['t1']}, t2: {server_info['voice_settings']['t2']}, general: {server_info['voice_settings']['general']}")
    

    # Building the request url and query parameters
    my_param = {"offset":"0", "limit":"3"}
    req_url = url + "hubs/" + server_info['hub']['hub_id'] + "/matches"

    print(f"Searching for matches in hub {server_info['hub']['hub_id']} using url {req_url}")

    # Searching for the hub requested...
    res = requests.get(req_url, headers=headers, params=my_param)

    # Checking if they have registered a hub under this server
    if server_info['hub']['hub_id'] == '':
        print("Error, no hub has been registered...")
        await ctx.send("Can't start until a hub is registered under this server...")
        return

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

    # Two lists that will hold the information for both teams.
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

        reg_players = server_info['players'].keys()

        print(reg_players)

        # Making sure current member is registered
        if str(member.id) not in reg_players:
            print(f"Member {member.name} is not registered...")
            continue

        # Checking if they are in team 1
        if reg_players[str(member.id)] in t1:
            await move(ctx, member, get(ctx.guild.voice_channels, name = str(server_info['voice_settings']['t1'])))
            print(f"Moving {member.name} to team 1 channel")
        elif reg_players[str(member.id)] in t2:
            await move(ctx, member, get(ctx.guild.voice_channels, name = str(server_info['voice_settings']['t2'])))
            print(f"Moving {member.name} to team 2 channel")
        else:
            print(f"Player {member.name} is not part of current match")

# Command used to move all teams back to one voice channel upon the end of a CS 10 man game
@client.command(aliases = ["END"])
async def end(ctx):
    check_server(ctx)

    server_info = server_config_cl.find_one({"discord_server_id" : str(ctx.guild.id)})
    print(f"t1: {server_info['voice_settings']['t1']}, t2: {server_info['voice_settings']['t2']}, general: {server_info['voice_settings']['general']}")
    print(get(ctx.guild.voice_channels, name = str(server_info['voice_settings']['t1'])))

    # TODO: Add check to see if the voice channels that are set actually exist

    # move members in team1 chat back to voice channel when game is done
    for member in get(ctx.guild.voice_channels, name = str(server_info['voice_settings']['t1'])).members:
        await move(ctx, member, get(ctx.guild.voice_channels, name = str(server_info['voice_settings']['general'])))

    # move members in team 2 chat back to voice channel when game is done
    for member in get(ctx.guild.voice_channels, name = str(server_info['voice_settings']['t2'])).members:
        await move(ctx, member, get(ctx.guild.voice_channels, name = str(server_info['voice_settings']['general'])))

# Command that changes what the lobby voice channel is
@client.command(aliases = ["setg"])
async def setgen(ctx, general):
    server_info = server_config_cl.find_one({"discord_server_id" : str(ctx.guild.id)})
    print(server_info)
    server_info['voice_settings']['general'] = general
    server_config_cl.update_one({"discord_server_id" : str(ctx.guild.id)}, {"$set" : server_info})
    await ctx.send(f"Lobby voice channel has been changed to {general} ") 

# Command that changes what team 1's voice channel is
@client.command(aliases = ["set1"])
async def sett1(ctx, team1):
    server_info = server_config_cl.find_one({"discord_server_id" : str(ctx.guild.id)})
    print(server_info)
    server_info['voice_settings']['t1'] = team1
    server_config_cl.update_one({"discord_server_id" : str(ctx.guild.id)}, {"$set" : server_info})
    await ctx.send(f"Team 1 voice channel has been changed to {team1} ")     

# Command that changes what team 1's voice channel is
@client.command(aliases = ["set2"])
async def sett2(ctx, team2):
    server_info = server_config_cl.find_one({"discord_server_id" : str(ctx.guild.id)})
    print(server_info)
    server_info['voice_settings']['t2'] = team2
    server_config_cl.update_one({"discord_server_id" : str(ctx.guild.id)}, {"$set" : server_info})
    await ctx.send(f"Team 2 voice channel has been changed to {team2} ")    

# Command that changes the voice channels for General, Team 1 and Team 2
@client.command()
async def setvcs(ctx, general, team1, team2):
    await setgen(ctx, general)
    await sett1(ctx, team1)
    await sett2(ctx, team2)

# Function that filters out all the other faceit player information and only makes a list of names
def get_player_names(team):
    player_list = []
    for p in team:
        player_list.append(p['nickname'])
    return player_list

# Command used to display the list of all registered players
@client.command(aliases = ["pl"])
async def playersList(ctx):
    # Making sure the server is registered
    check_server(ctx)

    players = server_config_cl.find_one({"discord_server_id" : str(ctx.guild.id)})
    players = players['players']
    pString = ""

    # Checking case where there are no players registered
    if len(players.keys()) == 0:
        print("There is no one registered yet...")
        await ctx.send("No players registered on this server...")
    else:
        # Creates String for all players that have been registered
        for key in players:
            pString = pString + f"Discord ID: {key}\t\tFaceit Username: {players[key]}\n"
            print(f"Discord ID: {key}\t\tFaceit Username: {players[key]}")
        # Prints the string of registered players to discord
        print(f"Printing all players in the list of players")
        await ctx.send(pString)
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

# Command used to give the general settings of the server
@client.command(aliases = ["i"])
async def info(ctx):
    check_server(ctx)

    server_info = server_config_cl.find_one({"discord_server_id" : str(ctx.guild.id)})

    if(server_info['hub'] == ''):
        await ctx.send("There is no hub registered to this server.")
        print(f"Server has no registered hub...")
    else:
        await ctx.send(f"Server has `{server_info['hub']['hub_name']}` registered as its primary hub...")
        print(f"Server has faceit hub w/ id: {server_info['hub']['hub_id']} registered as its primary hub...")

        print("Printing registered players...")
        await ctx.send(f"Registered Players in {server_info['hub']['hub_name']}:")
        await playersList(ctx)

    #Printing the set voice channels
    print("printing lobby voice channel")
    await ctx.send(f"Lobby Voice Channel:     {server_info['voice_settings']['general']}")

    print("printing team 1 voice channel")
    await ctx.send(f"Team 1 Voice Channel:     {server_info['voice_settings']['t1']}")

    print("printing team 2 voice channel")
    await ctx.send(f"Team 2 Voice Channel:     {server_info['voice_settings']['t2']}")

# Command for help command
@client.command()
async def help(ctx):
    # Building the help string
    help_string = "Available commands \n"
    help_string += "{:8} {:20} {}\n".format("Command ", "| Argument", "| Description")
    help_string += "-------------------------------------------------------------\n"
    help_string += "{:10} {:20} {}\n".format("!help", "", "Provides a list of available commands")
    help_string += "{:10} {:20} {}\n".format("!reghub", "<hub_name>", "Assigns faceit hub with name <hub_name> to discord server")
    help_string += "{:10} {:20} {}\n".format("!reg", "<faceit_name>", "Assigns faceit player <faceit_name> with the discord user who invoked to command")
    help_string += "{:10} {:20} {}\n".format("!pl", "", "Provides a list of all the players that have registered their faceit name to the server")
    help_string += "{:10} {:20} {}\n".format("!info", "", "Displays the information about the Faceit hub that is registered")
    help_string += "{:10} {:20} {}\n".format("!start", "", "Moves all players to their respective team's voice channel")
    help_string += "{:10} {:20} {}\n".format("!end", "", "Moves all players back to general voice channel")
    help_string += "{:10} {:20} {}\n".format("!setgen", "<voice_channel_name>", "Assigns the lobby voice channel to <voice_channel_name>")
    help_string += "{:10} {:20} {}\n".format("!sett1", "<voice_channel_name>", "Assigns team 1's voice channel to <voice_channel_name>")
    help_string += "{:10} {:20} {}\n".format("!sett2", "<voice_channel_name>", "Assigns team 2's voice channel to <voice_channel_name>")
    help_string += "{:10} {:20} {}\n".format("!setvcs", "<voice_channel_name1>, <voice_channel_name2>, <voice_channel_name3>", "Changes the lobby, team 1 and team 2's voice channels respectively")

    await ctx.send(help_string)

load_db()

client.run(token)