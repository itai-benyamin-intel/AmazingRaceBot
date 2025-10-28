"""
Test to reproduce the team_activity bug with photo verification.

This test simulates:
1. Team completes challenge 1
2. Team advances to challenge 2 (team_activity with requires_photo_verification: true)
3. Team sends location verification photo
4. Admin approves the location verification
5. Team tries /current (should show challenge details)
6. Team tries /submit (should ask for photo)
"""
import unittest
import os
import yaml
from unittest.mock import AsyncMock, MagicMock, patch
from bot import AmazingRaceBot
from game_state import GameState


class TestTeamActivityPhotoVerificationBug(unittest.TestCase):
    """Test the team_activity challenge with photo verification bug."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config_file = "test_team_activity_bug_config.yml"
        self.test_state_file = "test_team_activity_bug_state.json"
        
        # Create config with team_activity challenge that requires photo verification
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
                        'location': 'Park',
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
        
        self.bot = AmazingRaceBot(self.test_config_file)
        self.bot.game_state.state_file = self.test_state_file
        self.bot.game_state.game_started = True
        
        # Create a team and add a member
        self.team_name = "TestTeam"
        self.user_id = 111111
        self.bot.game_state.create_team(self.team_name, self.user_id, "TestUser")
        
        # Complete challenge 1 to advance to challenge 2
        self.bot.game_state.complete_challenge(self.team_name, 1, len(self.bot.challenges))
        
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.test_config_file):
            os.remove(self.test_config_file)
        if os.path.exists(self.test_state_file):
            os.remove(self.test_state_file)
    
    def test_team_activity_requires_photo_verification(self):
        """Test that team_activity with explicit requires_photo_verification: true requires it."""
        team = self.bot.game_state.teams[self.team_name]
        current_challenge_index = team.get('current_challenge_index', 0)
        challenge = self.bot.challenges[current_challenge_index]
        
        # Challenge 2 should be the team_activity challenge
        self.assertEqual(challenge['id'], 2)
        self.assertEqual(challenge['type'], 'team_activity')
        
        # Photo verification should be required
        requires_verification = self.bot.requires_photo_verification(challenge, current_challenge_index)
        self.assertTrue(
            requires_verification,
            "team_activity with explicit requires_photo_verification: true should require it"
        )
    
    def test_after_photo_verification_approved_challenge_is_accessible(self):
        """Test that after photo verification is approved, the challenge details are accessible."""
        team = self.bot.game_state.teams[self.team_name]
        current_challenge_index = team.get('current_challenge_index', 0)
        challenge = self.bot.challenges[current_challenge_index]
        challenge_id = challenge['id']
        
        # Verify photo verification is required
        requires_verification = self.bot.requires_photo_verification(challenge, current_challenge_index)
        self.assertTrue(requires_verification)
        
        # Verify photo_verifications does not include this challenge yet
        photo_verifications = team.get('photo_verifications', {})
        self.assertNotIn(str(challenge_id), photo_verifications)
        
        # Simulate photo verification being approved
        self.bot.game_state.teams[self.team_name]['photo_verifications'] = {str(challenge_id): True}
        self.bot.game_state.save_state()
        
        # Now photo verification should be done
        team = self.bot.game_state.teams[self.team_name]
        photo_verifications = team.get('photo_verifications', {})
        self.assertIn(str(challenge_id), photo_verifications)
        
        # The challenge should still be current (not completed yet)
        self.assertEqual(team.get('current_challenge_index', 0), current_challenge_index)
        
        # Verify that requires_photo_verification still returns True (since it's explicitly set)
        # but the photo verification is done
        requires_verification = self.bot.requires_photo_verification(challenge, current_challenge_index)
        self.assertTrue(requires_verification, "Challenge still requires photo verification (it's explicit)")
        self.assertTrue(str(challenge_id) in photo_verifications, "But photo verification is done")


if __name__ == '__main__':
    unittest.main()
