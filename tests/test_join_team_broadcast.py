"""
Unit tests for the /jointeam command broadcast functionality.
"""
import unittest
import os
import yaml
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from bot import AmazingRaceBot


class TestJoinTeamBroadcast(unittest.TestCase):
    """Test cases for the /jointeam command broadcast functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config_file = "test_join_team_broadcast_config.yml"
        
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
                        'location': 'Starting Point',
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
    def test_jointeam_broadcasts_to_existing_members(self, mock_context_types, mock_update):
        """Test that /jointeam broadcasts a welcome message to existing team members."""
        async def _test():
            # Setup
            player1_id = 123456
            player2_id = 789012
            player3_id = 345678
            
            # Create team with two existing members
            self.bot.game_state.create_team('Team Alpha', player1_id, 'Alice')
            self.bot.game_state.join_team('Team Alpha', player2_id, 'Bob')
            
            # Setup mock for new player joining
            mock_update.effective_user = MagicMock(id=player3_id, first_name='Charlie')
            mock_update.message = MagicMock()
            mock_update.message.reply_text = AsyncMock()
            
            # Create mock context
            mock_context = MagicMock()
            mock_context.args = ['Team', 'Alpha']
            mock_context.bot = MagicMock()
            mock_context.bot.send_message = AsyncMock()
            
            # Execute
            await self.bot.join_team_command(mock_update, mock_context)
            
            # Verify
            # New player should get confirmation message
            mock_update.message.reply_text.assert_called_once()
            reply_text = mock_update.message.reply_text.call_args[0][0]
            self.assertIn('You joined team', reply_text)
            self.assertIn('Team Alpha', reply_text)
            
            # Existing team members should get broadcast message
            send_message_calls = mock_context.bot.send_message.call_args_list
            
            # Should be exactly 2 calls (one for each existing member)
            self.assertEqual(len(send_message_calls), 2,
                           "Should send broadcast to both existing team members")
            
            # Check that both existing players got messages
            player_ids_messaged = [call.kwargs['chat_id'] for call in send_message_calls]
            self.assertIn(player1_id, player_ids_messaged, "Alice should receive notification")
            self.assertIn(player2_id, player_ids_messaged, "Bob should receive notification")
            self.assertNotIn(player3_id, player_ids_messaged, 
                           "Charlie (new joiner) should NOT receive broadcast")
            
            # Verify message content
            for call in send_message_calls:
                message = call.kwargs['text']
                self.assertIn('New Team Member', message)
                self.assertIn('Charlie', message, "Should mention new member's name")
                self.assertIn('Team Alpha', message, "Should mention team name")
                self.assertIn('3/5', message, "Should show updated team size")
        
        asyncio.run(_test())
    
    @patch('bot.Update')
    @patch('bot.ContextTypes')
    def test_jointeam_no_broadcast_for_first_member(self, mock_context_types, mock_update):
        """Test that no broadcast is sent when the first person creates a team."""
        async def _test():
            # Setup
            player1_id = 123456
            
            mock_update.effective_user = MagicMock(id=player1_id, first_name='Alice')
            mock_update.message = MagicMock()
            mock_update.message.reply_text = AsyncMock()
            
            # Create mock context
            mock_context = MagicMock()
            mock_context.args = ['Team', 'Alpha']
            mock_context.bot = MagicMock()
            mock_context.bot.send_message = AsyncMock()
            
            # Create the team (first member)
            await self.bot.create_team_command(mock_update, mock_context)
            
            # Verify
            # No broadcast messages should be sent (only reply to command)
            mock_context.bot.send_message.assert_not_called()
        
        asyncio.run(_test())
    
    @patch('bot.Update')
    @patch('bot.ContextTypes')
    def test_jointeam_broadcast_includes_welcome_emoji(self, mock_context_types, mock_update):
        """Test that the broadcast message includes a welcoming emoji."""
        async def _test():
            # Setup
            player1_id = 123456
            player2_id = 789012
            
            # Create team with one existing member
            self.bot.game_state.create_team('Team Beta', player1_id, 'Alice')
            
            # Setup mock for new player joining
            mock_update.effective_user = MagicMock(id=player2_id, first_name='Bob')
            mock_update.message = MagicMock()
            mock_update.message.reply_text = AsyncMock()
            
            # Create mock context
            mock_context = MagicMock()
            mock_context.args = ['Team', 'Beta']
            mock_context.bot = MagicMock()
            mock_context.bot.send_message = AsyncMock()
            
            # Execute
            await self.bot.join_team_command(mock_update, mock_context)
            
            # Verify
            send_message_calls = mock_context.bot.send_message.call_args_list
            
            # Check message has emoji/welcoming content
            message = send_message_calls[0].kwargs['text']
            self.assertIn('🎉', message, "Should include celebration emoji")
            self.assertIn('Welcome', message, "Should include welcoming message")
        
        asyncio.run(_test())
    
    @patch('bot.Update')
    @patch('bot.ContextTypes')
    def test_jointeam_broadcast_handles_multiple_existing_members(self, mock_context_types, mock_update):
        """Test that broadcast is sent to all existing members when multiple exist."""
        async def _test():
            # Setup
            player1_id = 111111
            player2_id = 222222
            player3_id = 333333
            player4_id = 444444
            player5_id = 555555
            
            # Create team with four existing members
            self.bot.game_state.create_team('Team Gamma', player1_id, 'Alice')
            self.bot.game_state.join_team('Team Gamma', player2_id, 'Bob')
            self.bot.game_state.join_team('Team Gamma', player3_id, 'Charlie')
            self.bot.game_state.join_team('Team Gamma', player4_id, 'Diana')
            
            # Setup mock for new player joining (5th member - max team size)
            mock_update.effective_user = MagicMock(id=player5_id, first_name='Eve')
            mock_update.message = MagicMock()
            mock_update.message.reply_text = AsyncMock()
            
            # Create mock context
            mock_context = MagicMock()
            mock_context.args = ['Team', 'Gamma']
            mock_context.bot = MagicMock()
            mock_context.bot.send_message = AsyncMock()
            
            # Execute
            await self.bot.join_team_command(mock_update, mock_context)
            
            # Verify
            send_message_calls = mock_context.bot.send_message.call_args_list
            
            # Should send to all 4 existing members
            self.assertEqual(len(send_message_calls), 4,
                           "Should send broadcast to all 4 existing team members")
            
            # Check that all existing players got messages
            player_ids_messaged = [call.kwargs['chat_id'] for call in send_message_calls]
            self.assertIn(player1_id, player_ids_messaged)
            self.assertIn(player2_id, player_ids_messaged)
            self.assertIn(player3_id, player_ids_messaged)
            self.assertIn(player4_id, player_ids_messaged)
            self.assertNotIn(player5_id, player_ids_messaged, 
                           "New joiner should NOT receive broadcast")
        
        asyncio.run(_test())
    
    @patch('bot.Update')
    @patch('bot.ContextTypes')
    def test_jointeam_no_broadcast_when_already_in_team(self, mock_context_types, mock_update):
        """Test that no broadcast is sent when user tries to join but is already in a team."""
        async def _test():
            # Setup
            player1_id = 123456
            player2_id = 789012
            
            # Create two teams
            self.bot.game_state.create_team('Team Alpha', player1_id, 'Alice')
            self.bot.game_state.create_team('Team Beta', player2_id, 'Bob')
            
            # Player 1 tries to join Team Beta (but already in Team Alpha)
            mock_update.effective_user = MagicMock(id=player1_id, first_name='Alice')
            mock_update.message = MagicMock()
            mock_update.message.reply_text = AsyncMock()
            
            # Create mock context
            mock_context = MagicMock()
            mock_context.args = ['Team', 'Beta']
            mock_context.bot = MagicMock()
            mock_context.bot.send_message = AsyncMock()
            
            # Execute
            await self.bot.join_team_command(mock_update, mock_context)
            
            # Verify
            # Error message should be sent
            mock_update.message.reply_text.assert_called_once()
            reply_text = mock_update.message.reply_text.call_args[0][0]
            self.assertIn('already in a team', reply_text)
            
            # No broadcast messages should be sent
            mock_context.bot.send_message.assert_not_called()
        
        asyncio.run(_test())
    
    @patch('bot.Update')
    @patch('bot.ContextTypes')
    def test_jointeam_broadcast_continues_on_send_failure(self, mock_context_types, mock_update):
        """Test that broadcast continues to other members even if sending to one fails."""
        async def _test():
            # Setup
            player1_id = 123456
            player2_id = 789012
            player3_id = 345678
            
            # Create team with two existing members
            self.bot.game_state.create_team('Team Delta', player1_id, 'Alice')
            self.bot.game_state.join_team('Team Delta', player2_id, 'Bob')
            
            # Setup mock for new player joining
            mock_update.effective_user = MagicMock(id=player3_id, first_name='Charlie')
            mock_update.message = MagicMock()
            mock_update.message.reply_text = AsyncMock()
            
            # Create mock context with send_message that fails for player1
            mock_context = MagicMock()
            mock_context.args = ['Team', 'Delta']
            mock_context.bot = MagicMock()
            
            # Make send_message fail for player1_id, succeed for player2_id
            async def send_message_side_effect(**kwargs):
                if kwargs['chat_id'] == player1_id:
                    raise Exception("Network error")
            
            mock_context.bot.send_message = AsyncMock(side_effect=send_message_side_effect)
            
            # Execute
            await self.bot.join_team_command(mock_update, mock_context)
            
            # Verify
            send_message_calls = mock_context.bot.send_message.call_args_list
            
            # Should attempt to send to both members even though first one fails
            self.assertEqual(len(send_message_calls), 2,
                           "Should attempt to send to both members")
            
            # Verify both attempts were made
            player_ids_attempted = [call.kwargs['chat_id'] for call in send_message_calls]
            self.assertIn(player1_id, player_ids_attempted)
            self.assertIn(player2_id, player_ids_attempted)
        
        asyncio.run(_test())


if __name__ == '__main__':
    unittest.main()
