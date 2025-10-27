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
        
        # Initially should be True (default)
        self.assertTrue(game_state.photo_verification_enabled)
        
        # Toggle it
        result = game_state.toggle_photo_verification()
        self.assertFalse(result)
        self.assertFalse(game_state.photo_verification_enabled)
        
        # Create new instance and verify it's loaded correctly
        new_game_state = GameState(self.test_state_file)
        self.assertFalse(new_game_state.photo_verification_enabled)
    
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
        """Test that reset resets photo verification state to default (True)."""
        game_state = GameState(self.test_state_file)
        
        # Disable photo verification
        game_state.set_photo_verification(False)
        self.assertFalse(game_state.photo_verification_enabled)
        
        # Reset game - should restore to default (True)
        game_state.reset_game()
        self.assertTrue(game_state.photo_verification_enabled)
    
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


class TestPhotoVerificationBypass(unittest.IsolatedAsyncioTestCase):
    """Test cases for photo verification bypass prevention."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config_file = "test_bypass_config.yml"
        self.test_state_file = "test_bypass_state.json"
        
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
                        'name': 'Challenge 1',
                        'description': 'First challenge',
                        'location': 'Start',
                        'type': 'riddle',
                        'verification': {'method': 'answer', 'answer': 'test1'}
                    },
                    {
                        'id': 2,
                        'name': 'Challenge 2',
                        'description': 'Second challenge',
                        'location': 'Location 2',
                        'type': 'riddle',
                        'verification': {'method': 'answer', 'answer': 'test2'}
                    },
                    {
                        'id': 3,
                        'name': 'Challenge 3',
                        'description': 'Third challenge',
                        'location': 'Location 3',
                        'type': 'multi_choice',
                        'verification': {'method': 'answer', 'answer': 'test3'}
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
    
    async def test_submit_answer_requires_photo_verification_when_enabled(self):
        """Test that submitting an answer requires photo verification when enabled."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        
        # Enable photo verification
        bot.game_state.set_photo_verification(True)
        
        # Create team and complete first challenge
        bot.game_state.create_team("Team A", 111111, "Alice")
        bot.game_state.complete_challenge("Team A", 1, 3, {'type': 'answer'})
        
        # Mock the update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.effective_user.first_name = "Alice"
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.args = ['test2']  # Correct answer for challenge 2
        context.bot_data = {}
        
        # Try to submit answer without photo verification
        await bot.submit_command(update, context)
        
        # Verify challenge was NOT completed
        team = bot.game_state.teams["Team A"]
        self.assertEqual(len(team['completed_challenges']), 1)
        self.assertNotIn(2, team['completed_challenges'])
        
        # Verify photo verification message was sent
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn("Photo Verification Required", call_args)
        self.assertIn("Before you can submit an answer to this challenge", call_args)
    
    async def test_submit_answer_works_after_photo_verification(self):
        """Test that submitting an answer works after photo verification."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        
        # Enable photo verification
        bot.game_state.set_photo_verification(True)
        
        # Create team and complete first challenge
        bot.game_state.create_team("Team A", 111111, "Alice")
        bot.game_state.complete_challenge("Team A", 1, 3, {'type': 'answer'})
        
        # Add photo verification for challenge 2
        team = bot.game_state.teams["Team A"]
        team['photo_verifications'] = {
            '2': {
                'verified_by': 111111,
                'user_name': 'Alice',
                'photo_id': 'test_photo_id',
                'timestamp': '2024-01-01T00:00:00'
            }
        }
        bot.game_state.save_state()
        
        # Mock the update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.effective_user.first_name = "Alice"
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.args = ['test2']  # Correct answer for challenge 2
        context.bot_data = {}
        
        # Submit answer with photo verification done
        await bot.submit_command(update, context)
        
        # Verify challenge WAS completed
        team = bot.game_state.teams["Team A"]
        self.assertEqual(len(team['completed_challenges']), 2)
        self.assertIn(2, team['completed_challenges'])
        
        # Verify success message was sent
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn("Correct!", call_args)
    
    async def test_first_challenge_does_not_require_photo_verification(self):
        """Test that the first challenge does not require photo verification."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        
        # Enable photo verification
        bot.game_state.set_photo_verification(True)
        
        # Create team
        bot.game_state.create_team("Team A", 111111, "Alice")
        
        # Mock the update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.effective_user.first_name = "Alice"
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.args = ['test1']  # Correct answer for challenge 1
        context.bot_data = {}
        
        # Submit answer for first challenge (should work without photo verification)
        await bot.submit_command(update, context)
        
        # Verify challenge WAS completed
        team = bot.game_state.teams["Team A"]
        self.assertEqual(len(team['completed_challenges']), 1)
        self.assertIn(1, team['completed_challenges'])
        
        # Verify success message was sent
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn("Correct!", call_args)
    
    async def test_photo_verification_disabled_allows_submission(self):
        """Test that photo verification can be disabled."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        
        # Photo verification should be enabled by default
        self.assertTrue(bot.game_state.photo_verification_enabled)
        
        # Disable it for this test
        bot.game_state.set_photo_verification(False)
        
        # Create team and complete first challenge
        bot.game_state.create_team("Team A", 111111, "Alice")
        bot.game_state.complete_challenge("Team A", 1, 3, {'type': 'answer'})
        
        # Mock the update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.effective_user.first_name = "Alice"
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.args = ['test2']  # Correct answer for challenge 2
        context.bot_data = {}
        
        # Submit answer without photo verification (should work when disabled)
        await bot.submit_command(update, context)
        
        # Verify challenge WAS completed
        team = bot.game_state.teams["Team A"]
        self.assertEqual(len(team['completed_challenges']), 2)
        self.assertIn(2, team['completed_challenges'])


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
        
        # Initial state should be True (default)
        self.assertTrue(bot.game_state.photo_verification_enabled)
        
        # Toggle to False
        await bot.togglephotoverify_command(update, context)
        self.assertFalse(bot.game_state.photo_verification_enabled)
        
        # Verify message was sent
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0]
        self.assertIn("disabled", message)
    
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
        
        # State should not have changed from default (True)
        self.assertTrue(bot.game_state.photo_verification_enabled)


if __name__ == '__main__':
    unittest.main()
