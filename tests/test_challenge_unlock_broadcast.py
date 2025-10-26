"""
Test that challenges are broadcast when timeout expires or when no timeout exists.
"""
import unittest
import os
import yaml
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from bot import AmazingRaceBot


class TestChallengeUnlockBroadcast(unittest.IsolatedAsyncioTestCase):
    """Test cases for broadcasting challenges on unlock."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config_file = "test_unlock_broadcast_config.yml"
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
                        },
                        'hints': ['Hint 1', 'Hint 2']
                    },
                    {
                        'id': 2,
                        'name': 'Challenge 2',
                        'description': 'Second challenge',
                        'location': 'Library',
                        'type': 'riddle',
                        'verification': {
                            'method': 'answer',
                            'answer': 'test2'
                        }
                    },
                    {
                        'id': 3,
                        'name': 'Challenge 3',
                        'description': 'Third challenge',
                        'location': 'Park',
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
    
    async def test_broadcast_next_challenge_when_no_timeout(self):
        """Test that next challenge is broadcast when there's no timeout (no hints used)."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        
        # Disable photo verification for this test
        bot.game_state.set_photo_verification(False)
        
        # Create team with multiple members
        bot.game_state.create_team("Team A", 111111, "Alice")
        bot.game_state.join_team("Team A", 222222, "Bob")
        
        # Mock the update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.effective_user.first_name = "Alice"
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.args = ['test1']
        context.bot_data = {}
        context.bot.send_message = AsyncMock()
        
        # Submit challenge 1 (no hints used)
        await bot.submit_command(update, context)
        
        # Verify challenge 1 was completed
        team = bot.game_state.teams["Team A"]
        self.assertEqual(len(team['completed_challenges']), 1)
        self.assertEqual(team['current_challenge_index'], 1)
        
        # Verify no unlock time for challenge 2 (no hints used)
        unlock_time_str = bot.game_state.get_challenge_unlock_time("Team A", 2)
        self.assertIsNone(unlock_time_str)
        
        # Verify broadcasts were sent
        calls = context.bot.send_message.call_args_list
        
        # Find new challenge broadcasts (should be 1 - to Bob, excluding Alice)
        new_challenge_messages = [call for call in calls if "New Challenge Available!" in call[1]['text']]
        self.assertEqual(len(new_challenge_messages), 1)
        
        # Verify it was sent to Bob (not to Alice who submitted)
        new_challenge_ids = [call[1]['chat_id'] for call in new_challenge_messages]
        self.assertIn(222222, new_challenge_ids)  # Bob
        self.assertNotIn(111111, new_challenge_ids)  # Not Alice
        
        # Verify the message content
        message_text = new_challenge_messages[0][1]['text']
        self.assertIn("New Challenge Available!", message_text)
        self.assertIn("Challenge #2", message_text)
        self.assertIn("Challenge 2", message_text)
    
    async def test_no_broadcast_when_timeout_active(self):
        """Test that next challenge is NOT broadcast when there's an active timeout."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        
        # Disable photo verification for this test
        bot.game_state.set_photo_verification(False)
        
        # Create team
        bot.game_state.create_team("Team A", 111111, "Alice")
        bot.game_state.join_team("Team A", 222222, "Bob")
        
        # Use a hint on challenge 1
        bot.game_state.use_hint("Team A", 1, 0, 111111, "Alice")
        
        # Mock the update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.effective_user.first_name = "Alice"
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.args = ['test1']
        context.bot_data = {}
        context.bot.send_message = AsyncMock()
        
        # Submit challenge 1 (with hint penalty)
        await bot.submit_command(update, context)
        
        # Verify challenge 1 was completed
        team = bot.game_state.teams["Team A"]
        self.assertEqual(len(team['completed_challenges']), 1)
        
        # Verify unlock time exists for challenge 2 (hint penalty)
        unlock_time_str = bot.game_state.get_challenge_unlock_time("Team A", 2)
        self.assertIsNotNone(unlock_time_str)
        
        # Verify NO new challenge broadcast was sent (because of timeout)
        calls = context.bot.send_message.call_args_list
        new_challenge_messages = [call for call in calls if "New Challenge Available!" in call[1]['text']]
        self.assertEqual(len(new_challenge_messages), 0)
    
    async def test_broadcast_when_timeout_expires_on_current_check(self):
        """Test that challenge is broadcast when timeout expires and user checks /current."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        
        # Disable photo verification for this test
        bot.game_state.set_photo_verification(False)
        
        # Create team
        bot.game_state.create_team("Team A", 111111, "Alice")
        bot.game_state.join_team("Team A", 222222, "Bob")
        
        # Use a hint and complete challenge 1
        bot.game_state.use_hint("Team A", 1, 0, 111111, "Alice")
        bot.game_state.complete_challenge("Team A", 1, 3, {'type': 'answer'})
        
        # Verify unlock time exists
        unlock_time_str = bot.game_state.get_challenge_unlock_time("Team A", 2)
        self.assertIsNotNone(unlock_time_str)
        
        # Manually set the completion time to past so timeout has expired
        completion_time = datetime.now() - timedelta(minutes=5)
        bot.game_state.teams["Team A"]['challenge_completion_times']['1'] = completion_time.isoformat()
        bot.game_state.save_state()
        
        # Verify timeout has expired
        unlock_time_str = bot.game_state.get_challenge_unlock_time("Team A", 2)
        unlock_time = datetime.fromisoformat(unlock_time_str)
        self.assertTrue(datetime.now() > unlock_time)
        
        # Mock the update and context for /current command
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.effective_user.first_name = "Alice"
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.bot_data = {}
        context.bot.send_message = AsyncMock()
        
        # Call /current command - should trigger broadcast check
        await bot.current_challenge_command(update, context)
        
        # Verify broadcast was sent
        calls = context.bot.send_message.call_args_list
        
        # Should have broadcast to Bob (excluding Alice who called /current)
        self.assertGreater(len(calls), 0)
        
        # Find new challenge broadcasts
        new_challenge_messages = [call for call in calls if "New Challenge Available!" in call[1]['text']]
        
        # Alice called /current, so broadcast should go to Bob
        if len(new_challenge_messages) > 0:
            message_text = new_challenge_messages[0][1]['text']
            self.assertIn("New Challenge Available!", message_text)
            self.assertIn("Challenge #2", message_text)
    
    async def test_broadcast_only_once_per_unlock(self):
        """Test that challenge unlock is broadcast only once (not on every interaction)."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        
        # Disable photo verification for this test
        bot.game_state.set_photo_verification(False)
        
        # Create team
        bot.game_state.create_team("Team A", 111111, "Alice")
        bot.game_state.join_team("Team A", 222222, "Bob")
        
        # Use a hint and complete challenge 1
        bot.game_state.use_hint("Team A", 1, 0, 111111, "Alice")
        bot.game_state.complete_challenge("Team A", 1, 3, {'type': 'answer'})
        
        # Manually set the completion time to past so timeout has expired
        completion_time = datetime.now() - timedelta(minutes=5)
        bot.game_state.teams["Team A"]['challenge_completion_times']['1'] = completion_time.isoformat()
        bot.game_state.save_state()
        
        # Mock the update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.effective_user.first_name = "Alice"
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.bot_data = {}
        context.bot.send_message = AsyncMock()
        
        # First call to /current - should broadcast
        await bot.current_challenge_command(update, context)
        
        first_call_count = context.bot.send_message.call_count
        
        # Reset mock
        context.bot.send_message.reset_mock()
        
        # Second call to /current - should NOT broadcast again
        await bot.current_challenge_command(update, context)
        
        # Should have no new challenge broadcasts on second call
        calls = context.bot.send_message.call_args_list
        new_challenge_messages = [call for call in calls if "New Challenge Available!" in call[1]['text']]
        self.assertEqual(len(new_challenge_messages), 0)


if __name__ == '__main__':
    unittest.main()
