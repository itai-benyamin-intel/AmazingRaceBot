# Amazing Race Bot - Quick Reference

## Setup Checklist

1. ✅ Install Python 3.8+
2. ✅ Install dependencies: `pip install -r requirements.txt`
3. ✅ Create config: `cp config.example.yml config.yml`
4. ✅ Get bot token from [@BotFather](https://t.me/botfather)
5. ✅ Add token to `config.yml`
6. ✅ Add your Telegram user ID to admins in `config.yml`
7. ✅ Customize challenges in `config.yml`
8. ✅ Run: `python run_bot.py`

## Quick Command Reference

### For Players

| Command | Description | Example |
|---------|-------------|---------|
| `/start` | Start the bot | `/start` |
| `/help` | Show all commands | `/help` |
| `/createteam <name>` | Create a team | `/createteam Racers` |
| `/jointeam <name>` | Join a team | `/jointeam Racers` |
| `/myteam` | View team info | `/myteam` |
| `/teams` | List all teams | `/teams` |
| `/challenges` | View challenges | `/challenges` |
| `/submit <id>` | Submit challenge | `/submit 1` |
| `/leaderboard` | View standings | `/leaderboard` |

### For Admins

| Command | Description | When to Use |
|---------|-------------|-------------|
| `/startgame` | Start the game | After teams are formed |
| `/endgame` | End the game | When time is up |
| `/reset` | Reset everything | To start fresh |

## Game Flow

```
1. SETUP
   ├─ Admin: Configure challenges in config.yml
   ├─ Players: Create teams (/createteam)
   └─ Players: Join teams (/jointeam)

2. START
   └─ Admin: Start game (/startgame)

3. PLAY
   ├─ Teams: Complete challenges in real world
   ├─ Teams: Submit completions (/submit)
   └─ Everyone: Check leaderboard (/leaderboard)

4. END
   ├─ Admin: End game (/endgame)
   └─ Winner announced!
```

## Tips

- **For Organizers:**
  - Test the bot before the event
  - Have challenges ready in advance
  - Keep admin password/token secure
  - Monitor the leaderboard during the game

- **For Players:**
  - Form your team early
  - Check `/challenges` to plan your route
  - Submit challenges as you complete them
  - Watch the `/leaderboard` to see your position

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Bot not responding | Check bot is running, verify token |
| Can't create team | Check max teams limit in config |
| Can't join team | Team might be full or you're already in one |
| Can't submit | Game might not be started yet |
| Not authorized | Check you're in admins list for admin commands |

## Configuration Tips

### Custom Challenge Ideas

```yaml
challenges:
  - id: 1
    name: "Photo Hunt"
    description: "Take a selfie at the landmark"
    points: 10
    location: "City Center"
    
  - id: 2
    name: "Riddle Master"
    description: "Solve the riddle to find next location"
    points: 15
    location: "Mystery Location"
    
  - id: 3
    name: "Team Task"
    description: "Build a tower using provided materials"
    points: 20
    location: "Workshop"
```

### Adjusting Difficulty

- **Easy Game:** Low max_teams, high max_team_size, more points
- **Hard Game:** Many challenges, strict team size, lower points
- **Long Game:** More challenges, spread out locations
- **Quick Game:** 3-5 challenges, close locations

## Getting Help

- Check README.md for detailed documentation
- Review config.example.yml for configuration options
- Test with test_game_state.py to verify installation
