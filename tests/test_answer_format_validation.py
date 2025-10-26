"""
Unit tests for answer format validation.

Tests that the bot correctly detects and responds when:
- A photo is sent when text is expected
- Text is sent when a photo is expected
"""
import unittest
import os
import yaml
from unittest.mock import AsyncMock, MagicMock, patch
from bot import AmazingRaceBot


class TestAnswerFormatValidation(unittest.IsolatedAsyncioTestCase):
    """Test cases for answer format validation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config_file = "test_format_validation_config.yml"
        self.config = {
            'telegram': {'bot_token': 'test_token'},
            'game': {
                'name': 'Test Game',
                'max_teams': 10,
                'max_team_size': 5,
                'challenges': [
                    {
                        'id': 1,
                        'name': 'Text Challenge',
                        'description': 'A riddle',
                        'location': 'Start',
                        'type': 'riddle',
                        'verification': {
                            'method': 'answer',
                            'answer': 'keyboard'
                        }
                    },
                    {
                        'id': 2,
                        'name': 'Photo Challenge',
                        'description': 'Take a photo',
                        'location': 'Park',
                        'type': 'photo',
                        'verification': {
                            'method': 'photo'
                        }
                    },
                    {
                        'id': 3,
                        'name': 'Another Text Challenge',
                        'description': 'Answer a question',
                        'location': 'Library',
                        'type': 'trivia',
                        'verification': {
                            'method': 'answer',
                            'answer': 'python'
                        }
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
    
    async def test_photo_sent_when_text_expected(self):
        """Test that sending a photo when text is expected shows an error message."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        
        # Create team and user
        bot.game_state.create_team("Team A", 111111, "Alice")
        
        # Mock the update and context for photo message
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.effective_user.first_name = "Alice"
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        update.message.photo = [MagicMock()]  # Simulate a photo
        update.message.photo[-1].file_id = "test_photo_id"
        
        context = MagicMock()
        context.bot_data = {}
        
        # Call photo_handler when on a text challenge
        await bot.photo_handler(update, context)
        
        # Verify that an error message was sent
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args.kwargs.get('text', '')
        
        # Check that the message indicates text is required
        self.assertIn('text answer is required', message.lower())
        self.assertIn('Text Challenge', message)
    
    async def test_text_sent_when_photo_expected(self):
        """Test that sending text when photo is expected shows an error message."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        
        # Create team and complete first challenge to get to photo challenge
        bot.game_state.create_team("Team A", 111111, "Alice")
        total_challenges = len(self.config['game']['challenges'])
        bot.game_state.complete_challenge("Team A", 1, total_challenges, {'type': 'answer', 'answer': 'keyboard'})
        
        # Mock the update and context for text message
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.effective_user.first_name = "Alice"
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        update.message.text = "some random text"
        
        context = MagicMock()
        context.user_data = {}
        context.args = None
        
        # Call unrecognized_message_handler when on a photo challenge
        await bot.unrecognized_message_handler(update, context)
        
        # Verify that an error message was sent
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args.kwargs.get('text', '')
        
        # Check that the message indicates photo is required
        self.assertIn('photo', message.lower())
        self.assertIn('Photo Challenge', message)
    
    async def test_correct_format_photo_accepted(self):
        """Test that sending a photo when photo is expected works correctly."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        
        # Create team and complete first challenge to get to photo challenge
        bot.game_state.create_team("Team A", 111111, "Alice")
        total_challenges = len(self.config['game']['challenges'])
        bot.game_state.complete_challenge("Team A", 1, total_challenges, {'type': 'answer', 'answer': 'keyboard'})
        
        # Mock the update and context for photo message
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.effective_user.first_name = "Alice"
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        update.message.photo = [MagicMock()]  # Simulate a photo
        update.message.photo[-1].file_id = "test_photo_id"
        
        context = MagicMock()
        context.bot_data = {}
        context.bot = MagicMock()
        context.bot.send_photo = AsyncMock()
        
        # Call photo_handler when on a photo challenge
        await bot.photo_handler(update, context)
        
        # Verify that a photo submission was sent to admin (pending approval)
        # Check that reply_text was called (confirming photo was accepted)
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args.kwargs.get('text', '')
        
        # Should indicate photo was submitted for review
        self.assertIn('photo', message.lower())
        self.assertIn('submitted', message.lower())
    
    async def test_correct_format_text_accepted(self):
        """Test that sending text when text is expected works correctly."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        
        # Create team
        bot.game_state.create_team("Team A", 111111, "Alice")
        
        # Mock the update and context for text message
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.effective_user.first_name = "Alice"
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        update.message.text = "keyboard"
        
        context = MagicMock()
        context.user_data = {}
        context.args = None
        context.bot_data = {}
        context.bot = MagicMock()
        context.bot.send_message = AsyncMock()
        
        # Call unrecognized_message_handler when on a text challenge
        await bot.unrecognized_message_handler(update, context)
        
        # Verify that the challenge was completed
        team = bot.game_state.teams["Team A"]
        self.assertEqual(len(team['completed_challenges']), 1)
        self.assertIn(1, team['completed_challenges'])
    
    async def test_get_expected_answer_format_photo(self):
        """Test get_expected_answer_format returns 'photo' for photo challenges."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        
        photo_challenge = self.config['game']['challenges'][1]  # Photo Challenge
        format_type = bot.get_expected_answer_format(photo_challenge)
        
        self.assertEqual(format_type, 'photo')
    
    async def test_get_expected_answer_format_text(self):
        """Test get_expected_answer_format returns 'text' for answer challenges."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        
        text_challenge = self.config['game']['challenges'][0]  # Text Challenge
        format_type = bot.get_expected_answer_format(text_challenge)
        
        self.assertEqual(format_type, 'text')
    
    async def test_get_format_mismatch_message_photo(self):
        """Test format mismatch message for photo requirement."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        
        photo_challenge = self.config['game']['challenges'][1]  # Photo Challenge
        message = bot.get_format_mismatch_message('photo', photo_challenge)
        
        self.assertIn('Photo Required', message)
        self.assertIn('Photo Challenge', message)
        self.assertIn('upload a photo', message.lower())
    
    async def test_get_format_mismatch_message_text(self):
        """Test format mismatch message for text requirement."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        
        text_challenge = self.config['game']['challenges'][0]  # Text Challenge
        message = bot.get_format_mismatch_message('text', text_challenge)
        
        self.assertIn('Text Answer Required', message)
        self.assertIn('Text Challenge', message)
        self.assertIn('text', message.lower())


if __name__ == '__main__':
    unittest.main()
