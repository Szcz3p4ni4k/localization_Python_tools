import os
import csv
import xml.etree.ElementTree as ET
import re
import gc # Garbage Collector do zwalniania pamięci

# --- FUNKCJE POMOCNICZE ---

def format_date(date_str):
    """
    Formatuje datę z formatu TMX na czytelny format YYYY.MM.DD.
    """
    if not date_str or len(date_str) < 8:
        return "-"
    year = date_str[0:4]
    month = date_str[4:6]
    day = date_str[6:8]
    return f"{year}.{month}.{day}"

def get_clean_text_length(segment_element):
    """
    Oblicza długość tekstu, usuwając tagi XML oraz tagi wewnętrzne.
    """
    if segment_element is None:
        return 0
    
    # Wyciągamy tekst (itertext łączy tekst z wnętrza tagów)
    raw_text = "".join(segment_element.itertext())
    
    if not raw_text:
        return 0

    # Usuwamy wszystko co wygląda jak tag HTML/XML
    clean_text = re.sub(r'<[^>]+>', '', raw_text)
    return len(clean_text)

def analyze_tmx_file_streaming(file_path):
    """
    Analizuje plik TMX w trybie strumieniowym (iterparse).
    Zużywa minimalną ilość pamięci RAM nawet przy ogromnych plikach.
    """
    translators_stats = {} 
    target_lang = None

    try:
        # Używamy iterparse zamiast parse - czyta plik zdarzeniami
        # events=('end',) oznacza, że reagujemy, gdy parser "zamyka" dany tag (przeczytał go całego)
        context = ET.iterparse(file_path, events=('end',))
        
        # Iterujemy po elementach w miarę czytania pliku
        for event, elem in context:
            
            # Pobieranie tagu bez namespace (czasami TMX ma {namespace}tu)
            tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag

            # 1. Szukanie języka docelowego w nagłówku (zazwyczaj jest na początku pliku)
            if tag_name == 'prop' and elem.get('type') == 'targetlang':
                target_lang = elem.text

            # 2. Przetwarzanie jednostki tłumaczeniowej <tu>
            if tag_name == 'tu':
                creation_date = elem.get('creationdate')
                creation_id = elem.get('creationid')
                change_date = elem.get('changedate')
                change_id = elem.get('changeid')

                # Znalezienie tekstu segmentu docelowego wewnątrz obecnego <tu>
                target_text_len = 0
                
                for tuv in elem.findall('tuv'): # lub elem.findall('{...}tuv')
                    # TUV też może mieć namespace, więc sprawdzamy ostrożnie
                    xml_lang = tuv.get('{http://www.w3.org/XML/1998/namespace}lang')
                    if not xml_lang:
                        xml_lang = tuv.get('lang')

                    if target_lang and xml_lang and target_lang.lower() in xml_lang.lower():
                        seg = tuv.find('seg') # lub z namespace
                        if seg is None:
                            # Próba znalezienia z dowolnym namespace
                            for child in tuv:
                                if child.tag.endswith('seg'):
                                    seg = child
                                    break
                        
                        target_text_len = get_clean_text_length(seg)
                        break 

                # --- LOGIKA ZLICZANIA (identyczna jak wcześniej) ---
                
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

                # LOGIKA: TWORZENIE
                if creation_id:
                    init_translator(creation_id)
                    translators_stats[creation_id]['created_segs_count'] += 1
                    translators_stats[creation_id]['created_chars_count'] += target_text_len
                    
                    current_c_date = translators_stats[creation_id]['last_creation_date']
                    if creation_date:
                        if current_c_date == "-" or creation_date > current_c_date:
                            translators_stats[creation_id]['last_creation_date'] = creation_date

                # LOGIKA: ZMIANA
                c_date_day = creation_date[:8] if creation_date else None
                m_date_day = change_date[:8] if change_date else None
                is_creation_only = (c_date_day == m_date_day) and (creation_id == change_id)

                if change_id and not is_creation_only:
                    init_translator(change_id)
                    translators_stats[change_id]['changed_segs_count'] += 1
                    translators_stats[change_id]['changed_chars_count'] += target_text_len

                    current_m_date = translators_stats[change_id]['last_change_date']
                    if change_date:
                        if current_m_date == "-" or change_date > current_m_date:
                            translators_stats[change_id]['last_change_date'] = change_date

                # === KLUCZOWY MOMENT DLA WYDAJNOŚCI ===
                # Czyścimy element <tu> z pamięci RAM po jego przetworzeniu.
                # Dzięki temu RAM nie rośnie w nieskończoność.
                elem.clear()
                
                # Czyścimy też referencje do przodków (dla pewności przy ogromnych plikach)
                # (W prostym iterparse 'root' może puchnąć, ale clear() na tu zazwyczaj wystarcza)
            
        return translators_stats

    except Exception as e:
        return f"ERROR: {str(e)}"
    finally:
        # Wymuszenie sprzątania pamięci po pliku
        gc.collect()


# --- GŁÓWNA CZĘŚĆ SKRYPTU ---

input_path = os.path.dirname(os.path.abspath(__file__))

print("========================================")
print(f"Folder roboczy: {input_path}")
print(f"Tryb: SUPER WYDAJNY (STREAMING)")
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
        with open(csv_path, mode='w', newline='', encoding='utf-8-sig') as f_out:
            writer = csv.writer(f_out, delimiter=';')
            
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
                
                # Używamy nowej funkcji streamingowej
                result = analyze_tmx_file_streaming(full_path)
                
                status_msg = "OK"

                if isinstance(result, str) and result.startswith("ERROR"):
                    status_msg = result
                    writer.writerow([filename, "-", "-", "-", "-", "-", "-", "-", status_msg])
                
                elif result:
                    for user_id, stats in result.items():
                        writer.writerow([
                            filename,
                            stats['creation_id'],
                            format_date(stats['last_creation_date']),
                            format_date(stats['last_change_date']),
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
