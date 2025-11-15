"""
src/scraper/match_scraper.py - VERSIONE OTTIMIZZATA
Scraper modulare: match list + standings + statistics centralizzate
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Optional, Dict
import re
from pathlib import Path
import json

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.models.match_data import Match, MatchOdds, TeamStats, TeamStanding
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class MatchScraper:
    """Scraper ottimizzato con cache campionati"""
    
    BASE_URL = "https://tipsterarea.com"
    
    def __init__(self, config):
        self.config = config
        self.session = None
        self.semaphore = asyncio.Semaphore(config.max_concurrent_requests)
        
        # CACHE per evitare download ripetuti
        self.league_standings_cache = {}  # {league_key: standings_data}
        self.league_statistics_cache = {}  # {league_key: statistics_data}
        
    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=30)
        headers = {'User-Agent': self.config.user_agent}
        self.session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    # ========== STEP 1: SCARICA LISTA MATCH ==========
    
    async def get_matches_by_date(self, date: datetime) -> List[Match]:
        """Scarica lista partite (veloce, senza JavaScript)"""
        async with self:
            url = self._build_date_url(date)
            logger.info(f"📥 Scaricamento lista match: {url}")
            
            html = await self._fetch_page(url)
            if not html:
                logger.warning("❌ Nessun HTML ricevuto")
                return []
            
            matches = self._parse_matches_list(html, date)
            logger.info(f"✅ Estratte {len(matches)} partite da {len(set(m.league for m in matches))} campionati")
            
            return matches
    
    def _build_date_url(self, date: datetime) -> str:
        day = date.strftime("%d")
        month = date.strftime("%m")
        year = date.strftime("%Y")
        return f"{self.BASE_URL}/matches/date-{day}-{month}-{year}"
    
    async def _fetch_page(self, url: str) -> Optional[str]:
        """Download pagina con aiohttp + gestione errori"""
        async with self.semaphore:
            try:
                async with self.session.get(url) as response:
                    if response.status == 200:
                        return await response.text()
                    elif response.status == 410:
                        # 410 Gone = risorsa non disponibile (playoff, coppe, ecc.)
                        logger.debug(f"⚠️ Status 410 (Gone) per {url} - risorsa non disponibile")
                        return None
                    else:
                        logger.warning(f"⚠️ Status {response.status} per {url}")
                        return None
            except Exception as e:
                logger.error(f"❌ Errore download {url}: {e}")
                return None
    
    def _parse_matches_list(self, html: str, date: datetime) -> List[Match]:
        """Parser lista match con estrazione nome campionato"""
        soup = BeautifulSoup(html, 'html.parser')
        matches = []
        
        games_container = soup.find('div', id='games')
        if not games_container:
            logger.warning("❌ Container #games non trovato")
            return matches
        
        game_links = games_container.find_all('a', class_='game')
        logger.info(f"📊 Trovati {len(game_links)} link partite")
        
        current_league = "Unknown League"
        
        for game_link in game_links:
            # Estrai nome campionato dall'header precedente
            league_header = game_link.find_previous('div', class_='league-header')
            if league_header:
                league_span = league_header.find('span', class_='league-name')
                if league_span:
                    inner_span = league_span.find('span')
                    current_league = (inner_span or league_span).get_text(strip=True)
            
            try:
                match = self._parse_match_element(game_link, date, current_league)
                if match:
                    matches.append(match)
            except Exception as e:
                logger.error(f"❌ Errore parsing match: {e}")
        
        return matches
    
    def _parse_match_element(self, element, date: datetime, league: str) -> Optional[Match]:
        """Parse singolo elemento match"""
        try:
            href = element.get('href', '')
            if not href:
                return None
            
            match_url = self.BASE_URL + href if href.startswith('/') else href
            
            # Orario
            time_span = element.find('span', class_='time')
            time_str = time_span.get_text(strip=True) if time_span else "00:00"
            match_time = self._parse_time(time_str, date)
            
            # Squadre
            teams_span = element.find('span', class_='teams')
            home_team = "Unknown"
            away_team = "Unknown"
            
            if teams_span:
                home_span = teams_span.find('span', class_='home')
                if home_span:
                    inner = home_span.find('span')
                    home_team = (inner or home_span).get_text(strip=True)
                
                away_span = teams_span.find('span', class_='away')
                if away_span:
                    inner = away_span.find('span')
                    away_team = (inner or away_span).get_text(strip=True)
            
            home_team = self._clean_team_name(home_team)
            away_team = self._clean_team_name(away_team)
            
            # Quote base (dalla lista)
            odds = MatchOdds()
            odds_span = element.find('span', class_='odds')
            
            if odds_span and 'noodds' not in odds_span.get('class', []):
                try:
                    o1 = odds_span.find('span', class_='o1')
                    oX = odds_span.find('span', class_='oX')
                    o2 = odds_span.find('span', class_='o2')
                    
                    if o1 and o1.get_text(strip=True) != '-':
                        odds.home_win = float(o1.get_text(strip=True))
                    if oX and oX.get_text(strip=True) != '-':
                        odds.draw = float(oX.get_text(strip=True))
                    if o2 and o2.get_text(strip=True) != '-':
                        odds.away_win = float(o2.get_text(strip=True))
                    
                    if odds.home_win > 0:
                        odds.bookmakers_count = 1
                except:
                    pass
            
            match = Match(
                url=match_url,
                date=date,
                time=match_time,
                league=league,
                home_team=home_team,
                away_team=away_team,
                odds=odds
            )
            
            return match
            
        except Exception as e:
            logger.error(f"❌ Errore parsing match: {e}")
            return None
    
    def _clean_team_name(self, name: str) -> str:
        """Pulisce nome squadra"""
        if not name:
            return "Unknown"
        
        name = name.replace('**', '')
        name = ' '.join(name.split())
        name = re.sub(r'\s*\d+\s*-\s*\d+\s*', '', name)
        name = re.sub(r'\s*vs\s*', '', name, flags=re.IGNORECASE)
        
        return name.strip() or "Unknown"
    
    def _parse_time(self, time_str: str, date: datetime) -> datetime:
        """Parse orario"""
        try:
            time_str = re.sub(r'[^0-9:]', '', time_str)
            if ':' in time_str:
                parts = time_str.split(':')
                hour = int(parts[0])
                minute = int(parts[1])
                return date.replace(hour=hour, minute=minute, second=0)
        except:
            pass
        return date
    
    # ========== STEP 2: SCARICA DETTAGLI COMPLETI ==========
    
    async def get_matches_details(self, matches: List[Match]) -> List[Match]:
        """
        Arricchisce match con standings + statistics centralizzate
        OTTIMIZZAZIONE: scarica standings/statistics UNA VOLTA per campionato
        """
        async with self:
            # 1. Identifica campionati unici
            unique_leagues = list(set(m.league for m in matches))
            logger.info(f"📊 Campionati unici: {len(unique_leagues)}")
            
            # 2. Scarica standings + statistics per ogni campionato
            for league_name in unique_leagues:
                league_key = self._league_name_to_key(league_name)
                
                logger.info(f"🏆 Scaricamento dati per: {league_name} [{league_key}]")
                
                # Standings (ora ritorna dict con overall/home/away)
                standings_data = await self._fetch_league_standings(league_key)
                if standings_data:
                    self.league_standings_cache[league_key] = standings_data
                    overall_count = len(standings_data.get('overall', []))
                    home_count = len(standings_data.get('home', []))
                    away_count = len(standings_data.get('away', []))
                    logger.info(f"✅ Standings: {overall_count} squadre (Home: {home_count}, Away: {away_count})")
                
                # Statistics
                statistics = await self._fetch_league_statistics(league_key)
                if statistics:
                    self.league_statistics_cache[league_key] = statistics
                    logger.info(f"✅ Statistics: {len(statistics)} metriche")
            
            # 3. Arricchisci ogni match con dati cache
            detailed_matches = []
            for i, match in enumerate(matches, 1):
                try:
                    enriched = await self._enrich_match(match)
                    detailed_matches.append(enriched)
                    
                    if i % 10 == 0:
                        logger.info(f"📈 Processati {i}/{len(matches)} match")
                except Exception as e:
                    logger.error(f"❌ Errore arricchimento {match.home_team} vs {match.away_team}: {e}")
                    detailed_matches.append(match)
            
            logger.info(f"✅ Completato: {len(detailed_matches)} match arricchiti")
            
            # IMPORTANTE: Esporta cache PRIMA di chiudere il context manager
            self.export_league_data()
            
            return detailed_matches
    
    def _league_name_to_key(self, league_name: str) -> str:
        """
        Converte nome campionato in chiave URL
        "England - Premier League" -> "england/premier-league"
        "Italy - Serie C - Group B" -> "italy/serie-c-group-b"
        """
        league_name = league_name.strip()
        
        # Split su " - " (può essere multiplo per gironi)
        parts = league_name.split(' - ')
        
        if len(parts) < 2:
            logger.warning(f"⚠️ Formato campionato inaspettato: {league_name}")
            return league_name.lower().replace(' ', '-')
        
        # Primo elemento = paese
        country = parts[0].strip().lower().replace(' ', '-')
        
        # Resto = nome campionato (unito con -)
        league = '-'.join(p.strip().lower().replace(' ', '-') for p in parts[1:])
        
        return f"{country}/{league}"
    
    # ========== FETCH STANDINGS ==========
    
    async def _fetch_league_standings(self, league_key: str) -> Optional[Dict]:
        """Scarica classifica completa del campionato (generale + casa + trasferta)"""
        url = f"{self.BASE_URL}/standings/{league_key}"
        
        html = await self._fetch_page(url)
        if not html:
            return None
        
        # DEBUG: Salva HTML
        self._save_debug_html(html, f"standings_{league_key.replace('/', '_')}.html")
        
        return self._parse_standings_page_full(html)
    
    def _parse_standings_page_full(self, html: str) -> Dict:
        """Parser pagina standings - ritorna dict con overall/home/away"""
        soup = BeautifulSoup(html, 'html.parser')
        
        result = {
            'overall': [],
            'home': [],
            'away': []
        }
        
        # CERCA TUTTE LE TABELLE STANDING
        standing_tables = soup.find_all('table', class_='standing')
        
        if not standing_tables:
            logger.warning("❌ Nessuna tabella 'standing' trovata")
            return result
        
        logger.info(f"✅ Trovate {len(standing_tables)} tabelle standing")
        
        # Identifica quale tabella è quale
        for i, table in enumerate(standing_tables):
            # Cerca heading prima della tabella
            prev_elements = table.find_all_previous(['h1', 'h2', 'h3', 'h4'], limit=5)
            
            table_type = None
            
            # Controlla heading
            for elem in prev_elements:
                text = elem.get_text(strip=True).lower()
                
                if 'home standing' in text or 'home table' in text:
                    table_type = 'home'
                    break
                elif 'away standing' in text or 'away table' in text:
                    table_type = 'away'
                    break
            
            # Se non ha heading specifico, usa posizione
            if table_type is None:
                if i == 0:
                    table_type = 'overall'  # Prima tabella = overall
                elif i == 1:
                    table_type = 'home'     # Seconda = home (se non già identificata)
                elif i == 2:
                    table_type = 'away'     # Terza = away (se non già identificata)
                else:
                    table_type = 'overall'  # Fallback
            
            # Parse tabella
            standings = self._parse_single_standing_table(table)
            
            # Aggiungi solo se non già popolato (evita duplicati)
            if not result[table_type]:
                result[table_type] = standings
                logger.info(f"  - {table_type.upper()}: {len(standings)} squadre")
            else:
                logger.debug(f"  - Ignorata duplicato {table_type.upper()}")
        
        return result
    
    def _parse_standings_page(self, html: str) -> List[Dict]:
        """Parser pagina standings - estrae TUTTE le classifiche (generale + casa + trasferta)"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Struttura risultato
        result = {
            'overall': [],
            'home': [],
            'away': []
        }
        
        # CERCA TUTTE LE TABELLE STANDING
        standing_tables = soup.find_all('table', class_='standing')
        
        if not standing_tables:
            logger.warning("❌ Nessuna tabella 'standing' trovata")
            return result['overall']
        
        logger.info(f"✅ Trovate {len(standing_tables)} tabelle standing")
        
        # Identifica quale tabella è quale
        for table in standing_tables:
            # Cerca heading prima della tabella
            prev_elements = table.find_all_previous(['h2', 'h3', 'div', 'p'], limit=5)
            
            table_type = 'overall'  # Default
            
            for elem in prev_elements:
                text = elem.get_text(strip=True).lower()
                
                if 'home standing' in text or 'home table' in text:
                    table_type = 'home'
                    break
                elif 'away standing' in text or 'away table' in text:
                    table_type = 'away'
                    break
            
            # Parse tabella
            standings = self._parse_single_standing_table(table)
            result[table_type] = standings
            
            logger.info(f"  - {table_type.upper()}: {len(standings)} squadre")
        
        # Ritorna classifica generale (per compatibilità)
        return result['overall']
    
    def _parse_single_standing_table(self, table) -> List[Dict]:
        """Parser singola tabella standing"""
        standings = []
        
        tbody = table.find('tbody')
        if not tbody:
            return standings
        
        for row in tbody.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) < 10:
                continue
            
            try:
                team_data = {
                    'position': int(cells[0].get_text(strip=True)),
                    'team': cells[1].get_text(strip=True),
                    'matches_played': int(cells[2].get_text(strip=True)),
                    'wins': int(cells[3].get_text(strip=True)),
                    'draws': int(cells[4].get_text(strip=True)),
                    'losses': int(cells[5].get_text(strip=True)),
                    'goals_for': int(cells[6].get_text(strip=True)),
                    'goals_against': int(cells[7].get_text(strip=True)),
                    'goal_difference': int(cells[8].get_text(strip=True)),
                    'points': int(cells[9].get_text(strip=True))
                }
                standings.append(team_data)
            except Exception as e:
                logger.debug(f"⚠️ Errore parsing riga: {e}")
        
        return standings
    
    # ========== FETCH STATISTICS ==========
    
    def _parse_standings_page(self, html: str) -> List[Dict]:
        """Parser pagina standings"""
        soup = BeautifulSoup(html, 'html.parser')
        standings = []
        
        # Cerca tabella classifica
        standing_table = soup.find('table', class_='standing')
        
        if not standing_table:
            logger.warning("❌ Tabella 'standing' non trovata")
            return standings
        
        tbody = standing_table.find('tbody')
        if not tbody:
            logger.warning("❌ Tbody non trovato in standing")
            return standings
        
        for row in tbody.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) < 10:
                continue
            
            try:
                team_data = {
                    'position': int(cells[0].get_text(strip=True)),
                    'team': cells[1].get_text(strip=True),
                    'matches_played': int(cells[2].get_text(strip=True)),
                    'wins': int(cells[3].get_text(strip=True)),
                    'draws': int(cells[4].get_text(strip=True)),
                    'losses': int(cells[5].get_text(strip=True)),
                    'goals_for': int(cells[6].get_text(strip=True)),
                    'goals_against': int(cells[7].get_text(strip=True)),
                    'goal_difference': int(cells[8].get_text(strip=True)),
                    'points': int(cells[9].get_text(strip=True))
                }
                standings.append(team_data)
            except Exception as e:
                logger.warning(f"⚠️ Errore parsing riga standing: {e}")
        
        logger.info(f"✅ Parsed {len(standings)} teams da standings")
        return standings
    
    # ========== FETCH STATISTICS ==========
    
    async def _fetch_league_statistics(self, league_key: str) -> Optional[Dict]:
        """Scarica statistiche campionato"""
        url = f"{self.BASE_URL}/statistics/{league_key}"
        
        html = await self._fetch_page(url)
        if not html:
            return None
        
        # DEBUG: Salva HTML
        self._save_debug_html(html, f"statistics_{league_key.replace('/', '_')}.html")
        
        return self._parse_statistics_page(html)
    
    def _parse_statistics_page(self, html: str) -> Dict:
        """Parser pagina statistics - gestisce entrambe le versioni HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        stats = {}
        
        # VERSIONE 1: Nuovo sito (class="league-stat-summary")
        new_tables = soup.find_all('table', class_='league-stat-summary')
        
        # VERSIONE 2: Vecchio sito (id="leagueStatSummary")
        old_container = soup.find('table', id='leagueStatSummary')
        old_tables = old_container.find_all('table', class_='leagueStatSummaryTable') if old_container else []
        
        # Usa la versione trovata
        sub_tables = new_tables if new_tables else old_tables
        
        if not sub_tables:
            logger.warning("❌ Nessuna tabella statistics trovata (né nuova né vecchia versione)")
            return stats
        
        logger.info(f"✅ Trovate {len(sub_tables)} tabelle statistics")
        
        # PARSING UNIFICATO (funziona per entrambe le versioni)
        for table in sub_tables:
            # Header (th)
            thead = table.find('thead')
            if thead:
                header_cells = thead.find_all('th')
                if len(header_cells) >= 2:
                    header_label = header_cells[0].get_text(strip=True).lower()
                    header_value = header_cells[1].get_text(strip=True)
                    
                    # Completed
                    if 'completed' in header_label:
                        try:
                            stats['completed_percentage'] = float(header_value.replace('%', ''))
                        except:
                            pass
                    
                    # Played
                    elif 'played' in header_label:
                        try:
                            stats['finished'] = int(header_value)
                        except:
                            pass
            
            # Body (td)
            tbody = table.find('tbody')
            if not tbody:
                continue
            
            for row in tbody.find_all('tr'):
                cells = row.find_all('td')
                if len(cells) < 2:
                    continue
                
                label = cells[0].get_text(strip=True).lower()
                value = cells[1].get_text(strip=True)
                
                # PARSING VALORI
                
                # Matches
                if label == 'matches':
                    try:
                        stats['total_matches'] = int(value)
                    except:
                        pass
                
                # Finished
                elif label == 'finished':
                    try:
                        stats['finished'] = int(value)
                    except:
                        pass
                
                # Remaining
                elif label == 'remaining':
                    try:
                        stats['remaining'] = int(value)
                    except:
                        pass
                
                # Home Win
                elif label == 'home win':
                    try:
                        stats['home_win_pct'] = float(value.replace('%', ''))
                    except:
                        pass
                
                # Draw
                elif label == 'draw':
                    try:
                        stats['draw_pct'] = float(value.replace('%', ''))
                    except:
                        pass
                
                # Away Win
                elif label == 'away win':
                    try:
                        stats['away_win_pct'] = float(value.replace('%', ''))
                    except:
                        pass
                
                # Average (goals)
                elif label == 'average':
                    try:
                        stats['avg_goals'] = float(value)
                    except:
                        pass
                
                # Home Team (avg goals)
                elif label == 'home team':
                    try:
                        stats['avg_home_goals'] = float(value)
                    except:
                        pass
                
                # Away Team (avg goals)
                elif label == 'away team':
                    try:
                        stats['avg_away_goals'] = float(value)
                    except:
                        pass
                
                # BTS (può essere "Goal/Goal" o "BTS")
                elif 'goal/goal' in label or label == 'bts':
                    try:
                        stats['bts_pct'] = float(value.replace('%', ''))
                    except:
                        pass
        
        # PARSING TABELLA OVER/UNDER
        for table in sub_tables:
            thead = table.find('thead')
            if not thead:
                continue
            
            header_cells = thead.find_all('th')
            
            # Cerca tabella con 3 colonne: Goals | Under | Over
            if len(header_cells) == 3:
                header_texts = [th.get_text(strip=True).lower() for th in header_cells]
                
                if 'under' in header_texts and 'over' in header_texts:
                    tbody = table.find('tbody')
                    if tbody:
                        stats['over_under'] = {}
                        
                        for row in tbody.find_all('tr'):
                            cells = row.find_all('td')
                            if len(cells) >= 3:
                                threshold = cells[0].get_text(strip=True).strip()
                                under_val = cells[1].get_text(strip=True).replace('%', '')
                                over_val = cells[2].get_text(strip=True).replace('%', '')
                                
                                try:
                                    stats['over_under'][threshold] = {
                                        'under': float(under_val),
                                        'over': float(over_val)
                                    }
                                except:
                                    pass
        
        logger.info(f"✅ Estratte {len(stats)} metriche: {list(stats.keys())}")
        return stats
    
    # ========== ARRICCHIMENTO MATCH ==========
    
    async def _enrich_match(self, match: Match) -> Match:
        """Arricchisce match con dati da cache campionato"""
        league_key = self._league_name_to_key(match.league)
        
        # 1. STANDINGS (con casa/trasferta)
        standings_data = self.league_standings_cache.get(league_key, {})
        
        if isinstance(standings_data, dict):
            # Nuovo formato con overall/home/away
            overall = standings_data.get('overall', [])
            home_standings = standings_data.get('home', [])
            away_standings = standings_data.get('away', [])
        else:
            # Vecchio formato (solo overall)
            overall = standings_data
            home_standings = []
            away_standings = []
        
        match.league_standings = overall
        
        # Estrai standing specifico per home/away team
        for team_data in overall:
            team_name = team_data['team'].lower()
            
            if match.home_team.lower() in team_name or team_name in match.home_team.lower():
                match.home_standing = TeamStanding(
                    position=team_data['position'],
                    team_name=team_data['team'],
                    matches_played=team_data['matches_played'],
                    wins=team_data['wins'],
                    draws=team_data['draws'],
                    losses=team_data['losses'],
                    goals_for=team_data['goals_for'],
                    goals_against=team_data['goals_against'],
                    goal_difference=team_data['goal_difference'],
                    points=team_data['points']
                )
                
                # CREA home_stats con gol TOTALI da classifica overall
                if not match.home_stats:
                    match.home_stats = TeamStats()
                
                match.home_stats.goals_for = team_data['goals_for']
                match.home_stats.goals_against = team_data['goals_against']
            
            elif match.away_team.lower() in team_name or team_name in match.away_team.lower():
                match.away_standing = TeamStanding(
                    position=team_data['position'],
                    team_name=team_data['team'],
                    matches_played=team_data['matches_played'],
                    wins=team_data['wins'],
                    draws=team_data['draws'],
                    losses=team_data['losses'],
                    goals_for=team_data['goals_for'],
                    goals_against=team_data['goals_against'],
                    goal_difference=team_data['goal_difference'],
                    points=team_data['points']
                )
                
                # CREA away_stats con gol TOTALI da classifica overall
                if not match.away_stats:
                    match.away_stats = TeamStats()
                
                match.away_stats.goals_for = team_data['goals_for']
                match.away_stats.goals_against = team_data['goals_against']
        
        # CREA TeamStats da standings casa/trasferta
        if home_standings:
            for team_data in home_standings:
                team_name = team_data['team'].lower()
                
                if match.home_team.lower() in team_name or team_name in match.home_team.lower():
                    # Crea home_stats se non esiste
                    if not match.home_stats:
                        match.home_stats = TeamStats()
                    
                    # Crea home_stats (stats in casa)
                    if not match.home_stats.home_stats:
                        match.home_stats.home_stats = TeamStats()
                    
                    match.home_stats.home_stats.goals_for = team_data['goals_for']
                    match.home_stats.home_stats.goals_against = team_data['goals_against']
                    match.home_stats.home_stats.wins = team_data['wins']
                    match.home_stats.home_stats.draws = team_data['draws']
                    match.home_stats.home_stats.losses = team_data['losses']
                    
                    # 🔍 DEBUG
                    logger.info(f"🎯 {match.home_team}: home_stats.home_stats.goals_for = {team_data['goals_for']}")
                    break
        
        if away_standings:
            for team_data in away_standings:
                team_name = team_data['team'].lower()
                
                if match.away_team.lower() in team_name or team_name in match.away_team.lower():
                    # Crea away_stats se non esiste
                    if not match.away_stats:
                        match.away_stats = TeamStats()
                    
                    # Crea away_stats (stats in trasferta)
                    if not match.away_stats.away_stats:
                        match.away_stats.away_stats = TeamStats()
                    
                    match.away_stats.away_stats.goals_for = team_data['goals_for']
                    match.away_stats.away_stats.goals_against = team_data['goals_against']
                    match.away_stats.away_stats.wins = team_data['wins']
                    match.away_stats.away_stats.draws = team_data['draws']
                    match.away_stats.away_stats.losses = team_data['losses']
                    
                    # 🔍 DEBUG
                    logger.info(f"🎯 {match.away_team}: away_stats.away_stats.goals_for = {team_data['goals_for']}")
                    break
        
        # 2. STATISTICS
        statistics = self.league_statistics_cache.get(league_key, {})
        if statistics:
            match.league_statistics = statistics
        
        # 3. SCARICA QUOTE DETTAGLIATE + LAST MATCHES dalla pagina singola
        match = await self._fetch_match_page_details(match)
        
        return match
    
    async def _fetch_match_page_details(self, match: Match) -> Match:
        """
        Scarica SOLO quote dettagliate + last matches dalla pagina singola
        (NO Playwright, NO statistics/standings ridondanti)
        """
        html = await self._fetch_page(match.url)
        if not html:
            return match
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Quote dettagliate
        match.odds = self._extract_all_odds(soup)
        
        # Last matches (senza outcome/quote se non servono)
        match.home_last_matches = self._extract_last_matches(soup, 'home')
        match.away_last_matches = self._extract_last_matches(soup, 'away')
        
        # Head to Head
        match.head_to_head = self._extract_head_to_head(soup)
        
        return match
    
    # ========== PARSING ODDS ==========
    
    def _extract_all_odds(self, soup) -> MatchOdds:
        """Estrae tutte le quote dalla pagina singola"""
        odds = MatchOdds()
        
        try:
            odds_tables = soup.find_all('table', class_='odds')
            
            for table in odds_tables:
                thead = table.find('thead')
                if not thead:
                    continue
                
                odds_type_th = thead.find('th', class_='odds-type')
                if not odds_type_th:
                    continue
                
                market_type = odds_type_th.get_text(strip=True).lower()
                tbody = table.find('tbody')
                if not tbody:
                    continue
                
                # Cerca riga bwin (o prima riga)
                bwin_row = None
                for row in tbody.find_all('tr'):
                    img = row.find('img', class_='bookie')
                    if img and 'bwin' in img.get('alt', '').lower():
                        bwin_row = row
                        break
                
                if not bwin_row:
                    bwin_row = tbody.find('tr')
                
                if not bwin_row:
                    continue
                
                # Parse in base al tipo di mercato
                if 'standard 1x2' in market_type or '1x2' in market_type:
                    self._parse_1x2_odds(bwin_row, odds)
                elif 'double chance' in market_type:
                    self._parse_double_chance(bwin_row, odds)
                elif 'over/under' in market_type:
                    self._parse_over_under(tbody, odds)
                elif 'bts' in market_type or 'both teams' in market_type:
                    self._parse_bts(bwin_row, odds)
        
        except Exception as e:
            logger.error(f"❌ Errore estrazione quote: {e}")
        
        return odds
    
    def _parse_1x2_odds(self, row, odds: MatchOdds):
        try:
            cells = row.find_all('td', class_='odd')
            if len(cells) >= 3:
                odds.home_win = float(cells[0].get_text(strip=True))
                odds.draw = float(cells[1].get_text(strip=True))
                odds.away_win = float(cells[2].get_text(strip=True))
        except:
            pass
    
    def _parse_double_chance(self, row, odds: MatchOdds):
        try:
            cells = row.find_all('td', class_='odd')
            if len(cells) >= 3:
                odds.dc_1x = float(cells[0].get_text(strip=True))
                odds.dc_12 = float(cells[1].get_text(strip=True))
                odds.dc_x2 = float(cells[2].get_text(strip=True))
        except:
            pass
    
    def _parse_over_under(self, tbody, odds: MatchOdds):
        try:
            for row in tbody.find_all('tr'):
                cells = row.find_all('td')
                if len(cells) < 4:
                    continue
                
                img = cells[0].find('img')
                if not (img and 'bwin' in img.get('alt', '').lower()):
                    continue
                
                threshold = cells[1].get_text(strip=True)
                under = float(cells[2].get_text(strip=True))
                over = float(cells[3].get_text(strip=True))
                
                if '1.5' in threshold:
                    odds.under_1_5 = under
                    odds.over_1_5 = over
                elif '2.5' in threshold:
                    odds.under_2_5 = under
                    odds.over_2_5 = over
                elif '3.5' in threshold:
                    odds.under_3_5 = under
                    odds.over_3_5 = over
        except:
            pass
    
    def _parse_bts(self, row, odds: MatchOdds):
        try:
            cells = row.find_all('td', class_='odd')
            if len(cells) >= 2:
                odds.bts_yes = float(cells[0].get_text(strip=True))
                odds.bts_no = float(cells[1].get_text(strip=True))
        except:
            pass
    
    # ========== PARSING LAST MATCHES ==========
    
    def _extract_last_matches(self, soup, team_type: str) -> List[Dict]:
        """Estrae ultimi match (semplificato)"""
        results = []
        
        try:
            all_tables = soup.find_all('table', class_='games-stat')
            target_idx = 0 if team_type == 'home' else 1
            
            if len(all_tables) > target_idx:
                tbody = all_tables[target_idx].find('tbody')
                
                if tbody:
                    for row in tbody.find_all('tr')[:10]:
                        cells = row.find_all('td')
                        if len(cells) < 5:
                            continue
                        
                        result_cell = cells[3]
                        outcome = 'D'
                        if 'win' in result_cell.get('class', []):
                            outcome = 'W'
                        elif 'loss' in result_cell.get('class', []):
                            outcome = 'L'
                        
                        match_data = {
                            'date': cells[0].get_text(strip=True),
                            'competition': cells[1].get_text(strip=True),
                            'home_team': cells[2].get_text(strip=True),
                            'score': result_cell.get_text(strip=True),
                            'away_team': cells[4].get_text(strip=True),
                            'outcome': outcome
                        }
                        
                        results.append(match_data)
        except Exception as e:
            logger.error(f"❌ Errore estrazione last matches: {e}")
        
        return results
    
    def _extract_head_to_head(self, soup) -> List[Dict]:
        """Estrae head to head (semplificato)"""
        h2h_matches = []
        
        try:
            all_tables = soup.find_all('table', class_='games-stat')
            
            # H2H è tipicamente la terza tabella
            h2h_table = None
            for table in all_tables:
                prev = table.find_previous(['h2', 'div'])
                if prev and 'head to head' in prev.get_text(strip=True).lower():
                    h2h_table = table
                    break
            
            if not h2h_table and len(all_tables) >= 3:
                h2h_table = all_tables[2]
            
            if not h2h_table:
                return h2h_matches
            
            tbody = h2h_table.find('tbody')
            if not tbody:
                return h2h_matches
            
            for row in tbody.find_all('tr')[:10]:
                cells = row.find_all('td')
                if len(cells) < 5:
                    continue
                
                result_cell = cells[3]
                outcome = 'D'
                if 'win' in result_cell.get('class', []):
                    outcome = 'W'
                elif 'loss' in result_cell.get('class', []):
                    outcome = 'L'
                
                match_data = {
                    'date': cells[0].get_text(strip=True),
                    'competition': cells[1].get_text(strip=True),
                    'home_team': cells[2].get_text(strip=True),
                    'score': result_cell.get_text(strip=True),
                    'away_team': cells[4].get_text(strip=True),
                    'outcome': outcome
                }
                
                h2h_matches.append(match_data)
        
        except Exception as e:
            logger.error(f"❌ Errore estrazione H2H: {e}")
        
        return h2h_matches
    
    # ========== UTILITY ==========
    
    def _save_debug_html(self, html: str, filename: str):
        """Salva HTML per debug"""
        try:
            debug_dir = Path("debug_html")
            debug_dir.mkdir(exist_ok=True)
            
            filepath = debug_dir / filename
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html)
            
            logger.info(f"💾 HTML salvato: {filepath}")
        except Exception as e:
            logger.warning(f"⚠️ Impossibile salvare HTML debug: {e}")
    
    # ========== EXPORT CACHE ==========
    
    def export_league_data(self, output_dir: str = "league_data"):
        """Esporta dati campionati in JSON per analisi"""
        try:
            output_path = Path(output_dir)
            output_path.mkdir(exist_ok=True)
            
            # Export standings
            standings_file = output_path / "standings_cache.json"
            with open(standings_file, 'w', encoding='utf-8') as f:
                json.dump(self.league_standings_cache, f, indent=2, ensure_ascii=False)
            logger.info(f"📊 Standings esportate: {standings_file}")
            logger.info(f"   Campionati: {len(self.league_standings_cache)}")
            
            # Export statistics
            stats_file = output_path / "statistics_cache.json"
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.league_statistics_cache, f, indent=2, ensure_ascii=False)
            logger.info(f"📊 Statistics esportate: {stats_file}")
            logger.info(f"   Campionati: {len(self.league_statistics_cache)}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"❌ Errore export dati campionati: {e}")
            import traceback
            traceback.print_exc()
            return None