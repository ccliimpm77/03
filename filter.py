import requests
import xml.etree.ElementTree as ET
import sys
import json
import os
import html
from deep_translator import GoogleTranslator
from concurrent.futures import ThreadPoolExecutor

# Configurazione
EPG_URL = "https://epg.ovh/pl.xml"
CACHE_FILE = "cache_traduzioni.json"
MAX_WORKERS = 10  # Numero di traduzioni simultanee (non esagerare per evitare ban)

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
    return html.unescape(text).strip()

def translate_single(text, translator):
    """Funzione per tradurre una singola stringa (usata dai thread)"""
    try:
        return text, translator.translate(text)
    except:
        return text, text # In caso di errore restituisce l'originale

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
        
        print("3. Analisi XML e raccolta testi unici...")
        root = ET.fromstring(r.content)
        
        to_translate = set()
        relevant_programmes = [p for p in root.findall("programme") if p.get("channel") in wanted]
        tags_to_translate = ["title", "sub-title", "desc", "category"]

        for p in relevant_programmes:
            for tag in tags_to_translate:
                elem = p.find(tag)
                if elem is not None and elem.text:
                    txt = clean_text(elem.text)
                    if txt and txt not in cache and not txt.isdigit():
                        to_translate.add(txt)

        # Fase traduzione VELOCE con ThreadPool
        if to_translate:
            print(f"--- Traduzione di {len(to_translate)} testi nuovi (modalità veloce)... ---")
            
            # Usiamo ThreadPoolExecutor per fare più richieste insieme
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                # Creiamo una lista di compiti
                futures = [executor.submit(translate_single, t, translator) for t in to_translate]
                
                contatore = 0
                for future in futures:
                    original, translated = future.result()
                    cache[original] = translated
                    contatore += 1
                    if contatore % 20 == 0:
                        print(f"Progresso: {contatore}/{len(to_translate)}...")

            save_cache(cache)
        else:
            print("Nessun nuovo testo da tradurre (tutto in cache).")

        print("4. Generazione file epg.xml finale...")
        new_root = ET.Element("tv", root.attrib)
        
        # Canali
        for c in root.findall("channel"):
            if c.get("id") in wanted:
                for dn in c.findall("display-name"):
                    dn.set("lang", "it")
                new_root.append(c)

        # Programmi
        for p in relevant_programmes:
            for tag in tags_to_translate:
                elem = p.find(tag)
                if elem is not None and elem.text:
                    cleaned = clean_text(elem.text)
                    if cleaned in cache:
                        elem.text = cache[cleaned]
                    elem.set("lang", "it")
            new_root.append(p)

        tree = ET.ElementTree(new_root)
        tree.write("epg.xml", encoding="utf-8", xml_declaration=True)
        
        print(f"Completato con successo! File epg.xml generato.")

    except Exception as e:
        print(f"ERRORE CRITICO: {e}")

if __name__ == "__main__":
    main()
