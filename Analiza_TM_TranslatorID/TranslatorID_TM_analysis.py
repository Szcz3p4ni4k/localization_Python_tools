import os
import csv
import xml.etree.ElementTree as ET
import re

# Funkcja czyszcząca tekst z tagów XML/HTML (np. <bpt>, <ept>)
def usun_tagi(tekst):
    if not tekst:
        return ""
    # Wyrażenie regularne: znajdź wszystko co zaczyna się od < i kończy na >
    czysty_tekst = re.sub(r'<[^>]+>', '', tekst)
    return czysty_tekst

def analizuj_plik_tmx(sciezka_pliku):
    # Słownik do przechowywania danych tłumaczy dla tego konkretnego pliku
    # Kluczem będzie ID tłumacza, wartością słownik ze statystykami
    dane_tlumaczy = {}

    try:
        # Parsowanie pliku XML. TMX często są w UTF-16, ale na wypadek UTF-8 używamy trybów
        try:
            tree = ET.parse(sciezka_pliku)
        except:
            # Jeśli domyślne parsowanie zawiedzie, próbujemy wymusić parser XML
            parser = ET.XMLParser(encoding="utf-16")
            tree = ET.parse(sciezka_pliku, parser=parser)
            
        root = tree.getroot()

        # 1. Ustalenie języka docelowego (Target Language) dla całego pliku
        # Szukamy w headerze lub w pierwszym prop type="targetlang"
        jezyk_target = None
        
        # Próba znalezienia we właściwościach (zgodnie z instrukcją)
        for prop in root.iter('prop'):
            if prop.get('type') == 'targetlang':
                jezyk_target = prop.text
                break
        
        # Jeśli nie znaleziono w prop, szukamy w nagłówku (standard TMX)
        if not jezyk_target:
            header = root.find('header')
            if header is not None:
                # Często header ma atrybut 'srclang', więc target musimy wywnioskować
                # W tym prostym skrypcie założymy, że jeśli nie ma prop, spróbujemy znaleźć
                # język w segmentach później, ale dla bezpieczeństwa logujemy informację.
                pass

        # Iteracja przez wszystkie jednostki tłumaczeniowe <tu>
        # namespace w XML może być kłopotliwy, więc używamy iter() który szuka głęboko
        for tu in root.iter('tu'):
            # Pobranie atrybutów creation i change
            creation_date = tu.get('creationdate')
            creation_id = tu.get('creationid')
            change_date = tu.get('changedate')
            change_id = tu.get('changeid')

            # --- KROK 1: Znalezienie tekstu targetu ---
            tekst_target = ""
            # Szukamy wszystkich wariantów tłumaczenia <tuv>
            for tuv in tu.findall('tuv'):
                # Pobieramy atrybut xml:lang. Uwaga: ElementTree dodaje namespace w klamrach
                xml_lang = tuv.get('{http://www.w3.org/XML/1998/namespace}lang')
                if not xml_lang:
                    # Czasami atrybut jest bez namespace (zależy od parsera/pliku)
                    xml_lang = tuv.get('lang')

                # Sprawdzamy czy to język docelowy. 
                # Jeśli mamy ustalony jezyk_target, sprawdzamy zgodność.
                # Jeśli nie mamy, zakładamy (ryzykownie), że drugi tuv to target, 
                # ale bezpieczniej jest wymagać prop targetlang.
                if jezyk_target and xml_lang and jezyk_target.lower() in xml_lang.lower():
                    seg = tuv.find('seg')
                    if seg is not None and seg.text:
                        # Pobieramy tekst (może zawierać tagi w środku, więc itertext łączy wszystko)
                        # Ale musimy uważać na tagi <bpt>. Użyjemy metody itertext() lub parsowania stringa.
                        # Tutaj prostsze podejście: pobierzmy surowy XML segmentu i wyczyśćmy regexem,
                        # aby zachować spacje ale usunąć tagi.
                        raw_content = "".join(seg.itertext()) # To pobiera sam tekst, pomijając tagi <..>
                        tekst_target = raw_content
                    break # Znaleźliśmy target, przerywamy pętlę tuv
            
            # Obliczenie długości czystego tekstu
            dlugosc_tekstu = len(tekst_target)

            # Funkcja pomocnicza do inicjalizacji danych tłumacza w słowniku
            def inicjuj_tlumacza(id_tlumacza):
                if id_tlumacza not in dane_tlumaczy:
                    dane_tlumaczy[id_tlumacza] = {
                        'creation_id': id_tlumacza, # ID Tłumacza
                        'last_creation_date': "-",  # Data ost. segmentu
                        'last_change_date': "-",    # Data ost. zmiany
                        'created_segs': 0,          # ilość stworzonych segmentów
                        'changed_segs': 0,          # ilość zmienionych segmentów
                        'created_chars': 0,         # ilość stworzonych znaków
                        'changed_chars': 0          # ilość zmienionych znaków
                    }

            # --- KROK 2: Logika CREATION (Zawsze liczona) ---
            if creation_id:
                inicjuj_tlumacza(creation_id)
                dane_tlumaczy[creation_id]['created_segs'] += 1
                dane_tlumaczy[creation_id]['created_chars'] += dlugosc_tekstu
                
                # Aktualizacja daty (bierzemy późniejszą)
                obecna_data = dane_tlumaczy[creation_id]['last_creation_date']
                if creation_date:
                    if obecna_data == "-" or creation_date > obecna_data:
                        dane_tlumaczy[creation_id]['last_creation_date'] = creation_date

            # --- KROK 3: Logika CHANGE (Warunkowa) ---
            # Warunek wykluczenia z pliku:
            # Jeżeli changedate = creationdate i creationid = changeid -> NIE bierzemy pod uwagę
            jest_to_tylko_stworzenie = (creation_date == change_date) and (creation_id == change_id)

            if change_id and not jest_to_tylko_stworzenie:
                inicjuj_tlumacza(change_id)
                dane_tlumaczy[change_id]['changed_segs'] += 1
                dane_tlumaczy[change_id]['changed_chars'] += dlugosc_tekstu

                # Aktualizacja daty zmiany
                obecna_data_zmiany = dane_tlumaczy[change_id]['last_change_date']
                if change_date:
                    if obecna_data_zmiany == "-" or change_date > obecna_data_zmiany:
                        dane_tlumaczy[change_id]['last_change_date'] = change_date

    except Exception as e:
        print(f"Błąd podczas przetwarzania pliku {sciezka_pliku}: {e}")
        return None

    return dane_tlumaczy

def main():
    # Pobranie ścieżki do folderu, w którym jest skrypt
    sciezka_skryptu = os.getcwd()
    folder_raportu = os.path.join(sciezka_skryptu, "Raport")

    # Tworzenie folderu Raport, jeśli nie istnieje
    if not os.path.exists(folder_raportu):
        os.makedirs(folder_raportu)

    sciezka_wynikowa = os.path.join(folder_raportu, "analiza_tm.csv")

    print("Rozpoczynam analizę plików TMX...")
    
    # Lista do zbierania wszystkich wierszy do CSV
    wszystkie_dane = []

    # Szukanie plików .tmx w folderze
    for plik in os.listdir(sciezka_skryptu):
        if plik.lower().endswith('.tmx'):
            pelna_sciezka = os.path.join(sciezka_skryptu, plik)
            print(f"Analizuję: {plik}")
            
            # Analiza pojedynczego pliku
            wyniki_pliku = analizuj_plik_tmx(pelna_sciezka)
            
            if wyniki_pliku:
                # Przekształcenie wyników słownika na listę wierszy do CSV
                for id_tlumacza, statystyki in wyniki_pliku.items():
                    wiersz = {
                        'nazwa_pliku': plik,
                        'id_tlumacza': id_tlumacza,
                        'data_ost_seg': statystyki['last_creation_date'],
                        'data_ost_zmiany': statystyki['last_change_date'],
                        'ilosc_stworzonych_seg': statystyki['created_segs'],
                        'ilosc_zmienionych_seg': statystyki['changed_segs'],
                        'ilosc_stworzonych_znak': statystyki['created_chars'],
                        'ilosc_zmienionych_znak': statystyki['changed_chars']
                    }
                    wszystkie_dane.append(wiersz)

    # Zapis do CSV
    naglowki = [
        'nazwa TMa', 'ID Tłumacza', 'data ostatniego segmentu', 
        'data ostatniej zmiany', 'ilość stworzonych segmentów', 
        'ilość zmienionych segmentów', 'ilość stworzonych znaków', 
        'ilość zmienionych znaków'
    ]

    try:
        with open(sciezka_wynikowa, mode='w', newline='', encoding='utf-8') as csvfile:
            # Używamy separatora '|' zgodnie z instrukcją
            writer = csv.DictWriter(csvfile, fieldnames=[
                'nazwa_pliku', 'id_tlumacza', 'data_ost_seg', 'data_ost_zmiany',
                'ilosc_stworzonych_seg', 'ilosc_zmienionych_seg',
                'ilosc_stworzonych_znak', 'ilosc_zmienionych_znak'
            ], delimiter='|')

            # Pisanie nagłówków ręcznie, aby dopasować nazwy kolumn z instrukcji do kluczy
            writer.writer.writerow(naglowki)

            # Pisanie wierszy
            for dane in wszystkie_dane:
                writer.writerow(dane)
        
        print(f"\nSukces! Raport został zapisany w: {sciezka_wynikowa}")

    except IOError as e:
        print(f"Błąd zapisu pliku CSV: {e}")

if __name__ == "__main__":
    main()