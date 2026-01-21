import requests
import csv
import urllib3
import os
import xml.etree.ElementTree as ET

# ==========================================
# KONFIGURACJA
# ==========================================
SERVER_URL = "ADRES_SERWERA"
USERNAME = "TWOJ_LOGIN"
PASSWORD = "TWOJE_HASLO"

# Plik sterujący
RAPORT_FILE = "raport.csv"
# Folder gdzie leżą pliki .tmx (jeśli są w tym samym, zostaw kropkę)
TMX_DIR = "." 

# Wyłączamy ostrzeżenia SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# FUNKCJE POMOCNICZE
# ==========================================

def log(msg):
    print(f"[INFO] {msg}")

def error(msg):
    print(f"[ERROR] {msg}")

def api_login():
    """Logowanie POST /auth/login"""
    url = f"{SERVER_URL}/auth/login"
    payload = {
        "username": USERNAME,
        "password": PASSWORD,
        "LoginMode": "0"
    }
    headers = {"Content-Type": "application/json"}
    
    log(f"Logowanie do: {url}")
    try:
        resp = requests.post(url, json=payload, headers=headers, verify=False)
        if resp.status_code == 200:
            token = resp.json().get("AccessToken")
            log("Zalogowano pomyślnie.")
            return token
        else:
            error(f"Błąd logowania: {resp.status_code} | {resp.text}")
            return None
    except Exception as e:
        error(f"Wyjątek połączenia: {e}")
        return None

def get_server_tms_map(token):
    """Pobiera listę TM i mapuje FriendlyName -> TMGuid"""
    url = f"{SERVER_URL}/tms?authToken={token}"
    log("Pobieranie listy pamięci z serwera...")
    
    try:
        resp = requests.get(url, verify=False)
        if resp.status_code == 200:
            data = resp.json()
            mapping = {}
            for tm in data:
                # Szukamy FriendlyName, jeśli brak to Name
                name = tm.get("FriendlyName") or tm.get("Name")
                guid = tm.get("TMGuid") or tm.get("TmGuid")
                if name and guid:
                    mapping[name] = guid
            log(f"Pobrano {len(mapping)} pamięci.")
            return mapping
        else:
            error(f"Błąd pobierania listy TM: {resp.status_code}")
            return {}
    except Exception as e:
        error(f"Błąd pobierania listy: {e}")
        return {}

def get_ids_to_delete_from_tmx(file_path, banned_user):
    """
    Parsuje plik TMX w trybie strumieniowym (oszczędność RAM).
    Zwraca listę indeksów (int), w których creationid == banned_user.
    Indeksy liczone są od 0 (kolejność występowania <tu>).
    """
    ids_list = []
    
    # Licznik segmentów (nasze ID)
    current_index = 0
    
    try:
        # iterparse pozwala czytać plik kawałek po kawałku
        context = ET.iterparse(file_path, events=("end",))
        
        for event, elem in context:
            # Interesują nas tylko tagi <tu> (Translation Unit)
            if elem.tag == "tu":
                # Sprawdzamy atrybut creationid
                # Uwaga: atrybuty w XML bywają case-sensitive, zazwyczaj jest to 'creationid'
                c_id = elem.get("creationid")
                
                # Czasem memoQ używa 'changeid' jeśli to była edycja, 
                # ale instrukcja mówi o creationid. Sprawdzamy match.
                if c_id and c_id.lower() == banned_user.lower():
                    ids_list.append(current_index)
                
                # WAŻNE: Czyścimy element z RAMu po przetworzeniu!
                elem.clear()
                current_index += 1
                
        return ids_list
        
    except Exception as e:
        error(f"Błąd parsowania pliku {file_path}: {e}")
        return []

def delete_entries_on_server(token, tm_guid, ids_list):
    """
    Wysyła żądania usunięcia dla listy ID.
    Sortuje ID malejąco, aby uniknąć problemu przesuwania indeksów.
    """
    # SORTOWANIE MALEJĄCE (Reverse) - Kluczowe dla bezpieczeństwa indeksów
    ids_list.sort(reverse=True)
    
    deleted_count = 0
    total = len(ids_list)
    
    log(f"Rozpoczynam usuwanie {total} segmentów (kolejność malejąca)...")
    
    for i, entry_id in enumerate(ids_list, 1):
        # URL do usuwania
        url = f"{SERVER_URL}/tms/{tm_guid}/entries/{entry_id}/delete?authToken={token}"
        
        try:
            # POST bez body, token w URL
            resp = requests.post(url, verify=False)
            
            if resp.status_code in [200, 204]:
                # Sukces
                deleted_count += 1
            elif resp.status_code == 404:
                error(f"Segment ID {entry_id} nie istnieje na serwerze (już usunięty?).")
            else:
                error(f"Błąd usuwania ID {entry_id}: {resp.status_code}")
                
        except Exception as e:
            error(f"Wyjątek przy ID {entry_id}: {e}")
            
        # Logowanie postępu co 100 sztuk
        if i % 100 == 0:
            print(f"   Postęp: {i}/{total} usunięto...")
            
    return deleted_count

# ==========================================
# GŁÓWNA PĘTLA
# ==========================================

def main():
    # 1. Logowanie
    token = api_login()
    if not token: return
    
    # 2. Mapa pamięci z serwera
    server_map = get_server_tms_map(token)
    if not server_map: return

    # 3. Przetwarzanie raportu
    if not os.path.exists(RAPORT_FILE):
        error(f"Brak pliku raportu: {RAPORT_FILE}")
        return

    with open(RAPORT_FILE, "r", encoding="utf-8") as f:
        # Zakładam separator średnik ; (typowy dla CSV w PL)
        reader = csv.reader(f, delimiter=";")
        
        for row in reader:
            # Format: NazwaPliku.tmx ; Liczba ; UserID
            if len(row) < 3: continue
            
            filename = row[0].strip()
            banned_user = row[2].strip()
            
            # 3a. Znalezienie FriendlyName (usuwamy .tmx)
            friendly_name_search = filename.replace(".tmx", "").strip()
            
            print(f"\n--- Przetwarzanie: {filename} (User: {banned_user}) ---")
            
            # 3b. Pobranie GUID z mapy serwera
            # Szukamy dokładnego dopasowania lub ignorując wielkość liter
            tm_guid = server_map.get(friendly_name_search)
            
            if not tm_guid:
                # Próba case-insensitive
                for s_name, s_guid in server_map.items():
                    if s_name.lower() == friendly_name_search.lower():
                        tm_guid = s_guid
                        break
            
            if not tm_guid:
                error(f"Nie znaleziono pamięci '{friendly_name_search}' na serwerze. Pomijam.")
                continue
                
            log(f"Znaleziono GUID: {tm_guid}")
            
            # 3c. Analiza lokalnego pliku TMX (wyznaczanie ID do usunięcia)
            local_path = os.path.join(TMX_DIR, filename)
            if not os.path.exists(local_path):
                error(f"Nie znaleziono pliku lokalnego: {local_path}. Nie mogę wyznaczyć ID.")
                continue
                
            ids_to_delete = get_ids_to_delete_from_tmx(local_path, banned_user)
            
            if not ids_to_delete:
                log("Brak segmentów tego użytkownika w pliku lokalnym.")
                continue
                
            log(f"Znaleziono {len(ids_to_delete)} segmentów do usunięcia w pliku lokalnym.")
            
            # 3d. Wykonanie usuwania na serwerze
            deleted = delete_entries_on_server(token, tm_guid, ids_to_delete)
            log(f"Zakończono dla {filename}. Pomyślnie usunięto: {deleted}/{len(ids_to_delete)}")

    # 4. Wylogowanie
    try:
        requests.post(f"{SERVER_URL}/auth/logout", headers={"Content-Type": "application/json"}, verify=False)
        log("Wylogowano.")
    except: pass

if __name__ == "__main__":
    main()
