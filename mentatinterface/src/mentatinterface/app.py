import time
import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
import os
from pathlib import Path
from dotenv import load_dotenv
from mentat.python_client.client import PythonClient
import warnings

# Filter out deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

class MentatInterface(toga.App):
    def startup(self):
        main_box = toga.Box(style=Pack(direction=COLUMN))

        # File Selector UI
        self.label = toga.Label('Select a file or directory:', style=Pack(padding=(0, 5)))
        self.browse_button = toga.Button('Browse...', on_press=self.select_file, style=Pack(padding=5))
        self.run_button = toga.Button('Run Mentat', on_press=self.run_mentat, style=Pack(padding=5))

        file_selector_box = toga.Box(style=Pack(direction=COLUMN))
        file_selector_box.add(self.label)
        file_selector_box.add(self.browse_button)
        file_selector_box.add(self.run_button)

        # Chat Interface UI
        self.chat_log = toga.MultilineTextInput(readonly=True, style=Pack(flex=1, padding=5))
        self.input_field = toga.TextInput(style=Pack(flex=1))
        self.send_button = toga.Button('Send', on_press=self.send_message, style=Pack(padding_left=5))
        self.send_button.enabled = False  # Initially disable the send button

        input_box = toga.Box(style=Pack(direction=ROW, padding=5))
        input_box.add(self.input_field)
        input_box.add(self.send_button)

        chat_interface_box = toga.Box(style=Pack(direction=COLUMN, flex=1))
        chat_interface_box.add(self.chat_log)
        chat_interface_box.add(input_box)

        main_box.add(file_selector_box)
        main_box.add(chat_interface_box)

        self.main_window = toga.MainWindow(title=self.formal_name)
        self.main_window.content = main_box
        self.main_window.show()

        self.target = None
        self.python_client = None
        self.times = 0

    async def select_file(self, widget):
        try:
            selected = await self.main_window.open_file_dialog('Select a file or directory')
            if selected:
                self.label.text = f'Selected: {selected}'
                self.target = selected
        except Exception as e:
            self.label.text = f'Error: {e}'

    async def run_mentat(self, widget):
        if not self.target:
            self.chat_log.value += "No target file or directory selected.\n"
            return

        try:
            env_file = os.path.expanduser("~/.mentat/.env")
            if os.path.exists(env_file):
                load_dotenv(env_file)

            self.python_client = PythonClient(
                cwd=Path(self.target).parent,
                paths=[self.target],
            )

            await self.python_client.startup()
            time.sleep(1)
            self.chat_log.value += "Mentat initialized. You can start chatting now.\n\n"
            self.send_button.enabled = True  # Enable the send button after Mentat is initialized
        except Exception as e:
            self.chat_log.value += f"Failed to initialize Mentat: {str(e)}\n"

    async def send_message(self, widget):
        message = self.input_field.value
        if not message.strip():
            return

        self.chat_log.value += f'User: {message}\n'
        self.input_field.value = ''
        self.send_button.enabled = False

        await self.response(message)

    async def response(self, message):
        await self.get_response_from_mentat(message)
        response = await self.get_response_from_mentat(message)
        self.chat_log.value += f'Mentat: {response}\n'
        self.send_button.enabled = True

    async def get_response_from_mentat(self, message):
        if not self.python_client:
            return "Please select a file or directory and run Mentat first."

        try:
            return await self.python_client.call_mentat(message)
             
        except Exception as e:
            return f"Error: {str(e)}"

def main():
    return MentatInterface('Mentat Toga App', 'org.example.mentat_toga')

if __name__ == '__main__':
    main().main_loop()
