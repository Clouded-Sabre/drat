import json
import subprocess
import os
import time
import getpass
import threading

# --- CONFIG ---
RECOVERY_MAP = "recovery_map.json"
OUTPUT_DIR = os.path.expanduser("~/Desktop/audrey_recovered")
DRAT_PATH = "./drat"
CONTAINER = "/dev/rdisk5"
VOLUME = "1"

def keep_sudo_alive():
    """Background thread to keep sudo credentials fresh."""
    def refresh():
        while True:
            # -v (validate) updates the timestamp without running a command
            subprocess.run(["sudo", "-v"], check=True)
            time.sleep(120) # Refresh every 2 minutes
    
    timer_thread = threading.Thread(target=refresh, daemon=True)
    timer_thread.start()

def recover_data():
    with open(RECOVERY_MAP, "r") as f:
        recovery_data = json.load(f)

    current_user = getpass.getuser()
    total_files = len(recovery_data)
    
    stats = {
        "files_success": 0,
        "files_failed": 0,
        "dirs_created": 0,
        "total_bytes": 0
    }

    # Use enumerate to track the current file index (starting at 1)
    for index, (fsoid, info) in enumerate(recovery_data.items(), 1):
        path = info['path']
        xid = info['xid']
        filename = os.path.basename(path)
        
        # Calculate percentage for the progress display
        percent = (index / total_files) * 100
        
        # 1. Setup paths
        local_file_path = os.path.join(OUTPUT_DIR, path.lstrip('/'))
        parent_dir = os.path.dirname(local_file_path)
        
        if not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
            stats["dirs_created"] += 1

        drat_temp_file = os.path.join(parent_dir, f"_com.dratapp.recover_{filename}")

        for f_to_rem in [drat_temp_file, local_file_path]:
            if os.path.exists(f_to_rem):
                os.remove(f_to_rem)

        # 2. Updated Print Statement with Overall Progress
        # Using :>3 for alignment so the text doesn't jitter
        print(f"[*] [{index}/{total_files}] ({percent:3.0f}%) Recovering: {path[-50:]:50}...", end="\r")

        # 3. Execution
        cmd = [
            "sudo", DRAT_PATH, "--container", CONTAINER, "--volume", VOLUME, 
            "--max-xid", xid, "recover", "--fsoid", fsoid, "--output", local_file_path
        ]
        
        process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        process.communicate(input="y\n" * 10)

        # 4. Post-Process
        time.sleep(0.05) 
        if os.path.exists(drat_temp_file) and not os.path.exists(local_file_path):
            os.rename(drat_temp_file, local_file_path)

        # 5. Update Stats
        if os.path.exists(local_file_path):
            f_size = os.path.getsize(local_file_path)
            stats["files_success"] += 1
            stats["total_bytes"] += f_size
        else:
            # Clear the current line before printing a failure so it doesn't look messy
            print(" " * 100, end="\r")
            print(f"[!] FAILED: {path}")
            stats["files_failed"] += 1

if __name__ == "__main__":
    subprocess.run(["sudo", "-v"], check=True)
    keep_sudo_alive()
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    recover_data()