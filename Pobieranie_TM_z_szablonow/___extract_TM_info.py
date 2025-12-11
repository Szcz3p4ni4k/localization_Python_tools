import os
import csv
import re

# Pobiera ścieżkę do folderu, w którym jest ten skrypt
input_path = os.path.dirname(os.path.abspath(__file__))

print("========================================")
print(f"Folder roboczy: {input_path}")
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
    csv_path = os.path.join(output_dir, "wyniki_pelne.csv")
    
    print(f"Tworze plik csv: {csv_path}")
    
    try:
        with open(csv_path, mode='w', newline='', encoding='utf-8') as f_out:
            writer = csv.writer(f_out, delimiter=';')
            
            # NOWE NAGŁÓWKI KOLUMN
            writer.writerow(['Nazwa pliku', 'TM', 'Working TM', 'Master TM', 'Status'])
            
            count = 0
            
            # === DEFINICJA REGEXÓW ===
            # 1. TM (Szuka w bloku TemplateTMResourceInfo - tak jak ustaliliśmy wcześniej)
            pattern_tm = re.compile(
                r"<TemplateTMResourceInfo>.*?<ResourceName>(.*?)</ResourceName>", 
                re.DOTALL | re.IGNORECASE
            )
            
            # 2. Working TM (Szuka tagu WorkingTMNamingRule gdziekolwiek w pliku)
            pattern_working = re.compile(
                r"<WorkingTMNamingRule>(.*?)</WorkingTMNamingRule>", 
                re.DOTALL | re.IGNORECASE
            )

            # 3. Master TM (Szuka tagu MasterTMNamingRule gdziekolwiek w pliku)
            pattern_master = re.compile(
                r"<MasterTMNamingRule>(.*?)</MasterTMNamingRule>", 
                re.DOTALL | re.IGNORECASE
            )

            for filename in mqres_files:
                count += 1
                full_path = os.path.join(input_path, filename)
                
                # Zmienne na wyniki (domyślnie myślnik)
                val_tm = "-"
                val_working = "-"
                val_master = "-"
                status_msg = "OK"

                try:
                    with open(full_path, 'r', encoding='utf-8', errors='ignore') as f_in:
                        content = f_in.read()
                        
                        # --- SZUKANIE TM ---
                        match_tm = pattern_tm.search(content)
                        if match_tm:
                            val_tm = match_tm.group(1).strip()
                        else:
                            val_tm = "BRAK DANYCH"

                        # --- SZUKANIE WORKING TM ---
                        match_work = pattern_working.search(content)
                        if match_work:
                            val_working = match_work.group(1).strip()

                        # --- SZUKANIE MASTER TM ---
                        match_master = pattern_master.search(content)
                        if match_master:
                            val_master = match_master.group(1).strip()
                            
                except Exception as e:
                    status_msg = f"BLAD ODCZYTU: {str(e)}"

                # Zapisujemy wszystko do jednego wiersza
                writer.writerow([filename, val_tm, val_working, val_master, status_msg])
                
                # Wyświetlamy postęp (skrócony)
                print(f"[{count}/{total_files}] {filename} -> TM: {val_tm}")

            print("========================================")
            print(f"SUKCES! Przetworzono {count} plikow.")
            
    except Exception as e:
        print(f"BLAD zapisu pliku CSV (zamknij Excela!): {e}")

else:
    print("Nie mam czego przetwarzac. Brak plikow .mqres w folderze.")

print("========================================")
input("Nacisnij ENTER, aby zakonczyc")