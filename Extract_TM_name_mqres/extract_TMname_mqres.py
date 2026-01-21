import os
import csv
import re  # Biblioteka do wyrażeń regularnych (Regex)

# Pobiera ścieżkę do folderu, w którym jest ten skrypt
input_path = os.path.dirname(os.path.abspath(__file__))

print("========================================")
print(f"Pracuje w folderze: {input_path}")
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

# Krok 2: Przetwarzanie tekstowe
if mqres_files:
    output_dir = os.path.join(input_path, "output")
    os.makedirs(output_dir, exist_ok=True)
    csv_path = os.path.join(output_dir, "wyniki_regex.csv")
    
    print(f"Tworze plik csv: {csv_path}")
    
    try:
        with open(csv_path, mode='w', newline='', encoding='utf-8') as f_out: 
            writer = csv.writer(f_out, delimiter=';')
            writer.writerow(['Nazwa pliku', 'ResourceName', 'Status'])
            
            count = 0
            
            # Wzorzec Regex: szukamy wszystkiego pomiędzy tagami
            # (.*?) oznacza: złap dowolny ciąg znaków (jak najmniej), aż trafisz na zamknięcie tagu
            pattern = re.compile(r"<ResourceName>(.*?)</ResourceName>")
            

            for filename in mqres_files:
                count += 1
                full_path = os.path.join(input_path, filename)
                resource_val = "-"
                status_msg = "OK"

                try:
                    # Otwieramy plik jako zwykły tekst.
                    # errors='ignore' sprawia, że skrypt nie wyrzuci błędu przy dziwnych znakach.
                    with open(full_path, 'r', encoding='utf-8', errors='ignore') as f_in:
                        content = f_in.read()
                        
                        # Szukamy wzorca w treści pliku
                        match = pattern.search(content)
                        
                        if match:
                            # match.group(1) to to, co jest wewnątrz nawiasów (.*?)
                            resource_val = match.group(1)
                        else:
                            resource_val = "BRAK TAGU"
                            status_msg = "Nie znaleziono wzorca"
                            
                except Exception as e:
                    resource_val = "BLAD ODCZYTU PLIKU"
                    status_msg = str(e)

                # Zapis do CSV
                writer.writerow([filename, resource_val, status_msg])
                
                # Wyświetlanie postępu
                print(f"[{count}/{total_files}] {filename} -> {resource_val}")

            print("========================================")
            print(f"SUKCES! Przetworzono {count} plikow.")
            
    except Exception as e:
        print(f"BLAD zapisu pliku CSV (zamknij Excela!): {e}")

else:
    print("Nie mam czego przetwarzac. Brak plikow .mqres w folderze.")

print("========================================")
input("Nacisnij ENTER, aby zakonczyc")