"""
Telegram Amazing Race Bot - Main bot implementation
"""
import logging
import yaml
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
            "/reset - Reset the game\n\n"
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
            if i < current_challenge_index:
                # Completed challenge
                message += (
                    f"✅ *Challenge #{challenge['id']}: {challenge['name']}*\n"
                    f"   📍 Location: {challenge['location']}\n"
                    f"   📝 {challenge['description']}\n\n"
                )
            elif i == current_challenge_index:
                # Current challenge (unlocked)
                message += (
                    f"🎯 *Challenge #{challenge['id']}: {challenge['name']}* (CURRENT)\n"
                    f"   📍 Location: {challenge['location']}\n"
                    f"   📝 {challenge['description']}\n\n"
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
            await update.message.reply_text("Usage: /submit <challenge_id>")
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
        
        # Complete challenge
        if self.game_state.complete_challenge(team_name, challenge_id, len(self.challenges)):
            team = self.game_state.teams[team_name]
            completed = len(team['completed_challenges'])
            total = len(self.challenges)
            
            response = (
                f"🎉 Congratulations! Team '{team_name}' completed:\n"
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
        
        # Add error handler
        application.add_error_handler(self.error_handler)
        
        # Start the bot
        logger.info("Starting Amazing Race Bot...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    bot = AmazingRaceBot()
    bot.run()
