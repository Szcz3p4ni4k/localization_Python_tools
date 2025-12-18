def process_tmx_file(file_path, file_name, banned_ids):
    """
    Parses TMX, removes segments created by banned IDs, and saves new file
    preserving UTF-16 LE encoding and DOCTYPE.
    """
    # Define output path (Ścieżka zapisu)
    new_file_name = file_name.replace(".tmx", "") + "_Updated.tmx"
    output_path = os.path.join(OUTPUT_DIR, new_file_name)

    try:
        # Parse XML tree (Parsowanie drzewa XML)
        tree = ET.parse(file_path)
        root = tree.getroot()

        # Find body element (Znajdujemy element body)
        body = root.find('body')
        
        if body is None:
            log_status(f"ERROR: No <body> found in {file_name}")
            return

        removed_count = 0
        total_segments = 0

        # Iterate safely over copy (Iterujemy bezpiecznie po kopii)
        for tu in list(body):
            total_segments += 1
            creation_id = tu.get('creationid', '').lower()
            change_id = tu.get('changeid', '').lower() # Opcjonalnie sprawdzamy też changeid
            
            if creation_id in banned_ids: # lub 'or change_id in banned_ids'
                body.remove(tu)
                removed_count += 1

        # Check result status (Status wyniku)
        if removed_count > 0:
            status_msg = f"SUCCESS: {file_name} -> Removed {removed_count} segments (Total checked: {total_segments})."
        else:
            status_msg = f"OK (NO CHANGES): {file_name} -> No banned IDs found."

        # --- ZMIANA SPOSOBU ZAPISU (FIX DLA UTF-16 i DOCTYPE) ---
        
        with open(output_path, 'wb') as f:
            # 1. Ręczny zapis BOM dla UTF-16 LE (Byte Order Mark)
            f.write(b'\xff\xfe')
            
            # 2. Ręczny zapis nagłówka XML i DOCTYPE (zakodowany w utf-16-le)
            # Dzięki temu mamy idealną kontrolę nad tym, co jest na początku pliku
            header = '<?xml version="1.0" encoding="utf-16"?>\n<!DOCTYPE tmx SYSTEM "tmx14.dtd">\n'
            f.write(header.encode('utf-16-le'))
            
            # 3. Zapis drzewa XML
            # Używamy 'utf-16-le' żeby pasowało do BOM, który daliśmy ręcznie.
            # xml_declaration=False, bo napisaliśmy własną deklarację wyżej.
            tree.write(f, encoding='utf-16-le', xml_declaration=False)

        # --------------------------------------------------------

        log_status(status_msg)

        # Memory cleanup (Czyszczenie pamięci)
        del body
        del root
        del tree

    except ET.ParseError:
        log_status(f"ERROR: Could not parse XML in {file_name}. File might be corrupted.")
    except Exception as e:
        log_status(f"ERROR: Critical failure processing {file_name}: {str(e)}")
