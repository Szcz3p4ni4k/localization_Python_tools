import os
import xml.etree.ElementTree as ET
import gc  # Garbage Collector do ręcznego zwalniania pamięci RAM
import datetime

# --- CONFIGURATION (KONFIGURACJA) ---

# Current directory (Bieżący katalog, w którym jest skrypt)
INPUT_DIR = "."
# Output directory (Folder na wyczyszczone pliki)
OUTPUT_DIR = "output"
# File with banned IDs (Plik tekstowy z listą ID do usunięcia)
ID_LIST_FILE = "translatorID_list.txt"
# Log file (Plik raportu)
LOG_FILE = "log.txt"

# --- FUNCTIONS (FUNKCJE) ---

def load_banned_ids(file_path):
    """
    Loads banned translator IDs from a text file.
    (Wczytuje zbanowane ID tłumaczy z pliku tekstowego.)
    """
    ids = set()
    if not os.path.exists(file_path):
        log_status(f"CRITICAL ERROR: File {file_path} not found!")
        return ids

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            # Strip whitespace and convert to lower case
            # (Usuwamy białe znaki i zamieniamy na małe litery)
            clean_id = line.strip().lower()
            if clean_id:
                ids.add(clean_id)
    
    print(f"Loaded {len(ids)} banned IDs from list.")
    return ids

def log_status(message):
    """
    Writes message to log file and prints to console.
    (Zapisuje wiadomość do pliku logu i wyświetla w konsoli.)
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_message = f"[{timestamp}] {message}"
    
    # Print to console (Wypisz w konsoli)
    print(formatted_message)
    
    # Append to log file (Dopisz do pliku)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(formatted_message + "\n")
    except Exception as e:
        print(f"Error writing to log: {e}")

def process_tmx_file(file_path, file_name, banned_ids):
    """
    Parses TMX, removes segments by banned IDs, saves preserving UTF-16 LE + DOCTYPE.
    (Parsuje TMX, usuwa segmenty, zapisuje zachowując format UTF-16 LE i DOCTYPE.)
    """
    # Create output filename with suffix
    # (Tworzenie nazwy pliku wyjściowego z dopiskiem _Updated)
    new_file_name = file_name.replace(".tmx", "") + "_Updated.tmx"
    output_path = os.path.join(OUTPUT_DIR, new_file_name)

    try:
        # Parse the XML file
        # (Parsowanie pliku XML)
        tree = ET.parse(file_path)
        root = tree.getroot()

        # Find the body section
        # (Znajdź sekcję body)
        body = root.find('body')
        
        if body is None:
            log_status(f"ERROR: No <body> section found in {file_name}")
            return

        removed_count = 0
        total_segments = 0

        # Iterate over a COPY of the list (list(body)) to remove items safely
        # (Iterujemy po KOPII listy dzieci, aby bezpiecznie usuwać elementy)
        for tu in list(body):
            total_segments += 1
            
            # Get attributes safely, convert to lower case
            # (Pobierz atrybuty bezpiecznie, zamień na małe litery)
            creation_id = tu.get('creationid', '').lower()
            # If needed, you can also check changeid:
            # change_id = tu.get('changeid', '').lower()
            
            # Check if ID is banned
            # (Sprawdź czy ID jest na liście)
            if creation_id in banned_ids:
                body.remove(tu)
                removed_count += 1

        # Determine status message
        # (Określ status do raportu)
        if removed_count > 0:
            status_msg = f"SUCCESS: {file_name} -> Removed {removed_count} segments (Total checked: {total_segments})."
        else:
            status_msg = f"OK (NO CHANGES): {file_name} -> No banned IDs found."

        # --- SAVING FILE (ZAPIS PLIKU) ---
        # Manual write to enforce UTF-16 LE BOM and DOCTYPE
        # (Ręczny zapis w celu wymuszenia UTF-16 LE BOM i DOCTYPE)
        
        with open(output_path, 'wb') as f:
            # 1. Write BOM for UTF-16 Little Endian
            # (Zapisz BOM dla UTF-16 Little Endian)
            f.write(b'\xff\xfe')
            
            # 2. Write custom header string encoded in UTF-16 LE
            # (Zapisz niestandardowy nagłówek zakodowany w UTF-16 LE)
            header = '<?xml version="1.0" encoding="utf-16"?>\n<!DOCTYPE tmx SYSTEM "tmx14.dtd">\n'
            f.write(header.encode('utf-16-le'))
            
            # 3. Write the XML tree
            # (Zapisz drzewo XML)
            tree.write(f, encoding='utf-16-le', xml_declaration=False)

        log_status(status_msg)

        # Cleanup memory immediately
        # (Natychmiastowe czyszczenie pamięci)
        del body
        del root
        del tree

    except ET.ParseError:
        log_status(f"ERROR: XML Parse Error in {file_name}. File might be corrupted.")
    except Exception as e:
        log_status(f"ERROR: Critical failure processing {file_name}: {str(e)}")

def main():
    # Ensure output directory exists
    # (Upewnij się, że folder wyjściowy istnieje)
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # Reset/Create log file
    # (Reset/Tworzenie pliku logu)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"--- CLEANUP STARTED: {datetime.datetime.now()} ---\n")

    # Load IDs
    # (Wczytaj ID)
    banned_ids = load_banned_ids(ID_LIST_FILE)
    
    if not banned_ids:
        log_status("WARNING: ID list is empty! No segments will be removed.")
        # We continue anyway to check files, but nothing will be deleted.
        # (Kontynuujemy, ale nic nie zostanie usunięte).

    # Get list of .tmx files
    # (Pobierz listę plików .tmx)
    files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith('.tmx')]
    total_files = len(files)

    if total_files == 0:
        log_status("No .tmx files found in current directory.")
        return

    log_status(f"Found {total_files} TMX files. Starting process...")

    # Main Loop
    # (Główna pętla)
    for i, file_name in enumerate(files, 1):
        file_path = os.path.join(INPUT_DIR, file_name)
        
        # Display simplified progress in console
        # (Wyświetl uproszczony postęp w konsoli)
        print(f"Processing [{i}/{total_files}]: {file_name} ...", end="\r")
        
        # Process the file
        # (Przetwórz plik)
        process_tmx_file(file_path, file_name, banned_ids)
        
        # Force Garbage Collection to free RAM
        # (Wymuś zwolnienie pamięci RAM)
        gc.collect()

    # Final message
    # (Wiadomość końcowa)
    print("\n")
    log_status("--- PROCESS COMPLETED SUCCESSFULLY ---")
    print(f"Check {LOG_FILE} for details.")

if __name__ == "__main__":
    main()
