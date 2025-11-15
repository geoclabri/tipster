"""
src/utils/validators.py
Funzioni di validazione e pulizia dati
"""

from datetime import datetime
from typing import Optional


def validate_date(date_str: str) -> Optional[datetime]:
    """
    Valida e converte stringa data in datetime
    
    Args:
        date_str: Stringa data formato YYYY-MM-DD
        
    Returns:
        datetime object se valida, None altrimenti
        
    Examples:
        >>> validate_date("2024-11-10")
        datetime.datetime(2024, 11, 10, 0, 0)
        
        >>> validate_date("invalid")
        None
    """
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except (ValueError, TypeError):
        return None


def validate_odds(value: float) -> bool:
    """
    Valida se una quota è nel range accettabile
    
    Args:
        value: Valore quota
        
    Returns:
        True se quota valida (tra 1.0 e 1000.0)
        
    Examples:
        >>> validate_odds(2.50)
        True
        
        >>> validate_odds(0.5)
        False
    """
    try:
        return 1.0 <= float(value) <= 1000.0
    except (ValueError, TypeError):
        return False


def clean_team_name(name: str) -> str:
    """
    Pulisce il nome di una squadra rimuovendo caratteri speciali
    
    Args:
        name: Nome grezzo della squadra
        
    Returns:
        Nome pulito
        
    Examples:
        >>> clean_team_name("  Milan   \\n \\t ")
        'Milan'
        
        >>> clean_team_name("Manchester\\nUnited")
        'Manchester United'
    """
    if not name:
        return ""
    
    # Rimuovi spazi multipli e whitespace
    name = ' '.join(name.split())
    
    # Rimuovi caratteri speciali comuni
    replacements = {
        '\n': ' ',
        '\r': '',
        '\t': ' ',
        '  ': ' ',
    }
    
    for old, new in replacements.items():
        name = name.replace(old, new)
    
    return name.strip()


def validate_url(url: str) -> bool:
    """
    Valida se una URL è ben formata
    
    Args:
        url: URL da validare
        
    Returns:
        True se URL valida
    """
    if not url:
        return False
    
    url_lower = url.lower()
    return (url_lower.startswith('http://') or 
            url_lower.startswith('https://'))


def parse_time(time_str: str) -> Optional[tuple]:
    """
    Parse stringa orario in formato HH:MM
    
    Args:
        time_str: Stringa orario (es: "15:30")
        
    Returns:
        Tupla (ore, minuti) o None se invalida
        
    Examples:
        >>> parse_time("15:30")
        (15, 30)
        
        >>> parse_time("25:70")
        None
    """
    try:
        parts = time_str.split(':')
        if len(parts) != 2:
            return None
        
        hour = int(parts[0])
        minute = int(parts[1])
        
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return (hour, minute)
        
        return None
    except (ValueError, AttributeError):
        return None
