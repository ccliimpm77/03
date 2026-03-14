import requests
import xml.etree.ElementTree as ET
import sys
import json
import os
from deep_translator import GoogleTranslator

# Configurazione
EPG_URL = "https://epg.ovh/pl.xml"
CACHE_FILE = "cache_traduzioni.json"
BATCH_SIZE = 50  # Numero di testi da tradurre in una singola chiamata

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def translate_batch(translator, texts_to_translate, cache):
    if not texts_to_translate:
        return
    
    print(f"--- Traduzione di un blocco di {len(texts_to_translate)} testi... ---")
    try:
        # translate_batch accetta una lista di stringhe
        results = translator.translate_batch(texts_to_translate)
        for original, translated in zip(texts_to_translate, results):
            cache[original] = translated
    except Exception as e:
        print(f"Errore durante la traduzione batch: {e}")
        # In caso di errore, non salviamo nulla in cache per questi testi
        pass

def main():
    try:
        translator = GoogleTranslator(source='auto', target='it')
        cache = load_cache()
        
        print("1. Lettura canali.txt...")
        try:
            with open("canali.txt", "r") as f:
                wanted = set(line.strip() for line in f if line.strip())
        except FileNotFoundError:
            print("ERRORE: file canali.txt non trovato!")
            sys.exit(1)

        print("2. Scaricamento EPG...")
        r = requests.get(EPG_URL, timeout=60)
        r.raise_for_status()
        
        print("3. Analisi XML e raccolta testi da tradurre...")
        root = ET.fromstring(r.content)
        
        # Fase 1: Raccogliamo tutti i testi UNICI che non sono in cache
        to_translate = set()
        
        # Filtro canali e programmi per trovare i testi
        relevant_programmes = [p for p in root.findall("programme") if p.get("channel") in wanted]
        relevant_channels = [c for c in root.findall("channel") if c.get("id") in wanted]

        for c in relevant_channels:
            name = c.find("display-name")
            if name is not None and name.text and name.text not in cache:
                to_translate.add(name.text)

        for p in relevant_programmes:
            for tag in ["title", "desc", "category"]:
                elem = p.find(tag)
                if elem is not None and elem.text and elem.text.strip() != "":
                    if elem.text not in cache:
                        to_translate.add(elem.text)

        # Fase 2: Traduzione in batch
        to_translate_list = list(to_translate)
        for i in range(0, len(to_translate_list), BATCH_SIZE):
            batch = to_translate_list[i : i + BATCH_SIZE]
            translate_batch(translator, batch, cache)
            # Salvataggio intermedio della cache per sicurezza
            if i % (BATCH_SIZE * 5) == 0:
                save_cache(cache)

        save_cache(cache) # Salvataggio finale

        # Fase 3: Costruzione del nuovo XML usando la cache
        print("4. Generazione file finale...")
        new_root = ET.Element("tv", root.attrib)
        
        for c in relevant_channels:
            name = c.find("display-name")
            if name is not None and name.text in cache:
                name.text = cache[name.text]
            new_root.append(c)

        for p in relevant_programmes:
            for tag in ["title", "desc", "category"]:
                elem = p.find(tag)
                if elem is not None and elem.text in cache:
                    elem.text = cache[elem.text]
            new_root.append(p)

        ET.ElementTree(new_root).write("epg.xml", encoding="utf-8", xml_declaration=True)
        print(f"Completato! Canali: {len(relevant_channels)}, Programmi: {len(relevant_programmes)}")

    except Exception as e:
        print(f"ERRORE CRITICO: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
