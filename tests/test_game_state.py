"""
Unit tests for the game state management.
"""
import unittest
import os
import json
from game_state import GameState


class TestGameState(unittest.TestCase):
    """Test cases for GameState class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_state_file = "test_game_state.json"
        self.game_state = GameState(self.test_state_file)
        self.game_state.reset_game()
    
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.test_state_file):
            os.remove(self.test_state_file)
    
    def test_create_team(self):
        """Test team creation."""
        result = self.game_state.create_team("Team A", 123, "Alice")
        self.assertTrue(result)
        self.assertIn("Team A", self.game_state.teams)
        self.assertEqual(self.game_state.teams["Team A"]["captain_id"], 123)
        self.assertEqual(len(self.game_state.teams["Team A"]["members"]), 1)
        self.assertEqual(self.game_state.teams["Team A"]["current_challenge_index"], 0)
        self.assertIsNone(self.game_state.teams["Team A"]["finish_time"])
    
    def test_create_duplicate_team(self):
        """Test that duplicate team names are rejected."""
        self.game_state.create_team("Team A", 123, "Alice")
        result = self.game_state.create_team("Team A", 456, "Bob")
        self.assertFalse(result)
        self.assertEqual(len(self.game_state.teams), 1)
    
    def test_join_team(self):
        """Test joining a team."""
        self.game_state.create_team("Team A", 123, "Alice")
        result = self.game_state.join_team("Team A", 456, "Bob")
        self.assertTrue(result)
        self.assertEqual(len(self.game_state.teams["Team A"]["members"]), 2)
    
    def test_join_nonexistent_team(self):
        """Test joining a team that doesn't exist."""
        result = self.game_state.join_team("Team Z", 456, "Bob")
        self.assertFalse(result)
    
    def test_join_team_already_member(self):
        """Test that a user cannot join multiple teams."""
        self.game_state.create_team("Team A", 123, "Alice")
        self.game_state.create_team("Team B", 789, "Charlie")
        self.game_state.join_team("Team A", 456, "Bob")
        result = self.game_state.join_team("Team B", 456, "Bob")
        self.assertFalse(result)
    
    def test_complete_challenge(self):
        """Test completing a challenge sequentially."""
        self.game_state.create_team("Team A", 123, "Alice")
        # Complete first challenge (ID 1)
        result = self.game_state.complete_challenge("Team A", 1, 4)
        self.assertTrue(result)
        self.assertEqual(self.game_state.teams["Team A"]["current_challenge_index"], 1)
        self.assertIn(1, self.game_state.teams["Team A"]["completed_challenges"])
        self.assertIsNone(self.game_state.teams["Team A"]["finish_time"])
    
    def test_complete_challenge_out_of_order(self):
        """Test that challenges must be completed in order."""
        self.game_state.create_team("Team A", 123, "Alice")
        # Try to complete challenge 2 before challenge 1
        result = self.game_state.complete_challenge("Team A", 2, 4)
        self.assertFalse(result)
        self.assertEqual(self.game_state.teams["Team A"]["current_challenge_index"], 0)
        self.assertEqual(len(self.game_state.teams["Team A"]["completed_challenges"]), 0)
    
    def test_complete_all_challenges(self):
        """Test completing all challenges sets finish time."""
        self.game_state.create_team("Team A", 123, "Alice")
        total_challenges = 3
        
        # Complete challenges 1, 2, 3
        for i in range(1, total_challenges + 1):
            result = self.game_state.complete_challenge("Team A", i, total_challenges)
            self.assertTrue(result)
        
        # Check team finished
        self.assertIsNotNone(self.game_state.teams["Team A"]["finish_time"])
        self.assertEqual(len(self.game_state.teams["Team A"]["completed_challenges"]), total_challenges)
    
    def test_complete_challenge_twice(self):
        """Test that a challenge cannot be completed twice."""
        self.game_state.create_team("Team A", 123, "Alice")
        self.game_state.complete_challenge("Team A", 1, 4)
        result = self.game_state.complete_challenge("Team A", 1, 4)
        self.assertFalse(result)
        self.assertEqual(len(self.game_state.teams["Team A"]["completed_challenges"]), 1)
    
    def test_get_team_by_user(self):
        """Test getting team by user ID."""
        self.game_state.create_team("Team A", 123, "Alice")
        team_name = self.game_state.get_team_by_user(123)
        self.assertEqual(team_name, "Team A")
    
    def test_get_team_by_user_not_found(self):
        """Test getting team for user not in any team."""
        team_name = self.game_state.get_team_by_user(999)
        self.assertIsNone(team_name)
    
    def test_leaderboard(self):
        """Test leaderboard generation with new sequential system."""
        self.game_state.create_team("Team A", 123, "Alice")
        self.game_state.create_team("Team B", 456, "Bob")
        self.game_state.complete_challenge("Team A", 1, 4)
        self.game_state.complete_challenge("Team B", 1, 4)
        self.game_state.complete_challenge("Team B", 2, 4)
        
        leaderboard = self.game_state.get_leaderboard()
        self.assertEqual(len(leaderboard), 2)
        # Team B completed more challenges (2 vs 1)
        self.assertEqual(leaderboard[0][0], "Team B")
        self.assertEqual(leaderboard[0][1], 2)  # Completed challenges count
        self.assertEqual(leaderboard[1][0], "Team A")
        self.assertEqual(leaderboard[1][1], 1)
    
    def test_start_game(self):
        """Test starting the game."""
        self.assertFalse(self.game_state.game_started)
        self.game_state.start_game()
        self.assertTrue(self.game_state.game_started)
    
    def test_end_game(self):
        """Test ending the game."""
        self.assertFalse(self.game_state.game_ended)
        self.game_state.end_game()
        self.assertTrue(self.game_state.game_ended)
    
    def test_save_and_load_state(self):
        """Test state persistence."""
        self.game_state.create_team("Team A", 123, "Alice")
        self.game_state.complete_challenge("Team A", 1, 4)
        self.game_state.save_state()
        
        # Load state in new instance
        new_game_state = GameState(self.test_state_file)
        self.assertIn("Team A", new_game_state.teams)
        self.assertEqual(new_game_state.teams["Team A"]["current_challenge_index"], 1)
        self.assertEqual(len(new_game_state.teams["Team A"]["completed_challenges"]), 1)
    
    def test_reset_game(self):
        """Test resetting the game."""
        self.game_state.create_team("Team A", 123, "Alice")
        self.game_state.start_game()
        self.game_state.reset_game()
        
        self.assertEqual(len(self.game_state.teams), 0)
        self.assertFalse(self.game_state.game_started)
        self.assertFalse(self.game_state.game_ended)
    
    def test_update_team_rename(self):
        """Test renaming a team."""
        self.game_state.create_team("Team A", 123, "Alice")
        result = self.game_state.update_team("Team A", new_team_name="Team Alpha")
        self.assertTrue(result)
        self.assertIn("Team Alpha", self.game_state.teams)
        self.assertNotIn("Team A", self.game_state.teams)
    
    def test_update_team_duplicate_name(self):
        """Test that renaming to existing name fails."""
        self.game_state.create_team("Team A", 123, "Alice")
        self.game_state.create_team("Team B", 456, "Bob")
        result = self.game_state.update_team("Team A", new_team_name="Team B")
        self.assertFalse(result)
        self.assertIn("Team A", self.game_state.teams)
    
    def test_remove_team(self):
        """Test removing a team."""
        self.game_state.create_team("Team A", 123, "Alice")
        result = self.game_state.remove_team("Team A")
        self.assertTrue(result)
        self.assertNotIn("Team A", self.game_state.teams)
    
    def test_remove_nonexistent_team(self):
        """Test removing a team that doesn't exist."""
        result = self.game_state.remove_team("Team Z")
        self.assertFalse(result)
    
    def test_add_member_to_team(self):
        """Test admin adding member to team."""
        self.game_state.create_team("Team A", 123, "Alice")
        result = self.game_state.add_member_to_team("Team A", 789, "Charlie", 5)
        self.assertTrue(result)
        self.assertEqual(len(self.game_state.teams["Team A"]["members"]), 2)
    
    def test_remove_member_from_team(self):
        """Test removing a member from team."""
        self.game_state.create_team("Team A", 123, "Alice")
        self.game_state.join_team("Team A", 456, "Bob")
        result = self.game_state.remove_member_from_team("Team A", 456)
        self.assertTrue(result)
        self.assertEqual(len(self.game_state.teams["Team A"]["members"]), 1)
    
    def test_remove_last_member_fails(self):
        """Test that removing the last member (captain) fails."""
        self.game_state.create_team("Team A", 123, "Alice")
        result = self.game_state.remove_member_from_team("Team A", 123)
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()
