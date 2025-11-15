"""
test_scraper.py - Test completo del nuovo scraper
"""

import asyncio
from datetime import datetime
from pathlib import Path
import sys
import json

sys.path.insert(0, str(Path(__file__).parent))

from src.scraper.match_scraper import MatchScraper
from src.utils.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


async def test_league_conversion():
    """Test conversione nomi campionati"""
    scraper = MatchScraper(Config())
    
    test_cases = [
        ("England - Premier League", "england/premier-league"),
        ("Italy - Serie C - Group B", "italy/serie-c-group-b"),
        ("Spain - Segunda Division", "spain/segunda-division"),
        ("World Championship Qual. grp. B", "world-championship-qual.-grp.-b"),
        ("National Friendly", "national-friendly"),
        ("Club Friendly", "club-friendly"),
    ]
    
    print("\n" + "="*70)
    print("TEST: Conversione nomi campionati")
    print("="*70)
    
    for name, expected in test_cases:
        result = scraper._league_name_to_key(name)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{name}'")
        print(f"   Expected: {expected}")
        print(f"   Got:      {result}")
        print()


async def test_statistics_parsing():
    """Test parsing statistics da HTML reale"""
    
    print("\n" + "="*70)
    print("TEST: Parsing Statistics (HTML reale)")
    print("="*70)
    
    # Leggi HTML salvato
    html_file = Path("debug_html/statistics_italy_serie-c-group-b.html")
    
    if not html_file.exists():
        print("⚠️  File HTML non trovato. Scarico ora...")
        
        # Scarica HTML
        config = Config()
        async with MatchScraper(config) as scraper:
            stats = await scraper._fetch_league_statistics("italy/serie-c-group-b")
            
            if stats:
                print(f"\n📊 Estratte {len(stats)} metriche:\n")
                
                for key, value in sorted(stats.items()):
                    if key == 'over_under':
                        print(f"  {key}:")
                        for threshold, values in value.items():
                            print(f"    {threshold}: Under {values['under']}% | Over {values['over']}%")
                    else:
                        print(f"  {key}: {value}")
            else:
                print("❌ Impossibile scaricare statistics")
        
        print("\n" + "="*70)
        return
    
    with open(html_file, 'r', encoding='utf-8') as f:
        html = f.read()
    
    scraper = MatchScraper(Config())
    stats = scraper._parse_statistics_page(html)
    
    print(f"\n📊 Estratte {len(stats)} metriche:\n")
    
    for key, value in sorted(stats.items()):
        if key == 'over_under':
            print(f"  {key}:")
            for threshold, values in value.items():
                print(f"    {threshold}: Under {values['under']}% | Over {values['over']}%")
        else:
            print(f"  {key}: {value}")
    
    print("\n" + "="*70)


async def test_full_scraping():
    """Test scraping completo su data specifica"""
    
    print("\n" + "="*70)
    print("TEST: Scraping completo")
    print("="*70)
    
    config = Config()
    
    async with MatchScraper(config) as scraper:
        # Scarica match
        date = datetime(2025, 11, 15)
        matches = await scraper.get_matches_by_date(date)
        
        print(f"\n✅ Scaricati {len(matches)} match da {len(set(m.league for m in matches))} campionati\n")
        
        # Scarica dettagli (solo primi 5 campionati per test rapido)
        test_matches = matches[:10]
        detailed = await scraper.get_matches_details(test_matches)
        
        # Statistiche
        with_standings = sum(1 for m in detailed if m.league_standings)
        with_statistics = sum(1 for m in detailed if m.league_statistics)
        
        print(f"\n📊 Risultati:")
        print(f"  - Match con standings: {with_standings}/{len(detailed)}")
        print(f"  - Match con statistics: {with_statistics}/{len(detailed)}")
        
        # Export cache
        output_dir = scraper.export_league_data()
        if output_dir:
            print(f"\n💾 Cache esportata in: {output_dir}")
        
        # Mostra esempio statistics
        for match in detailed:
            if match.league_statistics:
                print(f"\n✅ Statistics trovate per: {match.league}")
                print(f"   Keys: {list(match.league_statistics.keys())}")
                break
    
    print("\n" + "="*70)


async def main():
    """Esegue tutti i test"""
    
    # Test 1: Conversione nomi
    await test_league_conversion()
    
    # Test 2: Parsing statistics
    await test_statistics_parsing()
    
    # Test 3: Scraping completo (opzionale - commentare se troppo lento)
    # await test_full_scraping()
    
    print("\n✅ Test completati!\n")


if __name__ == "__main__":
    asyncio.run(main())