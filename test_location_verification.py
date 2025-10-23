"""
Unit tests for location verification functionality.
"""
import unittest
import os
import yaml
from unittest.mock import AsyncMock, MagicMock, patch
from bot import AmazingRaceBot
from game_state import GameState


class TestLocationVerification(unittest.TestCase):
    """Test cases for location verification functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config_file = "test_location_config.yml"
        self.test_state_file = "test_location_state.json"
        
        # Create test configuration
        self.config = {
            'telegram': {'bot_token': 'test_token'},
            'game': {
                'name': 'Test Game',
                'max_teams': 10,
                'max_team_size': 5,
                'location_verification_enabled': False,
                'challenges': [
                    {
                        'id': 1,
                        'name': 'Start Challenge',
                        'description': 'Starting point',
                        'location': 'Start',
                        'type': 'photo',
                        'verification': {'method': 'photo'},
                        'coordinates': {
                            'latitude': 37.7749,
                            'longitude': -122.4194,
                            'radius': 100
                        }
                    },
                    {
                        'id': 2,
                        'name': 'Second Challenge',
                        'description': 'Second location',
                        'location': 'Location 2',
                        'type': 'riddle',
                        'verification': {'method': 'answer', 'answer': 'test'},
                        'coordinates': {
                            'latitude': 37.7849,
                            'longitude': -122.4094,
                            'radius': 100
                        }
                    },
                    {
                        'id': 3,
                        'name': 'Third Challenge',
                        'description': 'No coordinates',
                        'location': 'Anywhere',
                        'type': 'text',
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
    
    def test_calculate_distance_same_point(self):
        """Test distance calculation for same point (should be 0)."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        distance = bot.calculate_distance(37.7749, -122.4194, 37.7749, -122.4194)
        self.assertAlmostEqual(distance, 0, places=1)
    
    def test_calculate_distance_different_points(self):
        """Test distance calculation for different points."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        # Distance between two points roughly 1km apart
        distance = bot.calculate_distance(37.7749, -122.4194, 37.7849, -122.4094)
        # Should be around 1300 meters (rough estimate)
        self.assertTrue(1000 < distance < 2000)
    
    def test_verify_location_within_radius(self):
        """Test location verification when within radius."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        challenge = self.config['game']['challenges'][0]
        
        # Same location
        is_valid, distance = bot.verify_location(37.7749, -122.4194, challenge)
        self.assertTrue(is_valid)
        self.assertAlmostEqual(distance, 0, places=1)
    
    def test_verify_location_outside_radius(self):
        """Test location verification when outside radius."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        challenge = self.config['game']['challenges'][0]
        
        # Location far away
        is_valid, distance = bot.verify_location(37.8749, -122.4194, challenge)
        self.assertFalse(is_valid)
        self.assertTrue(distance > 100)
    
    def test_verify_location_no_coordinates(self):
        """Test location verification when challenge has no coordinates."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        challenge = self.config['game']['challenges'][2]  # Challenge without coordinates
        
        # Should pass verification when no coordinates are set
        is_valid, distance = bot.verify_location(37.7749, -122.4194, challenge)
        self.assertTrue(is_valid)
        self.assertEqual(distance, 0)
    
    def test_location_verification_state_persistence(self):
        """Test that location verification state is saved and loaded."""
        game_state = GameState(self.test_state_file)
        
        # Initially should be False
        self.assertFalse(game_state.location_verification_enabled)
        
        # Toggle it
        result = game_state.toggle_location_verification()
        self.assertTrue(result)
        self.assertTrue(game_state.location_verification_enabled)
        
        # Create new instance and verify it's loaded correctly
        new_game_state = GameState(self.test_state_file)
        self.assertTrue(new_game_state.location_verification_enabled)
    
    def test_set_location_verification(self):
        """Test setting location verification state."""
        game_state = GameState(self.test_state_file)
        
        # Set to True
        game_state.set_location_verification(True)
        self.assertTrue(game_state.location_verification_enabled)
        
        # Set to False
        game_state.set_location_verification(False)
        self.assertFalse(game_state.location_verification_enabled)
    
    def test_reset_game_clears_location_verification(self):
        """Test that reset clears location verification state."""
        game_state = GameState(self.test_state_file)
        
        # Enable location verification
        game_state.set_location_verification(True)
        self.assertTrue(game_state.location_verification_enabled)
        
        # Reset game
        game_state.reset_game()
        self.assertFalse(game_state.location_verification_enabled)


class TestLocationVerificationCommands(unittest.IsolatedAsyncioTestCase):
    """Test cases for location verification commands."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config_file = "test_location_config.yml"
        self.test_state_file = "test_location_state.json"
        
        self.config = {
            'telegram': {'bot_token': 'test_token'},
            'game': {
                'name': 'Test Game',
                'max_teams': 10,
                'max_team_size': 5,
                'location_verification_enabled': False,
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
    
    async def test_togglelocation_command_admin(self):
        """Test togglelocation command by admin."""
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
        self.assertFalse(bot.game_state.location_verification_enabled)
        
        # Toggle to True
        await bot.togglelocation_command(update, context)
        self.assertTrue(bot.game_state.location_verification_enabled)
        
        # Verify message was sent
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0]
        self.assertIn("enabled", message)
    
    async def test_togglelocation_command_non_admin(self):
        """Test togglelocation command by non-admin (should be rejected)."""
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
        
        await bot.togglelocation_command(update, context)
        
        # Verify rejection message
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0]
        self.assertIn("Only admins", message)
        
        # State should not have changed
        self.assertFalse(bot.game_state.location_verification_enabled)



if __name__ == '__main__':
    unittest.main()
