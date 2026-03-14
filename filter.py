import requests
import xml.etree.ElementTree as ET
import sys
import json
import os
import html
from deep_translator import GoogleTranslator

# Configurazione
EPG_URL = "https://epg.ovh/pl.xml"
CACHE_FILE = "cache_traduzioni.json"
BATCH_SIZE = 40 

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

def clean_text(text):
    if not text: return ""
    # Rimuove entità HTML residue e spazi bianchi eccessivi
    return html.unescape(text).strip()

def translate_batch(translator, texts_to_translate, cache):
    if not texts_to_translate:
        return
    
    # Pulizia testi prima dell'invio
    clean_list = [clean_text(t) for t in texts_to_translate if t]
    if not clean_list: return

    print(f"--- Traduzione blocco di {len(clean_list)} testi... ---")
    try:
        results = translator.translate_batch(clean_list)
        for original, translated in zip(texts_to_translate, results):
            cache[original] = translated
    except Exception as e:
        print(f"Errore durante la traduzione: {e}")

def main():
    try:
        translator = GoogleTranslator(source='auto', target='it')
        cache = load_cache()
        
        print("1. Lettura canali.txt...")
        try:
            with open("canali.txt", "r") as f:
                wanted = set(line.strip() for line in f if line.strip())
        except FileNotFoundError:
            print("ERRORE: canali.txt non trovato!")
            sys.exit(1)

        print("2. Scaricamento EPG...")
        r = requests.get(EPG_URL, timeout=60)
        r.raise_for_status()
        
        print("3. Analisi XML e raccolta testi...")
        root = ET.fromstring(r.content)
        
        to_translate = set()
        relevant_programmes = [p for p in root.findall("programme") if p.get("channel") in wanted]
        
        # Tags da tradurre nei programmi
        tags_to_translate = ["title", "sub-title", "desc", "category"]

        for p in relevant_programmes:
            for tag in tags_to_translate:
                elem = p.find(tag)
                if elem is not None and elem.text:
                    txt = clean_text(elem.text)
                    if txt and txt not in cache and not txt.isdigit():
                        to_translate.add(txt)

        # Fase traduzione
        to_translate_list = list(to_translate)
        for i in range(0, len(to_translate_list), BATCH_SIZE):
            batch = to_translate_list[i : i + BATCH_SIZE]
            translate_batch(translator, batch, cache)
            if i % 200 == 0: save_cache(cache)

        save_cache(cache)

        print("4. Generazione file epg.xml corretto...")
        new_root = ET.Element("tv", root.attrib)
        
        # Gestione Canali (copia senza tradurre il nome per evitare errori nei loghi)
        for c in root.findall("channel"):
            if c.get("id") in wanted:
                # Opzionale: forziamo lang="it" sui nomi display
                for dn in c.findall("display-name"):
                    dn.set("lang", "it")
                new_root.append(c)

        # Gestione Programmi
        for p in relevant_programmes:
            # Creiamo una copia del programma per non sporcare l'originale
            for tag in tags_to_translate:
                elem = p.find(tag)
                if elem is not None and elem.text:
                    cleaned = clean_text(elem.text)
                    if cleaned in cache:
                        elem.text = cache[cleaned]
                    # IMPORTANTE: Cambiamo la lingua in italiano
                    elem.set("lang", "it")
            new_root.append(p)

        # Scrittura finale con codifica corretta
        tree = ET.ElementTree(new_root)
        tree.write("epg.xml", encoding="utf-8", xml_declaration=True)
        
        print("Fatto! Il file epg.xml è pronto e ottimizzato per l'Italia.")

    except Exception as e:
        print(f"ERRORE: {e}")

if __name__ == "__main__":
    main()
