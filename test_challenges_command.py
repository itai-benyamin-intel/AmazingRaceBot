"""
Unit tests for the challenges command - testing that locked challenges are hidden.
"""
import unittest
import os
import yaml
from unittest.mock import AsyncMock, MagicMock
from bot import AmazingRaceBot


class TestChallengesCommand(unittest.IsolatedAsyncioTestCase):
    """Test cases for the /challenges command."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config_file = "test_challenges_config.yml"
        self.config = {
            'telegram': {'bot_token': 'test_token'},
            'game': {
                'name': 'Test Game',
                'max_teams': 10,
                'max_team_size': 5,
                'challenges': [
                    {
                        'id': 1,
                        'name': 'First Challenge',
                        'description': 'Complete the first task',
                        'location': 'Starting Point',
                        'type': 'photo',
                        'verification': {'method': 'photo'}
                    },
                    {
                        'id': 2,
                        'name': 'Second Challenge',
                        'description': 'Solve the riddle',
                        'location': 'Library',
                        'type': 'riddle',
                        'verification': {'method': 'answer', 'answer': 'keyboard'}
                    },
                    {
                        'id': 3,
                        'name': 'Third Challenge',
                        'description': 'Find the location',
                        'location': 'Park',
                        'type': 'location',
                        'verification': {'method': 'location'}
                    },
                    {
                        'id': 4,
                        'name': 'Fourth Challenge',
                        'description': 'Final task',
                        'location': 'Finish Line',
                        'type': 'photo',
                        'verification': {'method': 'photo'}
                    }
                ]
            },
            'admin': 123456789
        }
        
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.test_config_file):
            os.remove(self.test_config_file)
        if os.path.exists("game_state.json"):
            os.remove("game_state.json")
    
    async def test_challenges_shows_only_completed_and_current(self):
        """Test that /challenges only shows completed challenges and current challenge, not locked ones."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        
        # Create a team and complete first challenge
        bot.game_state.create_team("Team A", 111111, "Alice")
        bot.game_state.complete_challenge("Team A", 1, 4, {'type': 'photo'})
        
        # Mock the update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        
        # Call challenges_command
        await bot.challenges_command(update, context)
        
        # Verify reply_text was called
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0]
        
        # Verify completed challenge is shown (brief format)
        self.assertIn("First Challenge", message)
        self.assertIn("✅", message)
        self.assertIn("Complete the first task", message)
        
        # Verify current challenge is shown (brief format)
        self.assertIn("Second Challenge", message)
        self.assertIn("(CURRENT)", message)
        self.assertIn("Solve the riddle", message)
        
        # Verify brief format - should NOT have type, location emoji, or instructions
        self.assertNotIn("Type:", message)
        self.assertNotIn("📍 Location:", message)
        self.assertNotIn("ℹ️", message)
        
        # Verify locked challenges are NOT shown
        self.assertNotIn("Third Challenge", message)
        self.assertNotIn("Fourth Challenge", message)
        self.assertNotIn("🔒", message)
        self.assertNotIn("LOCKED", message)
        
        # Verify hint about /current_challenge is shown
        self.assertIn("Use /current_challenge", message)
        
        # Verify hint about /submit is shown
        self.assertIn("Use /submit", message)
    
    async def test_challenges_shows_all_completed_when_finished(self):
        """Test that /challenges shows all challenges when team has finished."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        
        # Create a team and complete all challenges
        bot.game_state.create_team("Team A", 111111, "Alice")
        bot.game_state.complete_challenge("Team A", 1, 4, {'type': 'photo'})
        bot.game_state.complete_challenge("Team A", 2, 4, {'type': 'answer'})
        bot.game_state.complete_challenge("Team A", 3, 4, {'type': 'location'})
        bot.game_state.complete_challenge("Team A", 4, 4, {'type': 'photo'})
        
        # Mock the update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        
        # Call challenges_command
        await bot.challenges_command(update, context)
        
        # Verify reply_text was called
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0]
        
        # Verify all challenges are shown as completed (brief format)
        self.assertIn("First Challenge", message)
        self.assertIn("Second Challenge", message)
        self.assertIn("Third Challenge", message)
        self.assertIn("Fourth Challenge", message)
        
        # Verify all are marked as completed
        self.assertEqual(message.count("✅"), 4)
        
        # Verify brief format - should NOT have type or location
        self.assertNotIn("Type:", message)
        self.assertNotIn("📍 Location:", message)
        
        # Verify no locked challenges shown
        self.assertNotIn("🔒", message)
        self.assertNotIn("LOCKED", message)
        self.assertNotIn("(CURRENT)", message)
    
    async def test_challenges_shows_only_first_when_no_progress(self):
        """Test that /challenges shows only the first challenge when no progress made."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        
        # Create a team with no progress
        bot.game_state.create_team("Team A", 111111, "Alice")
        
        # Mock the update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        
        # Call challenges_command
        await bot.challenges_command(update, context)
        
        # Verify reply_text was called
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0]
        
        # Verify only first challenge is shown as current (brief format)
        self.assertIn("First Challenge", message)
        self.assertIn("(CURRENT)", message)
        self.assertIn("Complete the first task", message)
        
        # Verify brief format
        self.assertNotIn("Type:", message)
        self.assertNotIn("📍 Location:", message)
        
        # Verify other challenges are NOT shown
        self.assertNotIn("Second Challenge", message)
        self.assertNotIn("Third Challenge", message)
        self.assertNotIn("Fourth Challenge", message)
        self.assertNotIn("🔒", message)
        self.assertNotIn("LOCKED", message)
    
    async def test_challenges_user_not_in_team(self):
        """Test that /challenges shows first challenge even if user is not in a team."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        
        # Mock the update and context (user not in any team)
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 999999  # User not in any team
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        
        # Call challenges_command
        await bot.challenges_command(update, context)
        
        # Verify reply_text was called
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0]
        
        # Verify only first challenge is shown (brief format)
        self.assertIn("First Challenge", message)
        self.assertIn("(CURRENT)", message)
        
        # Verify brief format
        self.assertNotIn("Type:", message)
        
        # Verify other challenges are NOT shown
        self.assertNotIn("Second Challenge", message)
        self.assertNotIn("Third Challenge", message)
        self.assertNotIn("Fourth Challenge", message)


if __name__ == '__main__':
    unittest.main()
