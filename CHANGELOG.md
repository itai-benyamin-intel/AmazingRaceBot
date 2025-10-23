# Changelog

## [Unreleased] - 2025-10-23

### Added
- **Challenge Completion Broadcast**: When a challenge is solved, a confirmation message is broadcast to:
  - All team members (except the person who submitted)
  - The admin
  - Message includes team name, challenge name, who submitted it, and progress
  - Includes special congratulations message when team finishes all challenges
- **Challenge Types System**: Support for diverse challenge types with automatic verification
  - Photo challenges: Submit photos (auto-accepted, admin receives copy)
  - Riddle challenges: Text answer verification with keyword matching
  - Code challenges: Submit code solutions or results
  - QR Hunt challenges: Scan and submit QR code text
  - Trivia challenges: Support multiple required keywords
  - Scavenger Hunt: Find and photograph items
  - Team Activity: Photo verification for team activities
  - Decryption challenges: Decode messages and submit answers
- **Automatic Verification**: 
  - Text answers verified automatically against configured answers
  - Case-insensitive matching with keyword support
  - Photo submissions auto-accepted with admin notification
- **Challenge Configuration**:
  - `type` field for each challenge (photo, riddle, code, qr, trivia, etc.)
  - `verification` object with `method` and `answer` fields
  - Flexible answer matching (exact, keyword, or multi-keyword)
- **Enhanced Challenge Display**:
  - Challenge types shown with emojis (📷, 🧩, 💻, 📱, etc.)
  - Type-specific submission instructions
  - Clear guidance on how to complete each challenge
- **Photo Submission Handler**: 
  - Accept photos from teams
  - Store photo metadata in game state
  - Notify admin with submitted photos
- **Submission Data Tracking**:
  - Store answer text, photo IDs, and timestamps
  - Backward compatible with existing game state
- **Comprehensive Tests**: 
  - 14 new tests for challenge types functionality
  - Tests for answer verification, photo handling, and config loading
- **Documentation**:
  - Detailed CHALLENGE_TYPES.md guide with examples
  - Updated README.md with challenge types information
  - Updated config.example.yml with 8 example challenges
- Sequential challenge system: Teams must complete challenges in order (1, 2, 3, etc.)
- Challenge locking: Only the current challenge is visible and unlocked
- Finish time tracking: Records when teams complete all challenges
- Admin team management commands:
  - `/teamstatus` - View detailed status of all teams
  - `/addteam <name>` - Create teams as admin
  - `/editteam <old> <new>` - Rename teams
  - `/removeteam <name>` - Remove teams
- Progress tracking: Shows current challenge number for each team
- Comprehensive test coverage for all new features

### Changed
- **BREAKING**: Challenge config structure updated to include `type` and `verification` fields
- `/submit` command now supports both photo and answer submissions:
  - `/submit <id>` then send photo for photo challenges
  - `/submit <id> <answer>` for answer challenges
- `/challenges` command displays challenge types and submission instructions
- `complete_challenge` in game_state.py accepts optional `submission_data` parameter
- **BREAKING**: Removed points system - winner is determined by who finishes first
- Leaderboard now shows:
  - Finished teams ranked by finish time
  - Racing teams ranked by number of completed challenges
- Team info displays progress instead of score
- Challenge view shows locked/unlocked status
- Challenge completion requires sequential order
- Submit command validates challenge order

### Removed
- Points field from challenge definitions in config.yml
- Score tracking from team data
- Point-based winning system

### Fixed
- Enhanced error messages for out-of-order challenge attempts
- Improved team management for admins
- Better progress visibility

## Migration Guide

### For Existing Installations

1. **Config File Update**: Add `type` and `verification` fields to all challenges
   ```yaml
   # Old format
   - id: 1
     name: "Challenge"
     description: "Description"
     location: "Location"
   
   # New format
   - id: 1
     name: "Challenge"
     description: "Description"
     location: "Location"
     type: "photo"           # Add this
     verification:           # Add this
       method: "photo"
   ```

2. **Challenge Types**: Choose appropriate types for your challenges
   - `photo` - Photo submissions
   - `riddle` - Riddles/puzzles with text answers
   - `code` - Coding challenges
   - `qr` - QR code hunts
   - `trivia` - Trivia questions
   - `scavenger` - Scavenger hunts
   - `team_activity` - Team activities
   - `decryption` - Decryption challenges
   - `text` - General text submissions

3. **Verification Method**: Set the verification method
   - `method: "photo"` - For photo-based challenges
   - `method: "answer"` - For text answer challenges
     - Add `answer: "expected_answer"` field
     - For trivia: Use comma-separated keywords `answer: "python, java, javascript"`

4. **Game State**: Existing game state is backward compatible
   - Old format without submission data still works
   - New submissions include detailed metadata
   - No data migration required

5. **Team Submissions**: Update how teams submit
   - Photo challenges: `/submit <id>` then send photo
   - Answer challenges: `/submit <id> <answer>`

### Example Migration

**Before:**
```yaml
challenges:
  - id: 1
    name: "First Challenge"
    description: "Find the clue"
    location: "Main Hall"
```

**After:**
```yaml
challenges:
  - id: 1
    name: "First Challenge"
    description: "Find the clue and take a photo"
    location: "Main Hall"
    type: "photo"
    verification:
      method: "photo"
```

### New Features Usage

**Photo Challenges:**
```
Player: /submit 1
Bot: Please send a photo for: First Challenge
Player: [sends photo]
Bot: Photo submitted! Challenge marked as complete.
```

**Answer Challenges:**
```
Player: /submit 2 keyboard
Bot: Correct! Team completed: Library Riddle
```

**Trivia (Multiple Keywords):**
```yaml
verification:
  method: "answer"
  answer: "python, java, javascript"
```
```
Player: /submit 3 I know Python, Java, and JavaScript
Bot: Correct! All keywords found.
```
