"""
Unit tests for tournament challenge functionality.
"""
import unittest
import os
from game_state import GameState


class TestTournament(unittest.TestCase):
    """Test cases for tournament system."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.game_state = GameState("test_tournament.json")
        self.game_state.reset_game()
        
        # Create test teams
        self.game_state.create_team("Alpha", 1, "Alice")
        self.game_state.create_team("Beta", 2, "Bob")
        self.game_state.create_team("Gamma", 3, "Charlie")
        self.game_state.create_team("Delta", 4, "David")
    
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.game_state.state_file):
            os.remove(self.game_state.state_file)
    
    def test_create_tournament_even_teams(self):
        """Test creating a tournament with even number of teams."""
        teams = ["Alpha", "Beta", "Gamma", "Delta"]
        success = self.game_state.create_tournament(1, teams, "Rock Paper Scissors")
        
        self.assertTrue(success)
        
        tournament = self.game_state.get_tournament(1)
        self.assertIsNotNone(tournament)
        self.assertEqual(tournament['challenge_id'], 1)
        self.assertEqual(tournament['game_name'], "Rock Paper Scissors")
        self.assertEqual(tournament['status'], 'active')
        self.assertEqual(len(tournament['teams']), 4)
        
        # Should have 2 matches in first round (4 teams = 2 matches)
        bracket = tournament['bracket']
        self.assertEqual(len(bracket), 1)  # One round initially
        self.assertEqual(len(bracket[0]), 2)  # Two matches
    
    def test_create_tournament_odd_teams(self):
        """Test creating a tournament with odd number of teams."""
        teams = ["Alpha", "Beta", "Gamma"]
        success = self.game_state.create_tournament(1, teams, "Tournament")
        
        self.assertTrue(success)
        
        tournament = self.game_state.get_tournament(1)
        self.assertIsNotNone(tournament)
        
        # Should have 2 matches in first round (1 bye + 1 match)
        bracket = tournament['bracket']
        self.assertEqual(len(bracket[0]), 2)
        
        # One should be a bye
        bye_count = sum(1 for m in bracket[0] if m['status'] == 'bye')
        self.assertEqual(bye_count, 1)
    
    def test_create_tournament_already_exists(self):
        """Test that creating a tournament for same challenge twice fails."""
        teams = ["Alpha", "Beta"]
        success1 = self.game_state.create_tournament(1, teams, "Game1")
        success2 = self.game_state.create_tournament(1, teams, "Game2")
        
        self.assertTrue(success1)
        self.assertFalse(success2)
    
    def test_get_current_round_matches(self):
        """Test getting current round matches."""
        teams = ["Alpha", "Beta", "Gamma", "Delta"]
        self.game_state.create_tournament(1, teams, "Tournament")
        
        matches = self.game_state.get_current_round_matches(1)
        self.assertEqual(len(matches), 2)
        
        # All should be pending
        pending_count = sum(1 for m in matches if m['status'] == 'pending')
        self.assertEqual(pending_count, 2)
    
    def test_report_match_winner(self):
        """Test reporting match winners."""
        teams = ["Alpha", "Beta", "Gamma", "Delta"]
        self.game_state.create_tournament(1, teams, "Tournament")
        
        # Get first match
        matches = self.game_state.get_current_round_matches(1)
        first_match = matches[0]
        winner = first_match['team1']
        
        # Report winner
        success = self.game_state.report_match_winner(1, winner)
        self.assertTrue(success)
        
        # Check match status
        updated_matches = self.game_state.get_current_round_matches(1)
        updated_match = [m for m in updated_matches if m['team1'] == winner or m['team2'] == winner][0]
        self.assertEqual(updated_match['status'], 'complete')
        self.assertEqual(updated_match['winner'], winner)
    
    def test_tournament_advancement(self):
        """Test that tournament advances to next round after all matches complete."""
        teams = ["Alpha", "Beta", "Gamma", "Delta"]
        self.game_state.create_tournament(1, teams, "Tournament")
        
        # Complete all matches in round 1
        matches = self.game_state.get_current_round_matches(1)
        self.assertEqual(len(matches), 2)
        
        # Report winners for both matches
        for match in matches:
            self.game_state.report_match_winner(1, match['team1'])
        
        # Should now be in round 2
        tournament = self.game_state.get_tournament(1)
        self.assertEqual(tournament['current_round'], 1)  # 0-indexed
        
        # Round 2 should have 1 match (2 winners)
        round2_matches = self.game_state.get_current_round_matches(1)
        self.assertEqual(len(round2_matches), 1)
    
    def test_tournament_completion(self):
        """Test tournament completes when only one winner remains."""
        teams = ["Alpha", "Beta"]
        self.game_state.create_tournament(1, teams, "Tournament")
        
        # Complete the only match
        matches = self.game_state.get_current_round_matches(1)
        self.assertEqual(len(matches), 1)
        
        winner = matches[0]['team1']
        self.game_state.report_match_winner(1, winner)
        
        # Tournament should be complete
        self.assertTrue(self.game_state.is_tournament_complete(1))
        
        tournament = self.game_state.get_tournament(1)
        self.assertEqual(tournament['status'], 'complete')
    
    def test_get_last_place(self):
        """Test getting last place team from completed tournament."""
        teams = ["Alpha", "Beta"]
        self.game_state.create_tournament(1, teams, "Tournament")
        
        # Complete match
        matches = self.game_state.get_current_round_matches(1)
        winner = matches[0]['team1']
        loser = matches[0]['team2']
        
        self.game_state.report_match_winner(1, winner)
        
        # Get last place
        last_place = self.game_state.get_tournament_last_place(1)
        self.assertEqual(last_place, loser)
    
    def test_reset_tournament(self):
        """Test resetting a tournament."""
        teams = ["Alpha", "Beta"]
        self.game_state.create_tournament(1, teams, "Tournament")
        
        self.assertIsNotNone(self.game_state.get_tournament(1))
        
        # Reset
        success = self.game_state.reset_tournament(1)
        self.assertTrue(success)
        
        # Should be gone
        self.assertIsNone(self.game_state.get_tournament(1))
    
    def test_reset_nonexistent_tournament(self):
        """Test resetting a tournament that doesn't exist."""
        success = self.game_state.reset_tournament(999)
        self.assertFalse(success)
    
    def test_report_winner_invalid_team(self):
        """Test reporting winner for team not in match."""
        teams = ["Alpha", "Beta"]
        self.game_state.create_tournament(1, teams, "Tournament")
        
        # Try to report Gamma as winner (not in match)
        success = self.game_state.report_match_winner(1, "Gamma")
        self.assertFalse(success)
    
    def test_report_winner_nonexistent_tournament(self):
        """Test reporting winner for tournament that doesn't exist."""
        success = self.game_state.report_match_winner(999, "Alpha")
        self.assertFalse(success)
    
    def test_tournament_with_three_teams(self):
        """Test tournament with 3 teams (one gets bye)."""
        teams = ["Alpha", "Beta", "Gamma"]
        self.game_state.create_tournament(1, teams, "Tournament")
        
        # Round 1 should have 2 items (1 bye, 1 match)
        round1_matches = self.game_state.get_current_round_matches(1)
        self.assertEqual(len(round1_matches), 2)
        
        # One should be bye, one should be pending
        bye_count = sum(1 for m in round1_matches if m['status'] == 'bye')
        pending_count = sum(1 for m in round1_matches if m['status'] == 'pending')
        self.assertEqual(bye_count, 1)
        self.assertEqual(pending_count, 1)
        
        # Complete the pending match
        pending_match = [m for m in round1_matches if m['status'] == 'pending'][0]
        winner = pending_match['team1']
        self.game_state.report_match_winner(1, winner)
        
        # Should advance to round 2 with 2 teams (bye team + match winner)
        tournament = self.game_state.get_tournament(1)
        self.assertEqual(tournament['current_round'], 1)
        
        round2_matches = self.game_state.get_current_round_matches(1)
        self.assertEqual(len(round2_matches), 1)
    
    def test_tournament_persistence(self):
        """Test that tournament state is persisted and loaded correctly."""
        teams = ["Alpha", "Beta"]
        self.game_state.create_tournament(1, teams, "Tournament")
        
        # Complete match
        matches = self.game_state.get_current_round_matches(1)
        winner = matches[0]['team1']
        self.game_state.report_match_winner(1, winner)
        
        # Create new game state instance (load from file)
        new_game_state = GameState("test_tournament.json")
        
        # Should still be complete
        self.assertTrue(new_game_state.is_tournament_complete(1))
        last_place = new_game_state.get_tournament_last_place(1)
        self.assertIsNotNone(last_place)


if __name__ == '__main__':
    unittest.main()
