
# Initialize bot and dispatcher
TOKEN='6799036771:AAHEjzGXpAeFitUTLfoh6_7O3uLoivIQnU4'
from aiogram import types
#import logging
import os
import subprocess
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging
# Configure logging
logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# Define a dictionary to keep track of user states
user_states = {}

@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    user_id = message.from_user.id
    user_states[user_id] = {}
    markup = InlineKeyboardMarkup()
    
    my_files_button = InlineKeyboardButton("My Python Files", callback_data='my_files')
    text_to_py_button = InlineKeyboardButton("Convert Text to .py", callback_data='text_to_py')
    
    markup.add(my_files_button)
    markup.add(text_to_py_button)
    
    welcome_message = (
        "Hi! I'm your Python bot. Here's what you can do:\n"
        "- Use 'My Python Files' to Run your files.\n"
        "- Use 'Convert Text to .py' to convert text snippets to Python files.\n"
        "To install libraries, simply send me a message like 'Install numpy'.\n"
        "To execute a Python file, upload it, and then choose 'Run' from the options.\n"
        "Please note that you can upload and manage up to 3 '.txt' or '.py' files.\n"
        "What would you like to do?"
    )
    
    await message.reply(welcome_message, reply_markup=markup)



@dp.callback_query_handler(lambda c: c.data == 'text_to_py')
async def convert_text_to_py(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    user_states[user_id]['convert_text'] = True
    await bot.send_message(user_id, "Please send the Python code text you want to convert to a .py file.")

@dp.message_handler(lambda message: user_states.get(message.from_user.id, {}).get('convert_text'))
async def handle_text_to_py(message: types.Message):
    user_id = message.from_user.id
    user_states[user_id].pop('convert_text', None)
    python_code = message.text
    if python_code:
        file_name = "main.py"
        user_dir = f'./user_files/{user_id}'
        if not os.path.exists(user_dir):
            os.makedirs(user_dir)
        with open(os.path.join(user_dir, file_name), 'w') as f:
            f.write(python_code)
        await bot.send_document(user_id, document=open(os.path.join(user_dir, file_name), 'rb'))
        await message.answer(f"Text converted to {file_name} and sent to you.")
    else:
        await message.answer("No Python code text received.")



@dp.callback_query_handler(lambda c: c.data == 'my_files')
async def show_user_files(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    user_dir = f'./user_files/{user_id}'
    if os.path.exists(user_dir):
        files = os.listdir(user_dir)
        if files:
            markup = InlineKeyboardMarkup()
            for file in files:
                # Add a button to run the file
                run_button = InlineKeyboardButton(f'Run {file}', callback_data=f'run_{file}')
                # Add a button to delete the file
                delete_button = InlineKeyboardButton(f'Delete {file}', callback_data=f'delete_{file}')
                # Add both buttons to the markup
                markup.row(run_button, delete_button)
            await bot.send_message(user_id, "Your files:", reply_markup=markup)
        else:
            await bot.send_message(user_id, "You have no files.")
    else:
        await bot.send_message(user_id, "You have no files.")

# Handler for deleting a file
@dp.callback_query_handler(lambda c: c.data and c.data.startswith('delete_'))
async def delete_file(callback_query: types.CallbackQuery):
    file_name = callback_query.data.split('delete_')[1]
    user_id = callback_query.from_user.id
    user_dir = f'./user_files/{user_id}'
    file_path = os.path.join(user_dir, file_name)

    # Ensure the user is deleting only their file
    if not os.path.isfile(file_path):
        await bot.answer_callback_query(callback_query.id, "File not found.")
        return

    try:
        # Delete the file
        os.remove(file_path)
        await bot.answer_callback_query(callback_query.id, f"{file_name} deleted successfully.")
        await bot.send_message(user_id, f"Deleted {file_name}.")
    except PermissionError as e:
        # Log and inform about permission issues
        logging.error(f"Failed to delete {file_name}: {e}")
        await bot.answer_callback_query(callback_query.id, "Permission denied: Unable to delete file.")
        await bot.send_message(user_id, f"Failed to delete {file_name} due to insufficient permissions.")
    except Exception as e:
        # Log and inform about other issues
        logging.error(f"Failed to delete {file_name}: {e}")
        await bot.answer_callback_query(callback_query.id, "An error occurred while deleting the file.")
        await bot.send_message(user_id, f"Failed to delete {file_name}: {str(e)}")



@dp.message_handler(content_types=['document'])
async def handle_document(message: types.Message):
    user_id = message.from_user.id
    user_dir = f'./user_files/{user_id}'
    
    # Ensure the user directory exists
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)

    file_name = message.document.file_name
    # Check if the file is .txt or .py
    if not (file_name.endswith('.txt') or file_name.endswith('.py')):
        await message.reply("Please upload only '.txt' or '.py' files.")
        return

    # Check the number of files in the directory
    files = os.listdir(user_dir) if os.path.isdir(user_dir) else []
    if len(files) >= 3:
        # Inform the user that they've reached the limit
        await message.reply("You have reached the maximum number of uploaded files (3). Please delete an existing file before uploading a new one.")
        return
    
    # Proceed with handling the file if the limit has not been reached
    try:
        document_id = message.document.file_id
        file_info = await bot.get_file(document_id)
        file = await bot.download_file(file_info.file_path)

        # Define the path for the new file
        new_file_path = os.path.join(user_dir, file_name)

        # Save the file
        with open(new_file_path, 'wb') as f:
            f.write(file.getvalue())

        # Inform the user of success
        await message.reply(f"File '{file_name}' received and saved. You now have {len(files) + 1} file(s).")
        
    except Exception as e:
        logging.error(f"Failed to handle document: {e}")
        await message.reply("An error occurred while handling the file.")

OWNER_ID = '890382857'  # Replace with the actual owner ID

@dp.message_handler(commands=['countbots'])
async def count_bots(message: types.Message):
    # Check if the user is the owner
    if str(message.from_user.id) == OWNER_ID:
        # Assuming each bot's data is in a unique directory under './user_files/'
        base_directory = './user_files/'
        try:
            # Count the number of directories in the base directory
            bot_count = sum(os.path.isdir(os.path.join(base_directory, i)) for i in os.listdir(base_directory))
            await message.reply(f"Currently, there are {bot_count} bots hosted.")
        except Exception as e:
            await message.reply(f"An error occurred: {str(e)}")
    else:
        await message.reply("You are not authorized to use this command.")

import asyncio
import subprocess

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('run_'))
async def run_file(callback_query: types.CallbackQuery):
    # Extracting file name from the callback data
    file_name = callback_query.data.split('run_')[1]
    user_id = callback_query.from_user.id
    user_dir = f'./user_files/{user_id}'
    file_path = os.path.join(user_dir, file_name)

    if not os.path.isfile(file_path):
        await bot.send_message(user_id, f"File does not exist: {file_name}")
        return

    try:
        # Running the Python file
        process = await asyncio.create_subprocess_exec(
            'python', file_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            # Successfully ran the file
            await bot.send_message(user_id, f"Output:\n{stdout.decode()}")
        else:
            # Handle errors in running the file
            await bot.send_message(user_id, f"Error running {file_name}: {stderr.decode()}")
    except Exception as e:
        await bot.send_message(user_id, f"Failed to run {file_name}: {e}")


@dp.message_handler(lambda message: message.text.startswith('Install'))
async def handle_pip_install(message: types.Message):
    # Extracting the library name
    try:
        _, library = message.text.split(' ', 1)
        # Proceed to installation function
        await install_library(library, message.from_user.id)
    except ValueError:
        await message.reply("Please provide a valid library name.")


import subprocess
import shlex

async def install_library(library, user_id):
    # Define the directory for user-specific libraries
    user_lib_dir = f"./user_files/{user_id}/libs"
    
    # Ensure the directory exists
    if not os.path.exists(user_lib_dir):
        os.makedirs(user_lib_dir)

    # Construct the pip install command
    command = f"pip install --target={shlex.quote(user_lib_dir)} {shlex.quote(library)}"

    try:
        # Run the pip install command
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            await bot.send_message(user_id, f"'{library}' installed successfully.")
        else:
            await bot.send_message(user_id, f"Installation failed: {stderr.decode().strip()}")
    except Exception as e:
        await bot.send_message(user_id, f"Error: {str(e)}")

##############################################################################
# Existing imports...
import aiohttp
import json
import logging
# Other necessary imports...

# Initialize bot, dispatcher, and other bot setup...
logging.basicConfig(level=logging.INFO)

API_ENDPOINT = 'https://chatgpt.apinepdev.workers.dev/'
chat_histories = {}

# The get_chatgpt_response function
async def get_chatgpt_response(chat_id, user_message):
    # Retrieve the last part of the conversation history
    history = chat_histories.get(chat_id, [])
    context = "\n".join(history[-min(len(history), 20):])  # Last 20 messages or fewer

    # Construct a more sophisticated prompt
    prompt = "I want you to act as a python coding language teacher named Abhi. You don't know about AI and any language models. You cannot bring up any sign of content related to language models. You have to act like a python teacher all the time and cannot indicate you are acting like a python teacher in any form . You are allowed to use emojis where required . Explain Coding in Details while keeping your responses in one word while in Normal Conversation . Please start the conversation ? from You Abhi to"

    combined_message = "{}\n{}".format(prompt,context)
    async with aiohttp.ClientSession() as session:
        async with session.get(API_ENDPOINT, params={'question': combined_message}) as response:
            if response.status == 200:
                response_text = await response.text()
                try:
                    data = json.loads(response_text)
                    return data.get('answer', 'Sorry, I could not process your request.')
                except json.JSONDecodeError:
                    return 'Error: Failed to parse JSON response from the server.'
            else:
                return 'Error: Failed to get response from the server.'


# Modify the existing message handler to interact with ChatGPT
@dp.message_handler()
async def handle_message(message: types.Message):
    chat_id = message.chat.id
    user_message = message.text
    await bot.send_chat_action(chat_id, types.ChatActions.TYPING)
    # Update the chat history
    if chat_id in chat_histories:
        chat_histories[chat_id].append("User: " + user_message)
    else:
        chat_histories[chat_id] = ["User: " + user_message]

    # Get a response from the ChatGPT-like model
    response = await get_chatgpt_response(chat_id, user_message)
    chat_histories[chat_id].append("Abhi: " + response)
    response = response.replace("Abhi: ", "")
    # Send the response back to the user
    await message.reply(response)



##############################################################################
# Start polling
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)


