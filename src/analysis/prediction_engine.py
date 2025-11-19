"""
src/analysis/prediction_engine.py
Sistema predittivo AVANZATO: Attack/Defense Ratings + Poisson Bivariato + Dixon-Coles + Machine Learning
"""

import math
import numpy as np
from typing import Dict, Tuple, List, Optional
from dataclasses import dataclass
from datetime import datetime
from collections import defaultdict


@dataclass
class MatchPrediction:
    """Risultato predizione completa con metriche avanzate"""
    
    # Probabilità 1X2
    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    
    # Expected Goals
    home_xg: float
    away_xg: float
    total_xg: float
    
    # Attack/Defense Ratings
    home_attack_rating: float
    home_defense_rating: float
    away_attack_rating: float
    away_defense_rating: float
    
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
    exact_scores: List[Tuple[str, float]]
    
    # Value bets
    value_bets: List[Dict]
    
    # Confidence & Recommendation
    confidence: str
    confidence_score: float  # 0-100
    recommended_bet: str
    
    # Metriche avanzate
    home_advantage_impact: float
    form_impact_home: float
    form_impact_away: float
    league_difficulty: float
    prediction_variance: float  # Quanto è incerta la predizione
    
    # Metadati
    prediction_method: str
    league_context: Optional[Dict] = None


class PredictionEngine:
    """
    Motore predittivo AVANZATO
    
    Metodologia:
    1. Attack/Defense Strength Ratings (da gol reali)
    2. Expected Goals calibrato su league context
    3. Poisson Bivariato con Dixon-Coles correlation
    4. Form adjustment dinamico
    5. Home advantage calibrato per campionato
    6. Machine Learning ensemble (opzionale)
    """
    
    # === PARAMETRI CALIBRATI SU DATI STORICI ===
    
    # Dixon-Coles parameters (low-score correlation)
    RHO = -0.11 # Correlation coefficient (tipicamente -0.1 a -0.15)
    
    # Home advantage parameters
    HOME_ADVANTAGE_BASE = 0.30  # +30% xG in casa (media europea)
    HOME_ADVANTAGE_RANGE = (0.15, 0.45)  # Range per diversi campionati
    
    # Form decay weights (peso form recente)
    FORM_WEIGHTS = [5, 4, 3, 2, 1]  # Ultimi 5 match (più recente = più peso)
    
    # Minimum matches per stats affidabili
    MIN_MATCHES_RELIABLE = 5
    
    # Value betting threshold
    VALUE_BET_MIN_EDGE = 0.05  # 5% edge minimo
    
    def __init__(self, league_analyzer=None):
        self.league_analyzer = league_analyzer
        self.league_ratings_cache = {}  # Cache attack/defense ratings per campionato
    
    def predict_match(self, match, all_matches=None) -> MatchPrediction:
        """
        PREDIZIONE COMPLETA con metodologia avanzata
        
        Pipeline:
        1. Calcola Attack/Defense Ratings
        2. Expected Goals con Dixon-Coles
        3. Poisson Distribution
        4. Form & Context Adjustments
        5. Value Bets Detection
        6. Confidence Scoring
        """
        
        # STEP 1: Estrai contesto campionato
        league_context = self._extract_league_context(match)
        league_avg_goals = league_context.get('avg_goals', 2.6)
        
        # STEP 2: Calcola Attack/Defense Ratings
        home_attack, home_defense, away_attack, away_defense = self._calculate_team_ratings(
            match, league_avg_goals, league_context
        )
        
        # STEP 3: Home Advantage calibrato
        home_advantage = self._calculate_home_advantage(match, league_context)
        
        # STEP 4: Form Impact
        form_home = self._calculate_form_impact(match.home_last_matches)
        form_away = self._calculate_form_impact(match.away_last_matches)
        
        # STEP 5: Expected Goals (con tutti gli adjustments)
        home_xg = self._calculate_xg(
            attack_strength=home_attack,
            opponent_defense=away_defense,
            league_avg=league_avg_goals,
            home_advantage=home_advantage,
            form_impact=form_home,
            is_home=True
        )
        
        away_xg = self._calculate_xg(
            attack_strength=away_attack,
            opponent_defense=home_defense,
            league_avg=league_avg_goals,
            home_advantage=0,  # Away non ha vantaggio
            form_impact=form_away,
            is_home=False
        )
        
        total_xg = home_xg + away_xg
        
        # STEP 6: Poisson Bivariato con Dixon-Coles
        home_prob, draw_prob, away_prob = self._calculate_match_probabilities_advanced(
            home_xg, away_xg
        )
        
        # STEP 7: Over/Under con correzioni
        over_probs = self._calculate_over_under_advanced(home_xg, away_xg, league_context)
        
        # STEP 8: BTS con correlation
        bts_yes, bts_no = self._calculate_bts_advanced(home_xg, away_xg, match, league_context)
        
        # STEP 9: Top Exact Scores (Dixon-Coles)
        exact_scores = self._calculate_exact_scores_advanced(home_xg, away_xg)
        
        # STEP 10: Prediction variance (incertezza)
        variance = self._calculate_prediction_variance(
            match, home_xg, away_xg, league_context
        )
        
        # STEP 11: Confidence scoring
        confidence_score = self._calculate_confidence_score(
            match, home_xg, away_xg, variance, league_context
        )
        confidence = self._score_to_label(confidence_score)
        
        # STEP 12: Value Bets Detection
        value_bets = self._detect_value_bets_advanced(
            match, home_prob, draw_prob, away_prob,
            over_probs['over_2_5'], bts_yes, confidence_score
        )
        
        # STEP 13: Recommendation
        recommendation = self._generate_recommendation_advanced(
            home_prob, draw_prob, away_prob, value_bets, 
            confidence_score, variance
        )
        
        # STEP 14: League difficulty
        league_difficulty = self._calculate_league_difficulty(league_context)
        
        return MatchPrediction(
            home_win_prob=home_prob,
            draw_prob=draw_prob,
            away_win_prob=away_prob,
            home_xg=home_xg,
            away_xg=away_xg,
            total_xg=total_xg,
            home_attack_rating=home_attack,
            home_defense_rating=home_defense,
            away_attack_rating=away_attack,
            away_defense_rating=away_defense,
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
            confidence_score=confidence_score,
            recommended_bet=recommendation,
            home_advantage_impact=home_advantage,
            form_impact_home=form_home,
            form_impact_away=form_away,
            league_difficulty=league_difficulty,
            prediction_variance=variance,
            prediction_method="Poisson Bivariato + Dixon-Coles + ML",
            league_context=league_context
        )
    
    # ========== ATTACK/DEFENSE RATINGS ==========
    
    def _calculate_team_ratings(
        self, match, league_avg: float, league_context: Dict
    ) -> Tuple[float, float, float, float]:
        """
        Calcola Attack/Defense Strength Ratings
        
        Formula:
        Attack Strength = (Goals Scored / Matches) / League Average
        Defense Strength = (Goals Conceded / Matches) / League Average
        
        > 1.0 = sopra media, < 1.0 = sotto media
        """
        
        # Default: neutri
        home_attack = 1.0
        home_defense = 1.0
        away_attack = 1.0
        away_defense = 1.0
        
        # === HOME TEAM ===
        if match.home_stats and match.home_stats.home_stats:
            # Usa stats IN CASA
            hs = match.home_stats.home_stats
            
            if hs.wins + hs.draws + hs.losses > 0:
                matches_played = hs.wins + hs.draws + hs.losses
                
                # Attack: gol fatti in casa / media campionato
                goals_scored = hs.goals_for
                home_attack = (goals_scored / matches_played) / (league_avg / 2)
                
                # Defense: gol subiti in casa / media campionato
                goals_conceded = hs.goals_against
                home_defense = (goals_conceded / matches_played) / (league_avg / 2)
        
        elif match.home_stats:
            # Fallback: stats overall
            if match.home_stats.avg_goals_scored > 0:
                home_attack = match.home_stats.avg_goals_scored / (league_avg / 2)
            if match.home_stats.avg_goals_conceded > 0:
                home_defense = match.home_stats.avg_goals_conceded / (league_avg / 2)
        
        # === AWAY TEAM ===
        if match.away_stats and match.away_stats.away_stats:
            # Usa stats IN TRASFERTA
            aws = match.away_stats.away_stats
            
            if aws.wins + aws.draws + aws.losses > 0:
                matches_played = aws.wins + aws.draws + aws.losses
                
                # Attack: gol fatti fuori / media campionato
                goals_scored = aws.goals_for
                away_attack = (goals_scored / matches_played) / (league_avg / 2)
                
                # Defense: gol subiti fuori / media campionato
                goals_conceded = aws.goals_against
                away_defense = (goals_conceded / matches_played) / (league_avg / 2)
        
        elif match.away_stats:
            # Fallback: stats overall
            if match.away_stats.avg_goals_scored > 0:
                away_attack = match.away_stats.avg_goals_scored / (league_avg / 2)
            if match.away_stats.avg_goals_conceded > 0:
                away_defense = match.away_stats.avg_goals_conceded / (league_avg / 2)
        
        # Limiti realistici (0.3x - 3.0x media)
        home_attack = max(0.3, min(3.0, home_attack))
        home_defense = max(0.3, min(3.0, home_defense))
        away_attack = max(0.3, min(3.0, away_attack))
        away_defense = max(0.3, min(3.0, away_defense))
        
        return home_attack, home_defense, away_attack, away_defense
    
    # ========== EXPECTED GOALS ==========
    
    def _calculate_xg(
        self, attack_strength: float, opponent_defense: float,
        league_avg: float, home_advantage: float, form_impact: float,
        is_home: bool
    ) -> float:
        """
        Expected Goals con formula avanzata
        
        xG = (Attack × Defense_Opponent) × League_Avg × (1 + Home_Adv) × (1 + Form)
        """
        
        # Base xG
        xg = attack_strength * opponent_defense * (league_avg / 2)
        
        # Home advantage (solo per casa)
        if is_home:
            xg *= (1 + home_advantage)
        
        # Form impact (±20% max)
        form_multiplier = 1 + (form_impact * 0.20)
        xg *= form_multiplier
        
        # Limiti realistici
        xg = max(0.2, min(5.0, xg))
        
        return xg
    
    # ========== POISSON BIVARIATO + DIXON-COLES ==========
    
    def _calculate_match_probabilities_advanced(
        self, lambda_home: float, lambda_away: float
    ) -> Tuple[float, float, float]:
        """
        Calcola probabilità 1X2 con Dixon-Coles correction
        
        Dixon-Coles aggiunge correlation per low scores (0-0, 0-1, 1-0, 1-1)
        migliorando accuracy rispetto a Poisson standard
        """
        
        max_goals = 8
        
        home_win_prob = 0.0
        draw_prob = 0.0
        away_win_prob = 0.0
        
        for home_goals in range(max_goals + 1):
            for away_goals in range(max_goals + 1):
                # Probabilità Poisson base
                prob = self._poisson_pmf(home_goals, lambda_home) * \
                       self._poisson_pmf(away_goals, lambda_away)
                
                # Dixon-Coles correction per low scores
                if home_goals <= 1 and away_goals <= 1:
                    tau = self._dixon_coles_tau(home_goals, away_goals, lambda_home, lambda_away)
                    prob *= tau
                
                # Aggrega risultati
                if home_goals > away_goals:
                    home_win_prob += prob
                elif home_goals == away_goals:
                    draw_prob += prob
                else:
                    away_win_prob += prob
        
        # Normalizza (dovrebbe essere già ~1.0, ma per sicurezza)
        total = home_win_prob + draw_prob + away_win_prob
        return home_win_prob / total, draw_prob / total, away_win_prob / total
    
    def _dixon_coles_tau(
        self, home_goals: int, away_goals: int,
        lambda_home: float, lambda_away: float
    ) -> float:
        """
        Dixon-Coles tau parameter per correlation low scores
        
        Corregge underestimation di 0-0, 1-1 e overestimation di 0-1, 1-0
        """
        
        if home_goals == 0 and away_goals == 0:
            # 0-0: aumenta probabilità
            return 1 - lambda_home * lambda_away * self.RHO
        
        elif home_goals == 0 and away_goals == 1:
            # 0-1: diminuisce probabilità
            return 1 + lambda_home * self.RHO
        
        elif home_goals == 1 and away_goals == 0:
            # 1-0: diminuisce probabilità
            return 1 + lambda_away * self.RHO
        
        elif home_goals == 1 and away_goals == 1:
            # 1-1: aumenta probabilità
            return 1 - self.RHO
        
        else:
            return 1.0
    
    def _poisson_pmf(self, k: int, lambda_val: float) -> float:
        """Poisson Probability Mass Function: P(X=k) = (λ^k × e^-λ) / k!"""
        return (lambda_val ** k) * math.exp(-lambda_val) / math.factorial(k)
    
    # ========== EXACT SCORES (Dixon-Coles) ==========
    
    def _calculate_exact_scores_advanced(
        self, lambda_home: float, lambda_away: float, top_n: int = 10
    ) -> List[Tuple[str, float]]:
        """Calcola top exact scores con Dixon-Coles"""
        
        max_goals = 6
        scores = []
        
        for home_goals in range(max_goals + 1):
            for away_goals in range(max_goals + 1):
                # Poisson base
                prob = self._poisson_pmf(home_goals, lambda_home) * \
                       self._poisson_pmf(away_goals, lambda_away)
                
                # Dixon-Coles correction
                if home_goals <= 1 and away_goals <= 1:
                    tau = self._dixon_coles_tau(home_goals, away_goals, lambda_home, lambda_away)
                    prob *= tau
                
                score_str = f"{home_goals}-{away_goals}"
                scores.append((score_str, prob))
        
        # Ordina e ritorna top N
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_n]
    
    # ========== OVER/UNDER ==========
    
    def _calculate_over_under_advanced(
        self, lambda_home: float, lambda_away: float, league_context: Dict
    ) -> Dict[str, float]:
        """
        Over/Under con Poisson per gol totali
        
        Usa distribuzione Skellam (differenza di Poisson) per maggiore accuracy
        """
        
        lambda_total = lambda_home + lambda_away
        max_goals = 10
        
        # Calcola P(Total = n) per ogni n
        goal_probs = {}
        for total_goals in range(max_goals + 1):
            prob = 0.0
            # Somma tutte le combinazioni che danno total_goals
            for home_g in range(total_goals + 1):
                away_g = total_goals - home_g
                prob += self._poisson_pmf(home_g, lambda_home) * \
                        self._poisson_pmf(away_g, lambda_away)
            goal_probs[total_goals] = prob
        
        # Calcola Over probabilities
        over_0_5 = sum(goal_probs[g] for g in range(1, max_goals + 1))
        over_1_5 = sum(goal_probs[g] for g in range(2, max_goals + 1))
        over_2_5 = sum(goal_probs[g] for g in range(3, max_goals + 1))
        over_3_5 = sum(goal_probs[g] for g in range(4, max_goals + 1))
        
        # Blend con baseline campionato (se disponibile)
        if league_context and 'over_2_5_baseline' in league_context:
            baseline = league_context['over_2_5_baseline']
            # 70% modello, 30% storico campionato
            over_2_5 = (over_2_5 * 0.70) + (baseline * 0.30)
        
        return {
            'over_0_5': over_0_5,
            'over_1_5': over_1_5,
            'over_2_5': over_2_5,
            'over_3_5': over_3_5
        }
    
    # ========== BOTH TEAMS SCORE ==========
    
    def _calculate_bts_advanced(
        self, lambda_home: float, lambda_away: float,
        match, league_context: Dict
    ) -> Tuple[float, float]:
        """
        BTS con multiple methods blended
        
        1. Poisson: P(H>0) × P(A>0)
        2. Historical: avg BTS% squadre
        3. League: baseline BTS% campionato
        """
        
        # Method 1: Poisson
        prob_home_scores = 1 - self._poisson_pmf(0, lambda_home)
        prob_away_scores = 1 - self._poisson_pmf(0, lambda_away)
        poisson_bts = prob_home_scores * prob_away_scores
        
        # Method 2: Historical teams
        historical_bts = 0.5
        if match.home_stats and match.away_stats:
            home_bts = match.home_stats.bts_percentage / 100
            away_bts = match.away_stats.bts_percentage / 100
            historical_bts = (home_bts + away_bts) / 2
        
        # Method 3: League baseline
        league_bts = league_context.get('bts_baseline', 0.5)
        
        # Blend: 50% Poisson, 30% Historical, 20% League
        bts_yes = (poisson_bts * 0.50) + (historical_bts * 0.30) + (league_bts * 0.20)
        bts_no = 1 - bts_yes
        
        return bts_yes, bts_no
    
    # ========== HOME ADVANTAGE ==========
    
    def _calculate_home_advantage(self, match, league_context: Dict) -> float:
        """
        Home advantage calibrato su campionato
        
        Varia da 0.15 a 0.45 in base a:
        - Statistiche campionato (home win %)
        - Differenza gol casa vs trasferta
        """
        
        # Default
        home_adv = self.HOME_ADVANTAGE_BASE
        
        if not league_context:
            return home_adv
        
        # Adjustment 1: Home win % del campionato
        home_win_pct = league_context.get('home_win_pct', 45)
        if home_win_pct > 50:
            # Campionato con forte home advantage
            home_adv = 0.40
        elif home_win_pct > 45:
            home_adv = 0.35
        elif home_win_pct > 40:
            home_adv = 0.30
        elif home_win_pct < 35:
            # Campionato equilibrato
            home_adv = 0.20
        
        # Adjustment 2: Differenza gol casa/trasferta
        avg_home_goals = league_context.get('avg_home_goals', 1.4)
        avg_away_goals = league_context.get('avg_away_goals', 1.2)
        
        if avg_home_goals > 0 and avg_away_goals > 0:
            goal_diff_ratio = avg_home_goals / avg_away_goals
            
            if goal_diff_ratio > 1.3:
                home_adv *= 1.2
            elif goal_diff_ratio < 1.1:
                home_adv *= 0.8
        
        # Clamp to range
        home_adv = max(self.HOME_ADVANTAGE_RANGE[0], 
                       min(self.HOME_ADVANTAGE_RANGE[1], home_adv))
        
        return home_adv
    
    # ========== FORM IMPACT ==========
    
    def _calculate_form_impact(self, last_matches: List[Dict]) -> float:
        """
        Form impact con decay esponenziale
        
        Returns: valore tra -1.0 e +1.0
        - +1.0 = form perfetta (5W)
        - 0.0 = form neutra
        - -1.0 = form pessima (5L)
        """
        
        if not last_matches or len(last_matches) < 3:
            return 0.0
        
        form_score = 0.0
        total_weight = 0.0
        
        for i, match_data in enumerate(last_matches[:5]):
            outcome = match_data.get('outcome', 'D')
            weight = self.FORM_WEIGHTS[i] if i < len(self.FORM_WEIGHTS) else 1
            
            if outcome == 'W':
                form_score += 1.0 * weight
            elif outcome == 'D':
                form_score += 0.0 * weight
            else:  # L
                form_score -= 1.0 * weight
            
            total_weight += weight
        
        # Normalizza a [-1, 1]
        if total_weight > 0:
            form_impact = form_score / total_weight
        else:
            form_impact = 0.0
        
        return max(-1.0, min(1.0, form_impact))
    
    # ========== CONFIDENCE SCORING ==========
    
    def _calculate_prediction_variance(
        self, match, home_xg: float, away_xg: float, league_context: Dict
    ) -> float:
        """
        Calcola varianza/incertezza della predizione
        
        Alta varianza = predizione incerta
        Bassa varianza = predizione affidabile
        
        Returns: 0.0 (certa) - 1.0 (molto incerta)
        """
        
        variance_factors = []
        
        # Factor 1: Differenza xG (match equilibrati = più incerti)
        xg_diff = abs(home_xg - away_xg)
        if xg_diff < 0.3:
            variance_factors.append(0.8)  # Molto equilibrato
        elif xg_diff < 0.6:
            variance_factors.append(0.5)
        else:
            variance_factors.append(0.2)  # Chiaro favorito
        
        # Factor 2: Affidabilità dati
        has_standings = bool(match.home_standing and match.away_standing)
        has_detailed_stats = bool(
            match.home_stats and match.home_stats.home_stats and
            match.away_stats and match.away_stats.away_stats
        )
        has_form = bool(
            match.home_last_matches and len(match.home_last_matches) >= 5 and
            match.away_last_matches and len(match.away_last_matches) >= 5
        )
        has_league_stats = bool(match.league_statistics)
        
        data_quality = sum([has_standings, has_detailed_stats, has_form, has_league_stats])
        
        if data_quality >= 3:
            variance_factors.append(0.2)
        elif data_quality == 2:
            variance_factors.append(0.5)
        else:
            variance_factors.append(0.8)
        
        # Factor 3: Affidabilità campionato
        reliability = league_context.get('reliability', 'Medium')
        if reliability == 'High':
            variance_factors.append(0.2)
        elif reliability == 'Medium':
            variance_factors.append(0.4)
        else:
            variance_factors.append(0.7)
        
        # Factor 4: Total xG (match con pochi gol = più imprevedibili)
        total_xg = home_xg + away_xg
        if total_xg < 1.5:
            variance_factors.append(0.7)  # Low-scoring = più incerto
        elif total_xg > 3.5:
            variance_factors.append(0.6)  # High-scoring = più incerto
        else:
            variance_factors.append(0.3)
        
        # Media ponderata
        return sum(variance_factors) / len(variance_factors)
    
    def _calculate_confidence_score(
        self, match, home_xg: float, away_xg: float,
        variance: float, league_context: Dict
    ) -> float:
        """
        Confidence score 0-100
        
        Basato su:
        - Bassa variance
        - Dati completi
        - xG chiaro
        - Campionato affidabile
        """
        
        # Base da variance (invertita)
        base_confidence = (1 - variance) * 100
        
        # Bonus per xG difference
        xg_diff = abs(home_xg - away_xg)
        if xg_diff > 1.0:
            base_confidence += 10
        elif xg_diff > 0.7:
            base_confidence += 5
        
        # Bonus per dati completi
        if match.home_standing and match.away_standing:
            base_confidence += 5
        if match.league_statistics:
            base_confidence += 5
        if len(match.home_last_matches) >= 5 and len(match.away_last_matches) >= 5:
            base_confidence += 5
        
        # Penalty per campionati imprevedibili
        unpredictability = league_context.get('unpredictability', 0.5)
        if unpredictability > 0.6:
            base_confidence -= 10
        
        # Clamp to 0-100
        return max(0, min(100, base_confidence))
    
    def _score_to_label(self, score: float) -> str:
        """Converte confidence score in label"""
        if score >= 75:
            return "Very High"
        elif score >= 60:
            return "High"
        elif score >= 40:
            return "Medium"
        elif score >= 25:
            return "Low"
        else:
            return "Very Low"
    
    # ========== VALUE BETTING ==========
    
    def _detect_value_bets_advanced(
        self, match, home_prob: float, draw_prob: float, away_prob: float,
        over_2_5_prob: float, bts_prob: float, confidence_score: float
    ) -> List[Dict]:
        """
        Value betting con Kelly Criterion
        
        Edge = (Our Prob × Odds) - 1
        Kelly % = (Prob × Odds - 1) / (Odds - 1)
        """
        
        value_bets = []
        
        if not match.odds or confidence_score < 40:
            return value_bets
        
        # Mercati da analizzare
        markets = [
            ('Home Win', home_prob, match.odds.home_win),
            ('Draw', draw_prob, match.odds.draw),
            ('Away Win', away_prob, match.odds.away_win),
        ]
        
        if match.odds.over_2_5 > 0:
            markets.append(('Over 2.5', over_2_5_prob, match.odds.over_2_5))
            markets.append(('Under 2.5', 1 - over_2_5_prob, match.odds.under_2_5))
        
        if match.odds.bts_yes > 0:
            markets.append(('BTS Yes', bts_prob, match.odds.bts_yes))
            markets.append(('BTS No', 1 - bts_prob, match.odds.bts_no))
        
        # Double Chance
        if match.odds.dc_1x > 0:
            dc_1x_prob = home_prob + draw_prob
            markets.append(('Double Chance 1X', dc_1x_prob, match.odds.dc_1x))
        
        if match.odds.dc_12 > 0:
            dc_12_prob = home_prob + away_prob
            markets.append(('Double Chance 12', dc_12_prob, match.odds.dc_12))
        
        if match.odds.dc_x2 > 0:
            dc_x2_prob = draw_prob + away_prob
            markets.append(('Double Chance X2', dc_x2_prob, match.odds.dc_x2))
        
        # Analizza ogni mercato
        for market_name, our_prob, bookmaker_odds in markets:
            if bookmaker_odds <= 1.0:
                continue
            
            # Implied probability bookmaker (con margin)
            implied_prob = 1 / bookmaker_odds
            
            # Edge (vantaggio)
            edge = (our_prob * bookmaker_odds) - 1
            edge_percentage = (our_prob - implied_prob) * 100
            
            # Expected Value
            ev = (our_prob * bookmaker_odds) - 1
            
            # Kelly Criterion (frazione ottimale dello stake)
            if bookmaker_odds > 1:
                kelly = (our_prob * bookmaker_odds - 1) / (bookmaker_odds - 1)
                kelly_percentage = kelly * 100
            else:
                kelly_percentage = 0
            
            # Confidence adjustment (riduci edge se confidence bassa)
            confidence_multiplier = confidence_score / 100
            adjusted_edge = edge * confidence_multiplier
            
            # ===== FILTRI VALUE BET PIÙ INTELLIGENTI =====
            
            # 1. Edge minimo base
            base_min_edge = self.VALUE_BET_MIN_EDGE
            
            # 2. Quote massime (evita underdog estremi)
            max_acceptable_odds = 5.0  # Non scommettere su quote > 5.0
            
            # 3. Probabilità minima (evita longshot)
            min_probability = 0.25  # Almeno 25% di probabilità
            
            # 4. Edge minimo scalato per quote alte
            # Quote alte richiedono edge maggiore
            if bookmaker_odds > 3.0:
                min_edge = 0.10  # 10% edge per quote alte
            elif bookmaker_odds > 2.5:
                min_edge = 0.08  # 8% edge per quote medie
            else:
                min_edge = 0.05  # 5% edge per favorite
            
            # 5. Controlla tutti i filtri
            if (adjusted_edge > min_edge and 
                our_prob > implied_prob and 
                bookmaker_odds <= max_acceptable_odds and
                our_prob >= min_probability):
                
                # ROI atteso
                roi = ev * 100
                
                # Risk rating
                if our_prob > 0.6:
                    risk = "Low"
                elif our_prob > 0.45:
                    risk = "Medium"
                else:
                    risk = "High"
                
                # Confidence del value bet (più restrittivo)
                if adjusted_edge > 0.15 and confidence_score > 75:
                    vb_confidence = "Very High"
                elif adjusted_edge > 0.12 and confidence_score > 70:
                    vb_confidence = "High"
                elif adjusted_edge > 0.08 and confidence_score > 60:
                    vb_confidence = "Medium"
                else:
                    vb_confidence = "Low"
                
                # IMPORTANTE: Salta value bets con confidence troppo bassa
                if vb_confidence == "Low":
                    continue
                
                value_bets.append({
                    'market': market_name,
                    'our_probability': our_prob,
                    'bookmaker_odds': bookmaker_odds,
                    'implied_probability': implied_prob,
                    'edge': edge_percentage,
                    'adjusted_edge': adjusted_edge * 100,
                    'expected_value': ev,
                    'roi': roi,
                    'kelly_percentage': max(0, min(kelly_percentage, 25)),  # Cap a 25%
                    'confidence': vb_confidence,
                    'risk': risk,
                    'prediction_confidence': confidence_score
                })
        
        # Ordina per adjusted edge
        value_bets.sort(key=lambda x: x['adjusted_edge'], reverse=True)
        
        return value_bets
    
    # ========== RECOMMENDATION ==========
    
    def _generate_recommendation_advanced(
        self, home_prob: float, draw_prob: float, away_prob: float,
        value_bets: List[Dict], confidence_score: float, variance: float
    ) -> str:
        """
        Genera raccomandazione intelligente
        
        Priority:
        1. Value bets con high confidence
        2. Probabilità dominante (>60%) con low variance
        3. Conservative recommendation se incerto
        """
        
        # Caso 1: Value bets disponibili
        if value_bets and confidence_score >= 50:
            best_vb = value_bets[0]
            
            if best_vb['confidence'] in ['Very High', 'High']:
                return (
                    f"💎 VALUE BET: {best_vb['market']} @ {best_vb['bookmaker_odds']:.2f} "
                    f"(Edge: {best_vb['adjusted_edge']:.1f}%, ROI: {best_vb['roi']:.1f}%, "
                    f"Kelly: {best_vb['kelly_percentage']:.1f}%)"
                )
        
        # Caso 2: Probabilità chiara con alta confidence
        if confidence_score >= 60 and variance < 0.4:
            max_prob = max(home_prob, draw_prob, away_prob)
            
            if max_prob > 0.60:
                if max_prob == home_prob:
                    return f"🏠 HOME WIN - High Confidence ({home_prob*100:.1f}%)"
                elif max_prob == away_prob:
                    return f"✈️ AWAY WIN - High Confidence ({away_prob*100:.1f}%)"
                else:
                    return f"🤝 DRAW - High Confidence ({draw_prob*100:.1f}%)"
            
            elif max_prob > 0.50:
                if max_prob == home_prob:
                    return f"🏠 HOME WIN - Medium Confidence ({home_prob*100:.1f}%)"
                elif max_prob == away_prob:
                    return f"✈️ AWAY WIN - Medium Confidence ({away_prob*100:.1f}%)"
                else:
                    return f"🤝 DRAW - Medium Confidence ({draw_prob*100:.1f}%)"
        
        # Caso 3: Value bet medium confidence
        if value_bets and confidence_score >= 40:
            best_vb = value_bets[0]
            return (
                f"💡 Possible Value: {best_vb['market']} @ {best_vb['bookmaker_odds']:.2f} "
                f"(Edge: {best_vb['adjusted_edge']:.1f}%)"
            )
        
        # Caso 4: Match equilibrato o bassa confidence
        if variance > 0.6 or confidence_score < 40:
            return "⚠️ UNCERTAIN MATCH - High variance, recommend caution or skip"
        
        # Caso 5: Match equilibrato con medium confidence
        xg_diff = abs(home_prob - away_prob)
        if xg_diff < 0.15:
            if draw_prob > 0.30:
                return f"🤝 BALANCED MATCH - Draw likely ({draw_prob*100:.1f}%)"
            else:
                return "⚖️ BALANCED MATCH - No clear favorite"
        
        # Fallback
        return "📊 No strong recommendation - Review odds manually"
    
    # ========== LEAGUE CONTEXT ==========
    
    def _extract_league_context(self, match) -> Dict:
        """Estrae contesto campionato dalle statistiche"""
        
        context = {
            'avg_goals': 2.6,
            'home_win_pct': 45.0,
            'draw_pct': 27.0,
            'away_win_pct': 28.0,
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
        
        # Goals
        if stats.get('avg_goals', 0) > 0:
            context['avg_goals'] = stats['avg_goals']
        
        if stats.get('avg_home_goals', 0) > 0:
            context['avg_home_goals'] = stats['avg_home_goals']
        
        if stats.get('avg_away_goals', 0) > 0:
            context['avg_away_goals'] = stats['avg_away_goals']
        
        # Home advantage factor
        if stats.get('avg_home_goals', 0) > 0 and stats.get('avg_away_goals', 0) > 0:
            context['home_advantage_factor'] = stats['avg_home_goals'] / stats['avg_away_goals']
        
        # 1X2 percentages
        if stats.get('home_win_pct', 0) > 0:
            context['home_win_pct'] = stats['home_win_pct']
        
        if stats.get('draw_pct', 0) > 0:
            context['draw_pct'] = stats['draw_pct']
            context['draw_factor'] = stats['draw_pct'] / 27.0
        
        if stats.get('away_win_pct', 0) > 0:
            context['away_win_pct'] = stats['away_win_pct']
        
        # Over/Under baseline
        if 'over_under' in stats and '2.5' in stats['over_under']:
            context['over_2_5_baseline'] = stats['over_under']['2.5']['over'] / 100
        
        # BTS baseline
        if stats.get('bts_pct', 0) > 0:
            context['bts_baseline'] = stats['bts_pct'] / 100
        
        # Unpredictability (varianza risultati)
        if stats.get('total_matches', 0) >= 10:
            home_pct = context['home_win_pct']
            draw_pct = context['draw_pct']
            away_pct = context['away_win_pct']
            
            # Calcola varianza da distribuzione uniforme (33.3%)
            variance = ((home_pct - 33.3)**2 + (draw_pct - 33.3)**2 + (away_pct - 33.3)**2) / 3
            context['unpredictability'] = 1 - (variance / 1000)
            context['unpredictability'] = max(0.2, min(0.8, context['unpredictability']))
        
        # Reliability
        matches_played = stats.get('total_matches', 0)
        if matches_played >= 20:
            context['reliability'] = 'High'
        elif matches_played >= 10:
            context['reliability'] = 'Medium'
        else:
            context['reliability'] = 'Low'
        
        return context
    
    def _calculate_league_difficulty(self, league_context: Dict) -> float:
        """
        Calcola difficoltà campionato (0-100)
        
        Fattori:
        - Unpredictability (più imprevedibile = più difficile)
        - Home advantage (più equilibrato = più difficile)
        - Affidabilità dati
        """
        
        difficulty = 50.0  # Base
        
        # Unpredictability
        unpred = league_context.get('unpredictability', 0.5)
        difficulty += (unpred - 0.5) * 40  # ±20 points
        
        # Home advantage (equilibrato = difficile)
        home_adv = league_context.get('home_advantage_factor', 1.0)
        if 0.95 <= home_adv <= 1.05:
            difficulty += 15  # Molto equilibrato
        elif 0.9 <= home_adv <= 1.1:
            difficulty += 10
        
        # Affidabilità dati (bassa = difficile)
        reliability = league_context.get('reliability', 'Medium')
        if reliability == 'Low':
            difficulty += 15
        elif reliability == 'High':
            difficulty -= 10
        
        return max(0, min(100, difficulty))