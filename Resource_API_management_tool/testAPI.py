import requests

# Składamy pełny adres: Domena + Port + Ścieżka do zasobów
# Zazwyczaj jest to /memoq/api/v1
BASE_URL = "https://memoqapi.lidex.com.pl:8081/memoq/api/v1/translationmemories"

print(f"📡 Testuję połączenie z: {BASE_URL} ...\n")

try:
    # verify=False pozwala pominąć błąd certyfikatu SSL, 
    # co jest częste przy portach technicznych jak 8081
    response = requests.get(BASE_URL, timeout=10, verify=False)
    
    code = response.status_code
    print(f"Odpowiedź serwera: Kod {code}")

    if code == 401:
        print("✅ SUKCES! Serwer działa, API jest aktywne.")
        print("   Otrzymaliśmy '401 Unauthorized', co oznacza, że adres jest dobry,")
        print("   a serwer po prostu czeka na klucz API (którego jeszcze nie podaliśmy).")
    elif code == 200:
        print("⚠️ Działa, ale wpuścił nas bez klucza (nietypowe, ale OK).")
    elif code == 404:
        print("❌ Połączenie jest, ale ścieżka jest błędna.")
        print("   Spróbuj usunąć '/v1' z adresu.")
    else:
        print(f"❓ Inny status: {code}")

except requests.exceptions.ConnectionError:
    print("❌ Nie można połączyć się z serwerem.")
    print("   Upewnij się, że jesteś w sieci firmowej lub VPN, bo port 8081 może być zablokowany z zewnątrz.")
except Exception as e:
    print(f"❌ Wystąpił błąd: {e}")

# Wyłączenie ostrzeżeń o braku weryfikacji SSL (dla czytelności w konsoli)
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
