import subprocess
import sys
import os
import logging


def run_script():
    # Dynamically get the path to the script (e.g., create_Midpoints_Table.py) relative to the current script
    current_dir = os.path.dirname(os.path.abspath(__file__))  # Get the directory of the current script
    script_name = 'create_Midpoints_Table.py'  # Name of the script you want to run
    script_path = os.path.join(current_dir, 'DBM', script_name)  # Combine the directory with relative path

    print("Using Python interpreter:", sys.executable)  # Check Python executable being used
    print("Script path:", script_path)  # Verify the script path

    # Set up logging to a file
    logging.basicConfig(filename='script_execution_log.txt', level=logging.DEBUG,
                        format='%(asctime)s - %(levelname)s - %(message)s')

    try:
        result = subprocess.run([sys.executable, script_path], capture_output=True, text=True,
                                timeout=300)  # Timeout after 5 minutes

        if result.returncode == 0:
            print("Script executed successfully:", result.stdout)
            logging.info("Script executed successfully:\n" + result.stdout)
        else:
            print("Error executing script:")
            print("stderr:", result.stderr)
            print("stdout:", result.stdout)  # Also print stdout in case it provides useful info
            logging.error(f"Error executing script:\nstderr: {result.stderr}\nstdout: {result.stdout}")

    except subprocess.TimeoutExpired:
        print("Error: Script execution timed out.")
        logging.error("Script execution timed out.")
    except Exception as e:
        print(f"Unexpected error: {e}")
        logging.error(f"Unexpected error: {e}")




