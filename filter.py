import requests
import xml.etree.ElementTree as ET
import sys

def main():
    try:
        EPG_URL = "https://epg.ovh/pl.xml"
        
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
        
        print("3. Analisi XML...")
        root = ET.fromstring(r.content)
        new_root = ET.Element("tv", root.attrib)

        # Filtro canali
        canali_trovati = 0
        for c in root.findall("channel"):
            if c.get("id") in wanted:
                new_root.append(c)
                canali_trovati += 1
        
        # Filtro programmi
        programmi_trovati = 0
        for p in root.findall("programme"):
            if p.get("channel") in wanted:
                new_root.append(p)
                programmi_trovati += 1

        print(f"Risultato: Trovati {canali_trovati} canali e {programmi_trovati} programmi.")

        # Scrive il file in ogni caso, anche se vuoto, per non far fallire Git
        ET.ElementTree(new_root).write("epg.xml", encoding="utf-8", xml_declaration=True)
        print("4. File epg.xml creato correttamente.")

    except Exception as e:
        print(f"ERRORE CRITICO: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
