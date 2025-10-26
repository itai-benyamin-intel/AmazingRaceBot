"""
Unit tests for the enhanced /help command and unrecognized message handler.
"""
import unittest
import os
import yaml
from unittest.mock import AsyncMock, MagicMock, patch
from bot import AmazingRaceBot


class TestHelpCommand(unittest.TestCase):
    """Test cases for the enhanced /help command."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config_file = "test_help_config.yml"
        
        # Create a minimal config
        config = {
            'telegram': {'bot_token': 'test_token'},
            'game': {
                'max_teams': 10,
                'max_team_size': 5,
                'challenges': [
                    {
                        'id': 1,
                        'description': 'Test challenge',
                        'location': 'Test location',
                        'type': 'riddle',
                        'verification': {'method': 'answer', 'answer': 'test'}
                    },
                    {
                        'id': 2,
                        'description': 'Test challenge 2',
                        'location': 'Test location 2',
                        'type': 'photo',
                        'verification': {'method': 'photo'}
                    }
                ]
            },
            'admin': 999999999
        }
        
        with open(self.test_config_file, 'w') as f:
            yaml.dump(config, f)
        
        self.bot = AmazingRaceBot(self.test_config_file)
        
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.test_config_file):
            os.remove(self.test_config_file)
        if os.path.exists("game_state.json"):
            os.remove("game_state.json")
    
    @patch('bot.Update')
    @patch('bot.ContextTypes')
    async def test_help_no_team(self, mock_context_types, mock_update):
        """Test /help when user has no team."""
        # Setup
        mock_update.effective_user = MagicMock(id=123456, first_name='TestUser')
        mock_update.message = MagicMock()
        mock_update.message.reply_text = AsyncMock()
        
        # Execute
        await self.bot.help_command(mock_update, mock_context_types)
        
        # Verify
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        message = call_args[0][0]
        
        # Check that message contains team creation instructions
        self.assertIn('not part of a team', message)
        self.assertIn('/createteam', message)
        self.assertIn('/jointeam', message)
        self.assertIn('menu button', message)
        
        # Should NOT contain game-started content
        self.assertNotIn('/current', message)
        self.assertNotIn('/submit', message)
    
    @patch('bot.Update')
    @patch('bot.ContextTypes')
    async def test_help_has_team_game_not_started(self, mock_context_types, mock_update):
        """Test /help when user has team but game hasn't started."""
        # Setup
        user_id = 123456
        mock_update.effective_user = MagicMock(id=user_id, first_name='TestUser')
        mock_update.message = MagicMock()
        mock_update.message.reply_text = AsyncMock()
        
        # Create team and add user
        self.bot.game_state.create_team('TestTeam', user_id, 'TestUser')
        
        # Execute
        await self.bot.help_command(mock_update, mock_context_types)
        
        # Verify
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        message = call_args[0][0]
        
        # Check that message contains waiting message
        self.assertIn('Waiting for Game to Start', message)
        self.assertIn('/myteam', message)
        self.assertIn('/leaderboard', message)
        self.assertIn('menu button', message)
        
        # Should NOT contain game-started content
        self.assertNotIn('/current', message)
        self.assertNotIn('/submit', message)
    
    @patch('bot.Update')
    @patch('bot.ContextTypes')
    async def test_help_game_started(self, mock_context_types, mock_update):
        """Test /help when game has started."""
        # Setup
        user_id = 123456
        mock_update.effective_user = MagicMock(id=user_id, first_name='TestUser')
        mock_update.message = MagicMock()
        mock_update.message.reply_text = AsyncMock()
        
        # Create team, add user, and start game
        self.bot.game_state.create_team('TestTeam', user_id, 'TestUser')
        self.bot.game_state.start_game()
        
        # Execute
        await self.bot.help_command(mock_update, mock_context_types)
        
        # Verify
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        message = call_args[0][0]
        
        # Check that message contains game instructions
        self.assertIn('How to Play', message)
        self.assertIn('/current', message)
        self.assertIn('/challenges', message)
        self.assertIn('/submit', message)
        self.assertIn('/hint', message)
        self.assertIn('menu button', message)
        
        # Should NOT contain team creation content
        self.assertNotIn('/createteam', message)
        self.assertNotIn('/jointeam', message)


class TestUnrecognizedMessageHandler(unittest.TestCase):
    """Test cases for unrecognized message handler."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config_file = "test_unrecognized_config.yml"
        
        # Create a minimal config
        config = {
            'telegram': {'bot_token': 'test_token'},
            'game': {
                'max_teams': 10,
                'max_team_size': 5,
                'challenges': [
                    {
                        'id': 1,
                        'description': 'Test challenge',
                        'location': 'Test location',
                        'type': 'riddle',
                        'verification': {'method': 'answer', 'answer': 'test'}
                    }
                ]
            },
            'admin': 999999999
        }
        
        with open(self.test_config_file, 'w') as f:
            yaml.dump(config, f)
        
        self.bot = AmazingRaceBot(self.test_config_file)
        
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.test_config_file):
            os.remove(self.test_config_file)
        if os.path.exists("game_state.json"):
            os.remove("game_state.json")
    
    @patch('bot.Update')
    @patch('bot.ContextTypes')
    async def test_unrecognized_text_message(self, mock_context_types, mock_update):
        """Test that unrecognized text messages get a helpful response."""
        # Setup
        mock_update.message = MagicMock()
        mock_update.message.text = "some random text that isn't a command"
        mock_update.message.reply_text = AsyncMock()
        
        # Execute
        await self.bot.unrecognized_message_handler(mock_update, mock_context_types)
        
        # Verify
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        message = call_args[0][0]
        
        # Check that message contains helpful information
        self.assertIn("didn't understand", message)
        self.assertIn('/help', message)
    
    @patch('bot.Update')
    @patch('bot.ContextTypes')
    async def test_unrecognized_handler_ignores_commands(self, mock_context_types, mock_update):
        """Test that unrecognized handler ignores commands (they have their own handlers)."""
        # Setup
        mock_update.message = MagicMock()
        mock_update.message.text = "/somecommand"
        mock_update.message.reply_text = AsyncMock()
        
        # Execute
        await self.bot.unrecognized_message_handler(mock_update, mock_context_types)
        
        # Verify - should NOT send a message
        mock_update.message.reply_text.assert_not_called()
    
    @patch('bot.Update')
    @patch('bot.ContextTypes')
    async def test_unrecognized_handler_ignores_no_message(self, mock_context_types, mock_update):
        """Test that unrecognized handler ignores updates without messages."""
        # Setup
        mock_update.message = None
        
        # Execute
        await self.bot.unrecognized_message_handler(mock_update, mock_context_types)
        
        # Verify - should not crash or send anything
        # If we get here without exception, test passes
        self.assertTrue(True)
    
    @patch('bot.Update')
    @patch('bot.ContextTypes')
    async def test_unrecognized_handler_ignores_no_text(self, mock_context_types, mock_update):
        """Test that unrecognized handler ignores messages without text."""
        # Setup
        mock_update.message = MagicMock()
        mock_update.message.text = None
        mock_update.message.reply_text = AsyncMock()
        
        # Execute
        await self.bot.unrecognized_message_handler(mock_update, mock_context_types)
        
        # Verify - should NOT send a message
        mock_update.message.reply_text.assert_not_called()


if __name__ == '__main__':
    unittest.main()
