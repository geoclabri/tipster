"""
download_match.py
Scarica la pagina della partita specifica
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
import re

async def download_and_analyze():
    url = "https://tipsterarea.com/match/penya-encarnada-pas-de-la-casa-primera-divisio-andorra-901602"
    
    print("="*80)
    print(f"Downloading: {url}")
    print("="*80)
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers={'User-Agent': 'Mozilla/5.0'}) as response:
            if response.status != 200:
                print(f"❌ Error: Status {response.status}")
                return
            
            html = await response.text()
            print(f"✓ Downloaded {len(html):,} bytes\n")
            
            # Salva
            with open('andorra_match.html', 'w', encoding='utf-8') as f:
                f.write(html)
            print("✓ Saved to andorra_match.html\n")
            
            # Parse
            soup = BeautifulSoup(html, 'html.parser')
            
            # ===== ANALISI RAPIDA =====
            print("="*80)
            print("QUICK ANALYSIS")
            print("="*80)
            
            # 1. Heading
            print("\n1. ALL HEADINGS:")
            print("-"*80)
            headings = soup.find_all(['h1', 'h2', 'h3', 'h4'])
            for h in headings:
                print(f"  <{h.name}> {h.get_text(strip=True)}")
            
            # 2. Cerca "Statistics"
            print("\n2. SEARCH 'STATISTICS':")
            print("-"*80)
            stats_text = soup.find_all(string=re.compile(r'Statistic', re.I))
            for i, txt in enumerate(stats_text[:5], 1):
                parent = txt.parent
                print(f"  {i}. <{parent.name}> class={parent.get('class', [])} → {txt.strip()}")
            
            # 3. Tabelle
            print("\n3. ALL TABLES:")
            print("-"*80)
            tables = soup.find_all('table')
            print(f"Found {len(tables)} tables\n")
            
            for i, table in enumerate(tables, 1):
                classes = table.get('class', [])
                rows = table.find_all('tr')
                
                print(f"Table {i}: class={classes}, rows={len(rows)}")
                
                # Prima riga
                if rows:
                    first_cells = rows[0].find_all(['th', 'td'])
                    first_text = [c.get_text(strip=True) for c in first_cells[:8]]
                    print(f"  First row: {first_text}")
                
                # Se ha "standing" nel class
                if any('standing' in str(c).lower() for c in classes):
                    print(f"  → THIS IS STANDINGS TABLE!")
                
                # Se ha "perft" o "stats"
                if any(x in str(classes).lower() for x in ['perft', 'stat', 'performance']):
                    print(f"  → THIS IS STATS TABLE!")
                
                print()
            
            # 4. Cerca pattern specifici
            print("\n4. SPECIFIC PATTERNS:")
            print("-"*80)
            
            # Pattern: "Completed XX%"
            completed = soup.find(string=re.compile(r'Completed.*?\d+%', re.I))
            if completed:
                print(f"  ✓ Found 'Completed': {completed.strip()}")
            
            # Pattern: "Home Win XX%"
            home_win = soup.find(string=re.compile(r'Home Win.*?\d+%', re.I))
            if home_win:
                print(f"  ✓ Found 'Home Win': {home_win.strip()}")
            
            # Pattern: "Average X.XX"
            average = soup.find(string=re.compile(r'Average.*?\d+\.\d+', re.I))
            if average:
                print(f"  ✓ Found 'Average': {average.strip()}")
            
            # 5. Div con statistiche
            print("\n5. DIV WITH 'stat' CLASS:")
            print("-"*80)
            stat_divs = soup.find_all('div', class_=re.compile(r'stat|info', re.I))
            print(f"Found {len(stat_divs)} divs")
            
            for i, div in enumerate(stat_divs[:10], 1):
                text = div.get_text(strip=True)[:100]
                print(f"  {i}. class={div.get('class', [])} → {text}")
            
            # 6. Cerca "Primera Divisio" (nome campionato)
            print("\n6. LEAGUE NAME MENTIONS:")
            print("-"*80)
            league_mentions = soup.find_all(string=re.compile(r'Primera Divisio', re.I))
            print(f"Found {len(league_mentions)} mentions of 'Primera Divisio'")
            
            for i, mention in enumerate(league_mentions[:5], 1):
                parent = mention.parent
                context = parent.get_text(strip=True)[:80]
                print(f"  {i}. <{parent.name}> {context}")
            
            print("\n" + "="*80)
            print("ANALYSIS COMPLETE")
            print("="*80)
            print("\nCheck 'andorra_match.html' and send me the output!")

if __name__ == "__main__":
    asyncio.run(download_and_analyze())
