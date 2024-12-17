import os
import sys
import subprocess
import logging




def run_script():


    # Dynamically get the path to the script (e.g., create_Midpoints_Table.py) relative to the current script
    current_dir = os.path.dirname(os.path.abspath(__file__))  # Get the directory of the current script
    script_name = 'create_Midpoints_Table.py'  # Name of the script you want to run
    script_path = os.path.join(current_dir, script_name)  # Combine the directory with relative path

    # Log the long path of the script
    logging.info(f"Using Python interpreter: {sys.executable}")
    logging.info(f"Script path: {script_path}")  # Log the full script path
    print(f"Using Python interpreter: {sys.executable}")  # Check Python executable being used
    print(f"Script path: {script_path}")  # Verify the script path

    # Check if the script file exists before running
    if not os.path.exists(script_path):
        error_message = f"Error: Script {script_name} not found at {script_path}"
        print(error_message)
        logging.error(error_message)
        return

    try:
        # Run the script via subprocess
        result = subprocess.run([sys.executable, script_path], capture_output=True, text=True, timeout=300)  # Timeout after 5 minutes

        # Check the result of the execution
        if result.returncode == 0:
            print("Script executed successfully:", result.stdout)
            logging.info(f"Script executed successfully from path: {script_path}\n{result.stdout}")
        else:
            print("Error executing script:")
            print("stderr:", result.stderr)
            print("stdout:", result.stdout)  # Also print stdout in case it provides useful info
            logging.error(f"Error executing script from path: {script_path}\nstderr: {result.stderr}\nstdout: {result.stdout}")

    except subprocess.TimeoutExpired:
        timeout_error_message = f"Error: Script execution timed out after 5 minutes."
        print(timeout_error_message)
        logging.error(timeout_error_message)
    except FileNotFoundError as fnf_error:
        print(f"Error: {fnf_error}")
        logging.error(f"FileNotFoundError for script {script_path}: {fnf_error}")
    except OSError as os_error:
        print(f"OS error: {os_error}")
        logging.error(f"OSError for script {script_path}: {os_error}")
    except Exception as e:
        print(f"Unexpected error: {e}")
        logging.exception(f"Unexpected error for script {script_path}: {e}")
