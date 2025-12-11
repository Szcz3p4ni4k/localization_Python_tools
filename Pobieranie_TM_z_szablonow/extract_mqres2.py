import os
import csv
import xml.etree.ElementTree as ET

input_path = r"C:\Users\TomaszSzczepaniak\_Workdesk\Tools\Pobieranie_TM_z_szablonow\test\Backup_Szablonow_memoq"

def get_resource_name(file_path):
    # Funkcja pomocnicza, która otwiera plik XML 
    # i szuka tagu <ResourceName> wewnątrz bloku <TemplateTMResourceInfo>
    try:
        #Parsowanie pliku XML
        tree = ET.parse(file_path)
        root = tree.getroot()

        # Szukanie konkretnego bloku i tagu przy użyciu XPath
        # .//oznacza szukanie na dowolnej głębokości, co jest bezpieczniejsze,
        # jeśli struktura pliku .mqres jest bardziej zagnieżdżona
        resource_node = root.find(".//TemplateTMResourceInfo/ResourceName")

        # Sprawdzenie, czy znaleziono węzeł i czy ma on tekst
        if resource_node is not None and resource_node.text:
            return resource_node.text
        else:
            return "-"
        
    except ET.ParseError:
        # Obsługa przypadku, gdy plik nie jest poprawnym XMLem
        return "Błąd pliku. Invalid file"
    except Exception as e:
        # Ogólna obsługa innych błędów (np. problem z uprawinieniami)
        print(f"Błąd przy przetwarzaniu pliku {file_path}: {e}")


def process_directory():
    
    input_path = input_path.strip()

    print(f"---START---")
    print(f"Szukam plików w folderze: {input_path}")

    if not os.path.isdir(input_path):
        print("Podana ścieżka nie istnieje lub nie jest folderem. Sprawdź zmienną input_path w piątej linii")
        return
    
    # Utworzenie ścieżki do folderu output
    output_dir = os.path.join(input_path, "output")

    # Utworzenie folderu output, jeśli nie istnieje
    # (exist_ok=True ignoruje błąd, jeśli folder już jest)
    os.makedirs(output_dir, exist_ok=True)

    # Ścieżka do pliku wynikowego CSV
    csv_file_path = os.path.join(output_dir, "mqres_data.csv")

    print("Rozpoczynam przetwarzanie plików...")

    # Otwarcie pliku CSV do zapisu
    # newline='' jest wymagane przez moduł csv,
    # encoding='utf-8' obsługuje polskie znaki
    with open(csv_file_path, mode='w', newline='', encoding='utf-8') as csvfile:
        csv_writer = csv.writer(csvfile, delimiter=";")

        # Zapisanie nagłówków
        csv_writer.writerow(['Nazwa szablonu', 'TM'])
        
        # Iteracja przez pliki w folderze
        files_processed_count = 0
        try:
            files = os.listdir(input_path)
        except Exception as e:
            print(f"Nie mogę otworzyć folderu: {e}")
            return
        
        for filename in files:
            if filename.endswith(".mqres"):
                full_path = os.path.join(input_path, filename)

                # Pobieranie informacji z XML
                resource_name = get_resource_name(full_path)

                # Zapisanie wiersza do CSV
                csv_writer.writerow([filename, resource_name])
                files_processed_count += 1
    
    print(f"Zakończono. Liczba przetworzonych plików: {files_processed_count}.")
    print(f"Plik z wynikiem znajduje się tutaj: {csv_file_path}.")

if __name__ == "__main__":
    process_directory