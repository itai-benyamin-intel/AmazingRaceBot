# Changelog

## [Unreleased] - 2025-10-23

### Added
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

1. **Config File**: Remove `points` field from all challenges in `config.yml`
   ```yaml
   # Old format
   - id: 1
     name: "Challenge"
     points: 10    # Remove this line
   
   # New format
   - id: 1
     name: "Challenge"
   ```

2. **Game State**: Existing game state will be automatically migrated on first load
   - Old `score` field will be ignored
   - New fields (`current_challenge_index`, `finish_time`) will be added

3. **Game Rules**: Teams must now complete challenges in sequential order
   - Challenge IDs should be sequential (1, 2, 3, 4, etc.)
   - Teams cannot skip ahead to later challenges

### New Features Usage

**Admin Commands:**
```
/teamstatus              # View all teams' detailed status
/addteam TeamName        # Create a team as admin
/editteam Old New        # Rename a team
/removeteam TeamName     # Remove a team
```

**Player Experience:**
- Only current challenge is visible in detail
- Future challenges show as "LOCKED"
- Must complete Challenge 1 before Challenge 2, etc.
- Winning team is the first to finish all challenges
