# XLIFF Source to Target Copier

A specialized Python utility designed to prepare XML files for translation in Computer-Assisted Translation (CAT) tools like MemoQ.

Its primary purpose is to automate the pre-processing stage by populating missing target elements with source text. This ensures that the file is valid for import into localization software. In this workflow, after the translation is completed, the translated target text is used to overwrite the original content during the reconversion to the source format.

## Key Features

* **Localization Workflow Optimization:** Prepares files for CAT tools by ensuring every segment has a target container, which is crucial for specific reconversion processes where the target text replaces the source.
* **Smart Source Copying:** Identifies segments where the translation target is missing and automatically creates it by copying the source content.
* **Tag Preservation:** Uses deep copying to ensure all internal formatting tags (like inline codes, placeholders, or formatting tags) are correctly transferred to the target.
* **Namespace Handling:** Automatically detects and registers XML namespaces to ensure the output file maintains a clean structure without generated prefixes (e.g., ns0:).
* **Batch Processing:** Processes all .xml files in the directory simultaneously.
* **Non-destructive:** Saves processed files to a separate output folder, keeping original files untouched.

## Requirements

* Python 3.6+
* Standard libraries: os, copy, xml.etree.ElementTree

## How to Use

1. Place the script in the directory containing your .xml translation files.
2. Run the script:
   python Copy_source_to_target.py
3. The script will analyze all files with the .xml extension.
4. Processed files are saved in the newly created output folder.

## How It Works

1. **Namespace Registration:** The script first performs a pass to map all XML namespaces found in the file to prevent malformed output.
2. **Parsing:** It traverses the XML tree looking for elements ending with 'segment'.
3. **Gap Analysis:** Within each segment, it checks for the existence of 'source' and 'target' tags.
4. **Content Replication:** If a 'target' is missing, a new element is created. The text and all child elements (tags) from 'source' are deep-copied to the new 'target' element.
5. **Saving:** The modified XML tree is written to the output directory with standard UTF-8 encoding.

## Configuration

By default, the script looks for files with the .xml extension. You can modify the target extension by changing the configuration variable at the top of the script:

INPUT_EXT = '.xlf'  # Change to .xlf if needed

## License

This project is open-source and available for personal and educational use.