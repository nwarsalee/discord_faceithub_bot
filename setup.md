# Discord Faceit Hub Bot Setup
1. Invite the bot to your server
2. Ensure that your discord server has two voice channels called "CSGO", "CSGO II" and "Voice Chat" (currently bot only moves people to those two exactly named channels)
3. Type **"!registerhub <`hub_name`>"** where `hub_name` is the name of your Faceit hub as it appears on Faceit
4. Ensure that every player who will be moved by the bot is registered with the bot. 
Tell the user to type **"!register <`faceit_name`>"** where `faceit_name` is the faceit name of the user as it appears on faceit.
5. When the faceit game has been created (i.e. server and map have been chosen and the game is in warmup stage) have one user type **"!start"** in discord. Users from each team will be moved into the respective channels.
6. When the game is finished, type *"!end"* to move everyone back into the lobby voice channel.

### List of Commands
* !register <`faceit_name`> --- Adds a user to the bots list of Faceit players
* !registerhub <`hub_name`> --- Sets the default Faceit hub for hte bot to use
* !playersList              --- Gives a list of registered discord users, prints out their discord ID and Faceit name
* !start                    --- Marks start of a Faceit game, the bot will look for the first macth within the Faceit hub that has status READY and move the players to their respective voice channels
* !end                      --- Marks end of a game, the bot will take all players currently in a team voice channel and move them back to the lobby voice channel
