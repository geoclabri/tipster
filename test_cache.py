"""
test_cache.py - Verifica contenuto cache standings
"""

import json
from pathlib import Path

print("="*80)
print("TEST CACHE STANDINGS")
print("="*80)

# Verifica se cartella esiste
league_data_dir = Path("league_data")
if not league_data_dir.exists():
    print("\n❌ Cartella 'league_data' NON ESISTE")
    print("   SOLUZIONE: Apri GUI e scarica match con 'Download complete details'\n")
    exit()

# Verifica se file cache esiste
cache_file = league_data_dir / "standings_cache.json"
if not cache_file.exists():
    print("\n❌ File 'standings_cache.json' NON ESISTE")
    print("   SOLUZIONE: Apri GUI e scarica match con 'Download complete details'\n")
    exit()

# Leggi cache
with open(cache_file, 'r', encoding='utf-8') as f:
    cache = json.load(f)

print(f"\n✅ Cache trovata con {len(cache)} campionati\n")

# Elenca campionati
print("Campionati in cache:")
for i, league_key in enumerate(list(cache.keys())[:5], 1):
    print(f"  {i}. {league_key}")

if len(cache) > 5:
    print(f"  ... e altri {len(cache) - 5}")

# Analizza UN campionato esempio
league_key = "italy/serie-c-group-b"

print(f"\n{'='*80}")
print(f"ANALISI: {league_key}")
print("="*80)

if league_key not in cache:
    print(f"\n⚠️ '{league_key}' non trovato in cache")
    print(f"\nCampionati disponibili:")
    for key in cache.keys():
        if 'italy' in key.lower():
            print(f"  - {key}")
    exit()

data = cache[league_key]

# Verifica struttura
print(f"\nStruttura dati:")
print(f"  Tipo: {type(data)}")
print(f"  Keys: {list(data.keys()) if isinstance(data, dict) else 'N/A'}")

# Verifica squadre
if isinstance(data, dict):
    overall = data.get('overall', [])
    home = data.get('home', [])
    away = data.get('away', [])
    
    print(f"\n📊 Conteggio squadre:")
    print(f"  Overall: {len(overall)}")
    print(f"  Home: {len(home)}")
    print(f"  Away: {len(away)}")
    
    # Mostra prima squadra di ogni tipo
    if overall:
        print(f"\n✅ OVERALL - Prima squadra:")
        print(f"   {json.dumps(overall[0], indent=4, ensure_ascii=False)}")
    
    if home:
        print(f"\n✅ HOME - Prima squadra:")
        print(f"   {json.dumps(home[0], indent=4, ensure_ascii=False)}")
    
    if away:
        print(f"\n✅ AWAY - Prima squadra:")
        print(f"   {json.dumps(away[0], indent=4, ensure_ascii=False)}")
    
    # IMPORTANTE: Verifica goals_for
    if home:
        gf = home[0].get('goals_for', 'N/A')
        print(f"\n🎯 GOALS_FOR (Home): {gf}")
    
    if away:
        gf = away[0].get('goals_for', 'N/A')
        print(f"🎯 GOALS_FOR (Away): {gf}")
else:
    print("\n❌ Struttura dati NON È UN DICT!")
    print(f"   È invece: {type(data)}")
    if isinstance(data, list) and data:
        print(f"\n   Prima entry: {data[0]}")

print("\n" + "="*80)
print("TEST COMPLETATO")
print("="*80 + "\n")