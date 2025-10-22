# uCode Amazing Race - Telegram Bot

A Telegram chatbot template for managing an Amazing Race game. This bot allows teams to register, track their progress through challenges, and compete for the highest score.

## Features

- 🏁 **Team Management**: Create and join teams
- 🎯 **Challenge Tracking**: Track challenge completions and scores
- 🏆 **Leaderboard**: Real-time standings
- 👥 **Multi-team Support**: Support for multiple teams competing simultaneously
- 🔐 **Admin Controls**: Game start/stop and reset functionality
- 💾 **Persistent State**: Game state saved across bot restarts

## Setup

### Prerequisites

- Python 3.8 or higher
- A Telegram Bot Token (get it from [@BotFather](https://t.me/botfather) on Telegram)

### Installation

1. Clone this repository:
```bash
git clone https://github.com/itai-benyamin-intel/uCodeAmazingRace.git
cd uCodeAmazingRace
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create your configuration file:
```bash
cp config.example.yml config.yml
```

4. Edit `config.yml` and add your Telegram bot token:
```yaml
telegram:
  bot_token: "YOUR_BOT_TOKEN_HERE"
```

5. Customize the challenges and game settings in `config.yml`

6. Add your Telegram user ID to the admins list in `config.yml`:
   - To find your user ID, message [@userinfobot](https://t.me/userinfobot) on Telegram

### Running the Bot

```bash
python bot.py
```

The bot will start and be ready to receive commands!

## Usage

### Player Commands

- `/start` - Show welcome message and available commands
- `/help` - Display all available commands
- `/createteam <team_name>` - Create a new team (you become the captain)
- `/jointeam <team_name>` - Join an existing team
- `/myteam` - View your team's information and progress
- `/challenges` - View all available challenges
- `/submit <challenge_id>` - Submit a completed challenge
- `/leaderboard` - View current team standings
- `/teams` - List all teams

### Admin Commands

- `/startgame` - Start the game (allows teams to submit challenges)
- `/endgame` - End the game and show final standings
- `/reset` - Reset all game data (use with caution!)

## Game Flow

1. **Setup Phase**
   - Admin creates challenges in `config.yml`
   - Players create/join teams using `/createteam` and `/jointeam`

2. **Game Phase**
   - Admin starts the game with `/startgame`
   - Teams complete challenges in the real world
   - Teams submit completions using `/submit <challenge_id>`
   - Scores update automatically

3. **End Phase**
   - Admin ends the game with `/endgame`
   - Final leaderboard is displayed
   - Winners are announced!

## Configuration

Edit `config.yml` to customize your game:

```yaml
game:
  name: "uCode Amazing Race"
  max_teams: 10
  max_team_size: 5
  
  challenges:
    - id: 1
      name: "Challenge Name"
      description: "What teams need to do"
      points: 10
      location: "Where to go"
```

## File Structure

```
uCodeAmazingRace/
├── bot.py                 # Main bot implementation
├── game_state.py          # Game state management
├── config.yml             # Your configuration (create from example)
├── config.example.yml     # Example configuration
├── requirements.txt       # Python dependencies
├── game_state.json        # Persistent game state (auto-generated)
└── README.md             # This file
```

## Features Explained

### Team Management
- Teams can have up to 5 members (configurable)
- Each player can only be in one team
- Team captains are the players who create the team

### Challenge System
- Challenges are defined in the configuration file
- Each challenge has an ID, name, description, location, and point value
- Teams can complete challenges in any order
- Each challenge can only be completed once per team

### Scoring
- Teams earn points by completing challenges
- Points are defined per challenge
- Leaderboard ranks teams by total points

### Admin Controls
- Only users listed in the `admins` section can use admin commands
- Admins can start/end the game and reset state
- The game must be started before teams can submit challenges

## Customization

### Adding Custom Commands

Edit `bot.py` and add new command handlers:

```python
async def my_custom_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Custom response")

# In the run() method:
application.add_handler(CommandHandler("mycommand", self.my_custom_command))
```

### Modifying Challenge Validation

You can add custom validation logic in the `submit_command` method in `bot.py` to verify challenge completions (e.g., requiring photo proof, location verification, etc.).

## Troubleshooting

### Bot doesn't respond
- Check that your bot token is correct in `config.yml`
- Ensure the bot is running (`python bot.py`)
- Check the console for error messages

### Permission errors
- Make sure you're listed in the `admins` section for admin commands
- Verify your user ID is correct

### State issues
- Delete `game_state.json` to reset the game state
- Or use the `/reset` command (admin only)

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

## License

MIT License - feel free to use this template for your own Amazing Race events!
