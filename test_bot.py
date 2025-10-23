"""
Unit tests for the bot implementation, specifically the contact command and admin configuration.
"""
import unittest
import os
import yaml
from unittest.mock import AsyncMock, MagicMock, patch
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


if __name__ == '__main__':
    unittest.main()
