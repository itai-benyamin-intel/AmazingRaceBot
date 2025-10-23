# uCode Amazing Race - Telegram Bot

A Telegram chatbot template for managing an Amazing Race game. This bot allows teams to register, track their progress through sequential challenges, and compete to finish first.

## Features

- 🏁 **Team Management**: Create and join teams
- 🎯 **Sequential Challenge Tracking**: Teams must complete challenges in order
- 💡 **Hints System**: Teams can request up to 3 hints per challenge with time penalties
- 📷 **Challenge Types System**: Support for diverse challenge types with automatic verification
- 📍 **Location-Based Verification**: Optional GPS-based verification for physical challenge locations
- 🏆 **Leaderboard**: Real-time standings showing progress and finishers
- 👥 **Multi-team Support**: Support for multiple teams competing simultaneously
- 🔐 **Admin Controls**: Game start/stop, reset, and team management functionality
- 📊 **Admin Team Management**: View, edit, add, and remove teams
- 💾 **Persistent State**: Game state saved across bot restarts

## Challenge Types

The bot supports various challenge types with different verification methods:

### Supported Challenge Types

1. **📷 Photo Challenge**: Teams submit photos (e.g., team photo at location, completed puzzle)
   - Verification: Photo submission (auto-accepted)
   
2. **🧩 Riddle/Clue Challenge**: Teams solve riddles or puzzles
   - Verification: Text answer (auto-checked)
   
3. **💻 Code Challenge**: Teams write or debug code
   - Verification: Text submission with keyword matching
   
4. **📱 QR Hunt Challenge**: Teams find and scan QR codes
   - Verification: Text answer from QR code
   
5. **❓ Trivia Challenge**: Teams answer questions
   - Verification: Text answer (supports multiple keywords)
   
6. **🔍 Scavenger Hunt**: Teams find and document items
   - Verification: Photo submission
   
7. **🤝 Team Activity**: Teams perform activities together
   - Verification: Photo/video submission
   
8. **🔐 Decryption Challenge**: Teams decrypt encoded messages
   - Verification: Text answer

### Verification Methods

- **Photo**: Teams submit a photo which is automatically accepted and sent to admin
- **Answer**: Text answer is automatically verified against configured answer(s)
  - Supports exact match or keyword matching
  - Case-insensitive comparison
  - For trivia: supports multiple required keywords (comma-separated)

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

6. Add your Telegram user ID to the admin field in `config.yml`:
   - To find your user ID, message [@userinfobot](https://t.me/userinfobot) on Telegram
   - Note: Only one admin is supported

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
- `/challenges` - View completed challenges and your current challenge
- `/current_challenge` - View your current challenge (shows available/used hints)
- `/hint` - Request a hint for the current challenge (costs 2 min penalty)
- `/submit [answer]` - Submit current challenge
  - For photo challenges: `/submit` then send a photo
  - For answer challenges: `/submit <your answer>`
- `/leaderboard` - View current team standings
- `/teams` - List all teams
- `/contact` - Contact the bot admin

### Admin Commands

- `/startgame` - Start the game (allows teams to submit challenges)
- `/endgame` - End the game and show final standings
- `/reset` - Reset all game data (use with caution!)
- `/teamstatus` - View detailed status of all teams
- `/addteam <name>` - Create a team as admin
- `/editteam <old_name> <new_name>` - Rename a team
- `/removeteam <name>` - Remove a team
- `/togglelocation` - Enable/disable location-based verification globally

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

## Hints System

The bot supports an optional hints system that allows teams to request help when stuck on a challenge. Each hint comes with a time penalty that delays the next challenge.

### How It Works

1. **Hints Configuration**: Each challenge can have up to 3 hints defined in `config.yml`
2. **Requesting Hints**: Teams use `/hint` to request the next available hint
3. **Confirmation**: Bot asks for confirmation, warning about the 2-minute penalty
4. **Team Broadcast**: When approved, the hint is sent to all team members
5. **Penalty Applied**: When the challenge is completed, a timer delays the next challenge unlock
6. **Maximum Penalty**: With 3 hints used, teams wait 6 minutes before the next challenge

### For Teams

**To request a hint:**
```
/hint
```

The bot will:
- Show any previously used hints
- Ask for confirmation (warns about 2-minute penalty)
- Display current penalty time
- Reveal the hint when confirmed
- Broadcast the hint to all team members

**Viewing hints:**
- `/current_challenge` - Shows how many hints are available and which ones you've used
- `/hint` - Shows previously used hints and allows requesting the next one

**Penalty timing:**
When you complete a challenge after using hints, the next challenge will be locked for 2 minutes per hint used. For example:
- 1 hint used = 2 minutes wait
- 2 hints used = 4 minutes wait
- 3 hints used = 6 minutes wait (maximum)

### For Admins

**Configure Hints in config.yml:**
```yaml
challenges:
  - id: 1
    name: "Find the Landmark"
    description: "Take a team photo with the city skyline"
    location: "Downtown Viewpoint"
    type: "photo"
    verification:
      method: "photo"
    hints:
      - "Look for the tallest building in the area"
      - "The viewpoint is near the waterfront"
      - "Check the tourist information center for directions"
```

**Hints are optional:**
- Challenges without hints will show "No hints available" when teams use `/hint`
- You can provide 1, 2, or 3 hints per challenge
- Each hint costs 2 minutes penalty when the next challenge is unlocked

### Hint Strategy

Teams should consider:
- **When to use hints**: Balance speed vs. getting stuck
- **Team coordination**: Any team member can request a hint (all members are notified)
- **Penalty impact**: 6 minutes total penalty can be significant in a close race
- **Progressive difficulty**: Hints are revealed one at a time (can't skip to the last hint)

## Location-Based Verification

The bot supports optional GPS-based location verification for challenges. When enabled, teams must physically be at the challenge location (within a specified radius) before they can submit their answer.

### How It Works

1. **Enable/Disable**: Admin can toggle location verification using `/togglelocation`
2. **Location Verification**: Teams share their GPS location using Telegram's location attachment
3. **Distance Check**: Bot calculates distance using the Haversine formula
4. **Radius Verification**: Team must be within the configured radius (default: 100m)
5. **Challenge 1 Exception**: Location verification is skipped for Challenge 1 (starting point)

### For Teams

To share your location:
1. In the chat, tap the attachment button (📎)
2. Select "Location"
3. Choose "Send My Current Location"
4. Wait for the bot to verify your location
5. Once verified, submit your challenge answer

### For Admins

**Toggle Location Verification:**
```
/togglelocation
```
This enables or disables location verification for all challenges (except Challenge 1).

**Configure Challenge Coordinates in config.yml:**
```yaml
game:
  location_verification_enabled: true  # Enable on startup
  
  challenges:
    - id: 2
      name: "Library Challenge"
      # ... other fields ...
      coordinates:
        latitude: 37.7749
        longitude: -122.4194
        radius: 100  # meters
```

### Privacy Considerations

- Location data is only used for verification during the game
- Locations are stored temporarily in the game state
- Teams can choose to share their location only when needed
- Location verification can be disabled at any time by the admin

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
      type: "photo"  # Challenge type (photo, riddle, code, qr, trivia, etc.)
      verification:
        method: "photo"  # Verification method (photo or answer)
      hints:  # Optional: up to 3 hints per challenge
        - "First hint (easier)"
        - "Second hint (more specific)"
        - "Third hint (almost gives it away)"
    
    - id: 2
      name: "Riddle Challenge"
      description: "What has keys but no locks?"
      location: "Library"
      type: "riddle"
      verification:
        method: "answer"
        answer: "keyboard"  # Expected answer (case-insensitive)
      hints:
        - "Think about what you're using right now"
        - "It's used for typing"
    
    - id: 3
      name: "Trivia Challenge"
      description: "Name three programming languages"
      location: "Anywhere"
      type: "trivia"
      verification:
        method: "answer"
        answer: "python, java, javascript"  # Comma-separated for multiple keywords
      # No hints - this challenge is optional without hints
```

### Challenge Configuration Fields

- **id**: Unique challenge number (sequential: 1, 2, 3, etc.)
- **name**: Display name of the challenge
- **description**: Instructions for the challenge
- **location**: Where the challenge takes place
- **type**: Challenge type (photo, riddle, code, qr, trivia, scavenger, team_activity, decryption, text)
- **verification**: Verification configuration
  - **method**: "photo" or "answer"
  - **answer**: (for answer method) Expected answer or comma-separated keywords
- **hints**: (optional) List of up to 3 hints for the challenge
  - Each hint costs 2 minutes penalty (max 6 minutes total)
  - Hints are revealed sequentially (one at a time)
  - Teams can request hints using `/hint`
- **coordinates**: (optional) GPS coordinates for location verification
  - **latitude**: Latitude coordinate (-90 to 90)
  - **longitude**: Longitude coordinate (-180 to 180)
  - **radius**: Verification radius in meters (default: 100)

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
- Challenges are defined in the configuration file with types and verification methods
- Each challenge has an ID, name, description, location, type, and verification config
- **Teams must complete challenges in sequential order (1, 2, 3, etc.)**
- Each challenge can only be completed once per team
- Next challenge is unlocked only after completing the previous one
- Different challenge types support different submission methods:
  - **Photo challenges**: Submit photos which are auto-accepted
  - **Answer challenges**: Submit text answers which are auto-verified
  - **Trivia challenges**: Support multiple required keywords
- Challenge instructions are displayed based on the challenge type
- **Challenge Completion Broadcast**: When a team completes a challenge:
  - All team members receive a notification (except the submitter)
  - The admin receives a notification
  - Message includes team name, challenge name, submitter, and progress
  - Special congratulations message when team finishes all challenges

### Winning
- The winner is the **first team to complete all challenges**
- Teams that finish are ranked by their finish time
- Teams still racing are ranked by number of completed challenges
- No points system - it's a race to finish!

### Admin Controls
- Only one user can be configured as the admin in the `admin` field
- The bot supports backward compatibility with the old `admins` list format (uses first admin only)
- Admins can start/end the game and reset state
- Admins can view detailed team status with `/teamstatus`
- Admins can manage teams (add, edit, remove)
- The game must be started before teams can submit challenges
- Players can contact the admin using the `/contact` command

## Customization

### Adding Custom Commands

Edit `bot.py` and add new command handlers:

```python
async def my_custom_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Custom response")

# In the run() method:
application.add_handler(CommandHandler("mycommand", self.my_custom_command))
```

### Challenge Verification

The bot supports automatic verification for challenges:

**Photo Challenges:**
- Teams submit photos via Telegram
- Photos are automatically accepted and marked as complete
- Admin receives a copy of each photo submission

**Answer Challenges:**
- Teams submit text answers via the `/submit` command
- Answers are automatically verified against configured expected answers
- Supports exact match or keyword matching
- Case-insensitive comparison

**Customizing Verification:**
You can customize verification logic in the `verify_answer` method in `bot.py`. The bot now includes:
- **Location-based verification**: GPS coordinate verification using Haversine formula
- **Answer verification**: Exact match or keyword matching (case-insensitive)
- **Photo verification**: Automatic acceptance with admin notification

For location verification:
- Distance is calculated using the Haversine formula for accuracy
- Teams must be within the configured radius (default 100m)
- Verification is skipped for Challenge 1
- Can be toggled on/off globally by admins

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
