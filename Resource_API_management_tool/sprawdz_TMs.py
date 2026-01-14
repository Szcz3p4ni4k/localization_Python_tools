import requests
import json
import urllib3

# --- KONFIGURACJA ---
MY_ACCESS_TOKEN = "WKLEJ_TUTAJ_SWOJ_TOKEN"
API_BASE_URL = "https://memoqapi.lidex.com.pl:8081/memoqserverhttpapi/v1/tms"

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def main():
    print("--- DIAGNOSTYKA STRUKTURY JSON ---")
    
    headers = {
        "Authorization": f"MQS-API {MY_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(API_BASE_URL, headers=headers, verify=False)
        
        print(f"Status HTTP: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                # Wypisujemy ładnie sformatowany JSON (pierwszy element lub strukturę)
                print("\nCO ZWRACA SERWER (Próbka):")
                print(json.dumps(data, indent=4)[:2000]) # Pokaż pierwsze 2000 znaków
                
                print("\n--- ANALIZA ---")
                if isinstance(data, list):
                    print(f"To jest LISTA. Zawiera {len(data)} elementów.")
                    if len(data) > 0:
                        print("Przykładowe klucze w pierwszym elemencie:", data[0].keys())
                elif isinstance(data, dict):
                    print("To jest SŁOWNIK (Obiekt).")
                    print("Główne klucze:", data.keys())
                    # Często lista jest ukryta pod kluczem "Tms", "Values" lub "Result"
                else:
                    print("Nieznany typ danych.")
                    
            except json.JSONDecodeError:
                print("BŁĄD: Serwer nie zwrócił JSONa, tylko zwykły tekst.")
                print(response.text[:500])
        else:
            print("Błąd połączenia.")
            print(response.text)
            
    except Exception as e:
        print(f"Błąd krytyczny: {e}")

if __name__ == "__main__":
    main()
