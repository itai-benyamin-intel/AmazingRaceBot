"""
Quick test to verify multi_choice challenge behavior.
"""
import unittest
import os
import yaml
from unittest.mock import AsyncMock, MagicMock
from bot import AmazingRaceBot


class TestMultiChoiceIssue(unittest.IsolatedAsyncioTestCase):
    """Test multi_choice challenge issues."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config_file = "test_multi_choice_config.yml"
        self.config = {
            'telegram': {'bot_token': 'test_token'},
            'game': {
                'name': 'Test Game',
                'max_teams': 10,
                'max_team_size': 5,
                'challenges': [
                    {
                        'id': 1,
                        'name': 'Multi-Choice Question',
                        'description': 'Name three inventors',
                        'location': 'Anywhere',
                        'type': 'multi_choice',
                        'verification': {
                            'method': 'answer',
                            'answer': 'turing, lovelace, babbage'
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
    
    async def test_current_command_with_multi_choice(self):
        """Test that /current works with multi_choice challenges."""
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        bot.game_state.create_team("Team A", 111111, "Alice")
        
        # Mock update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.bot = MagicMock()
        
        # Call current command
        await bot.current_challenge_command(update, context)
        
        # Verify response was sent
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args[0][0]
        
        # Should show challenge details
        self.assertIn("Multi-Choice Question", call_args)
        self.assertIn("multi_choice", call_args.lower())
        print(f"Current command response:\n{call_args}")
    
    async def test_submit_auto_verification_multi_choice(self):
        """Test that /submit automatically verifies multi_choice challenges."""
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        bot.game_state.create_team("Team A", 111111, "Alice")
        
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
        
        # Call submit command
        await bot.submit_command(update, context)
        
        # Verify challenge was completed automatically (no admin verification)
        team = bot.game_state.teams["Team A"]
        self.assertEqual(len(team['completed_challenges']), 1)
        self.assertIn(1, team['completed_challenges'])
        
        # Verify correct response
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn("Correct", call_args)
        print(f"Submit response:\n{call_args}")


if __name__ == '__main__':
    unittest.main()
