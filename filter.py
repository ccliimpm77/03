import requests
import xml.etree.ElementTree as ET
import os

# Configurazione
EPG_URL = "https://epg.ovh/pl.xml"
CHANNELS_FILE = "channel 01.txt"
OUTPUT_FILE = "epg.xml"

def main():
    if not os.path.exists(CHANNELS_FILE):
        print("Errore: canali.txt non trovato")
        return

    with open(CHANNELS_FILE, "r") as f:
        wanted_ids = set(line.strip() for line in f if line.strip())

    print("Scaricamento EPG originale...")
    r = requests.get(EPG_URL)
    root = ET.fromstring(r.content)

    new_root = ET.Element("tv", root.attrib)

    # Filtra Canali
    for channel in root.findall("channel"):
        if channel.get("id") in wanted_ids:
            new_root.append(channel)

    # Filtra Programmi
    for programme in root.findall("programme"):
        if programme.get("channel") in wanted_ids:
            new_root.append(programme)

    # Salva
    tree = ET.ElementTree(new_root)
    tree.write(OUTPUT_FILE, encoding="utf-8", xml_declaration=True)
    print("Fatto!")

if __name__ == "__main__":
    main()
