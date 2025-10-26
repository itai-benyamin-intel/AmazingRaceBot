"""
Unit tests for the custom success message feature.
"""
import unittest
import os
import yaml
from unittest.mock import AsyncMock, MagicMock, patch, call
from bot import AmazingRaceBot


class TestSuccessMessage(unittest.IsolatedAsyncioTestCase):
    """Test cases for custom success messages after challenge completion."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config_file = "test_success_message_config.yml"
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
                        },
                        'success_message': 'Great job! Proceed to the next checkpoint.'
                    },
                    {
                        'id': 2,
                        'description': 'Second challenge',
                        'location': 'Library',
                        'type': 'trivia',
                        'verification': {
                            'method': 'answer',
                            'answer': 'test2'
                        },
                        'success_message': 'Excellent work! You are making great progress.'
                    },
                    {
                        'id': 3,
                        'description': 'Third challenge with no custom message',
                        'location': 'Park',
                        'type': 'riddle',
                        'verification': {
                            'method': 'answer',
                            'answer': 'test3'
                        }
                        # No success_message - should work normally
                    }
                ]
            },
            'admin': 123456789
        }
        
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.test_config_file):
            os.remove(self.test_config_file)
        if os.path.exists("game_state.json"):
            os.remove("game_state.json")
    
    async def test_success_message_sent_on_text_answer(self):
        """Test that custom success message is sent after correct text answer."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        
        # Create team and user
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
        context.bot = MagicMock()
        context.bot.send_message = AsyncMock()
        
        # Call submit_command
        await bot.submit_command(update, context)
        
        # Verify challenge was completed
        team = bot.game_state.teams["Team A"]
        self.assertEqual(len(team['completed_challenges']), 1)
        self.assertIn(1, team['completed_challenges'])
        
        # Verify that reply_text was called twice: once for completion, once for success_message
        self.assertEqual(update.message.reply_text.call_count, 2)
        
        # First call should be the completion message
        first_call = update.message.reply_text.call_args_list[0]
        self.assertIn("Correct!", first_call[0][0])
        
        # Second call should be the custom success message
        second_call = update.message.reply_text.call_args_list[1]
        self.assertEqual("Great job! Proceed to the next checkpoint.", second_call[0][0])
        
    async def test_no_success_message_when_not_configured(self):
        """Test that no extra message is sent when success_message is not configured."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        
        # Disable photo verification for this test
        bot.game_state.set_photo_verification(False)
        
        # Create team and user
        bot.game_state.create_team("Team A", 111111, "Alice")
        
        # Complete first two challenges to get to challenge 3 (which has no success_message)
        bot.game_state.complete_challenge("Team A", 1, 3)
        bot.game_state.complete_challenge("Team A", 2, 3)
        
        # Mock the update and context for challenge 3
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.effective_user.first_name = "Alice"
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.args = ['test3']
        context.bot_data = {}
        context.bot = MagicMock()
        context.bot.send_message = AsyncMock()
        
        # Call submit_command for challenge 3
        await bot.submit_command(update, context)
        
        # Verify challenge was completed
        team = bot.game_state.teams["Team A"]
        self.assertEqual(len(team['completed_challenges']), 3)
        
        # Verify that reply_text was called only once (no success_message)
        self.assertEqual(update.message.reply_text.call_count, 1)
        
        # The call should be the completion message
        call_args = update.message.reply_text.call_args_list[0]
        self.assertIn("Correct!", call_args[0][0])
    
    async def test_success_message_with_markdown(self):
        """Test that success message supports markdown formatting."""
        # Add a challenge with markdown in success_message
        self.config['game']['challenges'].append({
            'id': 4,
            'description': 'Fourth challenge',
            'location': 'Museum',
            'type': 'trivia',
            'verification': {
                'method': 'answer',
                'answer': 'test4'
            },
            'success_message': '*Congratulations!* You have completed the _historical_ challenge. 🎉'
        })
        
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        
        # Disable photo verification for this test
        bot.game_state.set_photo_verification(False)
        
        # Create team and complete previous challenges
        bot.game_state.create_team("Team A", 111111, "Alice")
        bot.game_state.complete_challenge("Team A", 1, 4)
        bot.game_state.complete_challenge("Team A", 2, 4)
        bot.game_state.complete_challenge("Team A", 3, 4)
        
        # Mock the update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.effective_user.first_name = "Alice"
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.args = ['test4']
        context.bot_data = {}
        context.bot = MagicMock()
        context.bot.send_message = AsyncMock()
        
        # Call submit_command
        await bot.submit_command(update, context)
        
        # Verify that reply_text was called with parse_mode='Markdown'
        second_call = update.message.reply_text.call_args_list[1]
        self.assertEqual(second_call[1]['parse_mode'], 'Markdown')
        self.assertIn('*Congratulations!*', second_call[0][0])


class TestSuccessMessagePhotoChallenge(unittest.IsolatedAsyncioTestCase):
    """Test cases for custom success messages with photo challenges."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config_file = "test_photo_success_config.yml"
        self.config = {
            'telegram': {'bot_token': 'test_token'},
            'game': {
                'max_teams': 10,
                'max_team_size': 5,
                'challenges': [
                    {
                        'id': 1,
                        'description': 'Take a team photo',
                        'location': 'Start',
                        'type': 'photo',
                        'verification': {
                            'method': 'photo'
                        },
                        'success_message': '📷 Amazing photo! On to the next challenge!'
                    }
                ]
            },
            'admin': 123456789
        }
        
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.test_config_file):
            os.remove(self.test_config_file)
        if os.path.exists("game_state.json"):
            os.remove("game_state.json")
    
    async def test_success_message_sent_on_photo_approval(self):
        """Test that custom success message is sent when admin approves photo."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        
        # Create team and user
        bot.game_state.create_team("Team A", 111111, "Alice")
        
        # Add a pending photo submission
        submission_id = bot.game_state.add_pending_photo_submission(
            "Team A", 1, "photo_file_id", 111111, "Alice"
        )
        
        # Mock the update and context for photo approval
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 123456789  # Admin
        update.callback_query = MagicMock()
        update.callback_query.data = f"approve_{submission_id}"
        update.callback_query.answer = AsyncMock()
        update.callback_query.message = MagicMock()
        update.callback_query.message.caption = "Photo Submission"
        update.callback_query.edit_message_caption = AsyncMock()
        
        context = MagicMock()
        context.bot = MagicMock()
        context.bot.send_message = AsyncMock()
        
        # Call photo approval handler
        await bot.photo_approval_callback_handler(update, context)
        
        # Verify that send_message was called twice for the user:
        # once for approval notification, once for success_message
        user_messages = [
            call_obj for call_obj in context.bot.send_message.call_args_list
            if call_obj[1].get('chat_id') == 111111
        ]
        
        self.assertEqual(len(user_messages), 2)
        
        # First message should be the approval notification
        first_msg = user_messages[0][1]['text']
        self.assertIn("Photo Approved!", first_msg)
        
        # Second message should be the custom success message
        second_msg = user_messages[1][1]['text']
        self.assertEqual("📷 Amazing photo! On to the next challenge!", second_msg)


if __name__ == '__main__':
    unittest.main()
