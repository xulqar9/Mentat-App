import logging
import os
from datetime import datetime

# Configure logging
# log_directory = os.path.expanduser("~/.mentat/logs")
# os.makedirs(log_directory, exist_ok=True)
# log_file = os.path.join(log_directory, f"errors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    #filename=log_file,
    level=logging.ERROR,
    #format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def log_error(error_message):
    logging.error(error_message)
    #print(f"Error logged: {error_message}")