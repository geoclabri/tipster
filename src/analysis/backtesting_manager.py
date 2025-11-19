"""
src/analysis/backtesting_manager.py
Gestione archivio predictions per backtesting
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import numpy as np


class BacktestingManager:
    """
    Gestisce archivio predictions per backtesting
    
    Struttura:
    backtesting_archive/
    ├─ 2024-10-01.json
    ├─ 2024-10-02.json
    └─ ...
    """
    
    ARCHIVE_DIR = Path("backtesting_archive")
    
    def __init__(self):
        self.ARCHIVE_DIR.mkdir(exist_ok=True)
    
    # ========== SAVE PREDICTIONS ==========
    
    def save_predictions(self, date: datetime, predictions_data: List[Dict]):
        """
        Salva predictions per una data
        
        Args:
            date: Data match
            predictions_data: Lista di dict da match.to_backtesting_dict()
        """
        
        filename = self._get_filename(date)
        filepath = self.ARCHIVE_DIR / filename
        
        data = {
            'date': date.strftime('%Y-%m-%d'),
            'saved_at': datetime.now().isoformat(),
            'matches_count': len(predictions_data),
            'matches': predictions_data
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return filepath
    
    # ========== LOAD PREDICTIONS ==========
    
    def load_predictions(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[Dict]:
        """
        Carica predictions per range date
        
        Returns:
            Lista di dict con match + predictions + actual results
        """
        
        all_predictions = []
        
        # Itera su tutte le date nel range
        current_date = start_date
        while current_date <= end_date:
            filename = self._get_filename(current_date)
            filepath = self.ARCHIVE_DIR / filename
            
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    all_predictions.extend(data.get('matches', []))
            
            # Prossimo giorno
            current_date = current_date.replace(day=current_date.day + 1)
        
        return all_predictions
    
    def get_available_dates(self) -> List[str]:
        """
        Ritorna lista date disponibili in archivio
        
        Returns:
            Lista stringhe formato 'YYYY-MM-DD'
        """
        
        dates = []
        
        for filepath in sorted(self.ARCHIVE_DIR.glob("*.json")):
            date_str = filepath.stem  # Nome file senza .json
            dates.append(date_str)
        
        return dates
    
    # ========== BACKTESTING ANALYSIS ==========
    
    def analyze_predictions(
        self,
        predictions_data: List[Dict],
        filters: Dict = None
    ) -> Dict:
        """
        Analizza predictions con filtri
        
        Args:
            predictions_data: Lista predictions da load_predictions()
            filters: Dict con filtri (confidence, odds, variance, ecc)
        
        Returns:
            Dict con tutte le metriche backtesting
        """
        
        # Applica filtri
        filtered = self._apply_filters(predictions_data, filters or {})
        
        if not filtered:
            return self._empty_results()
        
        # Calcola metriche
        results = {
            'total_matches': len(filtered),
            'original_matches': len(predictions_data),
            'accuracy': self._calculate_accuracy(filtered),
            'brier_score': self._calculate_brier_score(filtered),
            'log_loss': self._calculate_log_loss(filtered),
            'calibration': self._calculate_calibration(filtered),
            'value_bets': self._analyze_value_bets(filtered, filters),
            'by_confidence': self._breakdown_by_confidence(filtered),
            'by_league': self._breakdown_by_league(filtered),
            'by_market': self._breakdown_by_market(filtered),
            'matches_details': filtered  # Per tabella dettagliata
        }
        
        return results
    
    # ========== FILTERS ==========
    
    def _apply_filters(self, predictions: List[Dict], filters: Dict) -> List[Dict]:
        """Applica filtri a predictions"""
        
        filtered = predictions.copy()
        
        # Filtra solo match con actual result
        filtered = [p for p in filtered if 'actual' in p and p['actual']]
        
        # Confidence range
        if 'min_confidence' in filters:
            min_conf = filters['min_confidence']
            filtered = [
                p for p in filtered 
                if p.get('prediction', {}).get('confidence_score', 0) >= min_conf
            ]
        
        if 'max_confidence' in filters:
            max_conf = filters['max_confidence']
            filtered = [
                p for p in filtered 
                if p.get('prediction', {}).get('confidence_score', 100) <= max_conf
            ]
        
        # Odds range (Home)
        if 'home_odds_min' in filters and 'home_odds_max' in filters:
            min_odds = filters['home_odds_min']
            max_odds = filters['home_odds_max']
            filtered = [
                p for p in filtered
                if min_odds <= p.get('odds', {}).get('home_win', 0) <= max_odds
            ]
        
        # Odds range (Draw)
        if 'draw_odds_min' in filters and 'draw_odds_max' in filters:
            min_odds = filters['draw_odds_min']
            max_odds = filters['draw_odds_max']
            filtered = [
                p for p in filtered
                if min_odds <= p.get('odds', {}).get('draw', 0) <= max_odds
            ]
        
        # Odds range (Away)
        if 'away_odds_min' in filters and 'away_odds_max' in filters:
            min_odds = filters['away_odds_min']
            max_odds = filters['away_odds_max']
            filtered = [
                p for p in filtered
                if min_odds <= p.get('odds', {}).get('away_win', 0) <= max_odds
            ]
        
        # Variance
        if 'max_variance' in filters:
            max_var = filters['max_variance']
            filtered = [
                p for p in filtered
                if p.get('prediction', {}).get('prediction_variance', 1.0) <= max_var
            ]
        
        # Value bets only
        if filters.get('value_only', False):
            filtered = [
                p for p in filtered
                if p.get('prediction', {}).get('value_bets', [])
            ]
        
        # Min edge
        if 'min_edge' in filters:
            min_edge = filters['min_edge']
            filtered = [
                p for p in filtered
                if p.get('prediction', {}).get('value_bets', []) and
                   p['prediction']['value_bets'][0].get('adjusted_edge', 0) >= min_edge
            ]
        
        # Leagues
        if 'leagues' in filters and filters['leagues']:
            selected = filters['leagues']
            filtered = [
                p for p in filtered
                if p.get('match', {}).get('league', '') in selected
            ]
        
        return filtered
    
    # ========== ACCURACY METRICS ==========
    
    def _calculate_accuracy(self, predictions: List[Dict]) -> Dict:
        """Calcola accuracy predictions"""
        
        total = len(predictions)
        if total == 0:
            return {'top_1': 0, 'top_2': 0}
        
        top_1_correct = 0
        top_2_correct = 0
        
        for pred_data in predictions:
            pred = pred_data.get('prediction', {})
            actual = pred_data.get('actual', {}).get('outcome', '')
            
            if not actual:
                continue
            
            # Top 1
            probs = [
                (pred.get('home_win_prob', 0), '1'),
                (pred.get('draw_prob', 0), 'X'),
                (pred.get('away_win_prob', 0), '2')
            ]
            
            sorted_probs = sorted(probs, key=lambda x: x[0], reverse=True)
            
            top_1 = sorted_probs[0][1]
            top_2_outcomes = [sorted_probs[0][1], sorted_probs[1][1]]
            
            if top_1 == actual:
                top_1_correct += 1
                top_2_correct += 1
            elif actual in top_2_outcomes:
                top_2_correct += 1
        
        return {
            'top_1': (top_1_correct / total) * 100,
            'top_2': (top_2_correct / total) * 100,
            'top_1_count': top_1_correct,
            'top_2_count': top_2_correct,
            'total': total
        }
    
    def _calculate_brier_score(self, predictions: List[Dict]) -> float:
        """
        Brier Score: media delle differenze al quadrato
        
        0.0 = perfetto, 0.25 = random, >0.3 = pessimo
        """
        
        if not predictions:
            return 0.0
        
        scores = []
        
        for pred_data in predictions:
            pred = pred_data.get('prediction', {})
            actual = pred_data.get('actual', {}).get('outcome', '')
            
            if not actual:
                continue
            
            # Vettore predizione [P(1), P(X), P(2)]
            pred_probs = [
                pred.get('home_win_prob', 0),
                pred.get('draw_prob', 0),
                pred.get('away_win_prob', 0)
            ]
            
            # Vettore actual [1, 0, 0] o [0, 1, 0] o [0, 0, 1]
            actual_vec = [
                1 if actual == '1' else 0,
                1 if actual == 'X' else 0,
                1 if actual == '2' else 0
            ]
            
            # Brier score = somma(pred - actual)^2
            bs = sum((p - a)**2 for p, a in zip(pred_probs, actual_vec))
            scores.append(bs)
        
        return np.mean(scores) if scores else 0.0
    
    def _calculate_log_loss(self, predictions: List[Dict]) -> float:
        """Log Loss (cross-entropy loss)"""
        
        if not predictions:
            return 0.0
        
        losses = []
        
        for pred_data in predictions:
            pred = pred_data.get('prediction', {})
            actual = pred_data.get('actual', {}).get('outcome', '')
            
            if not actual:
                continue
            
            # Probabilità predetta per outcome corretto
            if actual == '1':
                prob = pred.get('home_win_prob', 0.01)
            elif actual == 'X':
                prob = pred.get('draw_prob', 0.01)
            else:
                prob = pred.get('away_win_prob', 0.01)
            
            # Clamp per evitare log(0)
            prob = max(0.01, min(0.99, prob))
            
            # Log loss
            loss = -np.log(prob)
            losses.append(loss)
        
        return np.mean(losses) if losses else 0.0
    
    def _calculate_calibration(self, predictions: List[Dict]) -> Dict:
        """
        Calibration: raggruppa predictions per probabilità e calcola win rate reale
        
        Returns:
            Dict con bins e accuracy per bin
        """
        
        bins = {
            '0-20%': {'predicted': [], 'actual': []},
            '20-40%': {'predicted': [], 'actual': []},
            '40-60%': {'predicted': [], 'actual': []},
            '60-80%': {'predicted': [], 'actual': []},
            '80-100%': {'predicted': [], 'actual': []}
        }
        
        for pred_data in predictions:
            pred = pred_data.get('prediction', {})
            actual = pred_data.get('actual', {}).get('outcome', '')
            
            if not actual:
                continue
            
            # Trova outcome predetto e sua probabilità
            probs = [
                (pred.get('home_win_prob', 0), '1'),
                (pred.get('draw_prob', 0), 'X'),
                (pred.get('away_win_prob', 0), '2')
            ]
            
            top_prob, top_outcome = max(probs, key=lambda x: x[0])
            
            # Determina bin
            prob_pct = top_prob * 100
            
            if prob_pct < 20:
                bin_name = '0-20%'
            elif prob_pct < 40:
                bin_name = '20-40%'
            elif prob_pct < 60:
                bin_name = '40-60%'
            elif prob_pct < 80:
                bin_name = '60-80%'
            else:
                bin_name = '80-100%'
            
            bins[bin_name]['predicted'].append(top_prob)
            bins[bin_name]['actual'].append(1 if top_outcome == actual else 0)
        
        # Calcola medie per bin
        calibration_data = {}
        
        for bin_name, data in bins.items():
            if data['predicted']:
                avg_pred = np.mean(data['predicted']) * 100
                avg_actual = np.mean(data['actual']) * 100
                count = len(data['predicted'])
                
                calibration_data[bin_name] = {
                    'avg_predicted': avg_pred,
                    'avg_actual': avg_actual,
                    'count': count,
                    'diff': abs(avg_pred - avg_actual)
                }
            else:
                calibration_data[bin_name] = {
                    'avg_predicted': 0,
                    'avg_actual': 0,
                    'count': 0,
                    'diff': 0
                }
        
        return calibration_data
    
    # ========== VALUE BETS ANALYSIS ==========
    
    def _analyze_value_bets(self, predictions: List[Dict], filters: Dict) -> Dict:
        """Analizza performance value bets"""
        
        stake_per_bet = filters.get('stake_per_bet', 10)  # Default €10
        use_kelly = filters.get('use_kelly', False)
        
        bets = []
        total_staked = 0
        total_return = 0
        
        for pred_data in predictions:
            pred = pred_data.get('prediction', {})
            actual = pred_data.get('actual', {}).get('outcome', '')
            value_bets = pred.get('value_bets', [])
            
            if not value_bets or not actual:
                continue
            
            # Prendi miglior value bet
            best_vb = value_bets[0]
            market = best_vb.get('market', '')
            odds = best_vb.get('bookmaker_odds', 0)
            edge = best_vb.get('adjusted_edge', 0)
            kelly_pct = best_vb.get('kelly_percentage', 0)
            
            if odds <= 1.0:
                continue
            
            # Determina stake
            if use_kelly:
                stake = stake_per_bet * (kelly_pct / 100)
                stake = max(1, min(stake, stake_per_bet * 0.25))  # Cap a 25% bankroll
            else:
                stake = stake_per_bet
            
            # Determina se vinto
            won = self._check_bet_won(market, actual)
            
            bet_return = (stake * odds) if won else 0
            profit = bet_return - stake
            
            bets.append({
                'market': market,
                'odds': odds,
                'stake': stake,
                'return': bet_return,
                'profit': profit,
                'won': won,
                'edge': edge,
                'match': f"{pred_data['match']['home_team']} vs {pred_data['match']['away_team']}"
            })
            
            total_staked += stake
            total_return += bet_return
        
        if not bets:
            return {
                'total_bets': 0,
                'won': 0,
                'lost': 0,
                'total_staked': 0,
                'total_return': 0,
                'net_profit': 0,
                'roi': 0,
                'win_rate': 0,
                'avg_odds': 0,
                'sharpe_ratio': 0,
                'bets': []
            }
        
        won_count = sum(1 for b in bets if b['won'])
        lost_count = len(bets) - won_count
        net_profit = total_return - total_staked
        roi = (net_profit / total_staked * 100) if total_staked > 0 else 0
        win_rate = (won_count / len(bets) * 100) if bets else 0
        avg_odds = np.mean([b['odds'] for b in bets])
        
        # Sharpe Ratio (rendimento/rischio)
        profits = [b['profit'] for b in bets]
        if len(profits) > 1:
            avg_profit = np.mean(profits)
            std_profit = np.std(profits)
            sharpe = (avg_profit / std_profit) if std_profit > 0 else 0
        else:
            sharpe = 0
        
        return {
            'total_bets': len(bets),
            'won': won_count,
            'lost': lost_count,
            'total_staked': round(total_staked, 2),
            'total_return': round(total_return, 2),
            'net_profit': round(net_profit, 2),
            'roi': round(roi, 2),
            'win_rate': round(win_rate, 2),
            'avg_odds': round(avg_odds, 2),
            'sharpe_ratio': round(sharpe, 2),
            'bets': bets
        }
    
    def _check_bet_won(self, market: str, actual_outcome: str) -> bool:
        """Determina se scommessa vinta"""
        
        market_lower = market.lower()
        
        if 'home win' in market_lower or market == '1':
            return actual_outcome == '1'
        elif 'draw' in market_lower or market == 'X':
            return actual_outcome == 'X'
        elif 'away win' in market_lower or market == '2':
            return actual_outcome == '2'
        elif '1x' in market_lower:
            return actual_outcome in ['1', 'X']
        elif '12' in market_lower:
            return actual_outcome in ['1', '2']
        elif 'x2' in market_lower:
            return actual_outcome in ['X', '2']
        else:
            # Per Over/Under/BTS serve il risultato completo (non solo 1X2)
            # Per ora ritorna False
            return False
    
    # ========== BREAKDOWNS ==========
    
    def _breakdown_by_confidence(self, predictions: List[Dict]) -> Dict:
        """Raggruppa per range confidence"""
        
        ranges = {
            '75-100': [],
            '60-75': [],
            '40-60': [],
            '0-40': []
        }
        
        for pred_data in predictions:
            conf = pred_data.get('prediction', {}).get('confidence_score', 0)
            
            if conf >= 75:
                ranges['75-100'].append(pred_data)
            elif conf >= 60:
                ranges['60-75'].append(pred_data)
            elif conf >= 40:
                ranges['40-60'].append(pred_data)
            else:
                ranges['0-40'].append(pred_data)
        
        # Calcola accuracy e ROI per range
        breakdown = {}
        
        for range_name, preds in ranges.items():
            if not preds:
                breakdown[range_name] = {
                    'count': 0,
                    'accuracy': 0,
                    'roi': 0
                }
                continue
            
            accuracy = self._calculate_accuracy(preds)['top_1']
            value_analysis = self._analyze_value_bets(preds, {})
            roi = value_analysis['roi']
            
            breakdown[range_name] = {
                'count': len(preds),
                'accuracy': round(accuracy, 1),
                'roi': round(roi, 1)
            }
        
        return breakdown
    
    def _breakdown_by_league(self, predictions: List[Dict]) -> Dict:
        """Raggruppa per campionato"""
        
        leagues = {}
        
        for pred_data in predictions:
            league = pred_data.get('match', {}).get('league', 'Unknown')
            
            if league not in leagues:
                leagues[league] = []
            
            leagues[league].append(pred_data)
        
        # Calcola metriche per lega
        breakdown = {}
        
        for league, preds in leagues.items():
            accuracy = self._calculate_accuracy(preds)['top_1']
            value_analysis = self._analyze_value_bets(preds, {})
            roi = value_analysis['roi']
            
            breakdown[league] = {
                'count': len(preds),
                'accuracy': round(accuracy, 1),
                'roi': round(roi, 1)
            }
        
        # Ordina per count
        breakdown = dict(sorted(breakdown.items(), key=lambda x: x[1]['count'], reverse=True))
        
        return breakdown
    
    def _breakdown_by_market(self, predictions: List[Dict]) -> Dict:
        """Raggruppa per mercato scommesso"""
        
        markets = {}
        
        for pred_data in predictions:
            value_bets = pred_data.get('prediction', {}).get('value_bets', [])
            
            if not value_bets:
                continue
            
            market = value_bets[0].get('market', 'Unknown')
            
            if market not in markets:
                markets[market] = []
            
            markets[market].append(pred_data)
        
        # Calcola metriche per mercato
        breakdown = {}
        
        for market, preds in markets.items():
            value_analysis = self._analyze_value_bets(preds, {})
            
            breakdown[market] = {
                'count': len(preds),
                'won': value_analysis['won'],
                'lost': value_analysis['lost'],
                'roi': value_analysis['roi'],
                'win_rate': value_analysis['win_rate']
            }
        
        return breakdown
    
    # ========== UTILS ==========
    
    def _get_filename(self, date: datetime) -> str:
        """Genera nome file per data"""
        return f"{date.strftime('%Y-%m-%d')}.json"
    
    def _empty_results(self) -> Dict:
        """Ritorna risultati vuoti"""
        return {
            'total_matches': 0,
            'original_matches': 0,
            'accuracy': {'top_1': 0, 'top_2': 0, 'top_1_count': 0, 'top_2_count': 0, 'total': 0},
            'brier_score': 0,
            'log_loss': 0,
            'calibration': {},
            'value_bets': {
                'total_bets': 0,
                'won': 0,
                'lost': 0,
                'total_staked': 0,
                'total_return': 0,
                'net_profit': 0,
                'roi': 0,
                'win_rate': 0,
                'avg_odds': 0,
                'sharpe_ratio': 0,
                'bets': []
            },
            'by_confidence': {},
            'by_league': {},
            'by_market': {},
            'matches_details': []
        }