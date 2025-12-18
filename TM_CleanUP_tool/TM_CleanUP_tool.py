
import os
import xml.etree.ElementTree as ET
import gc  # Garbage Collector do zarządzania pamięcią RAM
import datetime

# --- CONFIGURATION (KONFIGURACJA) ---

# Current directory where script is located (Bieżący katalog)
INPUT_DIR = "."
# Output directory for cleaned files (Katalog na wyczyszczone pliki)
OUTPUT_DIR = "output"
# File containing list of banned IDs (Plik z listą ID do usunięcia)
ID_LIST_FILE = "translatorID_list.txt"
# Log file name (Nazwa pliku z logami)
LOG_FILE = "log.txt"

# --- FUNCTIONS (FUNKCJE) ---

def load_banned_ids(file_path):
    """
    Loads banned translator IDs from a text file.
    (Wczytuje zbanowane ID tłumaczy z pliku tekstowego.)
    """
    ids = set()
    if not os.path.exists(file_path):
        print(f"CRITICAL ERROR: File {file_path} not found!")
        return ids

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            # Remove whitespace and convert to lower case for comparison
            # (Usuwamy białe znaki i zamieniamy na małe litery dla pewności porównania)
            clean_id = line.strip().lower()
            if clean_id:
                ids.add(clean_id)
    
    print(f"Loaded {len(ids)} banned IDs.")
    return ids

def log_status(message):
    """
    Writes message to log file and console.
    (Zapisuje wiadomość do pliku logu i konsoli.)
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_message = f"[{timestamp}] {message}"
    print(formatted_message)
    
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(formatted_message + "\n")

def process_tmx_file(file_path, file_name, banned_ids):
    """
    Parses TMX, removes segments created by banned IDs, and saves new file.
    (Parsuje TMX, usuwa segmenty stworzone przez zbanowane ID i zapisuje nowy plik.)
    """
    # Define output path (Ścieżka zapisu)
    new_file_name = file_name.replace(".tmx", "") + "_Updated.tmx"
    output_path = os.path.join(OUTPUT_DIR, new_file_name)

    try:
        # Parse XML tree
        # (Parsowanie drzewa XML)
        tree = ET.parse(file_path)
        root = tree.getroot()

        # Find body element. TMX structure: root -> header, body
        # (Znajdujemy element body)
        body = root.find('body')
        
        if body is None:
            log_status(f"ERROR: No <body> found in {file_name}")
            return

        removed_count = 0
        total_segments = 0

        # Iterate over a copy of the list to allow safe removal during iteration
        # (Iterujemy po kopii listy, aby bezpiecznie usuwać elementy w trakcie pętli)
        for tu in list(body):
            total_segments += 1
            
            # Get creationid attribute, safe get, lower case
            # (Pobieramy atrybut creationid, bezpieczne pobranie, małe litery)
            creation_id = tu.get('creationid', '').lower()
            
            # Check if ID is in banned list
            # (Sprawdzamy czy ID jest na liście do usunięcia)
            if creation_id in banned_ids:
                body.remove(tu)
                removed_count += 1

        # Check result status
        # (Sprawdzamy status wyniku)
        if removed_count > 0:
            status_msg = f"SUCCESS: {file_name} -> Removed {removed_count} segments (Total checked: {total_segments})."
        else:
            status_msg = f"OK (NO CHANGES): {file_name} -> No banned IDs found."

        # Save the updated file
        # (Zapisujemy zaktualizowany plik)
        # encoding="UTF-8" is standard for modern TMX, usually compatible with UTF-16 input
        tree.write(output_path, encoding="UTF-8", xml_declaration=True)
        
        log_status(status_msg)

        # Explicitly delete objects to free RAM immediately
        # (Jawne usunięcie obiektów, aby zwolnić RAM natychmiast)
        del body
        del root
        del tree

    except ET.ParseError:
        log_status(f"ERROR: Could not parse XML in {file_name}. File might be corrupted.")
    except Exception as e:
        log_status(f"ERROR: Critical failure processing {file_name}: {str(e)}")

def main():
    # Create output directory if not exists
    # (Stwórz folder wyjściowy jeśli nie istnieje)
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # Initialize log file
    # (Inicjalizacja pliku logu)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("--- TMX CLEANUP REPORT START ---\n")

    # Load IDs
    # (Wczytanie ID)
    banned_ids = load_banned_ids(ID_LIST_FILE)
    
    if not banned_ids:
        log_status("WARNING: ID list is empty. No segments will be removed.")

    # Get list of TMX files
    # (Pobranie listy plików TMX)
    files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith('.tmx')]
    
    log_status(f"Found {len(files)} TMX files to process.")

    # Process files loop
    # (Pętla przetwarzania plików)
    for i, file_name in enumerate(files, 1):
        file_path = os.path.join(INPUT_DIR, file_name)
        
        # Display progress in console only (so log file isn't cluttered)
        # (Wyświetl postęp tylko w konsoli)
        print(f"Processing [{i}/{len(files)}]: {file_name} ...", end="\r")
        
        process_tmx_file(file_path, file_name, banned_ids)
        
        # Force Garbage Collection after each file to handle 50GB volume safely
        # (Wymuś czyszczenie pamięci po każdym pliku, aby bezpiecznie obsłużyć 50GB)
        gc.collect()

    log_status("--- PROCESS COMPLETED ---")
    print("\nDone. Check log.txt for details.")

if __name__ == "__main__":
    main()
