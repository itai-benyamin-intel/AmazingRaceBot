"""
Unit tests for the /message and /broadcast admin commands.
"""
import unittest
import os
import yaml
from unittest.mock import AsyncMock, MagicMock, patch
from bot import AmazingRaceBot


class TestMessageCommand(unittest.IsolatedAsyncioTestCase):
    """Test cases for the /message command."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config_file = "test_message_config.yml"
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
                        'description': 'First challenge',
                        'location': 'Start',
                        'type': 'riddle',
                        'verification': {
                            'method': 'answer',
                            'answer': 'test1'
                        }
                    }
                ]
            },
            'admin': 123456789
        }
        
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        self.bot = AmazingRaceBot(self.test_config_file)
        
        # Create test teams
        self.bot.game_state.create_team("RedTeam", 111111, "Alice")
        self.bot.game_state.join_team("RedTeam", 222222, "Bob")
        self.bot.game_state.create_team("BlueTeam", 333333, "Charlie")
    
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.test_config_file):
            os.remove(self.test_config_file)
        if os.path.exists("game_state.json"):
            os.remove("game_state.json")
    
    async def test_message_command_admin_only(self):
        """Test that /message command is admin-only."""
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 999999  # Not admin
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.args = ["RedTeam", "Hello"]
        
        await self.bot.message_command(update, context)
        
        # Verify access denied
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn("Only admins", call_args)
    
    async def test_message_command_no_args(self):
        """Test /message command without arguments starts interactive flow."""
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 123456789  # Admin
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.args = []
        
        await self.bot.message_command(update, context)
        
        # Verify interactive flow starts with team selection
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn("Select the team", call_args)
        # Verify reply_markup is present (keyboard with team buttons)
        call_kwargs = update.message.reply_text.call_args[1]
        self.assertIn('reply_markup', call_kwargs)
    
    async def test_message_command_team_not_exist(self):
        """Test /message command with non-existent team."""
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 123456789  # Admin
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.args = ["NonExistentTeam", "Hello"]
        context.bot = MagicMock()
        context.bot.send_message = AsyncMock()
        
        await self.bot.message_command(update, context)
        
        # Verify error message
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn("doesn't exist", call_args)
    
    async def test_message_command_sends_to_team(self):
        """Test /message command sends message to all team members."""
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 123456789  # Admin
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.args = ["RedTeam", "Great", "job!"]
        context.bot = MagicMock()
        context.bot.send_message = AsyncMock()
        
        await self.bot.message_command(update, context)
        
        # Verify message was sent to both team members (Alice and Bob)
        self.assertEqual(context.bot.send_message.call_count, 2)
        
        # Verify confirmation was sent to admin
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn("Message Sent", call_args)
        self.assertIn("RedTeam", call_args)
        
        # Verify the message content
        message_calls = context.bot.send_message.call_args_list
        for call in message_calls:
            _, kwargs = call
            self.assertIn("Great job!", kwargs['text'])
            self.assertIn("Message from Admin", kwargs['text'])
    
    async def test_message_command_interactive_team_selection(self):
        """Test /message interactive flow - team selection callback."""
        # Create a mock callback query for team selection
        update = MagicMock()
        update.callback_query = MagicMock()
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        update.callback_query.data = "msg_team_RedTeam"
        
        context = MagicMock()
        context.user_data = {}
        
        await self.bot.message_team_callback_handler(update, context)
        
        # Verify team selection was processed
        update.callback_query.answer.assert_called_once()
        update.callback_query.edit_message_text.assert_called_once()
        
        # Verify waiting state is set correctly
        self.assertIn('waiting_for', context.user_data)
        self.assertEqual(context.user_data['waiting_for']['command'], 'message')
        self.assertEqual(context.user_data['waiting_for']['team_name'], 'RedTeam')
        
        # Verify the message asks for the message text
        call_args = update.callback_query.edit_message_text.call_args[0][0]
        self.assertIn("RedTeam", call_args)
        self.assertIn("enter the message", call_args)


class TestBroadcastCommand(unittest.IsolatedAsyncioTestCase):
    """Test cases for the /broadcast command."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config_file = "test_broadcast_config.yml"
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
                        'description': 'First challenge',
                        'location': 'Start',
                        'type': 'riddle',
                        'verification': {
                            'method': 'answer',
                            'answer': 'test1'
                        }
                    }
                ]
            },
            'admin': 123456789
        }
        
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        self.bot = AmazingRaceBot(self.test_config_file)
        
        # Create test teams
        self.bot.game_state.create_team("RedTeam", 111111, "Alice")
        self.bot.game_state.join_team("RedTeam", 222222, "Bob")
        self.bot.game_state.create_team("BlueTeam", 333333, "Charlie")
    
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.test_config_file):
            os.remove(self.test_config_file)
        if os.path.exists("game_state.json"):
            os.remove("game_state.json")
    
    async def test_broadcast_command_admin_only(self):
        """Test that /broadcast command is admin-only."""
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 999999  # Not admin
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.args = ["Hello", "everyone"]
        
        await self.bot.broadcast_command(update, context)
        
        # Verify access denied
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn("Only admins", call_args)
    
    async def test_broadcast_command_no_args(self):
        """Test /broadcast command without arguments starts interactive flow."""
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 123456789  # Admin
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.args = []
        context.user_data = {}
        
        await self.bot.broadcast_command(update, context)
        
        # Verify interactive flow starts - asking for message
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn("enter the message", call_args)
        # Verify waiting state is set
        self.assertIn('waiting_for', context.user_data)
        self.assertEqual(context.user_data['waiting_for']['command'], 'broadcast')
    
    async def test_broadcast_command_no_teams(self):
        """Test /broadcast command when no teams exist."""
        # Clear teams
        self.bot.game_state.teams = {}
        
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 123456789  # Admin
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.args = ["Hello"]
        context.bot = MagicMock()
        context.bot.send_message = AsyncMock()
        
        await self.bot.broadcast_command(update, context)
        
        # Verify error message
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn("No teams exist", call_args)
    
    async def test_broadcast_command_sends_to_all_teams(self):
        """Test /broadcast command sends message to all teams."""
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 123456789  # Admin
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.args = ["Great", "work", "everyone!"]
        context.bot = MagicMock()
        context.bot.send_message = AsyncMock()
        
        await self.bot.broadcast_command(update, context)
        
        # Verify message was sent to all 3 unique members (Alice, Bob, Charlie)
        self.assertEqual(context.bot.send_message.call_count, 3)
        
        # Verify confirmation was sent to admin
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn("Broadcast Sent", call_args)
        self.assertIn("2", call_args)  # 2 teams
        
        # Verify the message content
        message_calls = context.bot.send_message.call_args_list
        for call in message_calls:
            _, kwargs = call
            self.assertIn("Great work everyone!", kwargs['text'])
            self.assertIn("Broadcast from Admin", kwargs['text'])
    
    async def test_broadcast_command_avoids_duplicates(self):
        """Test /broadcast command avoids sending duplicate messages to same user."""
        # Create a scenario where the same user is in multiple teams (edge case)
        # This shouldn't normally happen but the code handles it
        
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 123456789  # Admin
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.args = ["Test", "message"]
        context.bot = MagicMock()
        context.bot.send_message = AsyncMock()
        
        await self.bot.broadcast_command(update, context)
        
        # Verify each unique user only gets one message
        sent_to = set()
        message_calls = context.bot.send_message.call_args_list
        for call in message_calls:
            _, kwargs = call
            chat_id = kwargs['chat_id']
            self.assertNotIn(chat_id, sent_to, "Duplicate message sent to same user")
            sent_to.add(chat_id)


if __name__ == '__main__':
    unittest.main()
