import os
import requests
import json
import time
import datetime
import urllib3

# --- KONFIGURACJA ---

# 1. TUTAJ WKLEJ TOKEN Z PIERWSZEGO SKRYPTU
MY_ACCESS_TOKEN = "WKLEJ_TUTAJ_DŁUGI_CIĄG_ZNAKÓW_Z_GENERATORA"

# Adres API
API_BASE_URL = "https://memoqapi.lidex.com.pl:8081/memoq/api/v1"

# Folder z plikami i logi
INPUT_DIR = "output"
LOG_FILE = "log_import.txt"

# --- PRZYGOTOWANIE NAGŁÓWKÓW ---
# Wyłączamy ostrzeżenia SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Budujemy nagłówek autoryzacji raz, na sztywno
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
    try:
        response = requests.get(f"{API_BASE_URL}/translationmemories", headers=HEADERS_JSON, verify=False)
        
        # Jeśli tutaj dostaniemy 401, to znaczy że token wygasł lub jest źle wklejony
        if response.status_code == 401:
            log_status("CRITICAL ERROR: Token wygasł lub jest nieprawidłowy! Wygeneruj nowy.")
            return None
        if response.status_code != 200:
            log_status(f"ERROR: Nie udało się pobrać listy TM. Kod: {response.status_code}")
            return None

        tms = response.json()
        original_name_search = tm_name_clean.replace("_Updated.tmx", "").replace(".tmx", "")
        
        target_tm = next((tm for tm in tms if tm['name'].lower() == original_name_search.lower()), None)
        return target_tm

    except Exception as e:
        log_status(f"ERROR: Błąd połączenia: {str(e)}")
        return None

def get_tm_details(tm_guid):
    url = f"{API_BASE_URL}/translationmemories/{tm_guid}"
    resp = requests.get(url, headers=HEADERS_JSON, verify=False)
    if resp.status_code == 200:
        return resp.json()
    return None

def create_new_tm(original_details, new_name):
    url = f"{API_BASE_URL}/translationmemories"
    
    payload = {
        "name": new_name,
        "sourceLanguageCode": original_details.get("sourceLanguageCode"),
        "targetLanguageCode": original_details.get("targetLanguageCode"),
        "client": original_details.get("client"),
        "domain": original_details.get("domain"),
        "subject": original_details.get("subject"),
        "project": original_details.get("project"),
        "isStoreFullContext": original_details.get("isStoreFullContext", True),
        "isReverseLang": original_details.get("isReverseLang", False)
    }

    resp = requests.post(url, headers=HEADERS_JSON, json=payload, verify=False)
    
    if resp.status_code == 200 or resp.status_code == 201:
        data = resp.json()
        new_guid = data.get("uniqueId") or data.get("tmGuid")
        log_status(f"SUCCESS: Utworzono nową TM: {new_name}")
        return new_guid
    else:
        log_status(f"ERROR: Nie udało się utworzyć TM {new_name}. Info: {resp.text}")
        return None

def upload_file(file_path):
    url = f"{API_BASE_URL}/files"
    try:
        with open(file_path, 'rb') as f:
            resp = requests.post(url, headers=HEADERS_STREAM, data=f, verify=False)
            
        if resp.status_code == 200:
            return resp.json().get("fileGuid")
        else:
            log_status(f"ERROR: Błąd uploadu pliku. Info: {resp.text}")
            return None
    except Exception as e:
        log_status(f"ERROR: Wyjątek przy uploadzie: {e}")
        return None

def wait_for_task(task_id):
    url = f"{API_BASE_URL}/tasks/{task_id}"
    log_status(f"Czekam na zakończenie zadania {task_id}...")
    
    while True:
        resp = requests.get(url, headers=HEADERS_JSON, verify=False)
        if resp.status_code != 200:
            time.sleep(5)
            continue
            
        task_info = resp.json()
        status = task_info.get("status")
        
        if status == "Completed":
            return True, "Zakończono sukcesem"
        elif status in ["Failed", "Cancelled"]:
            return False, f"Błąd zadania: {status}"
        
        time.sleep(2)

def main():
    if MY_ACCESS_TOKEN == "WKLEJ_TUTAJ_DŁUGI_CIĄG_ZNAKÓW_Z_GENERATORA":
        print("BŁĄD: Nie wkleiłeś tokena! Edytuj plik i wklej token w linii 11.")
        return

    if not os.path.exists(INPUT_DIR):
        print(f"Błąd: Nie znaleziono folderu {INPUT_DIR}")
        return

    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("--- START IMPORT PROCESS (MANUAL TOKEN) ---\n")

    files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith('.tmx')]
    log_status(f"Znaleziono {len(files)} plików do importu.")

    for i, file_name in enumerate(files, 1):
        print(f"\n--- Przetwarzanie [{i}/{len(files)}]: {file_name} ---")
        
        # 1. Sprawdź czy token działa (pobierając info o oryginale)
        original_info = get_original_tm_info(file_name)
        if original_info is None:
            # Jeśli get_original_tm_info zwróciło None, mogło paść połączenie lub auth
            # Sprawdź logi, jeśli to 401, to skrypt przerwie działanie przy następnym pliku też
            continue
        
        original_details = get_tm_details(original_info['tmGuid'])
        if not original_details: continue

        new_tm_name = file_name.replace(".tmx", "")
        new_tm_guid = create_new_tm(original_details, new_tm_name)
        if not new_tm_guid: continue

        file_path = os.path.join(INPUT_DIR, file_name)
        uploaded_file_id = upload_file(file_path)
        if not uploaded_file_id: continue
            
        log_status(f"Zlecam import...")
        import_url = f"{API_BASE_URL}/translationmemories/{new_tm_guid}/import"
        import_payload = { "fileGuid": uploaded_file_id, "updateBehavior": "Add" }
        
        resp_import = requests.post(import_url, headers=HEADERS_JSON, json=import_payload, verify=False)
        
        if resp_import.status_code == 200:
            task_id = resp_import.json().get("taskId")
            success, msg = wait_for_task(task_id)
            if success:
                log_status(f"SUCCESS: Import zakończony.")
            else:
                log_status(f"FAILURE: {msg}")
        else:
            log_status(f"ERROR IMPORTU: {resp_import.text}")

        time.sleep(1)

    # Na koniec próbujemy się wylogować, żeby być "grzecznym" dla serwera
    try:
        requests.post(f"{API_BASE_URL}/auth/logout", headers=HEADERS_JSON, verify=False)
        print("Wylogowano sesję.")
    except:
        pass

if __name__ == "__main__":
    main()
