import os
import csv
import xml.etree.ElementTree as ET
import re

# --- FUNKCJE POMOCNICZE (HELPER FUNCTIONS) ---

def format_date(date_str):
    """
    Formats TMX date string (YYYYMMDDThhmmssZ) to YYYY.MM.DD.
    Formatuje datę z formatu TMX na czytelny format 2015.08.25.
    """
    if not date_str or len(date_str) < 8:
        return "-"
    
    # Wyciągamy rok, miesiąc i dzień za pomocą indeksów (slicing)
    # TMX date format: 20150825T...
    year = date_str[0:4]
    month = date_str[4:6]
    day = date_str[6:8]
    
    return f"{year}.{month}.{day}"

def get_clean_text_length(segment_element):
    """
    Calculates the length of text within a segment, aggressively removing tags.
    Oblicza długość tekstu, usuwając tagi oraz "ukryte" tagi wewnątrz <it>.
    """
    if segment_element is None:
        return 0
    
    # 1. Wyciągamy całą zawartość tekstową (również to co jest wewnątrz tagów bpt, it, etc.)
    # ElementTree automatycznie zamienia &lt; na <, więc dostajemy np: "<rpr id="3">"
    raw_text = "".join(segment_element.itertext())
    
    if not raw_text:
        return 0

    # 2. Używamy Regex, aby usunąć wszystko co wygląda jak tag HTML/XML (<...>)
    # Wzorzec: Znajdź znak <, potem cokolwiek co NIE jest >, potem znak >
    clean_text = re.sub(r'<[^>]+>', '', raw_text)
    
    # 3. Opcjonalnie: usuwamy nadmiarowe spacje, jeśli to potrzebne (tutaj liczymy długość oryginału bez tagów)
    # Zgodnie z instrukcją "tekst razem ze spacjami", więc nie robimy .strip() na całości,
    # chyba że tagi zostawiły dziury. Regex po prostu wycina tagi, zostawiając resztę nienaruszoną.
    
    return len(clean_text)

def analyze_tmx_file(file_path):
    """
    Analyzes a single TMX file and returns statistics per translator.
    Analizuje pojedynczy plik TMX i zwraca statystyki.
    """
    translators_stats = {} 

    try:
        try:
            tree = ET.parse(file_path)
        except:
            parser = ET.XMLParser(encoding="utf-16")
            tree = ET.parse(file_path, parser=parser)
            
        root = tree.getroot()

        # 1. Ustalenie języka docelowego (Target Language)
        target_lang = None
        for prop in root.iter('prop'):
            if prop.get('type') == 'targetlang':
                target_lang = prop.text
                break
        
        # Iteracja przez jednostki tłumaczeniowe (TU)
        for tu in root.iter('tu'):
            creation_date = tu.get('creationdate')
            creation_id = tu.get('creationid')
            change_date = tu.get('changedate')
            change_id = tu.get('changeid')

            # Znalezienie tekstu segmentu docelowego
            target_text_len = 0
            
            for tuv in tu.findall('tuv'):
                xml_lang = tuv.get('{http://www.w3.org/XML/1998/namespace}lang')
                if not xml_lang:
                    xml_lang = tuv.get('lang')

                if target_lang and xml_lang and target_lang.lower() in xml_lang.lower():
                    seg = tuv.find('seg')
                    target_text_len = get_clean_text_length(seg)
                    break 

            # Inicjalizacja danych tłumacza
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

            # --- LOGIKA: TWORZENIE (CREATION) ---
            if creation_id:
                init_translator(creation_id)
                translators_stats[creation_id]['created_segs_count'] += 1
                translators_stats[creation_id]['created_chars_count'] += target_text_len
                
                # Porównujemy daty w formacie oryginalnym (ISO), bo tak jest poprawnie matematycznie
                current_c_date = translators_stats[creation_id]['last_creation_date']
                if creation_date:
                    if current_c_date == "-" or creation_date > current_c_date:
                        translators_stats[creation_id]['last_creation_date'] = creation_date

            # --- LOGIKA: ZMIANA (CHANGE) ---
            is_creation_only = (creation_date == change_date) and (creation_id == change_id)

            if change_id and not is_creation_only:
                init_translator(change_id)
                translators_stats[change_id]['changed_segs_count'] += 1
                translators_stats[change_id]['changed_chars_count'] += target_text_len

                current_m_date = translators_stats[change_id]['last_change_date']
                if change_date:
                    if current_m_date == "-" or change_date > current_m_date:
                        translators_stats[change_id]['last_change_date'] = change_date

        return translators_stats

    except Exception as e:
        return f"ERROR: {str(e)}"


# --- GŁÓWNA CZĘŚĆ SKRYPTU ---

# Pobiera ścieżkę do folderu, w którym jest ten skrypt
input_path = os.path.dirname(os.path.abspath(__file__))

print("========================================")
print(f"Folder roboczy: {input_path}")
print("========================================")

# Krok 1: Szukanie plików
try:
    all_files = os.listdir(input_path)
    tmx_files = [f for f in all_files if f.lower().endswith('.tmx')]
    total_files = len(tmx_files)
    print(f"Znaleziono pliki .tmx: {total_files}")
except Exception as e:
    print(f"Błąd krytyczny przy czytaniu folderu: {e}")
    tmx_files = []

# Krok 2: Przetwarzanie
if tmx_files:
    output_dir = os.path.join(input_path, "Raport")
    os.makedirs(output_dir, exist_ok=True)
    csv_path = os.path.join(output_dir, "analiza_tm_wyniki.csv")
    
    print(f"Tworzę plik csv: {csv_path}")
    
    try:
        # Kodowanie utf-8-sig dla polskich znaków w Excelu
        with open(csv_path, mode='w', newline='', encoding='utf-8-sig') as f_out:
            writer = csv.writer(f_out, delimiter=';')
            
            # NAGŁÓWKI KOLUMN
            headers = [
                'Nazwa pliku', 'ID Tlumacza', 'Data ost. segmentu', 
                'Data ost. zmiany', 'Ilosc stworzonych segmentow', 
                'Ilosc zmienionych segmentow', 'Ilosc stworzonych znakow', 
                'Ilosc zmienionych znakow', 'Status'
            ]
            writer.writerow(headers)
            
            count = 0
            
            for filename in tmx_files:
                count += 1
                full_path = os.path.join(input_path, filename)
                
                result = analyze_tmx_file(full_path)
                status_msg = "OK"

                if isinstance(result, str) and result.startswith("ERROR"):
                    status_msg = result
                    writer.writerow([filename, "-", "-", "-", "-", "-", "-", "-", status_msg])
                
                elif result:
                    for user_id, stats in result.items():
                        # Tutaj używamy funkcji format_date przy zapisie do CSV
                        writer.writerow([
                            filename,
                            stats['creation_id'],
                            format_date(stats['last_creation_date']), # Formatowanie daty 1
                            format_date(stats['last_change_date']),   # Formatowanie daty 2
                            stats['created_segs_count'],
                            stats['changed_segs_count'],
                            stats['created_chars_count'],
                            stats['changed_chars_count'],
                            status_msg
                        ])
                else:
                    writer.writerow([filename, "BRAK DANYCH", "-", "-", "-", "-", "-", "-", "Pusty plik/Brak TU"])

                print(f"[{count}/{total_files}] Analiza: {filename}")

            print("========================================")
            print(f"SUKCES! Przetworzono {count} plików.")
            
    except Exception as e:
        print(f"BŁĄD zapisu pliku CSV (zamknij Excela!): {e}")

else:
    print("Nie mam czego przetwarzać. Brak plików .tmx w folderze.")

print("========================================")
input("Naciśnij ENTER, aby zakończyć")
