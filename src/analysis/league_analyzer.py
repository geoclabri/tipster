"""
src/analysis/league_analyzer.py
Analizzatore statistiche campionato - VERSIONE SEMPLIFICATA
Ora la maggior parte dell'analisi è fatta direttamente in prediction_engine
"""

from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class LeagueStats:
    """Statistiche aggregate di un campionato"""
    
    league_name: str
    total_matches: int
    
    # Medie generali
    avg_goals_per_match: float
    avg_home_goals: float
    avg_away_goals: float
    
    # Percentuali risultati
    home_win_percentage: float
    draw_percentage: float
    away_win_percentage: float
    
    # Percentuali mercati
    over_0_5_percentage: float
    over_1_5_percentage: float
    over_2_5_percentage: float
    over_3_5_percentage: float
    bts_percentage: float
    
    # Forza campionato
    avg_home_advantage: float
    league_competitiveness: float
    
    # Classifica completa
    standings: List[Dict]


class LeagueAnalyzer:
    """
    Analizzatore campionati - WRAPPER SEMPLIFICATO
    
    Ora i dati del campionato arrivano già estratti in match.league_statistics
    Questo modulo serve solo per compatibilità con codice esistente
    """
    
    def __init__(self):
        self.league_cache = {}
    
    def analyze_league(self, matches: List, league_name: str) -> Optional[LeagueStats]:
        """
        Analizza campionato
        
        Mantenuto per compatibilità con codice esistente
        """
        
        league_matches = [m for m in matches if m.league == league_name]
        
        if not league_matches:
            return None
        
        # Prova a usare league_statistics del primo match
        first_match = league_matches[0]
        if first_match.league_statistics:
            return self._from_league_statistics(
                first_match.league_statistics, 
                league_name,
                first_match.league_standings or []
            )
        
        # Fallback: calcolo manuale (meno accurato)
        return self._calculate_league_stats_fallback(league_matches, league_name)
    
    def _from_league_statistics(
        self, stats: Dict, league_name: str, standings: List[Dict]
    ) -> LeagueStats:
        """Converte league_statistics in LeagueStats"""
        
        avg_goals = stats.get('avg_goals', 2.6)
        avg_home = stats.get('avg_home_goals', 1.4)
        avg_away = stats.get('avg_away_goals', 1.2)
        
        home_win_pct = stats.get('home_win_pct', 45.0)
        draw_pct = stats.get('draw_pct', 27.0)
        away_win_pct = stats.get('away_win_pct', 28.0)
        
        # Over/Under
        over_under = stats.get('over_under', {})
        over_0_5 = over_under.get('0.5', {}).get('over', 90.0)
        over_1_5 = over_under.get('1.5', {}).get('over', 75.0)
        over_2_5 = over_under.get('2.5', {}).get('over', 50.0)
        over_3_5 = over_under.get('3.5', {}).get('over', 25.0)
        
        bts_pct = stats.get('bts_pct', 50.0)
        
        total_matches = stats.get('total_matches', 0)
        
        # Home advantage
        home_advantage = avg_home - avg_away if avg_home > 0 and avg_away > 0 else 0.2
        
        # Competitiveness
        if total_matches > 0:
            variance = ((home_win_pct - 33.3)**2 + (draw_pct - 33.3)**2 + (away_win_pct - 33.3)**2) / 3
            competitiveness = 1 - (variance / 1000)
            competitiveness = max(0, min(1, competitiveness))
        else:
            competitiveness = 0.5
        
        return LeagueStats(
            league_name=league_name,
            total_matches=total_matches,
            avg_goals_per_match=avg_goals,
            avg_home_goals=avg_home,
            avg_away_goals=avg_away,
            home_win_percentage=home_win_pct,
            draw_percentage=draw_pct,
            away_win_percentage=away_win_pct,
            over_0_5_percentage=over_0_5,
            over_1_5_percentage=over_1_5,
            over_2_5_percentage=over_2_5,
            over_3_5_percentage=over_3_5,
            bts_percentage=bts_pct,
            avg_home_advantage=home_advantage,
            league_competitiveness=competitiveness,
            standings=standings
        )
    
    def _calculate_league_stats_fallback(self, matches: List, league_name: str) -> LeagueStats:
        """Calcolo fallback se league_statistics non disponibile"""
        
        total = len(matches)
        
        # Medie stimate da statistiche squadre
        total_goals = 0
        home_goals = 0
        away_goals = 0
        count = 0
        
        for match in matches:
            if match.home_stats and match.away_stats:
                est_home = match.home_stats.avg_goals_scored
                est_away = match.away_stats.avg_goals_scored
                
                total_goals += est_home + est_away
                home_goals += est_home
                away_goals += est_away
                count += 1
        
        avg_goals = total_goals / count if count > 0 else 2.6
        avg_home = home_goals / count if count > 0 else 1.4
        avg_away = away_goals / count if count > 0 else 1.2
        
        # Standings
        standings_dict = {}
        for match in matches:
            if match.home_standing:
                standings_dict[match.home_standing.team_name] = {
                    'team': match.home_standing.team_name,
                    'position': match.home_standing.position,
                    'points': match.home_standing.points,
                    'played': match.home_standing.matches_played,
                    'wins': match.home_standing.wins,
                    'draws': match.home_standing.draws,
                    'losses': match.home_standing.losses,
                    'gf': match.home_standing.goals_for,
                    'ga': match.home_standing.goals_against,
                    'gd': match.home_standing.goal_difference
                }
        
        standings_list = sorted(
            standings_dict.values(),
            key=lambda x: (x['points'], x['gd']),
            reverse=True
        )
        
        return LeagueStats(
            league_name=league_name,
            total_matches=total,
            avg_goals_per_match=avg_goals,
            avg_home_goals=avg_home,
            avg_away_goals=avg_away,
            home_win_percentage=45.0,
            draw_percentage=27.0,
            away_win_percentage=28.0,
            over_0_5_percentage=90.0,
            over_1_5_percentage=75.0,
            over_2_5_percentage=50.0,
            over_3_5_percentage=25.0,
            bts_percentage=50.0,
            avg_home_advantage=avg_home - avg_away,
            league_competitiveness=0.5,
            standings=standings_list
        )
    
    def get_league_adjustment_factors(self, league_stats: LeagueStats) -> Dict[str, float]:
        """
        Calcola fattori di aggiustamento per le predizioni
        (Deprecato - ora fatto in prediction_engine)
        """
        
        goal_factor = league_stats.avg_goals_per_match / 2.5
        home_factor = league_stats.avg_home_advantage / 0.3
        draw_factor = league_stats.draw_percentage / 27
        unpredictability = league_stats.league_competitiveness
        
        return {
            'goal_factor': goal_factor,
            'home_advantage_factor': home_factor,
            'draw_factor': draw_factor,
            'unpredictability': unpredictability,
            'over_2_5_baseline': league_stats.over_2_5_percentage / 100,
            'bts_baseline': league_stats.bts_percentage / 100
        }
    
    def format_standings_table(
        self, 
        league_stats: LeagueStats, 
        home_team: str, 
        away_team: str,
        max_teams: int = 20
    ) -> str:
        """
        Formatta classifica completa con evidenziazione squadre
        """
        
        if not league_stats.standings:
            return "Classifica non disponibile\n"
        
        text = ""
        text += "Pos  Team                          Pts  P   W  D  L   GF  GA  GD\n"
        text += "─" * 70 + "\n"
        
        for i, team in enumerate(league_stats.standings[:max_teams], 1):
            # Marker per squadre del match
            marker = ""
            if team['team'].lower() in home_team.lower() or home_team.lower() in team['team'].lower():
                marker = "► "
            elif team['team'].lower() in away_team.lower() or away_team.lower() in team['team'].lower():
                marker = "► "
            else:
                marker = "  "
            
            # Formato riga
            team_name = team['team'][:28]  # Tronca se troppo lungo
            
            text += f"{marker}{i:2}. {team_name:28} {team['points']:3} "
            text += f"{team['played']:2}  {team['wins']:2} {team['draws']:2} {team['losses']:2}  "
            text += f"{team['gf']:3} {team['ga']:3} {team['gd']:+3}\n"
        
        return text
