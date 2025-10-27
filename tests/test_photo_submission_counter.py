"""
Unit tests for photo submission counter functionality.
"""
import unittest
import os
from game_state import GameState


class TestPhotoSubmissionCounter(unittest.TestCase):
    """Test cases for photo submission counter system."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.game_state = GameState("test_photo_counter.json")
        self.game_state.reset_game()
        self.game_state.create_team("Team A", 123, "Alice")
        self.game_state.start_game()
    
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.game_state.state_file):
            os.remove(self.game_state.state_file)
    
    def test_get_photo_submission_count_initial(self):
        """Test that initial photo count is 0."""
        count = self.game_state.get_photo_submission_count("Team A", 1)
        self.assertEqual(count, 0)
    
    def test_increment_photo_submission_count(self):
        """Test incrementing photo submission count."""
        self.assertTrue(self.game_state.increment_photo_submission_count("Team A", 1))
        count = self.game_state.get_photo_submission_count("Team A", 1)
        self.assertEqual(count, 1)
    
    def test_increment_photo_submission_count_multiple(self):
        """Test incrementing photo count multiple times."""
        self.game_state.increment_photo_submission_count("Team A", 1)
        self.game_state.increment_photo_submission_count("Team A", 1)
        self.game_state.increment_photo_submission_count("Team A", 1)
        count = self.game_state.get_photo_submission_count("Team A", 1)
        self.assertEqual(count, 3)
    
    def test_photo_submission_count_per_challenge(self):
        """Test that photo counts are tracked separately per challenge."""
        self.game_state.increment_photo_submission_count("Team A", 1)
        self.game_state.increment_photo_submission_count("Team A", 1)
        self.game_state.increment_photo_submission_count("Team A", 2)
        
        count_challenge_1 = self.game_state.get_photo_submission_count("Team A", 1)
        count_challenge_2 = self.game_state.get_photo_submission_count("Team A", 2)
        
        self.assertEqual(count_challenge_1, 2)
        self.assertEqual(count_challenge_2, 1)
    
    def test_photo_submission_count_per_team(self):
        """Test that photo counts are tracked separately per team."""
        self.game_state.create_team("Team B", 456, "Bob")
        
        self.game_state.increment_photo_submission_count("Team A", 1)
        self.game_state.increment_photo_submission_count("Team A", 1)
        self.game_state.increment_photo_submission_count("Team B", 1)
        
        count_team_a = self.game_state.get_photo_submission_count("Team A", 1)
        count_team_b = self.game_state.get_photo_submission_count("Team B", 1)
        
        self.assertEqual(count_team_a, 2)
        self.assertEqual(count_team_b, 1)
    
    def test_photo_submission_count_persistence(self):
        """Test that photo counts persist across saves and loads."""
        self.game_state.increment_photo_submission_count("Team A", 1)
        self.game_state.increment_photo_submission_count("Team A", 1)
        self.game_state.increment_photo_submission_count("Team A", 1)
        self.game_state.save_state()
        
        # Load state in new instance
        new_game_state = GameState(self.game_state.state_file)
        count = new_game_state.get_photo_submission_count("Team A", 1)
        
        self.assertEqual(count, 3)
    
    def test_get_photo_count_nonexistent_team(self):
        """Test that getting photo count for nonexistent team returns 0."""
        count = self.game_state.get_photo_submission_count("Nonexistent Team", 1)
        self.assertEqual(count, 0)
    
    def test_increment_photo_count_nonexistent_team(self):
        """Test that incrementing photo count for nonexistent team fails."""
        result = self.game_state.increment_photo_submission_count("Nonexistent Team", 1)
        self.assertFalse(result)
    
    def test_approve_photo_submission_single_photo(self):
        """Test approving a single photo submission (default behavior)."""
        # Add a pending submission
        submission_id = self.game_state.add_pending_photo_submission(
            "Team A", 1, "photo_123", 123, "Alice"
        )
        
        # Approve with default photos_required=1
        result = self.game_state.approve_photo_submission(submission_id, 5, photos_required=1)
        self.assertTrue(result)
        
        # Check that photo count was incremented
        count = self.game_state.get_photo_submission_count("Team A", 1)
        self.assertEqual(count, 1)
        
        # Check that challenge was completed
        team = self.game_state.teams["Team A"]
        self.assertIn(1, team['completed_challenges'])
    
    def test_approve_photo_submission_multiple_photos_partial(self):
        """Test approving photos when more are required - challenge should not complete."""
        # Add a pending submission
        submission_id = self.game_state.add_pending_photo_submission(
            "Team A", 1, "photo_123", 123, "Alice"
        )
        
        # Approve with photos_required=5 (only 1 approved so far)
        result = self.game_state.approve_photo_submission(submission_id, 5, photos_required=5)
        self.assertTrue(result)
        
        # Check that photo count was incremented
        count = self.game_state.get_photo_submission_count("Team A", 1)
        self.assertEqual(count, 1)
        
        # Check that challenge was NOT completed (need 5 photos)
        team = self.game_state.teams["Team A"]
        self.assertNotIn(1, team['completed_challenges'])
    
    def test_approve_photo_submission_multiple_photos_complete(self):
        """Test approving multiple photos until required count is reached."""
        # Approve 5 photos one by one
        for i in range(5):
            submission_id = self.game_state.add_pending_photo_submission(
                "Team A", 1, f"photo_{i}", 123, "Alice"
            )
            result = self.game_state.approve_photo_submission(submission_id, 5, photos_required=5)
            self.assertTrue(result)
        
        # Check that photo count is 5
        count = self.game_state.get_photo_submission_count("Team A", 1)
        self.assertEqual(count, 5)
        
        # Check that challenge was completed
        team = self.game_state.teams["Team A"]
        self.assertIn(1, team['completed_challenges'])
    
    def test_approve_photo_submission_exceeding_required(self):
        """Test that approving more photos than required still completes the challenge."""
        # Pre-increment to 4 photos
        for i in range(4):
            submission_id = self.game_state.add_pending_photo_submission(
                "Team A", 1, f"photo_{i}", 123, "Alice"
            )
            self.game_state.approve_photo_submission(submission_id, 5, photos_required=3)
        
        # Verify count is 4 and challenge is complete
        count = self.game_state.get_photo_submission_count("Team A", 1)
        self.assertEqual(count, 4)
        
        team = self.game_state.teams["Team A"]
        self.assertIn(1, team['completed_challenges'])


if __name__ == '__main__':
    unittest.main()
