"""
Unit tests for the /startgame command broadcast functionality.
"""
import unittest
import os
import yaml
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call
from bot import AmazingRaceBot


class TestStartGameBroadcast(unittest.TestCase):
    """Test cases for the /startgame command broadcast functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config_file = "test_start_game_broadcast_config.yml"
        
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
                        'description': 'First challenge description',
                        'location': 'Starting Point',
                        'type': 'riddle',
                        'verification': {'method': 'answer', 'answer': 'test'},
                        'hints': ['Hint 1', 'Hint 2']
                    },
                    {
                        'id': 2,
                        'name': 'Challenge 2',
                        'description': 'Second challenge description',
                        'location': 'Second Location',
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
    def test_startgame_broadcasts_current_challenge(self, mock_context_types, mock_update):
        """Test that /startgame broadcasts current challenge to all team members."""
        async def _test():
            # Setup
            admin_id = 999999999
            player1_id = 123456
            player2_id = 789012
            
            mock_update.effective_user = MagicMock(id=admin_id, first_name='Admin')
            mock_update.message = MagicMock()
            mock_update.message.reply_text = AsyncMock()
            
            # Create mock context
            mock_context = MagicMock()
            mock_context.bot = MagicMock()
            mock_context.bot.send_message = AsyncMock()
            
            # Create teams with players
            self.bot.game_state.create_team('Team A', player1_id, 'Player1')
            self.bot.game_state.join_team('Team A', player2_id, 'Player2')
            
            # Execute
            await self.bot.start_game_command(mock_update, mock_context)
            
            # Verify
            # Admin should get reply
            mock_update.message.reply_text.assert_called_once()
            admin_message = mock_update.message.reply_text.call_args[0][0]
            
            # Check enhanced start message
            self.assertIn('THE GAME HAS STARTED', admin_message)
            self.assertIn('/current', admin_message)
            self.assertIn('/submit', admin_message)
            self.assertIn('/challenges', admin_message)
            self.assertIn('/hint', admin_message)
            self.assertIn('/myteam', admin_message)
            
            # Team members should get game start message
            send_message_calls = mock_context.bot.send_message.call_args_list
            
            # Should have at least 2 calls for game start message (player1, player2)
            # Plus additional calls for current challenge broadcast
            self.assertGreater(len(send_message_calls), 2)
            
            # Check that both players got messages
            player_ids_messaged = [call.kwargs['chat_id'] for call in send_message_calls]
            self.assertIn(player1_id, player_ids_messaged)
            self.assertIn(player2_id, player_ids_messaged)
            
            # Verify that current challenge info was broadcast
            challenge_broadcasts = [call for call in send_message_calls 
                                   if 'New Challenge Available' in call.kwargs.get('text', '')]
            self.assertGreater(len(challenge_broadcasts), 0, 
                              "Should broadcast current challenge after game starts")
            
            # Verify challenge details in broadcast
            challenge_message = challenge_broadcasts[0].kwargs['text']
            self.assertIn('Challenge #1', challenge_message)
            self.assertIn('Challenge 1', challenge_message)
            self.assertIn('First challenge description', challenge_message)
        
        asyncio.run(_test())
    
    @patch('bot.Update')
    @patch('bot.ContextTypes')
    def test_startgame_admin_as_player_gets_broadcast(self, mock_context_types, mock_update):
        """Test that admin who is also a player receives the challenge broadcast."""
        async def _test():
            # Setup
            admin_id = 999999999
            player1_id = 123456
            
            mock_update.effective_user = MagicMock(id=admin_id, first_name='Admin')
            mock_update.message = MagicMock()
            mock_update.message.reply_text = AsyncMock()
            
            # Create mock context
            mock_context = MagicMock()
            mock_context.bot = MagicMock()
            mock_context.bot.send_message = AsyncMock()
            
            # Create team with admin as a member
            self.bot.game_state.create_team('Team A', admin_id, 'Admin')
            self.bot.game_state.join_team('Team A', player1_id, 'Player1')
            
            # Execute
            await self.bot.start_game_command(mock_update, mock_context)
            
            # Verify
            send_message_calls = mock_context.bot.send_message.call_args_list
            
            # Check that admin got messages (both game start and challenge broadcast)
            admin_messages = [call for call in send_message_calls 
                             if call.kwargs['chat_id'] == admin_id]
            
            # Admin should receive at least 2 messages:
            # 1. Game start message
            # 2. Current challenge broadcast
            self.assertGreaterEqual(len(admin_messages), 2, 
                                   "Admin as player should receive game start and challenge broadcast")
            
            # Verify admin got the challenge broadcast
            admin_challenge_broadcasts = [call for call in admin_messages 
                                         if 'New Challenge Available' in call.kwargs.get('text', '')]
            self.assertGreater(len(admin_challenge_broadcasts), 0,
                              "Admin as player should receive current challenge broadcast")
        
        asyncio.run(_test())
    
    @patch('bot.Update')
    @patch('bot.ContextTypes')
    def test_startgame_admin_not_player_no_challenge_broadcast(self, mock_context_types, mock_update):
        """Test that admin who is NOT a player does NOT receive the challenge broadcast."""
        async def _test():
            # Setup
            admin_id = 999999999
            player1_id = 123456
            player2_id = 789012
            
            mock_update.effective_user = MagicMock(id=admin_id, first_name='Admin')
            mock_update.message = MagicMock()
            mock_update.message.reply_text = AsyncMock()
            
            # Create mock context
            mock_context = MagicMock()
            mock_context.bot = MagicMock()
            mock_context.bot.send_message = AsyncMock()
            
            # Create team WITHOUT admin
            self.bot.game_state.create_team('Team A', player1_id, 'Player1')
            self.bot.game_state.join_team('Team A', player2_id, 'Player2')
            
            # Execute
            await self.bot.start_game_command(mock_update, mock_context)
            
            # Verify
            send_message_calls = mock_context.bot.send_message.call_args_list
            
            # Check that admin did NOT get any direct messages
            admin_messages = [call for call in send_message_calls 
                             if call.kwargs['chat_id'] == admin_id]
            
            # Admin should NOT receive messages via send_message
            # (only via reply_text to their command)
            self.assertEqual(len(admin_messages), 0,
                            "Admin who is not a player should not receive broadcast messages")
            
            # But players should receive both game start and challenge broadcast
            player1_messages = [call for call in send_message_calls 
                               if call.kwargs['chat_id'] == player1_id]
            player2_messages = [call for call in send_message_calls 
                               if call.kwargs['chat_id'] == player2_id]
            
            self.assertGreater(len(player1_messages), 0, "Player1 should receive messages")
            self.assertGreater(len(player2_messages), 0, "Player2 should receive messages")
            
            # Verify players got challenge broadcast
            player1_challenge = [call for call in player1_messages 
                                if 'New Challenge Available' in call.kwargs.get('text', '')]
            self.assertGreater(len(player1_challenge), 0, 
                              "Player should receive challenge broadcast")
        
        asyncio.run(_test())


if __name__ == '__main__':
    unittest.main()
