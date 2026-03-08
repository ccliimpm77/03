import requests
import xml.etree.ElementTree as ET
import sys
from deep_translator import GoogleTranslator

def translate_text(translator, text, cache):
    if not text or text.strip() == "":
        return text
    if text in cache:
        return cache[text]
    
    try:
        translated = translator.translate(text)
        cache[text] = translated
        return translated
    except Exception:
        # In caso di errore (es. troppe richieste), restituisce il testo originale
        return text

def main():
    try:
        EPG_URL = "https://epg.ovh/pl.xml"
        translator = GoogleTranslator(source='auto', target='it')
        cache = {} # Per non tradurre due volte la stessa parola
        
        print("1. Lettura canali.txt...")
        try:
            with open("canali.txt", "r") as f:
                wanted = set(line.strip() for line in f if line.strip())
        except FileNotFoundError:
            print("ERRORE: file canali.txt non trovato!")
            sys.exit(1)

        print(f"Canali da cercare: {wanted}")

        print("2. Scaricamento EPG (potrebbe volerci un po')...")
        r = requests.get(EPG_URL, timeout=60)
        r.raise_for_status()
        
        print("3. Analisi e traduzione XML (fase lenta)...")
        root = ET.fromstring(r.content)
        new_root = ET.Element("tv", root.attrib)

        # Filtro canali
        canali_trovati = 0
        for c in root.findall("channel"):
            if c.get("id") in wanted:
                # Traduciamo il nome del canale se necessario (opzionale)
                display_name = c.find("display-name")
                if display_name is not None:
                    display_name.text = translate_text(translator, display_name.text, cache)
                new_root.append(c)
                canali_trovati += 1
        
        # Filtro programmi e traduzione
        programmi_trovati = 0
        programmi = root.findall("programme")
        totale_programmi = len([p for p in programmi if p.get("channel") in wanted])
        
        print(f"Inizio traduzione di {totale_programmi} programmi...")

        for p in programmi:
            if p.get("channel") in wanted:
                # Traduci Titolo
                title = p.find("title")
                if title is not None:
                    title.text = translate_text(translator, title.text, cache)
                
                # Traduci Descrizione (se esiste)
                desc = p.find("desc")
                if desc is not None:
                    desc.text = translate_text(translator, desc.text, cache)
                
                # Traduci Categoria (se esiste)
                category = p.find("category")
                if category is not None:
                    category.text = translate_text(translator, category.text, cache)

                new_root.append(p)
                programmi_trovati += 1
                
                if programmi_trovati % 10 == 0:
                    print(f"Progresso: {programmi_trovati}/{totale_programmi}...")

        print(f"Risultato: Trovati e tradotti {canali_trovati} canali e {programmi_trovati} programmi.")

        # Scrive il file
        ET.ElementTree(new_root).write("epg.xml", encoding="utf-8", xml_declaration=True)
        print("4. File epg.xml creato e tradotto correttamente.")

    except Exception as e:
        print(f"ERRORE CRITICO: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
