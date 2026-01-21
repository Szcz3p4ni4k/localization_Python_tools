import os
import copy
import xml.etree.ElementTree as ET

# Konfiguracja
INPUT_EXT = '.xml'
OUTPUT_FOLDER = 'output'

def register_all_namespaces(filename):
    """
    Funkcja pomocnicza do skanowania pliku i rejestrowania prefixów.
    Zapobiega pojawianiu się ns0: w pliku wynikowym.
    """
    namespaces = dict([node for _, node in ET.iterparse(filename, events=['start-ns'])])
    for ns, url in namespaces.items():
        ET.register_namespace(ns, url)

def process_xlf_files():
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)
        print(f"Utworzono folder: {OUTPUT_FOLDER}")

    files = [f for f in os.listdir('.') if f.endswith(INPUT_EXT)]

    if not files:
        print(f"Nie znaleziono plików {INPUT_EXT} w tym folderze.")
        return

    print(f"Znaleziono plików do przetworzenia: {len(files)}")

    for filename in files:
        try:
            # 1. Najpierw rejestrujemy przestrzenie nazw z pliku, żeby nie było ns0:
            register_all_namespaces(filename)

            # 2. Parsowanie pliku
            tree = ET.parse(filename)
            root = tree.getroot()
            
            modified = False

            # Iterujemy po elementach
            for elem in root.iter():
                # Sprawdzamy czy to segment
                if elem.tag.endswith('segment'):
                    source_node = None
                    target_node = None
                    
                    for child in elem:
                        if child.tag.endswith('source'):
                            source_node = child
                        elif child.tag.endswith('target'):
                            target_node = child
                    
                    # Jeśli jest source, a nie ma target -> kopiujemy
                    if source_node is not None and target_node is None:
                        # Tworzymy tag target używając tej samej pełnej nazwy co source
                        # (dzięki temu dziedziczy namespace {url}source -> {url}target)
                        new_tag_name = source_node.tag.replace('source', 'target')
                        target_node = ET.Element(new_tag_name)
                        
                        target_node.text = source_node.text
                        
                        for internal_tag in source_node:
                            target_node.append(copy.deepcopy(internal_tag))
                            
                        # Wstawiamy target po source
                        parent_list = list(elem)
                        source_index = parent_list.index(source_node)
                        elem.insert(source_index + 1, target_node)
                        
                        if source_node.tail:
                            target_node.tail = source_node.tail

                        modified = True

            # Zapisywanie
            output_path = os.path.join(OUTPUT_FOLDER, filename)
            if modified:
                tree.write(output_path, encoding='UTF-8', xml_declaration=True)
                print(f"[OK] Przetworzono: {filename}")
            else:
                tree.write(output_path, encoding='UTF-8', xml_declaration=True)
                print(f"[INFO] Bez zmian: {filename}")

        except ET.ParseError as e:
            print(f"[BŁĄD] Plik {filename} jest uszkodzony: {e}")
        except Exception as e:
            print(f"[BŁĄD] {filename}: {e}")

if __name__ == "__main__":
    process_xlf_files()
    input("\nNaciśnij Enter, aby zakończyć...")
