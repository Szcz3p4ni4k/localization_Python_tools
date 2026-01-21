# MemoQ Server Translation Memory Cleaner

A Python automation tool designed for granular management of Translation Memories hosted on a MemoQ Server.

This utility automates the process of removing specific translation units (TUs) created by designated users from a live server-based Translation Memory. It addresses a specific limitation in the standard MemoQ API by combining local TMX analysis with server-side execution.

## The Problem
The standard MemoQ Resource API allows deleting entries by their specific *Row Index*, but it lacks a direct function to "Delete all segments created by User X". Manually finding and removing thousands of segments scattered across massive TMs is impossible.

## The Solution (Hybrid Workflow)
This tool implements a hybrid approach:
1.  **Local Analysis:** It parses a local TMX backup of the memory to identify the exact indices of segments belonging to a specific user.
2.  **Server Execution:** It maps these indices to the live server TM and executes deletion requests via the HTTP API.

## Key Features

* **API Integration:** Connects seamlessly to MemoQ Server HTTP API (v1) to manage resources.
* **Memory Efficient Parsing:** Uses `xml.etree.ElementTree.iterparse` to stream process large TMX files (GBs in size) without loading them into RAM, ensuring low memory footprint.
* **Safe Deletion Logic:**
    * Automatically maps "Friendly Names" from reports to internal server "GUIDs".
    * Sorts deletion indices in **descending order** (`reverse=True`) before execution. This prevents index shifting errors (where deleting row 5 changes the index of row 6 to 5).
* **Batch Automation:** Capable of cleaning multiple TMs for different users in a single run based on a CSV control file.

## Requirements

* Python 3.8+
* External libraries: `requests`, `urllib3`
* Access to MemoQ Resource API (Base URL, Username, Password)

## Installation

1.  Clone the repository.
2.  Install required dependencies:
    ```bash
    pip install requests
    ```

## Configuration

Open the script file `RAPI_tm_cleaner.py` and configure the connection constants at the top:

```
# Server Configuration
SERVER_URL = "[https://your-memoq-server.com:8081/memoqserverhttpapi/v1](https://your-memoq-server.com:8081/memoqserverhttpapi/v1)"
USERNAME = "api_admin"
PASSWORD = "secure_password"

# File Configuration
RAPORT_FILE = "raport.csv" # The control file
TMX_DIR = "."              # Directory containing local TMX backups```

## Logic Overview

1. Authentication: Login to /auth/login to obtain a bearer token.

2. Mapping: Fetch the list of all TMs from the server (/tms) to link the filenames in the CSV to server GUIDs.

3. Iterative Processing:

	*Read the next line from raport.csv.
	*Open the corresponding local TMX file.
	*Scan for <tu> tags where creationid matches the target user.
	*Collect a list of indices (0-based).

4. Execution:
	*Send POST /tms/{guid}/entries/{id}/delete requests for each identified index.
	*Log success/failure counts.
	
## Disclaimer
This tool performs destructive actions (deletion) on a production database. Always ensure you have a fresh backup of your Translation Memories before running batch deletions.