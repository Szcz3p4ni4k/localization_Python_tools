import os
import csv
import xml.etree.ElementTree as ET

# Pobiera ścieżkę do folderu, w którym jest ten skrypt
input_path = os.path.dirname(os.path.abspath(__file__))

print("========================================")
print(f"Uruchomiono skrypt w: {input_path}")
print("========================================")

# Krok 1: Szukanie plików
try:
    all_files = os.listdir(input_path)
    mqres_files = [f for f in all_files if f.lower().endswith('.mqres')]
    total_files = len(mqres_files)
    print(f"Znaleziono pliki .mqres: {total_files}")
except Exception as e:
    print(f"Blad krytyczny przy czytaniu folderu: {e}")
    mqres_files = []

# Krok 2: Przetwarzanie
if mqres_files:
    output_dir = os.path.join(input_path, "output")
    os.makedirs(output_dir, exist_ok=True)
    csv_path = os.path.join(output_dir, "wyniki.csv")
    
    print(f"Tworze plik csv: {csv_path}")
    
    try:
        with open(csv_path, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter=';')
            # Nagłówki kolumn
            writer.writerow(['Nazwa pliku', 'ResourceName', 'Status'])
            
            count = 0
            for filename in mqres_files:
                count += 1
                full_path = os.path.join(input_path, filename)
                
                # Zmienne domyślne (resetowane dla każdego pliku)
                resource_val = "-"
                status_msg = "OK"
                
                # Próba wyciągnięcia danych
                try:
                    tree = ET.parse(full_path)
                    # Szukamy niezależnie od głębokości zagnieżdżenia
                    node = tree.find(".//TemplateTMResourceInfo/ResourceName")
                    
                    if node is not None and node.text:
                        resource_val = node.text
                    else:
                        resource_val = "BRAK DANYCH W XML"
                        
                except ET.ParseError:
                    resource_val = "USZKODZONY PLIK XML"
                    status_msg = "BLAD XML"
                except Exception as e:
                    resource_val = "BLAD ODCZYTU"
                    status_msg = f"Error: {str(e)}"
                
                # ZAPISUJEMY WIERSZ (To musi być równo z 'try' powyżej)
                writer.writerow([filename, resource_val, status_msg])
                
                # Wyświetlanie postępu co 10 plików (żeby nie spamować) lub dla każdego jeśli wolisz
                print(f"[{count}/{total_files}] Przetworzono: {filename} -> {resource_val}")

            print("========================================")
            print(f"SUKCES! Zapisano lacznie {count} wierszy.")
            
    except Exception as e:
        print(f"BLAD zapisu pliku CSV (czy plik jest otwarty w Excelu?): {e}")

else:
    print("Nie mam czego przetwarzac. Brak plikow .mqres w folderze.")

print("========================================")
input("Nacisnij ENTER, aby zakonczyc")