# Sample Bot Interaction

This document shows example interactions with the Amazing Race bot.

## Initial Setup (Admin)

**Getting Bot Token:**
1. Message @BotFather on Telegram
2. Send `/newbot`
3. Follow prompts to name your bot
4. Copy the token provided
5. Add token to `config.yml`

**Getting Your User ID:**
1. Message @userinfobot on Telegram
2. Your ID will be shown in the response
3. Add your ID to the `admins` list in `config.yml`

## Sample Game Session

### Phase 1: Team Formation

**Player 1:**
```
User: /start
Bot: 🏁 Welcome to uCode Amazing Race! 🏁
     [Welcome message with commands]

User: /createteam Speed Demons
Bot: ✅ Team 'Speed Demons' created successfully!
     You are the team captain. Other players can join with:
     /jointeam Speed Demons
```

**Player 2:**
```
User: /jointeam Speed Demons
Bot: ✅ You joined team 'Speed Demons'!
     Team members: 2/5
```

**Player 3:**
```
User: /createteam Code Runners
Bot: ✅ Team 'Code Runners' created successfully!
     [...]
```

**Player 4:**
```
User: /jointeam Code Runners
Bot: ✅ You joined team 'Code Runners'!
     Team members: 2/5
```

### Phase 2: Pre-Game

**Any Player:**
```
User: /challenges
Bot: 🎯 Challenges 🎯

     ⭕ Challenge #1: First Challenge
        📍 Location: Main Hall
        📝 Find the hidden clue in the main hall
        🏆 Points: 10

     ⭕ Challenge #2: Code Puzzle
        📍 Location: Lab A
        📝 Solve the programming puzzle
        🏆 Points: 20

     [... more challenges ...]
```

```
User: /teams
Bot: 👥 Teams 👥

     Speed Demons
       Members: 2/5
       Score: 0 points

     Code Runners
       Members: 2/5
       Score: 0 points
```

### Phase 3: Game Start

**Admin:**
```
User: /startgame
Bot: 🏁 THE GAME HAS STARTED! 🏁

     Teams can now start completing challenges!
     Use /challenges to see available challenges.
     Good luck! 🎯
```

### Phase 4: Gameplay

**Team Speed Demons - Player 1:**
```
User: /submit 1
Bot: 🎉 Congratulations! Team 'Speed Demons' completed:
     First Challenge
     Points earned: 10
     Total score: 10
```

**Team Code Runners - Player 3:**
```
User: /submit 2
Bot: 🎉 Congratulations! Team 'Code Runners' completed:
     Code Puzzle
     Points earned: 20
     Total score: 20
```

**Any Player:**
```
User: /leaderboard
Bot: 🏆 Leaderboard 🏆

     🥇 Code Runners - 20 points
     🥈 Speed Demons - 10 points
```

**Team Speed Demons - Player 2:**
```
User: /myteam
Bot: 👥 Team: Speed Demons

     🏆 Score: 10 points
     📊 Challenges: 1/4 completed

     Members:
       • Alice
       • Bob
```

**Team Speed Demons - Player 1:**
```
User: /submit 2
Bot: 🎉 Congratulations! Team 'Speed Demons' completed:
     Code Puzzle
     Points earned: 20
     Total score: 30
```

```
User: /leaderboard
Bot: 🏆 Leaderboard 🏆

     🥇 Speed Demons - 30 points
     🥈 Code Runners - 20 points
```

### Phase 5: Game End

**Admin:**
```
User: /endgame
Bot: 🏁 GAME OVER! 🏁

     Final Standings:

     🥇 Speed Demons - 30 points
     🥈 Code Runners - 20 points

     🎉 Congratulations to all teams! 🎉
```

## Error Handling Examples

**Trying to submit before game starts:**
```
User: /submit 1
Bot: The game hasn't started yet!
```

**Trying to join team when already in one:**
```
User: /jointeam Code Runners
Bot: You are already in a team!
```

**Trying to complete challenge twice:**
```
User: /submit 1
Bot: This challenge was already completed by your team!
```

**Non-admin trying admin command:**
```
User: /startgame
Bot: Only admins can start the game!
```

**Submitting without being in a team:**
```
User: /submit 1
Bot: You are not in any team!
```

## Tips for Running the Game

1. **Before the event:**
   - Test all commands
   - Verify challenges are configured correctly
   - Make sure bot responds quickly

2. **During setup:**
   - Give players 10-15 minutes to form teams
   - Show them the `/challenges` command
   - Explain the rules clearly

3. **During gameplay:**
   - Monitor the leaderboard
   - Be ready to help with technical issues
   - Consider having a backup admin

4. **After the game:**
   - Announce winners
   - Use `/reset` to clear for next game
   - Keep `game_state.json` as a record if needed
