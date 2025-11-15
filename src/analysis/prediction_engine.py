"""
src/analysis/prediction_engine.py
Sistema predittivo professionale: Poisson + Elo + Value Betting + League Context
"""

import math
from typing import Dict, Tuple, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class MatchPrediction:
    """Risultato predizione completa"""
    
    # Probabilità 1X2
    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    
    # Expected Goals
    home_xg: float
    away_xg: float
    total_xg: float
    
    # Over/Under
    over_0_5_prob: float
    over_1_5_prob: float
    over_2_5_prob: float
    over_3_5_prob: float
    under_2_5_prob: float
    
    # Both Teams Score
    bts_yes_prob: float
    bts_no_prob: float
    
    # Top risultati esatti
    exact_scores: List[Tuple[str, float]]  # [("2-1", 0.14), ...]
    
    # Value bets (se quote disponibili)
    value_bets: List[Dict]
    
    # Confidence & Recommendation
    confidence: str  # "High", "Medium", "Low"
    recommended_bet: str
    
    # Metadati
    elo_home: float
    elo_away: float
    elo_diff: float
    
    # Contesto campionato
    league_context: Optional[Dict] = None


class PredictionEngine:
    """Motore predittivo avanzato con contesto campionato"""
    
    # Costanti calibrate su dati storici
    HOME_ADVANTAGE = 0.15  # Vantaggio casa (~15%)
    POISSON_CORRECTION = 0.92  # Dixon-Coles correction factor
    MIN_MATCHES_RELIABLE = 5  # Minimo partite per stats affidabili
    
    # Elo parameters
    ELO_K_FACTOR = 32
    ELO_BASE = 1500
    
    def __init__(self, league_analyzer=None):
        self.league_factors = {}  # Cache per fattori lega
        self.league_analyzer = league_analyzer  # Iniettato dalla GUI
    
    def predict_match(self, match, all_matches=None) -> MatchPrediction:
        """
        Predice risultato partita con sistema ibrido + contesto campionato
        
        Args:
            match: Oggetto Match con tutti i dati
            all_matches: Lista tutte le partite (per analisi campionato)
            
        Returns:
            MatchPrediction completa
        """
        
        # 1. Estrai contesto campionato (dalle stats REALI della pagina)
        league_context = self._extract_league_context(match)
        
        # 2. Calcola Elo ratings (con adjustment campionato)
        elo_home, elo_away = self._calculate_elo_ratings(match, league_context)
        elo_diff = elo_home - elo_away
        
        # 3. Calcola Expected Goals (con adjustment campionato)
        home_xg, away_xg = self._calculate_expected_goals(match, league_context)
        total_xg = home_xg + away_xg
        
        # 4. Probabilità 1X2 (con peso draw_factor del campionato)
        home_prob, draw_prob, away_prob = self._calculate_1x2_probabilities(
            elo_diff, home_xg, away_xg, league_context
        )
        
        # 5. Probabilità Over/Under (con baseline campionato)
        over_probs = self._calculate_over_under_probabilities(total_xg, league_context)
        
        # 6. Probabilità BTS (con baseline campionato)
        bts_yes, bts_no = self._calculate_bts_probabilities(home_xg, away_xg, match, league_context)
        
        # 7. Top risultati esatti
        exact_scores = self._calculate_exact_scores(home_xg, away_xg)
        
        # 8. Value bets detection
        value_bets = self._detect_value_bets(
            match, home_prob, draw_prob, away_prob, 
            over_probs['over_2_5'], bts_yes
        )
        
        # 9. Confidence & Recommendation (con affidabilità campionato)
        confidence = self._calculate_confidence(match, elo_diff, league_context)
        recommendation = self._generate_recommendation(
            home_prob, draw_prob, away_prob, value_bets, confidence
        )
        
        return MatchPrediction(
            home_win_prob=home_prob,
            draw_prob=draw_prob,
            away_win_prob=away_prob,
            home_xg=home_xg,
            away_xg=away_xg,
            total_xg=total_xg,
            over_0_5_prob=over_probs['over_0_5'],
            over_1_5_prob=over_probs['over_1_5'],
            over_2_5_prob=over_probs['over_2_5'],
            over_3_5_prob=over_probs['over_3_5'],
            under_2_5_prob=1 - over_probs['over_2_5'],
            bts_yes_prob=bts_yes,
            bts_no_prob=bts_no,
            exact_scores=exact_scores,
            value_bets=value_bets,
            confidence=confidence,
            recommended_bet=recommendation,
            elo_home=elo_home,
            elo_away=elo_away,
            elo_diff=elo_diff,
            league_context=league_context
        )
    
    def _extract_league_context(self, match) -> Dict:
        """
        Estrae contesto campionato dalle statistiche REALI della pagina
        
        Returns:
            Dict con fattori di aggiustamento per le predizioni
        """
        context = {
            'goal_factor': 1.0,
            'home_advantage_factor': 1.0,
            'draw_factor': 1.0,
            'unpredictability': 0.5,
            'over_2_5_baseline': 0.5,
            'bts_baseline': 0.5,
            'reliability': 'Medium'
        }
        
        if not match.league_statistics:
            return context
        
        stats = match.league_statistics
        
        # 1. GOAL FACTOR (rispetto a media standard 2.5)
        if stats.get('avg_goals', 0) > 0:
            context['goal_factor'] = stats['avg_goals'] / 2.5
        
        # 2. HOME ADVANTAGE FACTOR (rispetto a standard 0.3)
        if stats.get('avg_home_goals', 0) > 0 and stats.get('avg_away_goals', 0) > 0:
            home_adv = stats['avg_home_goals'] - stats['avg_away_goals']
            context['home_advantage_factor'] = home_adv / 0.3
        
        # 3. DRAW FACTOR (rispetto a media 27%)
        if stats.get('draw_pct', 0) > 0:
            context['draw_factor'] = stats['draw_pct'] / 27.0
        
        # 4. OVER/UNDER BASELINE (dalla percentuale reale del campionato)
        if 'over_under' in stats and '2.5' in stats['over_under']:
            context['over_2_5_baseline'] = stats['over_under']['2.5']['over'] / 100
        
        # 5. BTS BASELINE (dalla percentuale reale)
        if stats.get('bts_pct', 0) > 0:
            context['bts_baseline'] = stats['bts_pct'] / 100
        
        # 6. UNPREDICTABILITY (competitività)
        if stats.get('total_matches', 0) >= 10:
            home_pct = stats.get('home_win_pct', 33)
            draw_pct = stats.get('draw_pct', 33)
            away_pct = stats.get('away_win_pct', 33)
            
            variance = ((home_pct - 33.3)**2 + (draw_pct - 33.3)**2 + (away_pct - 33.3)**2) / 3
            context['unpredictability'] = 1 - (variance / 1000)
            context['unpredictability'] = max(0.3, min(0.7, context['unpredictability']))
        
        # 7. RELIABILITY (affidabilità statistiche)
        matches_played = stats.get('total_matches', 0)
        if matches_played >= 15:
            context['reliability'] = 'High'
        elif matches_played >= 8:
            context['reliability'] = 'Medium'
        else:
            context['reliability'] = 'Low'
        
        return context
    
    def _calculate_elo_ratings(self, match, league_context: Dict = None) -> Tuple[float, float]:
        """Calcola Elo rating con adjustment campionato"""
        base_elo = self.ELO_BASE
        
        # Home team Elo
        elo_home = base_elo
        if match.home_standing:
            elo_home += match.home_standing.points * 2
            position_factor = (11 - match.home_standing.position) * 10
            elo_home += position_factor
            elo_home += match.home_standing.goal_difference * 3
        
        if match.home_last_matches:
            form_bonus = self._calculate_form_bonus(match.home_last_matches[:5])
            elo_home += form_bonus
        
        # Away team Elo
        elo_away = base_elo
        if match.away_standing:
            elo_away += match.away_standing.points * 2
            position_factor = (11 - match.away_standing.position) * 10
            elo_away += position_factor
            elo_away += match.away_standing.goal_difference * 3
        
        if match.away_last_matches:
            form_bonus = self._calculate_form_bonus(match.away_last_matches[:5])
            elo_away += form_bonus
        
        # ADJUSTMENT: Riduci differenza Elo se campionato è imprevedibile
        if league_context and league_context.get('unpredictability', 0) > 0.6:
            elo_diff = elo_home - elo_away
            compression = 0.8
            elo_home = self.ELO_BASE + (elo_diff * compression) / 2
            elo_away = self.ELO_BASE - (elo_diff * compression) / 2
        
        return elo_home, elo_away
    
    def _calculate_form_bonus(self, last_matches: List[Dict]) -> float:
        """Calcola bonus Elo dalla form recente"""
        bonus = 0.0
        weights = [5, 4, 3, 2, 1]
        
        for i, match in enumerate(last_matches[:5]):
            outcome = match.get('outcome', 'D')
            weight = weights[i] if i < len(weights) else 1
            
            if outcome == 'W':
                bonus += 15 * weight
            elif outcome == 'D':
                bonus += 5 * weight
            else:
                bonus -= 10 * weight
        
        return bonus / sum(weights) if weights else 0
    
    def _calculate_expected_goals(self, match, league_context: Dict = None) -> Tuple[float, float]:
        """Calcola Expected Goals con adjustment campionato"""
        
        # Default (usa contesto campionato se disponibile)
        if league_context and league_context.get('goal_factor', 0) > 0:
            league_avg = 1.4 * league_context['goal_factor']
        else:
            league_avg = 1.4
        
        home_xg = league_avg
        away_xg = league_avg
        
        if match.home_stats and match.away_stats:
            # Forza attacco casa
            if match.home_stats.home_stats:
                home_attack = match.home_stats.home_stats.avg_goals_scored or league_avg
            else:
                home_attack = match.home_stats.avg_goals_scored or league_avg
            
            # Debolezza difesa trasferta
            if match.away_stats.away_stats:
                away_defense_weak = match.away_stats.away_stats.avg_goals_conceded or league_avg
            else:
                away_defense_weak = match.away_stats.avg_goals_conceded or league_avg
            
            # Expected goals casa
            home_xg = (home_attack + away_defense_weak) / 2
            
            # Vantaggio casa con adjustment campionato
            home_adv = self.HOME_ADVANTAGE
            if league_context:
                home_adv *= league_context.get('home_advantage_factor', 1.0)
            home_xg *= (1 + home_adv)
            
            # Forza attacco trasferta
            if match.away_stats.away_stats:
                away_attack = match.away_stats.away_stats.avg_goals_scored or league_avg
            else:
                away_attack = match.away_stats.avg_goals_scored or league_avg
            
            # Debolezza difesa casa
            if match.home_stats.home_stats:
                home_defense_weak = match.home_stats.home_stats.avg_goals_conceded or league_avg
            else:
                home_defense_weak = match.home_stats.avg_goals_conceded or league_avg
            
            # Expected goals trasferta
            away_xg = (away_attack + home_defense_weak) / 2
        
        # ADJUSTMENT: Applica goal_factor del campionato
        if league_context:
            goal_factor = league_context.get('goal_factor', 1.0)
            home_xg *= goal_factor
            away_xg *= goal_factor
        
        # Limiti realistici
        home_xg = max(0.3, min(4.0, home_xg))
        away_xg = max(0.3, min(4.0, away_xg))
        
        return home_xg, away_xg
    
    def _calculate_1x2_probabilities(
        self, elo_diff: float, home_xg: float, away_xg: float, league_context: Dict = None
    ) -> Tuple[float, float, float]:
        """Combina Elo e Poisson con adjustment campionato"""
        
        # Metodo 1: Elo-based probabilities
        elo_home_prob = 1 / (1 + 10 ** (-elo_diff / 400))
        elo_away_prob = 1 - elo_home_prob
        elo_draw_prob = 0.27
        
        # Normalizza
        total = elo_home_prob + elo_draw_prob + elo_away_prob
        elo_home_prob /= total
        elo_away_prob /= total
        elo_draw_prob /= total
        
        # Metodo 2: Poisson simulation
        poisson_home, poisson_draw, poisson_away = self._poisson_match_outcome(home_xg, away_xg)
        
        # ADJUSTMENT: Usa draw_factor del campionato
        draw_weight = 0.6
        if league_context:
            draw_factor = league_context.get('draw_factor', 1.0)
            if draw_factor > 1.2:
                draw_weight = 0.7
            elif draw_factor < 0.8:
                draw_weight = 0.5
        
        # Combina
        home_prob = (elo_home_prob * 0.5) + (poisson_home * 0.5)
        draw_prob = (elo_draw_prob * (1 - draw_weight)) + (poisson_draw * draw_weight)
        away_prob = (elo_away_prob * 0.5) + (poisson_away * 0.5)
        
        # Normalizza finale
        total = home_prob + draw_prob + away_prob
        return home_prob / total, draw_prob / total, away_prob / total
    
    def _poisson_match_outcome(self, lambda_home: float, lambda_away: float) -> Tuple[float, float, float]:
        """Simula risultato partita con Poisson"""
        max_goals = 8
        
        home_win_prob = 0.0
        draw_prob = 0.0
        away_win_prob = 0.0
        
        for home_goals in range(max_goals + 1):
            for away_goals in range(max_goals + 1):
                prob = self._poisson_probability(home_goals, lambda_home) * \
                       self._poisson_probability(away_goals, lambda_away)
                
                if home_goals <= 1 and away_goals <= 1:
                    prob *= self.POISSON_CORRECTION
                
                if home_goals > away_goals:
                    home_win_prob += prob
                elif home_goals == away_goals:
                    draw_prob += prob
                else:
                    away_win_prob += prob
        
        return home_win_prob, draw_prob, away_win_prob
    
    def _poisson_probability(self, k: int, lambda_val: float) -> float:
        """Probabilità Poisson: P(X=k) = (λ^k * e^-λ) / k!"""
        return (lambda_val ** k) * math.exp(-lambda_val) / math.factorial(k)
    
    def _calculate_over_under_probabilities(self, total_xg: float, league_context: Dict = None) -> Dict[str, float]:
        """Calcola probabilità Over/Under con baseline campionato"""
        max_goals = 10
        
        goal_probs = {}
        for goals in range(max_goals + 1):
            goal_probs[goals] = self._poisson_probability(goals, total_xg)
        
        over_0_5 = sum(goal_probs[g] for g in range(1, max_goals + 1))
        over_1_5 = sum(goal_probs[g] for g in range(2, max_goals + 1))
        over_2_5 = sum(goal_probs[g] for g in range(3, max_goals + 1))
        over_3_5 = sum(goal_probs[g] for g in range(4, max_goals + 1))
        
        # ADJUSTMENT: Usa baseline campionato per Over 2.5
        if league_context and 'over_2_5_baseline' in league_context:
            baseline = league_context['over_2_5_baseline']
            over_2_5 = (over_2_5 * 0.7) + (baseline * 0.3)
        
        return {
            'over_0_5': over_0_5,
            'over_1_5': over_1_5,
            'over_2_5': over_2_5,
            'over_3_5': over_3_5
        }
    
    def _calculate_bts_probabilities(
        self, home_xg: float, away_xg: float, match, league_context: Dict = None
    ) -> Tuple[float, float]:
        """Probabilità Both Teams Score con baseline campionato"""
        
        # Metodo 1: Poisson
        home_scores = 1 - self._poisson_probability(0, home_xg)
        away_scores = 1 - self._poisson_probability(0, away_xg)
        poisson_bts = home_scores * away_scores
        
        # Metodo 2: Media storica squadre
        historical_bts = 0.5
        if match.home_stats and match.away_stats:
            home_bts_rate = match.home_stats.bts_percentage / 100
            away_bts_rate = match.away_stats.bts_percentage / 100
            historical_bts = (home_bts_rate + away_bts_rate) / 2
        
        # Metodo 3: Baseline campionato
        league_bts = 0.5
        if league_context and 'bts_baseline' in league_context:
            league_bts = league_context['bts_baseline']
        
        # Combina: 50% Poisson, 30% storico squadre, 20% campionato
        bts_yes = (poisson_bts * 0.5) + (historical_bts * 0.3) + (league_bts * 0.2)
        bts_no = 1 - bts_yes
        
        return bts_yes, bts_no
    
    def _calculate_exact_scores(self, home_xg: float, away_xg: float, top_n: int = 10) -> List[Tuple[str, float]]:
        """Calcola probabilità risultati esatti"""
        max_goals = 6
        scores = []
        
        for home_goals in range(max_goals + 1):
            for away_goals in range(max_goals + 1):
                prob = self._poisson_probability(home_goals, home_xg) * \
                       self._poisson_probability(away_goals, away_xg)
                
                if home_goals <= 1 and away_goals <= 1:
                    prob *= self.POISSON_CORRECTION
                
                score_str = f"{home_goals}-{away_goals}"
                scores.append((score_str, prob))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_n]
    
    def _detect_value_bets(
        self, match, home_prob: float, draw_prob: float, away_prob: float,
        over_2_5_prob: float, bts_prob: float
    ) -> List[Dict]:
        """Identifica value bets"""
        value_bets = []
        min_value = 0.05
        
        if not match.odds:
            return value_bets
        
        markets = [
            ('Home Win', home_prob, match.odds.home_win),
            ('Draw', draw_prob, match.odds.draw),
            ('Away Win', away_prob, match.odds.away_win),
        ]
        
        if match.odds.over_2_5 > 0:
            markets.append(('Over 2.5', over_2_5_prob, match.odds.over_2_5))
        
        if match.odds.bts_yes > 0:
            markets.append(('BTS Yes', bts_prob, match.odds.bts_yes))
        
        for market_name, prob, odds in markets:
            if odds > 0:
                ev = (prob * odds) - 1
                
                if ev > min_value:
                    implied_prob = 1 / odds if odds > 0 else 0
                    
                    value_bets.append({
                        'market': market_name,
                        'our_probability': prob,
                        'bookmaker_odds': odds,
                        'implied_probability': implied_prob,
                        'expected_value': ev,
                        'edge': (prob - implied_prob) * 100,
                        'confidence': 'High' if ev > 0.15 else 'Medium'
                    })
        
        value_bets.sort(key=lambda x: x['expected_value'], reverse=True)
        return value_bets
    
    def _calculate_confidence(self, match, elo_diff: float, league_context: Dict = None) -> str:
        """Calcola confidence con affidabilità campionato"""
        
        has_standings = bool(match.home_standing and match.away_standing)
        has_stats = bool(match.home_stats and match.away_stats)
        has_form = bool(match.home_last_matches and match.away_last_matches)
        has_odds = bool(match.odds and match.odds.home_win > 0)
        has_league_stats = bool(match.league_statistics)
        
        data_score = sum([has_standings, has_stats, has_form, has_odds, has_league_stats])
        
        elo_clear = abs(elo_diff) > 100
        
        league_reliable = True
        if league_context:
            reliability = league_context.get('reliability', 'Medium')
            if reliability == 'Low':
                league_reliable = False
        
        if data_score >= 4 and (elo_clear or has_odds) and league_reliable:
            return "High"
        elif data_score >= 3 and league_reliable:
            return "Medium"
        else:
            return "Low"
    
    def _generate_recommendation(
        self, home_prob: float, draw_prob: float, away_prob: float,
        value_bets: List[Dict], confidence: str
    ) -> str:
        """Genera raccomandazione scommessa"""
        
        if value_bets and confidence != "Low":
            best_value = value_bets[0]
            return f"{best_value['market']} @ {best_value['bookmaker_odds']:.2f} (EV: {best_value['expected_value']*100:.1f}%)"
        
        max_prob = max(home_prob, draw_prob, away_prob)
        
        if max_prob > 0.55 and confidence != "Low":
            if max_prob == home_prob:
                return f"Home Win (Prob: {home_prob*100:.1f}%)"
            elif max_prob == away_prob:
                return f"Away Win (Prob: {away_prob*100:.1f}%)"
            else:
                return f"Draw (Prob: {draw_prob*100:.1f}%)"
        
        return "No clear recommendation - Balanced match"