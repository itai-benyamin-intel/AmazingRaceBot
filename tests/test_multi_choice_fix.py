"""
Unit tests for multi_choice challenge fixes.
Tests that multi_choice and other answer-based challenges work correctly
with /current and /submit commands, regardless of photo verification settings.
"""
import unittest
import os
import yaml
from unittest.mock import AsyncMock, MagicMock
from bot import AmazingRaceBot


class TestMultiChoiceChallengeFix(unittest.IsolatedAsyncioTestCase):
    """Test cases for multi_choice challenge fixes."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config_file = "test_multi_choice_fix_config.yml"
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
                        'description': 'First riddle',
                        'location': 'Start',
                        'type': 'riddle',
                        'verification': {
                            'method': 'answer',
                            'answer': 'paris'
                        }
                    },
                    {
                        'id': 2,
                        'name': 'Multi-Choice Challenge',
                        'description': 'Name three inventors',
                        'location': 'Library',
                        'type': 'multi_choice',
                        'verification': {
                            'method': 'answer',
                            'answer': 'turing, lovelace, babbage'
                        }
                    },
                    {
                        'id': 3,
                        'name': 'Code Challenge',
                        'description': 'Debug the code',
                        'location': 'Lab',
                        'type': 'code',
                        'verification': {
                            'method': 'answer',
                            'acceptable_answers': ['5', 'five']
                        }
                    },
                    {
                        'id': 4,
                        'name': 'Photo Challenge',
                        'description': 'Take a team photo',
                        'location': 'Park',
                        'type': 'photo',
                        'verification': {
                            'method': 'photo'
                        }
                    }
                ]
            },
            'admin': 123456789
        }
        
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
    
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.test_config_file):
            os.remove(self.test_config_file)
        if os.path.exists("game_state.json"):
            os.remove("game_state.json")
    
    async def test_multi_choice_no_photo_verification_with_global_enabled(self):
        """Test that multi_choice doesn't require photo verification even when global setting is enabled."""
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        bot.game_state.create_team("Team A", 111111, "Alice")
        
        # Complete first challenge
        bot.game_state.complete_challenge("Team A", 1, 4)
        
        # Verify photo verification is enabled globally
        self.assertTrue(bot.game_state.photo_verification_enabled)
        
        # Verify multi_choice doesn't require photo verification
        challenge2 = bot.challenges[1]
        self.assertFalse(bot.requires_photo_verification(challenge2, 1))
    
    async def test_current_command_shows_multi_choice_details(self):
        """Test that /current shows multi_choice challenge details, not photo verification message."""
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        bot.game_state.create_team("Team A", 111111, "Alice")
        bot.game_state.complete_challenge("Team A", 1, 4)
        
        # Mock update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.bot = MagicMock()
        
        # Call /current
        await bot.current_challenge_command(update, context)
        
        # Verify response shows challenge details, not photo verification
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn("Multi-Choice Challenge", call_args)
        self.assertIn("Name three inventors", call_args)
        self.assertIn("multi_choice", call_args.lower())
        self.assertNotIn("Photo Verification Required", call_args)
    
    async def test_submit_command_auto_verifies_multi_choice(self):
        """Test that /submit auto-verifies multi_choice answers without photo verification."""
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        bot.game_state.create_team("Team A", 111111, "Alice")
        bot.game_state.complete_challenge("Team A", 1, 4)
        
        # Mock update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.effective_user.first_name = "Alice"
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.bot = MagicMock()
        context.bot.send_message = AsyncMock()
        context.bot_data = {}
        context.args = ['turing', 'lovelace', 'babbage']
        
        # Call /submit
        await bot.submit_command(update, context)
        
        # Verify response shows success, not photo verification required
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn("Correct", call_args)
        self.assertNotIn("Photo Verification Required", call_args)
        
        # Verify challenge was completed
        team = bot.game_state.teams["Team A"]
        self.assertIn(2, team['completed_challenges'])
    
    async def test_answer_based_challenges_no_photo_verification(self):
        """Test that multi_choice challenges don't require photo verification by default."""
        bot = AmazingRaceBot(self.test_config_file)
        
        # Test riddle (challenge 1) - index 0 never requires
        challenge1 = bot.challenges[0]
        self.assertFalse(bot.requires_photo_verification(challenge1, 0))
        
        # Test multi_choice (challenge 2) - should not require by default
        challenge2 = bot.challenges[1]
        self.assertFalse(bot.requires_photo_verification(challenge2, 1))
        
        # Test code (challenge 3) - uses global setting
        challenge3 = bot.challenges[2]
        self.assertTrue(bot.requires_photo_verification(challenge3, 2))
    
    async def test_photo_challenge_no_location_verification_by_default(self):
        """Test that photo challenges don't require location verification by default.
        
        Photo challenges (like team_activity, scavenger) require a photo submission
        as the answer itself, not as proof of location arrival. Therefore, they should
        NOT require location verification by default, even when photo_verification_enabled
        is True globally.
        """
        bot = AmazingRaceBot(self.test_config_file)
        
        # Photo verification enabled by default
        self.assertTrue(bot.game_state.photo_verification_enabled)
        
        # Test photo challenge (challenge 4)
        challenge4 = bot.challenges[3]
        # Photo challenges should NOT require location verification by default
        # because the photo IS the challenge itself
        self.assertFalse(bot.requires_photo_verification(challenge4, 3))
    
    async def test_explicit_requires_photo_verification_overrides(self):
        """Test that explicit requires_photo_verification=True overrides the default 
        multi_choice behavior (which is to not require photo verification)."""
        # Create config with explicit photo verification for multi_choice challenge
        config = {
            'telegram': {'bot_token': 'test_token'},
            'game': {
                'name': 'Test Game',
                'max_teams': 10,
                'max_team_size': 5,
                'challenges': [
                    {
                        'id': 1,
                        'name': 'Challenge 1',
                        'description': 'First',
                        'location': 'Start',
                        'type': 'riddle',
                        'verification': {'method': 'answer', 'answer': 'test'}
                    },
                    {
                        'id': 2,
                        'name': 'Special Multi-Choice',
                        'description': 'Requires location',
                        'location': 'Specific Place',
                        'type': 'multi_choice',
                        'verification': {
                            'method': 'answer',
                            'answer': 'test'
                        },
                        'requires_photo_verification': True  # Explicit override
                    }
                ]
            },
            'admin': 123456789
        }
        
        test_file = "test_explicit_override.yml"
        with open(test_file, 'w') as f:
            yaml.dump(config, f)
        
        try:
            bot = AmazingRaceBot(test_file)
            
            # Explicit True should be honored even for multi_choice
            challenge2 = bot.challenges[1]
            self.assertTrue(bot.requires_photo_verification(challenge2, 1))
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)
            if os.path.exists("game_state.json"):
                os.remove("game_state.json")


if __name__ == '__main__':
    unittest.main()
