"""
Unit tests for team creation after game has started.
"""
import unittest
import os
import yaml
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from bot import AmazingRaceBot


class TestTeamCreationAfterGameStart(unittest.TestCase):
    """Test cases for team creation after game has started."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config_file = "test_team_creation_config.yml"
        
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
                    },
                    {
                        'id': 2,
                        'name': 'Challenge 2',
                        'description': 'Second challenge',
                        'location': 'Middle',
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
    def test_create_team_after_game_started(self, mock_context_types, mock_update):
        """Test that teams can be created after game has started."""
        async def _test():
            # Setup - start the game first
            admin_id = 999999999
            player1_id = 123456
            player2_id = 789012
            
            # Create admin mock and start game
            admin_update = MagicMock()
            admin_update.effective_user = MagicMock(id=admin_id, first_name='Admin')
            admin_update.message = MagicMock()
            admin_update.message.reply_text = AsyncMock()
            
            admin_context = MagicMock()
            admin_context.bot = MagicMock()
            admin_context.bot.send_message = AsyncMock()
            
            # Start the game
            await self.bot.start_game_command(admin_update, admin_context)
            self.assertTrue(self.bot.game_state.game_started)
            
            # Now try to create a team after game has started
            player_update = MagicMock()
            player_update.effective_user = MagicMock(id=player1_id, first_name='Player1')
            player_update.message = MagicMock()
            player_update.message.reply_text = AsyncMock()
            
            player_context = MagicMock()
            player_context.args = ['TeamLate']
            
            # Execute - create team after game started
            await self.bot.create_team_command(player_update, player_context)
            
            # Verify team was created successfully
            self.assertIn('TeamLate', self.bot.game_state.teams)
            self.assertEqual(self.bot.game_state.teams['TeamLate']['captain_id'], player1_id)
            
            # Verify success message was sent
            player_update.message.reply_text.assert_called_once()
            message = player_update.message.reply_text.call_args[0][0]
            self.assertIn('created successfully', message)
            self.assertIn('TeamLate', message)
        
        asyncio.run(_test())
    
    @patch('bot.Update')
    @patch('bot.ContextTypes')
    def test_join_team_after_game_started(self, mock_context_types, mock_update):
        """Test that players can join existing teams after game has started."""
        async def _test():
            # Setup - create a team first
            admin_id = 999999999
            player1_id = 123456
            player2_id = 789012
            
            # Create a team before game starts
            self.bot.game_state.create_team('TeamEarly', player1_id, 'Player1')
            
            # Start the game
            admin_update = MagicMock()
            admin_update.effective_user = MagicMock(id=admin_id, first_name='Admin')
            admin_update.message = MagicMock()
            admin_update.message.reply_text = AsyncMock()
            
            admin_context = MagicMock()
            admin_context.bot = MagicMock()
            admin_context.bot.send_message = AsyncMock()
            
            await self.bot.start_game_command(admin_update, admin_context)
            self.assertTrue(self.bot.game_state.game_started)
            
            # Now try to join team after game has started
            player_update = MagicMock()
            player_update.effective_user = MagicMock(id=player2_id, first_name='Player2')
            player_update.message = MagicMock()
            player_update.message.reply_text = AsyncMock()
            
            player_context = MagicMock()
            player_context.args = ['TeamEarly']
            player_context.bot = MagicMock()
            player_context.bot.send_message = AsyncMock()
            
            # Execute - join team after game started
            await self.bot.join_team_command(player_update, player_context)
            
            # Verify player joined successfully
            team = self.bot.game_state.teams['TeamEarly']
            self.assertEqual(len(team['members']), 2)
            self.assertTrue(any(m['id'] == player2_id for m in team['members']))
            
            # Verify success message was sent
            player_update.message.reply_text.assert_called_once()
            message = player_update.message.reply_text.call_args[0][0]
            self.assertIn('joined team', message.lower())
            self.assertIn('TeamEarly', message)
        
        asyncio.run(_test())
    
    @patch('bot.Update')
    @patch('bot.ContextTypes')
    def test_new_team_starts_from_challenge_1(self, mock_context_types, mock_update):
        """Test that a team created after game starts begins from challenge 1."""
        async def _test():
            # Setup
            admin_id = 999999999
            player1_id = 123456
            
            # Start the game
            admin_update = MagicMock()
            admin_update.effective_user = MagicMock(id=admin_id, first_name='Admin')
            admin_update.message = MagicMock()
            admin_update.message.reply_text = AsyncMock()
            
            admin_context = MagicMock()
            admin_context.bot = MagicMock()
            admin_context.bot.send_message = AsyncMock()
            
            await self.bot.start_game_command(admin_update, admin_context)
            
            # Create a team after game has started
            player_update = MagicMock()
            player_update.effective_user = MagicMock(id=player1_id, first_name='Player1')
            player_update.message = MagicMock()
            player_update.message.reply_text = AsyncMock()
            
            player_context = MagicMock()
            player_context.args = ['NewTeam']
            
            await self.bot.create_team_command(player_update, player_context)
            
            # Verify team starts from challenge 1
            team = self.bot.game_state.teams['NewTeam']
            self.assertEqual(team['current_challenge_index'], 0)  # 0-based index means challenge 1
            self.assertEqual(len(team['completed_challenges']), 0)
        
        asyncio.run(_test())


if __name__ == '__main__':
    unittest.main()
