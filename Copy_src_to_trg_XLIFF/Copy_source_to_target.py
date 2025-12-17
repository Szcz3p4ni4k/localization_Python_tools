import os
import copy
import xml.etree.ElementTree as ET

# Konfiguracja
INPUT_EXT = '.xml'
OUTPUT_FOLDER = 'output'

def process_xlf_files():
    # Sprawdzenie i utworzenie folderu output
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)
        print(f"Utworzono folder: {OUTPUT_FOLDER}")

    # Pobranie listy plików w bieżącym katalogu
    files = [f for f in os.listdir('.') if f.endswith(INPUT_EXT)]

    if not files:
        print(f"Nie znaleziono plików {INPUT_EXT} w tym folderze.")
        return

    print(f"Znaleziono plików do przetworzenia: {len(files)}")

    for filename in files:
        try:
            # Parsowanie pliku XML
            tree = ET.parse(filename)
            root = tree.getroot()
            
            # Flaga informująca, czy dokonano zmian w pliku
            modified = False

            # Iterujemy po wszystkich elementach, szukając 'segment'
            # Używamy iter() zamiast findall z namespace, aby skrypt był uniwersalny
            for elem in root.iter():
                # Sprawdzamy czy tag kończy się na 'segment' (ignorując namespace)
                if elem.tag.endswith('segment'):
                    source_node = None
                    target_node = None
                    
                    # Szukamy source i sprawdzamy czy target już istnieje
                    for child in elem:
                        if child.tag.endswith('source'):
                            source_node = child
                        elif child.tag.endswith('target'):
                            target_node = child
                    
                    # Jeśli jest source, a nie ma target -> kopiujemy
                    if source_node is not None and target_node is None:
                        # Tworzymy nowy element target
                        # Używamy tej samej nazwy tagu co source, zamieniając końcówkę
                        # To pozwala zachować namespace, jeśli istnieje (np. {ns}source -> {ns}target)
                        new_tag_name = source_node.tag.replace('source', 'target')
                        target_node = ET.Element(new_tag_name)
                        
                        # Kopiowanie tekstu głównego (tego zaraz po otwarciu <source>)
                        target_node.text = source_node.text
                        
                        # Kopiowanie głębokie (deep copy) wszystkich tagów wewnątrz (np. <g>, <ph>, <br/>)
                        for internal_tag in source_node:
                            target_node.append(copy.deepcopy(internal_tag))
                            
                        # Znajdujemy indeks source, aby wstawić target zaraz po nim
                        parent_list = list(elem)
                        source_index = parent_list.index(source_node)
                        
                        # Wstawiamy target po source
                        elem.insert(source_index + 1, target_node)
                        
                        # Opcjonalnie: Dodanie entera/wciecia po source, aby target nie był w tej samej linii co zamknięcie source
                        # (To zależy od formatowania pliku, poniższa linia to kosmetyka dla czytelności XML)
                        if source_node.tail:
                            target_node.tail = source_node.tail

                        modified = True

            # Zapisywanie pliku w folderze output
            if modified:
                output_path = os.path.join(OUTPUT_FOLDER, filename)
                # encoding='utf-8' i xml_declaration=True są ważne dla plików XLF/XML
                tree.write(output_path, encoding='UTF-8', xml_declaration=True)
                print(f"[OK] Przetworzono: {filename}")
            else:
                # Jeśli plik nie wymagał zmian (np. miał już targety), po prostu go kopiujemy lub pomijamy
                # Tutaj zapisujemy go też do output dla porządku
                output_path = os.path.join(OUTPUT_FOLDER, filename)
                tree.write(output_path, encoding='UTF-8', xml_declaration=True)
                print(f"[INFO] Bez zmian (skopiowano): {filename}")

        except ET.ParseError as e:
            print(f"[BŁĄD] Nie można przetworzyć pliku {filename}: {e}")
        except Exception as e:
            print(f"[BŁĄD] Wystąpił niespodziewany błąd przy {filename}: {e}")

if __name__ == "__main__":
    process_xlf_files()
    input("\nNaciśnij Enter, aby zakończyć...")
