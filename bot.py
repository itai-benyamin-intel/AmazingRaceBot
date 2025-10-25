"""
Telegram Amazing Race Bot - Main bot implementation
"""
import logging
import yaml
import math
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
        
        # Load location verification setting from config, but allow runtime override via game_state
        config_location_enabled = self.config['game'].get('location_verification_enabled', False)
        # If game_state has a saved value, use it; otherwise use config value
        if hasattr(self.game_state, 'location_verification_enabled'):
            # Sync with config on first load if not set
            if not hasattr(self, '_location_synced'):
                if self.game_state.location_verification_enabled is False and config_location_enabled:
                    self.game_state.set_location_verification(config_location_enabled)
        else:
            # Fallback for older game states
            self.game_state.location_verification_enabled = config_location_enabled
            self.game_state.save_state()
    
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
    
    @staticmethod
    def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two GPS coordinates using Haversine formula.
        
        Args:
            lat1: Latitude of first point
            lon1: Longitude of first point
            lat2: Latitude of second point
            lon2: Longitude of second point
            
        Returns:
            Distance in meters
        """
        # Earth's radius in meters
        R = 6371000
        
        # Convert to radians
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        # Haversine formula
        a = math.sin(delta_lat / 2) ** 2 + \
            math.cos(lat1_rad) * math.cos(lat2_rad) * \
            math.sin(delta_lon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def verify_location(self, user_lat: float, user_lon: float, challenge: dict) -> tuple[bool, float]:
        """Verify if user's location is within the challenge's required radius.
        
        Args:
            user_lat: User's latitude
            user_lon: User's longitude
            challenge: Challenge configuration with coordinates
            
        Returns:
            Tuple of (is_within_radius, distance_in_meters)
        """
        coordinates = challenge.get('coordinates', {})
        if not coordinates:
            # No coordinates specified, skip verification
            return True, 0
        
        target_lat = coordinates.get('latitude')
        target_lon = coordinates.get('longitude')
        radius = coordinates.get('radius', 100)  # Default 100m radius
        
        if target_lat is None or target_lon is None:
            # Coordinates not properly configured, skip verification
            return True, 0
        
        distance = self.calculate_distance(user_lat, user_lon, target_lat, target_lon)
        return distance <= radius, distance
    
    def get_challenge_type_emoji(self, challenge_type: str) -> str:
        """Get emoji representation for challenge type."""
        type_emojis = {
            'photo': '📷',
            'riddle': '🧩',
            'code': '💻',
            'qr': '📱',
            'trivia': '❓',
            'location': '📍',
            'text': '📝',
            'scavenger': '🔍',
            'team_activity': '🤝',
            'decryption': '🔐'
        }
        return type_emojis.get(challenge_type, '🎯')
    
    def verify_answer(self, challenge: dict, user_answer: str) -> bool:
        """Verify a text answer for a challenge.
        
        Args:
            challenge: Challenge configuration
            user_answer: User's submitted answer
            
        Returns:
            True if answer is correct, False otherwise
        """
        verification = challenge.get('verification', {})
        if verification.get('method') != 'answer':
            return False
        
        expected_answer = verification.get('answer', '').lower().strip()
        user_answer = user_answer.lower().strip()
        
        # Check if the expected answer is a comma-separated list (for trivia)
        if ',' in expected_answer:
            # For trivia with multiple answers, check if user answer contains all required keywords
            required_keywords = [kw.strip() for kw in expected_answer.split(',')]
            return all(keyword in user_answer for keyword in required_keywords)
        else:
            # For single answer, check exact match or if expected answer is in user answer
            return expected_answer == user_answer or expected_answer in user_answer
    
    def get_challenge_instructions(self, challenge: dict) -> str:
        """Get submission instructions based on challenge type.
        
        Args:
            challenge: Challenge configuration
            
        Returns:
            Instruction text for how to submit the challenge
        """
        verification = challenge.get('verification', {})
        method = verification.get('method', 'photo')
        
        if method == 'photo':
            return "📷 Submit a photo to complete this challenge."
        elif method == 'answer':
            challenge_type = challenge.get('type', 'text')
            if challenge_type == 'riddle':
                return "💡 Reply with your answer to this riddle."
            elif challenge_type == 'code':
                return "💻 Reply with your code solution or the result."
            elif challenge_type == 'trivia':
                return "📝 Reply with your answer."
            elif challenge_type == 'decryption':
                return "🔓 Reply with the decrypted message."
            elif challenge_type == 'qr':
                return "📱 Reply with the text from the QR code."
            else:
                return "📝 Reply with your answer."
        elif method == 'location':
            return "📍 You need to be at the correct location."
        elif method == 'auto':
            return "✅ This challenge is auto-verified."
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
        unlock_time_str = self.game_state.get_challenge_unlock_time(team_name, challenge_id)
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
        
        # Check if photo verification is required and not yet done (for challenges 2+)
        if self.game_state.photo_verification_enabled and current_challenge_index > 0:
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
        instructions = self.get_challenge_instructions(challenge)
        
        # Create broadcast message
        broadcast_message = (
            f"🎯 *New Challenge Available!*\n\n"
            f"*Challenge #{challenge_id}: {challenge['name']}*\n"
            f"{type_emoji} Type: {challenge_type}\n"
            f"📍 Location: {challenge['location']}\n"
            f"📝 {challenge['description']}\n\n"
            f"ℹ️ {instructions}\n\n"
        )
        
        # Add hints information
        hints = challenge.get('hints', [])
        used_hints = self.game_state.get_used_hints(team_name, challenge_id)
        
        if hints:
            broadcast_message += f"💡 Hints available: {len(hints)}\n"
            if len(used_hints) < len(hints):
                broadcast_message += "Use /hint to get a hint (costs 2 min penalty)\n"
        
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
                await context.bot.send_message(
                    chat_id=member_id,
                    text=broadcast_message,
                    parse_mode='Markdown'
                )
                sent_to_users.add(member_id)
            except Exception as e:
                logger.error(f"Failed to send challenge broadcast to user {member_id}: {e}")
    
    async def broadcast_challenge_completion(self, context: ContextTypes.DEFAULT_TYPE, 
                                            team_name: str, challenge_id: int, 
                                            challenge_name: str, submitted_by_id: int,
                                            submitted_by_name: str, completed: int, 
                                            total: int):
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
                "Use `/createteam <team_name>` to create a team\n"
                "Example: `/createteam Awesome Team`\n\n"
                "👥 *Join an existing team:*\n"
                "Use `/jointeam <team_name>` to join a team\n"
                "Example: `/jointeam Awesome Team`\n\n"
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
                "Use `/hint` to get a hint (costs 2 min penalty)\n\n"
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
                "Use `/createteam <team_name>` to create a team\n"
                "Example: `/createteam Awesome Team`\n\n"
                "👥 *Join an existing team:*\n"
                "Use `/jointeam <team_name>` to join a team\n"
                "Example: `/jointeam Awesome Team`\n\n"
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
                "Use `/hint` to get a hint (costs 2 min penalty)\n\n"
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
            await update.message.reply_text(
                f"✅ You joined team '{team_name}'!\n"
                f"Team members: {len(team['members']) + 1}/{self.config['game']['max_team_size']}"
            )
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
        """Handle the /challenges command - shows brief summary of completed and current challenges."""
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
                unlock_time_str = self.game_state.get_challenge_unlock_time(team_name, challenge_id)
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
                # Completed challenge - show title and brief description only
                message += (
                    f"✅ *{challenge['name']}*\n"
                    f"   {challenge['description']}\n\n"
                )
            elif i == current_challenge_index:
                # Current challenge - show title and brief description only
                if penalty_info:
                    message += (
                        f"⏱️ *{challenge['name']}* (LOCKED - Penalty Timeout)\n"
                        f"   Challenge locked due to {penalty_info['hint_count']} hint(s) used\n"
                        f"   ⏳ Unlocks in: {penalty_info['minutes']}m {penalty_info['seconds']}s\n"
                        f"   Available at: {penalty_info['unlock_time'].strftime('%H:%M:%S')}\n\n"
                    )
                else:
                    message += (
                        f"🎯 *{challenge['name']}* (CURRENT)\n"
                        f"   {challenge['description']}\n\n"
                    )
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
        
        # Check if photo verification is required and not yet done (for challenges 2+)
        if self.game_state.photo_verification_enabled and current_challenge_index > 0:
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
        instructions = self.get_challenge_instructions(challenge)
        
        # Check if challenge is locked due to penalty
        is_locked = False
        penalty_info = None
        if current_challenge_index > 0:  # Not the first challenge
            unlock_time_str = self.game_state.get_challenge_unlock_time(team_name, challenge_id)
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
                    message += "\nUse /hint to get a hint (costs 2 min penalty)\n"
            
            message += "\nUse /submit [answer] to submit this challenge."
        
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
            unlock_time_str = self.game_state.get_challenge_unlock_time(team_name, challenge_id)
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
        
        # Check if photo verification is required and not yet done (for challenges 2+)
        if self.game_state.photo_verification_enabled and current_challenge_index > 0:
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
            
            if self.verify_answer(challenge, user_answer):
                # Answer is correct
                submission_data = {
                    'type': 'answer',
                    'answer': user_answer,
                    'timestamp': datetime.now().isoformat(),
                    'submitted_by': user.id
                }
                
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
                    else:
                        # Check if there's a penalty for the next challenge
                        next_challenge_id = challenge_id + 1
                        unlock_time_str = self.game_state.get_challenge_unlock_time(team_name, next_challenge_id)
                        if unlock_time_str:
                            unlock_time = datetime.fromisoformat(unlock_time_str)
                            hint_count = self.game_state.get_hint_count(team_name, challenge_id)
                            penalty_minutes = hint_count * 2
                            
                            response += (
                                f"\n\n⏱️ *Hint Penalty Applied*\n"
                                f"You used {hint_count} hint(s) on this challenge.\n"
                                f"Next challenge unlocks in {penalty_minutes} minutes at:\n"
                                f"{unlock_time.strftime('%H:%M:%S')}"
                            )
                    
                    await update.message.reply_text(response, parse_mode='Markdown')
                    
                    # Send custom success message if configured
                    success_message = challenge.get('success_message')
                    if success_message:
                        await update.message.reply_text(success_message, parse_mode='Markdown')
                    
                    # Broadcast completion to team and admin
                    await self.broadcast_challenge_completion(
                        context, team_name, challenge_id, challenge['name'],
                        user.id, user.first_name, completed, total
                    )
                    
                    # After completion message is sent, broadcast next challenge if no timeout
                    if not team.get('finish_time'):
                        next_challenge_id = challenge_id + 1
                        unlock_time_str = self.game_state.get_challenge_unlock_time(team_name, next_challenge_id)
                        if not unlock_time_str:
                            # No timeout - broadcast next challenge to all team members (excluding submitter)
                            await self.broadcast_current_challenge(context, team_name, user.id)
                else:
                    await update.message.reply_text("Error completing challenge. Please try again.")
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
            "• `/hint` - Get a hint (2 min penalty)\n"
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
        
        # Check if this might be a photo verification for location arrival
        team_name = self.game_state.get_team_by_user(user.id)
        if not team_name:
            # No team, ignore the photo
            return
        
        # Check if photo verification is enabled
        if not self.game_state.photo_verification_enabled:
            # Photo verification disabled, ignore
            return
        
        # Check if team is on a challenge that needs photo verification
        team = self.game_state.teams[team_name]
        current_challenge_index = team.get('current_challenge_index', 0)
        
        # Only for challenges 2 onwards (index 1+)
        if current_challenge_index == 0:
            return
        
        # Check if all challenges are completed
        if current_challenge_index >= len(self.challenges):
            return
        
        current_challenge = self.challenges[current_challenge_index]
        challenge_id = current_challenge['id']
        
        # Check if photo verification already done for this challenge
        photo_verifications = team.get('photo_verifications', {})
        if str(challenge_id) in photo_verifications:
            # Already verified
            await update.message.reply_text(
                f"✅ Photo verification already completed for this challenge.\n"
                f"Use /current to see the challenge details."
            )
            return
        
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
                # Update admin message
                await query.edit_message_caption(
                    caption=query.message.caption + "\n\n✅ *APPROVED - Challenge Revealed*",
                    parse_mode='Markdown'
                )
                
                # Broadcast the challenge to all team members (now that photo is approved)
                await self.broadcast_current_challenge(context, team_name)
                
                # Notify team members that photo was approved
                team = self.game_state.teams[team_name]
                team_members = team['members']
                for member in team_members:
                    try:
                        response = (
                            f"✅ *Photo Verified!*\n\n"
                            f"Your location photo for Challenge #{challenge_id} has been approved!\n\n"
                            f"The challenge is now revealed. Check your messages above for details.\n"
                            f"Use /current to see the challenge again."
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
        challenge_name = self.challenges[challenge_id - 1]['name']
        user_id = submission['user_id']
        user_name = submission['user_name']
        
        if action == 'approve':
            # Approve the submission
            if self.game_state.approve_photo_submission(submission_id, len(self.challenges)):
                team = self.game_state.teams[team_name]
                completed = len(team['completed_challenges'])
                total = len(self.challenges)
                
                # Update admin message
                await query.edit_message_caption(
                    caption=query.message.caption + "\n\n✅ *APPROVED*",
                    parse_mode='Markdown'
                )
                
                # Check if there's a penalty for the next challenge
                has_timeout = False
                if not team.get('finish_time'):
                    next_challenge_id = challenge_id + 1
                    unlock_time_str = self.game_state.get_challenge_unlock_time(team_name, next_challenge_id)
                    has_timeout = unlock_time_str is not None
                
                # Notify submitter that photo was approved
                try:
                    response = (
                        f"✅ *Photo Approved!*\n\n"
                        f"Your photo for *{challenge_name}* has been approved!\n"
                        f"Progress: {completed}/{total} challenges"
                    )
                    
                    # Check if team finished
                    if team.get('finish_time'):
                        response += f"\n\n🏆 *CONGRATULATIONS!* 🏆\n"
                        response += f"Your team finished the race!\n"
                        response += f"Finish time: {team['finish_time']}"
                    else:
                        # Check for hint penalty
                        next_challenge_id = challenge_id + 1
                        unlock_time_str = self.game_state.get_challenge_unlock_time(team_name, next_challenge_id)
                        if unlock_time_str:
                            unlock_time = datetime.fromisoformat(unlock_time_str)
                            hint_count = self.game_state.get_hint_count(team_name, challenge_id)
                            penalty_minutes = hint_count * 2
                            
                            response += (
                                f"\n\n⏱️ *Hint Penalty Applied*\n"
                                f"You used {hint_count} hint(s) on this challenge.\n"
                                f"Next challenge unlocks in {penalty_minutes} minutes at:\n"
                                f"{unlock_time.strftime('%H:%M:%S')}"
                            )
                    
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=response,
                        parse_mode='Markdown'
                    )
                    
                    # Send custom success message if configured
                    challenge = self.challenges[challenge_id - 1]
                    success_message = challenge.get('success_message')
                    if success_message:
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=success_message,
                            parse_mode='Markdown'
                        )
                except Exception as e:
                    logger.error(f"Failed to notify submitter {user_id}: {e}")
                
                # Broadcast completion to team and admin (excluding submitter)
                await self.broadcast_challenge_completion(
                    context, team_name, challenge_id, challenge_name,
                    user_id, user_name, completed, total
                )
                
                # After completion message is sent, broadcast next challenge if no timeout
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

    async def location_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle location submissions for challenge verification."""
        user = update.effective_user
        location = update.message.location
        
        if not location:
            return
        
        user_lat = location.latitude
        user_lon = location.longitude
        
        # Check if user is in a team
        team_name = self.game_state.get_team_by_user(user.id)
        if not team_name:
            await update.message.reply_text(
                "You are not in any team! Use /createteam or /jointeam first."
            )
            return
        
        # Check if location verification is enabled
        if not self.game_state.location_verification_enabled:
            await update.message.reply_text(
                "📍 Location received!\n\n"
                "ℹ️ Location verification is currently disabled.\n"
                "Your location has been recorded but is not required for challenge progression."
            )
            return
        
        # Get team's current challenge
        team = self.game_state.teams[team_name]
        current_challenge_index = team.get('current_challenge_index', 0)
        
        # Skip verification for challenge 1 (starting point)
        if current_challenge_index == 0:
            await update.message.reply_text(
                "📍 Location received!\n\n"
                "ℹ️ Challenge 1 is the starting point - no location verification required.\n"
                "Complete Challenge 1 to unlock the next challenge!"
            )
            return
        
        # Check if team has completed all challenges
        if current_challenge_index >= len(self.challenges):
            await update.message.reply_text(
                "🏆 Your team has completed all challenges!\n"
                "Location verification is not needed."
            )
            return
        
        # Get the current challenge (the one they need to verify location for)
        current_challenge = self.challenges[current_challenge_index]
        
        # Verify location
        is_valid, distance = self.verify_location(user_lat, user_lon, current_challenge)
        
        coordinates = current_challenge.get('coordinates', {})
        radius = coordinates.get('radius', 100)
        
        if is_valid:
            # Store location verification in team data
            if 'location_verifications' not in team:
                team['location_verifications'] = {}
            
            team['location_verifications'][str(current_challenge['id'])] = {
                'verified_by': user.id,
                'user_name': user.first_name,
                'latitude': user_lat,
                'longitude': user_lon,
                'distance': distance,
                'timestamp': datetime.now().isoformat()
            }
            self.game_state.save_state()
            
            response = (
                f"✅ *Location Verified!*\n\n"
                f"You are within {distance:.1f}m of the challenge location.\n"
                f"Challenge: *{current_challenge['name']}*\n"
                f"Location: {current_challenge['location']}\n\n"
                f"You can now complete this challenge!\n"
                f"Use /submit [answer] to submit your answer."
            )
            await update.message.reply_text(response, parse_mode='Markdown')
        else:
            response = (
                f"❌ *Location Not Verified*\n\n"
                f"You are {distance:.1f}m away from the challenge location.\n"
                f"Required: Within {radius}m\n\n"
                f"Challenge: *{current_challenge['name']}*\n"
                f"Location: {current_challenge['location']}\n\n"
                f"Please move closer to the location and share your location again."
            )
            await update.message.reply_text(response, parse_mode='Markdown')
    
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
            
            # Clear the waiting state
            del context.user_data['waiting_for']
            
            # Route to the appropriate command handler with the text as argument
            if waiting_command == 'createteam':
                # Simulate command with args
                context.args = user_input.split()
                await self.create_team_command(update, context)
                return
            elif waiting_command == 'jointeam':
                context.args = user_input.split()
                await self.join_team_command(update, context)
                return
            elif waiting_command == 'submit':
                # For submit, we need to call it with the answer
                context.args = user_input.split()
                await self.submit_command(update, context)
                return
            elif waiting_command == 'addteam':
                context.args = user_input.split()
                await self.addteam_command(update, context)
                return
            elif waiting_command == 'removeteam':
                context.args = user_input.split()
                await self.removeteam_command(update, context)
                return
        
        # Send helpful message
        response = (
            "❓ I didn't understand that message.\n\n"
            "Use /help to see what you can do based on your current game state."
        )
        
        await update.message.reply_text(response)
    
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
        
        # Add callback query handlers
        application.add_handler(CallbackQueryHandler(
            self.photo_verification_callback_handler, 
            pattern="^verify_(approve|reject)_.*"
        ))
        application.add_handler(CallbackQueryHandler(
            self.photo_approval_callback_handler, 
            pattern="^(approve|reject)_.*"
        ))
        application.add_handler(CallbackQueryHandler(self.hint_callback_handler))
        
        # Add photo handler for photo submissions
        application.add_handler(MessageHandler(filters.PHOTO, self.photo_handler))
        
        # Add location handler for location verification
        application.add_handler(MessageHandler(filters.LOCATION, self.location_handler))
        
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
