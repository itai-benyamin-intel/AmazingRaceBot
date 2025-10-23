# uCode Amazing Race - Telegram Bot

A Telegram chatbot template for managing an Amazing Race game. This bot allows teams to register, track their progress through sequential challenges, and compete to finish first.

## Features

- 🏁 **Team Management**: Create and join teams
- 🎯 **Sequential Challenge Tracking**: Teams must complete challenges in order
- 🏆 **Leaderboard**: Real-time standings showing progress and finishers
- 👥 **Multi-team Support**: Support for multiple teams competing simultaneously
- 🔐 **Admin Controls**: Game start/stop, reset, and team management functionality
- 📊 **Admin Team Management**: View, edit, add, and remove teams
- 💾 **Persistent State**: Game state saved across bot restarts

## Game Structure

### Sequential Challenges
Unlike traditional scavenger hunts, this Amazing Race requires teams to complete challenges **in order**:
- Teams start with only Challenge #1 unlocked
- After completing Challenge #1, Challenge #2 is unlocked
- This continues until all challenges are completed
- The first team to complete all challenges wins!

### Winning Condition
The winner is determined by **who finishes first**, not by points. Teams that complete all challenges are ranked by their finish time.

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
- `/challenges` - View available and unlocked challenges
- `/submit <challenge_id>` - Submit a completed challenge
- `/leaderboard` - View current team standings
- `/teams` - List all teams

### Admin Commands

- `/startgame` - Start the game (allows teams to submit challenges)
- `/endgame` - End the game and show final standings
- `/reset` - Reset all game data (use with caution!)
- `/teamstatus` - View detailed status of all teams
- `/addteam <name>` - Create a team as admin
- `/editteam <old_name> <new_name>` - Rename a team
- `/removeteam <name>` - Remove a team

## Game Flow

1. **Setup Phase**
   - Admin creates challenges in `config.yml`
   - Players create/join teams using `/createteam` and `/jointeam`

2. **Game Phase**
   - Admin starts the game with `/startgame`
   - Teams complete Challenge #1 first
   - After submitting Challenge #1, Challenge #2 is unlocked
   - Teams continue sequentially through all challenges
   - First team to complete all challenges wins!

3. **End Phase**
   - Admin ends the game with `/endgame`
   - Final leaderboard is displayed
   - Winner is the team that finished first!

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
      location: "Where to go"
```

**Note**: Challenges are completed sequentially based on their ID order (1, 2, 3, etc.)

## File Structure

```
uCodeAmazingRace/
├── bot.py                 # Main bot implementation
├── game_state.py          # Game state management
├── config.yml             # Your configuration (create from example)
├── config.example.yml     # Example configuration
├── requirements.txt       # Python dependencies
├── test_game_state.py     # Unit tests
├── game_state.json        # Persistent game state (auto-generated)
└── README.md             # This file
```

## Features Explained

### Team Management
- Teams can have up to 5 members (configurable)
- Each player can only be in one team
- Team captains are the players who create the team
- Admins can create, edit, and remove teams

### Challenge System
- Challenges are defined in the configuration file
- Each challenge has an ID, name, description, and location
- **Teams must complete challenges in sequential order (1, 2, 3, etc.)**
- Each challenge can only be completed once per team
- Next challenge is unlocked only after completing the previous one

### Winning
- The winner is the **first team to complete all challenges**
- Teams that finish are ranked by their finish time
- Teams still racing are ranked by number of completed challenges
- No points system - it's a race to finish!

### Admin Controls
- Only users listed in the `admins` section can use admin commands
- Admins can start/end the game and reset state
- Admins can view detailed team status with `/teamstatus`
- Admins can manage teams (add, edit, remove)
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

### Sequential challenge issues
- Make sure challenge IDs in `config.yml` are sequential (1, 2, 3, 4, etc.)
- Teams must complete challenges in order - they cannot skip ahead

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

## License

MIT License - feel free to use this template for your own Amazing Race events!
