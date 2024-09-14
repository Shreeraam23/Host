
TOKEN = '6799036771:AAGgfJ_mEU1W041O8r_ctnMfaKfdCj7XDKQ'

import telebot
from telebot import types
import logging
import os
import subprocess
import threading


bot = telebot.TeleBot(TOKEN)

# Configure logging
logging.basicConfig(level=logging.INFO)

running_processes = {}  # Key: user_id, Value: dict of {file_name: subprocess.Popen}
process_locks = {}      # Key: user_id, Value: threading.Lock object

# Dictionaries to keep track of user states and running processes
user_states = {}
running_processes = {}  # Key: user_id, Value: subprocess.Popen object
process_locks = {}      # Key: user_id, Value: threading.Lock object

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
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status not in ['left', 'kicked']
    except Exception as e:
        logging.error(f"Error checking user membership: {str(e)}")
        return False

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id

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
            # User is not a member of the group, prompt them to join
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(text="💳 Take Subscription", url="https://your_subscription_link.com"))
            bot.send_message(user_id, "🌟 Please subscribe to use this bot.", reply_markup=markup)
    else:
        # Group subscription check is disabled, proceed without it
        initialize_bot_functionalities(message)

def initialize_bot_functionalities(message):
    user_id = message.from_user.id
    user_states[user_id] = {}
    markup = types.InlineKeyboardMarkup()

    my_files_button = types.InlineKeyboardButton("📂 My Python Files", callback_data='my_files')
    markup.add(my_files_button)

    bot.send_message(
        user_id,
        "👋 Welcome to the Python Bot! You can do the following:\n"
        "- 🏃‍♂️ Run your Python files\n"
        "- 📦 Install libraries via requirements.txt\n"
        "Choose an option to proceed.",
        reply_markup=markup
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

@bot.callback_query_handler(func=lambda call: call.data.startswith('run_'))
def run_file(call):
    file_name = call.data[len('run_'):]
    file_name = os.path.basename(file_name)  # Sanitize filename
    user_id = call.from_user.id
    user_dir = f'./user_files/{user_id}'
    file_path = os.path.join(user_dir, file_name)
    user_lib_dir = os.path.join(user_dir, 'libs')

    if not os.path.isfile(file_path):
        bot.send_message(user_id, f"File does not exist: {file_name}")
        return

    # Prepare the environment variables
    env = os.environ.copy()
    env['PYTHONPATH'] = user_lib_dir + os.pathsep + env.get('PYTHONPATH', '')

    try:
        # Initialize the user's process dictionary and lock if not already done
        if user_id not in running_processes:
            running_processes[user_id] = {}
            process_locks[user_id] = threading.Lock()

        # Start the subprocess
        process = subprocess.Popen(
            ['python', file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
            bufsize=1
        )

        with process_locks[user_id]:
            running_processes[user_id][file_name] = process

        bot.send_message(user_id, f"🚀 Running '{file_name}'. Use /stop to stop scripts.")

        threading.Thread(target=stream_process_output, args=(user_id, file_name, process)).start()

    except Exception as e:
        bot.send_message(user_id, f"⚠️ Failed to run {file_name}: {e}")


def stream_process_output(user_id, file_name, process):
    try:
        for line in process.stdout:
            if line.strip():
                bot.send_message(user_id, f"[{file_name}] {line.strip()}")
    except Exception as e:
        logging.error(f"Error streaming output for user {user_id}, script {file_name}: {e}")
    finally:
        with process_locks[user_id]:
            if file_name in running_processes.get(user_id, {}):
                del running_processes[user_id][file_name]
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
        process = running_processes[user_id].get(file_name)
        if process:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            del running_processes[user_id][file_name]
            if not running_processes[user_id]:
                del running_processes[user_id]
                del process_locks[user_id]

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

@bot.callback_query_handler(func=lambda call: call.data == 'stop_all')
def stop_all_scripts_callback(call):
    user_id = call.from_user.id

    if user_id not in running_processes or not running_processes[user_id]:
        bot.answer_callback_query(call.id, "You don't have any running scripts.")
        return

    with process_locks[user_id]:
        for file_name in list(running_processes[user_id].keys()):
            stop_script(user_id, file_name)

    bot.answer_callback_query(call.id, "All your scripts have been stopped.")
    bot.send_message(user_id, "🛑 All your scripts have been stopped.")


# Owner-only command to count bots (ensure OWNER_ID is set correctly)
OWNER_ID = 'YOUR_TELEGRAM_USER_ID'  # Replace with the actual owner ID

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

# Start polling
if __name__ == '__main__':
    import time
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        logging.error(f"Bot polling failed: {e}")
        time.sleep(5)  # Wait before restarting
