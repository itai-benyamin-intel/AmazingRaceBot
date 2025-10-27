# AmazingRaceBot - Telegram Bot

A Telegram chatbot template for managing an Amazing Race game. This bot allows teams to register, track their progress through sequential challenges, and compete to finish first.

## Features

- 🏁 **Team Management**: Create and join teams
- 🎯 **Sequential Challenge Tracking**: Teams must complete challenges in order
- 💡 **Hints System**: Teams can request up to 3 hints per challenge with time penalties
- 📷 **Challenge Types System**: Support for diverse challenge types with automatic verification
- 📸 **Photo Verification**: Photo verification for location arrival (challenges 2+) - ensures teams are at locations
- 🏆 **Leaderboard**: Real-time standings showing progress and finishers
- 👥 **Multi-team Support**: Support for multiple teams competing simultaneously
- 🔐 **Admin Controls**: Game start/stop, reset, and team management functionality
- 📊 **Admin Team Management**: View, edit, add, and remove teams
- 💾 **Persistent State**: Game state saved across bot restarts

## Challenge Types

The bot supports various challenge types with different verification methods:

### Supported Challenge Types

1. **📷 Photo Challenge**: Teams submit photos (e.g., team photo at location, completed puzzle)
   - Verification: Photo submission (pending admin approval)
   
2. **🧩 Riddle/Clue Challenge**: Teams solve riddles or puzzles
   - Verification: Text answer (auto-checked)
   
3. **💻 Code Challenge**: Teams write or debug code
   - Verification: Text submission with flexible answer matching
   - Supports multiple acceptable answers (e.g., different output formats)
   - Can use simple keyword matching for function names
   
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

- **Photo**: Teams submit a photo which is sent to admin for approval
- **Answer**: Text answer is automatically verified against configured answer(s)
  - Supports exact match or keyword matching
  - Case-insensitive comparison
  - For trivia: supports multiple required keywords (comma-separated)
  - For code challenges: supports multiple acceptable answers (any one matches)
  - **Checklist Mode**: Allows progressive submission of list items
    - Teams can submit items one at a time or all at once
    - Progress is tracked for each individual item
    - Challenge completes when all checklist items are submitted
    - Perfect for challenges like "name 5 capitals" or "list 3 programming languages"

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
git clone https://github.com/itai-benyamin-intel/AmazingRaceBot.git
cd AmazingRaceBot
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
- `/help` - Get context-aware help based on your current game state
- `/createteam <team_name>` - Create a new team (you become the captain)
- `/jointeam <team_name>` - Join an existing team
- `/myteam` - View your team's information and progress
- `/challenges` - View completed challenges and your current challenge
- `/current` - View your current challenge (shows available/used hints)
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
- `/approve` - View pending photo submissions (approval via inline buttons)
- `/reject` - View pending photo submissions (same as `/approve`)
- `/togglephotoverify` - Enable/disable photo verification for location arrival (challenges 2+)

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
- `/current` - Shows how many hints are available and which ones you've used
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

## Photo Verification for Location Arrival

The bot supports optional photo verification for challenges. You can configure photo verification globally (for all challenges 2+) or per-challenge. When required, teams must send a photo of their team at the challenge location before the challenge details are revealed. This ensures teams physically arrive at each location before knowing what they need to do.

### How It Works

1. **Configuration**: Set photo verification globally with `/togglephotoverify` or per-challenge in `config.yml`
2. **Challenge Progression**: Team completes a challenge and moves to the next one
3. **Photo Required** (if configured): Before challenge details are shown, team must send a photo
4. **Admin Approval**: Admin reviews the photo and approves/rejects it
5. **Challenge Revealed**: Once approved, the full challenge details are revealed to all team members
6. **Timeout Starts**: The penalty timeout (from hints) only starts after photo approval

### Per-Challenge Configuration

You can specify whether photo verification is required for each individual challenge in `config.yml`:

```yaml
challenges:
  - id: 1
    name: "Find the Landmark"
    # Challenge 1 never requires photo verification
    # ...
  
  - id: 2
    name: "Visit the Library"
    requires_photo_verification: true  # Explicitly requires photo
    # ...
  
  - id: 3
    name: "Solve the Riddle"
    requires_photo_verification: false  # Explicitly does NOT require photo
    # ...
  
  - id: 4
    name: "Find the Statue"
    # No field specified - uses global photo_verification_enabled setting
    # ...
```

**Configuration Options:**
- `requires_photo_verification: true` - Challenge requires photo verification regardless of global setting
- `requires_photo_verification: false` - Challenge does NOT require photo verification regardless of global setting
- Field omitted - Challenge uses global `photo_verification_enabled` setting (for challenges 2+)
- Challenge 1 never requires photo verification

**Use Cases:**
- **Location-based challenges**: Set `requires_photo_verification: true` for challenges at specific locations
- **Trivia/puzzle challenges**: Set `requires_photo_verification: false` for challenges that can be completed anywhere
- **Mixed race format**: Combine both types for a dynamic race experience

### For Teams

**When you advance to a challenge that requires photo verification:**

1. You'll see a message indicating photo verification is required
2. Go to the challenge location (only the name and location are shown)
3. Take a photo of your team at that location
4. Send the photo to the bot
5. Wait for admin approval
6. Once approved, the full challenge details will be revealed
7. Complete the challenge as normal

**Important Notes:**
- Challenge 1 never requires photo verification (it's the starting point)
- Only challenges configured with photo verification will require it
- Any team member can send the photo
- The photo must show your team at the location
- The timeout/penalty timer only starts after the photo is approved

### For Admins

**Global Toggle:**
```
/togglephotoverify
```
This enables or disables photo verification globally. Challenges without explicit `requires_photo_verification` settings will follow this global setting.

**Per-Challenge Override:**
Configure `requires_photo_verification: true` or `false` in `config.yml` for any challenge to override the global setting.

**Approving Photos:**
When a team sends a location photo:
1. You'll receive the photo with the team name and challenge number
2. Review the photo to verify the team is at the correct location
3. Click ✅ **Approve** to reveal the challenge to the team
4. Click ❌ **Reject** if the photo is incorrect (team can resubmit)

**Managing Multiple Teams:**
- Multiple teams can have pending photo verifications simultaneously
- Each photo shows which team and challenge it's for
- Use the inline buttons on each photo to approve/reject
- Use `/approve` to see a list of all pending verifications

**Tips:**
- Review photos promptly to keep the game flowing
- Be clear about why photos are rejected (team can send a new one)
- Photo verification adds an extra layer of fairness to the race
- The timeout/penalty timer starts only after you approve the photo
- Use per-challenge configuration for maximum flexibility

### Privacy Considerations

- Photos are only used for verification during the game
- Photos are stored temporarily in the game state
- Teams control when they send photos
- Photo verification can be disabled at any time by the admin

## Configuration

Edit `config.yml` to customize your game:

```yaml
game:
  name: "AmazingRaceBot"
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
      name: "Code Challenge"
      description: |
        Debug this function and submit the output for fib(5):
        def fib(n):
            if n <= 1: return 1  # Bug here!
            return fib(n-1) + fib(n-2)
      location: "Computer Lab"
      type: "code"
      verification:
        method: "answer"
        # Multiple acceptable answer formats for flexibility
        acceptable_answers:
          - "5"
          - "five"
          - "answer is 5"
    
    - id: 4
      name: "Trivia Challenge"
      description: "Name three programming languages"
      location: "Anywhere"
      type: "trivia"
      verification:
        method: "answer"
        answer: "python, java, javascript"  # Comma-separated for multiple keywords
      # No hints - this challenge is optional without hints
    
    - id: 5
      name: "Capital Cities Checklist"
      description: "Name 5 capital cities from different continents"
      location: "Anywhere"
      type: "trivia"
      verification:
        method: "answer"
        # Checklist mode: participants can submit items one at a time or all at once
        checklist_items:
          - "Tokyo"
          - "Paris"
          - "Cairo"
          - "Brasilia"
          - "Canberra"
      hints:
        - "Think about each continent: Asia, Europe, Africa, South America, Australia"
```

### Challenge Configuration Fields

- **id**: Unique challenge number (sequential: 1, 2, 3, etc.)
- **name**: Display name of the challenge
- **description**: Instructions for the challenge
- **location**: Where the challenge takes place
- **type**: Challenge type (photo, riddle, code, qr, trivia, scavenger, team_activity, decryption, text)
- **verification**: Verification configuration
  - **method**: "photo" or "answer"
  - **answer**: (for answer method) Expected answer or comma-separated keywords (for trivia)
  - **acceptable_answers**: (for answer method) List of acceptable answers - any one matches (for code challenges)
  - **checklist_items**: (for answer method) List of items that can be submitted individually
    - Enables progressive answering - teams can submit items one at a time
    - Each item is tracked independently
    - Challenge completes when all items are submitted
    - Items are matched case-insensitively using substring matching
- **requires_photo_verification**: (optional) Boolean to control photo verification for this challenge
  - `true` - Requires photo verification regardless of global setting
  - `false` - Does NOT require photo verification regardless of global setting
  - Omitted - Uses global `photo_verification_enabled` setting (for challenges 2+)
  - Note: Challenge 1 never requires photo verification
- **hints**: (optional) List of up to 3 hints for the challenge
  - Each hint costs 2 minutes penalty (max 6 minutes total)
  - Hints are revealed sequentially (one at a time)
  - Teams can request hints using `/hint`

**Note**: Challenges are completed sequentially based on their ID order (1, 2, 3, etc.)

### Checklist Challenges

Checklist challenges allow teams to submit answers progressively instead of all at once. This is perfect for:
- Multi-part questions (e.g., "Name 5 capital cities")
- Collection tasks (e.g., "List 3 programming languages")
- Enumeration challenges (e.g., "Name the 7 continents")

**How it works:**
1. Configure a challenge with `checklist_items` instead of `answer`
2. Teams can submit answers one at a time: `/submit Tokyo`
3. Bot tracks progress and shows which items are completed
4. Teams can also submit multiple items: `/submit Tokyo Paris` or `/submit Tokyo and Paris`
5. Challenge completes when all items are submitted

**Example:**
```yaml
- id: 5
  name: "Programming Languages"
  description: "Name 3 popular programming languages"
  location: "Anywhere"
  type: "trivia"
  verification:
    method: "answer"
    checklist_items:
      - "Python"
      - "JavaScript"
      - "Java"
```

**Benefits:**
- Teams can make progress even if they don't know all answers
- Encourages teamwork as members can contribute different items
- Progress is visible, showing which items remain
- More engaging and interactive than all-or-nothing answers

## File Structure

```
AmazingRaceBot/
├── bot.py                 # Main bot implementation
├── game_state.py          # Game state management
├── run_bot.py             # Bot runner script
├── config.yml             # Your configuration (create from example)
├── config.example.yml     # Example configuration
├── requirements.txt       # Python dependencies
├── game_state.json        # Persistent game state (auto-generated)
├── tests/                 # Unit tests
│   ├── test_game_state.py
│   ├── test_bot.py
│   └── ...
├── docs/                  # Additional documentation
│   ├── QUICKSTART.md
│   ├── CHANGELOG.md
│   └── ...
├── commands.md            # Command reference
└── README.md              # This file
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
  - **Photo challenges**: Submit photos which are sent to admin for approval
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

### Photo Approval Workflow (for Admins)

When a team submits a photo for a challenge:

1. **Photo Submission**: Team member sends a photo for their current challenge
2. **Admin Notification**: Admin receives the photo with inline approval buttons
3. **Review**: Admin reviews the photo to verify it meets challenge requirements
4. **Approve or Reject**:
   - Click ✅ **Approve** to mark the challenge as complete
   - Click ❌ **Reject** to deny the submission
5. **Team Notification**: 
   - If approved: All team members receive a notification and can proceed
   - If rejected: The submitter is notified and can resubmit

**Admin Commands for Photo Management:**
- `/approve` - View list of all pending photo submissions
- `/reject` - View list of all pending photo submissions (same as approve)
- Use the inline buttons on photo messages to approve/reject

**Tips:**
- Review photos promptly to keep the game flowing
- Be clear about rejection reasons (teams can resubmit)
- Use the submission ID in the photo caption to track submissions

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
- Photos are sent to the admin for approval
- Admin can approve or reject submissions using inline buttons
- After approval, challenge is marked as complete
- Team members are notified when their photo is approved or rejected

**Answer Challenges:**
- Teams submit text answers via the `/submit` command
- Answers are automatically verified against configured expected answers
- Supports exact match or keyword matching
- Case-insensitive comparison

**Customizing Verification:**
You can customize verification logic in the `verify_answer` method in `bot.py`. The bot includes:
- **Answer verification**: Exact match or keyword matching (case-insensitive)
- **Photo verification**: Manual admin approval with notification

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
