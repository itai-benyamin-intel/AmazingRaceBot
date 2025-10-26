"""
Unit tests for teams and leaderboard commands.
Tests that /leaderboard is admin-only and /teams shows team info without progress.
"""
import unittest
import os
import yaml
from unittest.mock import AsyncMock, MagicMock
from bot import AmazingRaceBot


class TestTeamsAndLeaderboardCommands(unittest.IsolatedAsyncioTestCase):
    """Test cases for teams and leaderboard commands."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config_file = "test_teams_config.yml"
        self.config = {
            'telegram': {'bot_token': 'test_token'},
            'game': {
                'max_teams': 10,
                'max_team_size': 5,
                'challenges': [
                    {'id': 1, 'name': 'Challenge 1', 'description': 'Test 1', 'location': 'Loc 1'},
                    {'id': 2, 'name': 'Challenge 2', 'description': 'Test 2', 'location': 'Loc 2'},
                ]
            },
            'admin': 123456789
        }
        
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        self.bot = AmazingRaceBot(self.test_config_file)
        
        # Create some test teams
        self.bot.game_state.create_team("Team Alpha", 111, "Alice")
        self.bot.game_state.join_team("Team Alpha", 112, "Bob")
        self.bot.game_state.join_team("Team Alpha", 113, "Charlie")
        
        self.bot.game_state.create_team("Team Beta", 211, "David")
        self.bot.game_state.join_team("Team Beta", 212, "Eve")
        
        # Start the game
        self.bot.game_state.start_game()
        
        # Have Team Alpha complete a challenge
        self.bot.game_state.complete_challenge("Team Alpha", 1, 2)
        
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.test_config_file):
            os.remove(self.test_config_file)
        if os.path.exists("game_state.json"):
            os.remove("game_state.json")
    
    async def test_leaderboard_admin_only(self):
        """Test that /leaderboard is only accessible to admins."""
        # Create update and context for a regular player
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111  # Regular player (Alice from Team Alpha)
        update.message = AsyncMock()
        
        context = MagicMock()
        
        # Call leaderboard command
        await self.bot.leaderboard_command(update, context)
        
        # Verify that a rejection message was sent
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn("Only admins", call_args)
        self.assertIn("/teams", call_args)
    
    async def test_leaderboard_admin_access(self):
        """Test that admin can access /leaderboard."""
        # Create update and context for admin
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 123456789  # Admin ID
        update.message = AsyncMock()
        
        context = MagicMock()
        
        # Call leaderboard command
        await self.bot.leaderboard_command(update, context)
        
        # Verify that leaderboard was shown
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn("Leaderboard", call_args)
        self.assertIn("Team Alpha", call_args)
        self.assertIn("Team Beta", call_args)
        # Should show progress
        self.assertIn("1/2", call_args)  # Team Alpha completed 1/2
    
    async def test_teams_command_shows_members_without_progress(self):
        """Test that /teams shows team members but not progress."""
        # Create update and context for a regular player
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111  # Regular player
        update.message = AsyncMock()
        
        context = MagicMock()
        
        # Call teams command
        await self.bot.teams_command(update, context)
        
        # Verify response
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args[0][0]
        
        # Should show team names
        self.assertIn("Team Alpha", call_args)
        self.assertIn("Team Beta", call_args)
        
        # Should show captains
        self.assertIn("Alice", call_args)
        self.assertIn("David", call_args)
        self.assertIn("Captain", call_args)
        
        # Should show members
        self.assertIn("Bob", call_args)
        self.assertIn("Charlie", call_args)
        self.assertIn("Eve", call_args)
        
        # Should NOT show progress
        self.assertNotIn("1/2", call_args)
        self.assertNotIn("0/2", call_args)
        self.assertNotIn("Progress", call_args)
        self.assertNotIn("FINISHED", call_args)
    
    async def test_teams_command_shows_member_count(self):
        """Test that /teams shows total member count."""
        # Create update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111
        update.message = AsyncMock()
        
        context = MagicMock()
        
        # Call teams command
        await self.bot.teams_command(update, context)
        
        # Verify member counts are shown
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn("3/5", call_args)  # Team Alpha has 3 members, max is 5
        self.assertIn("2/5", call_args)  # Team Beta has 2 members
    
    async def test_endgame_broadcasts_leaderboard(self):
        """Test that /endgame broadcasts leaderboard to all players."""
        # This test verifies the existing behavior that should be maintained
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 123456789  # Admin
        update.message = AsyncMock()
        
        context = MagicMock()
        context.bot = MagicMock()
        context.bot.send_message = AsyncMock()
        
        # Call endgame command
        await self.bot.end_game_command(update, context)
        
        # Verify admin got the message
        update.message.reply_text.assert_called_once()
        admin_message = update.message.reply_text.call_args[0][0]
        self.assertIn("GAME OVER", admin_message)
        self.assertIn("Final Standings", admin_message)
        
        # Verify broadcast to team members (all players except admin)
        # Should send to 111, 112, 113, 211, 212 (all team members)
        self.assertEqual(context.bot.send_message.call_count, 5)
        
        # Verify broadcast includes leaderboard
        broadcast_calls = context.bot.send_message.call_args_list
        for call in broadcast_calls:
            message_text = call[1]['text']
            self.assertIn("GAME OVER", message_text)
            self.assertIn("Team Alpha", message_text)
            self.assertIn("Team Beta", message_text)


if __name__ == '__main__':
    unittest.main()
