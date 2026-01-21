# MemoQ Resource Name Extractor

A Python automation tool designed to manage and audit MemoQ resource backups (`.mqres` files).

When archiving Translation Memories, Term Bases, or LiveDocs in MemoQ, the resulting `.mqres` backup files often have filenames that do not reflect their internal resource names. This script batch-processes these files to extract the true "Resource Name" directly from the file content without needing to import them back into the CAT tool.

## Key Features

* **Regex-Based Extraction:** Utilizes Regular Expressions to rapidly scan file content for specific tags, avoiding the overhead of full XML parsing.
* **Bulk Processing:** Automatically identifies and processes all `.mqres` files within the directory.
* **Encoding Resilience:** Implements robust file reading (`errors='ignore'`) to handle potential character encoding issues often found in legacy backup files.
* **Reporting:** Exports findings to a CSV file, providing a clear mapping between the physical filename and the internal resource name.

## Requirements

* Python 3.6+
* Standard libraries: os, csv, re

## How to Use

1. Place the script in the directory containing your `.mqres` backup files.
2. Run the script:
   python extract_TMname_mqres.py
3. The script will scan the folder for supported files.
4. A new folder named "output" will be created.
5. The report is saved as: output/wyniki_regex.csv

## Output Data Structure

The generated CSV file uses a semicolon (;) delimiter and contains the following columns:

| Column | Description |
| :--- | :--- |
| **Nazwa pliku** | The physical filename on the disk. |
| **ResourceName** | The internal name of the resource extracted from the `<ResourceName>` tag. |
| **Status** | Processing result (e.g., OK, Missing Tag, Read Error). |

## Technical Details

### Extraction Logic
Instead of loading the entire DOM structure of potentially large XML-based backups, the script uses a targeted Regular Expression pattern:
`r"<ResourceName>(.*?)</ResourceName>"`

This approach is faster and more fault-tolerant when dealing with large batches of backup files where only specific metadata is required.

### Error Handling
The script is designed to continue processing even if individual files are corrupted. It uses a try-except block for file operations and logs specific error messages (e.g., read permission errors) directly into the "Status" column of the CSV report.

## License

This project is open-source and available for personal and educational use.