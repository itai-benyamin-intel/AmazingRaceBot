"""
Telegram Amazing Race Bot - Main bot implementation
"""
import logging
import yaml
import math
from datetime import datetime
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
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /start command."""
        welcome_message = (
            f"🏁 Welcome to {self.config['game']['name']}! 🏁\n\n"
            "This is an interactive Amazing Race game.\n"
            "Complete challenges sequentially to win!\n\n"
            "Available commands:\n"
            "/help - Show all commands\n"
            "/createteam <team_name> - Create a new team\n"
            "/jointeam <team_name> - Join an existing team\n"
            "/myteam - View your team info\n"
            "/leaderboard - View current standings\n"
            "/challenges - View challenges\n"
            "/submit <challenge_id> - Submit a challenge completion\n"
            "/contact - Contact the bot admin\n\n"
            "Admin commands:\n"
            "/startgame - Start the game\n"
            "/endgame - End the game\n"
            "/reset - Reset the game\n"
            "/setlocation - Set challenge location (admin)\n"
            "/togglelocation - Toggle location verification (admin)\n\n"
            "Good luck! 🎯"
        )
        await update.message.reply_text(welcome_message)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /help command."""
        help_text = (
            "📋 *Available Commands:*\n\n"
            "*Player Commands:*\n"
            "/start - Show welcome message\n"
            "/createteam <name> - Create a new team\n"
            "/jointeam <name> - Join an existing team\n"
            "/myteam - View your team information\n"
            "/leaderboard - View current standings\n"
            "/challenges - View challenges (sequential)\n"
            "/submit <challenge_id> - Submit challenge completion\n"
            "/teams - List all teams\n"
            "/contact - Contact the bot admin\n\n"
            "*Admin Commands:*\n"
            "/startgame - Start the game\n"
            "/endgame - End the game\n"
            "/reset - Reset all game data\n"
            "/teamstatus - View detailed team status\n"
            "/addteam <name> - Create a team (admin)\n"
            "/editteam <old> <new> - Rename a team\n"
            "/removeteam <name> - Remove a team\n"
            "/setlocation <id> <lat> <lon> [radius] - Set challenge location\n"
            "/togglelocation - Toggle location verification on/off\n"
        )
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def create_team_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /createteam command."""
        if not context.args:
            await update.message.reply_text("Usage: /createteam <team_name>")
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
            await update.message.reply_text("Usage: /jointeam <team_name>")
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
        """Handle the /leaderboard command."""
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
        """Handle the /challenges command."""
        user = update.effective_user
        team_name = self.game_state.get_team_by_user(user.id)
        
        completed_challenges = []
        current_challenge_index = 0
        
        if team_name:
            team = self.game_state.teams[team_name]
            completed_challenges = team['completed_challenges']
            current_challenge_index = team.get('current_challenge_index', 0)
        
        message = "🎯 *Challenges* 🎯\n\n"
        
        for i, challenge in enumerate(self.challenges):
            challenge_type = challenge.get('type', 'text')
            type_emoji = self.get_challenge_type_emoji(challenge_type)
            
            if i < current_challenge_index:
                # Completed challenge
                message += (
                    f"✅ *Challenge #{challenge['id']}: {challenge['name']}*\n"
                    f"   {type_emoji} Type: {challenge_type}\n"
                    f"   📍 Location: {challenge['location']}\n"
                    f"   📝 {challenge['description']}\n\n"
                )
            elif i == current_challenge_index:
                # Current challenge (unlocked)
                instructions = self.get_challenge_instructions(challenge)
                message += (
                    f"🎯 *Challenge #{challenge['id']}: {challenge['name']}* (CURRENT)\n"
                    f"   {type_emoji} Type: {challenge_type}\n"
                    f"   📍 Location: {challenge['location']}\n"
                    f"   📝 {challenge['description']}\n"
                    f"   ℹ️ {instructions}\n\n"
                )
            else:
                # Locked challenge
                message += (
                    f"🔒 *Challenge #{challenge['id']}:* LOCKED\n"
                    f"   Complete previous challenges to unlock\n\n"
                )
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def submit_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /submit command."""
        if not context.args:
            await update.message.reply_text(
                "Usage: /submit <challenge_id> [answer]\n"
                "For photo challenges: /submit <challenge_id> then send a photo\n"
                "For text/answer challenges: /submit <challenge_id> <your answer>"
            )
            return
        
        try:
            challenge_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("Invalid challenge ID!")
            return
        
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
        
        # Find challenge
        challenge = next((c for c in self.challenges if c['id'] == challenge_id), None)
        if not challenge:
            await update.message.reply_text("Challenge not found!")
            return
        
        # Get current challenge that should be completed
        team = self.game_state.teams[team_name]
        expected_challenge_id = team.get('current_challenge_index', 0) + 1
        
        # Check if this is the correct challenge to complete
        if challenge_id != expected_challenge_id:
            if challenge_id in team['completed_challenges']:
                await update.message.reply_text("This challenge was already completed by your team!")
            else:
                await update.message.reply_text(
                    f"You must complete challenges in order!\n"
                    f"Your current challenge is #{expected_challenge_id}."
                )
            return
        
        # Check location verification for challenges 2 onwards (if enabled)
        if self.game_state.location_verification_enabled and challenge_id > 1:
            location_verifications = team.get('location_verifications', {})
            if str(challenge_id) not in location_verifications:
                # Location not verified yet
                coordinates = challenge.get('coordinates', {})
                if coordinates and coordinates.get('latitude') is not None:
                    await update.message.reply_text(
                        f"📍 *Location Verification Required*\n\n"
                        f"Please share your location before submitting this challenge.\n"
                        f"You must be at: {challenge['location']}\n\n"
                        f"To share your location:\n"
                        f"1. Tap the attachment button (📎)\n"
                        f"2. Select 'Location'\n"
                        f"3. Choose 'Send My Current Location'",
                        parse_mode='Markdown'
                    )
                    return
        
        # Get verification method
        verification = challenge.get('verification', {})
        method = verification.get('method', 'photo')
        
        # Handle different verification methods
        if method == 'answer':
            # Text answer verification
            if len(context.args) < 2:
                await update.message.reply_text(
                    f"Please provide your answer:\n"
                    f"/submit {challenge_id} <your answer>"
                )
                return
            
            user_answer = ' '.join(context.args[1:])
            
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
                    
                    await update.message.reply_text(response, parse_mode='Markdown')
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
        await update.message.reply_text(
            "🏁 *THE GAME HAS STARTED!* 🏁\n\n"
            "Teams can now start completing challenges!\n"
            "Use /challenges to see available challenges.\n"
            "Good luck! 🎯",
            parse_mode='Markdown'
        )
    
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
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def reset_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /reset command (admin only)."""
        user = update.effective_user
        if not self.is_admin(user.id):
            await update.message.reply_text("Only admins can reset the game!")
            return
        
        self.game_state.reset_game()
        await update.message.reply_text("✅ Game has been reset! All data cleared.")
    
    async def teams_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /teams command."""
        if not self.game_state.teams:
            await update.message.reply_text("No teams created yet!")
            return
        
        message = "👥 *Teams* 👥\n\n"
        total_challenges = len(self.challenges)
        
        for team_name, team_data in self.game_state.teams.items():
            completed = len(team_data['completed_challenges'])
            status = "✅ FINISHED" if team_data.get('finish_time') else f"{completed}/{total_challenges}"
            message += (
                f"*{team_name}*\n"
                f"  Members: {len(team_data['members'])}/{self.config['game']['max_team_size']}\n"
                f"  Progress: {status}\n\n"
            )
        
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
            await update.message.reply_text("Usage: /addteam <team_name>")
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
            await update.message.reply_text("Usage: /removeteam <team_name>")
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
        """Handle photo submissions for challenges."""
        user = update.effective_user
        
        # Check if user has a pending photo submission
        if 'pending_submissions' not in context.bot_data:
            context.bot_data['pending_submissions'] = {}
        
        if user.id not in context.bot_data['pending_submissions']:
            # No pending submission, ignore the photo
            return
        
        pending = context.bot_data['pending_submissions'][user.id]
        team_name = pending['team_name']
        challenge_id = pending['challenge_id']
        challenge_name = pending['challenge_name']
        
        # Get the photo
        photo = update.message.photo[-1]  # Get highest resolution
        
        # Store submission data
        submission_data = {
            'type': 'photo',
            'photo_id': photo.file_id,
            'timestamp': datetime.now().isoformat(),
            'submitted_by': user.id,
            'user_name': user.first_name,
            'team_name': team_name,
            'status': 'pending'  # pending, approved, rejected
        }
        
        # Complete the challenge with submission data
        if self.game_state.complete_challenge(team_name, challenge_id, len(self.challenges), submission_data):
            team = self.game_state.teams[team_name]
            completed = len(team['completed_challenges'])
            total = len(self.challenges)
            
            response = (
                f"✅ Photo submitted for:\n"
                f"*{challenge_name}*\n\n"
                f"Your submission has been recorded and the challenge is marked as complete!\n"
                f"Progress: {completed}/{total} challenges"
            )
            
            # Check if team finished all challenges
            if team.get('finish_time'):
                response += f"\n\n🏆 *CONGRATULATIONS!* 🏆\n"
                response += f"Your team finished the race!\n"
                response += f"Finish time: {team['finish_time']}"
            
            await update.message.reply_text(response, parse_mode='Markdown')
            
            # Notify admin
            if self.admin_id:
                try:
                    await context.bot.send_photo(
                        chat_id=self.admin_id,
                        photo=photo.file_id,
                        caption=(
                            f"📷 *New Photo Submission*\n"
                            f"Team: {team_name}\n"
                            f"Challenge #{challenge_id}: {challenge_name}\n"
                            f"Submitted by: {user.first_name}\n"
                            f"Status: Automatically accepted (challenge marked complete)"
                        ),
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.error(f"Failed to notify admin: {e}")
            
            # Remove pending submission
            del context.bot_data['pending_submissions'][user.id]
        else:
            await update.message.reply_text("Error processing photo. Please try again.")
    
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
                f"Use /submit {current_challenge['id']} to submit your answer."
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
        """Handle the /approve command (admin only) - for manual verification if needed in future."""
        user = update.effective_user
        if not self.is_admin(user.id):
            await update.message.reply_text("Only admins can approve submissions!")
            return
        
        await update.message.reply_text(
            "ℹ️ Photo submissions are currently auto-approved.\n"
            "This command is reserved for future manual verification features."
        )
    
    async def reject_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /reject command (admin only) - for manual verification if needed in future."""
        user = update.effective_user
        if not self.is_admin(user.id):
            await update.message.reply_text("Only admins can reject submissions!")
            return
        
        await update.message.reply_text(
            "ℹ️ Photo submissions are currently auto-approved.\n"
            "This command is reserved for future manual verification features."
        )
    
    async def setlocation_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /setlocation command (admin only) - set coordinates for a challenge."""
        user = update.effective_user
        if not self.is_admin(user.id):
            await update.message.reply_text("Only admins can set challenge locations!")
            return
        
        if len(context.args) < 3:
            await update.message.reply_text(
                "Usage: /setlocation <challenge_id> <latitude> <longitude> [radius]\n"
                "Example: /setlocation 2 37.7749 -122.4194 100\n\n"
                "Note: This updates the runtime configuration, not the config.yml file."
            )
            return
        
        try:
            challenge_id = int(context.args[0])
            latitude = float(context.args[1])
            longitude = float(context.args[2])
            radius = int(context.args[3]) if len(context.args) > 3 else 100
            
            # Validate latitude and longitude ranges
            if not (-90 <= latitude <= 90):
                await update.message.reply_text("❌ Invalid latitude! Must be between -90 and 90.")
                return
            
            if not (-180 <= longitude <= 180):
                await update.message.reply_text("❌ Invalid longitude! Must be between -180 and 180.")
                return
            
            if radius <= 0:
                await update.message.reply_text("❌ Invalid radius! Must be greater than 0.")
                return
            
            # Find the challenge
            challenge = next((c for c in self.challenges if c['id'] == challenge_id), None)
            if not challenge:
                await update.message.reply_text(f"❌ Challenge #{challenge_id} not found!")
                return
            
            # Update challenge coordinates
            if 'coordinates' not in challenge:
                challenge['coordinates'] = {}
            
            challenge['coordinates']['latitude'] = latitude
            challenge['coordinates']['longitude'] = longitude
            challenge['coordinates']['radius'] = radius
            
            await update.message.reply_text(
                f"✅ Location set for Challenge #{challenge_id}: {challenge['name']}\n"
                f"📍 Coordinates: {latitude}, {longitude}\n"
                f"📏 Radius: {radius}m\n\n"
                f"⚠️ Note: This is a runtime change and will be lost if the bot restarts.\n"
                f"To make it permanent, update config.yml"
            )
        
        except ValueError:
            await update.message.reply_text("❌ Invalid input! Please provide valid numbers.")
    
    async def togglelocation_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /togglelocation command (admin only) - toggle location verification."""
        user = update.effective_user
        if not self.is_admin(user.id):
            await update.message.reply_text("Only admins can toggle location verification!")
            return
        
        new_state = self.game_state.toggle_location_verification()
        
        status = "enabled ✅" if new_state else "disabled ❌"
        message = f"📍 Location verification is now *{status}*\n\n"
        
        if new_state:
            message += (
                "Teams must now verify their location before submitting challenges 2 onwards.\n"
                "They can share their location using Telegram's location attachment feature.\n\n"
                "To share location:\n"
                "1. Tap the attachment button (📎)\n"
                "2. Select 'Location'\n"
                "3. Choose 'Send My Current Location'"
            )
        else:
            message += (
                "Teams can now submit challenges without location verification.\n"
                "Location verification can be re-enabled at any time."
            )
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    
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
        application.add_handler(CommandHandler("setlocation", self.setlocation_command))
        application.add_handler(CommandHandler("togglelocation", self.togglelocation_command))
        
        # Add photo handler for photo submissions
        application.add_handler(MessageHandler(filters.PHOTO, self.photo_handler))
        
        # Add location handler for location verification
        application.add_handler(MessageHandler(filters.LOCATION, self.location_handler))
        
        # Add error handler
        application.add_error_handler(self.error_handler)
        
        # Start the bot
        logger.info("Starting Amazing Race Bot...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    bot = AmazingRaceBot()
    bot.run()
