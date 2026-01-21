import os
import csv
import xml.etree.ElementTree as ET
import re
import gc

# --- FUNKCJE POMOCNICZE ---

def format_date(date_str):
    """
    Formatuje datę z surowego formatu TMX na czytelny format YYYY.MM.DD.
    """
    # Sprawdzamy, czy data w ogóle istnieje i czy jest wystarczająco długa
    if not date_str or len(date_str) < 8:
        return "-"
    
    # Data w TMX to np. "20250714T160952Z"
    # pobieramy rok, miesiąc i dzień
    year = date_str[0:4]   # Znaki od indeksu 0 do 3 (czyli 4 pierwsze)
    month = date_str[4:6]  # Znaki od 4 do 5
    day = date_str[6:8]    # Znaki od 6 do 7
    
    
    return f"{year}.{month}.{day}"

def get_clean_text_length(segment_element):
#Oblicza długość tekstu, agresywnie usuwając wszelkie tagi XML/HTML
    
    if segment_element is None:
        return 0
    
    # 1. Metoda .itertext() wyciąga tekst ze wszystkich zagnieżdżonych elementów
    #    Dzięki temu, jeśli tekst jest pocięty przez tagi <bpt>, <ept>, dostaniemy całość
    raw_text = "".join(segment_element.itertext())
    
    if not raw_text:
        return 0

    # 2. Używamy Regex (re.sub), aby usunąć pozostałości tagów
    #    r'<[^>]+> - znajdź znak '<', potem cokolwiek co NIE jest '>', i na końcu '>'
    #    Zamieniamy to na pusty ciąg znaków ('')
    clean_text = re.sub(r'<[^>]+>', '', raw_text)
    
    # Zwracamy długość wyczyszczonego tekstu (liczba znaków)
    return len(clean_text)

def analyze_tmx_file_streaming(file_path):   
#Główna funkcja analizująca. Używa trybu strumieniowego (iterparse),
 #co pozwala przetwarzać gigantyczne pliki bez ładowania ich w całości do RAM.
#Zwraca: (słownik ze statystykami, całkowitą liczbę segmentów).
    
    translators_stats = {} # Słownik, gdzie będziemy zbierać dane dla każdego ID tłumacza
    target_lang = None     # Zmienna na kod języka docelowego (np. "en-GB")
    total_segments_count = 0 # Licznik wszystkich segmentów <tu> w pliku

    try:
        # events=('end',) oznacza: "daj mi znać, gdy parser dojdzie do końca danego tagu".
        context = ET.iterparse(file_path, events=('end',))
        
        # Pętla idąca przez plik element po elemencie
        for event, elem in context:
            
            # Wyciągamy samą nazwę tagu, usuwając namespace (np. {xml...}tu -> tu)
            tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag

            # Szukamy informacji o języku w nagłówku (tag <prop type="targetlang">)
            if tag_name == 'prop' and elem.get('type') == 'targetlang':
                target_lang = elem.text

            # Jeśli trafiliśmy na tag <tu>, zaczynamy analizę segmentu
            if tag_name == 'tu':
                total_segments_count += 1 # Dodajemy 1 do ogólnej liczby segmentów
                
                # Pobieramy atrybuty z nagłówka segmentu
                creation_date = elem.get('creationdate')
                creation_id = elem.get('creationid')
                change_date = elem.get('changedate')
                change_id = elem.get('changeid')

                # --- Szukanie tekstu targetu ---
                target_text_len = 0
                
                # Przeszukujemy warianty tłumaczenia (<tuv>) wewnątrz tego <tu>
                for tuv in elem.findall('tuv'): 
                    # Pobieramy język danego wariantu (uwzględniając namespace XML)
                    xml_lang = tuv.get('{http://www.w3.org/XML/1998/namespace}lang')
                    if not xml_lang:
                        xml_lang = tuv.get('lang') # Zabezpieczenie, gdyby nie było namespace

                    # Sprawdzamy, czy język tuv pasuje do języka docelowego pliku
                    if target_lang and xml_lang and target_lang.lower() in xml_lang.lower():
                        # Szukamy treści w segmencie (<seg>)
                        seg = tuv.find('seg')
                        
                        if seg is None:
                            for child in tuv:
                                if child.tag.endswith('seg'):
                                    seg = child
                                    break
                        
                        # Obliczamy długość czystego tekstu w targecie
                        target_text_len = get_clean_text_length(seg)
                        break # Przerywamy pętlę po tuv, bo znaleźliśmy target

                # --- LOGIKA ZLICZANIA STATYSTYK ---
                
                # Funkcja wewnętrzna, żeby nie powtarzać kodu inicjalizacji słownika
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

                # Jeśli jest creation_id, zawsze to zliczamy.
                if creation_id:
                    init_translator(creation_id)
                    translators_stats[creation_id]['created_segs_count'] += 1
                    translators_stats[creation_id]['created_chars_count'] += target_text_len
                    
                    # Aktualizacja daty (bierzemy "najnowszą" datę jaką znaleźliśmy dla tego usera)
                    current_c_date = translators_stats[creation_id]['last_creation_date']
                    if creation_date:
                        if current_c_date == "-" or creation_date > current_c_date:
                            translators_stats[creation_id]['last_creation_date'] = creation_date

                # Tutaj musimy sprawdzić, czy zmiana nie jest fałszywa (czyli czy to nie jest ten sam moment co utworzenie)
                # Bierzemy tylko pierwsze 8 znaków (YYYYMMDD), ignorując godziny/minuty
                c_date_day = creation_date[:8] if creation_date else None
                m_date_day = change_date[:8] if change_date else None
                
                # Warunek wykluczenia: To samo ID oraz ten sam DZIEŃ
                is_creation_only = (c_date_day == m_date_day) and (creation_id == change_id)

                # Zliczamy zmianę tylko, jeśli mamy change_id i nie jest to wykluczony przypadek
                if change_id and not is_creation_only:
                    init_translator(change_id)
                    translators_stats[change_id]['changed_segs_count'] += 1
                    translators_stats[change_id]['changed_chars_count'] += target_text_len

                    current_m_date = translators_stats[change_id]['last_change_date']
                    if change_date:
                        if current_m_date == "-" or change_date > current_m_date:
                            translators_stats[change_id]['last_change_date'] = change_date

                # --- CZYSZCZENIE PAMIĘCI ---
                # Po przetworzeniu tagu <tu>, usuwamy go z pamięci RAM.
                elem.clear()
            
        # Gdy skończymy plik, zwracamy (statystyki, licznik)
        return translators_stats, total_segments_count

    except Exception as e:
        # W razie błędu zwracamy komunikat o błędzie jako string
        return f"ERROR: {str(e)}"
    finally:
        # Na koniec, niezależnie od wyniku, wymuszamy sprzątanie pamięci
        gc.collect()


# --- GŁÓWNA CZĘŚĆ SKRYPTU ---

# Pobieramy ścieżkę do folderu, w którym znajduje się plik skryptu (.py)
input_path = os.path.dirname(os.path.abspath(__file__))

print("========================================")
print(f"Folder roboczy: {input_path}")
print("========================================")

#Szukanie plików
try:
    # Pobieramy listę wszystkich plików w folderze
    all_files = os.listdir(input_path)
    # Filtrujemy listę, zostawiając tylko te z końcówką .tmx
    tmx_files = [f for f in all_files if f.lower().endswith('.tmx')]
    total_files = len(tmx_files)
    print(f"Znaleziono pliki .tmx: {total_files}")
except Exception as e:
    print(f"Błąd krytyczny przy czytaniu folderu: {e}")
    tmx_files = []

#Przetwarzanie
if tmx_files:
    # Tworzymy folder na wyniki
    output_dir = os.path.join(input_path, "Raport")
    os.makedirs(output_dir, exist_ok=True)
    csv_path = os.path.join(output_dir, "analiza_tm_wyniki.csv")
    
    print(f"Tworzę plik csv: {csv_path}")
    
    try:
        # Otwieramy plik CSV do zapisu.
        # 'utf-8-sig'
        # newline='' zapobiega pustym liniom w Windows.
        with open(csv_path, mode='w', newline='', encoding='utf-8-sig') as f_out:
            writer = csv.writer(f_out, delimiter=';')
            
            # Definiujemy i zapisujemy nagłówki kolumn
            headers = [
                'Nazwa pliku', 
                'Calkowita ilosc segmentow',
                'ID Tlumacza', 
                'Data ost. segmentu', 
                'Data ost. zmiany', 
                'Ilosc stworzonych segmentow', 
                'Ilosc zmienionych segmentow', 
                'Ilosc stworzonych znakow', 
                'Ilosc zmienionych znakow', 
                'Status'
            ]
            writer.writerow(headers)
            
            count = 0
            
            # Pętla po każdym znalezionym pliku TMX
            for filename in tmx_files:
                count += 1
                full_path = os.path.join(input_path, filename)
                
                # Wywołujemy funkcję analizującą dla pojedynczego pliku
                result = analyze_tmx_file_streaming(full_path)
                
                status_msg = "OK"

                # Sprawdzamy, czy funkcja zwróciła błąd (string) czy dane
                if isinstance(result, str) and result.startswith("ERROR"):
                    status_msg = result
                    # Zapisujemy wiersz z informacją o błędzie
                    writer.writerow([filename, "-", "-", "-", "-", "-", "-", "-", "-", status_msg])
                
                else:
                    # Rozpakowujemy wynik na dwie zmienne
                    stats_dict, total_count = result
                    
                    if stats_dict:
                        # Iterujemy po każdym tłumaczu znalezionym w pliku i zapisujemy wiersz
                        for user_id, stats in stats_dict.items():
                            writer.writerow([
                                filename,
                                total_count, # Wspólna wartość dla wszystkich tłumaczy w tym pliku
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
                        # Przypadek pustego pliku lub braku ID
                        writer.writerow([filename, total_count, "BRAK DANYCH", "-", "-", "-", "-", "-", "-", "BRAK ID"])

                # Wypisujemy postęp w konsoli
                print(f"[{count}/{total_files}] Analiza: {filename}")

            print("========================================")
            print(f"SUKCES! Przetworzono {count} plików.")
            
    except Exception as e:
        print(f"BŁĄD zapisu pliku CSV (zamknij Excela!): {e}")

else:
    print("Nie mam czego przetwarzać. Brak plików .tmx w folderze.")

# Zatrzymanie okna konsoli po zakończeniu
print("========================================")
input("Naciśnij ENTER, aby zakończyć")
