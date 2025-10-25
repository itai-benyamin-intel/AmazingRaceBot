"""
Unit tests for photo verification functionality.
"""
import unittest
import os
import yaml
from unittest.mock import AsyncMock, MagicMock, patch
from bot import AmazingRaceBot
from game_state import GameState


class TestPhotoVerification(unittest.TestCase):
    """Test cases for photo verification functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config_file = "test_photo_config.yml"
        self.test_state_file = "test_photo_state.json"
        
        # Create test configuration
        self.config = {
            'telegram': {'bot_token': 'test_token'},
            'game': {
                'name': 'Test Game',
                'max_teams': 10,
                'max_team_size': 5,
                'photo_verification_enabled': False,
                'challenges': [
                    {
                        'id': 1,
                        'name': 'Start Challenge',
                        'description': 'Starting point',
                        'location': 'Start',
                        'type': 'photo',
                        'verification': {'method': 'photo'}
                    },
                    {
                        'id': 2,
                        'name': 'Second Challenge',
                        'description': 'Second location',
                        'location': 'Location 2',
                        'type': 'riddle',
                        'verification': {'method': 'answer', 'answer': 'test'}
                    }
                ]
            },
            'admin': 123456789
        }
        
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.test_config_file):
            os.remove(self.test_config_file)
        if os.path.exists(self.test_state_file):
            os.remove(self.test_state_file)
        if os.path.exists("game_state.json"):
            os.remove("game_state.json")
    
    def test_photo_verification_state_persistence(self):
        """Test that photo verification state is saved and loaded."""
        game_state = GameState(self.test_state_file)
        
        # Initially should be False
        self.assertFalse(game_state.photo_verification_enabled)
        
        # Toggle it
        result = game_state.toggle_photo_verification()
        self.assertTrue(result)
        self.assertTrue(game_state.photo_verification_enabled)
        
        # Create new instance and verify it's loaded correctly
        new_game_state = GameState(self.test_state_file)
        self.assertTrue(new_game_state.photo_verification_enabled)
    
    def test_set_photo_verification(self):
        """Test setting photo verification state."""
        game_state = GameState(self.test_state_file)
        
        # Set to True
        game_state.set_photo_verification(True)
        self.assertTrue(game_state.photo_verification_enabled)
        
        # Set to False
        game_state.set_photo_verification(False)
        self.assertFalse(game_state.photo_verification_enabled)
    
    def test_reset_game_clears_photo_verification(self):
        """Test that reset clears photo verification state."""
        game_state = GameState(self.test_state_file)
        
        # Enable photo verification
        game_state.set_photo_verification(True)
        self.assertTrue(game_state.photo_verification_enabled)
        
        # Reset game
        game_state.reset_game()
        self.assertFalse(game_state.photo_verification_enabled)
    
    def test_add_pending_photo_verification(self):
        """Test adding pending photo verification."""
        game_state = GameState(self.test_state_file)
        
        # Create a team
        game_state.create_team("Test Team", 1, "Test User")
        
        # Add pending photo verification
        verification_id = game_state.add_pending_photo_verification(
            "Test Team", 2, "photo_id_123", 1, "Test User"
        )
        
        # Verify it was added
        self.assertIsNotNone(verification_id)
        self.assertIn(verification_id, game_state.pending_photo_verifications)
        
        verification = game_state.pending_photo_verifications[verification_id]
        self.assertEqual(verification['team_name'], "Test Team")
        self.assertEqual(verification['challenge_id'], 2)
        self.assertEqual(verification['photo_id'], "photo_id_123")
        self.assertEqual(verification['status'], 'pending')
    
    def test_get_pending_photo_verifications(self):
        """Test getting pending photo verifications."""
        game_state = GameState(self.test_state_file)
        game_state.create_team("Test Team", 1, "Test User")
        
        # Add two verifications
        id1 = game_state.add_pending_photo_verification(
            "Test Team", 2, "photo1", 1, "User1"
        )
        id2 = game_state.add_pending_photo_verification(
            "Test Team", 3, "photo2", 2, "User2"
        )
        
        # Get pending verifications
        pending = game_state.get_pending_photo_verifications()
        self.assertEqual(len(pending), 2)
        self.assertIn(id1, pending)
        self.assertIn(id2, pending)
    
    def test_approve_photo_verification(self):
        """Test approving photo verification."""
        game_state = GameState(self.test_state_file)
        game_state.create_team("Test Team", 1, "Test User")
        
        # Add pending verification
        verification_id = game_state.add_pending_photo_verification(
            "Test Team", 2, "photo_id", 1, "Test User"
        )
        
        # Approve it
        result = game_state.approve_photo_verification(verification_id)
        self.assertTrue(result)
        
        # Check status changed
        verification = game_state.pending_photo_verifications[verification_id]
        self.assertEqual(verification['status'], 'approved')
        
        # Check team data updated
        team = game_state.teams["Test Team"]
        self.assertIn('photo_verifications', team)
        self.assertIn('2', team['photo_verifications'])
    
    def test_reject_photo_verification(self):
        """Test rejecting photo verification."""
        game_state = GameState(self.test_state_file)
        game_state.create_team("Test Team", 1, "Test User")
        
        # Add pending verification
        verification_id = game_state.add_pending_photo_verification(
            "Test Team", 2, "photo_id", 1, "Test User"
        )
        
        # Reject it
        result = game_state.reject_photo_verification(verification_id)
        self.assertTrue(result)
        
        # Check status changed
        verification = game_state.pending_photo_verifications[verification_id]
        self.assertEqual(verification['status'], 'rejected')


class TestPhotoVerificationCommands(unittest.IsolatedAsyncioTestCase):
    """Test cases for photo verification commands."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config_file = "test_photo_config.yml"
        self.test_state_file = "test_photo_state.json"
        
        self.config = {
            'telegram': {'bot_token': 'test_token'},
            'game': {
                'name': 'Test Game',
                'max_teams': 10,
                'max_team_size': 5,
                'photo_verification_enabled': False,
                'challenges': [
                    {
                        'id': 1,
                        'name': 'Test',
                        'description': 'Test',
                        'location': 'Test',
                        'type': 'photo',
                        'verification': {'method': 'photo'}
                    }
                ]
            },
            'admin': 123456789
        }
        
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.test_config_file):
            os.remove(self.test_config_file)
        if os.path.exists(self.test_state_file):
            os.remove(self.test_state_file)
        if os.path.exists("game_state.json"):
            os.remove("game_state.json")
    
    async def test_togglephotoverify_command_admin(self):
        """Test togglephotoverify command by admin."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        
        # Mock the update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 123456789  # Admin ID
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        
        # Initial state should be False
        self.assertFalse(bot.game_state.photo_verification_enabled)
        
        # Toggle to True
        await bot.togglephotoverify_command(update, context)
        self.assertTrue(bot.game_state.photo_verification_enabled)
        
        # Verify message was sent
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0]
        self.assertIn("enabled", message)
    
    async def test_togglephotoverify_command_non_admin(self):
        """Test togglephotoverify command by non-admin (should be rejected)."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        
        # Mock the update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 999999999  # Non-admin ID
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        
        await bot.togglephotoverify_command(update, context)
        
        # Verify rejection message
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0]
        self.assertIn("Only admins", message)
        
        # State should not have changed
        self.assertFalse(bot.game_state.photo_verification_enabled)


if __name__ == '__main__':
    unittest.main()
