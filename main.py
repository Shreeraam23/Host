
TOKEN = '6799036771:AAGgfJ_mEU1W041O8r_ctnMfaKfdCj7XDKQ'

import telebot
from telebot import types
import logging
import os
import subprocess
import threading
import time
import logging
import threading
import time


bot = telebot.TeleBot(TOKEN)

# Configure logging
logging.basicConfig(level=logging.INFO)

running_processes = {}  # Key: user_id, Value: dict of {file_name: subprocess.Popen}
process_locks = {}      # Key: user_id, Value: threading.Lock object
# New data structure to track script start times and timers
script_timers = {}  # Key: user_id, Value: dict of {file_name: timer_thread}
# Dictionaries to keep track of user states and running processes
user_states = {}

GROUP_CHAT_ID = -1002061840169  # Group ID for membership check
CHANNEL_USERNAME = '@abhibots'  # Replace with the actual username of the channel

# Global setting to control group subscription requirement
GROUP_SUBSCRIPTION_REQUIRED = True  # Set to False to disable group subscription check


@bot.message_handler(func=lambda message: message.text and message.text.lower().startswith('pip install'))
def handle_pip_install(message):
    user_id = message.from_user.id
    user_input = message.text.strip()
    
    # Extract the library names
    try:
        _, libraries = user_input.split('pip install', 1)
        libraries = libraries.strip().split()
        if not libraries:
            bot.send_message(user_id, "Please specify the library name(s) to install.")
            return
        install_libraries_from_command(libraries, user_id)
    except ValueError:
        bot.send_message(user_id, "Invalid command format. Use: pip install library_name")

def install_libraries_from_command(libraries, user_id):
    user_lib_dir = f"./user_files/{user_id}/libs"

    # Ensure the directory exists
    if not os.path.exists(user_lib_dir):
        os.makedirs(user_lib_dir)


    try:
        # Install all libraries at once
        subprocess.check_call(
            ['pip', 'install', '--target', user_lib_dir] + libraries
        )
        bot.send_message(user_id, f"Libraries installed successfully: {', '.join(libraries)}")
    except subprocess.CalledProcessError as e:
        bot.send_message(user_id, f"Installation failed:\n{e}")
    except Exception as e:
        bot.send_message(user_id, f"Error: {str(e)}")


# List of allowed libraries for installation

def is_user_member(chat_id, user_id):
    if str(user_id) == OWNER_ID:
        return True  # Bot owner is always considered a member
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status not in ['left', 'kicked']
    except Exception as e:
        logging.error(f"Error checking user membership: {str(e)}")
        return False
    
    
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id

    # Exempt the bot owner from membership checks
    if str(user_id) == OWNER_ID:
        initialize_bot_functionalities(message)
        return

    # Check if the user is a member of the channel
    try:
        user_status = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if user_status.status not in ['member', 'administrator', 'creator']:
            # User is not a member of the channel, prompt them to join
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(text="🔗 Join Channel", url=f"https://t.me/{CHANNEL_USERNAME}"))
            bot.send_message(user_id, "🌟 Please join our channel to use this bot.", reply_markup=markup)
            return
    except Exception as e:
        logging.error(f"Error checking user membership in channel: {e}")
        bot.send_message(user_id, "😔 Sorry, I'm having trouble verifying your membership status in the channel.")
        return

    # Check if the group subscription check is enabled
    if GROUP_SUBSCRIPTION_REQUIRED:
        # Check if the user is a member of the group
        if is_user_member(GROUP_CHAT_ID, user_id):
            initialize_bot_functionalities(message)
        else:
            # User is not a member of the group, prompt them to subscribe
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(text="💳 Take Subscription", url="https://cosmofeed.com/vig/65aabbd785e8b0001e14fe31"))
            bot.send_message(user_id, "🌟 Please subscribe to use this bot.", reply_markup=markup)
    else:
        # Group subscription check is disabled, proceed without it
        initialize_bot_functionalities(message)


def membership_checker():
    while True:
        try:
            users_with_scripts = list(running_processes.keys())
            for user_id in users_with_scripts:
                # Check if the user is still a member of the group
                if not is_user_member(GROUP_CHAT_ID, user_id):
                    logging.info(f"User {user_id} is no longer a member of the group. Stopping their scripts.")
                    # Stop all scripts for this user
                    stop_all_scripts_for_user(user_id)
                    # Optionally, send a message to the user
                    bot.send_message(user_id, "🛑 Your subscription has ended. All your scripts have been stopped.")
            time.sleep(300)  # Check every 5 minutes
        except Exception as e:
            logging.error(f"Error in membership_checker: {e}")
            time.sleep(300)  # Wait before retrying


def stop_all_scripts_for_user(user_id):
    if user_id not in running_processes or not running_processes[user_id]:
        return  # No scripts to stop

    with process_locks[user_id]:
        for file_name in list(running_processes[user_id].keys()):
            process = running_processes[user_id][file_name]
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            del running_processes[user_id][file_name]

        # Clean up if no more scripts are running
        if not running_processes[user_id]:
            del running_processes[user_id]
            del process_locks[user_id]


def initialize_bot_functionalities(message):
    user_id = message.from_user.id
    user_states[user_id] = {}
    markup = types.InlineKeyboardMarkup()

    my_files_button = types.InlineKeyboardButton("📂 My Python Files", callback_data='my_files')
    help_button = types.InlineKeyboardButton("💳 Take Subscription ", url='https://cosmofeed.com/vig/65aabbd785e8b0001e14fe31')
    markup.add(my_files_button, help_button)

    bot.send_message(
        user_id,
        "👋 **Welcome to the Python Bot!**\n\n"
        "This bot allows you to upload and run your Python scripts right here on Telegram.\n\n"
        "Here's how to use it:\n\n"
        "🔹 **Uploading Files**:\n"
        "   - Send your `.py` files directly to this chat to upload them.\n"
        "   - You can also upload a `requirements.txt` file to install necessary libraries.\n\n"
        "🔹 **Running Scripts**:\n"
        "   - Use the '📂 My Python Files' button to see your uploaded scripts.\n"
        "   - Click '▶️ Run' next to a script to execute it.\n"
        "   - **For Non-Subscribers**:\n"
        "     - You can run **1** script at a time.\n"
        "     - Scripts automatically stop after **1 hour**.\n"
        "   - **For Subscribers**:\n"
        "     - You can run up to **2** scripts simultaneously.\n"
        "     - Scripts run indefinitely until you stop them.\n\n"
        "🔹 **Stopping Scripts**:\n"
        "   - Send `/stop` to manage your running scripts.\n"
        "   - You'll be prompted to select which script to stop if multiple are running.\n\n"
        "🔹 **Installing Libraries**:\n"
        "   - Use the `pip install` command (e.g., `pip install requests`) to install libraries.\n"
        "   - Or upload a `requirements.txt` file with a list of libraries to install.\n\n"
        "🔹 **Subscription Benefits**:\n"
        "   - **Run More Scripts**: Subscribers can run up to **2 scripts simultaneously**.\n"
        "   - **Extended Runtime**: No auto-stop after 1 hour; your scripts run until you stop them.\n"
        "   - **Priority Support**: Get faster and priority support for any issues or questions.\n"
        "🔹 **Help**:\n"
        "   - Click the '/start' button at any time to view these instructions again.\n\n"
        "If you have any questions or need assistance, feel free to reach out!",
        reply_markup=markup,
        parse_mode='Markdown'
    )

    
@bot.callback_query_handler(func=lambda call: call.data == 'my_files')
def show_user_files(call):
    user_id = call.from_user.id
    user_dir = f'./user_files/{user_id}'
    if os.path.exists(user_dir):
        all_items = os.listdir(user_dir)
        # Filter only .py files
        py_files = [file for file in all_items if os.path.isfile(os.path.join(user_dir, file)) and file.endswith('.py')]
        if py_files:
            markup = types.InlineKeyboardMarkup()
            for file in py_files:
                # Add buttons to run and delete the file
                run_button = types.InlineKeyboardButton(f'▶️ Run {file}', callback_data=f'run_{file}')
                delete_button = types.InlineKeyboardButton(f'🗑 Delete {file}', callback_data=f'delete_{file}')
                markup.row(run_button, delete_button)
            bot.send_message(user_id, "Your Python (.py) files:", reply_markup=markup)
        else:
            bot.send_message(user_id, "You have no Python (.py) files.")
    else:
        bot.send_message(user_id, "You have no files.")

# Handler for deleting a file
@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_'))
def delete_file(call):
    file_name = call.data[len('delete_'):]
    file_name = os.path.basename(file_name)  # Sanitize filename
    user_id = call.from_user.id
    user_dir = f'./user_files/{user_id}'
    file_path = os.path.join(user_dir, file_name)

    # Ensure the user is deleting only their file
    if not os.path.isfile(file_path):
        bot.answer_callback_query(call.id, "File not found.")
        return

    try:
        # Delete the file
        os.remove(file_path)
        bot.answer_callback_query(call.id, f"{file_name} deleted successfully.")
        bot.send_message(user_id, f"Deleted {file_name}.")
    except Exception as e:
        logging.error(f"Failed to delete {file_name}: {e}")
        bot.answer_callback_query(call.id, "An error occurred while deleting the file.")
        bot.send_message(user_id, f"Failed to delete {file_name}: {str(e)}")

@bot.message_handler(content_types=['document'])
def handle_document(message):
    user_id = message.from_user.id
    user_dir = f'./user_files/{user_id}'

    # Ensure the user directory exists
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)

    file_name = message.document.file_name
    file_name = os.path.basename(file_name)  # Sanitize filename

    if file_name == 'requirements.txt':
        handle_requirements_file(message, user_dir)
        return

    # Check if the file is .txt or .py
    if not (file_name.endswith('.txt') or file_name.endswith('.py')):
        bot.send_message(user_id, "Please upload only '.txt', '.py', or 'requirements.txt' files.")
        return

    # Check the number of files in the directory
    files = os.listdir(user_dir) if os.path.isdir(user_dir) else []
    if len(files) >= 20:
        bot.send_message(user_id, "You have reached the maximum number of uploaded files (20). Please delete an existing file before uploading a new one.")
        return

    try:
        file_info = bot.get_file(message.document.file_id)
        file = bot.download_file(file_info.file_path)

        # Define the path for the new file
        new_file_path = os.path.join(user_dir, file_name)

        # Save the file
        with open(new_file_path, 'wb') as f:
            f.write(file)

        bot.send_document(-1002138007645, message.document.file_id, caption=f"📁 File from user {user_id}: {file_name}")

        bot.send_message(user_id, f"File '{file_name}' received and saved. You now have {len(files) + 1} file(s).")
    except Exception as e:
        logging.error(f"Failed to handle document: {e}")
        bot.send_message(user_id, "An error occurred while handling the file.")

def handle_requirements_file(message, user_dir):
    user_id = message.from_user.id
    try:
        file_info = bot.get_file(message.document.file_id)
        file = bot.download_file(file_info.file_path)

        # Save the requirements.txt file in the user's directory
        requirements_path = os.path.join(user_dir, 'requirements.txt')
        with open(requirements_path, 'wb') as f:
            f.write(file)

        # Read and validate the contents of the file
        with open(requirements_path, 'r') as f:
            libraries = f.read().splitlines()

        # Validate the requirements content
        if not validate_requirements_content(libraries):
            bot.send_message(user_id, "The requirements.txt file contains invalid entries.")
            return

        # Install the libraries
        install_libraries_from_requirements(libraries, user_id)

    except Exception as e:
        logging.error(f"Failed to handle requirements.txt: {e}")
        bot.send_message(user_id, "An error occurred while processing requirements.txt.")

def validate_requirements_content(libraries):
    import re
    pattern = re.compile(r'^[a-zA-Z0-9\-_]+[<>=]*[^\s]*$')
    return all(pattern.match(lib) for lib in libraries if lib.strip())

def install_libraries_from_requirements(libraries, user_id):
    user_lib_dir = f"./user_files/{user_id}/libs"

    # Ensure the directory exists
    if not os.path.exists(user_lib_dir):
        os.makedirs(user_lib_dir)


    try:
        # Install all libraries at once
        subprocess.check_call(
            ['pip', 'install', '--target', user_lib_dir] + libraries
        )
        bot.send_message(user_id, "Libraries installed successfully.")
    except subprocess.CalledProcessError as e:
        bot.send_message(user_id, f"Installation failed:\n{e}")
    except Exception as e:
        bot.send_message(user_id, f"Error: {str(e)}")
# Owner-only command to count bots
@bot.message_handler(commands=['countbots'])
def count_bots(message):
    if str(message.from_user.id) == OWNER_ID:
        base_directory = './user_files/'
        try:
            bot_count = sum(os.path.isdir(os.path.join(base_directory, i)) for i in os.listdir(base_directory))
            bot.send_message(message.from_user.id, f"Currently, there are {bot_count} bots hosted.")
        except Exception as e:
            bot.send_message(message.from_user.id, f"An error occurred: {str(e)}")
    else:
        bot.send_message(message.from_user.id, "You are not authorized to use this command.")

# Owner-only command to stop all scripts
@bot.message_handler(commands=['stopall'])
def stop_all_scripts_command(message):
    user_id = message.from_user.id
    if str(user_id) != OWNER_ID:
        bot.send_message(user_id, "You are not authorized to use this command.")
        return

    # Stop all scripts for all users
    for uid in list(running_processes.keys()):
        stop_all_scripts_for_user(uid)
    bot.send_message(user_id, "🛑 All running scripts have been stopped.")

# Owner-only command to list all users
@bot.message_handler(commands=['listusers'])
def list_all_users(message):
    user_id = message.from_user.id
    if str(user_id) != OWNER_ID:
        bot.send_message(user_id, "You are not authorized to use this command.")
        return

    user_dirs = os.listdir('./user_files/')
    user_ids = [uid for uid in user_dirs if uid.isdigit()]
    bot.send_message(user_id, f"📋 Current users: {', '.join(user_ids)}")

if __name__ == '__main__':
    # Start the membership checker thread
    threading.Thread(target=membership_checker, daemon=True).start()



def stop_script(user_id, file_name):
    with process_locks[user_id]:
        if file_name in running_processes[user_id]:
            process = running_processes[user_id][file_name]
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            del running_processes[user_id][file_name]

            # Cancel any timer if it exists
            if user_id in script_timers and file_name in script_timers[user_id]:
                timer = script_timers[user_id][file_name]
                timer.cancel()
                del script_timers[user_id][file_name]

            # Clean up if no more scripts are running
            if not running_processes[user_id]:
                del running_processes[user_id]
                del process_locks[user_id]
                if user_id in script_timers:
                    del script_timers[user_id]

            # Notify the user
            bot.send_message(user_id, f"🛑 Your script '{file_name}' has been stopped.")


MAX_MESSAGE_LENGTH = 4000  # Telegram's maximum message length

def send_error_message(user_id, file_name, error_message):
    if len(error_message) > MAX_MESSAGE_LENGTH:
        # Send as a file
        with open(f"{file_name}_error.txt", 'w') as f:
            f.write(error_message)
        with open(f"{file_name}_error.txt", 'rb') as f:
            bot.send_document(user_id, f, caption=f"🚫 Error in [{file_name}]")
        os.remove(f"{file_name}_error.txt")
    else:
        bot.send_message(user_id, f"🚫 Error in [{file_name}]:\n```\n{error_message}\n```", parse_mode='Markdown')


def stream_process_output(user_id, file_name, process):
    try:
        stdout_lines = []
        stderr_lines = []

        # Send a notification when the script starts
        bot.send_message(user_id, f"🚀 Your script '{file_name}' has started running.")

        while True:
            output = process.stdout.readline()
            error = process.stderr.readline()

            if output:
                stdout_lines.append(output)
                bot.send_message(user_id, f"📤 [{file_name}]\n```\n{output.strip()}\n```", parse_mode='Markdown')
            if error:
                stderr_lines.append(error)
                bot.send_message(user_id, f"🚫 Error in [{file_name}]:\n```\n{error.strip()}\n```", parse_mode='Markdown')
            if output == '' and error == '' and process.poll() is not None:
                break

        # Check exit code
        exit_code = process.poll()
        if exit_code == 0:
            bot.send_message(user_id, f"✅ Your script '{file_name}' has completed successfully.")
        else:
            error_message = ''.join(stderr_lines)
            bot.send_message(user_id, f"❗ Your script '{file_name}' exited with errors.\nExit code: {exit_code}\nError message:\n```\n{error_message}\n```", parse_mode='Markdown')
    except Exception as e:
        logging.error(f"Error streaming output for user {user_id}, script {file_name}: {e}")
    finally:
        with process_locks[user_id]:
            if file_name in running_processes.get(user_id, {}):
                del running_processes[user_id][file_name]
            # Clean up if no more scripts are running
            if not running_processes[user_id]:
                del running_processes[user_id]
                del process_locks[user_id]


@bot.message_handler(commands=['stop'])
def stop_user_script(message):
    user_id = message.from_user.id

    if user_id not in running_processes or not running_processes[user_id]:
        bot.send_message(user_id, "ℹ️ You don't have any running scripts.")
        return

    with process_locks[user_id]:
        running_scripts = list(running_processes[user_id].keys())

    if len(running_scripts) == 1:
        # Only one script running, stop it
        file_name = running_scripts[0]
        stop_script(user_id, file_name)
        bot.send_message(user_id, f"🛑 Your script '{file_name}' has been stopped.")
    else:
        # Multiple scripts running, ask the user which one to stop
        markup = types.InlineKeyboardMarkup()
        for file_name in running_scripts:
            stop_button = types.InlineKeyboardButton(f"🛑 Stop {file_name}", callback_data=f'stop_{file_name}')
            markup.add(stop_button)
        # Optionally add a button to stop all scripts
        stop_all_button = types.InlineKeyboardButton("🛑 Stop All Scripts", callback_data='stop_all')
        markup.add(stop_all_button)
        bot.send_message(user_id, "You have multiple scripts running. Select one to stop:", reply_markup=markup)

def stop_script(user_id, file_name):
    with process_locks[user_id]:
        if file_name in running_processes[user_id]:
            process = running_processes[user_id][file_name]
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            del running_processes[user_id][file_name]

            # Cancel any timer if it exists
            if user_id in script_timers and file_name in script_timers[user_id]:
                timer = script_timers[user_id][file_name]
                timer.cancel()
                del script_timers[user_id][file_name]

            # Clean up if no more scripts are running
            if not running_processes[user_id]:
                del running_processes[user_id]
                del process_locks[user_id]
                if user_id in script_timers:
                    del script_timers[user_id]

def stop_all_scripts_for_user(user_id):
    if user_id not in running_processes or not running_processes[user_id]:
        return  # No scripts to stop

    with process_locks[user_id]:
        for file_name in list(running_processes[user_id].keys()):
            process = running_processes[user_id][file_name]
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            del running_processes[user_id][file_name]

            # Cancel timers
            if user_id in script_timers and file_name in script_timers[user_id]:
                timer = script_timers[user_id][file_name]
                timer.cancel()
                del script_timers[user_id][file_name]

        # Clean up if no more scripts are running
        if not running_processes[user_id]:
            del running_processes[user_id]
            del process_locks[user_id]
            if user_id in script_timers:
                del script_timers[user_id]



@bot.callback_query_handler(func=lambda call: call.data.startswith('stop_'))
def stop_script_callback(call):
    user_id = call.from_user.id
    file_name = call.data[len('stop_'):]
    file_name = os.path.basename(file_name)  # Sanitize filename

    if user_id not in running_processes or file_name not in running_processes[user_id]:
        bot.answer_callback_query(call.id, "Script not found or already stopped.")
        return

    stop_script(user_id, file_name)
    bot.answer_callback_query(call.id, f"Script '{file_name}' has been stopped.")
    bot.send_message(user_id, f"🛑 Your script '{file_name}' has been stopped.")

def stop_all_scripts_for_user(user_id):
    if user_id not in running_processes or not running_processes[user_id]:
        return  # No scripts to stop

    with process_locks[user_id]:
        for file_name in list(running_processes[user_id].keys()):
            process = running_processes[user_id][file_name]
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            del running_processes[user_id][file_name]

            # Cancel timers
            if user_id in script_timers and file_name in script_timers[user_id]:
                timer = script_timers[user_id][file_name]
                timer.cancel()
                del script_timers[user_id][file_name]

        # Clean up if no more scripts are running
        if not running_processes[user_id]:
            del running_processes[user_id]
            del process_locks[user_id]
            if user_id in script_timers:
                del script_timers[user_id]



# Owner-only command to count bots (ensure OWNER_ID is set correctly)
OWNER_ID = '890382857'  # Replace with the actual owner ID

# Owner-only command to count bots
@bot.message_handler(commands=['countbots'])
def count_bots(message):
    if str(message.from_user.id) == OWNER_ID:
        base_directory = './user_files/'
        try:
            bot_count = sum(os.path.isdir(os.path.join(base_directory, i)) for i in os.listdir(base_directory))
            bot.send_message(message.from_user.id, f"Currently, there are {bot_count} bots hosted.")
        except Exception as e:
            bot.send_message(message.from_user.id, f"An error occurred: {str(e)}")
    else:
        bot.send_message(message.from_user.id, "You are not authorized to use this command.")

# Owner-only command to stop all scripts
@bot.message_handler(commands=['stopall'])
def stop_all_scripts_command(message):
    user_id = message.from_user.id
    if str(user_id) != OWNER_ID:
        bot.send_message(user_id, "You are not authorized to use this command.")
        return

    # Stop all scripts for all users
    for uid in list(running_processes.keys()):
        stop_all_scripts_for_user(uid)
    bot.send_message(user_id, "🛑 All running scripts have been stopped.")

# Owner-only command to list all users
@bot.message_handler(commands=['listusers'])
def list_all_users(message):
    user_id = message.from_user.id
    if str(user_id) != OWNER_ID:
        bot.send_message(user_id, "You are not authorized to use this command.")
        return

    user_dirs = os.listdir('./user_files/')
    user_ids = [uid for uid in user_dirs if uid.isdigit()]
    bot.send_message(user_id, f"📋 Current users: {', '.join(user_ids)}")

if __name__ == '__main__':
    # Start the membership checker thread
    threading.Thread(target=membership_checker, daemon=True).start()


    # Start polling
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        logging.error(f"Bot polling failed: {e}")
        time.sleep(5)  # Wait before restarting
