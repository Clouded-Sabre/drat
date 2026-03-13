import json
import subprocess
import os
import sys
import time
import threading

# CONFIG
MANIFEST_FILE = "fs_manifest.json"
XID_START = 0x2d2
XID_LIMIT = 0x2c0 
RECOVERY_MAP = "recovery_map.json"

def keep_sudo_alive():
    """Background thread to keep sudo credentials fresh."""
    def refresh():
        while True:
            # -v (validate) updates the timestamp without running a command
            subprocess.run(["sudo", "-v"], check=True)
            time.sleep(120) # Refresh every 2 minutes
    
    timer_thread = threading.Thread(target=refresh, daemon=True)
    timer_thread.start()

def load_manifest():
    with open(MANIFEST_FILE, "r") as f:
        return json.load(f)

def harvest_metadata(xid, pending_files):
    found_this_round = {}
    total_to_check = len(pending_files)
    
    print(f"\n[*] Sifting through XID {hex(xid)}...")
    
    for i, file_entry in enumerate(pending_files, 1):
        fsoid = file_entry['id']
        path = file_entry['path']
        
        # Internal Progress: [5/100] (5.0%) Checking: /path/to/file
        percent = (i / total_to_check) * 100
        # Show only the last 40 chars of the path to keep line clean
        display_path = (path[:37] + '..') if len(path) > 40 else path.ljust(40)
        
        sys.stdout.write(f"\r    [{i}/{total_to_check}] ({percent:3.1f}%) Searching: {display_path}")
        sys.stdout.flush()
        
        cmd = ["sudo", "./drat", "--container", "/dev/rdisk5", "--volume", "1", 
               "--max-xid", hex(xid), "list", "--fsoid", fsoid]
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, _ = process.communicate()
        
        if "INODE" in stdout and "No file size found" not in stdout:
            found_this_round[fsoid] = {
                "xid": hex(xid),
                "path": path,
                "status": "Ready"
            }
            
    sys.stdout.write("\n") # New line after finishing an XID layer
    return found_this_round

def main():
    # Pre-auth sudo so it doesn't prompt inside the loop
    subprocess.run(["sudo", "-v"], check=True)
    keep_sudo_alive()
    
    all_files = load_manifest()
    pending = [f for f in all_files if f['type'] == 'RegFile']
    total_initial = len(pending)
    completed_map = {}

    current_xid = XID_START
    
    print(f"[*] Starting Metadata Harvest for {total_initial} files.")
    
    while pending and current_xid >= XID_LIMIT:
        found = harvest_metadata(current_xid, pending)
        
        for fsoid, data in found.items():
            completed_map[fsoid] = data
            
        pending = [f for f in pending if f['id'] not in found]
        
        print(f"    [+] XID {hex(current_xid)} complete. Found {len(found)} new files. ({len(pending)} still missing)")
        
        current_xid -= 1

    with open(RECOVERY_MAP, "w") as f:
        json.dump(completed_map, f, indent=4)
    
    print("\n" + "="*50)
    print(f" HARVEST COMPLETE ".center(50, "="))
    print(f" Total files targeted:  {total_initial}")
    print(f" Successfully mapped:   {len(completed_map)}")
    print(f" Failed (Orphaned):     {len(pending)}")
    print("="*50)

if __name__ == "__main__":
    main()