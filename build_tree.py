import subprocess
import re
import json
import os
import argparse
from datetime import datetime

# --- CONFIG ---
DRAT_PATH = "./drat"
CONTAINER = "/dev/rdisk5"
VOLUME = "1"
XID = "0x2d2"
LOG_FILE = "skipped_files.log"

# Global counter for skipped items in this run
skipped_count = 0

# Files and directories to ignore during the crawl
SKIP_LIST = {
    ".DS_Store", ".localized", ".Trashes", ".fseventsd", 
    ".Spotlight-V100", ".DocumentRevisions-V100", ".apdisk",
    "Network Trash Folder", "Temporary Items"
}

def log_skipped(path):
    """Appends skipped files to a persistent log with a timestamp."""
    global skipped_count
    skipped_count += 1
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] SKIPPED: {path}\n")

def run_list(path):
    cmd = ["sudo", DRAT_PATH, "--container", CONTAINER, "--volume", VOLUME, "--max-xid", XID, "list", "--path", path]
    print(f"[*] Listing: {path}")
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = process.communicate()
    return stdout

def parse_list(stdout, current_parent):
    items = []
    pattern = re.compile(r"DIR REC\s+\|\|\s+(\w+)\s+\|\|\s+target ID\s+=\s+(0x[0-9a-fA-F]+)\s+\|\|\s+name\s+=\s+(.+)")
    
    for line in stdout.splitlines():
        match = pattern.search(line)
        if match:
            obj_type, target_id, name = match.groups()
            name = name.strip()
            full_path = f"{current_parent.rstrip('/')}/{name}"
            
            if name in SKIP_LIST:
                log_skipped(full_path)
                continue
                
            items.append({'type': obj_type, 'id': target_id, 'name': name, 'full_path': full_path})
    return items

def build_manifest(start_path):
    manifest = []
    output = run_list(start_path)
    
    # Case 1: Single file
    if "INODE" in output and "DIR REC" not in output:
        print(f"[*] Path identified as a single file.")
        match = re.search(r"its FSOID is (0x[0-9a-fA-F]+)", output)
        if match:
            manifest.append({
                'path': start_path,
                'id': match.group(1),
                'type': 'RegFile'
            })
            return manifest

    # Case 2: Directory / Crawl
    queue = [start_path]
    while queue:
        current_path = queue.pop(0)
        current_output = output if current_path == start_path else run_list(current_path)
        children = parse_list(current_output, current_path)
        
        for child in children:
            entry = {
                'path': child['full_path'],
                'id': child['id'],
                'type': child['type']
            }
            manifest.append(entry)
            if child['type'] == 'Dirctry':
                queue.append(child['full_path'])
                
    return manifest

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build a directory tree manifest using drat.")
    parser.add_argument("path", help="The APFS path to start from (e.g., /WorkFiles)")
    args = parser.parse_args()

    subprocess.run(["sudo", "-v"], check=True)
    
    print(f"[*] Starting crawl at: {args.path}")
    full_tree = build_manifest(args.path)
    
    # Count breakdown
    file_count = sum(1 for item in full_tree if item['type'] == 'RegFile')
    dir_count = sum(1 for item in full_tree if item['type'] == 'Dirctry')
    
    with open("fs_manifest.json", "w") as f:
        json.dump(full_tree, f, indent=4)
        
    print("\n" + "="*40)
    print(" EXPLORATION SUMMARY ".center(40, "="))
    print(f" Total Directories: {dir_count}")
    print(f" Total Files:       {file_count}")
    print(f" Total Items:       {len(full_tree)}")
    print(f" Items Skipped:     {skipped_count}")
    print("="*40)
    print(f"[*] Manifest saved: fs_manifest.json")
    print(f"[*] Skip log updated: {LOG_FILE}")