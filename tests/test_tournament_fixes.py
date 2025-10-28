"""
Unit tests for tournament command fixes.
Tests for:
1. Tournament first round broadcast when tournament is first challenge
2. /submit command rejection for tournament challenges  
3. /current message without /submit instructions for tournament
"""
import unittest
import os
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from bot import AmazingRaceBot
from game_state import GameState


class TestTournamentFixes(unittest.IsolatedAsyncioTestCase):
    """Test cases for tournament command fixes."""
    
    async def asyncSetUp(self):
        """Set up test fixtures."""
        # Create a test config with a tournament as first challenge
        self.test_config = {
            'telegram': {
                'bot_token': 'test_token'
            },
            'admin': 12345,
            'game': {
                'name': 'Test Race',
                'max_teams': 10,
                'max_team_size': 4,
                'challenges': [
                    {
                        'id': 1,
                        'name': 'Team Championship',
                        'type': 'tournament',
                        'location': 'Arena',
                        'description': 'Compete in the tournament',
                        'verification': {
                            'method': 'tournament'
                        },
                        'tournament': {
                            'game_name': 'Rock Paper Scissors',
                            'timeout_minutes': 5
                        }
                    },
                    {
                        'id': 2,
                        'name': 'Regular Challenge',
                        'type': 'text',
                        'location': 'Location 2',
                        'description': 'Solve the puzzle',
                        'verification': {
                            'method': 'answer',
                            'answer': 'solution'
                        }
                    }
                ]
            }
        }
        
        # Create bot with mocked config loading
        with patch.object(AmazingRaceBot, 'load_config', return_value=self.test_config):
            self.bot = AmazingRaceBot("test_config.yml")
        
        # Use a test game state file
        self.bot.game_state = GameState("test_tournament_fixes.json")
        self.bot.game_state.reset_game()
        
        # Create test teams
        self.bot.game_state.create_team("Alpha", 100, "Alice")
        self.bot.game_state.create_team("Beta", 200, "Bob")
        self.bot.game_state.create_team("Gamma", 300, "Charlie")
    
    async def asyncTearDown(self):
        """Clean up test files."""
        if os.path.exists(self.bot.game_state.state_file):
            os.remove(self.bot.game_state.state_file)
    
    async def test_submit_command_rejects_tournament(self):
        """Test that /submit command rejects submissions for tournament challenges."""
        # Start the game
        self.bot.game_state.start_game()
        
        # Create mock update and context
        update = MagicMock()
        update.effective_user.id = 100
        update.effective_user.first_name = "Alice"
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.args = ['test', 'answer']
        context.bot.send_message = AsyncMock()
        context.bot_data = {}
        
        # Call submit command
        await self.bot.submit_command(update, context)
        
        # Verify rejection message was sent
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        
        self.assertIn('Submission Not Recognized', message_text)
        self.assertIn('tournament challenge', message_text.lower())
        self.assertIn('/tournamentwin', message_text)
    
    async def test_current_command_no_submit_for_tournament(self):
        """Test that /current command doesn't show /submit instructions for tournament."""
        # Start the game and initialize tournament
        self.bot.game_state.start_game()
        
        # Create mock update and context
        update = MagicMock()
        update.effective_user.id = 100
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.bot.send_message = AsyncMock()
        
        # Call current_challenge command
        await self.bot.current_challenge_command(update, context)
        
        # Verify message was sent
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        
        # Should NOT contain submit instructions
        self.assertNotIn('/submit', message_text)
        
        # Should contain tournament information
        self.assertIn('Tournament', message_text)
        self.assertIn('Rock Paper Scissors', message_text)
    
    async def test_broadcast_shows_tournament_matches(self):
        """Test that broadcast_current_challenge shows tournament match information."""
        # Start the game
        self.bot.game_state.start_game()
        
        # Create mock context
        context = MagicMock()
        context.bot.send_message = AsyncMock()
        
        # Broadcast to Alpha team
        await self.bot.broadcast_current_challenge(context, "Alpha")
        
        # Verify message was sent to team member
        context.bot.send_message.assert_called()
        
        # Get the broadcast message
        call_args = context.bot.send_message.call_args
        message_text = call_args[1].get('text', '')
        
        # Should contain tournament information
        self.assertIn('Tournament', message_text)
        self.assertIn('Rock Paper Scissors', message_text)
        
        # Should show match information
        # The message should mention either "Your match:" or "bye"
        self.assertTrue(
            'Your match:' in message_text or 'bye' in message_text,
            f"Expected match info in message: {message_text}"
        )
        
        # Should NOT contain /submit instructions
        self.assertNotIn('/submit', message_text)
    
    async def test_tournament_initialized_on_first_broadcast(self):
        """Test that tournament is initialized when first team's challenge is broadcast."""
        # Start the game
        self.bot.game_state.start_game()
        
        # Verify tournament doesn't exist yet
        tournament = self.bot.game_state.get_tournament(1)
        self.assertIsNone(tournament)
        
        # Create mock context
        context = MagicMock()
        context.bot.send_message = AsyncMock()
        
        # Broadcast to first team
        await self.bot.broadcast_current_challenge(context, "Alpha")
        
        # Verify tournament was created
        tournament = self.bot.game_state.get_tournament(1)
        self.assertIsNotNone(tournament)
        self.assertEqual(tournament['game_name'], 'Rock Paper Scissors')
        
        # Verify all teams are in the tournament
        self.assertEqual(len(tournament['teams']), 3)
        self.assertIn('Alpha', tournament['teams'])
        self.assertIn('Beta', tournament['teams'])
        self.assertIn('Gamma', tournament['teams'])
    
    async def test_non_tournament_challenge_shows_submit(self):
        """Test that non-tournament challenges still show /submit instructions."""
        # Start the game
        self.bot.game_state.start_game()
        
        # Disable photo verification for easier testing
        self.bot.game_state.set_photo_verification(False)
        
        # Move team to second challenge (non-tournament)
        self.bot.game_state.complete_challenge("Alpha", 1, 2)
        
        # Create mock update and context
        update = MagicMock()
        update.effective_user.id = 100
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.bot.send_message = AsyncMock()
        
        # Call current_challenge command
        await self.bot.current_challenge_command(update, context)
        
        # Verify message was sent
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        
        # Should contain /submit instructions for non-tournament challenge
        self.assertIn('/submit', message_text)


if __name__ == '__main__':
    unittest.main()
