"""
Unit tests for the bot implementation, specifically the contact command and admin configuration.
"""
import unittest
import os
import yaml
from unittest.mock import AsyncMock, MagicMock, patch, call
from bot import AmazingRaceBot


class TestBotAdminConfiguration(unittest.TestCase):
    """Test cases for admin configuration."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config_file = "test_bot_config.yml"
        
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.test_config_file):
            os.remove(self.test_config_file)
        if os.path.exists("game_state.json"):
            os.remove("game_state.json")
    
    def test_admin_single_id_new_format(self):
        """Test that single admin ID in new format is correctly loaded."""
        config = {
            'telegram': {'bot_token': 'test_token'},
            'game': {
                'name': 'Test Game',
                'max_teams': 10,
                'max_team_size': 5,
                'challenges': [
                    {'id': 1, 'name': 'Test', 'description': 'Test', 'location': 'Test'}
                ]
            },
            'admin': 123456789
        }
        
        with open(self.test_config_file, 'w') as f:
            yaml.dump(config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        self.assertEqual(bot.admin_id, 123456789)
        self.assertTrue(bot.is_admin(123456789))
        self.assertFalse(bot.is_admin(987654321))
    
    def test_admin_list_legacy_format(self):
        """Test that list of admins in legacy format uses first admin only."""
        config = {
            'telegram': {'bot_token': 'test_token'},
            'game': {
                'name': 'Test Game',
                'max_teams': 10,
                'max_team_size': 5,
                'challenges': [
                    {'id': 1, 'name': 'Test', 'description': 'Test', 'location': 'Test'}
                ]
            },
            'admins': [123456789, 987654321]  # Legacy format
        }
        
        with open(self.test_config_file, 'w') as f:
            yaml.dump(config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        # Should only use the first admin
        self.assertEqual(bot.admin_id, 123456789)
        self.assertTrue(bot.is_admin(123456789))
        # Second admin should not be recognized
        self.assertFalse(bot.is_admin(987654321))
    
    def test_admin_empty_list_legacy_format(self):
        """Test that empty admin list results in None admin_id."""
        config = {
            'telegram': {'bot_token': 'test_token'},
            'game': {
                'name': 'Test Game',
                'max_teams': 10,
                'max_team_size': 5,
                'challenges': [
                    {'id': 1, 'name': 'Test', 'description': 'Test', 'location': 'Test'}
                ]
            },
            'admins': []
        }
        
        with open(self.test_config_file, 'w') as f:
            yaml.dump(config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        self.assertIsNone(bot.admin_id)
        self.assertFalse(bot.is_admin(123456789))
    
    def test_admin_not_configured(self):
        """Test that missing admin configuration results in None admin_id."""
        config = {
            'telegram': {'bot_token': 'test_token'},
            'game': {
                'name': 'Test Game',
                'max_teams': 10,
                'max_team_size': 5,
                'challenges': [
                    {'id': 1, 'name': 'Test', 'description': 'Test', 'location': 'Test'}
                ]
            }
        }
        
        with open(self.test_config_file, 'w') as f:
            yaml.dump(config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        self.assertIsNone(bot.admin_id)
        self.assertFalse(bot.is_admin(123456789))


class TestBotContactCommand(unittest.IsolatedAsyncioTestCase):
    """Test cases for the contact command."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config_file = "test_bot_config.yml"
        self.config = {
            'telegram': {'bot_token': 'test_token'},
            'game': {
                'name': 'Test Game',
                'max_teams': 10,
                'max_team_size': 5,
                'challenges': [
                    {'id': 1, 'name': 'Test', 'description': 'Test', 'location': 'Test'}
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
    
    async def test_contact_command_with_admin_configured(self):
        """Test contact command when admin is configured."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        
        # Mock the update and context
        update = MagicMock()
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        
        await bot.contact_command(update, context)
        
        # Verify reply_text was called
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        
        # Verify the message contains the admin link
        message = call_args[0][0]
        self.assertIn("Contact Admin", message)
        self.assertIn("tg://user?id=123456789", message)
        self.assertIn("123456789", message)
        
        # Verify parse_mode is Markdown
        self.assertEqual(call_args[1]['parse_mode'], 'Markdown')
    
    async def test_contact_command_without_admin_configured(self):
        """Test contact command when admin is not configured."""
        config_no_admin = self.config.copy()
        del config_no_admin['admin']
        
        with open(self.test_config_file, 'w') as f:
            yaml.dump(config_no_admin, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        
        # Mock the update and context
        update = MagicMock()
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        
        await bot.contact_command(update, context)
        
        # Verify reply_text was called with error message
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0]
        
        self.assertIn("No admin is configured", message)


class TestStartGameBroadcast(unittest.IsolatedAsyncioTestCase):
    """Test cases for the start game broadcast functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config_file = "test_bot_config.yml"
        self.config = {
            'telegram': {'bot_token': 'test_token'},
            'game': {
                'name': 'Test Game',
                'max_teams': 10,
                'max_team_size': 5,
                'challenges': [
                    {'id': 1, 'name': 'Test', 'description': 'Test', 'location': 'Test'}
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
    
    async def test_start_game_broadcasts_to_all_team_members(self):
        """Test that /startgame sends message to all team members."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        
        # Create teams with members
        bot.game_state.create_team("Team A", 111111, "Alice")
        bot.game_state.join_team("Team A", 222222, "Bob")
        bot.game_state.create_team("Team B", 333333, "Charlie")
        bot.game_state.join_team("Team B", 444444, "David")
        
        # Mock the update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 123456789  # Admin
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.bot = MagicMock()
        context.bot.send_message = AsyncMock()
        
        # Call start_game_command
        await bot.start_game_command(update, context)
        
        # Verify admin got the message
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0]
        self.assertIn("THE GAME HAS STARTED!", message)
        
        # Verify that send_message was called for each team member
        # Should be called 4 times (for all team members except admin)
        self.assertEqual(context.bot.send_message.call_count, 4)
        
        # Get all user IDs that received messages
        sent_user_ids = set()
        for call in context.bot.send_message.call_args_list:
            sent_user_ids.add(call[1]['chat_id'])
        
        # Verify all team members received the message
        expected_user_ids = {111111, 222222, 333333, 444444}
        self.assertEqual(sent_user_ids, expected_user_ids)
        
        # Verify the message content
        for call in context.bot.send_message.call_args_list:
            self.assertIn("THE GAME HAS STARTED!", call[1]['text'])
            self.assertEqual(call[1]['parse_mode'], 'Markdown')
    
    async def test_start_game_no_duplicate_to_admin_in_team(self):
        """Test that admin doesn't get duplicate message if they're in a team."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        
        # Create team with admin as member
        bot.game_state.create_team("Team Admin", 123456789, "Admin")
        bot.game_state.join_team("Team Admin", 222222, "Bob")
        
        # Mock the update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 123456789  # Admin
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.bot = MagicMock()
        context.bot.send_message = AsyncMock()
        
        # Call start_game_command
        await bot.start_game_command(update, context)
        
        # Verify admin got the message via reply_text
        update.message.reply_text.assert_called_once()
        
        # Verify send_message was only called once for Bob (not for admin)
        self.assertEqual(context.bot.send_message.call_count, 1)
        call_args = context.bot.send_message.call_args
        self.assertEqual(call_args[1]['chat_id'], 222222)
    
    async def test_start_game_no_teams(self):
        """Test /startgame when there are no teams."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        
        # Mock the update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 123456789  # Admin
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.bot = MagicMock()
        context.bot.send_message = AsyncMock()
        
        # Call start_game_command
        await bot.start_game_command(update, context)
        
        # Verify admin got the message
        update.message.reply_text.assert_called_once()
        
        # Verify no broadcast messages were sent (no teams)
        context.bot.send_message.assert_not_called()
    
    async def test_start_game_handles_send_failure(self):
        """Test that /startgame continues even if sending to one user fails."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        
        # Create teams
        bot.game_state.create_team("Team A", 111111, "Alice")
        bot.game_state.join_team("Team A", 222222, "Bob")
        
        # Mock the update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 123456789  # Admin
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.bot = MagicMock()
        
        # Make send_message fail for first user but succeed for second
        async def send_message_side_effect(**kwargs):
            if kwargs['chat_id'] == 111111:
                raise Exception("Failed to send")
            # Otherwise succeed silently
        
        context.bot.send_message = AsyncMock(side_effect=send_message_side_effect)
        
        # Call start_game_command - should not raise exception
        await bot.start_game_command(update, context)
        
        # Verify admin still got the message
        update.message.reply_text.assert_called_once()
        
        # Verify send_message was called for both users (even though one failed)
        self.assertEqual(context.bot.send_message.call_count, 2)


class TestEndGameBroadcast(unittest.IsolatedAsyncioTestCase):
    """Test cases for the end game broadcast functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config_file = "test_bot_config.yml"
        self.config = {
            'telegram': {'bot_token': 'test_token'},
            'game': {
                'name': 'Test Game',
                'max_teams': 10,
                'max_team_size': 5,
                'challenges': [
                    {'id': 1, 'name': 'Test', 'description': 'Test', 'location': 'Test'}
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
    
    async def test_end_game_broadcasts_to_all_team_members(self):
        """Test that /endgame sends message to all team members."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        
        # Start the game first
        bot.game_state.start_game()
        
        # Create teams with members
        bot.game_state.create_team("Team A", 111111, "Alice")
        bot.game_state.join_team("Team A", 222222, "Bob")
        bot.game_state.create_team("Team B", 333333, "Charlie")
        bot.game_state.join_team("Team B", 444444, "David")
        
        # Mock the update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 123456789  # Admin
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.bot = MagicMock()
        context.bot.send_message = AsyncMock()
        
        # Call end_game_command
        await bot.end_game_command(update, context)
        
        # Verify admin got the message
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0]
        self.assertIn("GAME OVER!", message)
        
        # Verify that send_message was called for each team member
        # Should be called 4 times (for all team members except admin)
        self.assertEqual(context.bot.send_message.call_count, 4)
        
        # Get all user IDs that received messages
        sent_user_ids = set()
        for call in context.bot.send_message.call_args_list:
            sent_user_ids.add(call[1]['chat_id'])
        
        # Verify all team members received the message
        expected_user_ids = {111111, 222222, 333333, 444444}
        self.assertEqual(sent_user_ids, expected_user_ids)
        
        # Verify the message content
        for call in context.bot.send_message.call_args_list:
            self.assertIn("GAME OVER!", call[1]['text'])
            self.assertEqual(call[1]['parse_mode'], 'Markdown')
    
    async def test_end_game_no_duplicate_to_admin_in_team(self):
        """Test that admin doesn't get duplicate message if they're in a team."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        
        # Start the game first
        bot.game_state.start_game()
        
        # Create team with admin as member
        bot.game_state.create_team("Team Admin", 123456789, "Admin")
        bot.game_state.join_team("Team Admin", 222222, "Bob")
        
        # Mock the update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 123456789  # Admin
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.bot = MagicMock()
        context.bot.send_message = AsyncMock()
        
        # Call end_game_command
        await bot.end_game_command(update, context)
        
        # Verify admin got the message via reply_text
        update.message.reply_text.assert_called_once()
        
        # Verify send_message was only called once for Bob (not for admin)
        self.assertEqual(context.bot.send_message.call_count, 1)
        call_args = context.bot.send_message.call_args
        self.assertEqual(call_args[1]['chat_id'], 222222)
    
    async def test_end_game_no_teams(self):
        """Test /endgame when there are no teams."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        
        # Start the game first
        bot.game_state.start_game()
        
        # Mock the update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 123456789  # Admin
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.bot = MagicMock()
        context.bot.send_message = AsyncMock()
        
        # Call end_game_command
        await bot.end_game_command(update, context)
        
        # Verify admin got the message
        update.message.reply_text.assert_called_once()
        
        # Verify no broadcast messages were sent (no teams)
        context.bot.send_message.assert_not_called()
    
    async def test_end_game_handles_send_failure(self):
        """Test that /endgame continues even if sending to one user fails."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        
        # Start the game first
        bot.game_state.start_game()
        
        # Create teams
        bot.game_state.create_team("Team A", 111111, "Alice")
        bot.game_state.join_team("Team A", 222222, "Bob")
        
        # Mock the update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 123456789  # Admin
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.bot = MagicMock()
        
        # Make send_message fail for first user but succeed for second
        async def send_message_side_effect(**kwargs):
            if kwargs['chat_id'] == 111111:
                raise Exception("Failed to send")
            # Otherwise succeed silently
        
        context.bot.send_message = AsyncMock(side_effect=send_message_side_effect)
        
        # Call end_game_command - should not raise exception
        await bot.end_game_command(update, context)
        
        # Verify admin still got the message
        update.message.reply_text.assert_called_once()
        
        # Verify send_message was called for both users (even though one failed)
        self.assertEqual(context.bot.send_message.call_count, 2)


if __name__ == '__main__':
    unittest.main()
