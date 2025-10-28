"""
Telegram Amazing Race Bot - Main bot implementation
"""
import logging
import yaml
from datetime import datetime
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, PhotoSize
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters
)
from game_state import GameState

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class AmazingRaceBot:
    """Main bot class for the Amazing Race game."""
    
    # Challenge types that use photos as their answer and should not require
    # location verification by default, as the photo IS the challenge itself
    PHOTO_BASED_CHALLENGE_TYPES = ['multi_choice', 'team_activity', 'photo', 'scavenger']
    
    def __init__(self, config_file: str = "config.yml"):
        """Initialize the bot with configuration."""
        self.config = self.load_config(config_file)
        self.game_state = GameState()
        self.challenges = self.config['game']['challenges']
        # Support both single admin (new) and list of admins (backward compatibility)
        admin_config = self.config.get('admin') or self.config.get('admins', [])
        if isinstance(admin_config, list):
            # Legacy format: list of admins - only use the first one
            self.admin_id = admin_config[0] if admin_config else None
        else:
            # New format: single admin ID
            self.admin_id = admin_config
    
    @staticmethod
    def load_config(config_file: str) -> dict:
        """Load configuration from YAML file."""
        try:
            with open(config_file, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.error(f"Config file {config_file} not found!")
            raise
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is an admin."""
        return self.admin_id is not None and user_id == self.admin_id
    
    def validate_image_path(self, image_path: str) -> Optional[str]:
        """Validate a local image path for security.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Absolute path if valid, None otherwise
        """
        import os
        
        # Ensure path doesn't contain directory traversal attempts
        if '..' in image_path or image_path.startswith('/'):
            logger.warning(f"Rejected image path with directory traversal: {image_path}")
            return None
        
        # Construct absolute path relative to bot directory
        bot_dir = os.path.dirname(os.path.abspath(__file__))
        abs_path = os.path.abspath(os.path.join(bot_dir, image_path))
        
        # Ensure the path is within the bot directory
        if not abs_path.startswith(bot_dir):
            logger.warning(f"Rejected image path outside bot directory: {image_path}")
            return None
        
        # Check if file exists
        if not os.path.isfile(abs_path):
            logger.warning(f"Image file not found: {abs_path}")
            return None
        
        # Check file extension
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        ext = os.path.splitext(abs_path)[1].lower()
        if ext not in allowed_extensions:
            logger.warning(f"Rejected image with unsupported extension: {ext}")
            return None
        
        return abs_path
    
    def validate_image_url(self, image_url: str) -> bool:
        """Validate an image URL for security.
        
        Args:
            image_url: URL to the image
            
        Returns:
            True if valid, False otherwise
        """
        # Only allow HTTPS URLs for security
        if not image_url.startswith('https://'):
            logger.warning(f"Rejected non-HTTPS image URL: {image_url}")
            return False
        
        # Basic URL validation - check for common image extensions
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        url_lower = image_url.lower()
        
        # Allow URLs without extension if they're from common image hosting services
        # Note: 'example.com' is included for testing only - remove in production
        trusted_domains = ['imgur.com', 'i.imgur.com', 'example.com']
        if any(domain in url_lower for domain in trusted_domains):
            return True
        
        # Otherwise, check for image extension
        if not any(url_lower.endswith(ext) for ext in allowed_extensions):
            # Allow query parameters after extension
            for ext in allowed_extensions:
                if ext in url_lower:
                    return True
            logger.warning(f"Rejected URL without image extension: {image_url}")
            return False
        
        return True
    
    async def send_image(self, context: ContextTypes.DEFAULT_TYPE, chat_id: int, 
                        image_url: Optional[str] = None, image_path: Optional[str] = None,
                        caption: Optional[str] = None) -> bool:
        """Send an image to a chat.
        
        Args:
            context: Telegram context
            chat_id: Chat ID to send to
            image_url: Optional URL to remote image
            image_path: Optional path to local image
            caption: Optional caption for the image
            
        Returns:
            True if image was sent successfully, False otherwise
        """
        try:
            if image_url:
                # Validate URL
                if not self.validate_image_url(image_url):
                    logger.error(f"Invalid image URL: {image_url}")
                    return False
                
                # Send image from URL
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=image_url,
                    caption=caption,
                    parse_mode='Markdown' if caption else None
                )
                return True
            
            elif image_path:
                # Validate local path
                abs_path = self.validate_image_path(image_path)
                if not abs_path:
                    logger.error(f"Invalid image path: {image_path}")
                    return False
                
                # Send image from local file
                with open(abs_path, 'rb') as image_file:
                    await context.bot.send_photo(
                        chat_id=chat_id,
                        photo=image_file,
                        caption=caption,
                        parse_mode='Markdown' if caption else None
                    )
                return True
            
            else:
                logger.error("No image URL or path provided")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send image: {e}")
            return False
    
    def requires_photo_verification(self, challenge: dict, challenge_index: int) -> bool:
        """Check if photo verification is required for a specific challenge.
        
        Args:
            challenge: Challenge configuration dict
            challenge_index: 0-based index of the challenge
            
        Returns:
            True if photo verification is required, False otherwise
        """
        # Challenge 1 (index 0) never requires photo verification
        if challenge_index == 0:
            return False
        
        # Check if challenge has explicit requires_photo_verification setting
        if 'requires_photo_verification' in challenge:
            return challenge['requires_photo_verification']
        
        # Challenge types that use photos as their answer should NOT require
        # location verification by default, as the photo IS the challenge itself.
        # This can be overridden with explicit requires_photo_verification: true
        challenge_type = challenge.get('type', '')
        if challenge_type in self.PHOTO_BASED_CHALLENGE_TYPES:
            return False
        
        # Fall back to global setting for challenges 2+ (backward compatibility)
        return self.game_state.photo_verification_enabled
    
    def get_challenge_type_emoji(self, challenge_type: str) -> str:
        """Get emoji representation for challenge type."""
        type_emojis = {
            'photo': '📷',
            'riddle': '🧩',
            'code': '💻',
            'multi_choice': '❓',
            'location': '📍',
            'text': '📝',
            'scavenger': '🔍',
            'team_activity': '🤝',
            'decryption': '🔐',
            'tournament': '🏆'
        }
        return type_emojis.get(challenge_type, '🎯')
    
    def verify_answer(self, challenge: dict, user_answer: str, team_name: str = None) -> dict:
        """Verify a text answer for a challenge.
        
        Args:
            challenge: Challenge configuration
            user_answer: User's submitted answer
            team_name: Name of the team (needed for checklist verification)
            
        Returns:
            Dictionary with:
            - 'correct': bool - True if answer is fully correct
            - 'partial': bool - True if answer is partially correct (for checklist)
            - 'matched_items': list - List of matched checklist items (for checklist)
        """
        verification = challenge.get('verification', {})
        if verification.get('method') != 'answer':
            return {'correct': False, 'partial': False, 'matched_items': []}
        
        # Normalize user answer once at the beginning
        user_answer = user_answer.lower().strip()
        
        # Check if this is a checklist challenge
        checklist_items = verification.get('checklist_items')
        if checklist_items:
            # Checklist mode
            matched_items = []
            
            for item in checklist_items:
                item_lower = item.lower().strip()
                # Check if the user's answer matches this item
                if item_lower == user_answer or item_lower in user_answer:
                    matched_items.append(item)
            
            if matched_items and team_name:
                # Check if all items are now completed
                challenge_id = challenge['id']
                for item in matched_items:
                    self.game_state.update_checklist_item(team_name, challenge_id, item)
                
                all_complete = self.game_state.is_checklist_complete(team_name, challenge_id, checklist_items)
                return {
                    'correct': all_complete,
                    'partial': len(matched_items) > 0 and not all_complete,
                    'matched_items': matched_items
                }
            elif matched_items:
                # Team name not provided, but items matched
                return {
                    'correct': False,
                    'partial': True,
                    'matched_items': matched_items
                }
            else:
                return {
                    'correct': False,
                    'partial': False,
                    'matched_items': []
                }
        
        # Non-checklist mode
        # Check if there's a list of acceptable answers (for code challenges and alternatives)
        acceptable_answers = verification.get('acceptable_answers')
        if acceptable_answers:
            # For code challenges: accept any one of the acceptable answers
            for acceptable in acceptable_answers:
                acceptable_lower = acceptable.lower().strip()
                if acceptable_lower == user_answer or acceptable_lower in user_answer:
                    return {
                        'correct': True,
                        'partial': False,
                        'matched_items': []
                    }
            # None matched
            return {
                'correct': False,
                'partial': False,
                'matched_items': []
            }
        
        # Standard answer verification
        expected_answer = verification.get('answer', '').lower().strip()
        
        # Check if the expected answer is a comma-separated list (for multi_choice)
        if ',' in expected_answer:
            # For multi_choice with multiple answers, check if user answer contains all required keywords
            required_keywords = [kw.strip() for kw in expected_answer.split(',')]
            is_correct = all(keyword in user_answer for keyword in required_keywords)
        else:
            # For single answer, check exact match or if expected answer is in user answer
            is_correct = expected_answer == user_answer or expected_answer in user_answer
        
        return {
            'correct': is_correct,
            'partial': False,
            'matched_items': []
        }
    
    def get_expected_answer_format(self, challenge: dict) -> str:
        """Get the expected answer format for a challenge.
        
        Args:
            challenge: Challenge configuration
            
        Returns:
            'photo' or 'text' based on verification method
        """
        verification = challenge.get('verification', {})
        method = verification.get('method', 'photo')  # Default to 'photo' for backward compatibility
        
        if method == 'photo':
            return 'photo'
        elif method == 'answer':
            return 'text'
        else:
            # Log warning for unknown verification methods
            logger.warning(f"Unknown verification method '{method}' for challenge. Defaulting to 'unknown'.")
            return 'unknown'
    
    def get_format_mismatch_message(self, expected_format: str, challenge: dict) -> str:
        """Get an appropriate error message when answer format doesn't match.
        
        Args:
            expected_format: The expected format ('photo' or 'text')
            challenge: Challenge configuration
            
        Returns:
            Error message string
        """
        challenge_name = challenge.get('name', 'this challenge')
        
        if expected_format == 'photo':
            return (
                f"📷 *Photo Required*\n\n"
                f"A photo submission is required for *{challenge_name}*.\n\n"
                f"Please upload a photo as your answer instead of sending text.\n\n"
                f"Use `/submit` then send your photo."
            )
        elif expected_format == 'text':
            return (
                f"📝 *Text Answer Required*\n\n"
                f"A text answer is required for *{challenge_name}*.\n\n"
                f"Please send your answer as text instead of uploading a photo.\n\n"
                f"Use `/submit <your answer>` or `/submit` and then type your answer."
            )
        else:
            return (
                f"⚠️ *Invalid Submission Format*\n\n"
                f"The format you submitted doesn't match what's expected for *{challenge_name}*.\n\n"
                f"Please check the challenge instructions and try again."
            )
    
    def get_challenge_instructions(self, challenge: dict, team_name: str = None) -> str:
        """Get submission instructions based on challenge type.
        
        Args:
            challenge: Challenge configuration
            team_name: Optional team name for tracking photo submissions
            
        Returns:
            Instruction text for how to submit the challenge
        """
        verification = challenge.get('verification', {})
        method = verification.get('method', 'photo')
        
        if method == 'photo':
            photos_required = verification.get('photos_required', 1)
            if photos_required > 1:
                # Get current count if team_name provided
                if team_name:
                    current_count = self.game_state.get_photo_submission_count(team_name, challenge['id'])
                    return f"📷 Submit {photos_required} photos to complete this challenge. ({current_count}/{photos_required} submitted)"
                else:
                    return f"📷 Submit {photos_required} photos to complete this challenge."
            else:
                return "📷 Submit a photo to complete this challenge."
        elif method == 'answer':
            challenge_type = challenge.get('type', 'text')
            if challenge_type == 'riddle':
                return "💡 Reply with your answer to this riddle."
            elif challenge_type == 'code':
                return "💻 Reply with your code solution or the result."
            elif challenge_type == 'multi_choice':
                return "📝 Reply with your answer."
            elif challenge_type == 'decryption':
                return "🔓 Reply with the decrypted message."
            else:
                return "📝 Reply with your answer."
        elif method == 'location':
            return "📍 You need to be at the correct location."
        elif method == 'auto':
            return "✅ This challenge is auto-verified."
        elif method == 'tournament':
            return "🏆 Admin will report tournament results."
        else:
            return "📝 Submit your response to complete this challenge."
    
    async def check_and_broadcast_unlocked_challenge(self, context: ContextTypes.DEFAULT_TYPE, 
                                                     team_name: str) -> bool:
        """Check if a challenge became unlocked and broadcast if we haven't already.
        
        Args:
            context: Telegram context
            team_name: Name of the team
            
        Returns:
            True if a broadcast was sent, False otherwise
        """
        team_data = self.game_state.teams[team_name]
        current_challenge_index = team_data.get('current_challenge_index', 0)
        
        # Check if all challenges are completed
        if current_challenge_index >= len(self.challenges):
            return False
        
        challenge = self.challenges[current_challenge_index]
        challenge_id = challenge['id']
        
        # Only check for challenges after the first one
        if current_challenge_index == 0:
            return False
        
        # Check if there was a timeout that may have expired
        # Pass the previous challenge config for custom penalty support
        previous_challenge = self.challenges[current_challenge_index - 1]
        unlock_time_str = self.game_state.get_challenge_unlock_time(team_name, challenge_id, previous_challenge)
        if not unlock_time_str:
            return False
        
        unlock_time = datetime.fromisoformat(unlock_time_str)
        now = datetime.now()
        
        # Check if timeout has expired
        if now >= unlock_time:
            # Check if we've already broadcast this unlock
            broadcasts = team_data.get('challenge_unlock_broadcasts', {})
            if str(challenge_id) not in broadcasts:
                # Haven't broadcast yet - do it now
                await self.broadcast_current_challenge(context, team_name)
                
                # Mark as broadcast
                if 'challenge_unlock_broadcasts' not in team_data:
                    team_data['challenge_unlock_broadcasts'] = {}
                team_data['challenge_unlock_broadcasts'][str(challenge_id)] = datetime.now().isoformat()
                self.game_state.save_state()
                
                return True
        
        return False
    
    async def broadcast_current_challenge(self, context: ContextTypes.DEFAULT_TYPE, 
                                          team_name: str, exclude_user_id: Optional[int] = None):
        """Broadcast current challenge details to team members.
        
        Args:
            context: Telegram context
            team_name: Name of the team
            exclude_user_id: Optional user ID to exclude from broadcast (e.g., submitter)
        """
        team_data = self.game_state.teams[team_name]
        current_challenge_index = team_data.get('current_challenge_index', 0)
        
        # Check if all challenges are completed
        if current_challenge_index >= len(self.challenges):
            return
        
        # Get current challenge
        challenge = self.challenges[current_challenge_index]
        challenge_id = challenge['id']
        
        # Check if photo verification is required and not yet done
        if self.requires_photo_verification(challenge, current_challenge_index):
            photo_verifications = team_data.get('photo_verifications', {})
            if str(challenge_id) not in photo_verifications:
                # Photo verification not done yet - don't broadcast challenge details
                # Instead, notify team that they need to send a photo
                broadcast_message = (
                    f"📷 *Photo Verification Required*\n\n"
                    f"*Challenge #{challenge_id}: {challenge['name']}*\n\n"
                    f"Before you can view this challenge, send a photo of your team at the challenge location.\n\n"
                    f"📍 Location: {challenge['location']}\n\n"
                    f"*Instructions:*\n"
                    f"1. Go to the challenge location\n"
                    f"2. Take a photo of your team there\n"
                    f"3. Send the photo to this bot\n"
                    f"4. Wait for admin approval\n"
                    f"5. Challenge will be revealed after approval\n\n"
                    f"⏱️ Note: The timeout/penalty timer will only start after your photo is approved."
                )
                
                # Broadcast to all team members
                sent_to_users = set()
                for member in team_data['members']:
                    member_id = member['id']
                    if exclude_user_id and member_id == exclude_user_id:
                        continue
                    if member_id in sent_to_users:
                        continue
                    
                    try:
                        await context.bot.send_message(
                            chat_id=member_id,
                            text=broadcast_message,
                            parse_mode='Markdown'
                        )
                        sent_to_users.add(member_id)
                    except Exception as e:
                        logger.error(f"Failed to send photo verification notice to user {member_id}: {e}")
                
                return
        
        challenge_type = challenge.get('type', 'text')
        type_emoji = self.get_challenge_type_emoji(challenge_type)
        instructions = self.get_challenge_instructions(challenge, team_name)
        verification_method = challenge.get('verification', {}).get('method')
        
        # Check if this is a tournament challenge and initialize if needed
        if verification_method == 'tournament':
            tournament = self.game_state.get_tournament(challenge_id)
            if not tournament:
                # Initialize tournament with all teams that have reached this challenge
                current_challenge_index = team_data.get('current_challenge_index', 0)
                eligible_teams = [
                    name for name, data in self.game_state.teams.items()
                    if data.get('current_challenge_index', 0) >= current_challenge_index
                ]
                
                if len(eligible_teams) > 0:
                    tournament_config = challenge.get('tournament', {})
                    game_name = tournament_config.get('game_name', 'Tournament')
                    
                    self.game_state.create_tournament(challenge_id, eligible_teams, game_name)
                    tournament = self.game_state.get_tournament(challenge_id)
                    
                    if tournament:
                        # If tournament auto-completed, complete the challenge for the winning team(s)
                        if tournament['status'] == 'complete':
                            # Get the tournament winner(s) from rankings
                            rankings = tournament.get('rankings', [])
                            if rankings:
                                # Complete challenge for the winner (first in rankings)
                                winner = rankings[0]
                                self.game_state.complete_challenge(winner, challenge_id, len(self.challenges))
                        
                        # Notify admin that tournament is ready (only if needed)
                        if self.admin_id:
                            try:
                                # Only notify admin if tournament needs admin action
                                if tournament['status'] == 'active':
                                    first_round = self.game_state.get_current_round_matches(challenge_id)
                                    admin_msg = (
                                        f"🏆 *Tournament Started!*\n\n"
                                        f"Challenge: {challenge['name']}\n"
                                        f"Game: {game_name}\n"
                                        f"Teams: {len(eligible_teams)}\n\n"
                                        f"📋 *First Round Matches:*\n\n"
                                    )
                                    
                                    for i, match in enumerate(first_round):
                                        if match['status'] == 'pending':
                                            admin_msg += f"{i+1}. {match['team1']} vs {match['team2']}\n"
                                        elif match['status'] == 'bye':
                                            admin_msg += f"{i+1}. {match['team1']} (bye)\n"
                                    
                                    admin_msg += f"\nUse `/tournamentwin {challenge_id} <team_name>` to report winners."
                                    
                                    await context.bot.send_message(
                                        chat_id=self.admin_id,
                                        text=admin_msg,
                                        parse_mode='Markdown'
                                    )
                                elif tournament['status'] == 'complete' and len(eligible_teams) == 1:
                                    # Notify admin that single team auto-won
                                    admin_msg = (
                                        f"🏆 *Tournament Auto-Completed!*\n\n"
                                        f"Challenge: {challenge['name']}\n"
                                        f"Game: {game_name}\n"
                                        f"Only one team ({eligible_teams[0]}) reached this challenge.\n"
                                        f"They automatically win by default."
                                    )
                                    
                                    await context.bot.send_message(
                                        chat_id=self.admin_id,
                                        text=admin_msg,
                                        parse_mode='Markdown'
                                    )
                            except Exception as e:
                                logger.error(f"Failed to notify admin of tournament start: {e}")
        
        # Create broadcast message
        broadcast_message = (
            f"🎯 *New Challenge Available!*\n\n"
            f"*Challenge #{challenge_id}: {challenge['name']}*\n"
            f"{type_emoji} Type: {challenge_type}\n"
            f"📍 Location: {challenge['location']}\n"
            f"📝 {challenge['description']}\n\n"
            f"ℹ️ {instructions}\n\n"
        )
        
        # Check if this is a tournament challenge and add match information
        if verification_method == 'tournament':
            tournament = self.game_state.get_tournament(challenge_id)
            if tournament:
                tournament_config = challenge.get('tournament', {})
                game_name = tournament_config.get('game_name', 'Tournament')
                
                broadcast_message += f"🏆 *Tournament: {game_name}*\n\n"
                
                # Show current matches for this team
                current_matches = self.game_state.get_current_round_matches(challenge_id)
                team_match = None
                for match in current_matches:
                    if match['team1'] == team_name or match['team2'] == team_name:
                        team_match = match
                        break
                
                if team_match:
                    if team_match['status'] == 'pending':
                        if team_match['team2']:
                            broadcast_message += f"⚔️ Your match: {team_match['team1']} vs {team_match['team2']}\n"
                        else:
                            broadcast_message += f"🎫 You have a bye this round\n"
                        broadcast_message += "Waiting for admin to report results...\n\n"
                    elif team_match['status'] == 'bye':
                        broadcast_message += f"🎫 You have a bye and advance automatically\n\n"
                
                if tournament['status'] == 'complete':
                    broadcast_message += "Tournament is complete!\n"
            else:
                broadcast_message += "🏆 *Tournament will start when all teams arrive*\n\n"
        
        # Add hints information
        hints = challenge.get('hints', [])
        used_hints = self.game_state.get_used_hints(team_name, challenge_id)
        
        if hints:
            broadcast_message += f"💡 Hints available: {len(hints)}\n"
            if len(used_hints) < len(hints):
                penalty_minutes = self.game_state.get_penalty_minutes_per_hint(challenge)
                broadcast_message += f"Use /hint to get a hint (costs {penalty_minutes} min penalty)\n"
        
        # Don't show submit instructions for tournament challenges
        if verification_method == 'tournament':
            broadcast_message += "\nUse /current to see your match status."
        else:
            broadcast_message += "\nUse /current to see full details.\nUse /submit [answer] to submit this challenge."
        
        # Broadcast to all team members
        sent_to_users = set()
        for member in team_data['members']:
            member_id = member['id']
            # Skip excluded user (e.g., the submitter who already got the message)
            if exclude_user_id and member_id == exclude_user_id:
                continue
            if member_id in sent_to_users:
                continue
            
            try:
                # Send image first if configured
                image_url = challenge.get('image_url')
                image_path = challenge.get('image_path')
                if image_url or image_path:
                    await self.send_image(
                        context=context,
                        chat_id=member_id,
                        image_url=image_url,
                        image_path=image_path,
                        caption=f"📸 Image for Challenge #{challenge_id}"
                    )
                
                # Then send the challenge text
                await context.bot.send_message(
                    chat_id=member_id,
                    text=broadcast_message,
                    parse_mode='Markdown'
                )
                sent_to_users.add(member_id)
            except Exception as e:
                logger.error(f"Failed to send challenge broadcast to user {member_id}: {e}")
    
    async def send_success_message_if_configured(self, challenge: dict, chat_id: int, 
                                                  context: ContextTypes.DEFAULT_TYPE = None,
                                                  update: Update = None):
        """Send custom success message if configured for the challenge.
        
        Args:
            challenge: Challenge configuration dict
            chat_id: Telegram chat ID to send message to
            context: Telegram context (for bot.send_message), optional
            update: Telegram update (for message.reply_text), optional
            
        Note: At least one of context or update must be provided.
        """
        success_message = challenge.get('success_message')
        if not success_message:
            return
        
        if update and update.message:
            # Use reply_text if we have an update with a message
            await update.message.reply_text(success_message, parse_mode='Markdown')
        elif context:
            # Use send_message if we only have context
            await context.bot.send_message(
                chat_id=chat_id,
                text=success_message,
                parse_mode='Markdown'
            )
    
    async def broadcast_challenge_completion(self, context: ContextTypes.DEFAULT_TYPE, 
                                            team_name: str, challenge_id: int, 
                                            challenge_name: str, submitted_by_id: int,
                                            submitted_by_name: str, completed: int, 
                                            total: int, penalty_info: Optional[dict] = None,
                                            photo_verification_needed: bool = False):
        """Broadcast challenge completion message to team members and admin.
        
        Args:
            context: Telegram context
            team_name: Name of the team
            challenge_id: ID of the completed challenge
            challenge_name: Name of the completed challenge
            submitted_by_id: ID of user who submitted
            submitted_by_name: Name of user who submitted
            completed: Number of challenges completed
            total: Total number of challenges
            penalty_info: Optional dict with penalty information (hint_count, penalty_minutes, unlock_time)
            photo_verification_needed: Deprecated - no longer used to avoid duplicate messages.
                Photo verification details are sent by broadcast_current_challenge() instead.
        """
        team_data = self.game_state.teams[team_name]
        
        # Create broadcast message
        broadcast_message = (
            f"✅ *Challenge Completed!*\n\n"
            f"Team: {team_name}\n"
            f"Challenge #{challenge_id}: {challenge_name}\n"
            f"Submitted by: {submitted_by_name}\n"
            f"Progress: {completed}/{total} challenges"
        )
        
        # Add finish message if team completed all challenges
        if team_data.get('finish_time'):
            broadcast_message += f"\n\n🏆 *CONGRATULATIONS!* 🏆\n"
            broadcast_message += f"Your team finished the race!\n"
            broadcast_message += f"Finish time: {team_data['finish_time']}"
        else:
            # Add penalty information if present
            if penalty_info:
                broadcast_message += (
                    f"\n\n⏱️ *Hint Penalty Applied*\n"
                    f"You used {penalty_info['hint_count']} hint(s) on this challenge.\n"
                    f"Next challenge unlocks in {penalty_info['penalty_minutes']} minutes at:\n"
                    f"{penalty_info['unlock_time'].strftime('%H:%M:%S')}"
                )
            
            # Note: Photo verification notification is NOT added here to avoid duplication.
            # The detailed photo verification message will be sent by broadcast_current_challenge()
            # which is called immediately after this function.
        
        # Broadcast to all team members
        sent_to_users = set()
        for member in team_data['members']:
            member_id = member['id']
            # Skip the user who submitted (they already got the message)
            if member_id == submitted_by_id or member_id in sent_to_users:
                continue
            
            try:
                await context.bot.send_message(
                    chat_id=member_id,
                    text=broadcast_message,
                    parse_mode='Markdown'
                )
                sent_to_users.add(member_id)
            except Exception as e:
                logger.error(f"Failed to send completion broadcast to user {member_id}: {e}")
        
        # Notify admin
        if self.admin_id and self.admin_id not in sent_to_users:
            try:
                await context.bot.send_message(
                    chat_id=self.admin_id,
                    text=broadcast_message,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to send completion broadcast to admin: {e}")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /start command."""
        welcome_message = (
            f"🏁 Welcome to {self.config['game']['name']}! 🏁\n\n"
            "This is an interactive Amazing Race game.\n"
            "Complete challenges sequentially to win!\n\n"
        )
        
        user = update.effective_user
        team_name = self.game_state.get_team_by_user(user.id)
        
        # Check player state and provide context-aware help
        if not team_name:
            # Player has no team
            help_text = (
                "You're not part of a team yet. Here's how to get started:\n\n"
                "🆕 *Create a new team:*\n"
                "Use /createteam <team_name> to create a team\n"
                "Example: /createteam Awesome Team\n\n"
                "👥 *Join an existing team:*\n"
                "Use /jointeam <team_name> to join a team\n"
                "Example: /jointeam Awesome Team\n\n"
                "🏆 *See existing teams:*\n"
                "Use /teams to see which teams exist in the race\n\n"
                "📋 You can also use the menu button below to see all available commands."
            )
        elif not self.game_state.game_started:
            # Player has team but game hasn't started
            help_text = (
                "⏳ *Waiting for Game to Start*\n\n"
                "You're all set! Your team is ready to go.\n\n"
                "The game will begin once the admin starts it.\n"
                "While you wait, you can:\n\n"
                "👥 `/myteam` - View your team members\n"
                "🏆 `/teams` - See all registered teams\n\n"
                "📋 Use the menu button below to see all available commands."
            )
        else:
            # Game has started
            help_text = (
                "🎯 *How to Play*\n\n"
                "The game is in progress! Here's how to navigate:\n\n"
                "📍 *View your current challenge:*\n"
                "Use `/current` to see details of your current challenge\n\n"
                "📊 *Check your progress:*\n"
                "Use `/challenges` to see completed and current challenges\n\n"
                "✅ *Submit your answer:*\n"
                "Use `/submit [answer]` for text answers\n"
                "Use `/submit` for photo challenges\n\n"
                "💡 *Need help?*\n"
                "Use `/hint` to get a hint (costs penalty, default 2 min)\n\n"
                "📋 Use the menu button below to see all available commands."
            )
        
        full_message = welcome_message + help_text
        await update.message.reply_text(full_message, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /help command with context-aware messages."""
        user = update.effective_user
        team_name = self.game_state.get_team_by_user(user.id)
        
        # Check player state and provide context-aware help
        if not team_name:
            # Player has no team
            help_text = (
                "👋 *Welcome to the Amazing Race!*\n\n"
                "You're not part of a team yet. Here's how to get started:\n\n"
                "🆕 *Create a new team:*\n"
                "Use /createteam <team_name> to create a team\n"
                "Example: /createteam Awesome Team\n\n"
                "👥 *Join an existing team:*\n"
                "Use /jointeam <team_name> to join a team\n"
                "Example: /jointeam Awesome Team\n\n"
                "🏆 *See existing teams:*\n"
                "Use /teams to see which teams exist in the race\n\n"
                "📋 You can also use the menu button below to see all available commands."
            )
        elif not self.game_state.game_started:
            # Player has team but game hasn't started
            help_text = (
                "⏳ *Waiting for Game to Start*\n\n"
                "You're all set! Your team is ready to go.\n\n"
                "The game will begin once the admin starts it.\n"
                "While you wait, you can:\n\n"
                "👥 `/myteam` - View your team members\n"
                "🏆 `/teams` - See all registered teams\n\n"
                "📋 Use the menu button below to see all available commands."
            )
        else:
            # Game has started
            help_text = (
                "🎯 *How to Play*\n\n"
                "The game is in progress! Here's how to navigate:\n\n"
                "📍 *View your current challenge:*\n"
                "Use `/current` to see details of your current challenge\n\n"
                "📊 *Check your progress:*\n"
                "Use `/challenges` to see completed and current challenges\n\n"
                "✅ *Submit your answer:*\n"
                "Use `/submit [answer]` for text answers\n"
                "Use `/submit` for photo challenges\n\n"
                "💡 *Need help?*\n"
                "Use `/hint` to get a hint (costs penalty, default 2 min)\n\n"
                "📋 Use the menu button below to see all available commands."
            )
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def create_team_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /createteam command."""
        if not context.args:
            # Store that we're waiting for team name
            if 'waiting_for' not in context.user_data:
                context.user_data['waiting_for'] = {}
            context.user_data['waiting_for']['command'] = 'createteam'
            await update.message.reply_text(
                "Please provide a team name:\n"
                "What would you like to name your team?"
            )
            return
        
        team_name = ' '.join(context.args)
        user = update.effective_user
        
        # Check if user is already in a team
        existing_team = self.game_state.get_team_by_user(user.id)
        if existing_team:
            await update.message.reply_text(f"You are already in team '{existing_team}'!")
            return
        
        # Check max teams
        if len(self.game_state.teams) >= self.config['game']['max_teams']:
            await update.message.reply_text("Maximum number of teams reached!")
            return
        
        # Create team
        if self.game_state.create_team(team_name, user.id, user.first_name):
            await update.message.reply_text(
                f"✅ Team '{team_name}' created successfully!\n"
                f"You are the team captain. Other players can join with:\n"
                f"/jointeam {team_name}"
            )
        else:
            await update.message.reply_text(f"Team '{team_name}' already exists!")
    
    async def join_team_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /jointeam command."""
        if not context.args:
            # Store that we're waiting for team name
            if 'waiting_for' not in context.user_data:
                context.user_data['waiting_for'] = {}
            context.user_data['waiting_for']['command'] = 'jointeam'
            await update.message.reply_text(
                "Please provide the team name:\n"
                "Which team would you like to join?"
            )
            return
        
        team_name = ' '.join(context.args)
        user = update.effective_user
        
        # Check if team exists
        if team_name not in self.game_state.teams:
            await update.message.reply_text(f"Team '{team_name}' does not exist!")
            return
        
        # Check team size
        team = self.game_state.teams[team_name]
        if len(team['members']) >= self.config['game']['max_team_size']:
            await update.message.reply_text("This team is full!")
            return
        
        # Join team
        if self.game_state.join_team(team_name, user.id, user.first_name):
            # Get updated team data after join
            team_data = self.game_state.teams[team_name]
            
            await update.message.reply_text(
                f"✅ You joined team '{team_name}'!\n"
                f"Team members: {len(team_data['members'])}/{self.config['game']['max_team_size']}"
            )
            
            # Broadcast to existing team members (excluding the new joiner)
            broadcast_message = (
                f"👥 *New Team Member!*\n\n"
                f"Welcome *{user.first_name}* to team '{team_name}'! 🎉\n\n"
                f"Team size: {len(team_data['members'])}/{self.config['game']['max_team_size']}"
            )
            
            for member in team_data['members']:
                member_id = member['id']
                # Skip the user who just joined (they already got a confirmation message)
                if member_id == user.id:
                    continue
                
                try:
                    await context.bot.send_message(
                        chat_id=member_id,
                        text=broadcast_message,
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.error(f"Failed to send team join notification to user {member_id}: {e}")
        else:
            await update.message.reply_text("You are already in a team!")
    
    async def my_team_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /myteam command."""
        user = update.effective_user
        team_name = self.game_state.get_team_by_user(user.id)
        
        if not team_name:
            await update.message.reply_text("You are not in any team yet! Use /createteam or /jointeam")
            return
        
        team = self.game_state.teams[team_name]
        members_list = '\n'.join([f"  • {m['name']}" for m in team['members']])
        completed = len(team['completed_challenges'])
        total = len(self.challenges)
        current_challenge = team.get('current_challenge_index', 0) + 1
        
        status = ""
        if team.get('finish_time'):
            status = f"✅ *FINISHED!* at {team['finish_time']}\n"
        elif completed < total:
            status = f"🎯 *Current Challenge:* #{current_challenge}\n"
        
        message = (
            f"👥 *Team: {team_name}*\n\n"
            f"{status}"
            f"📊 Progress: {completed}/{total} challenges completed\n\n"
            f"*Members:*\n{members_list}"
        )
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def leaderboard_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /leaderboard command (admin only)."""
        user = update.effective_user
        if not self.is_admin(user.id):
            await update.message.reply_text("Only admins can view the leaderboard during the game!\nYou can view teams using /teams")
            return
        
        leaderboard = self.game_state.get_leaderboard()
        
        if not leaderboard:
            await update.message.reply_text("No teams yet! Create one with /createteam")
            return
        
        message = "🏆 *Leaderboard* 🏆\n\n"
        
        finished_teams = [t for t in leaderboard if t[2] is not None]
        racing_teams = [t for t in leaderboard if t[2] is None]
        
        if finished_teams:
            message += "*Finished Teams:*\n"
            for i, (team_name, completed, finish_time) in enumerate(finished_teams, 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                message += f"{medal} *{team_name}* - Finished!\n"
            message += "\n"
        
        if racing_teams:
            message += "*Still Racing:*\n"
            for team_name, completed, _ in racing_teams:
                total = len(self.challenges)
                message += f"🏃 *{team_name}* - {completed}/{total} challenges\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def challenges_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /challenges command - shows names of completed and current challenges."""
        user = update.effective_user
        team_name = self.game_state.get_team_by_user(user.id)
        
        completed_challenges = []
        current_challenge_index = 0
        
        if team_name:
            team = self.game_state.teams[team_name]
            completed_challenges = team['completed_challenges']
            current_challenge_index = team.get('current_challenge_index', 0)
        
        message = "🎯 *Challenges* 🎯\n\n"
        
        # Check if current challenge is locked due to penalty
        penalty_info = None
        if team_name and current_challenge_index < len(self.challenges):
            current_challenge = self.challenges[current_challenge_index]
            challenge_id = current_challenge['id']
            
            if current_challenge_index > 0:  # Not the first challenge
                previous_challenge = self.challenges[current_challenge_index - 1]
                unlock_time_str = self.game_state.get_challenge_unlock_time(team_name, challenge_id, previous_challenge)
                if unlock_time_str:
                    unlock_time = datetime.fromisoformat(unlock_time_str)
                    now = datetime.now()
                    
                    if now < unlock_time:
                        # Challenge is still locked
                        time_remaining = unlock_time - now
                        minutes = int(time_remaining.total_seconds() // 60)
                        seconds = int(time_remaining.total_seconds() % 60)
                        
                        previous_challenge_id = challenge_id - 1
                        hint_count = self.game_state.get_hint_count(team_name, previous_challenge_id)
                        
                        penalty_info = {
                            'minutes': minutes,
                            'seconds': seconds,
                            'unlock_time': unlock_time,
                            'hint_count': hint_count
                        }
        
        for i, challenge in enumerate(self.challenges):
            if i < current_challenge_index:
                # Completed challenge - show title only
                message += f"✅ *{challenge['name']}*\n\n"
            elif i == current_challenge_index:
                # Current challenge - show title only
                if penalty_info:
                    message += (
                        f"⏱️ *{challenge['name']}* (LOCKED - Penalty Timeout)\n"
                        f"   Challenge locked due to {penalty_info['hint_count']} hint(s) used\n"
                        f"   ⏳ Unlocks in: {penalty_info['minutes']}m {penalty_info['seconds']}s\n"
                        f"   Available at: {penalty_info['unlock_time'].strftime('%H:%M:%S')}\n\n"
                    )
                else:
                    message += f"🎯 *{challenge['name']}* (CURRENT)\n"
                    
                    # Show checklist progress if applicable
                    verification = challenge.get('verification', {})
                    checklist_items = verification.get('checklist_items')
                    if checklist_items and team_name:
                        progress = self.game_state.get_checklist_progress(team_name, challenge['id'])
                        completed_count = sum(1 for item in checklist_items if progress.get(item, False))
                        message += f"   📝 Checklist: {completed_count}/{len(checklist_items)} items completed\n"
                    
                    message += "\n"
            # Locked challenges are not shown anymore
        
        if penalty_info:
            message += "⏱️ Your current challenge is locked due to hint penalty.\n"
            message += f"It will unlock at {penalty_info['unlock_time'].strftime('%H:%M:%S')}.\n\n"
        
        message += "Use /current to see full details of your current challenge.\n"
        message += "Use /submit [answer] to submit your answers."
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def current_challenge_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /current_challenge command."""
        user = update.effective_user
        team_name = self.game_state.get_team_by_user(user.id)
        
        if not team_name:
            await update.message.reply_text("You are not in any team yet! Use /createteam or /jointeam")
            return
        
        # Check if a timeout just expired and broadcast if needed
        await self.check_and_broadcast_unlocked_challenge(context, team_name)
        
        team = self.game_state.teams[team_name]
        current_challenge_index = team.get('current_challenge_index', 0)
        
        # Check if all challenges are completed
        if current_challenge_index >= len(self.challenges):
            await update.message.reply_text(
                "🏆 Congratulations! Your team has completed all challenges!\n"
                f"Finish time: {team.get('finish_time', 'N/A')}"
            )
            return
        
        # Get current challenge
        challenge = self.challenges[current_challenge_index]
        challenge_id = challenge['id']
        
        # Check if photo verification is required and not yet done
        if self.requires_photo_verification(challenge, current_challenge_index):
            photo_verifications = team.get('photo_verifications', {})
            if str(challenge_id) not in photo_verifications:
                # Photo verification not done yet
                message = (
                    f"📷 *Photo Verification Required*\n\n"
                    f"*Challenge #{challenge_id}: {challenge['name']}*\n\n"
                    f"Before you can view this challenge, you need to send a photo of your team at the challenge location.\n\n"
                    f"📍 Location: {challenge['location']}\n\n"
                    f"*Instructions:*\n"
                    f"1. Go to the challenge location\n"
                    f"2. Take a photo of your team there\n"
                    f"3. Send the photo to this bot\n"
                    f"4. Wait for admin approval\n"
                    f"5. Challenge will be revealed after approval\n\n"
                    f"⏱️ Note: The timeout/penalty timer will only start after your photo is approved."
                )
                await update.message.reply_text(message, parse_mode='Markdown')
                return
        
        challenge_type = challenge.get('type', 'text')
        type_emoji = self.get_challenge_type_emoji(challenge_type)
        instructions = self.get_challenge_instructions(challenge, team_name)
        
        # Check if this is a tournament challenge and initialize if needed
        verification_method = challenge.get('verification', {}).get('method')
        if verification_method == 'tournament':
            tournament = self.game_state.get_tournament(challenge_id)
            if not tournament:
                # Initialize tournament with all teams that have reached this challenge
                eligible_teams = [
                    name for name, data in self.game_state.teams.items()
                    if data.get('current_challenge_index', 0) >= current_challenge_index
                ]
                
                if len(eligible_teams) >= 1:
                    tournament_config = challenge.get('tournament', {})
                    game_name = tournament_config.get('game_name', 'Tournament')
                    
                    self.game_state.create_tournament(challenge_id, eligible_teams, game_name)
                    tournament = self.game_state.get_tournament(challenge_id)
                    
                    # If tournament auto-completed, complete the challenge for the winning team(s)
                    if tournament and tournament['status'] == 'complete':
                        # Get the tournament winner(s) from rankings
                        rankings = tournament.get('rankings', [])
                        if rankings:
                            # Complete challenge for the winner (first in rankings)
                            winner = rankings[0]
                            self.game_state.complete_challenge(winner, challenge_id, len(self.challenges))
                    
                    # Notify admin that tournament is ready
                    if self.admin_id:
                        try:
                            # Only notify admin if tournament needs admin action
                            if tournament and tournament['status'] == 'active':
                                first_round = self.game_state.get_current_round_matches(challenge_id)
                                admin_msg = (
                                    f"🏆 *Tournament Started!*\n\n"
                                    f"Challenge: {challenge['name']}\n"
                                    f"Game: {game_name}\n"
                                    f"Teams: {len(eligible_teams)}\n\n"
                                    f"📋 *First Round Matches:*\n\n"
                                )
                                
                                for i, match in enumerate(first_round):
                                    if match['status'] == 'pending':
                                        admin_msg += f"{i+1}. {match['team1']} vs {match['team2']}\n"
                                    elif match['status'] == 'bye':
                                        admin_msg += f"{i+1}. {match['team1']} (bye)\n"
                                
                                admin_msg += f"\nUse `/tournamentwin {challenge_id} <team_name>` to report winners."
                                
                                await context.bot.send_message(
                                    chat_id=self.admin_id,
                                    text=admin_msg,
                                    parse_mode='Markdown'
                                )
                            elif tournament and tournament['status'] == 'complete' and len(eligible_teams) == 1:
                                # Notify admin that single team auto-won
                                admin_msg = (
                                    f"🏆 *Tournament Auto-Completed!*\n\n"
                                    f"Challenge: {challenge['name']}\n"
                                    f"Game: {game_name}\n"
                                    f"Only one team ({eligible_teams[0]}) reached this challenge.\n"
                                    f"They automatically win by default."
                                )
                                
                                await context.bot.send_message(
                                    chat_id=self.admin_id,
                                    text=admin_msg,
                                    parse_mode='Markdown'
                                )
                        except Exception as e:
                            logger.error(f"Failed to notify admin of tournament start: {e}")
        
        # Check if challenge is locked due to penalty
        is_locked = False
        penalty_info = None
        if current_challenge_index > 0:  # Not the first challenge
            previous_challenge = self.challenges[current_challenge_index - 1]
            unlock_time_str = self.game_state.get_challenge_unlock_time(team_name, challenge_id, previous_challenge)
            if unlock_time_str:
                unlock_time = datetime.fromisoformat(unlock_time_str)
                now = datetime.now()
                
                if now < unlock_time:
                    # Challenge is still locked
                    is_locked = True
                    time_remaining = unlock_time - now
                    minutes = int(time_remaining.total_seconds() // 60)
                    seconds = int(time_remaining.total_seconds() % 60)
                    
                    previous_challenge_id = challenge_id - 1
                    hint_count = self.game_state.get_hint_count(team_name, previous_challenge_id)
                    
                    penalty_info = {
                        'minutes': minutes,
                        'seconds': seconds,
                        'unlock_time': unlock_time,
                        'hint_count': hint_count
                    }
        
        if is_locked and penalty_info:
            # Show locked challenge message
            message = (
                f"⏱️ *Challenge Locked - Penalty Timeout*\n\n"
                f"*Next Challenge: #{challenge_id}: {challenge['name']}*\n\n"
                f"Your team used {penalty_info['hint_count']} hint(s) on the previous challenge.\n"
                f"You must wait before this challenge is unlocked.\n\n"
                f"⏳ Time remaining: {penalty_info['minutes']}m {penalty_info['seconds']}s\n\n"
                f"The challenge will be available at:\n"
                f"{penalty_info['unlock_time'].strftime('%H:%M:%S')}\n\n"
                f"Once unlocked, you'll be able to view the full challenge details and submit your answer."
            )
        else:
            # Show full challenge details
            message = (
                f"🎯 *Your Current Challenge*\n\n"
                f"*Challenge #{challenge_id}: {challenge['name']}*\n"
                f"{type_emoji} Type: {challenge_type}\n"
                f"📍 Location: {challenge['location']}\n"
                f"📝 {challenge['description']}\n\n"
                f"ℹ️ {instructions}\n\n"
            )
            
            # Check if this is a checklist challenge
            verification = challenge.get('verification', {})
            checklist_items = verification.get('checklist_items')
            if checklist_items:
                # Show checklist progress
                progress = self.game_state.get_checklist_progress(team_name, challenge_id)
                completed_count = 0
                completed_items = []
                for item in checklist_items:
                    if progress.get(item, False):
                        completed_items.append(item)
                        completed_count += 1
                
                if completed_items:
                    message += "📝 *Completed Items:*\n"
                    for item in completed_items:
                        message += f"✅ {item}\n"
                    message += "\n"
                
                message += f"*Progress:* {completed_count}/{len(checklist_items)} items completed\n"
                if completed_count < len(checklist_items):
                    message += "💡 *Tip:* Submit items to reveal them!\n\n"
                else:
                    message += "\n"
            
            # Check if this is a tournament challenge
            if verification_method == 'tournament':
                tournament = self.game_state.get_tournament(challenge_id)
                if tournament:
                    tournament_config = challenge.get('tournament', {})
                    game_name = tournament_config.get('game_name', 'Tournament')
                    
                    message += f"🏆 *Tournament: {game_name}*\n\n"
                    
                    # Show current matches for this team
                    current_matches = self.game_state.get_current_round_matches(challenge_id)
                    team_match = None
                    for match in current_matches:
                        if match['team1'] == team_name or match['team2'] == team_name:
                            team_match = match
                            break
                    
                    if team_match:
                        if team_match['status'] == 'pending':
                            if team_match['team2']:
                                message += f"⚔️ Your match: {team_match['team1']} vs {team_match['team2']}\n"
                            else:
                                message += f"🎫 You have a bye this round\n"
                            message += "Waiting for admin to report results...\n\n"
                        elif team_match['status'] == 'bye':
                            message += f"🎫 You have a bye and advance automatically\n\n"
                    
                    if tournament['status'] == 'complete':
                        message += "Tournament is complete!\n"
                else:
                    message += "🏆 *Tournament will start when all teams arrive*\n\n"
            
            # Add hints information
            hints = challenge.get('hints', [])
            used_hints = self.game_state.get_used_hints(team_name, challenge_id)
            
            if hints:
                message += f"💡 Hints available: {len(hints)}\n"
                message += f"💡 Hints used: {len(used_hints)}/{len(hints)}\n"
                
                if used_hints:
                    message += "\n*Used Hints:*\n"
                    for hint_record in used_hints:
                        hint_idx = hint_record['hint_index']
                        if hint_idx < len(hints):
                            message += f"  • {hints[hint_idx]}\n"
                
                if len(used_hints) < len(hints):
                    penalty_minutes = self.game_state.get_penalty_minutes_per_hint(challenge)
                    message += f"\nUse /hint to get a hint (costs {penalty_minutes} min penalty)\n"
            
            # Don't show submit instructions for tournament challenges
            if verification_method != 'tournament':
                message += "\nUse /submit [answer] to submit this challenge."
        
        # Send image first if configured and challenge is not locked
        if not is_locked:
            image_url = challenge.get('image_url')
            image_path = challenge.get('image_path')
            if image_url or image_path:
                await self.send_image(
                    context=context,
                    chat_id=update.effective_chat.id,
                    image_url=image_url,
                    image_path=image_path,
                    caption=f"📸 Image for Challenge #{challenge_id}"
                )
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def hint_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /hint command."""
        user = update.effective_user
        team_name = self.game_state.get_team_by_user(user.id)
        
        if not team_name:
            await update.message.reply_text("You are not in any team yet! Use /createteam or /jointeam")
            return
        
        team = self.game_state.teams[team_name]
        current_challenge_index = team.get('current_challenge_index', 0)
        
        # Check if all challenges are completed
        if current_challenge_index >= len(self.challenges):
            await update.message.reply_text("🏆 Your team has completed all challenges!")
            return
        
        # Get current challenge
        challenge = self.challenges[current_challenge_index]
        hints = challenge.get('hints', [])
        
        # Check if challenge has hints
        if not hints:
            await update.message.reply_text(
                "💡 No hints are available for this challenge.\n"
                "Good luck! 🍀"
            )
            return
        
        # Get used hints
        used_hints = self.game_state.get_used_hints(team_name, challenge['id'])
        
        # Check if all hints are used
        if len(used_hints) >= len(hints):
            message = "💡 All hints have been used for this challenge:\n\n"
            for i, hint in enumerate(hints):
                message += f"{i+1}. {hint}\n"
            await update.message.reply_text(message)
            return
        
        # Display used hints if any
        if used_hints:
            message = "*Previously Used Hints:*\n"
            for hint_record in used_hints:
                hint_idx = hint_record['hint_index']
                if hint_idx < len(hints):
                    message += f"  • {hints[hint_idx]}\n"
            message += "\n"
        else:
            message = ""
        
        # Ask for confirmation to use next hint
        next_hint_index = len(used_hints)
        hints_remaining = len(hints) - len(used_hints)
        
        message += (
            f"⚠️ *Hint Confirmation*\n\n"
            f"Using a hint will cost your team a *2-minute penalty*.\n"
            f"The penalty is applied when the next challenge is unlocked.\n\n"
            f"Hints remaining: {hints_remaining}/{len(hints)}\n"
            f"Current penalty: {len(used_hints) * 2} minutes\n"
            f"Penalty if you use this hint: {(len(used_hints) + 1) * 2} minutes\n\n"
            f"Do you want to use a hint?"
        )
        
        # Create inline keyboard for confirmation
        keyboard = [
            [
                InlineKeyboardButton("✅ Yes, use hint", callback_data=f"hint_yes_{challenge['id']}_{next_hint_index}"),
                InlineKeyboardButton("❌ No, cancel", callback_data="hint_no")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
    
    async def hint_callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle hint confirmation callbacks."""
        query = update.callback_query
        await query.answer()
        
        user = update.effective_user
        team_name = self.game_state.get_team_by_user(user.id)
        
        if not team_name:
            await query.edit_message_text("You are not in any team!")
            return
        
        # Parse callback data
        callback_data = query.data
        
        if callback_data == "hint_no":
            await query.edit_message_text("❌ Hint request cancelled.")
            return
        
        # Parse hint confirmation: hint_yes_{challenge_id}_{hint_index}
        parts = callback_data.split('_')
        if len(parts) != 4 or parts[0] != 'hint' or parts[1] != 'yes':
            await query.edit_message_text("Invalid request.")
            return
        
        challenge_id = int(parts[2])
        hint_index = int(parts[3])
        
        # Verify this is still the current challenge
        team = self.game_state.teams[team_name]
        current_challenge_index = team.get('current_challenge_index', 0)
        current_challenge = self.challenges[current_challenge_index]
        
        if current_challenge['id'] != challenge_id:
            await query.edit_message_text(
                "❌ This hint is for a different challenge. Your team has moved on!"
            )
            return
        
        # Get hints for the challenge
        hints = current_challenge.get('hints', [])
        
        # Verify hint index is valid
        if hint_index >= len(hints):
            await query.edit_message_text("❌ Invalid hint request.")
            return
        
        # Verify this hint hasn't been used already
        used_hints = self.game_state.get_used_hints(team_name, challenge_id)
        if any(h['hint_index'] == hint_index for h in used_hints):
            await query.edit_message_text("❌ This hint has already been used.")
            return
        
        # Record hint usage
        self.game_state.use_hint(team_name, challenge_id, hint_index, user.id, user.first_name)
        
        # Get the hint text
        hint_text = hints[hint_index]
        
        # Calculate updated penalty
        total_hints_used = len(used_hints) + 1
        total_penalty = total_hints_used * 2
        
        # Edit the confirmation message
        await query.edit_message_text(
            f"✅ Hint revealed! (Penalty: {total_penalty} minutes)\n\n"
            f"💡 *Hint:* {hint_text}",
            parse_mode='Markdown'
        )
        
        # Check if there's an image for this hint
        hint_images = current_challenge.get('hint_images', {})
        hint_image_url = None
        hint_image_path = None
        
        if hint_images:
            # hint_images is a dict with hint index as key
            hint_image_config = hint_images.get(hint_index) or hint_images.get(str(hint_index))
            if hint_image_config:
                # Check if it's a URL or path
                if isinstance(hint_image_config, str):
                    if hint_image_config.startswith('http'):
                        hint_image_url = hint_image_config
                    else:
                        hint_image_path = hint_image_config
        
        # Send hint image to the requesting user if available
        if hint_image_url or hint_image_path:
            await self.send_image(
                context=context,
                chat_id=user.id,
                image_url=hint_image_url,
                image_path=hint_image_path,
                caption=f"📸 Image for Hint #{hint_index + 1}"
            )
        
        # Broadcast hint to all team members
        team_data = self.game_state.teams[team_name]
        broadcast_message = (
            f"💡 *Hint Revealed for Challenge #{challenge_id}*\n\n"
            f"Requested by: {user.first_name}\n"
            f"Challenge: {current_challenge['name']}\n\n"
            f"*Hint:* {hint_text}\n\n"
            f"⏱️ Penalty: {total_penalty} minutes total"
        )
        
        sent_to_users = set()
        for member in team_data['members']:
            member_id = member['id']
            # Skip the user who requested (they already got the message)
            if member_id == user.id or member_id in sent_to_users:
                continue
            
            try:
                # Send image to team members if available
                if hint_image_url or hint_image_path:
                    await self.send_image(
                        context=context,
                        chat_id=member_id,
                        image_url=hint_image_url,
                        image_path=hint_image_path,
                        caption=f"📸 Image for Hint #{hint_index + 1}"
                    )
                
                # Send text broadcast
                await context.bot.send_message(
                    chat_id=member_id,
                    text=broadcast_message,
                    parse_mode='Markdown'
                )
                sent_to_users.add(member_id)
            except Exception as e:
                logger.error(f"Failed to send hint broadcast to user {member_id}: {e}")

    
    async def submit_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /submit command."""
        # Check if game has started
        if not self.game_state.game_started:
            await update.message.reply_text("The game hasn't started yet!")
            return
        
        if self.game_state.game_ended:
            await update.message.reply_text("The game has ended!")
            return
        
        user = update.effective_user
        team_name = self.game_state.get_team_by_user(user.id)
        
        if not team_name:
            await update.message.reply_text("You are not in any team!")
            return
        
        # Check if a timeout just expired and broadcast if needed
        await self.check_and_broadcast_unlocked_challenge(context, team_name)
        
        # Get current challenge that should be completed
        team = self.game_state.teams[team_name]
        current_challenge_index = team.get('current_challenge_index', 0)
        
        # Always use the current challenge
        if current_challenge_index >= len(self.challenges):
            await update.message.reply_text("🏆 Your team has completed all challenges!")
            return
        
        challenge = self.challenges[current_challenge_index]
        challenge_id = challenge['id']
        
        # Check if challenge is still locked due to penalty
        if current_challenge_index > 0:  # Not the first challenge
            previous_challenge = self.challenges[current_challenge_index - 1]
            unlock_time_str = self.game_state.get_challenge_unlock_time(team_name, challenge_id, previous_challenge)
            if unlock_time_str:
                unlock_time = datetime.fromisoformat(unlock_time_str)
                now = datetime.now()
                
                if now < unlock_time:
                    # Challenge is still locked
                    time_remaining = unlock_time - now
                    minutes = int(time_remaining.total_seconds() // 60)
                    seconds = int(time_remaining.total_seconds() % 60)
                    
                    previous_challenge_id = challenge_id - 1
                    hint_count = self.game_state.get_hint_count(team_name, previous_challenge_id)
                    
                    await update.message.reply_text(
                        f"⏱️ *Challenge Locked - Penalty Timer*\n\n"
                        f"Your team used {hint_count} hint(s) on the previous challenge.\n"
                        f"You must wait before this challenge is unlocked.\n\n"
                        f"⏳ Time remaining: {minutes}m {seconds}s\n\n"
                        f"The challenge will be available at:\n"
                        f"{unlock_time.strftime('%H:%M:%S')}",
                        parse_mode='Markdown'
                    )
                    return
        
        # Check if photo verification is required and not yet done
        if self.requires_photo_verification(challenge, current_challenge_index):
            photo_verifications = team.get('photo_verifications', {})
            if str(challenge_id) not in photo_verifications:
                # Photo verification not done yet - cannot submit answer
                message = (
                    f"📷 *Photo Verification Required*\n\n"
                    f"*Challenge #{challenge_id}: {challenge['name']}*\n\n"
                    f"Before you can submit an answer to this challenge, you need to send a photo of your team at the challenge location.\n\n"
                    f"📍 Location: {challenge['location']}\n\n"
                    f"*Instructions:*\n"
                    f"1. Go to the challenge location\n"
                    f"2. Take a photo of your team there\n"
                    f"3. Send the photo to this bot\n"
                    f"4. Wait for admin approval\n"
                    f"5. After approval, you can submit your answer\n\n"
                    f"⏱️ Note: The timeout/penalty timer will only start after your photo is approved."
                )
                await update.message.reply_text(message, parse_mode='Markdown')
                return
        
        # Get verification method
        verification = challenge.get('verification', {})
        method = verification.get('method', 'photo')
        
        # Handle different verification methods
        if method == 'answer':
            # Text answer verification
            if not context.args:
                # Store that we're waiting for answer
                if 'waiting_for' not in context.user_data:
                    context.user_data['waiting_for'] = {}
                context.user_data['waiting_for']['command'] = 'submit'
                context.user_data['waiting_for']['challenge_id'] = challenge_id
                await update.message.reply_text(
                    f"Please provide your answer to the challenge:\n"
                    f"*{challenge['name']}*\n\n"
                    f"Type your answer below:",
                    parse_mode='Markdown'
                )
                return
            
            user_answer = ' '.join(context.args)
            
            # Check if this is a checklist challenge
            verification = challenge.get('verification', {})
            is_checklist = 'checklist_items' in verification
            
            result = self.verify_answer(challenge, user_answer, team_name)
            
            if result['correct']:
                # Answer is correct (or all checklist items completed)
                submission_data = {
                    'type': 'answer',
                    'answer': user_answer,
                    'timestamp': datetime.now().isoformat(),
                    'submitted_by': user.id
                }
                
                if is_checklist:
                    submission_data['checklist_completed'] = True
                
                if self.game_state.complete_challenge(team_name, challenge_id, len(self.challenges), submission_data):
                    team = self.game_state.teams[team_name]
                    completed = len(team['completed_challenges'])
                    total = len(self.challenges)
                    
                    response = (
                        f"✅ Correct! Team '{team_name}' completed:\n"
                        f"*{challenge['name']}*\n"
                        f"Progress: {completed}/{total} challenges"
                    )
                    
                    # Check if team finished all challenges
                    if team.get('finish_time'):
                        response += f"\n\n🏆 *CONGRATULATIONS!* 🏆\n"
                        response += f"Your team finished the race!\n"
                        response += f"Finish time: {team['finish_time']}"
                    
                    await update.message.reply_text(response, parse_mode='Markdown')
                    
                    # Send custom success message if configured
                    await self.send_success_message_if_configured(challenge, user.id, update=update)
                    
                    # Prepare penalty information for broadcast
                    penalty_info = None
                    photo_verification_needed = False
                    
                    if not team.get('finish_time'):
                        # Check if there's a penalty for the next challenge
                        next_challenge_id = challenge_id + 1
                        unlock_time_str = self.game_state.get_challenge_unlock_time(team_name, next_challenge_id, challenge)
                        if unlock_time_str:
                            unlock_time = datetime.fromisoformat(unlock_time_str)
                            hint_count = self.game_state.get_hint_count(team_name, challenge_id)
                            penalty_minutes_per_hint = self.game_state.get_penalty_minutes_per_hint(challenge)
                            penalty_minutes = hint_count * penalty_minutes_per_hint
                            penalty_info = {
                                'hint_count': hint_count,
                                'penalty_minutes': penalty_minutes,
                                'unlock_time': unlock_time
                            }
                        
                        # Check if photo verification is needed for next challenge
                        if next_challenge_id <= len(self.challenges):
                            next_challenge_index = team.get('current_challenge_index', 0)
                            next_challenge = self.challenges[next_challenge_index]
                            if self.requires_photo_verification(next_challenge, next_challenge_index):
                                photo_verifications = team.get('photo_verifications', {})
                                if str(next_challenge_id) not in photo_verifications:
                                    photo_verification_needed = True
                    
                    # Broadcast completion to team and admin
                    await self.broadcast_challenge_completion(
                        context, team_name, challenge_id, challenge['name'],
                        user.id, user.first_name, completed, total,
                        penalty_info, photo_verification_needed
                    )
                    
                    # After completion message is sent, broadcast next challenge if no timeout
                    if not team.get('finish_time'):
                        next_challenge_id = challenge_id + 1
                        unlock_time_str = self.game_state.get_challenge_unlock_time(team_name, next_challenge_id, challenge)
                        if not unlock_time_str:
                            # No timeout - broadcast next challenge to all team members (excluding submitter)
                            await self.broadcast_current_challenge(context, team_name, user.id)
                else:
                    await update.message.reply_text("Error completing challenge. Please try again.")
            elif result['partial']:
                # Partial match for checklist items
                checklist_items = verification.get('checklist_items', [])
                progress = self.game_state.get_checklist_progress(team_name, challenge_id)
                
                # Build progress display - only show completed items
                progress_text = "📝 *Checklist Progress*\n\n"
                completed_count = 0
                completed_items = []
                for item in checklist_items:
                    if progress.get(item, False):
                        completed_items.append(item)
                        completed_count += 1
                
                if completed_items:
                    for item in completed_items:
                        progress_text += f"✅ {item}\n"
                    progress_text += "\n"
                
                progress_text += f"*Progress:* {completed_count}/{len(checklist_items)} items completed\n\n"
                
                if result['matched_items']:
                    progress_text += f"✅ Added: {', '.join(result['matched_items'])}\n\n"
                
                progress_text += "Keep submitting answers to complete remaining items!"
                
                await update.message.reply_text(progress_text, parse_mode='Markdown')
            else:
                # No match
                if is_checklist:
                    # Show checklist progress - only show completed items
                    checklist_items = verification.get('checklist_items', [])
                    progress = self.game_state.get_checklist_progress(team_name, challenge_id)
                    
                    progress_text = "❌ No match found.\n\n📝 *Checklist Progress*\n\n"
                    completed_count = 0
                    completed_items = []
                    for item in checklist_items:
                        if progress.get(item, False):
                            completed_items.append(item)
                            completed_count += 1
                    
                    if completed_items:
                        for item in completed_items:
                            progress_text += f"✅ {item}\n"
                        progress_text += "\n"
                    
                    progress_text += f"*Progress:* {completed_count}/{len(checklist_items)} items completed"
                    await update.message.reply_text(progress_text, parse_mode='Markdown')
                else:
                    await update.message.reply_text(
                        "❌ Incorrect answer. Please try again!\n"
                        f"Hint: Make sure your answer matches what's being asked."
                    )
        
        elif method == 'photo':
            # Photo verification - wait for photo
            # Store pending submission in context
            if 'pending_submissions' not in context.bot_data:
                context.bot_data['pending_submissions'] = {}
            
            context.bot_data['pending_submissions'][user.id] = {
                'team_name': team_name,
                'challenge_id': challenge_id,
                'challenge_name': challenge['name']
            }
            
            await update.message.reply_text(
                f"📷 Please send a photo for:\n"
                f"*{challenge['name']}*\n\n"
                f"The photo will be reviewed by the admin.",
                parse_mode='Markdown'
            )
        
        elif method == 'tournament':
            # Tournament challenges don't accept submissions from teams
            await update.message.reply_text(
                f"⚠️ *Submission Not Recognized*\n\n"
                f"This is a tournament challenge. You cannot submit an answer.\n"
                f"The admin will report tournament results using `/tournamentwin`.\n\n"
                f"Use `/current` to see your tournament match status.",
                parse_mode='Markdown'
            )
        
        else:
            # Default: manual verification by admin
            await update.message.reply_text(
                f"Submission recorded for *{challenge['name']}*.\n"
                f"Waiting for admin verification...",
                parse_mode='Markdown'
            )
    
    
    async def start_game_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /startgame command (admin only)."""
        user = update.effective_user
        if not self.is_admin(user.id):
            await update.message.reply_text("Only admins can start the game!")
            return
        
        if self.game_state.game_started:
            await update.message.reply_text("Game has already started!")
            return
        
        self.game_state.start_game()
        
        # Prepare the game started message with more information about relevant commands
        game_start_message = (
            "🏁 *THE GAME HAS STARTED!* 🏁\n\n"
            "The race is on! Complete challenges to win.\n\n"
            "📍 *Key Commands:*\n"
            "• `/current` - View your current challenge\n"
            "• `/submit [answer]` - Submit your answer\n"
            "• `/challenges` - See all challenges progress\n"
            "• `/hint` - Get a hint (penalty, default 2 min)\n"
            "• `/myteam` - View your team info\n\n"
            "Good luck! 🎯"
        )
        
        # Send message to admin
        await update.message.reply_text(game_start_message, parse_mode='Markdown')
        
        # Broadcast message to all team members and their current challenge
        sent_to_users = set()  # Track users to avoid duplicate messages
        admin_is_player = False  # Track if admin is also a player
        
        for team_name, team_data in self.game_state.teams.items():
            for member in team_data['members']:
                user_id = member['id']
                # Check if admin is also a player
                if user_id == user.id:
                    admin_is_player = True
                # Skip if already sent to this user
                if user_id in sent_to_users:
                    continue
                
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=game_start_message,
                        parse_mode='Markdown'
                    )
                    sent_to_users.add(user_id)
                except Exception as e:
                    logger.error(f"Failed to send game start message to user {user_id}: {e}")
                    # Continue sending to other users even if one fails
        
        # Broadcast current challenge to all teams (excluding admin only if admin is not a player)
        for team_name in self.game_state.teams.keys():
            exclude_user_id = None if admin_is_player else user.id
            await self.broadcast_current_challenge(context, team_name, exclude_user_id)
    
    async def end_game_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /endgame command (admin only)."""
        user = update.effective_user
        if not self.is_admin(user.id):
            await update.message.reply_text("Only admins can end the game!")
            return
        
        if self.game_state.game_ended:
            await update.message.reply_text("Game has already ended!")
            return
        
        self.game_state.end_game()
        
        # Get final leaderboard
        leaderboard = self.game_state.get_leaderboard()
        message = "🏁 *GAME OVER!* 🏁\n\n*Final Standings:*\n\n"
        
        finished_teams = [t for t in leaderboard if t[2] is not None]
        racing_teams = [t for t in leaderboard if t[2] is None]
        
        if finished_teams:
            message += "*Finished Teams:*\n"
            for i, (team_name, completed, finish_time) in enumerate(finished_teams, 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                message += f"{medal} *{team_name}* - Completed all challenges!\n"
            message += "\n"
        
        if racing_teams:
            message += "*Did Not Finish:*\n"
            for team_name, completed, _ in racing_teams:
                total = len(self.challenges)
                message += f"   *{team_name}* - {completed}/{total} challenges\n"
            message += "\n"
        
        message += "🎉 Congratulations to all teams! 🎉"
        
        # Send message to admin
        await update.message.reply_text(message, parse_mode='Markdown')
        
        # Broadcast message to all team members
        sent_to_users = set()  # Track users to avoid duplicate messages
        for team_name, team_data in self.game_state.teams.items():
            for member in team_data['members']:
                user_id = member['id']
                # Skip if already sent (e.g., admin is also a team member)
                if user_id in sent_to_users or user_id == user.id:
                    continue
                
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=message,
                        parse_mode='Markdown'
                    )
                    sent_to_users.add(user_id)
                except Exception as e:
                    logger.error(f"Failed to send game end message to user {user_id}: {e}")
                    # Continue sending to other users even if one fails
    
    async def reset_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /reset command (admin only)."""
        user = update.effective_user
        if not self.is_admin(user.id):
            await update.message.reply_text("Only admins can reset the game!")
            return
        
        self.game_state.reset_game()
        await update.message.reply_text("✅ Game has been reset! All data cleared.")
    
    async def teams_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /teams command - shows teams without progress information."""
        if not self.game_state.teams:
            await update.message.reply_text("No teams created yet!")
            return
        
        message = "👥 *Teams* 👥\n\n"
        
        for team_name, team_data in self.game_state.teams.items():
            captain_name = team_data.get('captain_name', 'Unknown')
            members_names = [m['name'] for m in team_data['members']]
            other_members = [name for name in members_names if name != captain_name]
            
            message += f"*{team_name}*\n"
            message += f"  👑 Captain: {captain_name}\n"
            
            if other_members:
                message += f"  👥 Members: {', '.join(other_members)}\n"
            else:
                message += f"  👥 Members: None\n"
            
            message += f"  Total: {len(team_data['members'])}/{self.config['game']['max_team_size']}\n\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def teamstatus_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /teamstatus command (admin only) - detailed team info."""
        user = update.effective_user
        if not self.is_admin(user.id):
            await update.message.reply_text("Only admins can view detailed team status!")
            return
        
        if not self.game_state.teams:
            await update.message.reply_text("No teams created yet!")
            return
        
        message = "📊 *Detailed Team Status* 📊\n\n"
        total_challenges = len(self.challenges)
        
        for team_name, team_data in self.game_state.teams.items():
            completed = len(team_data['completed_challenges'])
            current_challenge = team_data.get('current_challenge_index', 0) + 1
            members_list = ', '.join([m['name'] for m in team_data['members']])
            
            message += f"*{team_name}*\n"
            message += f"  👥 Members ({len(team_data['members'])}): {members_list}\n"
            message += f"  👑 Captain: {team_data['captain_name']}\n"
            message += f"  📊 Progress: {completed}/{total_challenges}\n"
            
            if team_data.get('finish_time'):
                message += f"  ✅ Status: FINISHED at {team_data['finish_time']}\n"
            else:
                message += f"  🎯 Current Challenge: #{current_challenge}\n"
            
            message += "\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def editteam_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /editteam command (admin only)."""
        user = update.effective_user
        if not self.is_admin(user.id):
            await update.message.reply_text("Only admins can edit teams!")
            return
        
        if len(context.args) < 2:
            await update.message.reply_text(
                "Usage: /editteam <old_team_name> <new_team_name>\n"
                "Example: /editteam \"Team A\" \"Super Team A\""
            )
            return
        
        old_name = context.args[0]
        new_name = ' '.join(context.args[1:])
        
        if self.game_state.update_team(old_name, new_team_name=new_name):
            await update.message.reply_text(f"✅ Team renamed from '{old_name}' to '{new_name}'")
        else:
            await update.message.reply_text(f"❌ Failed to rename team. Team '{old_name}' may not exist or '{new_name}' already exists.")
    
    async def addteam_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /addteam command (admin only)."""
        user = update.effective_user
        if not self.is_admin(user.id):
            await update.message.reply_text("Only admins can add teams!")
            return
        
        if not context.args:
            # Store that we're waiting for team name
            if 'waiting_for' not in context.user_data:
                context.user_data['waiting_for'] = {}
            context.user_data['waiting_for']['command'] = 'addteam'
            await update.message.reply_text(
                "Please provide the team name:\n"
                "What is the name of the team to add?"
            )
            return
        
        team_name = ' '.join(context.args)
        
        # Check max teams
        if len(self.game_state.teams) >= self.config['game']['max_teams']:
            await update.message.reply_text("Maximum number of teams reached!")
            return
        
        # Create team with admin as temporary captain (ID: 0)
        if self.game_state.create_team(team_name, 0, "Admin"):
            await update.message.reply_text(
                f"✅ Team '{team_name}' created successfully!\n"
                f"Note: This is an admin-created team. You can add members using:\n"
                f"Players can join with /jointeam {team_name}"
            )
        else:
            await update.message.reply_text(f"Team '{team_name}' already exists!")
    
    async def removeteam_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /removeteam command (admin only)."""
        user = update.effective_user
        if not self.is_admin(user.id):
            await update.message.reply_text("Only admins can remove teams!")
            return
        
        if not context.args:
            # Store that we're waiting for team name
            if 'waiting_for' not in context.user_data:
                context.user_data['waiting_for'] = {}
            context.user_data['waiting_for']['command'] = 'removeteam'
            await update.message.reply_text(
                "Please provide the team name:\n"
                "Which team would you like to remove?"
            )
            return
        
        team_name = ' '.join(context.args)
        
        if self.game_state.remove_team(team_name):
            await update.message.reply_text(f"✅ Team '{team_name}' has been removed.")
        else:
            await update.message.reply_text(f"❌ Team '{team_name}' not found!")
    
    async def contact_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /contact command - directs users to contact the admin."""
        if self.admin_id is None:
            await update.message.reply_text(
                "❌ No admin is configured for this bot.\n"
                "Please contact the bot operator."
            )
            return
        
        # Create a deep link to start a chat with the admin
        admin_link = f"tg://user?id={self.admin_id}"
        
        await update.message.reply_text(
            f"📞 *Contact Admin*\n\n"
            f"To contact the bot admin, click the link below:\n"
            f"[Contact Admin]({admin_link})\n\n"
            f"Or search for the admin using their user ID: `{self.admin_id}`",
            parse_mode='Markdown'
        )
    
    async def photo_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle photo submissions for challenges and photo verifications."""
        user = update.effective_user
        
        # Check if user has a pending photo submission
        if 'pending_submissions' not in context.bot_data:
            context.bot_data['pending_submissions'] = {}
        
        if user.id in context.bot_data['pending_submissions']:
            # This is a photo submission for a challenge
            await self._handle_photo_submission(update, context)
            return
        
        # Check if this might be a photo verification for location arrival or challenge submission
        team_name = self.game_state.get_team_by_user(user.id)
        if not team_name:
            # No team, ignore the photo
            return
        
        # Check if game is active
        if not self.game_state.game_started or self.game_state.game_ended:
            # Game not active, ignore the photo
            return
        
        # Get current challenge
        team = self.game_state.teams[team_name]
        current_challenge_index = team.get('current_challenge_index', 0)
        
        # Check if all challenges are completed
        if current_challenge_index >= len(self.challenges):
            return
        
        current_challenge = self.challenges[current_challenge_index]
        challenge_id = current_challenge['id']
        
        # Check if photo verification is required for this challenge
        if self.requires_photo_verification(current_challenge, current_challenge_index):
            # Check if photo verification already done for this challenge
            photo_verifications = team.get('photo_verifications', {})
            if str(challenge_id) not in photo_verifications:
                # Photo verification not done yet - this is a location verification photo
                
                # Check if there's already a pending verification for this team/challenge
                pending_verifications = self.game_state.get_pending_photo_verifications()
                for verification in pending_verifications.values():
                    if verification['team_name'] == team_name and verification['challenge_id'] == challenge_id:
                        await update.message.reply_text(
                            f"⏳ You already have a pending photo verification for this challenge.\n"
                            f"Please wait for admin approval."
                        )
                        return
                
                # Get the photo
                photo = update.message.photo[-1]  # Get highest resolution
                
                # Store the photo verification as pending
                verification_id = self.game_state.add_pending_photo_verification(
                    team_name, challenge_id, photo.file_id, user.id, user.first_name
                )
                
                # Notify the user that photo was submitted for verification
                response = (
                    f"📷 *Photo Verification Submitted*\n\n"
                    f"Your photo for arriving at Challenge #{challenge_id} has been sent to the admin for verification.\n\n"
                    f"The challenge details will be revealed once the admin approves your photo.\n"
                    f"You will be notified when approved."
                )
                
                await update.message.reply_text(response, parse_mode='Markdown')
                
                # Send photo to admin for verification with approval/rejection buttons
                if self.admin_id:
                    try:
                        keyboard = [
                            [
                                InlineKeyboardButton("✅ Approve", callback_data=f"verify_approve_{verification_id}"),
                                InlineKeyboardButton("❌ Reject", callback_data=f"verify_reject_{verification_id}")
                            ]
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        
                        challenge_name = current_challenge.get('name', f'Challenge #{challenge_id}')
                        
                        await context.bot.send_photo(
                            chat_id=self.admin_id,
                            photo=photo.file_id,
                            caption=(
                                f"📷 *Photo Verification - Location Arrival*\n"
                                f"Team: {team_name}\n"
                                f"Challenge #{challenge_id}: {challenge_name}\n"
                                f"Submitted by: {user.first_name}\n\n"
                                f"Approve to reveal the challenge to the team.\n"
                                f"Verification ID: `{verification_id}`"
                            ),
                            parse_mode='Markdown',
                            reply_markup=reply_markup
                        )
                    except Exception as e:
                        logger.error(f"Failed to send photo verification to admin: {e}")
                
                return
        
        # If we reach here, photo verification is either disabled or already done
        # Check if current challenge requires a photo submission
        verification = current_challenge.get('verification', {})
        if verification.get('method') == 'photo':
            # This is a photo challenge - treat the photo as a submission
            # Store in pending_submissions and call _handle_photo_submission
            if 'pending_submissions' not in context.bot_data:
                context.bot_data['pending_submissions'] = {}
            
            context.bot_data['pending_submissions'][user.id] = {
                'team_name': team_name,
                'challenge_id': challenge_id,
                'challenge_name': current_challenge['name']
            }
            
            await self._handle_photo_submission(update, context)
            return
        elif verification.get('method') == 'answer':
            # Photo sent but current challenge expects a text answer
            expected_format = self.get_expected_answer_format(current_challenge)
            error_message = self.get_format_mismatch_message(expected_format, current_challenge)
            await update.message.reply_text(error_message, parse_mode='Markdown')
            return
        
        # Photo sent but current challenge doesn't require a photo and isn't an answer challenge
        # Ignore it silently (user might be sending unrelated photos)
    
    async def _handle_photo_submission(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle photo submission for challenge completion."""
        user = update.effective_user
        
        pending = context.bot_data['pending_submissions'][user.id]
        team_name = pending['team_name']
        challenge_id = pending['challenge_id']
        challenge_name = pending['challenge_name']
        
        # Get the photo
        photo = update.message.photo[-1]  # Get highest resolution
        
        # Store the submission as pending (not auto-completing)
        submission_id = self.game_state.add_pending_photo_submission(
            team_name, challenge_id, photo.file_id, user.id, user.first_name
        )
        
        # Notify the user that photo was submitted and is pending review
        response = (
            f"📷 Photo submitted for:\n"
            f"*{challenge_name}*\n\n"
            f"Your photo has been sent to the admin for review.\n"
            f"You will be notified once it's approved."
        )
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
        # Send photo to admin for review with approval/rejection buttons
        if self.admin_id:
            try:
                keyboard = [
                    [
                        InlineKeyboardButton("✅ Approve", callback_data=f"approve_{submission_id}"),
                        InlineKeyboardButton("❌ Reject", callback_data=f"reject_{submission_id}")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await context.bot.send_photo(
                    chat_id=self.admin_id,
                    photo=photo.file_id,
                    caption=(
                        f"📷 *Photo Submission - Challenge Completion*\n"
                        f"Team: {team_name}\n"
                        f"Challenge #{challenge_id}: {challenge_name}\n"
                        f"Submitted by: {user.first_name}\n\n"
                        f"Submission ID: `{submission_id}`"
                    ),
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            except Exception as e:
                logger.error(f"Failed to send photo to admin: {e}")
        
        # Remove pending submission
        del context.bot_data['pending_submissions'][user.id]

    
    async def photo_verification_callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle photo verification approval/rejection callbacks from admin."""
        query = update.callback_query
        await query.answer()
        
        user = update.effective_user
        
        # Only admin can approve/reject
        if not self.is_admin(user.id):
            await query.edit_message_caption(
                caption=query.message.caption + "\n\n❌ Only admins can approve/reject verifications.",
                parse_mode='Markdown'
            )
            return
        
        # Parse callback data: verify_approve_{verification_id} or verify_reject_{verification_id}
        callback_data = query.data
        parts = callback_data.split('_', 2)
        
        if len(parts) != 3:
            await query.edit_message_caption(
                caption=query.message.caption + "\n\n❌ Invalid request.",
                parse_mode='Markdown'
            )
            return
        
        action = parts[1]  # approve or reject
        verification_id = parts[2]
        
        # Get verification details
        verification = self.game_state.get_photo_verification_by_id(verification_id)
        
        if not verification:
            await query.edit_message_caption(
                caption=query.message.caption + "\n\n❌ Verification not found.",
                parse_mode='Markdown'
            )
            return
        
        if verification.get('status') != 'pending':
            status = verification.get('status', 'unknown')
            await query.edit_message_caption(
                caption=query.message.caption + f"\n\n⚠️ This verification has already been {status}.",
                parse_mode='Markdown'
            )
            return
        
        team_name = verification['team_name']
        challenge_id = verification['challenge_id']
        challenge = self.challenges[challenge_id - 1]
        challenge_name = challenge['name']
        user_id = verification['user_id']
        user_name = verification['user_name']
        
        if action == 'approve':
            # Approve the verification
            if self.game_state.approve_photo_verification(verification_id):
                # Check if there's an active timeout penalty for this challenge
                team = self.game_state.teams[team_name]
                previous_challenge_index = challenge_id - 2  # challenge_id is 1-based, index is 0-based
                previous_challenge = self.challenges[previous_challenge_index] if previous_challenge_index >= 0 else None
                unlock_time_str = self.game_state.get_challenge_unlock_time(team_name, challenge_id, previous_challenge)
                
                should_broadcast = True
                timeout_message = ""
                admin_status = "Challenge Revealed"
                
                if unlock_time_str:
                    unlock_time = datetime.fromisoformat(unlock_time_str)
                    now = datetime.now()
                    
                    if now < unlock_time:
                        # Timeout is still active - don't broadcast challenge yet
                        should_broadcast = False
                        time_remaining = unlock_time - now
                        minutes = int(time_remaining.total_seconds() / 60)
                        seconds = int(time_remaining.total_seconds() % 60)
                        timeout_message = (
                            f"\n\n⏱️ *Timeout Active*\n"
                            f"Challenge will be revealed in {minutes}m {seconds}s.\n"
                            f"Use /current to check when it's available."
                        )
                        admin_status = f"Timeout Active ({minutes}m {seconds}s remaining)"
                
                # Update admin message
                await query.edit_message_caption(
                    caption=query.message.caption + f"\n\n✅ *APPROVED - {admin_status}*",
                    parse_mode='Markdown'
                )
                
                # Broadcast the challenge to all team members (now that photo is approved)
                # Only if timeout has expired or there's no timeout
                if should_broadcast:
                    await self.broadcast_current_challenge(context, team_name)
                
                # Notify team members that photo was approved
                team_members = team['members']
                for member in team_members:
                    try:
                        if should_broadcast:
                            response = (
                                f"✅ *Photo Verified!*\n\n"
                                f"Your location photo for Challenge #{challenge_id} has been approved!\n\n"
                                f"The challenge is now revealed. Check your messages above for details.\n"
                                f"Use /current to see the challenge again."
                            )
                        else:
                            response = (
                                f"✅ *Photo Verified!*\n\n"
                                f"Your location photo for Challenge #{challenge_id} has been approved!"
                                f"{timeout_message}"
                            )
                        
                        await context.bot.send_message(
                            chat_id=member['id'],
                            text=response,
                            parse_mode='Markdown'
                        )
                    except Exception as e:
                        logger.error(f"Failed to notify team member {member['id']}: {e}")
            else:
                await query.edit_message_caption(
                    caption=query.message.caption + "\n\n❌ Failed to approve verification.",
                    parse_mode='Markdown'
                )
        
        elif action == 'reject':
            # Reject the verification
            if self.game_state.reject_photo_verification(verification_id):
                # Update admin message
                await query.edit_message_caption(
                    caption=query.message.caption + "\n\n❌ *REJECTED*",
                    parse_mode='Markdown'
                )
                
                # Notify the submitter
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=(
                            f"❌ *Photo Verification Rejected*\n\n"
                            f"Your location photo for Challenge #{challenge_id} was rejected.\n"
                            f"Please take a new photo at the correct location and send it again."
                        ),
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.error(f"Failed to notify user {user_id}: {e}")
            else:
                await query.edit_message_caption(
                    caption=query.message.caption + "\n\n❌ Failed to reject verification.",
                    parse_mode='Markdown'
                )
        else:
            await query.edit_message_caption(
                caption=query.message.caption + "\n\n❌ Invalid action.",
                parse_mode='Markdown'
            )

    async def photo_approval_callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle photo approval/rejection callbacks from admin."""
        query = update.callback_query
        await query.answer()
        
        user = update.effective_user
        
        # Only admin can approve/reject
        if not self.is_admin(user.id):
            await query.edit_message_caption(
                caption=query.message.caption + "\n\n❌ Only admins can approve/reject submissions.",
                parse_mode='Markdown'
            )
            return
        
        # Parse callback data: approve_{submission_id} or reject_{submission_id}
        callback_data = query.data
        parts = callback_data.split('_', 1)
        
        if len(parts) != 2:
            await query.edit_message_caption(
                caption=query.message.caption + "\n\n❌ Invalid request.",
                parse_mode='Markdown'
            )
            return
        
        action = parts[0]
        submission_id = parts[1]
        
        # Get submission details
        submission = self.game_state.get_submission_by_id(submission_id)
        
        if not submission:
            await query.edit_message_caption(
                caption=query.message.caption + "\n\n❌ Submission not found.",
                parse_mode='Markdown'
            )
            return
        
        if submission.get('status') != 'pending':
            status = submission.get('status', 'unknown')
            await query.edit_message_caption(
                caption=query.message.caption + f"\n\n⚠️ This submission has already been {status}.",
                parse_mode='Markdown'
            )
            return
        
        team_name = submission['team_name']
        challenge_id = submission['challenge_id']
        challenge = self.challenges[challenge_id - 1]
        challenge_name = challenge['name']
        user_id = submission['user_id']
        user_name = submission['user_name']
        
        # Get photos_required from challenge verification config
        verification = challenge.get('verification', {})
        photos_required = verification.get('photos_required', 1)
        
        if action == 'approve':
            # Approve the submission
            if self.game_state.approve_photo_submission(submission_id, len(self.challenges), photos_required):
                team = self.game_state.teams[team_name]
                completed = len(team['completed_challenges'])
                total = len(self.challenges)
                
                # Get current photo count
                current_photo_count = self.game_state.get_photo_submission_count(team_name, challenge_id)
                challenge_completed = current_photo_count >= photos_required
                
                # Update admin message with photo count info
                if photos_required > 1:
                    approval_msg = f"\n\n✅ *APPROVED* ({current_photo_count}/{photos_required} photos)"
                    if challenge_completed:
                        approval_msg += " - Challenge Complete! ✅"
                else:
                    approval_msg = "\n\n✅ *APPROVED*"
                
                await query.edit_message_caption(
                    caption=query.message.caption + approval_msg,
                    parse_mode='Markdown'
                )
                
                # Check if there's a penalty for the next challenge
                has_timeout = False
                if not team.get('finish_time'):
                    next_challenge_id = challenge_id + 1
                    unlock_time_str = self.game_state.get_challenge_unlock_time(team_name, next_challenge_id, challenge)
                    has_timeout = unlock_time_str is not None
                
                # Notify submitter that photo was approved
                try:
                    if challenge_completed:
                        # Challenge is complete
                        response = (
                            f"✅ *Photo Approved!*\n\n"
                            f"Your photo for *{challenge_name}* has been approved!\n"
                        )
                        
                        if photos_required > 1:
                            response += f"📷 All {photos_required} photos submitted!\n\n"
                        
                        response += f"Progress: {completed}/{total} challenges"
                    else:
                        # More photos needed
                        response = (
                            f"✅ *Photo Approved!*\n\n"
                            f"Your photo for *{challenge_name}* has been approved!\n"
                            f"📷 Photos submitted: {current_photo_count}/{photos_required}\n\n"
                            f"⚠️ Please submit {photos_required - current_photo_count} more photo(s) to complete this challenge."
                        )
                    
                    # Check if team finished (only if challenge is complete)
                    if challenge_completed and team.get('finish_time'):
                        response += f"\n\n🏆 *CONGRATULATIONS!* 🏆\n"
                        response += f"Your team finished the race!\n"
                        response += f"Finish time: {team['finish_time']}"
                    
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=response,
                        parse_mode='Markdown'
                    )
                    
                    # Send custom success message if configured (only if challenge is complete)
                    if challenge_completed:
                        await self.send_success_message_if_configured(challenge, user_id, context=context)
                except Exception as e:
                    logger.error(f"Failed to notify submitter {user_id}: {e}")
                
                # Only broadcast and prepare for next challenge if this challenge is complete
                if challenge_completed:
                    # Prepare penalty information for broadcast
                    penalty_info = None
                    photo_verification_needed = False
                    
                    if not team.get('finish_time'):
                        # Check for hint penalty
                        next_challenge_id = challenge_id + 1
                        unlock_time_str = self.game_state.get_challenge_unlock_time(team_name, next_challenge_id, challenge)
                        if unlock_time_str:
                            unlock_time = datetime.fromisoformat(unlock_time_str)
                            hint_count = self.game_state.get_hint_count(team_name, challenge_id)
                            penalty_minutes_per_hint = self.game_state.get_penalty_minutes_per_hint(challenge)
                            penalty_minutes = hint_count * penalty_minutes_per_hint
                            penalty_info = {
                                'hint_count': hint_count,
                                'penalty_minutes': penalty_minutes,
                                'unlock_time': unlock_time
                            }
                        
                        # Check if photo verification is needed for next challenge
                        if next_challenge_id <= len(self.challenges):
                            next_challenge_index = team.get('current_challenge_index', 0)
                            next_challenge = self.challenges[next_challenge_index]
                            if self.requires_photo_verification(next_challenge, next_challenge_index):
                                photo_verifications = team.get('photo_verifications', {})
                                if str(next_challenge_id) not in photo_verifications:
                                    photo_verification_needed = True
                    
                    # Broadcast completion to team and admin (excluding submitter)
                    await self.broadcast_challenge_completion(
                        context, team_name, challenge_id, challenge_name,
                        user_id, user_name, completed, total,
                        penalty_info, photo_verification_needed
                    )
                    
                    # After completion message is sent, broadcast next challenge if no timeout
                    # Only do this if the challenge is complete
                    if not has_timeout and not team.get('finish_time'):
                        await self.broadcast_current_challenge(context, team_name, user_id)
            else:
                await query.edit_message_caption(
                    caption=query.message.caption + "\n\n❌ Failed to approve submission.",
                    parse_mode='Markdown'
                )
        
        elif action == 'reject':
            # Reject the submission
            if self.game_state.reject_photo_submission(submission_id):
                # Update admin message
                await query.edit_message_caption(
                    caption=query.message.caption + "\n\n❌ *REJECTED*",
                    parse_mode='Markdown'
                )
                
                # Notify the submitter
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=(
                            f"❌ *Photo Rejected*\n\n"
                            f"Your photo for *{challenge_name}* was rejected.\n"
                            f"Please submit a new photo using `/submit`."
                        ),
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.error(f"Failed to notify user {user_id}: {e}")
            else:
                await query.edit_message_caption(
                    caption=query.message.caption + "\n\n❌ Failed to reject submission.",
                    parse_mode='Markdown'
                )
        else:
            await query.edit_message_caption(
                caption=query.message.caption + "\n\n❌ Invalid action.",
                parse_mode='Markdown'
            )

    async def approve_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /approve command (admin only) - approve pending photo submissions."""
        user = update.effective_user
        if not self.is_admin(user.id):
            await update.message.reply_text("Only admins can approve submissions!")
            return
        
        # Check if there are pending submissions
        pending = self.game_state.get_pending_photo_submissions()
        
        if not pending:
            await update.message.reply_text(
                "ℹ️ No pending photo submissions to approve.\n"
                "Photo submissions will appear here when teams submit photos for challenges."
            )
            return
        
        # Display pending submissions
        message = "📷 *Pending Photo Submissions:*\n\n"
        for submission_id, submission in pending.items():
            message += (
                f"• Team: {submission['team_name']}\n"
                f"  Challenge #{submission['challenge_id']}\n"
                f"  Submitted by: {submission['user_name']}\n"
                f"  ID: `{submission_id}`\n\n"
            )
        message += "Use the buttons on the photo messages to approve/reject submissions."
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def reject_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /reject command (admin only) - view pending submissions."""
        user = update.effective_user
        if not self.is_admin(user.id):
            await update.message.reply_text("Only admins can reject submissions!")
            return
        
        # Check if there are pending submissions
        pending = self.game_state.get_pending_photo_submissions()
        
        if not pending:
            await update.message.reply_text(
                "ℹ️ No pending photo submissions to review.\n"
                "Photo submissions will appear here when teams submit photos for challenges."
            )
            return
        
        # Display pending submissions
        message = "📷 *Pending Photo Submissions:*\n\n"
        for submission_id, submission in pending.items():
            message += (
                f"• Team: {submission['team_name']}\n"
                f"  Challenge #{submission['challenge_id']}\n"
                f"  Submitted by: {submission['user_name']}\n"
                f"  ID: `{submission_id}`\n\n"
            )
        message += "Use the buttons on the photo messages to approve/reject submissions."
        
        await update.message.reply_text(message, parse_mode='Markdown')
    

    async def togglephotoverify_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /togglephotoverify command (admin only) - toggle photo verification."""
        user = update.effective_user
        if not self.is_admin(user.id):
            await update.message.reply_text("Only admins can toggle photo verification!")
            return
        
        new_state = self.game_state.toggle_photo_verification()
        
        status = "enabled ✅" if new_state else "disabled ❌"
        message = f"📷 Photo verification is now *{status}*\n\n"
        
        if new_state:
            message += (
                "Teams must now send a photo of their location before viewing challenges 2 onwards.\n"
                "The photo will be sent to you for approval.\n"
                "Only after you approve the photo will the challenge be revealed and the timeout start.\n\n"
                "To send a photo:\n"
                "1. Take a photo at the challenge location\n"
                "2. Send it to the bot\n"
                "3. Wait for admin approval\n"
                "4. Challenge will be revealed after approval"
            )
        else:
            message += (
                "Teams can now view challenges without photo verification.\n"
                "Photo verification can be re-enabled at any time."
            )
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def tournamentwin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /tournamentwin command (admin only) - report a tournament match winner."""
        user = update.effective_user
        if not self.is_admin(user.id):
            await update.message.reply_text("Only admins can report tournament results!")
            return
        
        if not self.game_state.game_started:
            await update.message.reply_text("The game hasn't started yet!")
            return
        
        # Parse command: /tournamentwin <challenge_id> <team_name>
        if not context.args or len(context.args) < 2:
            await update.message.reply_text(
                "Usage: `/tournamentwin <challenge_id> <team_name>`\n\n"
                "Example: `/tournamentwin 5 Team Alpha`",
                parse_mode='Markdown'
            )
            return
        
        try:
            challenge_id = int(context.args[0])
            team_name = ' '.join(context.args[1:])
        except ValueError:
            await update.message.reply_text("Invalid challenge ID! Please use a number.")
            return
        
        # Verify challenge exists and is a tournament
        if challenge_id < 1 or challenge_id > len(self.challenges):
            await update.message.reply_text(f"Challenge {challenge_id} doesn't exist!")
            return
        
        challenge = self.challenges[challenge_id - 1]
        if challenge.get('verification', {}).get('method') != 'tournament':
            await update.message.reply_text(f"Challenge {challenge_id} is not a tournament challenge!")
            return
        
        # Verify team exists
        if team_name not in self.game_state.teams:
            await update.message.reply_text(f"Team '{team_name}' doesn't exist!")
            return
        
        # Get or create tournament
        tournament = self.game_state.get_tournament(challenge_id)
        if not tournament:
            await update.message.reply_text(
                f"No active tournament for challenge {challenge_id}!\n"
                "Tournament will be created when teams reach this challenge."
            )
            return
        
        # Report winner
        success = self.game_state.report_match_winner(challenge_id, team_name)
        
        if not success:
            await update.message.reply_text(
                f"❌ Could not record win for {team_name}.\n\n"
                "Possible reasons:\n"
                "- Team is not in a pending match\n"
                "- Match already completed\n"
                "- Tournament already finished"
            )
            return
        
        # Send confirmation
        await update.message.reply_text(
            f"✅ *Match Winner Recorded*\n\n"
            f"Winner: {team_name}\n"
            f"Challenge: {challenge['name']}",
            parse_mode='Markdown'
        )
        
        # Check if tournament is complete
        if self.game_state.is_tournament_complete(challenge_id):
            last_place = self.game_state.get_tournament_last_place(challenge_id)
            tournament_config = challenge.get('tournament', {})
            timeout_minutes = tournament_config.get('timeout_minutes', 5)
            
            completion_msg = (
                f"🏆 *Tournament Complete!*\n\n"
                f"Challenge: {challenge['name']}\n"
                f"Last Place: {last_place}\n"
                f"Penalty: {timeout_minutes} minute timeout"
            )
            await update.message.reply_text(completion_msg, parse_mode='Markdown')
            
            # Complete the challenge for all teams except last place
            for team_name in tournament['teams']:
                if team_name != last_place:
                    self.game_state.complete_challenge(team_name, challenge_id, len(self.challenges))
            
            # Apply timeout penalty to last place team
            if last_place:
                self.game_state.complete_challenge(last_place, challenge_id, len(self.challenges))
                # The penalty is handled by the hint system (timeout_penalty_minutes)
                # We'll set a completion time offset to simulate the penalty
            
            # Broadcast the next challenge to all teams
            for team_name in tournament['teams']:
                team_data = self.game_state.teams.get(team_name)
                if team_data and not team_data.get('finish_time'):
                    # Only broadcast if team hasn't finished all challenges
                    await self.broadcast_current_challenge(context, team_name)
        else:
            # Show next round matches
            current_matches = self.game_state.get_current_round_matches(challenge_id)
            if current_matches:
                next_msg = "📋 *Next Matches:*\n\n"
                for i, match in enumerate(current_matches):
                    if match['status'] == 'pending':
                        next_msg += f"{i+1}. {match['team1']} vs {match['team2']}\n"
                    elif match['status'] == 'bye':
                        next_msg += f"{i+1}. {match['team1']} (bye)\n"
                
                await update.message.reply_text(next_msg, parse_mode='Markdown')
    
    async def tournamentstatus_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /tournamentstatus command (admin only) - view tournament status."""
        user = update.effective_user
        if not self.is_admin(user.id):
            await update.message.reply_text("Only admins can view tournament status!")
            return
        
        if not self.game_state.game_started:
            await update.message.reply_text("The game hasn't started yet!")
            return
        
        # Parse command: /tournamentstatus <challenge_id>
        if not context.args or len(context.args) < 1:
            await update.message.reply_text(
                "Usage: `/tournamentstatus <challenge_id>`\n\n"
                "Example: `/tournamentstatus 5`",
                parse_mode='Markdown'
            )
            return
        
        try:
            challenge_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("Invalid challenge ID! Please use a number.")
            return
        
        # Get tournament
        tournament = self.game_state.get_tournament(challenge_id)
        if not tournament:
            await update.message.reply_text(f"No tournament found for challenge {challenge_id}!")
            return
        
        challenge = self.challenges[challenge_id - 1]
        
        # Build status message
        status_msg = f"🏆 *Tournament Status*\n\n"
        status_msg += f"Challenge: {challenge['name']}\n"
        status_msg += f"Game: {tournament['game_name']}\n"
        status_msg += f"Status: {tournament['status']}\n"
        status_msg += f"Current Round: {tournament['current_round'] + 1}\n\n"
        
        # Show current round matches
        current_matches = self.game_state.get_current_round_matches(challenge_id)
        if current_matches:
            status_msg += "📋 *Current Round Matches:*\n\n"
            for i, match in enumerate(current_matches):
                if match['status'] == 'pending':
                    status_msg += f"{i+1}. {match['team1']} vs {match['team2']} - ⏳ Pending\n"
                elif match['status'] == 'complete':
                    status_msg += f"{i+1}. {match['team1']} vs {match['team2']} - ✅ Winner: {match['winner']}\n"
                elif match['status'] == 'bye':
                    status_msg += f"{i+1}. {match['team1']} - 🎫 Bye\n"
        
        if tournament['status'] == 'complete':
            rankings = tournament.get('rankings', [])
            if rankings:
                status_msg += "\n🏅 *Final Rankings:*\n\n"
                for i, team in enumerate(rankings):
                    status_msg += f"{i+1}. {team}\n"
        
        await update.message.reply_text(status_msg, parse_mode='Markdown')
    
    async def tournamentreset_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /tournamentreset command (admin only) - reset a tournament."""
        user = update.effective_user
        if not self.is_admin(user.id):
            await update.message.reply_text("Only admins can reset tournaments!")
            return
        
        # Parse command: /tournamentreset <challenge_id>
        if not context.args or len(context.args) < 1:
            await update.message.reply_text(
                "Usage: `/tournamentreset <challenge_id>`\n\n"
                "Example: `/tournamentreset 5`",
                parse_mode='Markdown'
            )
            return
        
        try:
            challenge_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("Invalid challenge ID! Please use a number.")
            return
        
        # Reset tournament
        success = self.game_state.reset_tournament(challenge_id)
        
        if success:
            await update.message.reply_text(
                f"✅ Tournament for challenge {challenge_id} has been reset.",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                f"❌ No tournament found for challenge {challenge_id}.",
                parse_mode='Markdown'
            )

    async def pass_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /pass command (admin only) - manually advance a team past current challenge."""
        user = update.effective_user
        if not self.is_admin(user.id):
            await update.message.reply_text("Only admins can use the /pass command!")
            return
        
        if not self.game_state.game_started:
            await update.message.reply_text("The game hasn't started yet!")
            return
        
        if self.game_state.game_ended:
            await update.message.reply_text("The game has already ended!")
            return
        
        # Parse command: /pass <team_name>
        if not context.args:
            await update.message.reply_text(
                "Usage: `/pass <team_name>`\n\n"
                "Example: `/pass RedTeam`\n\n"
                "This command manually advances a team past their current challenge.\n"
                "Use this for exceptional circumstances, technical difficulties, or manual overrides.",
                parse_mode='Markdown'
            )
            return
        
        team_name = ' '.join(context.args)
        
        # Verify team exists
        if team_name not in self.game_state.teams:
            await update.message.reply_text(f"❌ Team '{team_name}' doesn't exist!")
            return
        
        # Get team's current challenge info
        team_data = self.game_state.teams[team_name]
        current_challenge_index = team_data.get('current_challenge_index', 0)
        
        # Check if team has already finished all challenges
        if current_challenge_index >= len(self.challenges):
            await update.message.reply_text(
                f"❌ Team '{team_name}' has already completed all challenges!"
            )
            return
        
        # Get the current challenge
        current_challenge = self.challenges[current_challenge_index]
        challenge_id = current_challenge['id']
        challenge_name = current_challenge['name']
        
        # Check if challenge is already completed
        if challenge_id in team_data['completed_challenges']:
            await update.message.reply_text(
                f"❌ Team '{team_name}' has already completed Challenge #{challenge_id}!"
            )
            return
        
        # Pass the team
        success = self.game_state.pass_team(
            team_name, 
            len(self.challenges),
            user.id,
            user.first_name or "Admin"
        )
        
        if not success:
            await update.message.reply_text(
                f"❌ Failed to advance team '{team_name}'. Please check the team status and try again."
            )
            return
        
        # Calculate progress
        completed = len(team_data['completed_challenges'])
        total = len(self.challenges)
        
        # Send confirmation to admin
        confirmation_msg = (
            f"✅ *Team Manually Advanced*\n\n"
            f"Team: {team_name}\n"
            f"Challenge #{challenge_id}: {challenge_name}\n"
            f"Advanced by: {user.first_name}\n"
            f"Progress: {completed}/{total} challenges\n\n"
            f"⚠️ This action has been logged for audit purposes."
        )
        
        if team_data.get('finish_time'):
            confirmation_msg += f"\n\n🏆 *Team has finished all challenges!*"
        
        await update.message.reply_text(confirmation_msg, parse_mode='Markdown')
        
        # Notify all team members
        notification_msg = (
            f"✅ *Challenge Passed by Admin*\n\n"
            f"Team: {team_name}\n"
            f"Challenge #{challenge_id}: {challenge_name}\n"
            f"Progress: {completed}/{total} challenges\n\n"
            f"Your team has been manually advanced past this challenge by an admin.\n"
        )
        
        if team_data.get('finish_time'):
            notification_msg += (
                f"\n🏆 *CONGRATULATIONS!* 🏆\n"
                f"Your team finished the race!\n"
                f"Finish time: {team_data['finish_time']}"
            )
        else:
            notification_msg += "Use /current to see your next challenge."
        
        # Broadcast to all team members
        sent_to_users = set()
        for member in team_data['members']:
            member_id = member['id']
            if member_id in sent_to_users:
                continue
            
            try:
                await context.bot.send_message(
                    chat_id=member_id,
                    text=notification_msg,
                    parse_mode='Markdown'
                )
                sent_to_users.add(member_id)
            except Exception as e:
                logger.error(f"Failed to notify team member {member_id}: {e}")
        
        # Broadcast next challenge if team hasn't finished
        if not team_data.get('finish_time'):
            await self.broadcast_current_challenge(context, team_name)
    
    async def unrecognized_message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle unrecognized text messages."""
        # Only handle text messages that aren't commands
        if not update.message or not update.message.text:
            return
        
        # Ignore if this is a command (starts with /)
        if update.message.text.startswith('/'):
            return
        
        # Check if we're waiting for input from a command
        if 'waiting_for' in context.user_data and 'command' in context.user_data['waiting_for']:
            waiting_command = context.user_data['waiting_for']['command']
            user_input = update.message.text.strip()
            
            # Route to the appropriate command handler with the text as argument
            if waiting_command == 'createteam':
                # Clear the waiting state
                del context.user_data['waiting_for']
                # Simulate command with args
                context.args = user_input.split()
                await self.create_team_command(update, context)
                return
            elif waiting_command == 'jointeam':
                # Clear the waiting state
                del context.user_data['waiting_for']
                context.args = user_input.split()
                await self.join_team_command(update, context)
                return
            elif waiting_command == 'submit':
                # Clear the waiting state
                del context.user_data['waiting_for']
                # For submit, we need to call it with the answer
                context.args = user_input.split()
                await self.submit_command(update, context)
                return
            elif waiting_command == 'addteam':
                # Clear the waiting state
                del context.user_data['waiting_for']
                context.args = user_input.split()
                await self.addteam_command(update, context)
                return
            elif waiting_command == 'removeteam':
                # Clear the waiting state
                del context.user_data['waiting_for']
                context.args = user_input.split()
                await self.removeteam_command(update, context)
                return
            elif waiting_command == 'message':
                # Handle /message interactive flow - message text received
                team_name = context.user_data['waiting_for'].get('team_name')
                # Clear the waiting state
                del context.user_data['waiting_for']
                
                if not team_name:
                    await update.message.reply_text("❌ Error: Team name not found. Please try again.")
                    return
                
                # Verify team still exists
                if team_name not in self.game_state.teams:
                    await update.message.reply_text(f"❌ Team '{team_name}' no longer exists!")
                    return
                
                # Send the message using the same logic as message_command
                # user_input is the full message text, keep it together as one element after team name
                context.args = [team_name, user_input]
                await self.message_command(update, context)
                return
            elif waiting_command == 'broadcast':
                # Handle /broadcast interactive flow - message text received
                # Clear the waiting state
                del context.user_data['waiting_for']
                
                # Send the broadcast using the same logic as broadcast_command
                # user_input is the full message text, keep it as a single element
                context.args = [user_input]
                await self.broadcast_command(update, context)
                return
        
        # Check if game is active and user is in a team - treat message as submission
        if self.game_state.game_started and not self.game_state.game_ended:
            user = update.effective_user
            team_name = self.game_state.get_team_by_user(user.id)
            
            if team_name:
                # User is in a team during an active game
                # First, check what format the current challenge expects
                team = self.game_state.teams[team_name]
                current_challenge_index = team.get('current_challenge_index', 0)
                
                # Check if all challenges are completed
                if current_challenge_index < len(self.challenges):
                    current_challenge = self.challenges[current_challenge_index]
                    expected_format = self.get_expected_answer_format(current_challenge)
                    
                    if expected_format == 'photo':
                        # Text sent but photo is expected
                        error_message = self.get_format_mismatch_message(expected_format, current_challenge)
                        await update.message.reply_text(error_message, parse_mode='Markdown')
                        return
                
                # Treat this message as a submission
                # Note: We set context.args to simulate the /submit command being called with the message as the answer
                user_input = update.message.text.strip()
                context.args = user_input.split()
                await self.submit_command(update, context)
                return
        
        # Send helpful message
        response = (
            "❓ I didn't understand that message.\n\n"
            "Use /help to see what you can do based on your current game state."
        )
        
        await update.message.reply_text(response)
    
    async def message_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /message command (admin only) - send a message to a specific team."""
        user = update.effective_user
        if not self.is_admin(user.id):
            await update.message.reply_text("Only admins can use the /message command!")
            return
        
        # Check if no args provided - start interactive flow
        if not context.args:
            # Check if there are any teams
            if not self.game_state.teams:
                await update.message.reply_text("❌ No teams exist yet!")
                return
            
            # Create inline keyboard with team selection buttons
            keyboard = []
            for team_name in sorted(self.game_state.teams.keys()):
                keyboard.append([InlineKeyboardButton(team_name, callback_data=f"msg_team_{team_name}")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "📨 *Send Message to Team*\n\n"
                "Select the team you want to send a message to:",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            return
        
        # Parse command: /message <team_name> <message>
        if len(context.args) < 2:
            await update.message.reply_text(
                "Usage: `/message <team_name> <message>`\n\n"
                "Example: `/message RedTeam Great job on the last challenge!`\n\n"
                "Or use `/message` without arguments for interactive team selection.",
                parse_mode='Markdown'
            )
            return
        
        # Extract team name and message
        team_name = context.args[0]
        message_text = ' '.join(context.args[1:])
        
        # Verify team exists
        if team_name not in self.game_state.teams:
            await update.message.reply_text(f"❌ Team '{team_name}' doesn't exist!")
            return
        
        # Get team data
        team_data = self.game_state.teams[team_name]
        
        # Prepare the message to send to the team
        team_message = (
            f"📨 *Message from Admin*\n\n"
            f"{message_text}"
        )
        
        # Send message to all team members
        sent_to_users = set()
        success_count = 0
        for member in team_data['members']:
            member_id = member['id']
            if member_id in sent_to_users:
                continue
            
            try:
                await context.bot.send_message(
                    chat_id=member_id,
                    text=team_message,
                    parse_mode='Markdown'
                )
                sent_to_users.add(member_id)
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to send message to team member {member_id}: {e}")
        
        # Send confirmation to admin
        confirmation_msg = (
            f"✅ *Message Sent*\n\n"
            f"Team: {team_name}\n"
            f"Members notified: {success_count}/{len(team_data['members'])}\n"
            f"Message: {message_text}"
        )
        
        await update.message.reply_text(confirmation_msg, parse_mode='Markdown')
    
    async def broadcast_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /broadcast command (admin only) - send a message to all teams."""
        user = update.effective_user
        if not self.is_admin(user.id):
            await update.message.reply_text("Only admins can use the /broadcast command!")
            return
        
        # Check if no args provided - start interactive flow
        if not context.args:
            # Check if there are any teams
            if not self.game_state.teams:
                await update.message.reply_text("❌ No teams exist yet!")
                return
            
            # Store that we're waiting for broadcast message
            if 'waiting_for' not in context.user_data:
                context.user_data['waiting_for'] = {}
            context.user_data['waiting_for']['command'] = 'broadcast'
            
            await update.message.reply_text(
                "📢 *Broadcast to All Teams*\n\n"
                "Please enter the message you want to broadcast to all teams:",
                parse_mode='Markdown'
            )
            return
        
        # Extract message
        message_text = ' '.join(context.args)
        
        # Check if there are any teams
        if not self.game_state.teams:
            await update.message.reply_text("❌ No teams exist yet!")
            return
        
        # Prepare the message to broadcast
        broadcast_message = (
            f"📢 *Broadcast from Admin*\n\n"
            f"{message_text}"
        )
        
        # Send message to all team members across all teams
        sent_to_users = set()
        success_count = 0
        
        for team_name, team_data in self.game_state.teams.items():
            for member in team_data['members']:
                member_id = member['id']
                
                # Skip if already sent to this user (avoid duplicates if someone is in multiple teams)
                if member_id in sent_to_users:
                    continue
                
                try:
                    await context.bot.send_message(
                        chat_id=member_id,
                        text=broadcast_message,
                        parse_mode='Markdown'
                    )
                    sent_to_users.add(member_id)
                    success_count += 1
                except Exception as e:
                    logger.error(f"Failed to send broadcast to user {member_id}: {e}")
        
        # Send confirmation to admin
        confirmation_msg = (
            f"✅ *Broadcast Sent*\n\n"
            f"Teams: {len(self.game_state.teams)}\n"
            f"Unique members notified: {success_count}\n"
            f"Message: {message_text}"
        )
        
        await update.message.reply_text(confirmation_msg, parse_mode='Markdown')
    
    async def message_team_callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle team selection callback for /message command."""
        query = update.callback_query
        await query.answer()
        
        # Parse callback data: msg_team_{team_name}
        if not query.data.startswith('msg_team_'):
            await query.edit_message_text("❌ Invalid team selection.")
            return
        
        team_name = query.data.replace('msg_team_', '')
        
        # Verify team exists
        if team_name not in self.game_state.teams:
            await query.edit_message_text(f"❌ Team '{team_name}' no longer exists!")
            return
        
        # Store the selected team in user_data and set waiting state
        if 'waiting_for' not in context.user_data:
            context.user_data['waiting_for'] = {}
        context.user_data['waiting_for']['command'] = 'message'
        context.user_data['waiting_for']['team_name'] = team_name
        
        # Update the message to show team selected and ask for message text
        await query.edit_message_text(
            f"📨 *Send Message to Team: {team_name}*\n\n"
            f"Please enter the message you want to send to this team:",
            parse_mode='Markdown'
        )
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors."""
        logger.error(f"Update {update} caused error {context.error}")
    
    def run(self):
        """Run the bot."""
        # Create application
        application = Application.builder().token(
            self.config['telegram']['bot_token']
        ).build()
        
        # Add command handlers
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("createteam", self.create_team_command))
        application.add_handler(CommandHandler("jointeam", self.join_team_command))
        application.add_handler(CommandHandler("myteam", self.my_team_command))
        application.add_handler(CommandHandler("leaderboard", self.leaderboard_command))
        application.add_handler(CommandHandler("challenges", self.challenges_command))
        application.add_handler(CommandHandler("current_challenge", self.current_challenge_command))
        application.add_handler(CommandHandler("current", self.current_challenge_command))
        application.add_handler(CommandHandler("hint", self.hint_command))
        application.add_handler(CommandHandler("submit", self.submit_command))
        application.add_handler(CommandHandler("contact", self.contact_command))
        application.add_handler(CommandHandler("startgame", self.start_game_command))
        application.add_handler(CommandHandler("endgame", self.end_game_command))
        application.add_handler(CommandHandler("reset", self.reset_command))
        application.add_handler(CommandHandler("teams", self.teams_command))
        application.add_handler(CommandHandler("teamstatus", self.teamstatus_command))
        application.add_handler(CommandHandler("addteam", self.addteam_command))
        application.add_handler(CommandHandler("editteam", self.editteam_command))
        application.add_handler(CommandHandler("removeteam", self.removeteam_command))
        application.add_handler(CommandHandler("approve", self.approve_command))
        application.add_handler(CommandHandler("reject", self.reject_command))

        application.add_handler(CommandHandler("togglephotoverify", self.togglephotoverify_command))
        application.add_handler(CommandHandler("tournamentwin", self.tournamentwin_command))
        application.add_handler(CommandHandler("tournamentstatus", self.tournamentstatus_command))
        application.add_handler(CommandHandler("tournamentreset", self.tournamentreset_command))
        application.add_handler(CommandHandler("pass", self.pass_command))
        application.add_handler(CommandHandler("message", self.message_command))
        application.add_handler(CommandHandler("broadcast", self.broadcast_command))
        
        # Add callback query handlers
        application.add_handler(CallbackQueryHandler(
            self.photo_verification_callback_handler, 
            pattern="^verify_(approve|reject)_.*"
        ))
        application.add_handler(CallbackQueryHandler(
            self.photo_approval_callback_handler, 
            pattern="^(approve|reject)_.*"
        ))
        application.add_handler(CallbackQueryHandler(
            self.message_team_callback_handler,
            pattern="^msg_team_.*"
        ))
        application.add_handler(CallbackQueryHandler(self.hint_callback_handler))
        
        # Add photo handler for photo submissions
        application.add_handler(MessageHandler(filters.PHOTO, self.photo_handler))
        
        # Add handler for unrecognized text messages (must be last)
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.unrecognized_message_handler))
        
        # Add error handler
        application.add_error_handler(self.error_handler)
        
        # Start the bot
        logger.info("Starting Amazing Race Bot...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    bot = AmazingRaceBot()
    bot.run()
