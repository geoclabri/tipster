"""
test_single_match.py
Script per testare parsing di una singola partita con DEBUG
"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.scraper.match_scraper import MatchScraper
from src.utils.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


async def test_match(url: str):
    """Testa parsing singola partita"""
    
    print("="*80)
    print(f"TEST PARSING: {url}")
    print("="*80)
    
    config = Config()
    scraper = MatchScraper(config)
    
    async with scraper:
        # Download HTML
        print("\n1. Downloading HTML...")
        html = await scraper._fetch_page(url)
        
        if not html:
            print("❌ Failed to download HTML")
            return
        
        print(f"✓ Downloaded {len(html)} bytes")
        
        # Salva HTML per ispezione
        with open('debug_match_page.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("✓ Saved to debug_match_page.html")
        
        # Parse HTML
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        # ===== TEST 1: League Statistics =====
        print("\n" + "="*80)
        print("TEST 1: LEAGUE STATISTICS")
        print("="*80)
        
        # Cerca heading
        stats_heading = soup.find(['h2', 'h3', 'h4'], string=re.compile(r'Statistics for', re.I))
        print(f"\nHeading 'Statistics for...': {stats_heading is not None}")
        
        if stats_heading:
            print(f"Heading text: '{stats_heading.get_text(strip=True)}'")
            
            # Cerca tabelle/div vicini
            next_siblings = []
            for i, sibling in enumerate(stats_heading.find_next_siblings(limit=10)):
                if hasattr(sibling, 'name'):
                    next_siblings.append((i, sibling.name, sibling.get('class', [])))
            
            print(f"\nNext 10 siblings:")
            for i, name, classes in next_siblings:
                print(f"  {i}. <{name}> class={classes}")
            
            # Cerca tabelle
            tables_after = stats_heading.find_all_next('table', limit=3)
            print(f"\nTables after heading: {len(tables_after)}")
            
            for i, table in enumerate(tables_after, 1):
                print(f"\nTable {i}:")
                print(f"  Classes: {table.get('class', [])}")
                rows = table.find_all('tr')
                print(f"  Rows: {len(rows)}")
                
                if rows:
                    print(f"  First 3 rows:")
                    for row in rows[:3]:
                        cells = row.find_all(['td', 'th'])
                        texts = [c.get_text(strip=True) for c in cells]
                        print(f"    {texts}")
        
        # Test metodo scraper
        print("\n" + "-"*80)
        print("CALLING SCRAPER METHOD...")
        print("-"*80)
        
        league_stats = scraper._extract_league_statistics(soup)
        print(f"\nExtracted stats: {league_stats}")
        
        # ===== TEST 2: Full Standings =====
        print("\n" + "="*80)
        print("TEST 2: FULL STANDINGS")
        print("="*80)
        
        # Cerca tabella standings
        standing_table = soup.find('table', class_='standing')
        print(f"\nTable with class='standing': {standing_table is not None}")
        
        if standing_table:
            tbody = standing_table.find('tbody')
            print(f"Has tbody: {tbody is not None}")
            
            if tbody:
                rows = tbody.find_all('tr')
                print(f"Rows in tbody: {len(rows)}")
                
                if rows:
                    print(f"\nFirst 3 rows:")
                    for row in rows[:3]:
                        cells = row.find_all('td')
                        texts = [c.get_text(strip=True) for c in cells]
                        print(f"  {texts}")
        
        # Test metodo
        print("\n" + "-"*80)
        print("CALLING SCRAPER METHOD...")
        print("-"*80)
        
        standings = scraper._extract_full_standings(soup)
        print(f"\nExtracted {len(standings)} teams")
        
        if standings:
            print(f"\nFirst 3 teams:")
            for team in standings[:3]:
                print(f"  {team}")
        
        # ===== TEST 3: Last Matches =====
        print("\n" + "="*80)
        print("TEST 3: LAST MATCHES")
        print("="*80)
        
        # Cerca heading
        lm_headings = soup.find_all(['h2', 'h3', 'h4'], string=re.compile(r'Last Matches', re.I))
        print(f"\nFound {len(lm_headings)} 'Last Matches' headings")
        
        for i, heading in enumerate(lm_headings, 1):
            print(f"\nHeading {i}: '{heading.get_text(strip=True)}'")
            
            # Trova tabella
            table = heading.find_next('table')
            if table:
                print(f"  Has table: Yes")
                print(f"  Table classes: {table.get('class', [])}")
                
                tbody = table.find('tbody')
                if tbody:
                    rows = tbody.find_all('tr')
                    print(f"  Rows: {len(rows)}")
                    
                    if rows:
                        print(f"  First row cells:")
                        cells = rows[0].find_all('td')
                        texts = [c.get_text(strip=True) for c in cells]
                        print(f"    {texts}")
            else:
                print(f"  Has table: No")
        
        # ===== TEST 4: Head to Head =====
        print("\n" + "="*80)
        print("TEST 4: HEAD TO HEAD")
        print("="*80)
        
        h2h_heading = soup.find(['h2', 'h3', 'h4'], string=re.compile(r'Head to Head', re.I))
        print(f"\nHeading 'Head to Head': {h2h_heading is not None}")
        
        if h2h_heading:
            print(f"Heading text: '{h2h_heading.get_text(strip=True)}'")
            
            table = h2h_heading.find_next('table')
            if table:
                rows = table.find_all('tr')
                print(f"Table rows: {len(rows)}")
                
                if rows:
                    print(f"\nFirst row:")
                    cells = rows[0].find_all(['td', 'th'])
                    texts = [c.get_text(strip=True) for c in cells]
                    print(f"  {texts}")
        
        # ===== TEST 5: Home Away Comparison =====
        print("\n" + "="*80)
        print("TEST 5: HOME AWAY COMPARISON")
        print("="*80)
        
        comp_heading = soup.find(['h2', 'h3', 'h4'], string=re.compile(r'Home Away Comparison', re.I))
        print(f"\nHeading 'Home Away Comparison': {comp_heading is not None}")
        
        if comp_heading:
            table = comp_heading.find_next('table')
            if table:
                rows = table.find_all('tr')
                print(f"Table rows: {len(rows)}")
                
                for i, row in enumerate(rows[:5]):
                    cells = row.find_all(['td', 'th'])
                    texts = [c.get_text(strip=True) for c in cells]
                    print(f"  Row {i}: {texts}")
        
        print("\n" + "="*80)
        print("DEBUG COMPLETE")
        print("="*80)
        print("\nCheck 'debug_match_page.html' for full HTML")


if __name__ == "__main__":
    import re
    
    # USA L'URL della partita dalle tue screenshot
    # Boyaca Chico vs Millonarios Bogota
    test_url = "https://tipsterarea.com/match/boyaca-chico-millonarios-bogota-categoria-primera-a-colombia-901574"
    
    # O usa questo se è Penya Encarnada vs Pas de la Casa
    # test_url = "https://tipsterarea.com/match/penya-encarnada-pas-de-la-casa-primera-divisio-andorra-901602"
    
    asyncio.run(test_match(test_url))