"""
Unit tests for tournament challenge broadcast functionality.
"""
import unittest
import os
import yaml
from unittest.mock import AsyncMock, MagicMock
from bot import AmazingRaceBot


class TestTournamentBroadcast(unittest.IsolatedAsyncioTestCase):
    """Test cases for tournament challenge completion broadcast."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config_file = "test_tournament_broadcast_config.yml"
        self.config = {
            'telegram': {'bot_token': 'test_token'},
            'game': {
                'name': 'Test Game',
                'max_teams': 10,
                'max_team_size': 5,
                'challenges': [
                    {
                        'id': 1,
                        'name': 'Challenge 1',
                        'description': 'First challenge',
                        'location': 'Start',
                        'type': 'riddle',
                        'verification': {
                            'method': 'answer',
                            'answer': 'test1'
                        }
                    },
                    {
                        'id': 2,
                        'name': 'Tournament Challenge',
                        'description': 'Tournament challenge',
                        'location': 'Arena',
                        'type': 'tournament',
                        'verification': {
                            'method': 'tournament'
                        },
                        'tournament': {
                            'game_name': 'Rock Paper Scissors',
                            'timeout_minutes': 5
                        }
                    },
                    {
                        'id': 3,
                        'name': 'Challenge 3',
                        'description': 'Third challenge',
                        'location': 'Finish',
                        'type': 'riddle',
                        'verification': {
                            'method': 'answer',
                            'answer': 'test3'
                        }
                    }
                ]
            },
            'admin': 999999999
        }
        
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.test_config_file):
            os.remove(self.test_config_file)
        if os.path.exists("game_state.json"):
            os.remove("game_state.json")
    
    async def test_tournament_completion_broadcasts_next_challenge(self):
        """Test that completing a tournament broadcasts the next challenge to all teams."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        
        # Disable photo verification for this test
        bot.game_state.set_photo_verification(False)
        
        # Create two teams with multiple members each
        bot.game_state.create_team("Team Alpha", 111111, "Alice")
        bot.game_state.join_team("Team Alpha", 222222, "Bob")
        
        bot.game_state.create_team("Team Beta", 333333, "Charlie")
        bot.game_state.join_team("Team Beta", 444444, "Diana")
        
        # Complete challenge 1 for both teams
        bot.game_state.complete_challenge("Team Alpha", 1, len(bot.challenges))
        bot.game_state.complete_challenge("Team Beta", 1, len(bot.challenges))
        
        # Both teams should now be on challenge 2 (tournament)
        # Mock context for sending messages
        context = MagicMock()
        context.bot.send_message = AsyncMock()
        
        # Initialize the tournament by having one team check their current challenge
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        await bot.current_challenge_command(update, context)
        
        # Tournament should now exist
        tournament = bot.game_state.get_tournament(2)
        self.assertIsNotNone(tournament)
        self.assertEqual(tournament['status'], 'active')
        
        # Reset the mock to count only tournament completion broadcasts
        context.bot.send_message.reset_mock()
        
        # Admin reports tournament winner (Team Alpha wins)
        update.effective_user.id = 999999999  # Admin
        context.args = ['2', 'Team', 'Alpha']
        
        await bot.tournamentwin_command(update, context)
        
        # Tournament should now be complete
        self.assertTrue(bot.game_state.is_tournament_complete(2))
        
        # Verify that broadcasts were sent to team members
        # Both teams should receive the next challenge broadcast
        # Team Alpha: Alice (111111) and Bob (222222)
        # Team Beta: Charlie (333333) and Diana (444444)
        # Total: 4 broadcasts
        
        calls = context.bot.send_message.call_args_list
        sent_to_ids = [call[1]['chat_id'] for call in calls]
        
        # Verify all team members received a broadcast
        self.assertIn(111111, sent_to_ids, "Alice should receive broadcast")
        self.assertIn(222222, sent_to_ids, "Bob should receive broadcast")
        self.assertIn(333333, sent_to_ids, "Charlie should receive broadcast")
        self.assertIn(444444, sent_to_ids, "Diana should receive broadcast")
        
        # Verify the broadcast contains information about the next challenge (Challenge 3)
        broadcast_messages = [call[1]['text'] for call in calls]
        
        # Count how many messages mention "Challenge #3" or "New Challenge Available"
        next_challenge_broadcasts = [msg for msg in broadcast_messages 
                                     if "Challenge #3" in msg or "New Challenge Available" in msg]
        
        # Should have at least 4 broadcasts (one per team member)
        self.assertGreaterEqual(len(next_challenge_broadcasts), 4,
                               "Should broadcast next challenge to all team members")
        
        # Verify Challenge 3 is mentioned in broadcasts
        for msg in next_challenge_broadcasts:
            self.assertIn("Challenge 3", msg, "Broadcast should mention Challenge 3")
    
    async def test_tournament_completion_with_finished_team(self):
        """Test that tournament completion does not broadcast to teams that finished all challenges."""
        # Create a config with only 2 challenges (no challenge after tournament)
        config_two_challenges = {
            'telegram': {'bot_token': 'test_token'},
            'game': {
                'name': 'Test Game',
                'max_teams': 10,
                'max_team_size': 5,
                'challenges': [
                    {
                        'id': 1,
                        'name': 'Challenge 1',
                        'description': 'First challenge',
                        'location': 'Start',
                        'type': 'riddle',
                        'verification': {
                            'method': 'answer',
                            'answer': 'test1'
                        }
                    },
                    {
                        'id': 2,
                        'name': 'Tournament Challenge',
                        'description': 'Tournament challenge',
                        'location': 'Arena',
                        'type': 'tournament',
                        'verification': {
                            'method': 'tournament'
                        },
                        'tournament': {
                            'game_name': 'Rock Paper Scissors',
                            'timeout_minutes': 5
                        }
                    }
                ]
            },
            'admin': 999999999
        }
        
        with open(self.test_config_file, 'w') as f:
            yaml.dump(config_two_challenges, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        bot.game_state.set_photo_verification(False)
        
        # Create two teams
        bot.game_state.create_team("Team Alpha", 111111, "Alice")
        bot.game_state.create_team("Team Beta", 222222, "Bob")
        
        # Complete challenge 1 for both teams
        bot.game_state.complete_challenge("Team Alpha", 1, len(bot.challenges))
        bot.game_state.complete_challenge("Team Beta", 1, len(bot.challenges))
        
        # Initialize tournament
        context = MagicMock()
        context.bot.send_message = AsyncMock()
        
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        await bot.current_challenge_command(update, context)
        
        # Reset mock
        context.bot.send_message.reset_mock()
        
        # Complete tournament
        update.effective_user.id = 999999999  # Admin
        context.args = ['2', 'Team', 'Alpha']
        
        await bot.tournamentwin_command(update, context)
        
        # Both teams should have finished all challenges
        team_alpha = bot.game_state.teams["Team Alpha"]
        team_beta = bot.game_state.teams["Team Beta"]
        
        self.assertIsNotNone(team_alpha.get('finish_time'), "Team Alpha should have finished")
        self.assertIsNotNone(team_beta.get('finish_time'), "Team Beta should have finished")
        
        # Verify no "New Challenge Available" broadcasts were sent
        # (since there are no more challenges)
        calls = context.bot.send_message.call_args_list
        broadcast_messages = [call[1]['text'] for call in calls]
        
        new_challenge_broadcasts = [msg for msg in broadcast_messages 
                                   if "New Challenge Available" in msg]
        
        # Should be 0 since both teams finished all challenges
        self.assertEqual(len(new_challenge_broadcasts), 0,
                        "Should not broadcast new challenge when teams finish all challenges")


if __name__ == '__main__':
    unittest.main()
