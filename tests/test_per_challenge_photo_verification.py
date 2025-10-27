"""
Unit tests for per-challenge photo verification functionality.
"""
import unittest
import os
import yaml
from unittest.mock import AsyncMock, MagicMock
from bot import AmazingRaceBot
from game_state import GameState


class TestPerChallengePhotoVerification(unittest.IsolatedAsyncioTestCase):
    """Test cases for per-challenge photo verification configuration."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config_file = "test_per_challenge_config.yml"
        self.test_state_file = "test_per_challenge_state.json"
        
        # Create test configuration with mixed photo verification requirements
        self.config = {
            'telegram': {'bot_token': 'test_token'},
            'game': {
                'name': 'Test Game',
                'max_teams': 10,
                'max_team_size': 5,
                'challenges': [
                    {
                        'id': 1,
                        'name': 'Challenge 1',
                        'description': 'First challenge - no photo verification (challenge 1)',
                        'location': 'Start',
                        'type': 'riddle',
                        'verification': {'method': 'answer', 'answer': 'test1'}
                    },
                    {
                        'id': 2,
                        'name': 'Challenge 2',
                        'description': 'Second challenge - requires photo verification',
                        'location': 'Location 2',
                        'type': 'riddle',
                        'verification': {'method': 'answer', 'answer': 'test2'},
                        'requires_photo_verification': True
                    },
                    {
                        'id': 3,
                        'name': 'Challenge 3',
                        'description': 'Third challenge - no photo verification (trivia)',
                        'location': 'Location 3',
                        'type': 'trivia',
                        'verification': {'method': 'answer', 'answer': 'test3'},
                        'requires_photo_verification': False
                    },
                    {
                        'id': 4,
                        'name': 'Challenge 4',
                        'description': 'Fourth challenge - uses global setting',
                        'location': 'Location 4',
                        'type': 'riddle',
                        'verification': {'method': 'answer', 'answer': 'test4'}
                        # No requires_photo_verification field - should use global setting
                    }
                ]
            },
            'admin': 123456789
        }
        
    def tearDown(self):
        """Clean up test files."""
        for file in [self.test_config_file, self.test_state_file, "game_state.json"]:
            if os.path.exists(file):
                os.remove(file)
    
    def test_requires_photo_verification_method(self):
        """Test the requires_photo_verification method with different configurations."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        
        # Challenge 1 never requires photo verification
        challenge1 = bot.challenges[0]
        self.assertFalse(bot.requires_photo_verification(challenge1, 0))
        
        # Challenge 2 explicitly requires photo verification
        challenge2 = bot.challenges[1]
        self.assertTrue(bot.requires_photo_verification(challenge2, 1))
        
        # Challenge 3 explicitly does not require photo verification
        challenge3 = bot.challenges[2]
        self.assertFalse(bot.requires_photo_verification(challenge3, 2))
        
        # Challenge 4 uses global setting (enabled by default)
        challenge4 = bot.challenges[3]
        self.assertTrue(bot.requires_photo_verification(challenge4, 3))
        
        # Challenge 4 uses global setting (when disabled)
        bot.game_state.set_photo_verification(False)
        self.assertFalse(bot.requires_photo_verification(challenge4, 3))
    
    async def test_challenge_with_explicit_true_requires_verification(self):
        """Test that challenge with requires_photo_verification: true requires verification."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        
        # Create team and complete first challenge
        bot.game_state.create_team("Team A", 111111, "Alice")
        bot.game_state.complete_challenge("Team A", 1, 4, {'type': 'answer'})
        
        # Mock update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.effective_user.first_name = "Alice"
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.args = ['test2']  # Correct answer for challenge 2
        context.bot_data = {}
        
        # Try to submit answer without photo verification
        await bot.submit_command(update, context)
        
        # Verify challenge was NOT completed
        team = bot.game_state.teams["Team A"]
        self.assertEqual(len(team['completed_challenges']), 1)
        self.assertNotIn(2, team['completed_challenges'])
        
        # Verify photo verification message was sent
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn("Photo Verification Required", call_args)
    
    async def test_challenge_with_explicit_false_does_not_require_verification(self):
        """Test that challenge with requires_photo_verification: false does not require verification."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        
        # Create team and complete first two challenges
        bot.game_state.create_team("Team A", 111111, "Alice")
        bot.game_state.complete_challenge("Team A", 1, 4, {'type': 'answer'})
        bot.game_state.complete_challenge("Team A", 2, 4, {'type': 'answer'})
        
        # Mock update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.effective_user.first_name = "Alice"
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.args = ['test3']  # Correct answer for challenge 3
        context.bot_data = {}
        
        # Try to submit answer (should work without photo verification)
        await bot.submit_command(update, context)
        
        # Verify challenge WAS completed
        team = bot.game_state.teams["Team A"]
        self.assertEqual(len(team['completed_challenges']), 3)
        self.assertIn(3, team['completed_challenges'])
        
        # Verify success message was sent
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn("Correct!", call_args)
    
    async def test_challenge_without_field_uses_global_setting_enabled(self):
        """Test that challenge without requires_photo_verification field uses global setting when enabled."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        
        # Ensure photo verification is enabled globally
        bot.game_state.set_photo_verification(True)
        
        # Create team and complete first three challenges
        bot.game_state.create_team("Team A", 111111, "Alice")
        bot.game_state.complete_challenge("Team A", 1, 4, {'type': 'answer'})
        bot.game_state.complete_challenge("Team A", 2, 4, {'type': 'answer'})
        bot.game_state.complete_challenge("Team A", 3, 4, {'type': 'answer'})
        
        # Mock update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.effective_user.first_name = "Alice"
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.args = ['test4']  # Correct answer for challenge 4
        context.bot_data = {}
        
        # Try to submit answer without photo verification
        await bot.submit_command(update, context)
        
        # Verify challenge was NOT completed (requires photo verification via global setting)
        team = bot.game_state.teams["Team A"]
        self.assertEqual(len(team['completed_challenges']), 3)
        self.assertNotIn(4, team['completed_challenges'])
        
        # Verify photo verification message was sent
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn("Photo Verification Required", call_args)
    
    async def test_challenge_without_field_uses_global_setting_disabled(self):
        """Test that challenge without requires_photo_verification field uses global setting when disabled."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        
        # Disable photo verification globally
        bot.game_state.set_photo_verification(False)
        
        # Create team and complete first three challenges
        bot.game_state.create_team("Team A", 111111, "Alice")
        bot.game_state.complete_challenge("Team A", 1, 4, {'type': 'answer'})
        bot.game_state.complete_challenge("Team A", 2, 4, {'type': 'answer'})
        bot.game_state.complete_challenge("Team A", 3, 4, {'type': 'answer'})
        
        # Mock update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.effective_user.first_name = "Alice"
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.args = ['test4']  # Correct answer for challenge 4
        context.bot_data = {}
        
        # Try to submit answer (should work without photo verification)
        await bot.submit_command(update, context)
        
        # Verify challenge WAS completed (no photo verification required via global setting)
        team = bot.game_state.teams["Team A"]
        self.assertEqual(len(team['completed_challenges']), 4)
        self.assertIn(4, team['completed_challenges'])
        
        # Verify success message was sent
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn("Correct!", call_args)
    
    async def test_explicit_setting_overrides_global_setting(self):
        """Test that explicit requires_photo_verification setting overrides global setting."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        
        # Disable photo verification globally
        bot.game_state.set_photo_verification(False)
        
        # Create team and complete first challenge
        bot.game_state.create_team("Team A", 111111, "Alice")
        bot.game_state.complete_challenge("Team A", 1, 4, {'type': 'answer'})
        
        # Mock update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.effective_user.first_name = "Alice"
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.args = ['test2']  # Correct answer for challenge 2
        context.bot_data = {}
        
        # Try to submit answer for challenge 2 (explicitly requires photo verification)
        await bot.submit_command(update, context)
        
        # Verify challenge was NOT completed (explicit setting overrides global disabled)
        team = bot.game_state.teams["Team A"]
        self.assertEqual(len(team['completed_challenges']), 1)
        self.assertNotIn(2, team['completed_challenges'])
        
        # Verify photo verification message was sent
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn("Photo Verification Required", call_args)


if __name__ == '__main__':
    unittest.main()

