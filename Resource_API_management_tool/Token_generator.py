import requests
import json
import getpass # Biblioteka do bezpiecznego wpisywania hasła (nie widać znaków)

# --- KONFIGURACJA ---
API_BASE_URL = "https://memoqapi.lidex.com.pl:8081/memoq/api/v1"

def main():
    print("--- GENERATOR TOKENA MEMOQ ---")
    
    # 1. Pobieranie danych od użytkownika (nie zapisujemy ich w kodzie!)
    username = input("Podaj login (np. DOMENA\\user): ")
    # getpass ukrywa wpisywane znaki dla bezpieczeństwa
    password = getpass.getpass("Podaj hasło: ")
    
    print("\nWybierz tryb logowania:")
    print("0 - Użytkownik memoQ (wewnętrzny)")
    print("1 - Użytkownik Windows/AD (domena)")
    mode_input = input("Twój wybór (0 lub 1): ")
    
    login_mode = 1 if mode_input.strip() == "1" else 0

    # 2. Wysyłanie żądania
    url = f"{API_BASE_URL}/auth/login"
    payload = {
        "username": username,
        "password": password,
        "LoginMode": str(login_mode)
    }

    try:
        # verify=False dla portu 8081 (self-signed cert)
        # Wyłączamy ostrzeżenia, żeby nie śmieciły w konsoli
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        resp = requests.post(url, json=payload, verify=False, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            token = data.get("AccessToken")
            print("\n" + "="*50)
            print("SUKCES! Twój token (ważny ok. 20 min bezczynności):")
            print("="*50)
            print(token)
            print("="*50)
            print("\nSkopiuj powyższy ciąg znaków (bez spacji) i wklej do głównego skryptu.")
        else:
            print(f"\nBŁĄD LOGOWANIA! Kod: {resp.status_code}")
            print(f"Treść błędu: {resp.text}")
            
    except Exception as e:
        print(f"\nBłąd połączenia: {str(e)}")

if __name__ == "__main__":
    main()
