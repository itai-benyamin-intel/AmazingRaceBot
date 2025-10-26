"""
Unit tests for interactive command behavior - commands that wait for text input.
"""
import unittest
import os
import yaml
from unittest.mock import AsyncMock, MagicMock, patch
from bot import AmazingRaceBot


class TestInteractiveCommands(unittest.IsolatedAsyncioTestCase):
    """Test cases for interactive command behavior."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config_file = "test_interactive_config.yml"
        self.config = {
            'telegram': {'bot_token': 'test_token'},
            'game': {
                'max_teams': 10,
                'max_team_size': 5,
                'challenges': [
                    {
                        'id': 1,
                        'description': 'First challenge',
                        'location': 'Start',
                        'type': 'riddle',
                        'verification': {
                            'method': 'answer',
                            'answer': 'test1'
                        }
                    },
                    {
                        'id': 2,
                        'description': 'Second challenge',
                        'location': 'Library',
                        'type': 'trivia',
                        'verification': {
                            'method': 'answer',
                            'answer': 'test2'
                        }
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
    
    async def test_createteam_without_args_waits_for_input(self):
        """Test /createteam without args asks for team name."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        
        # Mock the update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.effective_user.first_name = "Alice"
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.args = []  # No args
        context.user_data = {}
        
        # Call createteam without args
        await bot.create_team_command(update, context)
        
        # Verify it asks for team name
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn("Please provide a team name", call_args)
        
        # Verify waiting state is set
        self.assertIn('waiting_for', context.user_data)
        self.assertEqual(context.user_data['waiting_for']['command'], 'createteam')
    
    async def test_createteam_interactive_flow(self):
        """Test /createteam interactive flow - command then text response."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        
        # Mock the update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.effective_user.first_name = "Alice"
        update.message = MagicMock()
        update.message.text = "Team Alpha"
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.args = []
        context.user_data = {'waiting_for': {'command': 'createteam'}}
        
        # Call unrecognized_message_handler with the team name
        await bot.unrecognized_message_handler(update, context)
        
        # Verify team was created
        self.assertIn("Team Alpha", bot.game_state.teams)
        
        # Verify waiting state was cleared
        self.assertNotIn('waiting_for', context.user_data)
    
    async def test_jointeam_without_args_waits_for_input(self):
        """Test /jointeam without args asks for team name."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        
        # Create a team first
        bot.game_state.create_team("Team Alpha", 999999, "Bob")
        
        # Mock the update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.effective_user.first_name = "Alice"
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.args = []
        context.user_data = {}
        
        # Call jointeam without args
        await bot.join_team_command(update, context)
        
        # Verify it asks for team name
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn("Please provide the team name", call_args)
        
        # Verify waiting state is set
        self.assertIn('waiting_for', context.user_data)
        self.assertEqual(context.user_data['waiting_for']['command'], 'jointeam')
    
    async def test_jointeam_interactive_flow(self):
        """Test /jointeam interactive flow - command then text response."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        
        # Create a team first
        bot.game_state.create_team("Team Alpha", 999999, "Bob")
        
        # Mock the update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.effective_user.first_name = "Alice"
        update.message = MagicMock()
        update.message.text = "Team Alpha"
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.args = []
        context.user_data = {'waiting_for': {'command': 'jointeam'}}
        
        # Call unrecognized_message_handler with the team name
        await bot.unrecognized_message_handler(update, context)
        
        # Verify user joined the team
        team = bot.game_state.teams["Team Alpha"]
        user_ids = [m['id'] for m in team['members']]
        self.assertIn(111111, user_ids)
        
        # Verify waiting state was cleared
        self.assertNotIn('waiting_for', context.user_data)
    
    async def test_submit_without_answer_waits_for_input(self):
        """Test /submit without answer asks for it."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        bot.game_state.create_team("Team Alpha", 111111, "Alice")
        
        # Mock the update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.effective_user.first_name = "Alice"
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.args = []
        context.user_data = {}
        context.bot_data = {}
        
        # Call submit without args
        await bot.submit_command(update, context)
        
        # Verify it asks for answer
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn("Please provide your answer", call_args)
        
        # Verify waiting state is set
        self.assertIn('waiting_for', context.user_data)
        self.assertEqual(context.user_data['waiting_for']['command'], 'submit')
        self.assertEqual(context.user_data['waiting_for']['challenge_id'], 1)
    
    async def test_submit_interactive_flow(self):
        """Test /submit interactive flow - command then text answer."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        bot.game_state.create_team("Team Alpha", 111111, "Alice")
        
        # Mock the update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.effective_user.first_name = "Alice"
        update.message = MagicMock()
        update.message.text = "test1"
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.args = []
        context.user_data = {'waiting_for': {'command': 'submit', 'challenge_id': 1}}
        context.bot_data = {}
        
        # Call unrecognized_message_handler with the answer
        await bot.unrecognized_message_handler(update, context)
        
        # Verify challenge was completed
        team = bot.game_state.teams["Team Alpha"]
        self.assertEqual(len(team['completed_challenges']), 1)
        self.assertIn(1, team['completed_challenges'])
        
        # Verify waiting state was cleared
        self.assertNotIn('waiting_for', context.user_data)
    
    async def test_submit_case_insensitive_answer(self):
        """Test that submit command accepts case-insensitive answers."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        bot.game_state.create_team("Team Alpha", 111111, "Alice")
        
        # Mock the update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.effective_user.first_name = "Alice"
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        # Test with uppercase answer when expected is lowercase
        context.args = ['TEST1']
        context.bot_data = {}
        
        # Call submit with uppercase answer
        await bot.submit_command(update, context)
        
        # Verify challenge was completed (case insensitive match)
        team = bot.game_state.teams["Team Alpha"]
        self.assertEqual(len(team['completed_challenges']), 1)
        self.assertIn(1, team['completed_challenges'])
    
    async def test_addteam_without_args_waits_for_input(self):
        """Test /addteam without args asks for team name (admin only)."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        
        # Mock the update and context (as admin)
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 123456789  # Admin ID
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.args = []
        context.user_data = {}
        
        # Call addteam without args
        await bot.addteam_command(update, context)
        
        # Verify it asks for team name
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn("Please provide the team name", call_args)
        
        # Verify waiting state is set
        self.assertIn('waiting_for', context.user_data)
        self.assertEqual(context.user_data['waiting_for']['command'], 'addteam')
    
    async def test_removeteam_without_args_waits_for_input(self):
        """Test /removeteam without args asks for team name (admin only)."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        
        # Create a team first
        bot.game_state.create_team("Team Alpha", 999999, "Bob")
        
        # Mock the update and context (as admin)
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 123456789  # Admin ID
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.args = []
        context.user_data = {}
        
        # Call removeteam without args
        await bot.removeteam_command(update, context)
        
        # Verify it asks for team name
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn("Please provide the team name", call_args)
        
        # Verify waiting state is set
        self.assertIn('waiting_for', context.user_data)
        self.assertEqual(context.user_data['waiting_for']['command'], 'removeteam')
    
    async def test_unrecognized_message_without_waiting_state(self):
        """Test that unrecognized messages show help when not waiting for input."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        
        # Mock the update and context
        update = MagicMock()
        update.message = MagicMock()
        update.message.text = "random text"
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.user_data = {}
        
        # Call unrecognized_message_handler with random text
        await bot.unrecognized_message_handler(update, context)
        
        # Verify it shows help message
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn("didn't understand", call_args)
        self.assertIn("/help", call_args)


if __name__ == '__main__':
    unittest.main()
