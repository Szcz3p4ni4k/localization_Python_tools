import os
import requests
import json
import time
import datetime

# --- KONFIGURACJA ---

API_BASE_URL = "https://ADRES_TWOJEGO_SERWERA/memoq/api/v1"

API_KEY = "TU_WKLEJ_SWOJ_KLUCZ_GUID"

# Folder z wyczyszczonymi plikami
INPUT_DIR = "output"

# Plik raportu
LOG_FILE = "log_import.txt"

# --- HEADERS ---
HEADERS_JSON = {
    "ApiKey": API_KEY,
    "Content-Type": "application/json"
}
HEADERS_STREAM = {
    "ApiKey": API_KEY,
    "Content-Type": "application/octet-stream" 
}

# --- FUNKCJE ---

def log_status(message):
    #Zapisuje logi do pliku i konsoli
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = f"[{timestamp}] {message}"
    print(msg)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

def get_original_tm_info(tm_name_clean):
    
    #Szuka na serwerze TM o podanej nazwie i zwraca jej ID oraz właściwości.
    
    try:
        # 1. Pobierz listę wszystkich TM
        response = requests.get(f"{API_BASE_URL}/translationmemories", headers=HEADERS_JSON)
        if response.status_code != 200:
            log_status(f"ERROR: Nie udało się pobrać listy TM. Kod: {response.status_code}")
            return None

        tms = response.json()
        
        # Szukamy TM o nazwie idealnie pasującej do nazwy pliku (bez _Updated.tmx)
        # Zakładamy, że plik na dysku to "Nazwa_Updated.tmx", a oryginał to "Nazwa"
        original_name_search = tm_name_clean.replace("_Updated.tmx", "").replace(".tmx", "")
        
        target_tm = next((tm for tm in tms if tm['name'].lower() == original_name_search.lower()), None)
        
        if target_tm:
            return target_tm
        else:
            log_status(f"WARNING: Nie znaleziono na serwerze TM o nazwie: {original_name_search}")
            return None

    except Exception as e:
        log_status(f"ERROR: Błąd połączenia przy szukaniu TM: {str(e)}")
        return None

def get_tm_details(tm_guid):
    #Pobiera szczegółowe metadane TM (Client, Domain, etc.)
    url = f"{API_BASE_URL}/translationmemories/{tm_guid}"
    resp = requests.get(url, headers=HEADERS_JSON)
    if resp.status_code == 200:
        return resp.json()
    return None

def create_new_tm(original_details, new_name):
    """Tworzy nową TM kopiując ustawienia starej"""
    url = f"{API_BASE_URL}/translationmemories"
    
    # Mapowanie pól ze starej TM do nowej
    # API memoQ zwraca obiekt, który możemy w dużej mierze użyć do stworzenia nowej,
    # ale musimy zmienić nazwę.
    
    payload = {
        "name": new_name,
        "sourceLanguageCode": original_details.get("sourceLanguageCode"),
        "targetLanguageCode": original_details.get("targetLanguageCode"),
        "client": original_details.get("client"),
        "domain": original_details.get("domain"),
        "subject": original_details.get("subject"),
        "project": original_details.get("project"),
        "isStoreFullContext": original_details.get("isStoreFullContext", True), # Domyślnie True jeśli brak pola
        "isReverseLang": original_details.get("isReverseLang", False)
    }

    resp = requests.post(url, headers=HEADERS_JSON, json=payload)
    
    if resp.status_code == 200 or resp.status_code == 201:
        # API zwraca GUID nowej TM
        # W zależności od wersji API, może to być w polu 'uniqueId' lub wprost w body
        data = resp.json()
        new_guid = data.get("uniqueId") or data.get("tmGuid")
        log_status(f"SUCCESS: Utworzono nową TM: {new_name} (GUID: {new_guid})")
        return new_guid
    else:
        log_status(f"ERROR: Nie udało się utworzyć TM {new_name}. Info: {resp.text}")
        return None

def upload_file(file_path):
    
    #Wgrywa plik do File Storage API i zwraca fileId.
    #Otwiera plik jako binary ('rb') żeby zachować UTF-16 BOM.
    
    url = f"{API_BASE_URL}/files"
    
    try:
        # Otwieramy w trybie 'rb' - raw binary. Python wyśle to byte-to-byte.
        # kodowanie UTF-16 LE BOM z poprzedniego skryptu przejdzie nienaruszone.
        with open(file_path, 'rb') as f:
            resp = requests.post(url, headers=HEADERS_STREAM, data=f)
            
        if resp.status_code == 200:
            return resp.json().get("fileGuid")
        else:
            log_status(f"ERROR: Błąd uploadu pliku {file_path}. Info: {resp.text}")
            return None
    except Exception as e:
        log_status(f"ERROR: Wyjątek przy uploadzie: {e}")
        return None

def wait_for_task(task_id):
    #Czeka aktywnie na zakończenie zadania importu
    url = f"{API_BASE_URL}/tasks/{task_id}"
    
    log_status(f"Waiting for task {task_id} to finish...")
    
    while True:
        resp = requests.get(url, headers=HEADERS_JSON)
        if resp.status_code != 200:
            log_status("WARNING: Nie można sprawdzić statusu zadania.")
            time.sleep(5)
            continue
            
        task_info = resp.json()
        status = task_info.get("status") # Np. 'Pending', 'Executing', 'Completed', 'Failed', 'Cancelled'
        
        if status == "Completed":
            return True, "Zakończono sukcesem"
        elif status in ["Failed", "Cancelled"]:
            return False, f"Zadanie zakończone błędem: {status}"
        
        # Czekaj 2 sekundy przed kolejnym sprawdzeniem
        time.sleep(2)

def main():
    if not os.path.exists(INPUT_DIR):
        print(f"Błąd: Nie znaleziono folderu {INPUT_DIR}")
        return

    # Inicjalizacja logu
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("--- START IMPORT PROCESS ---\n")

    files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith('.tmx')]
    
    log_status(f"Znaleziono {len(files)} plików do importu.")

    for i, file_name in enumerate(files, 1):
        print(f"\n--- Przetwarzanie pliku [{i}/{len(files)}]: {file_name} ---")
        
        # 1. Znajdź oryginał na serwerze
        original_info = get_original_tm_info(file_name)
        
        if not original_info:
            log_status(f"SKIP: Pomijam plik {file_name} - brak odpowiednika na serwerze.")
            continue
        
        # Pobierz szczegóły (żeby mieć metadane Client, Domain itp.)
        original_details = get_tm_details(original_info['tmGuid'])
        if not original_details:
            log_status(f"SKIP: Nie udało się pobrać detali dla {original_info['name']}")
            continue

        # 2. Utwórz nową TM (Klonowanie ustawień)
        # Nazwa nowej TM to nazwa pliku bez rozszerzenia .tmx
        # Ponieważ plik nazywa się np. "Finanse_Updated.tmx", nowa TM będzie "Finanse_Updated"
        new_tm_name = file_name.replace(".tmx", "")
        
        new_tm_guid = create_new_tm(original_details, new_tm_name)
        if not new_tm_guid:
            continue # Błąd tworzenia, idź dalej

        # 3. Upload pliku TMX
        file_path = os.path.join(INPUT_DIR, file_name)
        uploaded_file_id = upload_file(file_path)
        
        if not uploaded_file_id:
            log_status("ERROR: Upload nieudany. Pomijam import.")
            continue
            
        # 4. Import do nowej TM
        log_status(f"Importowanie pliku do TM: {new_tm_name}...")
        
        import_url = f"{API_BASE_URL}/translationmemories/{new_tm_guid}/import"
        import_payload = {
            "fileGuid": uploaded_file_id,
            "updateBehavior": "Add" 
        }
        
        resp_import = requests.post(import_url, headers=HEADERS_JSON, json=import_payload)
        
        if resp_import.status_code == 200:
            task_id = resp_import.json().get("taskId")
            success, msg = wait_for_task(task_id)
            if success:
                log_status(f"SUCCESS: Import zakończony dla {new_tm_name}")
            else:
                log_status(f"FAILURE: Błąd importu dla {new_tm_name}: {msg}")
        else:
            log_status(f"ERROR: Nie udało się zlecić importu. {resp_import.text}")

        time.sleep(1)

    log_status("--- KONIEC PROCESU IMPORTU ---")

if __name__ == "__main__":
    main()
