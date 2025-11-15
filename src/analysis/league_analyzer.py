"""
src/analysis/league_analyzer.py
Analizzatore statistiche campionato e classifica completa
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
from collections import defaultdict


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
    avg_home_advantage: float  # Differenza gol casa vs trasferta
    league_competitiveness: float  # Varianza punti (0-1, più alto = più equilibrato)
    
    # Classifica completa
    standings: List[Dict]  # Lista squadre ordinate per punti


class LeagueAnalyzer:
    """Analizza campionati e genera statistiche aggregate"""
    
    def __init__(self):
        self.league_cache = {}  # Cache statistiche per campionato
    
    def analyze_league(self, matches: List, league_name: str) -> Optional[LeagueStats]:
        """
        Analizza tutte le partite di un campionato
        
        Args:
            matches: Lista di Match dello stesso campionato
            league_name: Nome del campionato
            
        Returns:
            LeagueStats con tutte le statistiche
        """
        
        # Filtra solo partite del campionato richiesto
        league_matches = [m for m in matches if m.league == league_name]
        
        if not league_matches:
            return None
        
        # Usa cache se disponibile
        cache_key = f"{league_name}_{len(league_matches)}"
        if cache_key in self.league_cache:
            return self.league_cache[cache_key]
        
        # Calcola statistiche
        stats = self._calculate_league_stats(league_matches, league_name)
        
        # Salva in cache
        self.league_cache[cache_key] = stats
        
        return stats
    
    def _calculate_league_stats(self, matches: List, league_name: str) -> LeagueStats:
        """Calcola tutte le statistiche del campionato"""
        
        total_matches = len(matches)
        
        # Raccogli dati da tutte le partite
        total_goals = 0
        home_goals = 0
        away_goals = 0
        
        home_wins = 0
        draws = 0
        away_wins = 0
        
        over_counts = {0.5: 0, 1.5: 0, 2.5: 0, 3.5: 0}
        bts_count = 0
        
        # Raccogli standings (usa prima partita con standings completi)
        standings_dict = {}
        
        for match in matches:
            # Stats dai dati aggregati delle squadre
            if match.home_stats and match.away_stats:
                # Stima gol dalla media
                est_home_goals = match.home_stats.avg_goals_scored
                est_away_goals = match.away_stats.avg_goals_scored
                
                total_goals += est_home_goals + est_away_goals
                home_goals += est_home_goals
                away_goals += est_away_goals
                
                total_match_goals = est_home_goals + est_away_goals
                
                # Over/Under
                if total_match_goals > 0.5:
                    over_counts[0.5] += 1
                if total_match_goals > 1.5:
                    over_counts[1.5] += 1
                if total_match_goals > 2.5:
                    over_counts[2.5] += 1
                if total_match_goals > 3.5:
                    over_counts[3.5] += 1
                
                # BTS (se entrambe le medie > 0.5)
                if est_home_goals > 0.5 and est_away_goals > 0.5:
                    bts_count += 1
                
                # 1X2 (stima da medie)
                if est_home_goals > est_away_goals + 0.3:
                    home_wins += 1
                elif abs(est_home_goals - est_away_goals) <= 0.3:
                    draws += 1
                else:
                    away_wins += 1
            
            # Raccogli standings
            if match.home_standing and match.home_standing.team_name:
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
            
            if match.away_standing and match.away_standing.team_name:
                standings_dict[match.away_standing.team_name] = {
                    'team': match.away_standing.team_name,
                    'position': match.away_standing.position,
                    'points': match.away_standing.points,
                    'played': match.away_standing.matches_played,
                    'wins': match.away_standing.wins,
                    'draws': match.away_standing.draws,
                    'losses': match.away_standing.losses,
                    'gf': match.away_standing.goals_for,
                    'ga': match.away_standing.goals_against,
                    'gd': match.away_standing.goal_difference
                }
        
        # Calcola medie
        avg_goals = total_goals / total_matches if total_matches > 0 else 2.5
        avg_home = home_goals / total_matches if total_matches > 0 else 1.4
        avg_away = away_goals / total_matches if total_matches > 0 else 1.1
        
        # Percentuali
        home_win_pct = (home_wins / total_matches * 100) if total_matches > 0 else 45
        draw_pct = (draws / total_matches * 100) if total_matches > 0 else 27
        away_win_pct = (away_wins / total_matches * 100) if total_matches > 0 else 28
        
        over_pcts = {
            k: (v / total_matches * 100) if total_matches > 0 else 50 
            for k, v in over_counts.items()
        }
        
        bts_pct = (bts_count / total_matches * 100) if total_matches > 0 else 50
        
        # Home advantage
        home_advantage = avg_home - avg_away
        
        # Competitiveness (varianza punti normalizzata)
        if standings_dict:
            points_list = [s['points'] for s in standings_dict.values()]
            if len(points_list) > 1:
                variance = sum((p - sum(points_list)/len(points_list))**2 for p in points_list) / len(points_list)
                competitiveness = 1 - (variance / 100)  # Normalizza (0-1)
                competitiveness = max(0, min(1, competitiveness))
            else:
                competitiveness = 0.5
        else:
            competitiveness = 0.5
        
        # Ordina standings per punti
        standings_list = sorted(
            standings_dict.values(), 
            key=lambda x: (x['points'], x['gd']), 
            reverse=True
        )
        
        return LeagueStats(
            league_name=league_name,
            total_matches=total_matches,
            avg_goals_per_match=avg_goals,
            avg_home_goals=avg_home,
            avg_away_goals=avg_away,
            home_win_percentage=home_win_pct,
            draw_percentage=draw_pct,
            away_win_percentage=away_win_pct,
            over_0_5_percentage=over_pcts[0.5],
            over_1_5_percentage=over_pcts[1.5],
            over_2_5_percentage=over_pcts[2.5],
            over_3_5_percentage=over_pcts[3.5],
            bts_percentage=bts_pct,
            avg_home_advantage=home_advantage,
            league_competitiveness=competitiveness,
            standings=standings_list
        )
    
    def get_league_adjustment_factors(self, league_stats: LeagueStats) -> Dict[str, float]:
        """
        Calcola fattori di aggiustamento per le predizioni basati sul campionato
        
        Returns:
            Dict con fattori moltiplicativi per xG, home advantage, ecc.
        """
        
        # Fattore gol (rispetto a media generale ~2.5)
        goal_factor = league_stats.avg_goals_per_match / 2.5
        
        # Fattore home advantage (rispetto a standard ~0.3)
        home_factor = league_stats.avg_home_advantage / 0.3
        
        # Fattore draw (campionati con più pareggi)
        draw_factor = league_stats.draw_percentage / 27  # 27% è media
        
        # Fattore imprevedibilità (più competitivo = più imprevedibile)
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
        
        Args:
            league_stats: Statistiche campionato
            home_team: Nome squadra casa (da evidenziare)
            away_team: Nome squadra trasferta (da evidenziare)
            max_teams: Numero massimo squadre da mostrare
            
        Returns:
            Stringa formattata con classifica
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
