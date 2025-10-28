"""
Unit tests for team_activity challenge type.
Tests that team_activity challenges work correctly without requiring location verification.
"""
import unittest
import os
import yaml
from bot import AmazingRaceBot
from game_state import GameState


class TestTeamActivityChallenge(unittest.TestCase):
    """Test cases for team_activity challenge type."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config_file = "test_team_activity_config.yml"
        self.test_state_file = "test_team_activity_state.json"
        
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.test_config_file):
            os.remove(self.test_config_file)
        if os.path.exists(self.test_state_file):
            os.remove(self.test_state_file)
    
    def test_team_activity_no_location_verification_by_default(self):
        """Test that team_activity challenges don't require location verification by default."""
        config = {
            'telegram': {'bot_token': 'test_token'},
            'game': {
                'name': 'Test Game',
                'max_teams': 10,
                'max_team_size': 5,
                'challenges': [
                    {
                        'id': 1,
                        'name': 'First Challenge',
                        'description': 'Complete first task',
                        'location': 'Start',
                        'type': 'text',
                        'verification': {'method': 'answer', 'answer': 'test'}
                    },
                    {
                        'id': 2,
                        'name': 'Team Pyramid',
                        'description': 'Create a human pyramid with your team',
                        'location': 'Outdoor Area',
                        'type': 'team_activity',
                        'verification': {'method': 'photo'}
                    }
                ]
            },
            'admin': 123456789
        }
        
        with open(self.test_config_file, 'w') as f:
            yaml.dump(config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.state_file = self.test_state_file
        
        # Enable photo verification globally
        bot.game_state.photo_verification_enabled = True
        bot.game_state.save_state()
        
        # Get the team_activity challenge (index 1, which is challenge 2)
        challenge = bot.challenges[1]
        
        # Team activity challenges should NOT require location verification
        # even when photo_verification_enabled is True
        requires_verification = bot.requires_photo_verification(challenge, 1)
        
        self.assertFalse(
            requires_verification,
            "team_activity challenges should not require location verification by default"
        )
    
    def test_photo_challenge_no_location_verification_by_default(self):
        """Test that photo challenges don't require location verification by default."""
        config = {
            'telegram': {'bot_token': 'test_token'},
            'game': {
                'name': 'Test Game',
                'max_teams': 10,
                'max_team_size': 5,
                'challenges': [
                    {
                        'id': 1,
                        'name': 'First Challenge',
                        'description': 'Complete first task',
                        'location': 'Start',
                        'type': 'text',
                        'verification': {'method': 'answer', 'answer': 'test'}
                    },
                    {
                        'id': 2,
                        'name': 'Photo Challenge',
                        'description': 'Take a team photo',
                        'location': 'Anywhere',
                        'type': 'photo',
                        'verification': {'method': 'photo'}
                    }
                ]
            },
            'admin': 123456789
        }
        
        with open(self.test_config_file, 'w') as f:
            yaml.dump(config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.state_file = self.test_state_file
        
        # Enable photo verification globally
        bot.game_state.photo_verification_enabled = True
        bot.game_state.save_state()
        
        # Get the photo challenge (index 1)
        challenge = bot.challenges[1]
        
        # Photo challenges should NOT require location verification
        requires_verification = bot.requires_photo_verification(challenge, 1)
        
        self.assertFalse(
            requires_verification,
            "photo challenges should not require location verification by default"
        )
    
    def test_scavenger_challenge_no_location_verification_by_default(self):
        """Test that scavenger challenges don't require location verification by default."""
        config = {
            'telegram': {'bot_token': 'test_token'},
            'game': {
                'name': 'Test Game',
                'max_teams': 10,
                'max_team_size': 5,
                'challenges': [
                    {
                        'id': 1,
                        'name': 'First Challenge',
                        'description': 'Complete first task',
                        'location': 'Start',
                        'type': 'text',
                        'verification': {'method': 'answer', 'answer': 'test'}
                    },
                    {
                        'id': 2,
                        'name': 'Scavenger Hunt',
                        'description': 'Find 5 items',
                        'location': 'Campus',
                        'type': 'scavenger',
                        'verification': {'method': 'photo', 'photos_required': 5}
                    }
                ]
            },
            'admin': 123456789
        }
        
        with open(self.test_config_file, 'w') as f:
            yaml.dump(config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.state_file = self.test_state_file
        
        # Enable photo verification globally
        bot.game_state.photo_verification_enabled = True
        bot.game_state.save_state()
        
        # Get the scavenger challenge (index 1)
        challenge = bot.challenges[1]
        
        # Scavenger challenges should NOT require location verification
        requires_verification = bot.requires_photo_verification(challenge, 1)
        
        self.assertFalse(
            requires_verification,
            "scavenger challenges should not require location verification by default"
        )
    
    def test_location_based_challenge_with_explicit_photo_verification(self):
        """Test that riddle/text challenges can still require location verification if explicitly set."""
        config = {
            'telegram': {'bot_token': 'test_token'},
            'game': {
                'name': 'Test Game',
                'max_teams': 10,
                'max_team_size': 5,
                'challenges': [
                    {
                        'id': 1,
                        'name': 'First Challenge',
                        'description': 'Complete first task',
                        'location': 'Start',
                        'type': 'text',
                        'verification': {'method': 'answer', 'answer': 'test'}
                    },
                    {
                        'id': 2,
                        'name': 'Riddle at Library',
                        'description': 'Solve riddle',
                        'location': 'Library',
                        'type': 'riddle',
                        'verification': {'method': 'answer', 'answer': 'book'},
                        'requires_photo_verification': True  # Explicitly require location verification
                    }
                ]
            },
            'admin': 123456789
        }
        
        with open(self.test_config_file, 'w') as f:
            yaml.dump(config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.state_file = self.test_state_file
        
        # Get the riddle challenge (index 1)
        challenge = bot.challenges[1]
        
        # Riddle challenge with explicit requires_photo_verification should require it
        requires_verification = bot.requires_photo_verification(challenge, 1)
        
        self.assertTrue(
            requires_verification,
            "riddle challenges with explicit requires_photo_verification should require it"
        )
    
    def test_team_activity_with_explicit_photo_verification(self):
        """Test that team_activity can still require location verification if explicitly set."""
        config = {
            'telegram': {'bot_token': 'test_token'},
            'game': {
                'name': 'Test Game',
                'max_teams': 10,
                'max_team_size': 5,
                'challenges': [
                    {
                        'id': 1,
                        'name': 'First Challenge',
                        'description': 'Complete first task',
                        'location': 'Start',
                        'type': 'text',
                        'verification': {'method': 'answer', 'answer': 'test'}
                    },
                    {
                        'id': 2,
                        'name': 'Team Pyramid at Park',
                        'description': 'Create a human pyramid',
                        'location': 'Central Park',
                        'type': 'team_activity',
                        'verification': {'method': 'photo'},
                        'requires_photo_verification': True  # Explicitly require location verification
                    }
                ]
            },
            'admin': 123456789
        }
        
        with open(self.test_config_file, 'w') as f:
            yaml.dump(config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.state_file = self.test_state_file
        
        # Get the team_activity challenge (index 1)
        challenge = bot.challenges[1]
        
        # Team activity with explicit requires_photo_verification should require it
        requires_verification = bot.requires_photo_verification(challenge, 1)
        
        self.assertTrue(
            requires_verification,
            "team_activity with explicit requires_photo_verification should require it"
        )


if __name__ == '__main__':
    unittest.main()
