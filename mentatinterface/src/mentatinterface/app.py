import time
import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
import os, json
from pathlib import Path
from dotenv import load_dotenv
from mentat.python_client.client import PythonClient
from mentat.config import Config
import warnings, asyncio
from errors import log_error  # Import the log_error function

# Filter out deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

class MentatInterface(toga.App):
    def startup(self):
        self.env_file = os.path.expanduser("~/.mentat/.env")
        self.load_env()
        self.selected_provider = None
        self.selected_model = None
        main_box = toga.Box(style=Pack(direction=COLUMN))

        # Load the last saved settings
        configs_path = Path.home() / ".mentat/configs.json"
        if configs_path.exists():
            with open(configs_path, "r") as f:
                configs = json.load(f)
                self.selected_provider = configs.get("provider")
                self.selected_model = configs.get("model")
                self.api_key = configs.get(f'{self.selected_provider.upper()}_API_KEY',)

        # File Selector UI
        self.label = toga.Label('Select a file or directory:', style=Pack(padding=(0, 5)))
        self.browse_files_button = toga.Button('Select files...', on_press=self.select_files, style=Pack(padding=5))
        self.browse_folder_button = toga.Button('Select a folder...', on_press=self.select_folder, style=Pack(padding=5))
        self.run_button = toga.Button('Run Mentat', on_press=self.run_mentat, style=Pack(padding=5))

        file_selector_box = toga.Box(style=Pack(direction=COLUMN))
        file_selector_box.add(self.label)
        file_selector_box.add(self.browse_files_button)
        file_selector_box.add(self.browse_folder_button)
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

        self.load_configurations()

        # Add command to open the configuration window
        settings_command = toga.Command(
            text='Settings',
            action=self.open_settings,
            group=toga.Group.FILE,
            order=3
        )

        self.commands.add(settings_command)

    def load_env(self):
        if os.path.exists(self.env_file):
            load_dotenv(self.env_file)

    def load_configurations(self):
        env_file = os.path.expanduser("~/.mentat/.env")
        if os.path.exists(env_file):
            load_dotenv(env_file)
            self.api_key = os.getenv(f'{self.selected_provider.upper()}_API_KEY', )


    def open_settings(self, widget):
        settings_box = toga.Box(style=Pack(direction=COLUMN, padding=10))

        module_options = {
            "openai": ["gpt-3.5-turbo", "gpt-4-0125-preview", "gpt-4-turbo-preview"],
            "anthropic": ["claude-v1", "claude-3-5-sonnet-20240620"],
            "azure": ["gpt-35-turbo"]
        }

        self.provider_select = toga.Selection(items=list(module_options.keys()), on_select=self.select_provider, style=Pack(flex=1))
        self.model_select = toga.Selection(items=[], enabled=False, style=Pack(flex=1))  # Initialize model_select

        if self.selected_provider:
            self.provider_select.value = self.selected_provider
            self.model_select.items = module_options[self.selected_provider]  # Set items here
            self.model_select.enabled = True
            if self.selected_model:
                self.model_select.value = self.selected_model

        api_key_value = os.getenv(f"{self.selected_provider}_API_KEY", ) if self.selected_provider else ""
        self.api_key_input = toga.TextInput(placeholder="API Key", value=api_key_value, style=Pack(flex=1))

        save_button = toga.Button("Save", on_press=lambda x: self.save_settings(self.api_key_input.value, self.selected_provider, self.model_select.value), style=Pack(padding=5))

        settings_box.add(toga.Label("Provider:", style=Pack(padding=(0, 5))))
        settings_box.add(self.provider_select)
        settings_box.add(toga.Label("Model:", style=Pack(padding=(0, 5))))
        settings_box.add(self.model_select)
        settings_box.add(toga.Label("API Key:", style=Pack(padding=(0, 5))))
        settings_box.add(self.api_key_input)
        settings_box.add(save_button)

        settings_window = toga.Window(title="Settings")
        settings_window.content = settings_box
        settings_window.show()

    def select_provider(self, widget):
        self.selected_provider = widget.value
        module_options = {
            "openai": ["gpt-3.5-turbo", "gpt-4-0125-preview", "gpt-4-turbo-preview"],
            "anthropic": ["claude-v1", "claude-3-5-sonnet-20240620"],
            "azure": ["gpt-35-turbo"]
        }
        if self.selected_provider in module_options:
            self.model_select.items = module_options[self.selected_provider]
            self.model_select.enabled = True
        else:
            self.model_select.items = []
            self.model_select.enabled = False

    def save_settings(self, api_key, provider, model):
        if not provider:
            self.main_window.error_dialog("Error", "No provider selected.")
            return

        os.makedirs(os.path.dirname(self.env_file), exist_ok=True)
        env_content = f"{provider.upper()}_API_KEY={api_key}\n"
        with open(self.env_file, 'w') as env_file:
            env_file.write(env_content)

        self.load_env()


        # Save provider and model in configs.json
        configs_path = Path.home() / ".mentat/configs.json"
        configs = {}
        if configs_path.exists():
            with open(configs_path, "r") as f:
                configs = json.load(f)

        configs["api_key"] = api_key
        configs["provider"] = provider
        configs["model"] = model
        with open(configs_path, "w") as f:
            json.dump(configs, f, indent=4)

        # Save only model in .mentat/.mentat_config.json
        mentat_config_path = Path.home() / ".mentat/.mentat_config.json"
        mentat_config = {}
        if mentat_config_path.exists():
            with open(mentat_config_path, "r") as f:
                mentat_config = json.load(f)

        mentat_config["model"] = model
        with open(mentat_config_path, "w") as f:
            json.dump(mentat_config, f, indent=4)

        self.main_window.info_dialog("Info", "Settings Saved")

    async def select_files(self, widget):
        try:
            selected_files = await self.main_window.open_file_dialog('Select files', multiselect=True)
            if selected_files:
                # Convert WindowsPath objects to strings
                selected_files = [str(file) for file in selected_files]
                self.label.text = f'Selected files: {", ".join(selected_files)}'
                self.target = selected_files
        except Exception as e:
            self.label.text = f'Error: {e}'

    async def select_folder(self, widget):
        try:
            selected_folder = await self.main_window.select_folder_dialog('Select a folder')
            if selected_folder:
                # Convert WindowsPath object to string
                selected_folder = str(selected_folder)
                self.label.text = f'Selected folder: {selected_folder}'
                self.target = selected_folder
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

            if isinstance(self.target, list):
                paths = self.target
                cwd = Path(self.target[0]).parent
            else:
                paths = [self.target]
                cwd = Path(self.target).parent

            # Pass the --provider and --model arguments to the PythonClient instance
            config =Config(
                    provider=self.selected_provider,
                    model=self.selected_model,
                    #maximum_context=4000
            )

            self.python_client = PythonClient(
                cwd=cwd,
                paths=paths,
                config=config,

            )
            print(config)
            await self.python_client.startup()
            self.python_client.get_conversation()
            time.sleep(1)
            self.chat_log.value += "Mentat initialized. You can start chatting now.\n\n"
            self.send_button.enabled = True  # Enable the send button after Mentat is initialized
        except Exception as e:
            error_message = f"Failed to initialize Mentat: {str(e)}"
            self.chat_log.value += error_message + "\n"
            log_error(error_message)

    async def send_message(self, widget):
        message = self.input_field.value
        if not message.strip():
            return

        self.chat_log.value += f'User: {message}\n'
        self.chat_log.value += "Mentat is thinking...\n"
        self.input_field.value = ''
        self.send_button.enabled = False

        await self.get_response_from_mentat(message)
        await self.response(message)

    async def get_response_from_mentat(self, message):
        if not self.python_client:
            return "Please select a file or directory and run Mentat first."

        try:
            return await asyncio.wait_for(self.python_client.call_mentat(message), timeout=30)
        except Exception as e:
            error_message = f"Error: {str(e)}"
            log_error(error_message)
            return error_message

    async def response(self, message):
        response = await self.get_response_from_mentat(message)
        self.chat_log.value = self.chat_log.value.replace("Mentat is thinking...\n", "")
        self.chat_log.value += f'Mentat: {response}\n'
        self.send_button.enabled = True


def main():
    return MentatInterface('Mentat Toga App', 'org.example.mentat_toga')

if __name__ == '__main__':
    main().main_loop()
