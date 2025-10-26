"""
Unit tests for challenge completion broadcast functionality.
"""
import unittest
import os
import yaml
from unittest.mock import AsyncMock, MagicMock, patch, call
from bot import AmazingRaceBot


class TestChallengeBroadcast(unittest.IsolatedAsyncioTestCase):
    """Test cases for challenge completion broadcast."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config_file = "test_broadcast_config.yml"
        self.config = {
            'telegram': {'bot_token': 'test_token'},
            'game': {
                'max_teams': 10,
                'max_team_size': 5,
                'challenges': [
                    {
                        'id': 1,
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
                        'description': 'Second challenge',
                        'location': 'Library',
                        'type': 'photo',
                        'verification': {
                            'method': 'photo'
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
    
    async def test_broadcast_to_team_members_on_answer_challenge(self):
        """Test that challenge completion is broadcast to all team members for answer challenge."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        
        # Disable photo verification for this test
        bot.game_state.set_photo_verification(False)
        
        # Create team with multiple members
        bot.game_state.create_team("Team A", 111111, "Alice")
        bot.game_state.join_team("Team A", 222222, "Bob")
        bot.game_state.join_team("Team A", 333333, "Charlie")
        
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
        
        # Submit challenge
        await bot.submit_command(update, context)
        
        # Verify challenge was completed
        team = bot.game_state.teams["Team A"]
        self.assertEqual(len(team['completed_challenges']), 1)
        
        # Verify broadcasts were sent
        # Should have been called 5 times:
        # - Completion broadcast: Bob (222222), Charlie (333333), Admin (999999999)
        # - Next challenge broadcast (no timeout): Bob (222222), Charlie (333333)
        # Alice (111111) is the submitter so they don't get the next challenge broadcast
        self.assertEqual(context.bot.send_message.call_count, 5)
        
        # Get all call arguments
        calls = context.bot.send_message.call_args_list
        sent_to_ids = [call[1]['chat_id'] for call in calls]
        
        # Count messages per recipient
        bob_messages = sent_to_ids.count(222222)
        charlie_messages = sent_to_ids.count(333333)
        admin_messages = sent_to_ids.count(999999999)
        
        # Verify Bob and Charlie got 2 messages each (completion + next challenge)
        self.assertEqual(bob_messages, 2)  # Bob: completion + next challenge
        self.assertEqual(charlie_messages, 2)  # Charlie: completion + next challenge
        # Admin got 1 message (completion only, not next challenge)
        self.assertEqual(admin_messages, 1)  # Admin: completion only
        
        # Verify Alice (submitter) did NOT receive any broadcasts
        self.assertNotIn(111111, sent_to_ids)
        
        # Verify the message content includes both completion and new challenge
        completion_messages = [call[1]['text'] for call in calls if "Challenge Completed!" in call[1]['text']]
        new_challenge_messages = [call[1]['text'] for call in calls if "New Challenge Available!" in call[1]['text']]
        
        # Should have 3 completion messages (Bob, Charlie, Admin)
        self.assertEqual(len(completion_messages), 3)
        # Should have 2 new challenge messages (Bob, Charlie - excluding Alice)
        self.assertEqual(len(new_challenge_messages), 2)
        
        # Verify completion message content
        for message_text in completion_messages:
            self.assertIn("Team A", message_text)
            self.assertIn("Challenge #1", message_text)
            self.assertIn("Alice", message_text)
            self.assertIn("1/2 challenges", message_text)
        
        # Verify new challenge message content
        for message_text in new_challenge_messages:
            self.assertIn("New Challenge Available!", message_text)
            self.assertIn("Challenge #2", message_text)
    
    async def test_broadcast_includes_finish_message(self):
        """Test that broadcast includes finish message when team completes all challenges."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        
        # Create team with two members
        bot.game_state.create_team("Team A", 111111, "Alice")
        bot.game_state.join_team("Team A", 222222, "Bob")
        
        # Complete first challenge manually
        bot.game_state.complete_challenge("Team A", 1, 2, {'type': 'answer'})
        
        # Mock the update and context for photo submission
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.effective_user.first_name = "Alice"
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        update.message.photo = [MagicMock()]
        photo = update.message.photo[-1]
        photo.file_id = "test_photo_id"
        
        context = MagicMock()
        context.bot_data = {
            'pending_submissions': {
                111111: {
                    'team_name': 'Team A',
                    'challenge_id': 2
                }
            }
        }
        context.bot.send_message = AsyncMock()
        context.bot.send_photo = AsyncMock()
        
        # Submit photo for second challenge (now pending, not auto-complete)
        await bot.photo_handler(update, context)
        
        # Verify team has NOT finished yet (photo is pending approval)
        team = bot.game_state.teams["Team A"]
        self.assertEqual(len(team['completed_challenges']), 1)
        self.assertIsNone(team.get('finish_time'))
        
        # Verify photo was sent to admin with buttons (not broadcast yet)
        self.assertEqual(context.bot.send_photo.call_count, 1)
        photo_call = context.bot.send_photo.call_args[1]
        self.assertEqual(photo_call['chat_id'], 999999999)
        self.assertIn("Challenge #", photo_call['caption'])
        
        # Get the submission ID from pending submissions
        pending = bot.game_state.get_pending_photo_submissions()
        self.assertEqual(len(pending), 1)
        submission_id = list(pending.keys())[0]
        
        # Now simulate admin approval
        bot.game_state.approve_photo_submission(submission_id, 2)
        
        # Verify team finished after approval
        team = bot.game_state.teams["Team A"]
        self.assertEqual(len(team['completed_challenges']), 2)
        self.assertIsNotNone(team['finish_time'])
    
    async def test_no_broadcast_to_submitter(self):
        """Test that the person who submitted doesn't receive the broadcast."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        
        # Create team with one member
        bot.game_state.create_team("Team A", 111111, "Alice")
        
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
        
        # Submit challenge
        await bot.submit_command(update, context)
        
        # Verify challenge was completed
        team = bot.game_state.teams["Team A"]
        self.assertEqual(len(team['completed_challenges']), 1)
        
        # Verify broadcast was sent only to admin (not to Alice who is the only team member)
        self.assertEqual(context.bot.send_message.call_count, 1)
        
        # Verify it was sent to admin
        call_args = context.bot.send_message.call_args[1]
        self.assertEqual(call_args['chat_id'], 999999999)
    
    async def test_broadcast_on_photo_challenge(self):
        """Test that broadcast works for photo challenges."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        
        # Create team with two members and complete first challenge
        bot.game_state.create_team("Team A", 111111, "Alice")
        bot.game_state.join_team("Team A", 222222, "Bob")
        bot.game_state.complete_challenge("Team A", 1, 2, {'type': 'answer'})
        
        # Mock the update and context for photo submission
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 222222  # Bob submits
        update.effective_user.first_name = "Bob"
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        update.message.photo = [MagicMock()]
        photo = update.message.photo[-1]
        photo.file_id = "test_photo_id"
        
        context = MagicMock()
        context.bot_data = {
            'pending_submissions': {
                222222: {
                    'team_name': 'Team A',
                    'challenge_id': 2
                }
            }
        }
        context.bot.send_message = AsyncMock()
        context.bot.send_photo = AsyncMock()
        
        # Submit photo (now pending, not auto-complete)
        await bot.photo_handler(update, context)
        
        # Verify photo was sent to admin with buttons (no broadcast yet)
        self.assertEqual(context.bot.send_photo.call_count, 1)
        photo_call = context.bot.send_photo.call_args[1]
        self.assertEqual(photo_call['chat_id'], 999999999)
        self.assertIn("Challenge #", photo_call['caption'])
        
        # Verify challenge was NOT completed yet
        team = bot.game_state.teams["Team A"]
        self.assertEqual(len(team['completed_challenges']), 1)
        
        # No broadcast should have been sent yet
        self.assertEqual(context.bot.send_message.call_count, 0)


if __name__ == '__main__':
    unittest.main()
