# TMX Translator Statistics Analyzer

Python tool designed to analyze Translation Memory eXchange (.tmx) files. It extracts detailed productivity statistics for individual translators/users, including segment counts, character counts, and modification timestamps.

## Key Features

* Memory Efficiency: Uses XML Streaming (ET.iterparse) to process files. This allows the script to handle gigabyte-sized TMX files without loading the entire DOM into RAM.
* **Tag Cleaning:** Implements Regex-based cleaning to calculate the "real" character count of text content, stripping out internal XML tags.
* **Detailed Metrics:** Calculates:
    * Created segments vs. Modified segments.
    * Character counts for new and modified translations.
    * Timestamps for the last activity.
* **Zero Dependencies:** Runs on standard Python libraries (no pip install required).
* **Batch Processing:** Automatically processes all .tmx files found in the script's directory.

## Requirements

* Python 3.6+
* Standard libraries used: os, csv, xml.etree.ElementTree, re, gc

## How to Use

1. Place the script in the same folder as your .tmx files.
2. Run the script:
   python TranslatorID_TMX_analysis.py
3. The tool will scan the directory and process files one by one.
4. A new folder named "Raport" will be created.
5. Results are saved in: Raport/analiza_tm_wyniki.csv

## Output Data Structure

The generated CSV file uses a semicolon (;) delimiter and contains the following columns:

| Column | Description |
| :--- | :--- |
| **Nazwa pliku** | Name of the processed TMX file. |
| **Calkowita ilosc segmentow** | Total number of translation units (<tu>) in the file. |
| **ID Tlumacza** | User ID extracted from creationid or changeid. |
| **Data ost. segmentu** | Date of the most recently created segment (YYYY.MM.DD). |
| **Data ost. zmiany** | Date of the most recent modification. |
| **Ilosc stworzonych segmentow** | Count of segments originally created by this user. |
| **Ilosc zmienionych segmentow** | Count of segments modified by this user. |
| **Ilosc stworzonych znakow** | Character count of created segments (tags removed). |
| **Ilosc zmienionych znakow** | Character count of modified segments (tags removed). |
| **Status** | Processing status (e.g., OK, Error message). |

## Technical Details

### XML Parsing Strategy
The script utilizes xml.etree.ElementTree.iterparse with events=('end',) to traverse the XML structure.
* **Optimization:** After processing each <tu> element, elem.clear() is called to free up memory immediately.
* **Garbage Collection:** Explicit gc.collect() is invoked to ensure memory is managed correctly during large batch operations.

### Text Analysis
To ensure accurate billing/statistics, the script calculates character counts based on "clean" text:
1. Extracts text using .itertext() to handle nested elements.
2. Removes residual XML-like tags using Regular Expressions.
