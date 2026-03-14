import json
import subprocess
import os
import time
import getpass
import sys

# --- CONFIG ---
RECOVERY_MAP = "recovery_map.json"
OUTPUT_DIR = os.path.expanduser("~/Desktop/audrey_recovered")
DRAT_PATH = "./drat"
CONTAINER = "/dev/rdisk5"
VOLUME = "1"

def recover_data():
    # Verify we are running as root (UID 0)
    if os.getuid() != 0:
        print("[!] ERROR: This script must be run with sudo.")
        print("Usage: sudo python3 drat_final_recovery.py")
        sys.exit(1)

    if not os.path.exists(RECOVERY_MAP):
        print(f"[!] ERROR: {RECOVERY_MAP} not found. Run harvest_metadata.py first.")
        return
    
    with open(RECOVERY_MAP, "r") as f:
        recovery_data = json.load(f)

    # We need the actual username to fix permissions later
    # When running with sudo, SUDO_USER gives the original user name
    current_user = os.environ.get("SUDO_USER", getpass.getuser())
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

        # 2. Progress Display
        display_path = (path[-37:] + '..') if len(path) > 40 else path.ljust(40)
        sys.stdout.write(f"\r[*] [{index}/{total_files}] ({percent:3.0f}%) Recovering: {display_path}")
        sys.stdout.flush()

        # 3. Execution
        cmd = [
            DRAT_PATH, "--container", CONTAINER, "--volume", VOLUME, 
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
    
    # --- FINAL PERMISSIONS FIX ---
    print("\n" + "="*45)
    print(f"[*] Recovery complete. Finalizing {current_user}'s permissions...")
    subprocess.run(["chown", "-R", current_user, OUTPUT_DIR], check=True)
    subprocess.run(["chmod", "-R", "755", OUTPUT_DIR], check=True)

    # --- SUMMARY ---
    total_gb = stats["total_bytes"] / (1024**3)
    print("\n" + " RECOVERY REPORT ".center(45, "="))
    print(f" Directories:      {stats['dirs_created']}")
    print(f" Files Succeeded:  {stats['files_success']}")
    print(f" Files Failed:     {stats['files_failed']}")
    print(f" Total Recovered:  {total_gb:.2f} GB")
    print("="*45)
    print(f"[+] Files are ready in: {OUTPUT_DIR}")

if __name__ == "__main__":
    # Primary check for sudo/root privileges
    if os.getuid() != 0:
        print("[!] This script requires root privileges. Please run with sudo:")
        print(f"    sudo python3 {sys.argv[0]}")
        sys.exit(1)
    
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    
    recover_data()