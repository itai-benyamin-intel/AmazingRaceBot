"""
Test team_activity challenge with video verification method.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, User, Message, Chat, Video
from bot import AmazingRaceBot


@pytest.fixture
def bot_config(tmp_path):
    """Create a test configuration file."""
    config_content = """
telegram:
  bot_token: "test_token"

game:
  name: "Test Game"
  max_teams: 5
  max_team_size: 4
  challenges:
    - id: 1
      name: "First Challenge"
      description: "Take a photo"
      location: "Location 1"
      type: "photo"
      verification:
        method: "photo"
    
    - id: 2
      name: "Stars"
      description: |
        It's time to direct and film a short video that highlights a situation showing what it's like to work as uCode Engineers! 🎬
        - **Length:** Keep it between 30 seconds and 1 minute max.
        - **Participation:** Every team member must be in the video (including the person running the camera!).
      location: "Mishmar HaCarmel Farm"
      type: "team_activity"
      verification:
        method: "video"
      requires_photo_verification: true
      success_message: "Good Job, you are almost there!"

admin: 12345
"""
    config_file = tmp_path / "test_config.yml"
    config_file.write_text(config_content)
    return str(config_file)


@pytest.fixture
def bot(bot_config):
    """Create a bot instance with test configuration."""
    return AmazingRaceBot(bot_config)


class TestTeamActivityVideo:
    """Test team_activity challenge type with video verification."""

    @pytest.mark.asyncio
    async def test_video_verification_method_recognized(self, bot):
        """Test that 'video' verification method is recognized."""
        challenge = bot.challenges[1]  # Stars challenge
        assert challenge['verification']['method'] == 'video'
        
        # Test that video method returns 'photo' format (since they're handled the same)
        expected_format = bot.get_expected_answer_format(challenge)
        assert expected_format == 'photo'

    @pytest.mark.asyncio
    async def test_video_challenge_instructions(self, bot):
        """Test that video challenges get appropriate instructions."""
        challenge = bot.challenges[1]  # Stars challenge
        instructions = bot.get_challenge_instructions(challenge)
        
        # Should mention video
        assert 'video' in instructions.lower()
        # Should have video emoji
        assert '🎬' in instructions

    @pytest.mark.asyncio
    async def test_current_command_shows_video_challenge(self, bot):
        """Test that /current command works for video challenges."""
        # Setup: create a team and start the game
        bot.game_state.create_team("TestTeam", 111, "User1")
        bot.game_state.start_game()
        
        # Complete first challenge to reach video challenge
        bot.game_state.complete_challenge("TestTeam", 1, 2, None, False)
        
        # Create mock update and context
        update = MagicMock(spec=Update)
        update.effective_user = User(id=111, first_name="User1", is_bot=False)
        update.message = MagicMock(spec=Message)
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.bot = MagicMock()
        context.bot.send_message = AsyncMock()
        
        # Call current_challenge_command
        await bot.current_challenge_command(update, context)
        
        # Verify it was called (should not crash or return nothing)
        assert update.message.reply_text.called
        
        # Get the message that was sent
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        
        # Verify the message contains challenge information
        assert 'Stars' in message_text or 'video' in message_text.lower()

    @pytest.mark.asyncio
    async def test_submit_command_prompts_for_video(self, bot):
        """Test that /submit command prompts for video when method is 'video'."""
        # Setup: create a team and start the game
        bot.game_state.create_team("TestTeam", 111, "User1")
        bot.game_state.start_game()
        
        # Complete first challenge to reach video challenge
        bot.game_state.complete_challenge("TestTeam", 1, 2, None, False)
        
        # Complete photo verification for location (since requires_photo_verification is true)
        # Simulate that the photo verification was approved
        team = bot.game_state.teams["TestTeam"]
        if 'photo_verifications' not in team:
            team['photo_verifications'] = {}
        team['photo_verifications']['2'] = True
        
        # Create mock update and context
        update = MagicMock(spec=Update)
        update.effective_user = User(id=111, first_name="User1", is_bot=False)
        update.message = MagicMock(spec=Message)
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.args = []
        context.bot_data = {}
        
        # Call submit_command
        await bot.submit_command(update, context)
        
        # Verify it prompted for video
        assert update.message.reply_text.called
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        
        # Should mention video
        assert 'video' in message_text.lower() or '🎬' in message_text
        
        # Verify pending submission was created
        assert 111 in context.bot_data.get('pending_submissions', {})

    @pytest.mark.asyncio
    async def test_video_handler_processes_video_submission(self, bot):
        """Test that video handler processes video submissions."""
        # Setup: create a team and start the game
        bot.game_state.create_team("TestTeam", 111, "User1")
        bot.game_state.start_game()
        
        # Complete first challenge to reach video challenge
        bot.game_state.complete_challenge("TestTeam", 1, 2, None, False)
        
        # Create mock update with video
        update = MagicMock(spec=Update)
        update.effective_user = User(id=111, first_name="User1", is_bot=False)
        update.message = MagicMock(spec=Message)
        update.message.photo = None
        update.message.video = Video(
            file_id="test_video_123",
            file_unique_id="unique_123",
            width=1920,
            height=1080,
            duration=45
        )
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.bot_data = {
            'pending_submissions': {
                111: {
                    'team_name': 'TestTeam',
                    'challenge_id': 2,
                    'challenge_name': 'Stars'
                }
            }
        }
        context.bot = MagicMock()
        context.bot.send_video = AsyncMock()
        
        # Mock admin_id
        bot.admin_id = 12345
        
        # Call photo_handler (which also handles videos)
        await bot.photo_handler(update, context)
        
        # Verify video was accepted and notification sent
        assert update.message.reply_text.called
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        
        # Should confirm video submission
        assert 'video' in message_text.lower() or '🎬' in message_text
        
        # Verify admin was notified with video
        assert context.bot.send_video.called

    @pytest.mark.asyncio
    async def test_video_and_photo_verification_both_required(self, bot):
        """Test that a challenge can have both video verification method and photo location verification."""
        # Setup: create a team and start the game
        bot.game_state.create_team("TestTeam", 111, "User1")
        bot.game_state.start_game()
        
        # Complete first challenge to reach video challenge
        bot.game_state.complete_challenge("TestTeam", 1, 2, None, False)
        
        # Check that video challenge requires photo verification for location
        challenge = bot.challenges[1]
        assert challenge['requires_photo_verification'] == True
        assert challenge['verification']['method'] == 'video'
        
        # Verify the challenge requires photo verification
        requires_verification = bot.requires_photo_verification(challenge, 1)
        assert requires_verification == True
