
# Initialize bot and dispatcher
TOKEN='6799036771:AAHEjzGXpAeFitUTLfoh6_7O3uLoivIQnU4'
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

# Command handlers
@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    user_id = message.from_user.id
    user_states[user_id] = {}
    markup = InlineKeyboardMarkup()
    
    my_files_button = InlineKeyboardButton("My Python Files", callback_data='my_files')
    text_to_py_button = InlineKeyboardButton("Convert Text to .py", callback_data='text_to_py')
    
    markup.add(my_files_button)
    markup.add(text_to_py_button)
    
    await message.reply("Hi! I'm your Python Assistant bot. What would you like to do?", reply_markup=markup)
    


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
        file_name = "user_code.py"
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
                buttons_row = []
                buttons_row.append(InlineKeyboardButton(f'Run {file}', callback_data=f'run_{file}'))
                markup.row(*buttons_row)
            await bot.send_message(user_id, "Your files:", reply_markup=markup)
        else:
            await bot.send_message(user_id, "You have no files.")
    else:
        await bot.send_message(user_id, "You have no files.")

# Document handler for Python files
@dp.message_handler(content_types=['document'])
async def handle_document(message: types.Message):
    user_id = message.from_user.id
    if message.document.file_name.endswith('.py'):
        file_name = message.document.file_name
        user_dir = f'./user_files/{user_id}'
        if not os.path.exists(user_dir):
            os.makedirs(user_dir)
        try:
            document_id = message.document.file_id
            file = await bot.get_file(document_id)
            file_path = file.file_path
            file_content = await bot.download_file(file_path)
            with open(os.path.join(user_dir, file_name), 'wb') as f:
                f.write(file_content.getvalue())
            await message.answer(f"File {file_name} received and saved!")
        except Exception as e:
            logging.error(f"An error occurred: {e}")
            await message.reply(f"An error occurred: {e}")
    else:
        await message.reply("Please send a .py file.")


import asyncio
import subprocess

# Callback handler to run a Python file
@dp.callback_query_handler(lambda c: c.data and c.data.startswith('run_'))
async def run_file(callback_query: types.CallbackQuery):
    file_name = callback_query.data.split('_')[1]
    user_id = callback_query.from_user.id
    user_dir = f'./user_files/{user_id}'
    file_path = os.path.join(user_dir, file_name)

    # Run the Python file asynchronously
    await run_python_file_async(file_name, file_path, user_id)

    await bot.answer_callback_query(callback_query.id)

# Asynchronous function to run Python file
async def run_python_file_async(file_name, file_path, user_id):
    try:
        process = await asyncio.create_subprocess_exec(
            'python', file_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        # Decode stdout and stderr
        stdout_str = stdout.decode('utf-8')
        stderr_str = stderr.decode('utf-8')

        return_code = process.returncode

        if return_code == 0:
            success_message = f"Output:\n\n{stdout_str}"
            await bot.send_message(user_id, success_message)
        else:
            await bot.send_message(user_id, f"Error running {file_name}: {stderr_str}")
    except Exception as e:
        logging.error(f"Failed to run {file_name}: {e}")
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
    prompt = (
        "Hi! I'm your Python bot, here to assist with Python code execution and file management. \n"
        "You can use me to convert text snippets into .py files, run Python scripts, and manage your files.\n\n"
        "Here are some things you can do:\n"
        "- Click on 'My Python Files' to view or run your saved scripts.\n"
        "- Click on 'Convert Text to .py' to send me a text snippet to convert into a Python file.\n"
        "- Send me a .py file directly, and I'll save it for you.\n"
        "- Type 'Install [library name]' to install Python libraries for your scripts.\n\n"
        "How can I assist you today?"
    )
    combined_message = "{}\n{}".format(context, prompt)

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

    # Update the chat history
    if chat_id in chat_histories:
        chat_histories[chat_id].append("User: " + user_message)
    else:
        chat_histories[chat_id] = ["User: " + user_message]

    # Get a response from the ChatGPT-like model
    response = await get_chatgpt_response(chat_id, user_message)
    chat_histories[chat_id].append("Bot: " + response)

    # Send the response back to the user
    await message.reply(response)



##############################################################################
# Start polling
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)


