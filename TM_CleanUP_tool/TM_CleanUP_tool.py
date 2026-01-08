import os
import csv
import re
import gc
import xml.etree.ElementTree as ET
import datetime

# --- CONFIGURATION (KONFIGURACJA) ---

# Current directory is input (Bieżący katalog to input)
INPUT_DIR = "."
# Output directory for cleaned files (Folder na pliki wynikowe)
OUTPUT_DIR = "output"
# CSV Report file (Nazwa pliku z raportem CSV)
CSV_REPORT_FILE = "raport.csv"
# Log file (Plik logów)
LOG_FILE = "log.txt"

# --- FUNCTIONS (FUNKCJE) ---

def log_status(message):
    """
    Writes message to log file and prints to console.
    (Zapisuje wiadomość do pliku logu i wyświetla w konsoli.)
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_message = f"[{timestamp}] {message}"
    print(formatted_message)
    
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(formatted_message + "\n")
    except Exception as e:
        print(f"Error writing to log: {e}")

def parse_csv_tasks(csv_path):
    """
    Parses the CSV report and groups banned IDs by TM filename.
    Returns a dictionary: { 'filename.tmx': {'id1', 'id2'} }
    (Parsuje raport CSV i grupuje ID do usunięcia według nazwy pliku TM.)
    """
    tasks = {} # Key: TM Name, Value: Set of IDs
    
    if not os.path.exists(csv_path):
        log_status(f"CRITICAL ERROR: CSV report file '{csv_path}' not found!")
        return tasks

    log_status("Reading CSV report and grouping tasks...")

    try:
        with open(csv_path, 'r', encoding='utf-8', errors='replace') as f:
            # Detect delimiter automatically or force ';' based on instruction
            # (Wykrywamy separator, tutaj wymuszamy średnik zgodnie z instrukcją)
            reader = csv.reader(f, delimiter=';')
            
            headers = next(reader, None) # Skip header (Pomiń nagłówek)
            
            # We assume columns based on instruction:
            # Col 0: "Nazwa TM", Col 2: "ID Tlumacza"
            # (Zakładamy kolejność kolumn z instrukcji)
            
            for row_idx, row in enumerate(reader, start=2):
                if len(row) < 3:
                    continue # Skip empty/malformed rows (Pomiń błędne wiersze)
                
                tm_name = row[0].strip().replace('"', '') # Remove CSV quotes if present
                translator_id = row[2].strip().lower() # Normalize ID
                
                if not tm_name or not translator_id:
                    continue

                # Ensure filename has extension (Upewnij się, że nazwa ma rozszerzenie)
                if not tm_name.lower().endswith('.tmx'):
                    tm_name += ".tmx"

                # Add to tasks map (Dodaj do mapy zadań)
                if tm_name not in tasks:
                    tasks[tm_name] = set()
                
                tasks[tm_name].add(translator_id)
                
    except Exception as e:
        log_status(f"CRITICAL ERROR parsing CSV: {e}")
        return {}

    log_status(f"CSV Analysis complete. Found tasks for {len(tasks)} files.")
    return tasks

def restore_memoq_quotes(xml_bytes):
    """
    Post-processing to restore single quotes in specific memoQ tags (bpt, ept, ph, it).
    Standard XML parsers convert attributes to double quotes, which changes the file structure.
    This function uses Regex on the binary content to revert this for specific tags.
    
    (Post-processing przywracający pojedyncze cudzysłowy w tagach memoQ.
    Standardowe parsery XML zamieniają atrybuty na podwójne cudzysłowy.
    Ta funkcja używa Regex na danych binarnych, aby to naprawić w konkretnych tagach.)
    """
    
    # Decodes bytes to string for regex processing (ignoring potential encoding errors for safety)
    # (Dekodujemy bajty na string do obróbki regexem)
    try:
        content = xml_bytes.decode('utf-16-le')
    except UnicodeDecodeError:
        # Fallback if strict utf-16 fails, though unlikely with proper handling
        content = xml_bytes.decode('utf-16-le', errors='ignore')

    # Regex pattern to find tags: bpt, ept, ph, it, mq:ch
    # We look for the whole tag content
    # (Wzorzec Regex znajdujący całe tagi bpt, ept, ph, it)
    tag_pattern = re.compile(r'(<\s*(?:bpt|ept|ph|it|mq:ch)\s+[^>]*?>)', re.IGNORECASE)

    def replace_quotes_in_match(match):
        # Inside the tag, replace i="..." with i='...' and type="..." with type='...'
        # (Wewnątrz znalezionego taga zamień cudzysłowy w atrybutach)
        tag_content = match.group(1)
        # Replace double quotes with single quotes for attributes
        # (Zamiana " na ' wewnątrz taga)
        fixed_content = tag_content.replace('"', "'")
        return fixed_content

    # Apply replacement
    new_content = tag_pattern.sub(replace_quotes_in_match, content)

    # Re-encode to UTF-16 LE
    return new_content.encode('utf-16-le')

def process_tmx_file(file_path, file_name, banned_ids_set):
    """
    Opens TMX, removes segments by IDs, fixes quotes, saves as UTF-16 LE.
    (Otwiera TMX, usuwa segmenty wg ID, naprawia cudzysłowy, zapisuje jako UTF-16 LE.)
    """
    new_file_name = file_name.replace(".tmx", "") + "_Updated.tmx"
    output_path = os.path.join(OUTPUT_DIR, new_file_name)

    # Check if input file exists
    if not os.path.exists(file_path):
        log_status(f"ERROR: File listed in CSV not found on disk: {file_name}")
        return

    try:
        # Parse XML (Parsowanie XML)
        tree = ET.parse(file_path)
        root = tree.getroot()
        body = root.find('body')

        if body is None:
            log_status(f"ERROR: No <body> found in {file_name}")
            return

        removed_count = 0
        total_segments = 0

        # Iteration and removal (Iteracja i usuwanie)
        for tu in list(body):
            total_segments += 1
            creation_id = tu.get('creationid', '').lower()
            
            if creation_id in banned_ids_set:
                body.remove(tu)
                removed_count += 1

        if removed_count == 0:
            log_status(f"OK (NO CHANGES): {file_name} - IDs from CSV not found in this file.")
        else:
            log_status(f"SUCCESS: {file_name} -> Removed {removed_count} segments.")

        # --- SAVING WITH ENCODING AND QUOTE FIX ---
        
        # 1. Serialize XML to a bytes buffer first (standard formatting with double quotes)
        # (Serializacja XML do bufora bajtów - standardowo z podwójnymi cudzysłowami)
        # We manually construct header to ensure DOCTYPE and encoding declaration
        
        xml_content_buffer = io.BytesIO()
        tree.write(xml_content_buffer, encoding='utf-16-le', xml_declaration=False)
        raw_xml_bytes = xml_content_buffer.getvalue()

        # 2. Fix Quotes (bpt i="1" -> bpt i='1')
        # (Naprawa cudzysłowów funkcją regex)
        fixed_xml_bytes = restore_memoq_quotes(raw_xml_bytes)

        # 3. Write to file with BOM and Header
        # (Zapis do pliku z BOM i nagłówkiem)
        with open(output_path, 'wb') as f:
            f.write(b'\xff\xfe') # UTF-16 LE BOM
            header = '<?xml version="1.0" encoding="utf-16"?>\n<!DOCTYPE tmx SYSTEM "tmx14.dtd">\n'
            f.write(header.encode('utf-16-le'))
            f.write(fixed_xml_bytes)

        # Cleanup RAM (Czyszczenie RAM)
        del body, root, tree, raw_xml_bytes, fixed_xml_bytes
        gc.collect()

    except ET.ParseError:
        log_status(f"ERROR: Corrupted XML in {file_name}")
    except Exception as e:
        log_status(f"ERROR processing {file_name}: {str(e)}")

import io # Imported here for the buffer usage above

def main():
    # Setup folders (Przygotowanie folderów)
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    
    # Init log (Inicjalizacja logu)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"--- START: {datetime.datetime.now()} ---\n")

    # 1. Parse CSV to get tasks (Analiza CSV aby pobrać zadania)
    # This creates a map: filename -> list of IDs to remove
    # (To tworzy mapę: nazwa pliku -> lista ID do usunięcia)
    tm_tasks = parse_csv_tasks(CSV_REPORT_FILE)
    
    if not tm_tasks:
        log_status("No tasks found in CSV or CSV is missing.")
        return

    # 2. Process only files listed in CSV (Przetwarzanie tylko plików z CSV)
    total_files = len(tm_tasks)
    current_idx = 0

    for filename, banned_ids in tm_tasks.items():
        current_idx += 1
        file_path = os.path.join(INPUT_DIR, filename)
        
        print(f"Processing [{current_idx}/{total_files}]: {filename} ...", end="\r")
        
        process_tmx_file(file_path, filename, banned_ids)

    print("\n--- DONE. Check log.txt ---")

if __name__ == "__main__":
    main()
