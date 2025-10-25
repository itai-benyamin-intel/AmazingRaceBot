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
Bot: 🏁 Welcome to AmazingRaceBot! 🏁
     This is an interactive Amazing Race game.
     Complete challenges sequentially to win!
     [Commands list...]

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

     🎯 Challenge #1: First Challenge (CURRENT)
        📍 Location: Main Hall
        📝 Find the hidden clue in the main hall

     🔒 Challenge #2: LOCKED
        Complete previous challenges to unlock

     🔒 Challenge #3: LOCKED
        Complete previous challenges to unlock

     [... more locked challenges ...]
```

```
User: /teams
Bot: 👥 Teams 👥

     Speed Demons
       Members: 2/5
       Progress: 0/4

     Code Runners
       Members: 2/5
       Progress: 0/4
```

**Admin:**
```
User: /teamstatus
Bot: 📊 Detailed Team Status 📊

     Speed Demons
       👥 Members (2): Alice, Bob
       👑 Captain: Alice
       📊 Progress: 0/4
       🎯 Current Challenge: #1

     Code Runners
       👥 Members (2): Charlie, Diana
       👑 Captain: Charlie
       📊 Progress: 0/4
       🎯 Current Challenge: #1
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
     Progress: 1/4 challenges
```

**Team Speed Demons - Player 1 (trying to skip ahead):**
```
User: /submit 3
Bot: You must complete challenges in order!
     Your current challenge is #2.
```

**Team Code Runners - Player 3:**
```
User: /submit 1
Bot: 🎉 Congratulations! Team 'Code Runners' completed:
     First Challenge
     Progress: 1/4 challenges
```

**Team Speed Demons - Player 2:**
```
User: /myteam
Bot: 👥 Team: Speed Demons

     🎯 Current Challenge: #2
     📊 Progress: 1/4 challenges completed

     Members:
       • Alice
       • Bob
```

```
User: /challenges
Bot: 🎯 Challenges 🎯

     ✅ Challenge #1: First Challenge
        📍 Location: Main Hall
        📝 Find the hidden clue in the main hall

     🎯 Challenge #2: Code Puzzle (CURRENT)
        📍 Location: Lab A
        📝 Solve the programming puzzle

     🔒 Challenge #3: LOCKED
        Complete previous challenges to unlock

     [...]
```

**Any Player:**
```
User: /leaderboard
Bot: 🏆 Leaderboard 🏆

     Still Racing:
     🏃 Speed Demons - 1/4 challenges
     🏃 Code Runners - 1/4 challenges
```

**Team Speed Demons - Player 1:**
```
User: /submit 2
Bot: 🎉 Congratulations! Team 'Speed Demons' completed:
     Code Puzzle
     Progress: 2/4 challenges
```

```
User: /submit 3
Bot: 🎉 Congratulations! Team 'Speed Demons' completed:
     Team Challenge
     Progress: 3/4 challenges
```

```
User: /submit 4
Bot: 🎉 Congratulations! Team 'Speed Demons' completed:
     Final Sprint
     Progress: 4/4 challenges

     🏆 CONGRATULATIONS! 🏆
     Your team finished the race!
     Finish time: 2024-01-15T14:30:25.123456
```

```
User: /leaderboard
Bot: 🏆 Leaderboard 🏆

     Finished Teams:
     🥇 Speed Demons - Finished!

     Still Racing:
     🏃 Code Runners - 1/4 challenges
```

### Phase 5: Game End

**Admin:**
```
User: /endgame
Bot: 🏁 GAME OVER! 🏁

     Final Standings:

     Finished Teams:
     🥇 Speed Demons - Completed all challenges!

     Did Not Finish:
        Code Runners - 1/4 challenges

     🎉 Congratulations to all teams! 🎉
```

## Admin Team Management Examples

**Admin creating a team:**
```
User: /addteam Late Arrivals
Bot: ✅ Team 'Late Arrivals' created successfully!
     Note: This is an admin-created team. You can add members using:
     Players can join with /jointeam Late Arrivals
```

**Admin renaming a team:**
```
User: /editteam "Speed Demons" "Lightning Demons"
Bot: ✅ Team renamed from 'Speed Demons' to 'Lightning Demons'
```

**Admin removing a team:**
```
User: /removeteam "Late Arrivals"
Bot: ✅ Team 'Late Arrivals' has been removed.
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

**Trying to skip a challenge:**
```
User: /submit 3
Bot: You must complete challenges in order!
     Your current challenge is #1.
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
   - Make sure challenge IDs are sequential (1, 2, 3, etc.)
   - Test the sequential unlock mechanism

2. **During setup:**
   - Give players 10-15 minutes to form teams
   - Explain that challenges must be done in order
   - Show them the `/challenges` command
   - Explain the rules clearly

3. **During gameplay:**
   - Monitor with `/teamstatus` to see all teams' progress
   - Be ready to help with technical issues
   - Use `/editteam` to fix any team name typos
   - Consider having a backup admin

4. **After the game:**
   - Announce winners (first to finish wins!)
   - Use `/reset` to clear for next game
   - Keep `game_state.json` as a record if needed
