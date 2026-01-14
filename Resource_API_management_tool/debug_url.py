import requests
import urllib3

# --- KONFIGURACJA ---
MY_ACCESS_TOKEN = "TUTAJ_WKLEJ_SWOJ_TOKEN"
API_BASE_URL = "https://memoqapi.lidex.com.pl:8081/memoqserverhttpapi/v1"

# Wyłączamy ostrzeżenia SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def check_endpoint(suffix):
    url = f"{API_BASE_URL}/{suffix}"
    headers = {
        "Authorization": f"MQS-API {MY_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    print(f"Sprawdzam adres: {url}")
    try:
        response = requests.get(url, headers=headers, verify=False, timeout=10)
        print(f"KOD: {response.status_code}")
        
        if response.status_code == 200:
            print("SUKCES! To jest właściwy adres.")
            return True
        elif response.status_code == 404:
            print("404 (Nie znaleziono - zła nazwa endpointu)")
        elif response.status_code == 401:
            print("401 (Błąd tokena - czy na pewno jest świeży?)")
        else:
            print(f"Inny błąd: {response.text[:100]}")
            
    except Exception as e:
        print(f"Błąd połączenia: {e}")
    print("-" * 30)
    return False

def main():
    print("--- ROZPOCZYNAM DIAGNOSTYKĘ ADRESÓW ---\n")
    
    # 1. Sprawdzamy standardową nazwę REST API
    check_endpoint("translationmemories")
    
    # 2. Sprawdzamy nazwę z Twojej dokumentacji (Legacy/Client API)
    check_endpoint("tms")
    
    # 3. Sprawdzamy inne warianty
    check_endpoint("TMs")

if __name__ == "__main__":
    main()
