"""
main.py
Script principale per estrazione completa dati TipsterArea
"""

import asyncio
from datetime import datetime, timedelta
from src.scraper.match_scraper import MatchScraper
from src.models.match_data import MatchCollection
from src.utils.logger import setup_logger
from src.utils.config import Config

logger = setup_logger(__name__)


async def main():
    """
    Funzione principale - estrae dati completi
    """
    try:
        config = Config()
        
        # Parametri
        target_date = datetime.now()  # Cambia qui per altra data
        extract_details = True  # True = scarica anche stats, False = solo quote base
        
        logger.info("="*60)
        logger.info("🚀 TIPSTERAREA SCRAPER - AVVIO")
        logger.info("="*60)
        logger.info(f"📅 Data: {target_date.strftime('%d-%m-%Y')}")
        logger.info(f"📊 Dettagli: {'SÌ' if extract_details else 'NO'}")
        logger.info("")
        
        scraper = MatchScraper(config)
        
        # FASE 1: Download lista partite
        logger.info("📥 FASE 1: Download lista partite...")
        matches = await scraper.get_matches_by_date(target_date)
        
        if not matches:
            logger.warning("❌ Nessuna partita trovata")
            return
        
        logger.info(f"✓ Trovate {len(matches)} partite")
        
        # FASE 2: Download dettagli (opzionale)
        if extract_details:
            logger.info("")
            logger.info("📊 FASE 2: Download dettagli e statistiche...")
            matches = await scraper.get_matches_details(matches)
            logger.info(f"✓ Completati dettagli per {len(matches)} partite")
        
        # FASE 3: Salvataggio
        logger.info("")
        logger.info("💾 FASE 3: Salvataggio dati...")
        
        collection = MatchCollection(matches)
        
        # Excel
        excel_file = f"matches_{target_date.strftime('%Y%m%d')}.xlsx"
        excel_path = collection.to_excel(f"data/output/{excel_file}")
        logger.info(f"✓ Excel: {excel_path}")
        
        # CSV
        csv_file = f"matches_{target_date.strftime('%Y%m%d')}.csv"
        csv_path = collection.to_csv(f"data/output/{csv_file}")
        logger.info(f"✓ CSV: {csv_path}")
        
        # JSON
        json_file = f"matches_{target_date.strftime('%Y%m%d')}.json"
        json_path = collection.to_json(f"data/output/{json_file}")
        logger.info(f"✓ JSON: {json_path}")
        
        # STATISTICHE FINALI
        logger.info("")
        logger.info("="*60)
        logger.info("📊 STATISTICHE FINALI")
        logger.info("="*60)
        
        stats = collection.get_statistics()
        
        logger.info(f"Totale partite: {stats['total_matches']}")
        logger.info(f"Leghe uniche: {stats['unique_leagues']}")
        logger.info(f"Con quote complete: {stats['matches_with_odds']}")
        
        if extract_details:
            logger.info(f"Con statistiche: {stats.get('with_detailed_stats', 0)}")
        
        # Mostra alcune partite di esempio
        logger.info("")
        logger.info("📋 PRIME 3 PARTITE:")
        logger.info("-"*60)
        
        for i, match in enumerate(matches[:3], 1):
            logger.info(f"\n{i}. {match.home_team} vs {match.away_team}")
            logger.info(f"   🏆 {match.league}")
            logger.info(f"   🕐 {match.time.strftime('%H:%M')}")
            
            if match.odds:
                logger.info(f"   💰 1X2: {match.odds.home_win:.2f} / {match.odds.draw:.2f} / {match.odds.away_win:.2f}")
                
                if match.odds.over_2_5 > 0:
                    logger.info(f"   📊 O/U 2.5: {match.odds.over_2_5:.2f} / {match.odds.under_2_5:.2f}")
            
            if match.home_stats and match.home_stats.league_position.position > 0:
                logger.info(f"   🏠 Pos casa: {match.home_stats.league_position.position}° ({match.home_stats.league_position.points} pt)")
            
            if match.away_stats and match.away_stats.league_position.position > 0:
                logger.info(f"   ✈️  Pos trasferta: {match.away_stats.league_position.position}° ({match.away_stats.league_position.points} pt)")
        
        logger.info("")
        logger.info("="*60)
        logger.info("✅ COMPLETATO CON SUCCESSO!")
        logger.info("="*60)
        logger.info("")
        
    except Exception as e:
        logger.error(f"❌ ERRORE: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
