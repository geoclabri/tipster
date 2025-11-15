"""
gui.py - Analytica Bet
Interfaccia grafica professionale con salvataggio layout
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
from datetime import datetime, timedelta
import asyncio
import threading
from pathlib import Path
import sys
import json

sys.path.insert(0, str(Path(__file__).parent))

from src.scraper.match_scraper import MatchScraper
from src.models.match_data import MatchCollection
from src.utils.config import Config
from src.utils.logger import setup_logger
from src.analysis.prediction_engine import PredictionEngine, MatchPrediction
from src.analysis.league_analyzer import LeagueAnalyzer, LeagueStats

logger = setup_logger(__name__)


class ToolTip:
    """
    Crea tooltip al passaggio del mouse
    """
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.widget.bind('<Enter>', self.show_tip)
        self.widget.bind('<Leave>', self.hide_tip)
    
    def show_tip(self, event=None):
        if self.tip_window or not self.text:
            return
        
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                        background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                        font=("Segoe UI", 9, "normal"), padx=8, pady=6)
        label.pack()
    
    def hide_tip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None

class AnalyticaBetGUI:
    """GUI professionale per Analytica Bet"""
    
    # File per salvare layout
    SETTINGS_FILE = "analytica_settings.json"
    
    # Tema colori moderno
    COLORS = {
        'primary': '#2C3E50',      # Blu scuro
        'secondary': '#3498DB',    # Blu
        'accent': '#E74C3C',       # Rosso
        'success': '#27AE60',      # Verde
        'warning': '#F39C12',      # Arancione
        'bg_dark': '#34495E',      # Grigio scuro
        'bg_light': '#ECF0F1',     # Grigio chiaro
        'text_dark': '#2C3E50',    # Testo scuro
        'text_light': '#FFFFFF',   # Testo chiaro
        'row_even': '#FFFFFF',     # Righe pari
        'row_odd': '#F8F9FA',      # Righe dispari
        'selected': '#D6EAF8',     # Selezione
    }

    COLUMN_TOOLTIPS = {
        'Ora': 'Match time (local)',
        'Lega': 'League/Competition name',
        'Casa': 'Home team',
        'Trasf': 'Away team',
        '1': 'Home win odds',
        'X': 'Draw odds',
        '2': 'Away win odds',
        '1X': 'Double Chance: Home win or Draw',
        '12': 'Double Chance: Home or Away win (no draw)',
        'X2': 'Double Chance: Draw or Away win',
        'O1.5': 'Over 1.5 goals odds',
        'O2.5': 'Over 2.5 goals odds',
        'O3.5': 'Over 3.5 goals odds',
        'H_Pos': 'Home team league position',
        'A_Pos': 'Away team league position',
        'H_Pts': 'Home team total points',
        'A_Pts': 'Away team total points',
        'H_GF': 'Home team goals scored (overall)',
        'H_GS': 'Home team goals conceded (overall)',
        'A_GF': 'Away team goals scored (overall)',
        'A_GS': 'Away team goals conceded (overall)',
        'H_GF_Home': 'Home team goals scored at home',
        'A_GF_Away': 'Away team goals scored away',
        'H_GF_L5': 'Home team goals scored (last 5 matches)',
        'H_GS_L5': 'Home team goals conceded (last 5 matches)',
        'A_GF_L5': 'Away team goals scored (last 5 matches)',
        'A_GS_L5': 'Away team goals conceded (last 5 matches)',
        'H_GF_H_L5': 'Home team goals scored at home (last 5 home matches)',
        'A_GF_A_L5': 'Away team goals scored away (last 5 away matches)',
        'Form H': 'Home team form (W=Win, D=Draw, L=Loss)',
        'Form A': 'Away team form (W=Win, D=Draw, L=Loss)'
    }
    
    def __init__(self, root):
        self.root = root
        self.root.title("⚽ Analytica Bet - Professional Betting Analysis")
        
        self.config = Config()
        self.matches = []
        self.is_scraping = False
        self.selected_match = None
        self.league_analyzer = LeagueAnalyzer()
        self.prediction_engine = PredictionEngine(league_analyzer=self.league_analyzer)
        self.current_prediction = None
        
        # Carica impostazioni salvate
        self.settings = self.load_settings()
        
        # Applica geometria salvata
        geometry = self.settings.get('geometry', '1400x850')
        self.root.geometry(geometry)
        
        self.setup_style()
        self.create_widgets()
        
        # Applica larghezze colonne salvate
        self.apply_column_widths()
        
        # Centra finestra solo al primo avvio
        if 'geometry' not in self.settings:
            self.center_window()
        
        # Salva impostazioni alla chiusura
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def load_settings(self):
        """Carica impostazioni da file JSON"""
        try:
            if Path(self.SETTINGS_FILE).exists():
                with open(self.SETTINGS_FILE, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Impossibile caricare impostazioni: {e}")
        
        return {}
    
    def save_settings(self):
        """Salva impostazioni correnti"""
        try:
            # Salva geometria finestra
            self.settings['geometry'] = self.root.geometry()
            
            # Salva larghezze colonne
            column_widths = {}
            for col in self.tree['columns']:
                column_widths[col] = self.tree.column(col, 'width')
            self.settings['column_widths'] = column_widths
            
            # Salva stato filtri
            self.settings['filters'] = {
                'hide_no_odds': self.filter_no_odds_var.get(),
                'hide_no_stats': self.filter_no_stats_var.get()
            }
            
            # Salva su file
            with open(self.SETTINGS_FILE, 'w') as f:
                json.dump(self.settings, f, indent=2)
            
            logger.info("Impostazioni salvate")
        except Exception as e:
            logger.error(f"Errore salvataggio impostazioni: {e}")
    
    def apply_column_widths(self):
        """Applica larghezze colonne salvate"""
        if 'column_widths' in self.settings:
            for col, width in self.settings['column_widths'].items():
                try:
                    self.tree.column(col, width=width)
                except:
                    pass
        
        # Applica stato filtri salvati
        if 'filters' in self.settings:
            self.filter_no_odds_var.set(self.settings['filters'].get('hide_no_odds', False))
            self.filter_no_stats_var.set(self.settings['filters'].get('hide_no_stats', False))
    
    
    def on_closing(self):
        """Gestisce chiusura applicazione"""
        self.save_settings()
        self.root.destroy()
        
    def setup_style(self):
        """Configura tema visivo moderno"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # ===== STILI GENERALI =====
        self.root.configure(bg=self.COLORS['bg_light'])
        
        # Frame
        style.configure('TFrame', background=self.COLORS['bg_light'])
        style.configure('Card.TFrame', background=self.COLORS['row_even'], 
                       relief='raised', borderwidth=1)
        
        # Label
        style.configure('TLabel', 
                       background=self.COLORS['bg_light'],
                       foreground=self.COLORS['text_dark'],
                       font=('Segoe UI', 10))
        
        style.configure('Title.TLabel', 
                       font=('Segoe UI', 20, 'bold'),
                       foreground=self.COLORS['primary'])
        
        style.configure('Subtitle.TLabel',
                       font=('Segoe UI', 10),
                       foreground=self.COLORS['bg_dark'])
        
        style.configure('Header.TLabel',
                       font=('Segoe UI', 11, 'bold'),
                       foreground=self.COLORS['primary'])
        
        # Bottoni
        style.configure('Big.TButton',
                       font=('Segoe UI', 12, 'bold'),
                       padding=12,
                       background=self.COLORS['secondary'],
                       foreground=self.COLORS['text_light'])
        
        style.map('Big.TButton',
                 background=[('active', self.COLORS['primary']),
                           ('pressed', self.COLORS['bg_dark'])])
        
        style.configure('Action.TButton',
                       font=('Segoe UI', 9),
                       padding=8)
        
        # LabelFrame
        style.configure('TLabelframe',
                       background=self.COLORS['bg_light'],
                       foreground=self.COLORS['primary'],
                       font=('Segoe UI', 10, 'bold'),
                       relief='groove',
                       borderwidth=2)
        
        style.configure('TLabelframe.Label',
                       background=self.COLORS['bg_light'],
                       foreground=self.COLORS['primary'],
                       font=('Segoe UI', 10, 'bold'))
        
        # Treeview (Tabella)
        style.configure('Treeview',
                       background=self.COLORS['row_even'],
                       foreground=self.COLORS['text_dark'],
                       fieldbackground=self.COLORS['row_even'],
                       font=('Segoe UI', 9),
                       rowheight=28,
                       borderwidth=0)
        
        style.configure('Treeview.Heading',
                       background=self.COLORS['primary'],
                       foreground=self.COLORS['text_light'],
                       font=('Segoe UI', 9, 'bold'),
                       relief='raised',
                       borderwidth=1)
        
        style.map('Treeview.Heading',
                 background=[('active', self.COLORS['secondary'])])
        
        style.map('Treeview',
                 background=[('selected', self.COLORS['selected'])],
                 foreground=[('selected', self.COLORS['text_dark'])])
        
        # Progressbar
        style.configure('TProgressbar',
                       background=self.COLORS['secondary'],
                       troughcolor=self.COLORS['bg_light'],
                       borderwidth=0,
                       thickness=20)
        
    def center_window(self):
        """Centra finestra"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        
    def create_widgets(self):
        """Crea interfaccia moderna"""
        
        # ===== HEADER =====
        header_frame = ttk.Frame(self.root, padding="15", style='Card.TFrame')
        header_frame.pack(fill=tk.X, padx=10, pady=10)
        
        title_container = ttk.Frame(header_frame)
        title_container.pack()
        
        ttk.Label(title_container, 
                 text="⚽ Analytica Bet", 
                 style='Title.TLabel').pack()
        ttk.Label(title_container,
                 text="Professional Football Betting Analysis & Statistics",
                 style='Subtitle.TLabel').pack(pady=(0, 5))
        
        ttk.Separator(self.root, orient='horizontal').pack(fill=tk.X, padx=10)
        
        # ===== CONTROLLI =====
        controls_frame = ttk.LabelFrame(self.root, text="⚙️ Controls", padding="15")
        controls_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Riga 1: Data
        date_frame = ttk.Frame(controls_frame)
        date_frame.pack(fill=tk.X, pady=8)
        
        ttk.Label(date_frame, text="📅 Date:", style='Header.TLabel').pack(side=tk.LEFT, padx=5)
        
        self.date_var = tk.StringVar(value=datetime.now().strftime('%Y-%m-%d'))
        date_entry = ttk.Entry(date_frame, textvariable=self.date_var, 
                              width=15, font=('Segoe UI', 10))
        date_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(date_frame, text="Today", 
                  command=lambda: self.date_var.set(datetime.now().strftime('%Y-%m-%d')),
                  width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(date_frame, text="Tomorrow",
                  command=lambda: self.date_var.set((datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')),
                  width=10).pack(side=tk.LEFT, padx=2)
        
        self.download_details_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            date_frame,
            text="📊 Download complete details (odds, stats, standings)",
            variable=self.download_details_var
        ).pack(side=tk.LEFT, padx=20)
        
        # Riga 2: Bottone principale
        button_frame = ttk.Frame(controls_frame)
        button_frame.pack(pady=10)
        
        self.scrape_button = ttk.Button(
            button_frame,
            text="🔄 UPDATE MATCHES",
            command=self.start_scraping,
            style='Big.TButton',
            width=40
        )
        self.scrape_button.pack()
        
        # Riga 3: FILTRI INTELLIGENTI
        filters_frame = ttk.Frame(controls_frame)
        filters_frame.pack(pady=10)
        
        ttk.Label(filters_frame, text="🔍 Smart Filters:", 
                 style='Header.TLabel').pack(side=tk.LEFT, padx=10)
        
        # Checkbox filtri
        self.filter_no_odds_var = tk.BooleanVar(value=False)
        self.filter_no_stats_var = tk.BooleanVar(value=False)
        
        self.filter_no_odds_check = ttk.Checkbutton(
            filters_frame,
            text="Hide matches without odds",
            variable=self.filter_no_odds_var,
            command=self.apply_filters
        )
        self.filter_no_odds_check.pack(side=tk.LEFT, padx=5)
        
        self.filter_no_stats_check = ttk.Checkbutton(
            filters_frame,
            text="Hide matches without statistics",
            variable=self.filter_no_stats_var,
            command=self.apply_filters
        )
        self.filter_no_stats_check.pack(side=tk.LEFT, padx=5)
        
        # Bottone reset filtri
        ttk.Button(filters_frame, text="↻ Reset Filters",
                  command=self.reset_filters,
                  style='Action.TButton',
                  width=15).pack(side=tk.LEFT, padx=10)
        
        # Progress
        progress_frame = ttk.Frame(controls_frame)
        progress_frame.pack(fill=tk.X, pady=5)
        
        self.progress_var = tk.StringVar(value="Ready")
        ttk.Label(progress_frame, textvariable=self.progress_var,
                 font=('Segoe UI', 9, 'italic')).pack()
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='indeterminate', length=800)
        self.progress_bar.pack(pady=5)
        
        # ===== STATISTICHE =====
        stats_frame = ttk.LabelFrame(self.root, text="📈 Statistics", padding="12")
        stats_frame.pack(fill=tk.X, padx=10, pady=5)
        
        stats_grid = ttk.Frame(stats_frame)
        stats_grid.pack()
        
        self.stats_labels = {}
        stats_items = [
            ('matches', 'Matches:', '0', self.COLORS['primary']),
            ('leagues', 'Leagues:', '0', self.COLORS['secondary']),
            ('with_odds', 'With Odds:', '0', self.COLORS['success']),
            ('with_stats', 'With Stats:', '0', self.COLORS['warning']),
            ('with_standing', 'With Standings:', '0', self.COLORS['accent']),
        ]
        
        for i, (key, label, default, color) in enumerate(stats_items):
            row = i // 3
            col = (i % 3) * 2
            
            label_widget = ttk.Label(stats_grid, text=label, font=('Segoe UI', 10, 'bold'))
            label_widget.grid(row=row, column=col, sticky=tk.W, padx=10, pady=5)
            
            value_label = tk.Label(stats_grid, text=default, 
                                  font=('Segoe UI', 11, 'bold'),
                                  fg=color, bg=self.COLORS['bg_light'])
            value_label.grid(row=row, column=col+1, sticky=tk.W, padx=5, pady=5)
            self.stats_labels[key] = value_label
        
        # ===== TABELLA E DETTAGLI =====
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Pannello sinistro: Tabella
        left_frame = ttk.LabelFrame(main_paned, text="📋 Match List", padding="5")
        main_paned.add(left_frame, weight=3)
        
        # Frame per tabella con bordo
        table_container = tk.Frame(left_frame, bg=self.COLORS['primary'], 
                                  relief='solid', borderwidth=2)
        table_container.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbar
        table_scroll = ttk.Scrollbar(table_container)
        table_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Treeview
        columns = (
            # Info base
            'Ora', 'Lega', 'Casa', 'Trasf',
            
            # Quote 1X2
            '1', 'X', '2',
            
            # Quote Double Chance
            '1X', '12', 'X2',
            
            # Quote Over/Under
            'O1.5', 'O2.5', 'O3.5',
            
            # Classifica
            'H_Pos', 'A_Pos', 'H_Pts', 'A_Pts',
            
            # Gol Totali (Overall)
            'H_GF', 'H_GS', 'A_GF', 'A_GS',
            
            # Gol Casa/Trasferta
            'H_GF_Home', 'A_GF_Away',
            
            # Gol Ultimi 5 (Overall)
            'H_GF_L5', 'H_GS_L5', 'A_GF_L5', 'A_GS_L5',
            
            # Gol Ultimi 5 Casa/Trasferta
            'H_GF_H_L5', 'A_GF_A_L5',
            
            # Form
            'Form H', 'Form A'
        )

        self.tree = ttk.Treeview(
            left_frame, 
            columns=columns, 
            show='headings', 
            yscrollcommand=table_scroll.set, 
            height=20
        )
        table_scroll.config(command=self.tree.yview)

        # Larghezze colonne
        widths = [
            50,   # Ora
            200,  # Lega (NON troncata più)
            110,  # Casa
            110,  # Trasf
            40,   # 1
            40,   # X
            40,   # 2
            40,   # 1X
            40,   # 12
            40,   # X2
            45,   # O1.5
            45,   # O2.5
            45,   # O3.5
            40,   # H_Pos
            40,   # A_Pos
            40,   # H_Pts
            40,   # A_Pts
            40,   # H_GF
            40,   # H_GS
            40,   # A_GF
            40,   # A_GS
            50,   # H_GF_Home
            50,   # A_GF_Away
            45,   # H_GF_L5
            45,   # H_GS_L5
            45,   # A_GF_L5
            45,   # A_GS_L5
            50,   # H_GF_H_L5
            50,   # A_GF_A_L5
            60,   # Form H
            60,   # Form A
        ]

        for col, width in zip(columns, widths):
            self.tree.heading(col, text=col)
            
            # Allineamento: centro per numeri, sinistra per testo
            if col in ['Ora', 'Lega', 'Casa', 'Trasf', 'Form H', 'Form A']:
                align = tk.W
            else:
                align = tk.CENTER
            
            # IMPORTANTE: minwidth più basso per permettere resize, stretch=True
            self.tree.column(col, width=width, minwidth=50, anchor=align, stretch=True)

        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind('<<TreeviewSelect>>', self.on_match_select)
        
        # Tag per righe alternate
        self.tree.tag_configure('evenrow', background=self.COLORS['row_even'])
        self.tree.tag_configure('oddrow', background=self.COLORS['row_odd'])
        
        # Pannello destro: Dettagli
        right_frame = ttk.LabelFrame(main_paned, text="🔍 Match Details", padding="5")
        main_paned.add(right_frame, weight=2)
        
        self.details_text = scrolledtext.ScrolledText(right_frame, wrap=tk.WORD,
                                                     width=45, height=28,
                                                     font=('Consolas', 9),
                                                     bg=self.COLORS['row_even'],
                                                     fg=self.COLORS['text_dark'],
                                                     relief='solid',
                                                     borderwidth=2)
        self.details_text.pack(fill=tk.BOTH, expand=True)
        self.details_text.insert('1.0', 'Select a match to view details...')
        self.details_text.config(state='disabled')
        
        # ===== BOTTONI AZIONI =====
        actions_frame = ttk.Frame(self.root, padding="10")
        actions_frame.pack(fill=tk.X)
        
        btn_style = {'width': 18, 'style': 'Action.TButton'}
        
        ttk.Button(actions_frame, text="💾 Save Excel", 
                  command=self.save_excel, **btn_style).pack(side=tk.LEFT, padx=5)
        ttk.Button(actions_frame, text="📊 Save CSV",
                  command=self.save_csv, **btn_style).pack(side=tk.LEFT, padx=5)
        ttk.Button(actions_frame, text="📋 Save JSON",
                  command=self.save_json, **btn_style).pack(side=tk.LEFT, padx=5)
        ttk.Button(actions_frame, text="🔍 Filter Leagues",
                  command=self.filter_leagues, **btn_style).pack(side=tk.LEFT, padx=5)
        ttk.Button(actions_frame, text="🗑️ Clear",
                  command=self.clear_results, **btn_style).pack(side=tk.LEFT, padx=5)
        ttk.Button(actions_frame, text="🔮 Predict All Matches",
          command=self.predict_all_matches, **btn_style).pack(side=tk.LEFT, padx=5)
        
        # ===== STATUS BAR =====
        status_frame = tk.Frame(self.root, bg=self.COLORS['primary'], height=30)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_var = tk.StringVar(value="Ready - Analytica Bet v1.0")
        status_label = tk.Label(status_frame, textvariable=self.status_var,
                               bg=self.COLORS['primary'], fg=self.COLORS['text_light'],
                               font=('Segoe UI', 9), anchor=tk.W, padx=10)
        status_label.pack(fill=tk.X)

    def _on_tree_motion(self, event):
        """Gestisce tooltip sugli header delle colonne"""
        region = self.tree.identify_region(event.x, event.y)
        
        if region == "heading":
            column = self.tree.identify_column(event.x)
            col_index = int(column.replace('#', '')) - 1
            
            if 0 <= col_index < len(self.tree['columns']):
                col_name = self.tree['columns'][col_index]
                
                if col_name in self.COLUMN_TOOLTIPS:
                    tooltip_text = self.COLUMN_TOOLTIPS[col_name]
                    
                    # Mostra tooltip
                    if not hasattr(self, 'tooltip_window') or not self.tooltip_window:
                        x = event.x_root + 10
                        y = event.y_root + 10
                        
                        self.tooltip_window = tw = tk.Toplevel(self.tree)
                        tw.wm_overrideredirect(True)
                        tw.wm_geometry(f"+{x}+{y}")
                        
                        label = tk.Label(tw, text=tooltip_text, justify=tk.LEFT,
                                        background="#2C3E50", foreground="white",
                                        relief=tk.SOLID, borderwidth=1,
                                        font=("Segoe UI", 9, "bold"), padx=10, pady=5)
                        label.pack()
                    return
        
        # Nascondi tooltip se non su header
        if hasattr(self, 'tooltip_window') and self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


    def predict_all_matches(self):
        """Genera predizioni per tutte le partite e esporta"""
        if not self.matches:
            messagebox.showwarning("Warning", "No matches to analyze!")
            return
        
        # Conferma
        result = messagebox.askyesno(
            "Batch Prediction",
            f"Generate predictions for {len(self.matches)} matches?\n\n"
            "This may take a few seconds..."
        )
        
        if not result:
            return
        
        self.status_var.set("Generating predictions...")
        self.root.update()
        
        try:
            # Genera predizioni
            predictions_data = []
            
            for i, match in enumerate(self.matches, 1):
                self.status_var.set(f"Analyzing match {i}/{len(self.matches)}...")
                self.root.update()
                
                try:
                    pred = self.prediction_engine.predict_match(match, self.matches)
                    
                    # Crea row per export
                    row = {
                        'Time': match.time.strftime('%H:%M'),
                        'League': match.league,
                        'Home': match.home_team,
                        'Away': match.away_team,
                        'Home_xG': round(pred.home_xg, 2),
                        'Away_xG': round(pred.away_xg, 2),
                        'Total_xG': round(pred.total_xg, 2),
                        'Home_Win_%': round(pred.home_win_prob * 100, 1),
                        'Draw_%': round(pred.draw_prob * 100, 1),
                        'Away_Win_%': round(pred.away_win_prob * 100, 1),
                        'Over2.5_%': round(pred.over_2_5_prob * 100, 1),
                        'BTS_%': round(pred.bts_yes_prob * 100, 1),
                        'Top_Score': pred.exact_scores[0][0] if pred.exact_scores else 'N/A',
                        'Value_Bets': len(pred.value_bets),
                        'Best_Value': pred.value_bets[0]['market'] if pred.value_bets else 'None',
                        'Recommendation': pred.recommended_bet,
                        'Confidence': pred.confidence,
                        'Elo_Home': round(pred.elo_home),
                        'Elo_Away': round(pred.elo_away),
                        'Elo_Diff': round(pred.elo_diff)
                    }
                    
                    predictions_data.append(row)
                    
                except Exception as e:
                    logger.error(f"Error predicting {match.home_team} vs {match.away_team}: {e}")
            
            # Salva CSV
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")],
                initialfile=f"predictions_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
            )
            
            if filename:
                import pandas as pd
                df = pd.DataFrame(predictions_data)
                df.to_csv(filename, index=False)
                
                self.status_var.set(f"✓ Predictions saved: {filename}")
                messagebox.showinfo("Success", 
                    f"Predictions generated for {len(predictions_data)} matches!\n\n"
                    f"File saved: {filename}\n\n"
                    f"Value bets found: {sum(1 for p in predictions_data if p['Value_Bets'] > 0)}"
                )
        
        except Exception as e:
            messagebox.showerror("Error", f"Prediction error:\n\n{str(e)}")
            self.status_var.set("Error generating predictions")
    
    def populate_table(self, matches):
        """Popola tabella con TUTTI i dati richiesti"""
        # Pulisci tabella
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Ordina per orario
        sorted_matches = sorted(matches, key=lambda m: m.time)
        
        for match in sorted_matches:
            values = []
            
            # ===== INFO BASE =====
            values.append(match.time.strftime('%H:%M'))
            
            # LEGA - NOME COMPLETO senza troncamento
            values.append(match.league)
            
            values.append(match.home_team)
            values.append(match.away_team)
            
            # ===== QUOTE 1X2 =====
            if match.odds and match.odds.home_win > 0:
                values.extend([
                    f"{match.odds.home_win:.2f}",
                    f"{match.odds.draw:.2f}",
                    f"{match.odds.away_win:.2f}"
                ])
            else:
                values.extend(['-', '-', '-'])
            
            # ===== QUOTE DOUBLE CHANCE =====
            if match.odds and match.odds.dc_1x > 0:
                values.extend([
                    f"{match.odds.dc_1x:.2f}",
                    f"{match.odds.dc_12:.2f}",
                    f"{match.odds.dc_x2:.2f}"
                ])
            else:
                values.extend(['-', '-', '-'])
            
            # ===== OVER/UNDER =====
            if match.odds:
                values.extend([
                    f"{match.odds.over_1_5:.2f}" if match.odds.over_1_5 > 0 else '-',
                    f"{match.odds.over_2_5:.2f}" if match.odds.over_2_5 > 0 else '-',
                    f"{match.odds.over_3_5:.2f}" if match.odds.over_3_5 > 0 else '-'
                ])
            else:
                values.extend(['-', '-', '-'])
            
            # ===== CLASSIFICA (Posizione + Punti) =====
            if match.home_standing:
                values.append(str(match.home_standing.position) if match.home_standing.position > 0 else '-')
            else:
                values.append('-')
            
            if match.away_standing:
                values.append(str(match.away_standing.position) if match.away_standing.position > 0 else '-')
            else:
                values.append('-')
            
            if match.home_standing and match.home_standing.points > 0:
                values.append(str(match.home_standing.points))
            else:
                values.append('-')
            
            if match.away_standing and match.away_standing.points > 0:
                values.append(str(match.away_standing.points))
            else:
                values.append('-')
            
            # ===== GOL TOTALI (Overall) =====
            if match.home_stats:
                values.append(str(match.home_stats.goals_for) if match.home_stats.goals_for > 0 else '-')
                values.append(str(match.home_stats.goals_against) if match.home_stats.goals_against > 0 else '-')
            else:
                values.extend(['-', '-'])
            
            if match.away_stats:
                values.append(str(match.away_stats.goals_for) if match.away_stats.goals_for > 0 else '-')
                values.append(str(match.away_stats.goals_against) if match.away_stats.goals_against > 0 else '-')
            else:
                values.extend(['-', '-'])
            
            # ===== GOL CASA/TRASFERTA =====
            # Casa: gol fatti in casa
            if match.home_stats and match.home_stats.home_stats:
                values.append(str(match.home_stats.home_stats.goals_for) if match.home_stats.home_stats.goals_for > 0 else '-')
            else:
                values.append('-')
            
            # Trasferta: gol fatti fuori
            if match.away_stats and match.away_stats.away_stats:
                values.append(str(match.away_stats.away_stats.goals_for) if match.away_stats.away_stats.goals_for > 0 else '-')
            else:
                values.append('-')
            
            # ===== GOL ULTIMI 5 (Overall) =====
            # Casa
            if match.home_last_matches and len(match.home_last_matches) >= 5:
                gf_l5, gs_l5 = self._calculate_goals_last_n(match.home_last_matches[:5], match.home_team)
                values.append(str(gf_l5))
                values.append(str(gs_l5))
            else:
                values.extend(['-', '-'])
            
            # Trasferta
            if match.away_last_matches and len(match.away_last_matches) >= 5:
                gf_l5, gs_l5 = self._calculate_goals_last_n(match.away_last_matches[:5], match.away_team)
                values.append(str(gf_l5))
                values.append(str(gs_l5))
            else:
                values.extend(['-', '-'])
            
            # ===== GOL ULTIMI 5 CASA/TRASFERTA =====
            # Casa: ultimi 5 in casa
            if match.home_last_matches:
                home_matches_at_home = [m for m in match.home_last_matches if m['home_team'].lower() == match.home_team.lower()][:5]
                if home_matches_at_home:
                    gf_h_l5, _ = self._calculate_goals_last_n(home_matches_at_home, match.home_team)
                    values.append(str(gf_h_l5))
                else:
                    values.append('-')
            else:
                values.append('-')
            
            # Trasferta: ultimi 5 fuori
            if match.away_last_matches:
                away_matches_away = [m for m in match.away_last_matches if m['away_team'].lower() == match.away_team.lower()][:5]
                if away_matches_away:
                    gf_a_l5, _ = self._calculate_goals_last_n(away_matches_away, match.away_team)
                    values.append(str(gf_a_l5))
                else:
                    values.append('-')
            else:
                values.append('-')
            
            # ===== FORM =====
            values.append(match.get_home_form_string(5) or '-')
            values.append(match.get_away_form_string(5) or '-')
            
            # Inserisci nella tabella
            self.tree.insert('', tk.END, values=values, tags=(match.url,))
        
        self.status_var.set(f"Visualizzate {len(sorted_matches)} partite")
    
    def _calculate_goals_last_n(self, matches, team_name):
        """
        Calcola gol fatti e subiti negli ultimi N match
        
        Args:
            matches: Lista di dict con 'home_team', 'away_team', 'score'
            team_name: Nome della squadra
        
        Returns:
            tuple: (gol_fatti, gol_subiti)
        """
        goals_for = 0
        goals_against = 0
        
        for match in matches:
            score = match.get('score', '')
            
            # Parse score "2 - 1"
            try:
                parts = score.split('-')
                if len(parts) == 2:
                    home_goals = int(parts[0].strip())
                    away_goals = int(parts[1].strip())
                    
                    # Determina se la squadra era in casa o fuori
                    if match['home_team'].lower() == team_name.lower():
                        goals_for += home_goals
                        goals_against += away_goals
                    elif match['away_team'].lower() == team_name.lower():
                        goals_for += away_goals
                        goals_against += home_goals
            except:
                pass
        
        return goals_for, goals_against

    def _extract_match_values(self, match):
        """Estrae tutti i valori per una partita"""
        values = []
        
        # Info base
        values.append(match.time.strftime('%H:%M'))
        values.append(match.league)
        values.append(match.home_team)
        values.append(match.away_team)
        
        # Quote 1X2
        if match.odds and match.odds.home_win > 0:
            values.extend([f"{match.odds.home_win:.2f}", f"{match.odds.draw:.2f}", f"{match.odds.away_win:.2f}"])
        else:
            values.extend(['-', '-', '-'])
        
        # Double Chance
        if match.odds and match.odds.dc_1x > 0:
            values.extend([f"{match.odds.dc_1x:.2f}", f"{match.odds.dc_12:.2f}", f"{match.odds.dc_x2:.2f}"])
        else:
            values.extend(['-', '-', '-'])
        
        # Over/Under
        if match.odds:
            values.extend([
                f"{match.odds.over_1_5:.2f}" if match.odds.over_1_5 > 0 else '-',
                f"{match.odds.over_2_5:.2f}" if match.odds.over_2_5 > 0 else '-',
                f"{match.odds.over_3_5:.2f}" if match.odds.over_3_5 > 0 else '-'
            ])
        else:
            values.extend(['-', '-', '-'])
        
        # Classifica
        values.append(str(match.home_standing.position) if match.home_standing and match.home_standing.position > 0 else '-')
        values.append(str(match.away_standing.position) if match.away_standing and match.away_standing.position > 0 else '-')
        values.append(str(match.home_standing.points) if match.home_standing and match.home_standing.points > 0 else '-')
        values.append(str(match.away_standing.points) if match.away_standing and match.away_standing.points > 0 else '-')
        
        # Gol totali
        if match.home_stats:
            values.extend([
                str(match.home_stats.goals_for) if match.home_stats.goals_for > 0 else '-',
                str(match.home_stats.goals_against) if match.home_stats.goals_against > 0 else '-'
            ])
        else:
            values.extend(['-', '-'])
        
        if match.away_stats:
            values.extend([
                str(match.away_stats.goals_for) if match.away_stats.goals_for > 0 else '-',
                str(match.away_stats.goals_against) if match.away_stats.goals_against > 0 else '-'
            ])
        else:
            values.extend(['-', '-'])
        
        # Gol casa/trasferta
        if match.home_stats and match.home_stats.home_stats:
            values.append(str(match.home_stats.home_stats.goals_for) if match.home_stats.home_stats.goals_for > 0 else '-')
        else:
            values.append('-')
        
        if match.away_stats and match.away_stats.away_stats:
            values.append(str(match.away_stats.away_stats.goals_for) if match.away_stats.away_stats.goals_for > 0 else '-')
        else:
            values.append('-')
        
        # Gol ultimi 5 overall
        if match.home_last_matches and len(match.home_last_matches) >= 5:
            gf, gs = self._calculate_goals_last_n(match.home_last_matches[:5], match.home_team)
            values.extend([str(gf), str(gs)])
        else:
            values.extend(['-', '-'])
        
        if match.away_last_matches and len(match.away_last_matches) >= 5:
            gf, gs = self._calculate_goals_last_n(match.away_last_matches[:5], match.away_team)
            values.extend([str(gf), str(gs)])
        else:
            values.extend(['-', '-'])
        
        # Gol ultimi 5 casa/trasferta
        if match.home_last_matches:
            home_at_home = [m for m in match.home_last_matches if m['home_team'].lower() == match.home_team.lower()][:5]
            if home_at_home:
                gf, _ = self._calculate_goals_last_n(home_at_home, match.home_team)
                values.append(str(gf))
            else:
                values.append('-')
        else:
            values.append('-')
        
        if match.away_last_matches:
            away_away = [m for m in match.away_last_matches if m['away_team'].lower() == match.away_team.lower()][:5]
            if away_away:
                gf, _ = self._calculate_goals_last_n(away_away, match.away_team)
                values.append(str(gf))
            else:
                values.append('-')
        else:
            values.append('-')
        
        # Form
        values.append(match.get_home_form_string(5) or '-')
        values.append(match.get_away_form_string(5) or '-')
        
        return values
    
    def _calculate_goals_last_n(self, matches, team_name):
        """Calcola gol negli ultimi N match"""
        gf, gs = 0, 0
        for m in matches:
            try:
                parts = m.get('score', '').split('-')
                if len(parts) == 2:
                    home_g = int(parts[0].strip())
                    away_g = int(parts[1].strip())
                    if m['home_team'].lower() == team_name.lower():
                        gf += home_g
                        gs += away_g
                    elif m['away_team'].lower() == team_name.lower():
                        gf += away_g
                        gs += home_g
            except:
                pass
        return gf, gs
    
    # Metodi rimanenti (start_scraping, run_scraping, ecc.) rimangono identici
    # Copia dal tuo gui.py originale tutti i metodi da start_scraping in poi
    
    def start_scraping(self):
        """Avvia scraping"""
        if self.is_scraping:
            messagebox.showwarning("Warning", "Scraping already in progress!")
            return
        
        date_str = self.date_var.get().strip()
        target_date = None
        
        for fmt in ['%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y']:
            try:
                target_date = datetime.strptime(date_str, fmt)
                break
            except ValueError:
                continue
        
        if not target_date:
            messagebox.showerror("Error", "Invalid date format!\n\nUse: YYYY-MM-DD, DD-MM-YYYY, DD/MM/YYYY")
            return
        
        self.is_scraping = True
        self.scrape_button.config(state='disabled')
        self.progress_bar.start()
        self.progress_var.set("Scraping in progress...")
        self.status_var.set("Downloading data...")
        
        thread = threading.Thread(target=self.run_scraping, args=(target_date,), daemon=True)
        thread.start()
    
    def run_scraping(self, target_date):
        """Esegue scraping"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            matches = loop.run_until_complete(self.scrape_async(target_date))
            self.root.after(0, self.on_scraping_complete, matches)
        except Exception as e:
            logger.error(f"Scraping error: {e}", exc_info=True)
            self.root.after(0, self.on_scraping_error, str(e))
        finally:
            loop.close()
    
    async def scrape_async(self, target_date):
        """Scraping asincrono"""
        scraper = MatchScraper(self.config)
        
        self.root.after(0, lambda: self.progress_var.set("📥 Downloading match list..."))
        matches = await scraper.get_matches_by_date(target_date)
        
        if not matches:
            return []
        
        if self.download_details_var.get():
            self.root.after(0, lambda: self.progress_var.set(f"📊 Downloading details for {len(matches)} matches..."))
            detailed = await scraper.get_matches_details(matches)
            return detailed
        
        return matches
    
    def on_scraping_complete(self, matches):
        """Callback completamento"""
        self.is_scraping = False
        self.scrape_button.config(state='normal')
        self.progress_bar.stop()
        
        self.matches = matches
        
        if not matches:
            self.progress_var.set("No matches found")
            self.status_var.set("No data")
            messagebox.showinfo("Info", "No matches found for this date")
            return
        
        # Reset filtri quando si caricano nuove partite
        self.reset_filters()
        
        # Popola tabella (i filtri vengono applicati automaticamente se attivi)
        self.apply_filters()
        
        collection = MatchCollection(matches)
        stats = collection.get_statistics()
        
        self.stats_labels['matches'].config(text=str(stats['total_matches']))
        self.stats_labels['leagues'].config(text=str(stats['unique_leagues']))
        self.stats_labels['with_odds'].config(text=str(stats['matches_with_odds']))
        self.stats_labels['with_stats'].config(text=str(stats.get('matches_with_stats', 0)))
        self.stats_labels['with_standing'].config(text=str(stats.get('matches_with_standing', 0)))
        
        self.progress_var.set(f"✓ Completed: {len(matches)} matches")
        self.status_var.set(f"Loaded {len(matches)} matches - {stats['unique_leagues']} leagues")
        
        messagebox.showinfo("Success", f"✓ Downloaded {len(matches)} matches!\n\nLeagues: {stats['unique_leagues']}\nWith details: {stats.get('matches_with_stats', 0)}")
    
    def on_scraping_error(self, error_msg):
        """Callback errore"""
        self.is_scraping = False
        self.scrape_button.config(state='normal')
        self.progress_bar.stop()
        self.progress_var.set("✗ Error")
        self.status_var.set("Error occurred")
        
        messagebox.showerror("Error", f"Error during scraping:\n\n{error_msg}")
    
    def on_match_select(self, event):
        """Gestisce selezione partita"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item = selection[0]
        match_url = self.tree.item(item, 'tags')[0]
        
        match = next((m for m in self.matches if m.url == match_url), None)
        if not match:
            return
        
        self.selected_match = match
        self.display_match_details(match)
    
    def display_match_details(self, match):
            """Mostra dettagli partita con DATI REALI"""
            self.details_text.config(state='normal')
            self.details_text.delete('1.0', tk.END)
            
            text = "═" * 70 + "\n"
            text += f"  {match.home_team} vs {match.away_team}\n"
            text += "═" * 70 + "\n\n"
            
            text += f"📅 {match.date.strftime('%d/%m/%Y')} - {match.time.strftime('%H:%M')}\n"
            text += f"🏆 {match.league}\n\n"
            
            # ===== STATISTICS FOR LEAGUE =====
            if match.league_statistics:
                text += "═" * 70 + "\n"
                text += f"📊 STATISTICS FOR {match.league.upper()}\n"
                text += "═" * 70 + "\n\n"
                
                stats = match.league_statistics
                
                # Completamento
                if stats.get('total_matches', 0) > 0:
                    text += f"Competition Progress:\n"
                    text += f"  Completed: {stats.get('completed_percentage', 0):.0f}%\n"
                    text += f"  Matches: {stats.get('total_matches', 0)}\n"
                    text += f"  Finished: {stats.get('finished', 0)}\n"
                    text += f"  Remaining: {stats.get('remaining', 0)}\n\n"
                
                # Risultati
                if stats.get('home_win_pct', 0) > 0:
                    text += f"Match Outcomes:\n"
                    text += f"  Home Win: {stats.get('home_win_pct', 0):.0f}%\n"
                    text += f"  Draw: {stats.get('draw_pct', 0):.0f}%\n"
                    text += f"  Away Win: {stats.get('away_win_pct', 0):.0f}%\n\n"
                
                # Gol
                if stats.get('avg_goals', 0) > 0:
                    text += f"Goals:\n"
                    text += f"  Average per match: {stats.get('avg_goals', 0):.2f}\n"
                    text += f"  Home Team avg: {stats.get('avg_home_goals', 0):.2f}\n"
                    text += f"  Away Team avg: {stats.get('avg_away_goals', 0):.2f}\n\n"
                
                # BTS
                if stats.get('bts_pct', 0) > 0:
                    text += f"Both Teams Score:\n"
                    text += f"  Overall: {stats.get('bts_pct', 0):.0f}%\n\n"
                
                # Over/Under
                if stats.get('over_under'):
                    text += f"Over/Under:\n"
                    for threshold, values in sorted(stats['over_under'].items()):
                        text += f"  {threshold}: Under {values.get('under', 0):.0f}% | Over {values.get('over', 0):.0f}%\n"
                    text += "\n"
            
            # ===== CLASSIFICA COMPLETA =====
            if match.league_standings:
                text += "─" * 70 + "\n"
                text += "🏆 COMPLETE LEAGUE STANDINGS\n"
                text += "─" * 70 + "\n"
                text += "Pos  Team                          Pts  P   W  D  L   GF  GA  GD\n"
                text += "─" * 70 + "\n"
                
                for team in match.league_standings[:20]:
                    marker = "  "
                    if (team['team'].lower() in match.home_team.lower() or 
                        match.home_team.lower() in team['team'].lower() or
                        team['team'].lower() in match.away_team.lower() or
                        match.away_team.lower() in team['team'].lower()):
                        marker = "► "
                    
                    team_name = team['team'][:28]
                    
                    text += f"{marker}{team['position']:2}. {team_name:28} "
                    text += f"{team['points']:3} {team['matches_played']:2}  "
                    text += f"{team['wins']:2} {team['draws']:2} {team['losses']:2}  "
                    text += f"{team['goals_for']:3} {team['goals_against']:3} "
                    text += f"{team['goal_difference']:+3}\n"
                
                text += "\n"
            
            # ===== PREDIZIONI AI =====
            text += "═" * 70 + "\n"
            text += "🔮 AI PREDICTIONS\n"
            text += "═" * 70 + "\n\n"
            
            try:
                pred = self.prediction_engine.predict_match(match, self.matches)
                self.current_prediction = pred
                
                # Expected Goals
                text += "⚽ EXPECTED GOALS:\n"
                text += f"  {match.home_team}: {pred.home_xg:.2f} xG\n"
                text += f"  {match.away_team}: {pred.away_xg:.2f} xG\n"
                text += f"  Total: {pred.total_xg:.2f} xG\n"
                
                if match.league_statistics and match.league_statistics.get('avg_goals', 0) > 0:
                    text += f"  (League avg: {match.league_statistics['avg_goals']:.2f})\n"
                text += "\n"
                
                # Elo Ratings
                text += "📊 ELO RATINGS:\n"
                text += f"  {match.home_team}: {pred.elo_home:.0f}\n"
                text += f"  {match.away_team}: {pred.elo_away:.0f}\n"
                text += f"  Difference: {pred.elo_diff:+.0f}\n\n"
                
                # 1X2
                text += "🎯 MATCH OUTCOME:\n"
                text += f"  Home Win (1): {pred.home_win_prob*100:5.1f}%"
                if match.odds and match.odds.home_win > 0:
                    text += f"  [Odds: {match.odds.home_win:.2f}]"
                    if pred.home_win_prob > (1/match.odds.home_win) * 1.05:
                        text += " ⭐"
                text += "\n"
                
                text += f"  Draw (X):     {pred.draw_prob*100:5.1f}%"
                if match.odds and match.odds.draw > 0:
                    text += f"  [Odds: {match.odds.draw:.2f}]"
                    if pred.draw_prob > (1/match.odds.draw) * 1.05:
                        text += " ⭐"
                text += "\n"
                
                text += f"  Away Win (2): {pred.away_win_prob*100:5.1f}%"
                if match.odds and match.odds.away_win > 0:
                    text += f"  [Odds: {match.odds.away_win:.2f}]"
                    if pred.away_win_prob > (1/match.odds.away_win) * 1.05:
                        text += " ⭐"
                text += "\n\n"
                
                # Over/Under
                text += "⚽ GOALS MARKETS:\n"
                text += f"  Over 2.5:  {pred.over_2_5_prob*100:5.1f}%"
                if match.odds and match.odds.over_2_5 > 0:
                    text += f"  [Odds: {match.odds.over_2_5:.2f}]"
                    if pred.over_2_5_prob > (1/match.odds.over_2_5) * 1.05:
                        text += " ⭐"
                text += "\n"
                
                text += f"  Under 2.5: {pred.under_2_5_prob*100:5.1f}%"
                if match.odds and match.odds.under_2_5 > 0:
                    text += f"  [Odds: {match.odds.under_2_5:.2f}]"
                text += "\n\n"
                
                # BTS
                text += "🎯 BOTH TEAMS SCORE:\n"
                text += f"  Yes (GG): {pred.bts_yes_prob*100:5.1f}%"
                if match.odds and match.odds.bts_yes > 0:
                    text += f"  [Odds: {match.odds.bts_yes:.2f}]"
                    if pred.bts_yes_prob > (1/match.odds.bts_yes) * 1.05:
                        text += " ⭐"
                text += "\n"
                
                text += f"  No (NG):  {pred.bts_no_prob*100:5.1f}%"
                if match.odds and match.odds.bts_no > 0:
                    text += f"  [Odds: {match.odds.bts_no:.2f}]"
                text += "\n\n"
                
                # Top Scores
                text += "🎲 TOP EXACT SCORES:\n"
                for i, (score, prob) in enumerate(pred.exact_scores[:5], 1):
                    bar = "█" * int(prob * 40)
                    text += f"  {i}. {score:>5}  {prob*100:5.1f}%  {bar}\n"
                text += "\n"
                
                # Value Bets
                if pred.value_bets:
                    text += "💎 VALUE BETS:\n"
                    text += "─" * 70 + "\n"
                    for i, vb in enumerate(pred.value_bets[:3], 1):
                        text += f"{i}. {vb['market']} @ {vb['bookmaker_odds']:.2f}\n"
                        text += f"   EV: {vb['expected_value']*100:+.1f}% | Edge: {vb['edge']:+.1f}%\n\n"
                
                text += f"💡 {pred.recommended_bet}\n"
                text += f"🎯 Confidence: {pred.confidence}\n\n"
                
            except Exception as e:
                text += f"⚠️ Error: {e}\n\n"
            
            # ===== HEAD TO HEAD =====
            if match.head_to_head:
                text += "─" * 70 + "\n"
                text += "⚔️ HEAD TO HEAD\n"
                text += "─" * 70 + "\n"
                text += "Date        Home Team            Score  Away Team\n"
                text += "─" * 70 + "\n"
                
                for h2h in match.head_to_head[:6]:
                    date = h2h.get('date', '')[:10]
                    home = h2h.get('home_team', '')[:20]
                    score = h2h.get('score', '')
                    away = h2h.get('away_team', '')[:20]
                    
                    text += f"{date:11} {home:20} {score:6} {away:20}\n"
                
                text += "\n"
            
            # ===== LAST MATCHES =====
            text += "─" * 70 + "\n"
            text += f"📋 LAST MATCHES: {match.home_team}\n"
            text += "─" * 70 + "\n"
            
            if match.home_last_matches:
                text += "Date        Home Team            Score  Away Team\n"
                text += "─" * 70 + "\n"
                
                for lm in match.home_last_matches[:5]:
                    outcome = lm.get('outcome', 'D')
                    icon = "✓" if outcome == 'W' else "✗" if outcome == 'L' else "="
                    
                    date = lm.get('date', '')[:10]
                    home = lm.get('home_team', '')[:20]
                    score = lm.get('score', '')
                    away = lm.get('away_team', '')[:20]
                    
                    text += f"{icon} {date:9} {home:20} {score:6} {away:20}\n"
            
            text += "\n"
            text += "─" * 70 + "\n"
            text += f"📋 LAST MATCHES: {match.away_team}\n"
            text += "─" * 70 + "\n"
            
            if match.away_last_matches:
                text += "Date        Home Team            Score  Away Team\n"
                text += "─" * 70 + "\n"
                
                for lm in match.away_last_matches[:5]:
                    outcome = lm.get('outcome', 'D')
                    icon = "✓" if outcome == 'W' else "✗" if outcome == 'L' else "="
                    
                    date = lm.get('date', '')[:10]
                    home = lm.get('home_team', '')[:20]
                    score = lm.get('score', '')
                    away = lm.get('away_team', '')[:20]
                    
                    text += f"{icon} {date:9} {home:20} {score:6} {away:20}\n"
            
            text += "\n" + "═" * 70 + "\n"
            
            self.details_text.insert('1.0', text)
            self.details_text.config(state='disabled')

    
    def save_excel(self):
        """Salva Excel"""
        if not self.matches:
            messagebox.showwarning("Warning", "No data to save!")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile=f"analytica_bet_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        )
        
        if filename:
            try:
                collection = MatchCollection(self.matches)
                collection.to_excel(filename)
                self.status_var.set(f"✓ Saved: {filename}")
                messagebox.showinfo("Success", f"File saved:\n{filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Error: {e}")
    
    def save_csv(self):
        """Salva CSV"""
        if not self.matches:
            messagebox.showwarning("Warning", "No data to save!")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile=f"analytica_bet_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        )
        
        if filename:
            try:
                collection = MatchCollection(self.matches)
                collection.to_csv(filename)
                self.status_var.set(f"✓ Saved: {filename}")
                messagebox.showinfo("Success", f"File saved:\n{filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Error: {e}")
    
    def save_json(self):
        """Salva JSON"""
        if not self.matches:
            messagebox.showwarning("Warning", "No data to save!")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile=f"analytica_bet_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        )
        
        if filename:
            try:
                collection = MatchCollection(self.matches)
                collection.to_json(filename)
                self.status_var.set(f"✓ Saved: {filename}")
                messagebox.showinfo("Success", f"File saved:\n{filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Error: {e}")
    
    def filter_leagues(self):
        """Filtra per leghe"""
        if not self.matches:
            messagebox.showwarning("Warning", "No data to filter!")
            return
        
        leagues = sorted(set(m.league for m in self.matches))
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Filter by League")
        dialog.geometry("500x400")
        dialog.configure(bg=self.COLORS['bg_light'])
        
        ttk.Label(dialog, text="Select league:", style='Header.TLabel').pack(pady=15)
        
        # Frame con scrollbar
        frame = ttk.Frame(dialog)
        frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)
        
        scrollbar = ttk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        listbox = tk.Listbox(frame, height=15, font=('Segoe UI', 10),
                            yscrollcommand=scrollbar.set,
                            bg=self.COLORS['row_even'],
                            selectbackground=self.COLORS['selected'])
        listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=listbox.yview)
        
        for league in leagues:
            listbox.insert(tk.END, league)
        
        def apply_filter():
            selection = listbox.curselection()
            if selection:
                league = listbox.get(selection[0])
                collection = MatchCollection(self.matches)
                filtered = collection.filter_by_league(league)
                self.populate_table(filtered.matches)
                self.status_var.set(f"Filtered: {len(filtered.matches)} matches for {league}")
                dialog.destroy()
        
        def show_all():
            self.populate_table(self.matches)
            self.status_var.set(f"Showing all {len(self.matches)} matches")
            dialog.destroy()
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=15)
        
        ttk.Button(btn_frame, text="Apply Filter", command=apply_filter,
                  style='Action.TButton', width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Show All", command=show_all,
                  style='Action.TButton', width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy,
                  width=15).pack(side=tk.LEFT, padx=5)
    
    def apply_filters(self):
        """Applica filtri intelligenti"""
        if not self.matches:
            return
        
        filtered_matches = self.matches.copy()
        
        # Filtro: senza quote
        if self.filter_no_odds_var.get():
            filtered_matches = [
                m for m in filtered_matches 
                if m.odds and m.odds.home_win > 0
            ]
        
        # Filtro: senza statistiche
        if self.filter_no_stats_var.get():
            filtered_matches = [
                m for m in filtered_matches 
                if m.home_stats and m.away_stats and 
                   (m.home_stats.wins > 0 or m.away_stats.wins > 0)
            ]
        
        # Popola tabella con partite filtrate
        self.populate_table(filtered_matches)
        
        # Aggiorna status
        total = len(self.matches)
        shown = len(filtered_matches)
        hidden = total - shown
        
        if hidden > 0:
            self.status_var.set(f"Showing {shown}/{total} matches ({hidden} hidden by filters)")
        else:
            self.status_var.set(f"Showing all {total} matches")
    
    def reset_filters(self):
        """Reset tutti i filtri"""
        self.filter_no_odds_var.set(False)
        self.filter_no_stats_var.set(False)
        
        if self.matches:
            self.populate_table(self.matches)
            self.status_var.set(f"Showing all {len(self.matches)} matches - Filters cleared")
    
    def clear_results(self):
        """Pulisci risultati"""
        if messagebox.askyesno("Confirm", "Clear all results?"):
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            self.matches = []
            
            for label in self.stats_labels.values():
                label.config(text='0')
            
            self.details_text.config(state='normal')
            self.details_text.delete('1.0', tk.END)
            self.details_text.insert('1.0', 'Select a match to view details...')
            self.details_text.config(state='disabled')
            
            self.progress_var.set("Ready")
            self.status_var.set("Results cleared - Ready")


def main():
    root = tk.Tk()
    app = AnalyticaBetGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()