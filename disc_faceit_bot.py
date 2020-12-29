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
token = os.environ.get('DISCORD_TOKEN_FACEIT')

faceit_api_key = os.environ.get('FACEIT_API_KEY')

# Headers for GET request to the Faceit API
headers = {"Authorization" : f"Bearer {faceit_api_key}", "content-type":"json"}

# Function that loads the database information
def load_db():
    mongoDBURI = str(os.environ.get('DB_URI'))
    global server_config_cl

    # Connect to DB hosted on Atlas using DB_URI
    # NOTE: The password in the URI string may need to be encoded by urllib.quote if it contains the '@' symbol.
    my_client = pymongo.MongoClient(mongoDBURI)
    
    # Print out connection info
    print(f"Client connection info:")
    print(my_client.server_info)
    
    # Connecting to default database
    db = my_client["heroku_gvrmd9mb"]
    
    # Connecting to bot_info collection in the database
    server_config_cl = db["bot_info"]
    
    print()
    print(db.list_collection_names())
    print("Successfully connected to MongoDB database...")

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
    # Change bot's status to include the command prefix and call to the help command
    await client.change_presence(status=discord.Status.online, activity=discord.Game('!help'))
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
    
    # Attempt to find user in databse
    disc_server = server_config_cl.find_one({"discord_server_id" : str(ctx.guild.id)})

    # Checking if the faceit name is present in the dictionary
    if faceit in disc_server['players'].values():
        await ctx.send(f"faceit user, {faceit}, has already been registered.")
        print("tried registering an already previously registered user")
    else:
        #server_config[str(ctx.guild.id)]['players'][str(discord.id)] = faceit # Creating entry into the players dictionary for the new player
        disc_server['players'][str(discord.id)] = {'faceit_name' : faceit, 'discord_name' : discord.name } # Creating entry into the players dictionary for the new player
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
    
    # Check to see if all the channels exist
    if channelExists(ctx, server_info['voice_settings']['t1']) == False or channelExists(ctx, server_info['voice_settings']['t2']) == False or channelExists(ctx, server_info['voice_settings']['general']) == False:
        await ctx.send("One of the designated voice channels do not exist, make sure voice channels have been properly set before using !start command...")

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

        # Retrieve the list of registered players, to compare against current players in voice channel
        reg_players = server_info['players']

        print(reg_players)

        # list to store all encountered unregistered players.
        unregistered_players = []

        # Making sure current member is registered
        if str(member.id) not in reg_players:
            print(f"Member {member.name} is not registered...")
            continue

        # Checking if they are in team 1
        if reg_players[str(member.id)]["faceit_name"] in t1:
            await move(ctx, member, get(ctx.guild.voice_channels, name = str(server_info['voice_settings']['t1'])))
            print(f"Moving {member.name} to team 1 channel")
        
        # Checking if they are in team 2
        elif reg_players[str(member.id)]["faceit_name"] in t2:
            await move(ctx, member, get(ctx.guild.voice_channels, name = str(server_info['voice_settings']['t2'])))
            print(f"Moving {member.name} to team 2 channel")
        
        # Case for when player is not in the match
        else:
            unregistered_players.append(member.name)
            print(f"Player {member.name} is not part of current match")
    
    # Emote vars
    g_emote = ":regional_indicator_g:"
    l_emote = ":regional_indicator_l:"
    h_emote = ":regional_indicator_h:"
    f_emote = ":regional_indicator_f:"

    # Generic match start string that the bot outputs
    match_start_str = "**{0}{1}{2}{3} MATCH STARTED {0}{1}{2}{3}**".format(g_emote, l_emote, h_emote, f_emote)

    # All players inside the lobby channel were registered
    if len(unregistered_players) == 0:
        await ctx.send(match_start_str)
    
    # Notify which players could not be moved
    else:
        await ctx.send("{}\nCould not move the following players...\n{}".format(match_start_str, ", ".join(unregistered_players)))

# Command used to move all teams back to one voice channel upon the end of a CS 10 man game
@client.command(aliases = ["END"])
async def end(ctx):
    check_server(ctx)

    server_info = server_config_cl.find_one({"discord_server_id" : str(ctx.guild.id)})
    print(f"t1: {server_info['voice_settings']['t1']}, t2: {server_info['voice_settings']['t2']}, general: {server_info['voice_settings']['general']}")
    print(get(ctx.guild.voice_channels, name = str(server_info['voice_settings']['t1'])))

    # TODO: Add check to see if the voice channels that are set actually exist

    g_emote = ":regional_indicator_g:"

    await ctx.send("**{0}{0} MATCH END {0}{0}**\nMoving all players back to lobby...".format(g_emote))

    # move members in team1 chat back to voice channel when game is done
    for member in get(ctx.guild.voice_channels, name = str(server_info['voice_settings']['t1'])).members:
        await move(ctx, member, get(ctx.guild.voice_channels, name = str(server_info['voice_settings']['general'])))

    # move members in team 2 chat back to voice channel when game is done
    for member in get(ctx.guild.voice_channels, name = str(server_info['voice_settings']['t2'])).members:
        await move(ctx, member, get(ctx.guild.voice_channels, name = str(server_info['voice_settings']['general'])))

# Command that changes what the lobby voice channel is
@client.command(aliases = ["setg"])
async def setgen(ctx, general):
    if channelExists(ctx, general) == False:
        await ctx.send(f"**Voice channel '{general}' does not exist...**")
        return

    server_info = server_config_cl.find_one({"discord_server_id" : str(ctx.guild.id)})
    print(server_info)
    server_info['voice_settings']['general'] = general
    server_config_cl.update_one({"discord_server_id" : str(ctx.guild.id)}, {"$set" : server_info})
    await ctx.send(f"**Lobby voice channel has been changed to {general} **") 

# Command that changes what team 1's voice channel is
@client.command(aliases = ["set1"])
async def sett1(ctx, team1):
    if channelExists(ctx, team1) == False:
        await ctx.send(f"**Voice channel '{team1}' does not exist...**")
        return

    server_info = server_config_cl.find_one({"discord_server_id" : str(ctx.guild.id)})
    print(server_info)
    server_info['voice_settings']['t1'] = team1
    server_config_cl.update_one({"discord_server_id" : str(ctx.guild.id)}, {"$set" : server_info})
    await ctx.send(f"**Team 1 voice channel has been changed to {team1} **")     

# Command that changes what team 1's voice channel is
@client.command(aliases = ["set2"])
async def sett2(ctx, team2):
    if channelExists(ctx, team2) == False:
        await ctx.send(f"**Voice channel '{team2}' does not exist...**")
        return

    server_info = server_config_cl.find_one({"discord_server_id" : str(ctx.guild.id)})
    print(server_info)
    server_info['voice_settings']['t2'] = team2
    server_config_cl.update_one({"discord_server_id" : str(ctx.guild.id)}, {"$set" : server_info})
    await ctx.send(f"**Team 2 voice channel has been changed to {team2} **")    

# Command that changes the voice channels for General, Team 1 and Team 2
@client.command()
async def setvcs(ctx, general, team1, team2):
    await setgen(ctx, general)
    await sett1(ctx, team1)
    await sett2(ctx, team2)

# Function that checks to see if a voice channel exists
def channelExists(ctx, channel_name):
    if get(ctx.guild.voice_channels, name = channel_name) == None:
        return False
    else:
        return True

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

    # Get player information from database
    players = server_config_cl.find_one({"discord_server_id" : str(ctx.guild.id)})
    players = players['players']

    # Create new embed to add in help information
    embed = discord.Embed(
        title = "Player List",
        description = "Provides a list of all players that have registered their Faceit names to the bot. Shows Faceit name first then associated Discord name.",
        color = discord.Color.blue()
    )

    # Checking case where there are no players registered
    if len(players.keys()) == 0:
        embed.add_field(name="Not Available", value="*There are no players registered on this discord server...*", inline=False)
    else:
        # Creates embed field for all players that have been registered
        for key in players:
            # Retrieving the associated faceit name and discord name for the current discord ID
            faceit_user = players[key]['faceit_name']
            disc_user   = players[key]['discord_name']

            # Add embed field of the users faceitname and discord name
            embed.add_field(name=faceit_user, value=disc_user, inline=False)
            
    # Send back embed to voice channel
    await ctx.channel.send(embed=embed)

# Command used to gather information from faceit api regarding a specified player
# NOTE: This command is was used mostly for testing and is not intended for actual use by user.
#       This is the reason this command is not featured in the help menu
@client.command()
async def player(ctx, name: str):
    print(name)
    global headers

    # Setting up query param values and endpoint
    my_param = {"nickname":name, "offset":"0", "limit":"20"}
    req_url = url + "search/players"
    # Add query params and endpoint to request URL
    res = requests.get(req_url, headers=headers, params=my_param)
    
    # Printing the url
    print(res.url)
    # Printing the status
    print(res.status_code)
    # Printing the response to the console
    print(res.json())

    # Retrieve the response data
    data = res.json()['items'][0]

    # Sending message to Discord text chat
    await ctx.send(f"Faceit user {data['nickname']} has ID {data['player_id']}")

# Command used to give the general settings of the server
@client.command(aliases = ["i"])
async def info(ctx):
    check_server(ctx)

    # Get server information from database
    server_info = server_config_cl.find_one({"discord_server_id" : str(ctx.guild.id)})

    # Create new embed to add in help information
    embed = discord.Embed(
        title = "Info Menu",
        description = "Shows what hub is registered under this discord server and the set voice channels.",
        color = discord.Color.blue()
    )

    # Registered faceithub info
    if server_info['hub']['hub_name'] == '':
        hub_output = "*There is no registered Faceit hub for this discord server...*"
    else:
        hub_output = server_info['hub']['hub_name']

    embed.add_field(name="Registered Faceit hub", value=hub_output, inline=False)

    # Lobby voice channel info
    embed.add_field(name="Lobby Voice Channel", value=server_info['voice_settings']['general'])

    # Team 1 voice channel info
    embed.add_field(name="Team I Channel", value=server_info['voice_settings']['t1'])

    # Team 2 voice channel info
    embed.add_field(name="Team II Voice Channel", value=server_info['voice_settings']['t2'])

    # Send back embed to voice channel
    await ctx.channel.send(embed=embed)

# Command for help command
@client.command()
async def help(ctx):
    # Create new embed to add in help information
    embed = discord.Embed(
        title = "Help Menu",
        description = "List of commands for GabeN-Bot (FaceitHub bot)\n\nCommand prefix: **!**",
        color = discord.Color.blue()
    )
    
    # Help command
    embed.add_field(name="!help", value="*Provides a list of available commands*", inline=False)

    # Register hub command
    embed.add_field(name="!reghub  <hub_name>", value="*Assigns faceit hub with name <hub_name> to discord server.*", inline=False)

    # Register player command
    embed.add_field(name="!reg <faceit_name>", value="*Assigns faceit player <faceit_name> to the discord user who invoked to command.*", inline=False)

    # Player list command
    embed.add_field(name="!pl", value="*Provides a list of all the players that have registered their faceit name to the server.*", inline=False)

    # Info command
    embed.add_field(name="!info", value="*Displays the information about the Faceit hub that is registered.*", inline=False)

    # Start match command
    embed.add_field(name="!start", value="*Indicates start of match. Moves all players to their respective team channels.*", inline=False)

    # End match command
    embed.add_field(name="!end", value="*Indicates end of match. Moves all players back to main voice channel.*", inline=False)

    # Set main voice channel command
    embed.add_field(name="!setgen  <voice_channel_name>", value="*Assigns the lobby voice channel to <voice_channel_name>.*", inline=False)

    # Set team 1 voice channel command
    embed.add_field(name="!sett1  <voice_channel_name>", value="*Assigns team 1's voice channel to <voice_channel_name>.*", inline=False)

    # Set team 2 voice channel command
    embed.add_field(name="!sett2  <voice_channel_name>", value="*Assigns team 2's voice channel to <voice_channel_name>.*", inline=False)

    # Set all voice channels command
    embed.add_field(name="!setvcs  <channel1>  <channel2>  <channel3>", value="*Assigns the lobby, team 1 and team 2's voice channels respectively*", inline=False)

    # Send back embed to voice channel
    await ctx.channel.send(embed=embed)

# Load database before starting up discord bot instance
load_db()

# Start discord bot
client.run(token)
