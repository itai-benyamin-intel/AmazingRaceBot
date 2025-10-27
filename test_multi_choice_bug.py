"""
Test to verify the actual issue with multi_choice and photo verification.
"""
import unittest
import os
import yaml
from unittest.mock import AsyncMock, MagicMock
from bot import AmazingRaceBot


class TestMultiChoicePhotoVerificationIssue(unittest.IsolatedAsyncioTestCase):
    """Test multi_choice challenge with photo verification enabled."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config_file = "test_multi_photo_config.yml"
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
                        'description': 'Riddle',
                        'location': 'Start',
                        'type': 'riddle',
                        'verification': {
                            'method': 'answer',
                            'answer': 'test1'
                        }
                    },
                    {
                        'id': 2,
                        'name': 'Multi-Choice Question',
                        'description': 'Name three inventors',
                        'location': 'Library',
                        'type': 'multi_choice',
                        'verification': {
                            'method': 'answer',
                            'answer': 'turing, lovelace, babbage'
                        }
                        # No requires_photo_verification field - uses global setting
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
    
    async def test_multi_choice_with_global_photo_verification_enabled(self):
        """
        Test that multi_choice requires photo verification when global setting is enabled.
        This is the BUG - multi_choice should NOT require photo verification.
        """
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        bot.game_state.create_team("Team A", 111111, "Alice")
        
        # Complete first challenge
        bot.game_state.complete_challenge("Team A", 1, 2)
        
        # Verify photo verification is enabled
        self.assertTrue(bot.game_state.photo_verification_enabled)
        
        # Check if multi_choice challenge requires photo verification
        challenge2 = bot.challenges[1]
        requires_photo = bot.requires_photo_verification(challenge2, 1)
        
        print(f"Multi-choice challenge requires photo verification: {requires_photo}")
        print(f"Challenge type: {challenge2['type']}")
        
        # This is the BUG: it currently returns True, but should return False
        # because multi_choice challenges are quiz-based and don't need location verification
        if requires_photo:
            print("BUG CONFIRMED: multi_choice requires photo verification when it shouldn't!")
        
        # Now test /current command
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.bot = MagicMock()
        
        await bot.current_challenge_command(update, context)
        
        call_args = update.message.reply_text.call_args[0][0]
        print(f"\nCurrent command response:\n{call_args}\n")
        
        # Check if it shows photo verification requirement
        if "Photo Verification Required" in call_args:
            print("BUG CONFIRMED: /current shows photo verification for multi_choice!")
        
        # Now test /submit command
        update.message.reply_text.reset_mock()
        context.args = ['turing', 'lovelace', 'babbage']
        
        await bot.submit_command(update, context)
        
        call_args = update.message.reply_text.call_args[0][0]
        print(f"Submit command response:\n{call_args}\n")
        
        # Check if it blocks submission due to photo verification
        if "Photo Verification Required" in call_args:
            print("BUG CONFIRMED: /submit blocks multi_choice submission due to photo verification!")
        
        # Check if challenge was completed
        team = bot.game_state.teams["Team A"]
        if 2 not in team['completed_challenges']:
            print("BUG CONFIRMED: multi_choice challenge NOT completed due to photo verification!")
        else:
            print("Challenge was completed successfully (bug not present)")


if __name__ == '__main__':
    unittest.main()
