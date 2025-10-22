#!/usr/bin/env python3
"""
Quick start script for the Amazing Race Bot.
This script helps you set up and run the bot.
"""
import os
import sys
import shutil


def check_config():
    """Check if config.yml exists, if not create from example."""
    if not os.path.exists('config.yml'):
        if os.path.exists('config.example.yml'):
            print("📋 config.yml not found. Creating from config.example.yml...")
            shutil.copy('config.example.yml', 'config.yml')
            print("✅ Created config.yml")
            print("\n⚠️  IMPORTANT: Edit config.yml and add your bot token!")
            print("   Get your token from @BotFather on Telegram")
            print("   Then run this script again.\n")
            return False
        else:
            print("❌ Error: config.example.yml not found!")
            return False
    return True


def check_bot_token():
    """Check if bot token is configured."""
    try:
        import yaml
        with open('config.yml', 'r') as f:
            config = yaml.safe_load(f)
            token = config.get('telegram', {}).get('bot_token', '')
            if token == 'YOUR_BOT_TOKEN_HERE' or not token:
                print("⚠️  Bot token not configured!")
                print("   Edit config.yml and replace 'YOUR_BOT_TOKEN_HERE'")
                print("   with your actual bot token from @BotFather\n")
                return False
    except Exception as e:
        print(f"❌ Error reading config: {e}")
        return False
    return True


def check_dependencies():
    """Check if required packages are installed."""
    try:
        import telegram
        import yaml
        return True
    except ImportError as e:
        print("❌ Missing dependencies!")
        print("   Run: pip install -r requirements.txt\n")
        return False


def main():
    """Main function."""
    print("🏁 Amazing Race Bot Setup 🏁\n")
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Check config
    if not check_config():
        sys.exit(1)
    
    # Check bot token
    if not check_bot_token():
        sys.exit(1)
    
    print("✅ Configuration looks good!")
    print("\n🚀 Starting the bot...\n")
    
    # Import and run the bot
    try:
        from bot import AmazingRaceBot
        bot = AmazingRaceBot()
        bot.run()
    except KeyboardInterrupt:
        print("\n\n👋 Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
