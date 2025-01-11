import discord
from discord.ext import commands
import sqlite3
import os
from colorama import Fore, Style, init
import requests
import sys
import asyncio

VERSION_URL = "https://raw.githubusercontent.com/Reloisback/v4test/refs/heads/main/autoupdateinfo.txt"

def restart_bot():
    print(Fore.YELLOW + "\nRestarting bot..." + Style.RESET_ALL)
    python = sys.executable
    os.execl(python, python, *sys.argv)

def setup_version_table():
    try:
        with sqlite3.connect('db/settings.sqlite') as conn:
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS versions (
                file_name TEXT PRIMARY KEY,
                version TEXT,
                is_main INTEGER DEFAULT 0
            )''')
            conn.commit()
            print(Fore.GREEN + "Version table created successfully." + Style.RESET_ALL)
    except Exception as e:
        print(Fore.RED + f"Error creating version table: {e}" + Style.RESET_ALL)

async def check_and_update_files():
    try:
        response = requests.get(VERSION_URL)
        if response.status_code != 200:
            print(Fore.RED + "Failed to fetch version information from GitHub" + Style.RESET_ALL)
            return False

        content = response.text.split('\n')
        current_version = content[0].split('=')[1].strip()
        documents = {}
        main_py_updated = False

        
        doc_section = False
        for line in content[1:]:
            if line.startswith("Documants;"):
                doc_section = True
                continue
            elif line.startswith("Updated Info;"):
                break
            
            if doc_section and '=' in line:
                file_name, version = line.split('=')
                documents[file_name.strip()] = version.strip()

        
        update_notes = []
        update_section = False
        for line in content:
            if line.startswith("Updated Info;"):
                update_section = True
                continue
            if update_section and line.strip():
                update_notes.append(line.strip())

        
        updates_needed = []
        with sqlite3.connect('db/settings.sqlite') as conn:
            cursor = conn.cursor()
            
            
            cursor.execute("SELECT version FROM versions WHERE is_main = 1")
            db_version = cursor.fetchone()
            
            if not db_version:
                
                print(Fore.YELLOW + "First time setup detected" + Style.RESET_ALL)
                for file_name, version in documents.items():
                    
                    file_url = f"https://raw.githubusercontent.com/your_username/your_repo/main/{file_name}"
                    file_response = requests.get(file_url)
                    
                    if file_response.status_code == 200:
                        os.makedirs(os.path.dirname(file_name), exist_ok=True)
                        with open(file_name, 'w', encoding='utf-8') as f:
                            f.write(file_response.text)
                        
                        cursor.execute("""
                            INSERT INTO versions (file_name, version, is_main)
                            VALUES (?, ?, ?)
                        """, (file_name, version, 1 if file_name == 'main.py' else 0))
                
                conn.commit()
                print(Fore.GREEN + "Initial setup completed successfully" + Style.RESET_ALL)
                return True
            
            elif db_version[0] != current_version:
                
                for file_name, new_version in documents.items():
                    cursor.execute("SELECT version FROM versions WHERE file_name = ?", (file_name,))
                    current_file_version = cursor.fetchone()
                    
                    if not current_file_version or current_file_version[0] != new_version:
                        updates_needed.append((file_name, new_version))
                        if file_name.strip() == 'main.py':
                            main_py_updated = True

                if updates_needed:
                    print(Fore.YELLOW + "\nNew update available!" + Style.RESET_ALL)
                    print("\nFiles to be updated:")
                    for file_name, new_version in updates_needed:
                        print(f"• {file_name} -> {new_version}")
                    
                    print("\nUpdate Notes:")
                    for note in update_notes:
                        print(f"• {note}")

                    if main_py_updated:
                        print(Fore.YELLOW + "\nNOTE: This update includes changes to main.py. Bot will restart after update." + Style.RESET_ALL)

                    response = input("\nDo you want to update now? (y/n): ").lower()
                    if response == 'y':
                        
                        for file_name, new_version in updates_needed:
                            if file_name.strip() != 'main.py':
                                file_url = f"https://raw.githubusercontent.com/your_username/your_repo/main/{file_name}"
                                file_response = requests.get(file_url)
                                
                                if file_response.status_code == 200:
                                    os.makedirs(os.path.dirname(file_name), exist_ok=True)
                                    with open(file_name, 'w', encoding='utf-8') as f:
                                        f.write(file_response.text)
                                    
                                    cursor.execute("""
                                        INSERT OR REPLACE INTO versions (file_name, version, is_main)
                                        VALUES (?, ?, ?)
                                    """, (file_name, new_version, 0))

                        
                        if main_py_updated:
                            main_file_url = "https://raw.githubusercontent.com/your_username/your_repo/main/main.py"
                            main_response = requests.get(main_file_url)
                            
                            if main_response.status_code == 200:
                                
                                with open('main.py.new', 'w', encoding='utf-8') as f:
                                    f.write(main_response.text)
                                
                                
                                cursor.execute("""
                                    INSERT OR REPLACE INTO versions (file_name, version, is_main)
                                    VALUES (?, ?, 1)
                                """, ('main.py', current_version))
                                
                                conn.commit()
                                print(Fore.GREEN + "\nUpdate completed successfully!" + Style.RESET_ALL)
                                
                                
                                if os.path.exists('main.py.bak'):
                                    os.remove('main.py.bak')
                                os.rename('main.py', 'main.py.bak')
                                
                                
                                os.rename('main.py.new', 'main.py')
                                
                                print(Fore.YELLOW + "\nRestarting bot to apply main.py updates..." + Style.RESET_ALL)
                                restart_bot()
                        else:
                            conn.commit()
                            print(Fore.GREEN + "\nUpdate completed successfully!" + Style.RESET_ALL)
                    else:
                        print(Fore.YELLOW + "\nUpdate skipped. Running with existing files." + Style.RESET_ALL)

        return False

    except Exception as e:
        print(Fore.RED + f"Error during version check: {e}" + Style.RESET_ALL)
        return False

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='/', intents=intents)

init(autoreset=True)

token_file = 'bot_token.txt'
if not os.path.exists(token_file):
    bot_token = input("Enter the bot token: ")
    with open(token_file, 'w') as f:
        f.write(bot_token)
else:
    with open(token_file, 'r') as f:
        bot_token = f.read().strip()

if not os.path.exists('db'):
    os.makedirs('db')
    print(Fore.GREEN + "db folder created" + Style.RESET_ALL)

databases = {
    "conn_alliance": "db/alliance.sqlite",
    "conn_giftcode": "db/giftcode.sqlite",
    "conn_changes": "db/changes.sqlite",
    "conn_users": "db/users.sqlite",
    "conn_settings": "db/settings.sqlite",
}

connections = {name: sqlite3.connect(path) for name, path in databases.items()}

print(Fore.GREEN + "Database connections have been successfully established." + Style.RESET_ALL)

def create_tables():
    with connections["conn_changes"] as conn_changes:
        conn_changes.execute('''CREATE TABLE IF NOT EXISTS nickname_changes (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            fid INTEGER, 
            old_nickname TEXT, 
            new_nickname TEXT, 
            change_date TEXT
        )''')
        conn_changes.execute('''CREATE TABLE IF NOT EXISTS furnace_changes (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            fid INTEGER, 
            old_furnace_lv INTEGER, 
            new_furnace_lv INTEGER, 
            change_date TEXT
        )''')

    with connections["conn_settings"] as conn_settings:
        conn_settings.execute('''CREATE TABLE IF NOT EXISTS botsettings (
            id INTEGER PRIMARY KEY, 
            channelid INTEGER, 
            giftcodestatus TEXT 
        )''')
        conn_settings.execute('''CREATE TABLE IF NOT EXISTS admin (
            id INTEGER PRIMARY KEY, 
            is_initial INTEGER
        )''')

    with connections["conn_users"] as conn_users:
        conn_users.execute('''CREATE TABLE IF NOT EXISTS users (
            fid INTEGER PRIMARY KEY, 
            nickname TEXT, 
            furnace_lv INTEGER DEFAULT 0, 
            kid INTEGER, 
            stove_lv_content TEXT, 
            alliance TEXT
        )''')

    with connections["conn_giftcode"] as conn_giftcode:
        conn_giftcode.execute('''CREATE TABLE IF NOT EXISTS gift_codes (
            giftcode TEXT PRIMARY KEY, 
            date TEXT
        )''')
        conn_giftcode.execute('''CREATE TABLE IF NOT EXISTS user_giftcodes (
            fid INTEGER, 
            giftcode TEXT, 
            status TEXT, 
            PRIMARY KEY (fid, giftcode),
            FOREIGN KEY (giftcode) REFERENCES gift_codes (giftcode)
        )''')

    with connections["conn_alliance"] as conn_alliance:
        conn_alliance.execute('''CREATE TABLE IF NOT EXISTS alliancesettings (
            alliance_id INTEGER PRIMARY KEY, 
            channel_id INTEGER, 
            interval INTEGER
        )''')
        conn_alliance.execute('''CREATE TABLE IF NOT EXISTS alliance_list (
            alliance_id INTEGER PRIMARY KEY, 
            name TEXT
        )''')

    print(Fore.GREEN + "All tables checked." + Style.RESET_ALL)

create_tables()
setup_version_table()  

async def load_cogs():
    await bot.load_extension("cogs.olddb")
    await bot.load_extension("cogs.control")
    await bot.load_extension("cogs.alchannel")
    await bot.load_extension("cogs.alliance")
    await bot.load_extension("cogs.alliance_member_operations")
    await bot.load_extension("cogs.bot_operations")

@bot.event
async def on_ready():
    try:
        print(f"{bot.user} olarak giriş yapıldı!")
        print("Syncing all commands...")
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands!")
    except Exception as e:
        print(f"Error syncing commands: {e}")

async def main():
    
    await check_and_update_files()
    
    
    await load_cogs()
    await bot.start(bot_token)

if __name__ == "__main__":
    asyncio.run(main())
