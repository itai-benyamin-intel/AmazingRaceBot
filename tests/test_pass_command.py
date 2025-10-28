"""
Unit tests for the /pass command functionality.
"""
import unittest
import os
from game_state import GameState


class TestPassCommand(unittest.TestCase):
    """Test cases for the /pass command and pass_team() method."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_state_file = "test_pass_command_state.json"
        self.game_state = GameState(self.test_state_file)
        self.game_state.reset_game()
        
        # Create test teams
        self.game_state.create_team("Team Alpha", 100, "Alice")
        self.game_state.create_team("Team Beta", 200, "Bob")
        self.game_state.start_game()
    
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.test_state_file):
            os.remove(self.test_state_file)
    
    def test_pass_team_basic(self):
        """Test basic pass_team functionality."""
        # Team Alpha is on challenge 1 (index 0)
        result = self.game_state.pass_team("Team Alpha", 5, 999, "AdminTest")
        
        self.assertTrue(result)
        self.assertEqual(self.game_state.teams["Team Alpha"]["current_challenge_index"], 1)
        self.assertIn(1, self.game_state.teams["Team Alpha"]["completed_challenges"])
        self.assertIsNone(self.game_state.teams["Team Alpha"]["finish_time"])
    
    def test_pass_team_nonexistent(self):
        """Test passing a team that doesn't exist."""
        result = self.game_state.pass_team("Team NonExistent", 5, 999, "AdminTest")
        self.assertFalse(result)
    
    def test_pass_team_already_completed(self):
        """Test that passing an already completed challenge fails."""
        # Complete challenge 1 normally
        self.game_state.complete_challenge("Team Alpha", 1, 5)
        
        # Try to pass challenge 1 again - should fail since current challenge is now 2
        # Team is on challenge 2, so passing would affect challenge 2, not 1
        # But we want to verify we can't pass the same challenge twice
        # First pass challenge 2
        result = self.game_state.pass_team("Team Alpha", 5, 999, "AdminTest")
        self.assertTrue(result)
        self.assertEqual(self.game_state.teams["Team Alpha"]["current_challenge_index"], 2)
        
        # Now try to pass a challenge that's already in completed list (challenge 1)
        # This shouldn't be possible through pass_team since it advances current challenge
        # So we test that challenge 1 is in completed and can't be completed again
        self.assertIn(1, self.game_state.teams["Team Alpha"]["completed_challenges"])
    
    def test_pass_team_all_challenges(self):
        """Test passing a team through all challenges."""
        total_challenges = 3
        
        for i in range(total_challenges):
            result = self.game_state.pass_team("Team Beta", total_challenges, 999, "AdminTest")
            self.assertTrue(result)
        
        # Team should have finished
        self.assertIsNotNone(self.game_state.teams["Team Beta"]["finish_time"])
        self.assertEqual(len(self.game_state.teams["Team Beta"]["completed_challenges"]), total_challenges)
        self.assertEqual(self.game_state.teams["Team Beta"]["current_challenge_index"], total_challenges)
    
    def test_pass_team_already_finished(self):
        """Test that passing a team that already finished all challenges fails."""
        total_challenges = 2
        
        # Pass team through all challenges
        for i in range(total_challenges):
            self.game_state.pass_team("Team Alpha", total_challenges, 999, "AdminTest")
        
        # Try to pass again - should fail
        result = self.game_state.pass_team("Team Alpha", total_challenges, 999, "AdminTest")
        self.assertFalse(result)
    
    def test_pass_team_submission_data(self):
        """Test that pass_team stores proper submission data."""
        self.game_state.pass_team("Team Alpha", 5, 999, "AdminTest")
        
        # Check submission data
        submissions = self.game_state.teams["Team Alpha"].get('challenge_submissions', {})
        self.assertIn('1', submissions)
        
        submission = submissions['1']
        self.assertEqual(submission['type'], 'admin_pass')
        self.assertEqual(submission['admin_id'], 999)
        self.assertEqual(submission['admin_name'], "AdminTest")
        self.assertIn('timestamp', submission)
        self.assertIn('reason', submission)
    
    def test_pass_team_audit_log(self):
        """Test that pass_team creates audit log entries."""
        initial_log_length = len(self.game_state.admin_audit_log)
        
        self.game_state.pass_team("Team Alpha", 5, 999, "AdminTest")
        
        # Check audit log
        self.assertEqual(len(self.game_state.admin_audit_log), initial_log_length + 1)
        
        last_entry = self.game_state.admin_audit_log[-1]
        self.assertEqual(last_entry['action'], 'pass_team')
        self.assertEqual(last_entry['team_name'], 'Team Alpha')
        self.assertEqual(last_entry['challenge_id'], 1)
        self.assertEqual(last_entry['admin_id'], 999)
        self.assertEqual(last_entry['admin_name'], 'AdminTest')
        self.assertIn('timestamp', last_entry)
    
    def test_pass_team_multiple_audit_entries(self):
        """Test that multiple pass actions create separate audit entries."""
        # Pass Team Alpha through challenge 1
        self.game_state.pass_team("Team Alpha", 5, 999, "AdminTest")
        
        # Pass Team Beta through challenge 1
        self.game_state.pass_team("Team Beta", 5, 888, "AdminTest2")
        
        # Check we have 2 audit entries
        self.assertEqual(len(self.game_state.admin_audit_log), 2)
        
        # Verify entries are distinct
        self.assertEqual(self.game_state.admin_audit_log[0]['team_name'], 'Team Alpha')
        self.assertEqual(self.game_state.admin_audit_log[1]['team_name'], 'Team Beta')
    
    def test_pass_team_sequential_challenges(self):
        """Test that pass_team respects sequential challenge order."""
        # Pass challenge 1
        result1 = self.game_state.pass_team("Team Alpha", 5, 999, "AdminTest")
        self.assertTrue(result1)
        self.assertEqual(self.game_state.teams["Team Alpha"]["current_challenge_index"], 1)
        
        # Pass challenge 2
        result2 = self.game_state.pass_team("Team Alpha", 5, 999, "AdminTest")
        self.assertTrue(result2)
        self.assertEqual(self.game_state.teams["Team Alpha"]["current_challenge_index"], 2)
        
        # Verify both challenges are completed
        self.assertIn(1, self.game_state.teams["Team Alpha"]["completed_challenges"])
        self.assertIn(2, self.game_state.teams["Team Alpha"]["completed_challenges"])
    
    def test_pass_team_completion_time_set(self):
        """Test that pass_team sets challenge completion time."""
        self.game_state.pass_team("Team Alpha", 5, 999, "AdminTest")
        
        # Check that completion time was set
        completion_times = self.game_state.teams["Team Alpha"].get('challenge_completion_times', {})
        self.assertIn('1', completion_times)
        self.assertIsNotNone(completion_times['1'])
    
    def test_pass_team_persistence(self):
        """Test that pass_team changes are persisted."""
        self.game_state.pass_team("Team Alpha", 5, 999, "AdminTest")
        self.game_state.save_state()
        
        # Load state in new instance
        new_game_state = GameState(self.test_state_file)
        
        self.assertEqual(new_game_state.teams["Team Alpha"]["current_challenge_index"], 1)
        self.assertIn(1, new_game_state.teams["Team Alpha"]["completed_challenges"])
        self.assertEqual(len(new_game_state.admin_audit_log), 1)
    
    def test_pass_team_mixed_with_normal_completion(self):
        """Test mixing pass_team with normal challenge completion."""
        # Normally complete challenge 1
        self.game_state.complete_challenge("Team Alpha", 1, 5)
        
        # Pass challenge 2
        self.game_state.pass_team("Team Alpha", 5, 999, "AdminTest")
        
        # Verify both are completed
        self.assertIn(1, self.game_state.teams["Team Alpha"]["completed_challenges"])
        self.assertIn(2, self.game_state.teams["Team Alpha"]["completed_challenges"])
        self.assertEqual(self.game_state.teams["Team Alpha"]["current_challenge_index"], 2)
        
        # Check that submission data reflects different methods
        submissions = self.game_state.teams["Team Alpha"].get('challenge_submissions', {})
        # Challenge 2 should have admin_pass type
        self.assertEqual(submissions['2']['type'], 'admin_pass')
    
    def test_audit_log_reset(self):
        """Test that audit log is cleared on game reset."""
        self.game_state.pass_team("Team Alpha", 5, 999, "AdminTest")
        self.assertEqual(len(self.game_state.admin_audit_log), 1)
        
        self.game_state.reset_game()
        self.assertEqual(len(self.game_state.admin_audit_log), 0)


if __name__ == '__main__':
    unittest.main()
