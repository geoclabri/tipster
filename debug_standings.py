"""
debug_standings.py - Analizza struttura HTML standings
"""

from bs4 import BeautifulSoup
from pathlib import Path

# Leggi HTML
html_file = Path("debug_html/standings_italy_serie-c-group-b.html")

if not html_file.exists():
    print("❌ File non trovato!")
    exit()

with open(html_file, 'r', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')

print("="*80)
print("ANALISI STRUTTURA STANDINGS")
print("="*80)

# Trova tutte le tabelle
tables = soup.find_all('table', class_='standing')
print(f"\n✅ Trovate {len(tables)} tabelle 'standing'\n")

for i, table in enumerate(tables, 1):
    print(f"─" * 80)
    print(f"TABELLA {i}")
    print(f"─" * 80)
    
    # Cerca heading precedenti
    print("\n📍 HEADING PRECEDENTI:")
    prev_elements = table.find_all_previous(['h1', 'h2', 'h3', 'h4', 'div', 'p', 'span'], limit=10)
    
    for j, elem in enumerate(prev_elements, 1):
        text = elem.get_text(strip=True)
        if text:  # Solo se ha testo
            print(f"  {j}. <{elem.name}> {text[:100]}")
    
    # Conta righe
    tbody = table.find('tbody')
    if tbody:
        rows = tbody.find_all('tr')
        print(f"\n📊 Righe dati: {len(rows)}")
        
        # Mostra prima squadra
        if rows:
            cells = rows[0].find_all('td')
            if len(cells) >= 2:
                print(f"   Prima squadra: {cells[1].get_text(strip=True)}")
    
    print()

print("="*80)
