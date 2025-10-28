"""
Unit tests for image support in challenges and hints.
"""
import unittest
import os
import yaml
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from bot import AmazingRaceBot
from game_state import GameState


class TestImageSupport(unittest.IsolatedAsyncioTestCase):
    """Test cases for image support functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config_file = "test_image_config.yml"
        self.test_state_file = "test_image_state.json"
        
        # Create test configuration with image support
        self.config = {
            'telegram': {'bot_token': 'test_token'},
            'game': {
                'name': 'Test Game',
                'max_teams': 10,
                'max_team_size': 5,
                'challenges': [
                    {
                        'id': 1,
                        'name': 'Image Challenge',
                        'description': 'What landmark is shown?',
                        'location': 'Anywhere',
                        'type': 'riddle',
                        'verification': {'method': 'answer', 'answer': 'eiffel tower'},
                        'image_url': 'https://example.com/landmark.jpg',
                        'hints': ['It is in France', 'Built in 1889'],
                        'hint_images': {
                            0: 'images/test_hint.png',
                            1: 'https://example.com/hint2.jpg'
                        }
                    },
                    {
                        'id': 2,
                        'name': 'Local Image Challenge',
                        'description': 'Identify this building',
                        'location': 'Campus',
                        'type': 'riddle',
                        'verification': {'method': 'answer', 'answer': 'library'},
                        'image_path': 'images/test_challenge.png'
                    }
                ]
            },
            'admin': 100
        }
        
        # Write config to file
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        # Initialize bot
        self.bot = AmazingRaceBot(self.test_config_file)
        
        # Override game state file
        self.bot.game_state.state_file = self.test_state_file
    
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.test_config_file):
            os.remove(self.test_config_file)
        if os.path.exists(self.test_state_file):
            os.remove(self.test_state_file)
    
    def test_validate_image_url_https(self):
        """Test that HTTPS URLs are accepted."""
        url = "https://example.com/image.jpg"
        self.assertTrue(self.bot.validate_image_url(url))
    
    def test_validate_image_url_http_rejected(self):
        """Test that HTTP URLs are rejected."""
        url = "http://example.com/image.jpg"
        self.assertFalse(self.bot.validate_image_url(url))
    
    def test_validate_image_url_trusted_domain(self):
        """Test that trusted domains are accepted even without extension."""
        url = "https://i.imgur.com/abc123"
        self.assertTrue(self.bot.validate_image_url(url))
    
    def test_validate_image_path_valid(self):
        """Test that valid local paths are accepted."""
        path = "images/test_challenge.png"
        result = self.bot.validate_image_path(path)
        self.assertIsNotNone(result)
        self.assertTrue(os.path.isabs(result))
    
    def test_validate_image_path_directory_traversal(self):
        """Test that directory traversal is rejected."""
        path = "../../../etc/passwd"
        result = self.bot.validate_image_path(path)
        self.assertIsNone(result)
    
    def test_validate_image_path_absolute_rejected(self):
        """Test that absolute paths are rejected."""
        path = "/tmp/image.png"
        result = self.bot.validate_image_path(path)
        self.assertIsNone(result)
    
    def test_validate_image_path_nonexistent(self):
        """Test that non-existent files are rejected."""
        path = "images/nonexistent.png"
        result = self.bot.validate_image_path(path)
        self.assertIsNone(result)
    
    def test_validate_image_path_wrong_extension(self):
        """Test that files with wrong extensions are rejected."""
        # Create a test file with wrong extension
        test_file = "images/test.txt"
        os.makedirs(os.path.dirname(os.path.join(os.path.dirname(__file__), '..', test_file)), exist_ok=True)
        with open(os.path.join(os.path.dirname(__file__), '..', test_file), 'w') as f:
            f.write("test")
        
        result = self.bot.validate_image_path(test_file)
        self.assertIsNone(result)
        
        # Clean up
        os.remove(os.path.join(os.path.dirname(__file__), '..', test_file))
    
    async def test_send_image_url(self):
        """Test sending image from URL."""
        # Mock context
        context = MagicMock()
        context.bot.send_photo = AsyncMock()
        
        chat_id = 12345
        image_url = "https://example.com/test.jpg"
        caption = "Test caption"
        
        result = await self.bot.send_image(
            context=context,
            chat_id=chat_id,
            image_url=image_url,
            caption=caption
        )
        
        self.assertTrue(result)
        context.bot.send_photo.assert_called_once_with(
            chat_id=chat_id,
            photo=image_url,
            caption=caption,
            parse_mode='Markdown'
        )
    
    async def test_send_image_local_path(self):
        """Test sending image from local path."""
        # Mock context
        context = MagicMock()
        context.bot.send_photo = AsyncMock()
        
        chat_id = 12345
        image_path = "images/test_challenge.png"
        caption = "Test caption"
        
        result = await self.bot.send_image(
            context=context,
            chat_id=chat_id,
            image_path=image_path,
            caption=caption
        )
        
        self.assertTrue(result)
        context.bot.send_photo.assert_called_once()
        
        # Verify the photo parameter is a file-like object
        call_kwargs = context.bot.send_photo.call_args[1]
        self.assertEqual(call_kwargs['chat_id'], chat_id)
        self.assertEqual(call_kwargs['caption'], caption)
    
    async def test_send_image_invalid_url(self):
        """Test that invalid URLs are rejected."""
        context = MagicMock()
        context.bot.send_photo = AsyncMock()
        
        result = await self.bot.send_image(
            context=context,
            chat_id=12345,
            image_url="http://example.com/test.jpg"  # HTTP not HTTPS
        )
        
        self.assertFalse(result)
        context.bot.send_photo.assert_not_called()
    
    async def test_send_image_invalid_path(self):
        """Test that invalid paths are rejected."""
        context = MagicMock()
        context.bot.send_photo = AsyncMock()
        
        result = await self.bot.send_image(
            context=context,
            chat_id=12345,
            image_path="../../../etc/passwd"  # Directory traversal
        )
        
        self.assertFalse(result)
        context.bot.send_photo.assert_not_called()
    
    async def test_broadcast_challenge_with_image_url(self):
        """Test that broadcast_current_challenge sends image for challenge with image_url."""
        # Set up game state
        self.bot.game_state.start_game()
        self.bot.game_state.create_team('Team1', 1, 'User1')
        
        # Mock context
        context = MagicMock()
        context.bot.send_message = AsyncMock()
        context.bot.send_photo = AsyncMock()
        
        # Broadcast challenge
        await self.bot.broadcast_current_challenge(context, 'Team1')
        
        # Verify image was sent
        context.bot.send_photo.assert_called()
        
        # Verify text message was also sent
        context.bot.send_message.assert_called()
    
    async def test_broadcast_challenge_with_image_path(self):
        """Test that broadcast_current_challenge sends image for challenge with image_path."""
        # Set up game state - advance to challenge 2
        self.bot.game_state.start_game()
        self.bot.game_state.create_team('Team1', 1, 'User1')
        self.bot.game_state.complete_challenge('Team1', 1, len(self.bot.challenges))
        
        # Disable photo verification to ensure challenge is broadcast
        self.bot.game_state.photo_verification_enabled = False
        
        # Mock context
        context = MagicMock()
        context.bot.send_message = AsyncMock()
        context.bot.send_photo = AsyncMock()
        
        # Broadcast challenge
        await self.bot.broadcast_current_challenge(context, 'Team1')
        
        # Verify image was sent
        context.bot.send_photo.assert_called()
        
        # Verify text message was also sent
        context.bot.send_message.assert_called()
    
    async def test_current_command_sends_image(self):
        """Test that /current command sends image with challenge."""
        # Set up game state
        self.bot.game_state.start_game()
        self.bot.game_state.create_team('Team1', 1, 'User1')
        
        # Mock update and context
        update = MagicMock()
        update.effective_user.id = 1
        update.effective_chat.id = 1
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.bot.send_photo = AsyncMock()
        
        # Execute command
        await self.bot.current_challenge_command(update, context)
        
        # Verify image was sent
        context.bot.send_photo.assert_called()
        
        # Verify text message was also sent
        update.message.reply_text.assert_called()
    
    async def test_hint_with_image_url(self):
        """Test that hint with image URL sends the image."""
        # Set up game state
        self.bot.game_state.start_game()
        self.bot.game_state.create_team('Team1', 1, 'User1')
        
        # Mock update and context for hint confirmation callback
        update = MagicMock()
        update.callback_query.answer = AsyncMock()
        update.callback_query.data = "hint_yes_1_1"  # Challenge 1, hint index 1
        update.callback_query.edit_message_text = AsyncMock()
        update.effective_user.id = 1
        update.effective_user.first_name = 'User1'
        
        context = MagicMock()
        context.bot.send_message = AsyncMock()
        context.bot.send_photo = AsyncMock()
        
        # Execute hint callback
        await self.bot.hint_callback_handler(update, context)
        
        # Verify image was sent (hint index 1 has image_url)
        context.bot.send_photo.assert_called()
    
    async def test_hint_with_image_path(self):
        """Test that hint with image path sends the image."""
        # Set up game state
        self.bot.game_state.start_game()
        self.bot.game_state.create_team('Team1', 1, 'User1')
        
        # Mock update and context for hint confirmation callback
        update = MagicMock()
        update.callback_query.answer = AsyncMock()
        update.callback_query.data = "hint_yes_1_0"  # Challenge 1, hint index 0
        update.callback_query.edit_message_text = AsyncMock()
        update.effective_user.id = 1
        update.effective_user.first_name = 'User1'
        
        context = MagicMock()
        context.bot.send_message = AsyncMock()
        context.bot.send_photo = AsyncMock()
        
        # Execute hint callback
        await self.bot.hint_callback_handler(update, context)
        
        # Verify image was sent (hint index 0 has image_path)
        context.bot.send_photo.assert_called()


if __name__ == '__main__':
    unittest.main()
