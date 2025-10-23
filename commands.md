# Bot Commands for BotFather

This file contains the list of commands in a format compatible with Telegram's BotFather.
Use this to set up the bot's command menu by sending these commands to @BotFather.

## How to Use

1. Open a chat with [@BotFather](https://t.me/botfather) on Telegram
2. Send the command `/setcommands`
3. Select your bot
4. Copy and paste the commands below (without the headers)

## Commands List

### Player Commands
```
start - Show welcome message and get started
help - Display all available commands
createteam - Create a new team (usage: /createteam <team_name>)
jointeam - Join an existing team (usage: /jointeam <team_name>)
myteam - View your team information and progress
challenges - View completed and current challenge
current - View your current challenge
hint - Get a hint (costs 2 min penalty)
submit - Submit current challenge (usage: /submit [answer])
leaderboard - View current team standings
teams - List all teams
contact - Contact the bot admin
```

### Admin Commands
```
startgame - Start the game (admin only)
endgame - End the game and show final standings (admin only)
reset - Reset all game data (admin only)
teamstatus - View detailed status of all teams (admin only)
addteam - Create a team as admin (usage: /addteam <name>)
editteam - Rename a team (usage: /editteam <old_name> <new_name>)
removeteam - Remove a team (usage: /removeteam <name>)
togglelocation - Toggle location verification on/off (admin only)
```

## All Commands (Combined Format for BotFather)

Copy everything below this line and paste it to BotFather when asked:

```
start - Show welcome message and get started
help - Display all available commands
createteam - Create a new team
jointeam - Join an existing team
myteam - View your team information and progress
challenges - View completed and current challenge
current - View your current challenge
hint - Get a hint (costs 2 min penalty)
submit - Submit current challenge
leaderboard - View current team standings
teams - List all teams
contact - Contact the bot admin
startgame - Start the game (admin only)
endgame - End the game (admin only)
reset - Reset all game data (admin only)
teamstatus - View detailed team status (admin only)
addteam - Create a team (admin only)
editteam - Rename a team (admin only)
removeteam - Remove a team (admin only)
togglelocation - Toggle location verification (admin only)
```

## Notes

- Commands marked with "(admin only)" are restricted to the configured admin user
- Player commands are available to all users
- Some commands require parameters - use `/help` in the bot for detailed usage information
- The bot menu in Telegram will display these commands when users type `/` in the chat
