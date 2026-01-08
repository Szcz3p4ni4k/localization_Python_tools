import os
import csv
import re
import gc
import datetime

# --- KONFIGURACJA ---
INPUT_DIR = "."
OUTPUT_DIR = "output"
CSV_REPORT_FILE = "raport.csv"
LOG_FILE = "log.txt"

# --- FUNKCJE ---

def log_status(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_message = f"[{timestamp}] {message}"
    print(formatted_message)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(formatted_message + "\n")
    except Exception:
        pass

def parse_csv_tasks(csv_path):
    """
    Wczytuje CSV i tworzy mapę: { 'plik.tmx': {'id1', 'id2'} }
    """
    tasks = {}
    if not os.path.exists(csv_path):
        log_status(f"CRITICAL ERROR: Brak pliku raportu '{csv_path}'!")
        return tasks

    log_status("Analiza raportu CSV...")
    try:
        # errors='replace' pozwala przejść dalej mimo dziwnych znaków w CSV
        with open(csv_path, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.reader(f, delimiter=';')
            headers = next(reader, None) # Pomiń nagłówek
            
            for row in reader:
                if len(row) < 3: continue
                
                # Kolumna 0: Nazwa TM, Kolumna 2: ID Tłumacza
                tm_name = row[0].strip().replace('"', '')
                translator_id = row[2].strip().lower() # Normalizacja do małych liter
                
                if not tm_name or not translator_id: continue

                if not tm_name.lower().endswith('.tmx'):
                    tm_name += ".tmx"

                if tm_name not in tasks:
                    tasks[tm_name] = set()
                
                tasks[tm_name].add(translator_id)
                
    except Exception as e:
        log_status(f"BŁĄD CSV: {e}")
        return {}
    
    return tasks

def process_file_regex_mode(input_path, output_path, banned_ids):
    """
    Czyta plik linia po linii (jako czysty tekst UTF-16).
    Używa REGEX tylko do sprawdzenia ID wewnątrz bloku <tu>.
    Zachowuje oryginalną strukturę (znaki, cudzysłowy, entery) w 100%.
    """
    try:
        # UTF-16 w Pythonie automatycznie obsługuje BOM przy odczycie i zapisie
        with open(input_path, 'r', encoding='utf-16', newline='') as f_in, \
             open(output_path, 'w', encoding='utf-16', newline='') as f_out:
            
            tu_buffer = []      # Bufor na linie obecnego segmentu <tu>
            inside_tu = False   # Flaga: czy jesteśmy w środku segmentu?
            removed_count = 0
            
            # REGEX: Szuka creationid="X" LUB creationid='X' (niezależnie od wielkości liter)
            # Działa nawet jak atrybut jest w środku długiej linii
            creation_id_pattern = re.compile(r'creationid=["\'](.*?)["\']', re.IGNORECASE)

            for line in f_in:
                # Wykrywanie początku bloku <tu>
                # Sprawdzamy "<tu " (ze spacją) lub "<tu>" (sam tag), żeby nie złapać <tuv>
                if '<tu ' in line or '<tu>' in line:
                    inside_tu = True
                    tu_buffer.append(line)
                
                elif inside_tu:
                    tu_buffer.append(line)
                    
                    # Wykrywanie końca bloku </tu>
                    if '</tu>' in line:
                        # Blok się zamknął. Sprawdzamy czy go usunąć.
                        full_block_text = "".join(tu_buffer)
                        
                        # Szukamy ID w tekście bufora
                        match = creation_id_pattern.search(full_block_text)
                        should_remove = False
                        
                        if match:
                            found_id = match.group(1).lower()
                            if found_id in banned_ids:
                                should_remove = True
                        
                        if should_remove:
                            removed_count += 1
                            # Po prostu NIE zapisujemy tego bufora do pliku wyjściowego
                        else:
                            # Zapisujemy bufor dokładnie tak, jak został wczytany
                            f_out.write(full_block_text)
                        
                        # Resetujemy stan
                        inside_tu = False
                        tu_buffer = []
                
                else:
                    # Jesteśmy poza blokiem <tu> (nagłówek, stopka, inne tagi)
                    # Przepisujemy linię natychmiast bez zmian
                    f_out.write(line)

            return True, removed_count

    except Exception as e:
        return False, str(e)

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    
    # Inicjalizacja logu
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"--- START PROCESU: {datetime.datetime.now()} ---\n")

    # 1. Wczytaj zadania z CSV
    tm_tasks = parse_csv_tasks(CSV_REPORT_FILE)
    
    if not tm_tasks:
        log_status("Brak zadań w pliku CSV.")
        return

    total_files = len(tm_tasks)
    current_idx = 0

    # 2. Iteracja po plikach
    for filename, banned_ids in tm_tasks.items():
        current_idx += 1
        input_path = os.path.join(INPUT_DIR, filename)
        
        # Nazwa wyjściowa: Oryginał_Updated.tmx
        new_filename = filename.replace(".tmx", "") + "_Updated.tmx"
        output_path = os.path.join(OUTPUT_DIR, new_filename)
        
        print(f"Przetwarzanie [{current_idx}/{total_files}]: {filename} ...", end="\r")
        
        if not os.path.exists(input_path):
            log_status(f"BŁĄD: Nie znaleziono pliku {filename}")
            continue

        # Uruchomienie trybu REGEX
        success, result = process_file_regex_mode(input_path, output_path, banned_ids)
        
        if success:
            if result > 0:
                log_status(f"SUKCES: {filename} -> Usunięto {result} segmentów.")
            else:
                log_status(f"OK (BEZ ZMIAN): {filename} - Nie znaleziono ID z listy.")
        else:
            log_status(f"BŁĄD przetwarzania {filename}: {result}")
            
        # Zwolnij RAM
        gc.collect()

    print("\n--- ZAKOŃCZONO. Sprawdź log.txt ---")

if __name__ == "__main__":
    main()
