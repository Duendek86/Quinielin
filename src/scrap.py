import requests
from bs4 import BeautifulSoup
import json
import csv
import os

# Mapeo de nombres de la Quiniela a nombres de football-data.co.uk
NOMBRE_MAP = {
    # Primera División
    "RAYO": "Vallecano",
    "ATH.CLUB": "Ath Bilbao",
    "BARCELONA": "Barcelona",
    "VILLARREAL": "Villarreal",
    "MALLORCA": "Mallorca",
    "R.SOCIEDAD": "Sociedad",
    "AT.MADRID": "Ath Madrid",
    "VALENCIA": "Valencia",
    "OSASUNA": "Osasuna",
    "GIRONA": "Girona",
    "CELTA": "Celta",
    "R.MADRID": "Real Madrid",
    "GETAFE": "Getafe",
    "BETIS": "Betis",
    "SEVILLA": "Sevilla",
    "ALAVÉS": "Alaves",
    "ALAVES": "Alaves",
    "VALLADOLID": "Valladolid",
    "LEGANÉS": "Leganes",
    "LEGANES": "Leganes",
    "LAS PALMAS": "Las Palmas",
    "ESPANYOL": "Espanol",
    # Segunda División
    "R.OVIEDO": "Oviedo",
    "ELCHE": "Elche",
    "R.ZARAGOZA": "Zaragoza",
    "BURGOS": "Burgos",
    "GRANADA": "Granada",
    "MÁLAGA": "Malaga",
    "MALAGA": "Malaga",
    "CASTELLÓN": "Castellon",
    "CASTELLON": "Castellon",
    "RACING S.": "Santander",
    "SPORTING": "Sp Gijon",
    "C. LEONESA": "Cultural Leonesa",
    "EIBAR": "Eibar",
    "CÁDIZ": "Cadiz",
    "CADIZ": "Cadiz",
    "TENERIFE": "Tenerife",
    "LEVANTE": "Levante",
    "ALMERÍA": "Almeria",
    "ALMERIA": "Almeria",
    "HUESCA": "Huesca",
    "MIRANDÉS": "Mirandes",
    "MIRANDES": "Mirandes",
    "CARTAGENA": "Cartagena",
    "CÓRDOBA": "Cordoba",
    "CORDOBA": "Cordoba",
    "ELDENSE": "Eldense",
    "CEUTA": "Ceuta",
}

def mapear_nombre(nombre_quiniela):
    """Convierte un nombre de la Quiniela al formato de football-data.co.uk"""
    return NOMBRE_MAP.get(nombre_quiniela.strip().upper(), nombre_quiniela.strip())

def obtener_quiniela():
    url = "https://www.quinielista.es/ayuda-a-pronosticar"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        spans_partidos = soup.find_all('span', class_='c-equipos__teams')
        
        partidos = []

        for i, span in enumerate(spans_partidos[:15], 1):
            label = span.get('aria-label')
            
            if label and " contra " in label:
                partes = label.split(" contra ")
                local = partes[0].strip()
                visitante = partes[1].strip()
            else:
                texto = span.get_text(strip=True)
                if "-" in texto:
                    partes = texto.split("-")
                    local = partes[0].strip()
                    visitante = partes[1].strip()
                else:
                    local, visitante = texto, "???"

            partidos.append({
                "numero": i,
                "local": local,
                "visitante": visitante,
                "local_mapped": mapear_nombre(local),
                "visitante_mapped": mapear_nombre(visitante)
            })

        return partidos

    except Exception as e:
        print(f"Error: {e}")
        return []

if __name__ == "__main__":
    partidos = obtener_quiniela()
    
    if not partidos:
        print("No se pudieron obtener los partidos de la Quiniela.")
        exit(1)
    
    resultado = json.dumps(partidos, indent=4, ensure_ascii=False)
    print(resultado)
    
    # Guardar JSON para que Quinielin lo lea
    json_path = os.path.join(os.path.dirname(__file__), '..', 'bin', 'data', 'quiniela.json')
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    
    with open(json_path, 'w', encoding='utf-8') as f:
        f.write(resultado)
    
    print(f"\nGuardado en: {os.path.abspath(json_path)}")
    print(f"Total partidos: {len(partidos)}")