# **APFS Transactional Recovery Guide**

This guide describes a professional-grade recovery workflow for Apple File System (APFS) volumes using the drat (Diagnostic and Recovery Tool) and a suite of Python automation scripts.

## **The Core Concept: APFS Transactional Recovery**

Unlike older file systems (like HFS+), APFS is a **Copy-on-Write (CoW)** system. It never overwrites data in place. Every change creates a new **Transaction ID (XID)**.  
When a volume becomes unmountable or data is "deleted," the metadata pointers are often still present in older XID snapshots. Our workflow "sifts" through these snapshots to find the last known good state of your files.

## **Identifying Key Parameters**

Before running the scripts, you must identify three critical parameters specific to your hardware and data loss event.

### **1\. The Container Device (CONTAINER)**

This is the raw disk identifier for the APFS Container.

* **How to find it:** Run diskutil list in Terminal.  
* **Look for:** The entry labeled TYPE NAME as APFS Container Scheme.  
* **Example:** /dev/rdisk5. (Using the r prefix, e.g., rdisk instead of disk, often improves performance by bypassing the kernel buffer).

### **2\. The Volume ID (VOLUME)**

An APFS Container can hold multiple volumes (e.g., Macintosh HD, Data, Recovery).

* **How to find it:** Run sudo ./drat \--container /dev/rdiskX info.  
* **Look for:** The volume list at the start of the output. Volumes are indexed starting at 1\.  
* **Note:** Usually, the main user data volume is index 1\.

### **3\. The Transaction ID (XID\_START)**

This is the "point in time" you want to recover from.

* **How to find it:** Run sudo ./drat \--container /dev/rdiskX info.  
* **Look for:** The XID value in the Container Superblock (the most recent state) or browse the Checkpoint Descriptor Area for older XIDs.  
* **Example:** 0x2d2.

## **The Recovery Pipeline**

The process is divided into three distinct phases:

### **Phase 1: Exploration (drat\_explorer.py)**

**Goal:** Crawl the APFS B-Tree to find all file and directory entries.

* **Key Feature:** Allows targeting specific subdirectories to manage recovery in stages.  
* **Filtering:** Automatically skips macOS system "junk" (like .DS\_Store) to keep the recovery clean.  
* **Output:** fs\_manifest.json.

### **Phase 2: Metadata Harvesting (harvest\_metadata.py)**

**Goal:** Find the "Golden State" for every file in the manifest.

* **Mechanism:** It queries the disk layer-by-layer, starting from the XID\_START and moving backward to the XID\_LIMIT.  
* **Validation:** It ensures that the metadata (Inodes) and file sizes are intact.  
* **Output:** recovery\_map.json.

### **Phase 3: Data Extraction (drat\_final\_recovery.py)**

**Goal:** Reconstruct bytes from physical disk extents to your local drive.

* **Automation:** Handles directory creation, progress tracking, and fixes permissions.  
* **Output:** Recovered files in a designated folder on your Desktop.

## **Script Usage Instructions**

### **Step-by-Step Execution**

0. **Use the discovered parameter to change corresponding variables in build\_tree.py**
   CONTAINER = "/dev/rdisk5"
   VOLUME = "1"
   XID = "0x2d2"

1. **Map the Tree:**  
   sudo python build\_tree.py /TargetFolder

2. **Harvest Snapshots:**  
   sudo python3 harvest\_metadata.py

3. **Extract the Data:**  
   sudo python3 data\_recovery.py

## **Operational Tips**

### **Handling Long Recovery Times**

Use the keep\_sudo\_alive() function in the scripts to prevent the sudo session from timing out during long overnight runs.

### **The "Zero-Byte" Risk**

If a file recovers as 0 bytes, it may have been TRIMmed by the SSD. Try setting a deeper XID\_LIMIT in Phase 2 to find a version of the file before the blocks were marked as free.

## **Disclaimer**

This is a logical recovery tool. It cannot fix physical drive failure or broken encryption. Always attempt recovery on a "Read-Only" mount to prevent further data loss.