import os
import requests
import json
import time
import datetime
import urllib3

# --- KONFIGURACJA ---

# 1. TUTAJ WKLEJ SWÓJ AKTUALNY TOKEN
MY_ACCESS_TOKEN = "token"

# Adres bazowy (potwierdzony)
API_BASE_URL = "adres_servera"

# Folder z plikami i logi
INPUT_DIR = "output"
LOG_FILE = "log_import.txt"

# --- CONFIG ENDPOINTÓW (Dla łatwej zmiany) ---
ENDPOINT_TMS = "tms"          # Zmienione z translationmemories
ENDPOINT_FILES = "fileuploads" # Zmienione z files (często w parze z tms idzie fileuploads)
ENDPOINT_TASKS = "tasks"

# --- PRZYGOTOWANIE NAGŁÓWKÓW ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

AUTH_HEADER = f"MQS-API {MY_ACCESS_TOKEN}"

HEADERS_JSON = {
    "Authorization": AUTH_HEADER,
    "Content-Type": "application/json"
}

HEADERS_STREAM = {
    "Authorization": AUTH_HEADER,
    "Content-Type": "application/octet-stream" 
}

# --- FUNKCJE ---

def log_status(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = f"[{timestamp}] {message}"
    print(msg)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

def get_original_tm_info(tm_name_clean):
    # Endpoint: /tms
    url = f"{API_BASE_URL}/{ENDPOINT_TMS}"
    try:
        print(f"DEBUG: Pytam serwer o listę TM pod adresem: {url}")
        response = requests.get(url, headers=HEADERS_JSON, verify=False)
        
        if response.status_code != 200:
            log_status(f"ERROR: Błąd pobierania listy TM. Kod: {response.status_code}")
            return None

        tms = response.json()
        
        # Obliczamy czego szukamy
        search_name = tm_name_clean.replace("_Updated.tmx", "").replace(".tmx", "")
        print(f"DEBUG: Szukam pamięci o nazwie: '{search_name}'")
        print(f"DEBUG: Serwer zwrócił {len(tms)} pamięci.")

        # Przeszukujemy listę i wypisujemy co widzimy (pierwsze 5 dla testu)
        target_tm = None
        
        for i, tm in enumerate(tms):
            # Próba wyciągnięcia nazwy z różnych pól
            current_name = tm.get('Name') or tm.get('name') or tm.get('friendlyName')
            
            # Wypiszmy kilka pierwszych nazw, żeby zobaczyć format
            if i < 5: 
                print(f"Widzę na serwerze: '{current_name}'")

            if current_name and current_name.lower().strip() == search_name.lower().strip():
                print(f"ZNALAZŁEM PASUJĄCĄ PAMIĘĆ: {current_name}")
                target_tm = tm
                break
        
        if not target_tm:
            print(f"NIE ZNALAZŁEM pamięci '{search_name}' na liście pobranej z serwera.")
            print("Sprawdź, czy nie ma literówki lub spacji na końcu nazwy w memoQ.")
        
        return target_tm

    except Exception as e:
        log_status(f"ERROR: Błąd połączenia (Get Original): {str(e)}")
        return None

def get_tm_details(tm_guid):
    # Endpoint: /tms/{id}
    url = f"{API_BASE_URL}/{ENDPOINT_TMS}/{tm_guid}"
    resp = requests.get(url, headers=HEADERS_JSON, verify=False)
    if resp.status_code == 200:
        return resp.json()
    return None

def create_new_tm(original_details, new_name):
    # Endpoint: /tms
    url = f"{API_BASE_URL}/{ENDPOINT_TMS}"
    
    # Próbujemy pobrać dane, obsługując różne wielkości liter (Safe Get)
    def g(key_pascal, key_camel):
        return original_details.get(key_pascal) or original_details.get(key_camel)

    # Budujemy payload w PascalCase (wymagane dla /tms)
    payload = {
        "Name": new_name,
        "SourceLanguageCode": g("SourceLanguageCode", "sourceLanguageCode"),
        "TargetLanguageCode": g("TargetLanguageCode", "targetLanguageCode"),
        "Client": g("Client", "client"),
        "Domain": g("Domain", "domain"),
        "Subject": g("Subject", "subject"),
        "Project": g("Project", "project"),
        "IsStoreFullContext": g("IsStoreFullContext", "isStoreFullContext") or True,
        "IsReverseLang": g("IsReverseLang", "isReverseLang") or False
    }

    resp = requests.post(url, headers=HEADERS_JSON, json=payload, verify=False)
    
    if resp.status_code == 200 or resp.status_code == 201:
        data = resp.json()
        # Pobieramy ID (może być TmGuid lub Guid lub UniqueId)
        new_guid = data.get("TmGuid") or data.get("tmGuid") or data.get("Guid") or data.get("uniqueId")
        log_status(f"SUCCESS: Utworzono nową TM: {new_name}")
        return new_guid
    else:
        log_status(f"ERROR: Nie udało się utworzyć TM {new_name}. Kod: {resp.status_code}. Info: {resp.text}")
        return None

def upload_file(file_path):
    # Próbujemy endpoint /fileuploads (częsty dla /tms) lub /files
    url = f"{API_BASE_URL}/{ENDPOINT_FILES}"
    
    try:
        with open(file_path, 'rb') as f:
            resp = requests.post(url, headers=HEADERS_STREAM, data=f, verify=False)
            
        if resp.status_code == 200:
            # Zazwyczaj zwraca {"FileGuid": "..."}
            data = resp.json()
            return data.get("FileGuid") or data.get("fileGuid")
        elif resp.status_code == 404:
             log_status(f"ERROR: Endpoint '{ENDPOINT_FILES}' nie istnieje. Spróbuj zmienić w konfigu na 'files'.")
             return None
        else:
            log_status(f"ERROR: Błąd uploadu pliku. Kod: {resp.status_code}. Info: {resp.text}")
            return None
    except Exception as e:
        log_status(f"ERROR: Wyjątek przy uploadzie: {e}")
        return None

def wait_for_task(task_id):
    url = f"{API_BASE_URL}/{ENDPOINT_TASKS}/{task_id}"
    log_status(f"Czekam na zakończenie zadania {task_id}...")
    
    while True:
        resp = requests.get(url, headers=HEADERS_JSON, verify=False)
        if resp.status_code != 200:
            time.sleep(5)
            continue
            
        task_info = resp.json()
        # Status w PascalCase (Status) lub camelCase (status)
        status = task_info.get("Status") or task_info.get("status")
        
        if status == "Completed":
            return True, "Zakończono sukcesem"
        elif status in ["Failed", "Cancelled"]:
            # Pobierz error info
            err = task_info.get("TaskResult") # Czasem tu są szczegóły
            return False, f"Błąd zadania: {status} | {err}"
        
        time.sleep(2)

def main():
    if "WKLEJ" in MY_ACCESS_TOKEN:
        print("BŁĄD: Nie wkleiłeś tokena!")
        return

    if not os.path.exists(INPUT_DIR):
        print(f"Błąd: Nie znaleziono folderu {INPUT_DIR}")
        return

    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("--- START IMPORT PROCESS (TMS ENDPOINT MODE) ---\n")

    files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith('.tmx')]
    log_status(f"Znaleziono {len(files)} plików do importu.")

    for i, file_name in enumerate(files, 1):
        print(f"\n--- Przetwarzanie [{i}/{len(files)}]: {file_name} ---")
        
        # 1. Pobierz info o oryginale
        original_info = get_original_tm_info(file_name)
        if original_info is None:
            continue
        
        # Pobieramy GUID - obsługa różnych nazw pól
        orig_guid = original_info.get('TmGuid') or original_info.get('tmGuid') or original_info.get('Guid')
        
        # 2. Pobierz szczegóły
        original_details = get_tm_details(orig_guid)
        if not original_details: continue

        # 3. Utwórz nową TM
        new_tm_name = file_name.replace(".tmx", "")
        new_tm_guid = create_new_tm(original_details, new_tm_name)
        if not new_tm_guid: continue

        # 4. Upload pliku
        file_path = os.path.join(INPUT_DIR, file_name)
        uploaded_file_id = upload_file(file_path)
        if not uploaded_file_id: continue
            
        log_status(f"Zlecam import...")
        
        # Endpoint: /tms/{guid}/import
        import_url = f"{API_BASE_URL}/{ENDPOINT_TMS}/{new_tm_guid}/import"
        
        # Payload PascalCase
        import_payload = { "FileGuid": uploaded_file_id, "UpdateBehavior": "Add" }
        
        resp_import = requests.post(import_url, headers=HEADERS_JSON, json=import_payload, verify=False)
        
        if resp_import.status_code == 200:
            data = resp_import.json()
            task_id = data.get("TaskId") or data.get("taskId")
            success, msg = wait_for_task(task_id)
            if success:
                log_status(f"SUCCESS: Import zakończony.")
            else:
                log_status(f"FAILURE: {msg}")
        else:
            log_status(f"ERROR IMPORTU: {resp_import.text}")

        time.sleep(1)

    try:
        requests.post(f"{API_BASE_URL}/auth/logout", headers=HEADERS_JSON, verify=False)
        print("Wylogowano sesję.")
    except:
        pass

if __name__ == "__main__":
    main()
