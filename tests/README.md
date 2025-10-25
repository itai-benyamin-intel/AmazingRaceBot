# Tests

This directory contains the test suite for the Amazing Race Bot project.

## Running Tests

To run all tests:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

To run a specific test file:

```bash
python -m unittest tests.test_game_state
```

To run with verbose output:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

## Test Structure

The test suite is organized by functionality:

### Core Functionality
- **test_game_state.py** - Game state management tests
- **test_bot.py** - Bot configuration and admin tests

### Commands
- **test_start_command.py** - Start command tests
- **test_help_command.py** - Help command tests
- **test_challenges_command.py** - Challenges command tests
- **test_submit_command.py** - Submit command tests
- **test_interactive_commands.py** - Interactive command tests

### Features
- **test_challenge_types.py** - Challenge types and verification
- **test_hints.py** - Hints system tests
- **test_integration_hints.py** - Hints integration tests
- **test_photo_verification.py** - Photo verification tests
- **test_location_verification.py** - Location verification tests

### Broadcasting & Messaging
- **test_challenge_broadcast.py** - Challenge completion broadcasts
- **test_challenge_unlock_broadcast.py** - Challenge unlock broadcasts
- **test_start_game_broadcast.py** - Start game broadcast tests
- **test_message_order.py** - Message ordering tests

### UI & Display
- **test_timeout_display.py** - Timeout display tests
- **test_teams_leaderboard.py** - Teams and leaderboard tests

## Test Coverage

The test suite covers:
- Team creation and management
- Challenge completion and verification
- Game state persistence
- Admin controls
- Broadcast messaging
- Photo and location verification
- Hints system
- Sequential challenge progression

## Requirements

Tests require the same dependencies as the main application:
- python-telegram-bot
- pyyaml

Install with:
```bash
pip install -r ../requirements.txt
```
