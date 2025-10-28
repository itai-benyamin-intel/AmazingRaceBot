"""
Unit tests for help text showing team creation options after game has started.
"""
import unittest
import os
import yaml
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from bot import AmazingRaceBot


class TestHelpTextAfterGameStart(unittest.TestCase):
    """Test cases for help text after game has started."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config_file = "test_help_text_config.yml"
        
        # Create a minimal config
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
                        'description': 'First challenge',
                        'location': 'Start',
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
    def test_start_command_no_team_game_started_shows_createteam(self, mock_context_types, mock_update):
        """Test that /start shows createteam option for player without team after game starts."""
        async def _test():
            # Setup
            admin_id = 999999999
            player_id = 123456
            
            # Start the game as admin
            admin_update = MagicMock()
            admin_update.effective_user = MagicMock(id=admin_id, first_name='Admin')
            admin_update.message = MagicMock()
            admin_update.message.reply_text = AsyncMock()
            
            admin_context = MagicMock()
            admin_context.bot = MagicMock()
            admin_context.bot.send_message = AsyncMock()
            
            await self.bot.start_game_command(admin_update, admin_context)
            self.assertTrue(self.bot.game_state.game_started)
            
            # Now call /start as a player without a team
            player_update = MagicMock()
            player_update.effective_user = MagicMock(id=player_id, first_name='Player1')
            player_update.message = MagicMock()
            player_update.message.reply_text = AsyncMock()
            
            player_context = MagicMock()
            
            await self.bot.start_command(player_update, player_context)
            
            # Verify the message contains createteam and jointeam options
            player_update.message.reply_text.assert_called_once()
            message = player_update.message.reply_text.call_args[0][0]
            
            self.assertIn('/createteam', message)
            self.assertIn('/jointeam', message)
            # Check for key phrases indicating game has started but player can still join
            self.assertIn('game has already started', message.lower())
            self.assertIn('still join', message.lower())
        
        asyncio.run(_test())
    
    @patch('bot.Update')
    @patch('bot.ContextTypes')
    def test_help_command_no_team_game_started_shows_createteam(self, mock_context_types, mock_update):
        """Test that /help shows createteam option for player without team after game starts."""
        async def _test():
            # Setup
            admin_id = 999999999
            player_id = 123456
            
            # Start the game as admin
            admin_update = MagicMock()
            admin_update.effective_user = MagicMock(id=admin_id, first_name='Admin')
            admin_update.message = MagicMock()
            admin_update.message.reply_text = AsyncMock()
            
            admin_context = MagicMock()
            admin_context.bot = MagicMock()
            admin_context.bot.send_message = AsyncMock()
            
            await self.bot.start_game_command(admin_update, admin_context)
            self.assertTrue(self.bot.game_state.game_started)
            
            # Now call /help as a player without a team
            player_update = MagicMock()
            player_update.effective_user = MagicMock(id=player_id, first_name='Player1')
            player_update.message = MagicMock()
            player_update.message.reply_text = AsyncMock()
            
            player_context = MagicMock()
            
            await self.bot.help_command(player_update, player_context)
            
            # Verify the message contains createteam and jointeam options
            player_update.message.reply_text.assert_called_once()
            message = player_update.message.reply_text.call_args[0][0]
            
            self.assertIn('/createteam', message)
            self.assertIn('/jointeam', message)
            # Check for key phrases indicating game has started but player can still join
            self.assertIn('game has already started', message.lower())
            self.assertIn('still join', message.lower())
        
        asyncio.run(_test())
    
    @patch('bot.Update')
    @patch('bot.ContextTypes')
    def test_start_command_has_team_game_started_shows_gameplay(self, mock_context_types, mock_update):
        """Test that /start shows gameplay commands for player with team after game starts."""
        async def _test():
            # Setup
            admin_id = 999999999
            player_id = 123456
            
            # Create a team for the player
            self.bot.game_state.create_team('TestTeam', player_id, 'Player1')
            
            # Start the game as admin
            admin_update = MagicMock()
            admin_update.effective_user = MagicMock(id=admin_id, first_name='Admin')
            admin_update.message = MagicMock()
            admin_update.message.reply_text = AsyncMock()
            
            admin_context = MagicMock()
            admin_context.bot = MagicMock()
            admin_context.bot.send_message = AsyncMock()
            
            await self.bot.start_game_command(admin_update, admin_context)
            self.assertTrue(self.bot.game_state.game_started)
            
            # Now call /start as a player with a team
            player_update = MagicMock()
            player_update.effective_user = MagicMock(id=player_id, first_name='Player1')
            player_update.message = MagicMock()
            player_update.message.reply_text = AsyncMock()
            
            player_context = MagicMock()
            
            await self.bot.start_command(player_update, player_context)
            
            # Verify the message contains gameplay commands, not team creation
            player_update.message.reply_text.assert_called_once()
            message = player_update.message.reply_text.call_args[0][0]
            
            self.assertNotIn('/createteam', message)
            self.assertIn('/current', message)
            self.assertIn('/submit', message)
            # Check for gameplay-related text
            self.assertIn('in progress', message.lower())
        
        asyncio.run(_test())
    
    @patch('bot.Update')
    @patch('bot.ContextTypes')
    def test_start_command_no_team_game_not_started_shows_createteam(self, mock_context_types, mock_update):
        """Test that /start shows createteam option for player without team before game starts."""
        async def _test():
            # Setup
            player_id = 123456
            
            # Game NOT started
            self.assertFalse(self.bot.game_state.game_started)
            
            # Call /start as a player without a team
            player_update = MagicMock()
            player_update.effective_user = MagicMock(id=player_id, first_name='Player1')
            player_update.message = MagicMock()
            player_update.message.reply_text = AsyncMock()
            
            player_context = MagicMock()
            
            await self.bot.start_command(player_update, player_context)
            
            # Verify the message contains createteam and jointeam options
            player_update.message.reply_text.assert_called_once()
            message = player_update.message.reply_text.call_args[0][0]
            
            self.assertIn('/createteam', message)
            self.assertIn('/jointeam', message)
            # Check this is the pre-game message, not the mid-game message
            self.assertNotIn('game has already started', message.lower())
            self.assertIn('get started', message.lower())
        
        asyncio.run(_test())


if __name__ == '__main__':
    unittest.main()
