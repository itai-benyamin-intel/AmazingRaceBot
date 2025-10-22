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
        self.admins = set(self.config.get('admins', []))
    
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
        return user_id in self.admins
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /start command."""
        welcome_message = (
            f"🏁 Welcome to {self.config['game']['name']}! 🏁\n\n"
            "This is an interactive Amazing Race game.\n\n"
            "Available commands:\n"
            "/help - Show all commands\n"
            "/createteam <team_name> - Create a new team\n"
            "/jointeam <team_name> - Join an existing team\n"
            "/myteam - View your team info\n"
            "/leaderboard - View current standings\n"
            "/challenges - View all challenges\n"
            "/submit <challenge_id> - Submit a challenge completion\n\n"
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
            "/challenges - View all challenges\n"
            "/submit <challenge_id> - Submit challenge completion\n\n"
            "*Admin Commands:*\n"
            "/startgame - Start the game\n"
            "/endgame - End the game\n"
            "/reset - Reset all game data\n"
            "/teams - List all teams\n"
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
        
        message = (
            f"👥 *Team: {team_name}*\n\n"
            f"🏆 Score: {team['score']} points\n"
            f"📊 Challenges: {completed}/{total} completed\n\n"
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
        for i, (team_name, score) in enumerate(leaderboard, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            message += f"{medal} *{team_name}* - {score} points\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def challenges_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /challenges command."""
        user = update.effective_user
        team_name = self.game_state.get_team_by_user(user.id)
        
        completed_challenges = []
        if team_name:
            completed_challenges = self.game_state.teams[team_name]['completed_challenges']
        
        message = "🎯 *Challenges* 🎯\n\n"
        for challenge in self.challenges:
            status = "✅" if challenge['id'] in completed_challenges else "⭕"
            message += (
                f"{status} *Challenge #{challenge['id']}: {challenge['name']}*\n"
                f"   📍 Location: {challenge['location']}\n"
                f"   📝 {challenge['description']}\n"
                f"   🏆 Points: {challenge['points']}\n\n"
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
        
        # Complete challenge
        if self.game_state.complete_challenge(team_name, challenge_id, challenge['points']):
            await update.message.reply_text(
                f"🎉 Congratulations! Team '{team_name}' completed:\n"
                f"*{challenge['name']}*\n"
                f"Points earned: {challenge['points']}\n"
                f"Total score: {self.game_state.teams[team_name]['score']}",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("This challenge was already completed by your team!")
    
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
        
        for i, (team_name, score) in enumerate(leaderboard, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            message += f"{medal} *{team_name}* - {score} points\n"
        
        message += "\n🎉 Congratulations to all teams! 🎉"
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
        for team_name, team_data in self.game_state.teams.items():
            message += (
                f"*{team_name}*\n"
                f"  Members: {len(team_data['members'])}/{self.config['game']['max_team_size']}\n"
                f"  Score: {team_data['score']} points\n\n"
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
        application.add_handler(CommandHandler("startgame", self.start_game_command))
        application.add_handler(CommandHandler("endgame", self.end_game_command))
        application.add_handler(CommandHandler("reset", self.reset_command))
        application.add_handler(CommandHandler("teams", self.teams_command))
        
        # Add error handler
        application.add_error_handler(self.error_handler)
        
        # Start the bot
        logger.info("Starting Amazing Race Bot...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    bot = AmazingRaceBot()
    bot.run()
