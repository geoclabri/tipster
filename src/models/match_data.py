"""
src/models/match_data.py
Modelli dati completi con tutte le statistiche
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional, Dict
import pandas as pd
import json


@dataclass
class MatchOdds:
    """Quote complete di una partita"""
    # Quote base 1X2
    home_win: float = 0.0
    draw: float = 0.0
    away_win: float = 0.0
    
    # Double Chance
    dc_1x: float = 0.0
    dc_12: float = 0.0
    dc_x2: float = 0.0
    
    # Over/Under
    over_1_5: float = 0.0
    under_1_5: float = 0.0
    over_2_5: float = 0.0
    under_2_5: float = 0.0
    over_3_5: float = 0.0
    under_3_5: float = 0.0
    
    # Both Teams to Score
    bts_yes: float = 0.0
    bts_no: float = 0.0
    
    bookmakers_count: int = 0
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TeamStats:
    """Statistiche complete squadra"""
    # Record
    wins: int = 0
    draws: int = 0
    losses: int = 0
    
    # Gol
    goals_for: int = 0
    goals_against: int = 0
    avg_goals_scored: float = 0.0
    avg_goals_conceded: float = 0.0
    
    # Percentuali
    bts_percentage: float = 0.0
    over_1_5_percentage: float = 0.0
    over_2_5_percentage: float = 0.0
    over_3_5_percentage: float = 0.0
    
    # Stats separate home/away (nested)
    home_stats: Optional['TeamStats'] = None
    away_stats: Optional['TeamStats'] = None
    
    def to_dict(self) -> dict:
        data = {
            'wins': self.wins,
            'draws': self.draws,
            'losses': self.losses,
            'goals_for': self.goals_for,
            'goals_against': self.goals_against,
            'avg_goals_scored': self.avg_goals_scored,
            'avg_goals_conceded': self.avg_goals_conceded,
            'bts_percentage': self.bts_percentage,
            'over_1_5_percentage': self.over_1_5_percentage,
            'over_2_5_percentage': self.over_2_5_percentage,
            'over_3_5_percentage': self.over_3_5_percentage,
        }
        
        if self.home_stats:
            data['home_stats'] = self.home_stats.to_dict()
        if self.away_stats:
            data['away_stats'] = self.away_stats.to_dict()
            
        return data


@dataclass
class TeamStanding:
    """Posizione in classifica"""
    position: int = 0
    team_name: str = ""
    matches_played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0
    goal_difference: int = 0
    points: int = 0
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Match:
    """Partita con TUTTI i dati"""
    # Base
    url: str
    date: datetime
    time: datetime
    league: str
    home_team: str
    away_team: str

    # AGGIUNGI QUESTO CAMPO
    result: Optional[Dict] = None  # {'outcome': '1'/'X'/'2', 'score': '2-1', 'home_goals': 2, 'away_goals': 1}
    
    
    # Quote
    odds: Optional[MatchOdds] = None
    
    # Statistiche squadre
    home_stats: Optional[TeamStats] = None
    away_stats: Optional[TeamStats] = None
    
    # Classifica
    home_standing: Optional[TeamStanding] = None
    away_standing: Optional[TeamStanding] = None
    
    # Ultimi risultati (lista di dict)
    home_last_matches: List[Dict] = field(default_factory=list)
    away_last_matches: List[Dict] = field(default_factory=list)

    # Dati campionato
    league_statistics: Optional[Dict] = None
    league_standings: List[Dict] = field(default_factory=list)
    head_to_head: List[Dict] = field(default_factory=list)
    home_away_comparison: Dict = field(default_factory=dict)
    
    def __post_init__(self):
        if self.odds is None:
            self.odds = MatchOdds()
        if self.home_stats is None:
            self.home_stats = TeamStats()
        if self.away_stats is None:
            self.away_stats = TeamStats()
    
    def get_home_form_string(self, last_n: int = 5) -> str:
        """Ritorna stringa form tipo 'WWDLL'"""
        if not self.home_last_matches:
            return ""
        outcomes = [m['outcome'] for m in self.home_last_matches[:last_n]]
        return ''.join(outcomes)
    
    def get_away_form_string(self, last_n: int = 5) -> str:
        """Ritorna stringa form tipo 'DWWLW'"""
        if not self.away_last_matches:
            return ""
        outcomes = [m['outcome'] for m in self.away_last_matches[:last_n]]
        return ''.join(outcomes)
    
    def to_flat_dict(self) -> dict:
        """Converte in dizionario piatto per CSV/Excel"""
        data = {
            # Base
            'Data': self.date.strftime('%Y-%m-%d'),
            'Ora': self.time.strftime('%H:%M'),
            'Lega': self.league,
            'Squadra Casa': self.home_team,
            'Squadra Trasferta': self.away_team,
            
            # Quote 1X2
            'Quota 1': self.odds.home_win if self.odds else 0,
            'Quota X': self.odds.draw if self.odds else 0,
            'Quota 2': self.odds.away_win if self.odds else 0,
            
            # Double Chance
            'DC 1X': self.odds.dc_1x if self.odds else 0,
            'DC 12': self.odds.dc_12 if self.odds else 0,
            'DC X2': self.odds.dc_x2 if self.odds else 0,
            
            # Over/Under
            'Over 1.5': self.odds.over_1_5 if self.odds else 0,
            'Under 1.5': self.odds.under_1_5 if self.odds else 0,
            'Over 2.5': self.odds.over_2_5 if self.odds else 0,
            'Under 2.5': self.odds.under_2_5 if self.odds else 0,
            'Over 3.5': self.odds.over_3_5 if self.odds else 0,
            'Under 3.5': self.odds.under_3_5 if self.odds else 0,
            
            # BTS
            'GG': self.odds.bts_yes if self.odds else 0,
            'NG': self.odds.bts_no if self.odds else 0,
            
            # Classifica Casa
            'H_Pos': self.home_standing.position if self.home_standing else 0,
            'H_Pts': self.home_standing.points if self.home_standing else 0,
            'H_MP': self.home_standing.matches_played if self.home_standing else 0,
            'H_W': self.home_standing.wins if self.home_standing else 0,
            'H_D': self.home_standing.draws if self.home_standing else 0,
            'H_L': self.home_standing.losses if self.home_standing else 0,
            'H_GF': self.home_standing.goals_for if self.home_standing else 0,
            'H_GA': self.home_standing.goals_against if self.home_standing else 0,
            'H_GD': self.home_standing.goal_difference if self.home_standing else 0,
            
            # Classifica Trasferta
            'A_Pos': self.away_standing.position if self.away_standing else 0,
            'A_Pts': self.away_standing.points if self.away_standing else 0,
            'A_MP': self.away_standing.matches_played if self.away_standing else 0,
            'A_W': self.away_standing.wins if self.away_standing else 0,
            'A_D': self.away_standing.draws if self.away_standing else 0,
            'A_L': self.away_standing.losses if self.away_standing else 0,
            'A_GF': self.away_standing.goals_for if self.away_standing else 0,
            'A_GA': self.away_standing.goals_against if self.away_standing else 0,
            'A_GD': self.away_standing.goal_difference if self.away_standing else 0,
            
            # Stats Casa - Overall
            'H_AvgGF': self.home_stats.avg_goals_scored if self.home_stats else 0,
            'H_AvgGA': self.home_stats.avg_goals_conceded if self.home_stats else 0,
            'H_BTS%': self.home_stats.bts_percentage if self.home_stats else 0,
            'H_O25%': self.home_stats.over_2_5_percentage if self.home_stats else 0,
            
            # Stats Casa - In Casa
            'H_Home_W': self.home_stats.home_stats.wins if self.home_stats and self.home_stats.home_stats else 0,
            'H_Home_D': self.home_stats.home_stats.draws if self.home_stats and self.home_stats.home_stats else 0,
            'H_Home_L': self.home_stats.home_stats.losses if self.home_stats and self.home_stats.home_stats else 0,
            'H_Home_GF': self.home_stats.home_stats.goals_for if self.home_stats and self.home_stats.home_stats else 0,
            'H_Home_GA': self.home_stats.home_stats.goals_against if self.home_stats and self.home_stats.home_stats else 0,
            'H_Home_AvgGF': self.home_stats.home_stats.avg_goals_scored if self.home_stats and self.home_stats.home_stats else 0,
            'H_Home_AvgGA': self.home_stats.home_stats.avg_goals_conceded if self.home_stats and self.home_stats.home_stats else 0,
            
            # Stats Trasferta - Overall
            'A_AvgGF': self.away_stats.avg_goals_scored if self.away_stats else 0,
            'A_AvgGA': self.away_stats.avg_goals_conceded if self.away_stats else 0,
            'A_BTS%': self.away_stats.bts_percentage if self.away_stats else 0,
            'A_O25%': self.away_stats.over_2_5_percentage if self.away_stats else 0,
            
            # Stats Trasferta - Fuori Casa
            'A_Away_W': self.away_stats.away_stats.wins if self.away_stats and self.away_stats.away_stats else 0,
            'A_Away_D': self.away_stats.away_stats.draws if self.away_stats and self.away_stats.away_stats else 0,
            'A_Away_L': self.away_stats.away_stats.losses if self.away_stats and self.away_stats.away_stats else 0,
            'A_Away_GF': self.away_stats.away_stats.goals_for if self.away_stats and self.away_stats.away_stats else 0,
            'A_Away_GA': self.away_stats.away_stats.goals_against if self.away_stats and self.away_stats.away_stats else 0,
            'A_Away_AvgGF': self.away_stats.away_stats.avg_goals_scored if self.away_stats and self.away_stats.away_stats else 0,
            'A_Away_AvgGA': self.away_stats.away_stats.avg_goals_conceded if self.away_stats and self.away_stats.away_stats else 0,
            
            # Form (ultimi 5)
            'H_Form': self.get_home_form_string(5),
            'A_Form': self.get_away_form_string(5),
            
            # URL
            'URL': self.url,
        }
        
        return data
    
    def to_dict(self) -> dict:
        """Converte in dizionario completo (per JSON)"""
        return {
            'url': self.url,
            'date': self.date.strftime('%Y-%m-%d'),
            'time': self.time.strftime('%H:%M'),
            'league': self.league,
            'home_team': self.home_team,
            'away_team': self.away_team,
            'odds': self.odds.to_dict() if self.odds else {},
            'home_stats': self.home_stats.to_dict() if self.home_stats else {},
            'away_stats': self.away_stats.to_dict() if self.away_stats else {},
            'home_standing': self.home_standing.to_dict() if self.home_standing else {},
            'away_standing': self.away_standing.to_dict() if self.away_standing else {},
            'home_last_matches': self.home_last_matches,
            'away_last_matches': self.away_last_matches,
            'home_form': self.get_home_form_string(5),
            'away_form': self.get_away_form_string(5),
            'league_statistics': self.league_statistics,
            'league_standings': self.league_standings,
            'head_to_head': self.head_to_head,
        }
    
    def to_backtesting_dict(self, prediction=None, actual_result: dict = None) -> dict:
        """
        Converte match + prediction in formato per backtesting archive
        
        Args:
            prediction: MatchPrediction object
            actual_result: {'outcome': '1'/'X'/'2', 'score': '2-1', 'home_goals': 2, 'away_goals': 1}
        """
        data = {
            'match': {
                'date': self.date.strftime('%Y-%m-%d'),
                'time': self.time.strftime('%H:%M'),
                'league': self.league,
                'home_team': self.home_team,
                'away_team': self.away_team,
                'url': self.url
            },
            'odds': self.odds.to_dict() if self.odds else {},
        }
        
        # Prediction
        if prediction:
            data['prediction'] = {
                'home_win_prob': prediction.home_win_prob,
                'draw_prob': prediction.draw_prob,
                'away_win_prob': prediction.away_win_prob,
                'home_xg': prediction.home_xg,
                'away_xg': prediction.away_xg,
                'total_xg': prediction.total_xg,
                'confidence_score': prediction.confidence_score,
                'confidence': prediction.confidence,
                'prediction_variance': prediction.prediction_variance,
                'over_2_5_prob': prediction.over_2_5_prob,
                'bts_yes_prob': prediction.bts_yes_prob,
                'value_bets': prediction.value_bets,
                'recommended_bet': prediction.recommended_bet,
                'home_attack_rating': prediction.home_attack_rating,
                'home_defense_rating': prediction.home_defense_rating,
                'away_attack_rating': prediction.away_attack_rating,
                'away_defense_rating': prediction.away_defense_rating,
            }
        
        # Actual result (se disponibile)
        if actual_result:
            data['actual'] = actual_result
        
        return data


class MatchCollection:
    """Collezione di partite con utility"""
    
    def __init__(self, matches: List[Match]):
        self.matches = matches
    
    def to_dataframe(self) -> pd.DataFrame:
        """Converte in DataFrame pandas"""
        data = [match.to_flat_dict() for match in self.matches]
        return pd.DataFrame(data)
    
    def to_excel(self, filepath: str) -> str:
        """Salva in Excel con formattazione"""
        df = self.to_dataframe()
        
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Partite', index=False)
            
            worksheet = writer.sheets['Partite']
            
            # Auto-size colonne
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
            
            # Freezepanes (prima riga)
            worksheet.freeze_panes = 'A2'
        
        return filepath
    
    def to_csv(self, filepath: str, separator: str = ',') -> str:
        """Salva in CSV"""
        df = self.to_dataframe()
        df.to_csv(filepath, index=False, sep=separator, encoding='utf-8-sig')
        return filepath
    
    def to_json(self, filepath: str, indent: int = 2) -> str:
        """Salva in JSON"""
        data = {
            'timestamp': datetime.now().isoformat(),
            'matches_count': len(self.matches),
            'matches': [match.to_dict() for match in self.matches]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        
        return filepath
    
    def filter_by_league(self, league_name: str) -> 'MatchCollection':
        """Filtra per lega"""
        filtered = [m for m in self.matches if league_name.lower() in m.league.lower()]
        return MatchCollection(filtered)
    
    def filter_by_odds_range(self, min_home: float = 0, max_home: float = 100) -> 'MatchCollection':
        """Filtra per range quota casa"""
        filtered = [
            m for m in self.matches 
            if m.odds and min_home <= m.odds.home_win <= max_home
        ]
        return MatchCollection(filtered)
    
    def filter_by_over_percentage(self, min_percentage: float = 50) -> 'MatchCollection':
        """Filtra partite con alta % Over 2.5"""
        filtered = []
        for m in self.matches:
            if m.home_stats and m.away_stats:
                avg_over = (m.home_stats.over_2_5_percentage + m.away_stats.over_2_5_percentage) / 2
                if avg_over >= min_percentage:
                    filtered.append(m)
        return MatchCollection(filtered)
    
    def sort_by_time(self) -> 'MatchCollection':
        """Ordina per orario"""
        sorted_matches = sorted(self.matches, key=lambda m: m.time)
        return MatchCollection(sorted_matches)
    
    def get_statistics(self) -> dict:
        """Statistiche collezione"""
        total = len(self.matches)
        
        if total == 0:
            return {
                'total_matches': 0,
                'unique_leagues': 0,
                'matches_with_odds': 0,
                'matches_with_stats': 0,
                'matches_with_standing': 0,
            }
        
        leagues = set(m.league for m in self.matches)
        with_odds = sum(1 for m in self.matches if m.odds and m.odds.home_win > 0)
        with_stats = sum(1 for m in self.matches if m.home_stats and m.home_stats.wins > 0)
        with_standing = sum(1 for m in self.matches if m.home_standing and m.home_standing.position > 0)
        
        return {
            'total_matches': total,
            'unique_leagues': len(leagues),
            'matches_with_odds': with_odds,
            'matches_with_stats': with_stats,
            'matches_with_standing': with_standing,
            'leagues': sorted(list(leagues)),
        }
