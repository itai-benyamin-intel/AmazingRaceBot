# Challenge Broadcast Feature

## Overview
This feature implements automatic broadcasting of new challenges to team members when:
1. A timeout is revoked (penalty expires)
2. No timeout was available (no hints were used)

## Issue Requirements
After timeout is revoked (penalty for using hints) or when no timeout was available, broadcast the new challenge (`/current`) to the relevant team.

## Implementation Details

### 1. Broadcast When No Timeout Exists
When a team completes a challenge without using hints:
- The next challenge is immediately broadcast to all team members
- The submitter is excluded from the broadcast (they already know they completed it)
- Broadcast includes challenge details, location, type, and instructions

**Code Location:** `bot.py` - `submit_command()` method, lines ~920-926

### 2. Broadcast When Timeout Expires  
When a team has an active timeout (hint penalty) that expires:
- Bot checks for expired timeouts when team members interact via `/current` or `/submit`
- If timeout has expired and broadcast hasn't been sent yet, it broadcasts the challenge
- Tracks which challenges have been broadcast to prevent duplicates

**Code Location:** `bot.py` - `check_and_broadcast_unlocked_challenge()` method, lines ~206-255

### 3. Broadcast Tracking
To prevent duplicate broadcasts:
- System tracks broadcast status in team data: `challenge_unlock_broadcasts`
- Each challenge unlock is broadcast only once
- Tracking persists across bot restarts

### 4. Challenge Details Broadcast
The broadcast message includes:
- Challenge ID and name
- Challenge type (with emoji)
- Location
- Description
- Submission instructions
- Available hints count
- Commands to use (`/current`, `/submit`)

**Code Location:** `bot.py` - `broadcast_current_challenge()` method, lines ~257-323

## Usage Scenarios

### Scenario A: Complete Challenge Without Hints
1. Team member submits correct answer for Challenge 1
2. No hints were used → No timeout for Challenge 2
3. **Broadcast triggers:** Challenge 2 details sent to all team members (except submitter)
4. Team can immediately start working on Challenge 2

### Scenario B: Complete Challenge With Hints
1. Team uses 2 hints on Challenge 1 (4-minute penalty)
2. Team member submits correct answer
3. Challenge 2 is locked for 4 minutes
4. **No broadcast:** Team is notified about the timeout
5. After 4 minutes, when any team member calls `/current` or `/submit`:
   - Bot detects timeout expired
   - **Broadcast triggers:** Challenge 2 details sent to all team members
   - Team can now work on Challenge 2

## Code Changes

### Modified Files
1. **bot.py**
   - Added `check_and_broadcast_unlocked_challenge()` - checks for expired timeouts
   - Added `broadcast_current_challenge()` - broadcasts challenge details to team
   - Modified `submit_command()` - broadcasts next challenge when no timeout
   - Modified `current_challenge_command()` - checks for expired timeouts
   - Modified `photo_approval_callback_handler()` - broadcasts next challenge when no timeout

### Test Files
1. **test_challenge_broadcast.py** (modified)
   - Updated existing test to account for new broadcast behavior
   
2. **test_challenge_unlock_broadcast.py** (new)
   - Tests broadcasting when no timeout exists
   - Tests no broadcast when timeout is active
   - Tests broadcasting when timeout expires
   - Tests preventing duplicate broadcasts

## Test Coverage
- Total tests: 98 (added 4 new tests)
- All tests passing ✓
- Coverage includes:
  - No timeout scenario
  - Active timeout scenario
  - Expired timeout scenario
  - Duplicate broadcast prevention
  - Both answer and photo challenges

## Benefits
1. **Better User Experience:** Teams don't need to manually check when challenges unlock
2. **Real-time Updates:** Team members are notified immediately when challenges become available
3. **Fair Play:** All team members get the information at the same time
4. **Reduced Confusion:** Clear notifications prevent teams from wondering when they can proceed

## Technical Notes
- Uses Telegram's `send_message` API for broadcasts
- Handles async operations properly with `await`
- Stores broadcast tracking in game state (persists across restarts)
- Error handling for failed message sends (logs but continues)
- Excludes submitter from next challenge broadcast (they already know)
