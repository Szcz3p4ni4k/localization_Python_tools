import requests
import csv
import urllib3
import time

# ==========================================
# KONFIGURACJA
# ==========================================
SERVER_URL = "https://memoqapi.lidex.com.pl:8081/memoqserverhttpapi/v1"
USERNAME = "TUTAJ_WPISZ_LOGIN"  
PASSWORD = "TUTAJ_WPISZ_HASLO"
RAPORT_FILE = "raport.csv"       # Format: NazwaTM;Liczba;UserID_Do_Usuniecia

# Wyłączamy ostrzeżenia SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# FUNKCJE API
# ==========================================

def api_login():
    """Logowanie i pobranie tokena (zgodnie z obrazkiem 2.1 Authentication)"""
    url = f"{SERVER_URL}/auth/login"
    payload = {
        "username": USERNAME,
        "password": PASSWORD,
        "LoginMode": "0" # 0 dla kont memoQ, 1 dla AD
    }
    
    print(f"--- Logowanie do {url} ---")
    try:
        resp = requests.post(url, json=payload, verify=False)
        if resp.status_code == 200:
            data = resp.json()
            token = data.get("AccessToken")
            print("Zalogowano pomyślnie.")
            return token
        else:
            print(f"Błąd logowania: {resp.status_code} {resp.text}")
            return None
    except Exception as e:
        print(f"Błąd połączenia: {e}")
        return None

def get_tms_map(token):
    """Pobiera listę TM i zwraca mapę {FriendlyName: TMGuid}"""
    url = f"{SERVER_URL}/tms"
    headers = {"Authorization": f"MQS-API {token}"}
    
    try:
        resp = requests.get(url, headers=headers, verify=False)
        if resp.status_code == 200:
            tms = resp.json()
            # Tworzymy słownik: Klucz to Nazwa, Wartość to GUID
            tm_map = {tm.get("FriendlyName"): tm.get("TMGuid") for tm in tms}
            print(f"Pobrano listę {len(tm_map)} pamięci z serwera.")
            return tm_map
        else:
            print(f"Błąd pobierania TM: {resp.status_code}")
            return {}
    except Exception as e:
        print(f"Błąd: {e}")
        return {}

def get_tm_details(token, tm_guid):
    """Pobiera szczegóły TM, żeby poznać liczbę wpisów (NumEntries)"""
    url = f"{SERVER_URL}/tms/{tm_guid}"
    headers = {"Authorization": f"MQS-API {token}"}
    resp = requests.get(url, headers=headers, verify=False)
    if resp.status_code == 200:
        return resp.json()
    return None

def check_and_delete_entries(token, tm_guid, banned_user, num_entries):
    """
    Iteruje po wpisach, sprawdza Creatora i usuwa jeśli pasuje.
    Korzysta z endpointów: 
    - GET v1/tms/{tmGuid}/entries/{entryId}
    - POST v1/tms/{tmGuid}/entries/{entryId}/delete
    """
    headers = {
        "Authorization": f"MQS-API {token}",
        "Content-Type": "application/json"
    }
    
    deleted_count = 0
    print(f"   -> Rozpoczynam skanowanie ok. {num_entries} wpisów...")

    # UWAGA: API memoQ zazwyczaj indeksuje wpisy od 1 lub 0. 
    # Zakładamy pętlę po przybliżonej liczbie wpisów.
    # WIDOCZNY PROBLEM: Jeśli ID nie są ciągłe (np. 1, 5, 100), pętla może trafić w próżnię.
    # Jednak API nie daje funkcji "List All Entry IDs", więc musimy zgadywać ID.
    
    # Dla bezpieczeństwa sprawdzamy zakres nieco większy niż liczba wpisów
    search_limit = int(num_entries) + 2000 
    
    for entry_id in range(1, search_limit):
        # 1. Pobierz wpis
        get_url = f"{SERVER_URL}/tms/{tm_guid}/entries/{entry_id}"
        resp_get = requests.get(get_url, headers=headers, verify=False)
        
        if resp_get.status_code == 404:
            continue # Brak wpisu o takim ID, idziemy dalej
            
        if resp_get.status_code == 200:
            entry_data = resp_get.json()
            
            # Sprawdzamy pole Creator (lub Modifier, zależnie co chcesz czyścić)
            creator = entry_data.get("Creator", "")
            modifier = entry_data.get("Modifier", "")
            
            # Czy użytkownik pasuje?
            if banned_user.lower() in creator.lower() or banned_user.lower() in modifier.lower():
                # 2. USUWANIE
                del_url = f"{SERVER_URL}/tms/{tm_guid}/entries/{entry_id}/delete"
                resp_del = requests.post(del_url, headers=headers, verify=False)
                
                if resp_del.status_code in [200, 204]:
                    print(f"      [DEL] Usunięto ID {entry_id} (User: {creator})")
                    deleted_count += 1
                else:
                    print(f"      [ERR] Błąd usuwania ID {entry_id}: {resp_del.status_code}")
        
        # Raport postępu co 100 wpisów
        if entry_id % 100 == 0:
            print(f"      ...przeskanowano {entry_id}/{search_limit}")

    return deleted_count

# ==========================================
# GŁÓWNA PĘTLA
# ==========================================

def main():
    # 1. Login
    token = api_login()
    if not token: return

    # 2. Mapa TM z serwera
    server_tms = get_tms_map(token) # { "Nazwa": "GUID" }
    
    # 3. Czytanie raportu i procesowanie
    try:
        with open(RAPORT_FILE, "r", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter=";")
            
            for row in reader:
                # Format CSV: NazwaPliku;Liczba;UserDoUsuniecia
                if len(row) < 3: continue
                
                tm_name = row[0].strip()
                banned_user = row[2].strip()
                
                print(f"\n--- Przetwarzanie: {tm_name} (Szukam usera: {banned_user}) ---")
                
                # Szukamy GUID dla nazwy z pliku CSV
                guid = server_tms.get(tm_name)
                
                if not guid:
                    # Próba dopasowania bez rozszerzenia .tmx jeśli jest w CSV
                    guid = server_tms.get(tm_name.replace(".tmx", ""))
                
                if guid:
                    # Pobieramy info o TM, żeby wiedzieć ile skanować
                    details = get_tm_details(token, guid)
                    if details:
                        num_entries = details.get("NumEntries", 1000)
                        deleted = check_and_delete_entries(token, guid, banned_user, num_entries)
                        print(f"ZAKOŃCZONO: Usunięto łącznie {deleted} segmentów z {tm_name}.")
                    else:
                        print("Nie udało się pobrać szczegółów TM.")
                else:
                    print(f"Nie znaleziono TM o nazwie '{tm_name}' na serwerze.")

    except FileNotFoundError:
        print(f"Brak pliku {RAPORT_FILE}")

    # 4. Logout
    requests.post(f"{SERVER_URL}/auth/logout", headers={"Authorization": f"MQS-API {token}"}, verify=False)

if __name__ == "__main__":
    main()
