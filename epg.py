import requests
import xml.etree.ElementTree as ET

SOURCE_URL = "https://iptv-org.github.io/epg/guides/es/tv.movistar.com.pe.xml"
OUTPUT_FILE = "epg.xml"


def main():
    print("Descargando EPG de Movistar Perú...")

    response = requests.get(
        SOURCE_URL,
        timeout=60,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; Movistar-EPG/1.0)"
        }
    )

    response.raise_for_status()

    print("Validando XMLTV...")

    root = ET.fromstring(response.content)

    if root.tag != "tv":
        raise RuntimeError("La fuente no es un XMLTV válido.")

    channels = root.findall("channel")
    programmes = root.findall("programme")

    if not channels:
        raise RuntimeError("No se encontraron canales.")

    if not programmes:
        raise RuntimeError("No se encontraron programas.")

    tree = ET.ElementTree(root)

    try:
        ET.indent(tree, space="  ")
    except AttributeError:
        pass

    tree.write(
        OUTPUT_FILE,
        encoding="utf-8",
        xml_declaration=True
    )

    print("--------------------------------")
    print(f"Canales encontrados: {len(channels)}")
    print(f"Programas encontrados: {len(programmes)}")
    print(f"Archivo generado: {OUTPUT_FILE}")
    print("--------------------------------")


if __name__ == "__main__":
    main()
