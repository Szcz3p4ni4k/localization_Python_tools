import os
import csv
import xml.etree.ElementTree as ET

def get_clean_text_length(segment_element):
    """
    Calculates the length of text within a segment, ignoring tags.
    Oblicza długość tekstu wewnątrz segmentu, ignorując tagi (np. <bpt>, <ept>).
    """
    if segment_element is None:
        return 0
    # itertext() wyciąga tekst ze wszystkich pod-elementów, pomijając same znaczniki
    text_content = "".join(segment_element.itertext())
    return len(text_content)

def analyze_tmx_file(file_path):
    """
    Analyzes a single TMX file and returns statistics per translator.
    Analizuje pojedynczy plik TMX i zwraca statystyki dla każdego tłumacza.
    """
    translators_stats = {} # Słownik: ID Tłumacza -> Statystyki

    try:
        # Próba otwarcia pliku (najpierw domyślnie, potem UTF-16 w razie błędu)
        try:
            tree = ET.parse(file_path)
        except:
            parser = ET.XMLParser(encoding="utf-16")
            tree = ET.parse(file_path, parser=parser)
            
        root = tree.getroot()

        # 1. Determine Target Language
        # 1. Ustalenie języka docelowego
        target_lang = None
        
        # [cite_start]Szukanie w <prop type="targetlang"> [cite: 7]
        for prop in root.iter('prop'):
            if prop.get('type') == 'targetlang':
                target_lang = prop.text
                break
        
        # Iteration through translation units <tu>
        # Iteracja przez jednostki tłumaczeniowe
        for tu in root.iter('tu'):
            creation_date = tu.get('creationdate')
            creation_id = tu.get('creationid')
            change_date = tu.get('changedate')
            change_id = tu.get('changeid')

            # Find target segment text
            # Znalezienie tekstu segmentu docelowego
            target_text_len = 0
            
            for tuv in tu.findall('tuv'):
                # Pobranie atrybutu xml:lang (z uwzględnieniem namespace)
                xml_lang = tuv.get('{http://www.w3.org/XML/1998/namespace}lang')
                if not xml_lang:
                    xml_lang = tuv.get('lang') # Fallback

                # Sprawdzenie czy to język docelowy
                if target_lang and xml_lang and target_lang.lower() in xml_lang.lower():
                    seg = tuv.find('seg')
                    # [cite_start]Liczymy znaki czystego tekstu (bez tagów formatowania) [cite: 7]
                    target_text_len = get_clean_text_length(seg)
                    break 

            # Helper function to initialize translator data
            # Funkcja pomocnicza do inicjalizacji danych tłumacza
            def init_translator(user_id):
                if user_id not in translators_stats:
                    translators_stats[user_id] = {
                        'creation_id': user_id,
                        'last_creation_date': "-",
                        'last_change_date': "-",
                        'created_segs_count': 0,
                        'changed_segs_count': 0,
                        'created_chars_count': 0,
                        'changed_chars_count': 0
                    }

            # --- LOGIC: CREATION ---
            # [cite_start]Zawsze pobieramy dane o tworzeniu [cite: 3]
            if creation_id:
                init_translator(creation_id)
                translators_stats[creation_id]['created_segs_count'] += 1
                translators_stats[creation_id]['created_chars_count'] += target_text_len
                
                # Update last creation date
                current_c_date = translators_stats[creation_id]['last_creation_date']
                if creation_date:
                    if current_c_date == "-" or creation_date > current_c_date:
                        translators_stats[creation_id]['last_creation_date'] = creation_date

            # --- LOGIC: CHANGE ---
            # [cite_start]Sprawdzamy warunek wykluczenia: changedate = creationdate AND creationid = changeid [cite: 5, 6, 8]
            is_creation_only = (creation_date == change_date) and (creation_id == change_id)

            if change_id and not is_creation_only:
                init_translator(change_id)
                translators_stats[change_id]['changed_segs_count'] += 1
                translators_stats[change_id]['changed_chars_count'] += target_text_len

                # Update last change date
                current_m_date = translators_stats[change_id]['last_change_date']
                if change_date:
                    if current_m_date == "-" or change_date > current_m_date:
                        translators_stats[change_id]['last_change_date'] = change_date

    except Exception as e:
        print(f"Błąd podczas przetwarzania pliku {file_path}: {e}")
        return None

    return translators_stats

def main():
    # Setup paths
    # Ustawienie ścieżek
    current_dir = os.getcwd()
    report_dir = os.path.join(current_dir, "Raport")

    if not os.path.exists(report_dir):
        os.makedirs(report_dir)

    output_csv_path = os.path.join(report_dir, "analiza_tm.csv")

    print("Rozpoczynam analizę plików TMX...")
    
    all_rows = []

    # Iterate over files in directory
    # Iteracja po plikach w katalogu
    for filename in os.listdir(current_dir):
        if filename.lower().endswith('.tmx'):
            full_path = os.path.join(current_dir, filename)
            print(f"Analizuję: {filename}")
            
            file_results = analyze_tmx_file(full_path)
            
            if file_results:
                # Convert dictionary to list of rows for CSV
                # Konwersja słownika na listę wierszy do CSV
                for user_id, stats in file_results.items():
                    row = {
                        'Filename': filename,
                        'Translator ID': user_id,
                        'Last Segment Date': stats['last_creation_date'],
                        'Last Change Date': stats['last_change_date'],
                        'Created Segments': stats['created_segs_count'],
                        'Changed Segments': stats['changed_segs_count'],
                        'Created Chars': stats['created_chars_count'],
                        'Changed Chars': stats['changed_chars_count']
                    }
                    all_rows.append(row)

    # Define CSV Columns
    # Definicja kolumn CSV
    csv_headers = [
        'Filename', 'Translator ID', 'Last Segment Date', 
        'Last Change Date', 'Created Segments', 
        'Changed Segments', 'Created Chars', 
        'Changed Chars'
    ]

    # Write to CSV
    # Zapis do CSV
    try:
        # 'utf-8-sig' pozwala Excelowi poprawnie otworzyć plik z polskimi znakami
        with open(output_csv_path, mode='w', newline='', encoding='utf-8-sig') as csvfile:
            # Używamy standardowego separatora ',' (przecinek)
            writer = csv.DictWriter(csvfile, fieldnames=csv_headers, delimiter=',')
            
            writer.writeheader()
            for row in all_rows:
                writer.writerow(row)
        
        print(f"\nSukces! Raport został zapisany w: {output_csv_path}")

    except IOError as e:
        print(f"Błąd zapisu pliku CSV: {e}")

if __name__ == "__main__":
    main()
