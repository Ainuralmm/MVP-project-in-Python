import streamlit as st
from datetime import datetime, date, timedelta
import pandas as pd
import spacy
from typing import Optional, Dict, Any, Tuple, List

import presenter
from presenter import CoursePresenter
import automation_lock   # <-- NEW: VM-global lock + heartbeat


# NEW UTILITY FUNCTIONS FOR ENHANCED NLP PARSING
#========== UTILITY 1: SAFE TEXT EXTRACTION ==========
def safe_extract_text(original_text: str, normalized_text: str, match_start: int, match_end: int) -> str:
    """
    Safely extract text from original while using match positions from normalized text.

    WHY: When we normalize text (remove accents, lowercase), the character positions
    might shift. This function ensures we always extract from the correct positions.

    Args:
        original_text: The original user input (with proper case, accents)
        normalized_text: The text used for pattern matching (lowercase, no accents)
        match_start: Start position from the regex match on normalized_text
        match_end: End position from the regex match on normalized_text

    Returns:
        Extracted text from original, properly aligned
    """
    # ### HASHTAG: VERIFY LENGTHS MATCH ###
    if len(original_text) != len(normalized_text):
        # If lengths differ (due to accent removal), fall back to normalized extraction
        return normalized_text[match_start:match_end].strip()

    # ### HASHTAG: SAFE EXTRACTION WITH BOUNDS CHECK ###
    safe_start = max(0, match_start)
    safe_end = min(len(original_text), match_end)

    return original_text[safe_start:safe_end].strip()

# ========== UTILITY 2: ITALIAN MONTH NAME PARSER ==========
ITALIAN_MONTHS = {
    'gennaio': '01', 'febbraio': '02', 'marzo': '03', 'aprile': '04',
    'maggio': '05', 'giugno': '06', 'luglio': '07', 'agosto': '08',
    'settembre': '09', 'ottobre': '10', 'novembre': '11', 'dicembre': '12',
    # Short forms
    'gen': '01', 'feb': '02', 'mar': '03', 'apr': '04',
    'mag': '05', 'giu': '06', 'lug': '07', 'ago': '08',
    'set': '09', 'ott': '10', 'nov': '11', 'dic': '12'
}

def parse_italian_date(date_str: str) -> Optional[str]:
    """
    Parse Italian date format like "12 gennaio 2024" into "12/01/2024".

    WHY: Users might write dates in natural language. This converts them to
    the standard DD/MM/YYYY format our system expects.

    Args:
        date_str: Date string that might contain Italian month names

    Returns:
        Standardized date string in DD/MM/YYYY format, or None if parsing fails
    """
    import re

    # ### HASHTAG: PATTERN FOR "12 gennaio 2024" FORMAT ###
    month_name_pattern = r'(\d{1,2})\s+(\w+)\s+(\d{4})'
    match = re.search(month_name_pattern, date_str.lower())

    if match:
        day = match.group(1).zfill(2)  # Pad with zero: 5 → 05
        month_name = match.group(2)
        year = match.group(3)

        if month_name in ITALIAN_MONTHS:
            month = ITALIAN_MONTHS[month_name]
            return f"{day}/{month}/{year}"

    return None

# ========== UTILITY 3: TWO-DIGIT YEAR NORMALIZATION ==========
def normalize_two_digit_year(year_str: str) -> str:
    """
    Convert two-digit year to four-digit year using a pivot rule.

    WHY: "23" could mean 1923 or 2023. We need a consistent rule.

    RULE:
    - 00-69 → 2000-2069 (future dates, likely course start dates)
    - 70-99 → 1970-1999 (historical dates, unlikely for courses)

    Args:
        year_str: Two or four digit year as string

    Returns:
        Four-digit year as string
    """
    if len(year_str) == 4:
        return year_str

    if len(year_str) == 2:
        year_int = int(year_str)
        # ### HASHTAG: PIVOT RULE FOR CENTURY DETERMINATION ###
        if year_int <= 69:
            return f"20{year_str}"
        else:
            return f"19{year_str}"

    return year_str

# ========== UTILITY 4: CENTRALIZED DATE NORMALIZATION ==========
def normalize_date(date_value: Any, default_format: str = "%d/%m/%Y") -> Optional[str]:
    """
    Universal date normalizer - handles ANY date format and converts to DD/MM/YYYY.

    WHY: Dates come in many forms (datetime objects, strings, Excel dates).
    This single function handles all cases consistently.

    Args:
        date_value: Can be datetime object, string, int (Excel date), etc.
        default_format: Output format (default: DD/MM/YYYY)

    Returns:
        Normalized date string or None if parsing fails
    """
    # ### HASHTAG: CASE 1 - ALREADY A DATETIME OBJECT ###
    if isinstance(date_value, datetime):
        return date_value.strftime(default_format)

    # ### HASHTAG: CASE 2 - PANDAS TIMESTAMP ###
    if hasattr(date_value, 'strftime'):  # Pandas Timestamp
        return date_value.strftime(default_format)

    # ### HASHTAG: CASE 3 - STRING WITH VARIOUS FORMATS ###
    if isinstance(date_value, str):
        date_str = date_value.strip()

        # Try Italian month names first
        italian_date = parse_italian_date(date_str)
        if italian_date:
            return italian_date

        # ### HASHTAG: TRY COMMON FORMATS IN ORDER ###
        formats_to_try = [
            "%d/%m/%Y",  # 15/03/2024
            "%d-%m-%Y",  # 15-03-2024
            "%d/%m/%y",  # 15/03/24
            "%d-%m-%y",  # 15-03-24
            "%Y-%m-%d",  # 2024-03-15 (ISO format)
            "%d.%m.%Y",  # 15.03.2024
            "%d %m %Y",  # 15 03 2024
        ]

        for fmt in formats_to_try:
            try:
                parsed = datetime.strptime(date_str, fmt)
                # ### HASHTAG: HANDLE TWO-DIGIT YEARS ###
                if fmt.endswith("%y"):
                    year_normalized = normalize_two_digit_year(str(parsed.year)[-2:])
                    parsed = parsed.replace(year=int(year_normalized))
                return parsed.strftime(default_format)
            except ValueError:
                continue

        # ### HASHTAG: FALLBACK - PANDAS TO_DATETIME (VERY FLEXIBLE) ###
        try:
            parsed = pd.to_datetime(date_str, dayfirst=True, errors='coerce')
            if pd.notna(parsed):
                return parsed.strftime(default_format)
        except:
            pass

    # ### HASHTAG: CASE 4 - NUMERIC (EXCEL SERIAL DATE) ###
    if isinstance(date_value, (int, float)):
        try:
            # Excel dates are days since 1899-12-30
            parsed = pd.to_datetime('1899-12-30') + pd.Timedelta(days=date_value)
            return parsed.strftime(default_format)
        except:
            pass

    return None

# ========== UTILITY 4: CENTRALIZED DATE NORMALIZATION ==========
def normalize_date(date_value: Any, default_format: str = "%d/%m/%Y") -> Optional[str]:
    """
    Universal date normalizer - handles ANY date format and converts to DD/MM/YYYY.

    WHY: Dates come in many forms (datetime objects, strings, Excel dates).
    This single function handles all cases consistently.

    Args:
        date_value: Can be datetime object, string, int (Excel date), etc.
        default_format: Output format (default: DD/MM/YYYY)

    Returns:
        Normalized date string or None if parsing fails
    """
    # ### HASHTAG: CASE 1 - ALREADY A DATETIME OBJECT ###
    if isinstance(date_value, datetime):
        return date_value.strftime(default_format)

    # ### HASHTAG: CASE 2 - PANDAS TIMESTAMP ###
    if hasattr(date_value, 'strftime'):  # Pandas Timestamp
        return date_value.strftime(default_format)

    # ### HASHTAG: CASE 3 - STRING WITH VARIOUS FORMATS ###
    if isinstance(date_value, str):
        date_str = date_value.strip()

        # Try Italian month names first
        italian_date = parse_italian_date(date_str)
        if italian_date:
            return italian_date

        # ### HASHTAG: TRY COMMON FORMATS IN ORDER ###
        formats_to_try = [
            "%d/%m/%Y",  # 15/03/2024
            "%d-%m-%Y",  # 15-03-2024
            "%d/%m/%y",  # 15/03/24
            "%d-%m-%y",  # 15-03-24
            "%Y-%m-%d",  # 2024-03-15 (ISO format)
            "%d.%m.%Y",  # 15.03.2024
            "%d %m %Y",  # 15 03 2024
        ]

        for fmt in formats_to_try:
            try:
                parsed = datetime.strptime(date_str, fmt)
                # ### HASHTAG: HANDLE TWO-DIGIT YEARS ###
                if fmt.endswith("%y"):
                    year_normalized = normalize_two_digit_year(str(parsed.year)[-2:])
                    parsed = parsed.replace(year=int(year_normalized))
                return parsed.strftime(default_format)
            except ValueError:
                continue

        # ### HASHTAG: FALLBACK - PANDAS TO_DATETIME (VERY FLEXIBLE) ###
        try:
            parsed = pd.to_datetime(date_str, dayfirst=True, errors='coerce')
            if pd.notna(parsed):
                return parsed.strftime(default_format)
        except:
            pass

    # ### HASHTAG: CASE 4 - NUMERIC (EXCEL SERIAL DATE) ###
    if isinstance(date_value, (int, float)):
        try:
            # Excel dates are days since 1899-12-30
            parsed = pd.to_datetime('1899-12-30') + pd.Timedelta(days=date_value)
            return parsed.strftime(default_format)
        except:
            pass

    return None

# ========== UTILITY 5: EXTRACT WITH SPACY MATCHER ==========
def extract_with_spacy_matcher(text: str, nlp_model) -> Dict[str, str]:
    """
    Use spaCy's Matcher for robust keyword-based extraction.

    WHY: Regex assumes fixed word order. spaCy Matcher handles variations like:
    - "titolo: Excel" vs "Excel è il titolo"
    - "corso di Python" vs "Python corso"

    This is more robust for natural language input.

    Args:
        text: User input text
        nlp_model: Loaded spaCy model

    Returns:
        Dictionary with extracted 'title', 'description', 'date'
    """
    from spacy.matcher import Matcher

    doc = nlp_model(text)
    matcher = Matcher(nlp_model.vocab)

    results = {
        'title': "",
        'description': "",
        'date': ""
    }

    # ### HASHTAG: DEFINE PATTERNS FOR TITLE ###
    # Pattern: "titolo" + optional ":" + text until comma or end
    title_patterns = [
        [{"LOWER": "titolo"}, {"IS_PUNCT": True, "OP": "?"}, {"IS_ALPHA": True, "OP": "+"}],
        [{"LOWER": "corso"}, {"IS_ALPHA": True, "OP": "+"}],
    ]

    matcher.add("TITLE", title_patterns)

    # ### HASHTAG: DEFINE PATTERNS FOR DESCRIPTION ###
    desc_patterns = [
        [{"LOWER": "descrizione"}, {"IS_PUNCT": True, "OP": "?"}, {"IS_ALPHA": True, "OP": "+"}],
    ]

    matcher.add("DESCRIPTION", desc_patterns)

    # ### HASHTAG: RUN MATCHER ###
    matches = matcher(doc)

    for match_id, start, end in matches:
        match_label = nlp_model.vocab.strings[match_id]
        span = doc[start:end]

        if match_label == "TITLE" and not results['title']:
            # Extract tokens after "titolo" keyword
            title_tokens = [token.text for token in span if token.lower_ not in ['titolo', 'corso', ':']]
            results['title'] = ' '.join(title_tokens)

        elif match_label == "DESCRIPTION" and not results['description']:
            desc_tokens = [token.text for token in span if token.lower_ not in ['descrizione', ':']]
            results['description'] = ' '.join(desc_tokens)

    # ### HASHTAG: DATE EXTRACTION WITH REGEX (SPACY DOESN'T HANDLE THIS WELL) ###
    import re
    date_pattern = r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b'
    date_match = re.search(date_pattern, text)
    if date_match:
        results['date'] = date_match.group(1)

    return results


class CourseView:
    def __init__(self):
        self.presenter = presenter
        st.set_page_config(layout='centered')
        # --- Basic App State ---
        if "app_state" not in st.session_state:
            st.session_state.app_state = "IDLE"

        # === CONFIGURATION GUARD FOR CONTROLLER RUNS ===
        if "automation_in_progress" not in st.session_state:
            st.session_state.automation_in_progress = False

        # === AUTH STATE ===
        if "oracle_logged_in" not in st.session_state:
            st.session_state.oracle_logged_in = False
        if "oracle_username" not in st.session_state:
            st.session_state.oracle_username = None
        if "oracle_password" not in st.session_state:
            st.session_state.oracle_password = None

        # --- Message States: COURSE ---
        if "course_message" not in st.session_state:
            st.session_state.course_message = ""

        # NEW STATE VARIABLES FOR COURSE INPUT METHOD
        if "course_input_method" not in st.session_state:
            st.session_state.course_input_method = "structured"  # Options: "structured", "excel", "nlp"
        if "course_edit_mode" not in st.session_state:
            st.session_state.course_edit_mode = False
        if "courses_to_edit" not in st.session_state:
            st.session_state.courses_to_edit = []
        if "course_parsed_data" not in st.session_state:
            st.session_state.course_parsed_data = None  # Stores parsed data from Excel/NLP
        if "course_show_summary" not in st.session_state:
            st.session_state.course_show_summary = False  # Controls summary display
        if "course_nlp_input" not in st.session_state:
            st.session_state.course_nlp_input = ""  # Stores NLP text input

        # BATCH PROCESSING STATE VARIABLES ###
        if "batch_course_data" not in st.session_state:
            st.session_state.batch_course_data = None
        if "batch_continue_on_error" not in st.session_state:
            st.session_state.batch_continue_on_error = True
        if "batch_edition_data" not in st.session_state:
            st.session_state.batch_edition_data = None
        if "batch_edition_results" not in st.session_state:
            st.session_state.batch_edition_results = []
        if "show_edition_results" not in st.session_state:
            st.session_state.show_edition_results = False

        # INITIALIZE SPACY MODEL
        if "nlp_clear_requested" not in st.session_state:
            st.session_state.nlp_clear_requested = False
        if "nlp_model" not in st.session_state:
            try:
                st.session_state.nlp_model = spacy.load("it_core_news_sm")  # Italian model
            except OSError:
                st.session_state.nlp_model = None  # Will show error in UI if not loaded

        # === EDITION INPUT METHOD STATES ===
        if "edition_input_method" not in st.session_state:
            st.session_state.edition_input_method = "structured" # "structured", "excel", "nlp"
        if "edition_parsed_data" not in st.session_state:
            st.session_state.edition_parsed_data = None
        if "edition_show_summary" not in st.session_state:
            st.session_state.edition_show_summary = False
        if "edition_edit_mode" not in st.session_state:
            st.session_state.edition_edit_mode = False
        if "edition_to_edit" not in st.session_state:
            st.session_state.edition_to_edit = None
        if "edition_nlp_input" not in st.session_state:
            st.session_state.edition_nlp_input = ""
        if "edition_nlp_clear_requested" not in st.session_state:
            st.session_state.edition_nlp_clear_requested = False

        # --- Message States: EDITION and STUDENTS ---
        if "edition_message" not in st.session_state:
            st.session_state.edition_message = ""
        if "student_message" not in st.session_state:
            st.session_state.student_message = ""

        if st.session_state.get("student_input_method") == "manual":
            st.session_state.student_input_method = "txt"
        if "student_input_method" not in st.session_state:
            st.session_state.student_input_method = "txt"   # <-- was "manual"

        # if "student_input_method" not in st.session_state:
        #     st.session_state.student_input_method = "manual"
        if "student_parsed_data" not in st.session_state:
            st.session_state.student_parsed_data = None
        if "student_show_summary" not in st.session_state:
            st.session_state.student_show_summary = False
        if "batch_student_data" not in st.session_state:
            st.session_state.batch_student_data = None
        if "verify_student_data" not in st.session_state:
             st.session_state.verify_student_data = None

        # --- Form Specific State ---
        if "num_activities" not in st.session_state:
            st.session_state.num_activities = 1
        if "num_students" not in st.session_state:
            st.session_state.num_students = 1

        # --- Preserved form data storage ---
        if "preserved_activity_data" not in st.session_state:
            st.session_state.preserved_activity_data = {}
        if "preserved_student_data" not in st.session_state:
            st.session_state.preserved_student_data = {}

        #presenza
        if "presenza_data" not in st.session_state:
            st.session_state.presenza_data = None
        if "presenza_show_summary" not in st.session_state:
            st.session_state.presenza_show_summary = False
        if "presenza_message" not in st.session_state:
            st.session_state.presenza_message = ""
        # Multi-edition presenza batch state
        if "presenza_batch_data" not in st.session_state:
            st.session_state.presenza_batch_data = None
        if "presenza_show_batch_preview" not in st.session_state:
            st.session_state.presenza_show_batch_preview = False

        # --- Initialize Widget States ---
        if "course_date_str_key" not in st.session_state:
            st.session_state.course_date_str_key = "01/01/2023"

        # Initialize activity fields
        for i in range(30):
            if f"activity_title_{i}" not in st.session_state:
                st.session_state[f"activity_title_{i}"] = ""
            if f"activity_desc_{i}" not in st.session_state:
                st.session_state[f"activity_desc_{i}"] = ""
            if f"activity_date_{i}" not in st.session_state:
                st.session_state[f"activity_date_{i}"] = ""
            if f"activity_start_time_{i}" not in st.session_state:
                st.session_state[f"activity_start_time_{i}"] = "09.00"
            if f"activity_end_time_{i}" not in st.session_state:
                st.session_state[f"activity_end_time_{i}"] = "11.00"
            if f"impegno_previsto_in_ore_{i}" not in st.session_state:
                st.session_state[f"impegno_previsto_in_ore_{i}"] = ""

        # Initialize student fields
        for i in range(50):
            if f"student_name_{i}" not in st.session_state:
                st.session_state[f"student_name_{i}"] = ""

        st.image("logo-agsm.jpg", width=200)
        st.title("Automatore per la Gestione dei Corsi Oracle")

        #  Initialize placeholders as None
        self.course_output_placeholder = None
        self.edition_output_placeholder = None
        self.student_output_placeholder = None

        # Load saved theme preferences if they exist
        import json, os
        prefs_path = os.path.join(os.path.dirname(__file__), 'user_preferences.json')
        if os.path.exists(prefs_path):
            try:
                with open(prefs_path, 'r', encoding='utf-8') as f:
                    prefs = json.load(f)
                if 'user_theme' not in st.session_state:
                    st.session_state.user_theme = prefs.get(
                        'user_theme', 'Scuro (default)')
                if 'user_font' not in st.session_state:
                    st.session_state.user_font = prefs.get(
                        'user_font', 'Sans-serif (default)')
            except:
                pass

    def _apply_theme(self):
        """
        Inject user's chosen theme as CSS.
        Keeps the Streamlit header untouched so the sidebar
        toggle (<<) and menu (rerun, clear cache) work normally.
        """
        import json
        import os

        themes_path = os.path.join(os.path.dirname(__file__), 'themes.json')
        try:
            with open(themes_path, 'r', encoding='utf-8') as f:
                themes_config = json.load(f)
        except:
            return

        current_theme_name = st.session_state.get(
            'user_theme', 'Scuro (default)')
        current_font_name = st.session_state.get(
            'user_font', 'Sans-serif (default)')

        theme = themes_config['themes'].get(
            current_theme_name,
            themes_config['themes']['Scuro (default)'])
        font = themes_config['fonts'].get(
            current_font_name,
            'sans-serif')

        st.markdown(f"""
            <style>
            /* Main app background */
            .stApp {{
                background-color: {theme['bg_color']};
                color: {theme['text_color']};
                font-family: {font};
            }}
            /* Header bar — make it match the app background */
            [data-testid="stHeader"] {{
                 background-color: {theme['bg_color']} !important;
            }}

            /* Sidebar background */
            [data-testid="stSidebar"] {{
                background-color: {theme['secondary_bg']};
            }}

            /* Text in main content and sidebar */
            [data-testid="stMain"] p,
            [data-testid="stMain"] label,
            [data-testid="stMain"] h1,
            [data-testid="stMain"] h2,
            [data-testid="stMain"] h3,
            [data-testid="stMain"] h4,
            [data-testid="stSidebar"] p,
            [data-testid="stSidebar"] label,
            [data-testid="stSidebar"] h1,
            [data-testid="stSidebar"] h2,
            [data-testid="stSidebar"] h3,
            [data-testid="stSidebar"] h4 {{
                color: {theme['text_color']} !important;
                font-family: {font} !important;
            }}

            /* Input fields */
            .stTextInput > div > div > input,
            .stTextArea > div > div > textarea,
            .stSelectbox > div > div {{
                background-color: {theme['secondary_bg']};
                color: {theme['text_color']};
                font-family: {font};
            }}

            /* Expanders */
            [data-testid="stExpander"] {{
                background-color: {theme['secondary_bg']};
            }}
            /* Regular buttons + form submit buttons (Pulisci, etc.) */
            .stButton > button,
            [data-testid="stFormSubmitButton"] > button,
            [data-testid="stBaseButton-secondary"],
            [data-testid="stBaseButton-primary"] {{
            background-color: {theme['secondary_bg']} !important;
            color: {theme['text_color']} !important;
            border: 1px solid {theme['text_color']}33 !important;
            transition: filter 0.2s ease;
            }}
            
            /* Button hover — brighten slightly */
            .stButton > button:hover,
            [data-testid="stFormSubmitButton"] > button:hover,
            [data-testid="stBaseButton-secondary"]:hover,
            [data-testid="stBaseButton-primary"]:hover {{
            filter: brightness(1.15);
            border-color: {theme['text_color']}66 !important;
            }}
            
            /* Number input field ("Quanti giorni di attività?") */
            .stNumberInput input {{
            background-color: {theme['secondary_bg']} !important;
            color: {theme['text_color']} !important;
            }}
            
            /* Number input +/- buttons */
            .stNumberInput button {{
            background-color: {theme['secondary_bg']} !important;
            color: {theme['text_color']} !important;
            border-color: {theme['text_color']}33 !important;
            }}
            
            .stNumberInput button:hover {{
            filter: brightness(1.15);
            }}
            /* Info, warning, success, error boxes — match theme */
            [data-testid="stAlert"],
            [data-testid="stAlertContainer"],
            [data-testid="stNotification"] {{
                background-color: {theme['secondary_bg']} !important;
                color: {theme['text_color']} !important;
            }}
            
            [data-testid="stAlert"] *,
            [data-testid="stAlertContainer"] *,
            [data-testid="stNotification"] * {{
                color: {theme['text_color']} !important;
            }}
            
            /* File uploader (Drag and drop area) */
            [data-testid="stFileUploaderDropzone"],
            [data-testid="stFileUploader"] section {{
                background-color: {theme['secondary_bg']} !important;
                color: {theme['text_color']} !important;
                border-color: {theme['text_color']}33 !important;
            }}
            
            [data-testid="stFileUploaderDropzone"] *,
            [data-testid="stFileUploader"] section * {{
                color: {theme['text_color']} !important;
            }}
            
            /* Radio button dots — unselected */
            [data-baseweb="radio"] div[role="radio"] {{
                background-color: {theme['bg_color']} !important;
                border-color: {theme['text_color']}66 !important;
            }}
            
            /* Radio button dots — selected (red) */
            [data-baseweb="radio"] div[role="radio"][aria-checked="true"] {{
                background-color: #e63946 !important;
                border-color: #e63946 !important;
            }}
            </style>
        """, unsafe_allow_html=True)

    def _render_login_screen(self) -> bool:
        """
        Show Oracle credentials login form.
        Returns True if user is authenticated, False otherwise.

        Credentials are stored in st.session_state only — never written to disk.
        """
        # Already logged in? Skip
        if st.session_state.get('oracle_logged_in', False):
            return True

        # Apply theme CSS only (no sidebar panel on login screen)
        self._apply_theme()

        # Show logo + title
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            try:
                st.image("logo-agsm.jpg", width=200)
            except:
                pass
            st.title("🔐 Oracle Course Automator")
            st.markdown(
                "Inserisci le tue credenziali Oracle HCM per accedere."
            )

            with st.form("oracle_login_form"):
                username = st.text_input(
                    "Username Oracle",
                    placeholder="nome.cognome@gruppomagis.it",
                    key="login_username_input"
                )
                password = st.text_input(
                    "Password Oracle",
                    type="password",
                    key="login_password_input"
                )
                submitted = st.form_submit_button(
                    "Accedi", type="primary", width='stretch'
                )

            if submitted:
                if not username.strip():
                    st.error("❌ Inserisci lo username.")
                    return False
                if not password:
                    st.error("❌ Inserisci la password.")
                    return False

                # ── FRONT-DOOR CREDENTIAL CHECK ──────────────────────────
                # Verify the credentials actually work in Oracle BEFORE
                # showing the app. Catches a wrong password in ~15-25s with
                # a clear message, instead of hanging later inside an
                # automation. Uses its own browser, always closed.
                import automation_lock
                from model import OracleAutomator

                # (Lock removed — one user at a time by scheduling.)

                verify_ok = False
                verify_error = None
                try:
                    with st.spinner(
                            "🔐 Verifica delle credenziali su Oracle in corso… "
                            "(può richiedere fino a ~25 secondi)"
                    ):
                        import streamlit as st_mod  # local alias, safe
                        driver_path = st.secrets['EDGE_DRIVER_PATH']
                        checker = OracleAutomator(
                            driver_path=driver_path,
                            debug_mode=False,
                            debug_pause=1,
                            headless=True,  # invisible; just a credential probe
                        )
                        # record driver pid into the lock (self-heal safety)
                        try:
                            automation_lock.set_driver_pid(
                                checker.driver.service.process.pid)
                        except Exception:
                            pass

                        oracle_url = st.secrets['ORACLE_URL']
                        verify_ok = checker.verify_credentials_only(
                            oracle_url, username.strip(), password
                        )
                except Exception as e:
                    verify_error = str(e)
                    verify_ok = False
                finally:
                    pass

                if not verify_ok:
                    if verify_error:
                        st.error(
                            "❌ Impossibile verificare le credenziali "
                            f"(errore tecnico: {verify_error}). Riprova."
                        )
                    else:
                        st.error(
                            "❌ Credenziali errate o accesso a Oracle non "
                            "riuscito.\n\nControlla username e password e "
                            "riprova. Se il problema persiste, verifica di "
                            "poter accedere a Oracle HCM dal browser."
                        )
                    # Do NOT mark as logged in; stay on the login screen.
                    return False

                # ── Credentials confirmed good — proceed ──
                st.session_state.oracle_username = username.strip()
                st.session_state.oracle_password = password
                st.session_state.oracle_logged_in = True

                import logging
                logging.info(f"App login (verified): user={username.strip()}")

                st.rerun()
        return False

    def render_logout_button(self):
        """Show logout button in sidebar. Call from render_ui()."""
        if st.session_state.get('oracle_logged_in'):
            with st.sidebar:
                st.markdown(f"👤 **{st.session_state.get('oracle_username', 'Utente')}**")
                if st.button("🚪 Logout", key="logout_btn", width='stretch'):
                    # Log the logout event
                    import logging
                    logging.info(
                        f"App logout: user={st.session_state.get('oracle_username', 'unknown')}"
                    )
                    # Clear all credentials from memory
                    for key in ['oracle_username', 'oracle_password', 'oracle_logged_in']:
                        if key in st.session_state:
                            del st.session_state[key]
                    st.rerun()

    def _update_nlp_text(self):
        """
        Callback function for NLP text area.
        Streamlit automatically updates session_state when key is used.
        """
        # ### HASHTAG: CALLBACK TO ENSURE TEXT AREA UPDATES ARE CAPTURED ###
        pass  # No action needed, key parameter handles state update

    def _clear_nlp_input_callback(self):
        """Safely clear NLP input and ALL related states."""
        # If using key in text_area, clear that key
        if "course_nlp_text_key" in st.session_state:
            st.session_state.course_nlp_text_key = ""

        # Clear tracking variables
        st.session_state.nlp_clear_requested = True
        st.session_state.course_nlp_input = ""
        st.session_state.course_parsed_data = None
        st.session_state.course_show_summary = False
        print("NLP cleared - all states reset")

    def get_user_options(self):
        st.sidebar.header("Impostazioni")
        headless = st.sidebar.toggle("Esegui in background", value=True)
        debug_mode = False
        debug_pause = 1
        if not headless:
            debug_mode = st.sidebar.toggle("Modalità lenta con pause", value=False)
            if debug_mode:
                debug_pause = st.sidebar.slider("Durata pausa (secondi)", 1, 5, 2)
        return headless, debug_mode, debug_pause

    def _render_impostazioni(self, themes_config):
        """
        Renders the Impostazioni colori panel in the sidebar.
        Users pick their theme and font — saved to session_state.
        """
        import json
        import os

        themes_path = os.path.join(os.path.dirname(__file__), 'themes.json')
        try:
            with open(themes_path, 'r', encoding='utf-8') as f:
                themes_config = json.load(f)
        except:
            st.sidebar.warning("⚠️ File temi non trovato.")
            return

        st.sidebar.markdown("---")
        st.sidebar.markdown("### ⚙️ Impostazioni colori")

        theme_names = list(themes_config['themes'].keys())
        font_names = list(themes_config['fonts'].keys())

        # Show color preview dots next to theme names
        theme_labels = []
        for name, props in themes_config['themes'].items():
            theme_labels.append(f"{name}")

        current_theme = st.session_state.get('user_theme', 'Scuro (default)')
        current_font = st.session_state.get('user_font', 'Sans-serif (default)')

        selected_theme = st.sidebar.selectbox(
            "🎨 Tema colori",
            options=theme_names,
            index=theme_names.index(current_theme)
            if current_theme in theme_names else 0,
            key="theme_selector"
        )

        selected_font = st.sidebar.selectbox(
            "🔤 Tipo di carattere",
            options=font_names,
            index=font_names.index(current_font)
            if current_font in font_names else 0,
            key="font_selector"
        )

        # Show a live preview swatch
        theme_props = themes_config['themes'].get(selected_theme, {})
        st.sidebar.markdown(
            f"""<div style="
                background-color: {theme_props.get('bg_color', '#000')};
                color: {theme_props.get('text_color', '#fff')};
                font-family: {themes_config['fonts'].get(selected_font, 'sans-serif')};
                padding: 10px;
                border-radius: 8px;
                margin-top: 8px;
                font-size: 13px;
                border: 1px solid #ccc;
            ">
            👁️ Anteprima testo<br>
            <small>Sfondo: {theme_props.get('bg_color', '')}</small>
            </div>""",
            unsafe_allow_html=True
        )

        if st.sidebar.button("Applica tema", key="apply_theme_btn"):
            st.session_state.user_theme = selected_theme
            st.session_state.user_font = selected_font
            st.rerun()

        # Save to file for persistence across sessions
        prefs_path = os.path.join(
            os.path.dirname(__file__), 'user_preferences.json')
        if st.sidebar.button("💾 Salva preferenze", key="save_theme_btn"):
            prefs = {
                'user_theme': selected_theme,
                'user_font': selected_font
            }
            with open(prefs_path, 'w', encoding='utf-8') as f:
                json.dump(prefs, f)
            st.sidebar.success("✅ Preferenze salvate!")

    def render_ui(self):
        # Apply theme FIRST before rendering anything else
        self._apply_theme()

        # Show logout button in sidebar
        self.render_logout_button()

        # Render settings in sidebar
        self._render_impostazioni({})
        is_running = st.session_state.app_state != "IDLE"

        # === SHOW BATCH EDITION RESULTS PROMINENTLY (if any) ===
        if st.session_state.get('show_edition_results', False) and st.session_state.get('edition_message', ''):
            st.markdown("---")
            # Show the result message with success/error styling
            if "✅" in st.session_state.edition_message or "Successo" in st.session_state.edition_message:
                st.success(st.session_state.edition_message)
            else:
                st.error(st.session_state.edition_message)

            # Clear button
            if st.button("🧹 Cancella Messaggio Risultati", key="clear_batch_edition_results"):
                st.session_state.edition_message = ""
                st.session_state.show_edition_results = False
                st.rerun()
            st.markdown("---")

        # Create 4 tabs
        tab1, tab2, tab3, tab4 = st.tabs([
            " 1.Creazione Corso",
            " 2.Creazione Edizione + Attività",
            " 3.Aggiungi Allievi",
            " 4.Assegnazione Presenza"
        ])

        # --- Tab1:Course Form Container ---
        with tab1:
            st.header("Creazione Nuovo Corso")
            # FIX: Include RUNNING_BATCH_COURSE in the condition
            if st.session_state.app_state in ["RUNNING_COURSE", "RUNNING_BATCH_COURSE"]:
                self.course_output_placeholder = st.empty()
            else:
                self._render_course_form(is_disabled=is_running)
                self.course_output_placeholder = st.empty()
                if st.session_state.course_message:
                    self.show_message("course", st.session_state.course_message, show_clear_button=True)

        # --- Tab2: Combined Edition + Activity Form Container ---
        with tab2:
            st.header("Creazione Nuova Edizione + Attività")
            # FIX: Include RUNNING_BATCH_EDITION in the condition (for future)
            if st.session_state.app_state in ["RUNNING_EDITION", "RUNNING_BATCH_EDITION"]:
                self.edition_output_placeholder = st.empty()
            else:
                self._render_edition_form(is_disabled=is_running)
                self.edition_output_placeholder = st.empty()
                if st.session_state.edition_message:
                    self.show_message("edition", st.session_state.edition_message, show_clear_button=True)

        # --- Tab3:Student Form Container ---
        with tab3:
            st.header("Aggiungi Allievi")
            if st.session_state.app_state in ["RUNNING_STUDENTS", "RUNNING_BATCH_STUDENTS", "RUNNING_VERIFY_STUDENTS"]:
                self.student_output_placeholder = st.empty()

            else:
                self._render_student_form(is_disabled=is_running)
                self.student_output_placeholder = st.empty()
                if st.session_state.student_message:
                    self.show_message("student", st.session_state.student_message, True)

        with tab4:
            st.header("Assegnazione Presenza")
            if st.session_state.app_state in ["RUNNING_PRESENZA",
                                              "RUNNING_BATCH_PRESENZA"]:
                self.student_output_placeholder = st.empty()
            else:
                self._render_presenza_form(is_disabled=is_running)

                # Show result message — standalone, does NOT use show_message()
                # to avoid duplicate key conflict with tab3's clear_student button
                if st.session_state.get('presenza_message'):
                    msg = st.session_state.presenza_message
                    if "✅" in msg or "Successo" in msg:
                        st.success(msg)
                    else:
                        st.error(msg)
                    if st.button("🧹 Cancella Risultato", key="clear_presenza_message"):
                        st.session_state.presenza_message = ""
                        st.rerun()

    def _clear_course_form_callback(self):
        st.session_state.course_title_key = ""
        st.session_state.course_programme_key = ""
        st.session_state.course_short_desc_key = ""
        st.session_state.course_date_str_key = "01/01/2023"

    # NEW HELPER METHOD - PARSE EXCEL FILE
    def _parse_excel_file(self, uploaded_file) -> Optional[Dict[str, Any]]:
        """
        Parse uploaded Excel file and extract MULTIPLE courses.

        NEW FORMAT (Vertical/Table):
        Row 1: NOME CORSO | DESCRIZIONE | DATA INIZIO PUBBLICAZIONE
        Row 2: Analitica  | Informatica | 1.1.2023
        Row 3: Musica     | Art         | 1.1.2023
        Row 4: Fine art   | Art         | 1.1.2023

        Returns: Dictionary with 'courses' list and metadata

        WHY: Vertical format scales to any number of courses and matches
        standard spreadsheet practices.
        """
        try:
            # ### HASHTAG: READ EXCEL WITH HEADER ROW ###
            # Read with first row as header
            df = pd.read_excel(uploaded_file, header=0, engine='openpyxl')

            # ### HASHTAG: NORMALIZE COLUMN NAMES ###
            # Remove extra spaces, convert to lowercase for matching
            df.columns = df.columns.str.strip().str.lower()

            # ### HASHTAG: SHOW WHAT COLUMNS WERE FOUND ###
            st.info(f"📊 Colonne trovate nel file: {', '.join(df.columns)}")

            # ### HASHTAG: DEFINE EXPECTED COLUMN MAPPINGS ###
            # Support multiple possible column names for flexibility
            column_mappings = {
                'title': ['nome corso', 'titolo', 'corso', 'nome', 'title'],
                'description': ['descrizione', 'desc', 'breve descrizione', 'description'],
                'date': ['data inizio pubblicazione', 'data pubblicazione', 'data inizio',
                         'data', 'pubblicazione', 'date', 'start date']
            }

            # ### HASHTAG: FIND ACTUAL COLUMN NAMES IN FILE ###
            found_columns = {}
            for field, possible_names in column_mappings.items():
                for possible_name in possible_names:
                    if possible_name in df.columns:
                        found_columns[field] = possible_name
                        break

            # ### HASHTAG: VALIDATE REQUIRED COLUMNS EXIST ###
            missing_columns = []
            for field in ['title', 'description', 'date']:
                if field not in found_columns:
                    missing_columns.append(field)

            if missing_columns:
                st.error(f"❌ Colonne mancanti nel file Excel: {', '.join(missing_columns)}")
                st.info("""
                **Formato richiesto:**
                - Colonna 1: NOME CORSO (o TITOLO, CORSO)
                - Colonna 2: DESCRIZIONE (o DESC)
                - Colonna 3: DATA INIZIO PUBBLICAZIONE (o DATA)
                """)
                return None

            # ### HASHTAG: EXTRACT ALL COURSES FROM ROWS ###
            courses_list = []
            skipped_rows = []

            for index, row in df.iterrows():
                # Get values from mapped columns
                title_val = row[found_columns['title']]
                desc_val = row[found_columns['description']]
                date_val = row[found_columns['date']]

                # ### HASHTAG: SKIP EMPTY ROWS ###
                if pd.isna(title_val) and pd.isna(desc_val) and pd.isna(date_val):
                    continue  # Skip completely empty rows

                # ### HASHTAG: VALIDATE ROW DATA ###
                if pd.isna(title_val) or not str(title_val).strip():
                    skipped_rows.append(f"Riga {index + 2}: Titolo mancante")
                    continue

                if pd.isna(desc_val) or not str(desc_val).strip():
                    skipped_rows.append(f"Riga {index + 2}: Descrizione mancante")
                    continue

                if pd.isna(date_val):
                    skipped_rows.append(f"Riga {index + 2}: Data mancante")
                    continue

                # ### HASHTAG: NORMALIZE DATE USING CENTRALIZED FUNCTION ###
                normalized_date = normalize_date(date_val)

                if not normalized_date:
                    skipped_rows.append(f"Riga {index + 2}: Formato data non valido ({date_val})")
                    continue

                # ### HASHTAG: ADD VALID COURSE TO LIST ###
                courses_list.append({
                    'title': str(title_val).strip(),
                    'short_description': str(desc_val).strip(),
                    'start_date': normalized_date,
                    'programme': "",  # Optional field, empty for now
                    'row_number': index + 2  # Excel row number for reference
                })

            # ### HASHTAG: SHOW SUMMARY OF PARSING RESULTS ###
            if skipped_rows:
                st.warning(f"⚠️ {len(skipped_rows)} righe saltate:")
                for skip_msg in skipped_rows:
                    st.write(f"- {skip_msg}")

            if not courses_list:
                st.error("❌ Nessun corso valido trovato nel file Excel.")
                return None

            st.success(f"✅ {len(courses_list)} corsi estratti con successo!")

            # ### HASHTAG: RETURN DATA STRUCTURE FOR BATCH PROCESSING ###
            return {
                'courses': courses_list,
                'total_count': len(courses_list),
                'skipped_count': len(skipped_rows),
                'file_name': uploaded_file.name
            }

        except Exception as e:
            st.error(f"❌ Errore durante la lettura del file Excel: {str(e)}")
            import traceback
            with st.expander("🔍 Dettagli errore"):
                st.code(traceback.format_exc())
            return None

    def _render_batch_course_preview(self, batch_data: Dict[str, Any]):
        """
        Display preview table of all courses from Excel with selection options.
        """
        if not batch_data or 'courses' not in batch_data:
            return

        st.success(f"✅ {batch_data['total_count']} corsi pronti per la creazione!")

        if batch_data.get('skipped_count', 0) > 0:
            st.info(f"ℹ️ {batch_data['skipped_count']} righe saltate (dati incompleti)")

        st.subheader("📋 Anteprima Corsi da Creare")

        # ### CREATE PREVIEW DATAFRAME ###
        preview_data = []
        for idx, course in enumerate(batch_data['courses']):
            # Format date for display
            date_display = course['start_date']
            if isinstance(date_display, (datetime, date)):
                date_display = date_display.strftime("%d/%m/%Y")

            preview_data.append({
                '#': idx + 1,
                'Titolo': course['title'],
                'Descrizione': course['short_description'],
                'Data Pubblicazione': date_display,
                'Riga Excel': course.get('row_number', '-')
            })

        preview_df = pd.DataFrame(preview_data)

        st.dataframe(
            preview_df,
            width='stretch',
            hide_index=True,
            column_config={
                '#': st.column_config.NumberColumn('#', width='small'),
                'Titolo': st.column_config.TextColumn('Titolo', width='medium'),
                'Descrizione': st.column_config.TextColumn('Descrizione', width='large'),
                'Data Pubblicazione': st.column_config.TextColumn('Data', width='small'),
                'Riga Excel': st.column_config.NumberColumn('Riga', width='small')
            }
        )

        st.divider()
        st.subheader("⚙️ Opzioni di Creazione")

        # ### OPTIONS (outside form) ###
        continue_on_error = st.checkbox(
            "Continua anche se un corso fallisce",
            value=True,
            help="Se deselezionato, si ferma al primo errore",
            key="batch_continue_checkbox"
        )

        st.divider()

        # ### BUTTONS (NO FORM - regular buttons) ###
        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            if st.button(
                    f"✅ Conferma e Crea {len(batch_data['courses'])} Corsi",
                    type="primary",
                    width='stretch',
                    key="batch_confirm_btn"
            ):
                # Convert string dates to date objects
                for course in batch_data['courses']:
                    date_str = course['start_date']
                    if isinstance(date_str, str):
                        try:
                            course['start_date'] = datetime.strptime(date_str, "%d/%m/%Y").date()
                        except ValueError:
                            st.error(f"❌ Formato data non valido per '{course['title']}': {date_str}")
                            st.stop()
                    elif isinstance(date_str, date):
                        course['start_date'] = date_str

                st.session_state.batch_course_data = batch_data
                st.session_state.batch_continue_on_error = continue_on_error
                st.session_state.app_state = "RUNNING_BATCH_COURSE"
                st.session_state.course_message = ""
                st.rerun()

        with col2:
            if st.button(
                    "✏️ Modifica",
                    width='stretch',
                    key="batch_edit_btn"
            ):
                # Transfer data to edit mode
                st.session_state.course_edit_mode = True
                st.session_state.courses_to_edit = batch_data['courses'].copy()
                st.session_state.course_parsed_data = None
                st.session_state.course_show_summary = False
                st.rerun()

        with col3:
            if st.button(
                    "❌ Annulla",
                    width='stretch',
                    key="batch_cancel_btn"
            ):
                st.session_state.course_parsed_data = None
                st.session_state.course_show_summary = False
                st.session_state.course_input_method = "structured"
                st.session_state.course_edit_mode = False
                st.session_state.courses_to_edit = []
                st.rerun()

        # NEW HELPER METHOD - PARSE EXCEL FILE FOR BATCH (VERTICAL FORMAT)

    def _render_editable_courses_form(self):
        """
        Render editable form for courses imported from Excel.
        Users can modify each course before batch creation.
        """
        courses = st.session_state.courses_to_edit

        if not courses:
            st.warning("Nessun corso da modificare.")
            if st.button("⬅️ Torna indietro"):
                st.session_state.course_edit_mode = False
                st.rerun()
            return

        st.subheader(f"✏️ Modifica {len(courses)} Corsi")
        st.info("Modifica i dettagli di ogni corso, poi clicca 'Crea Tutti i Corsi' quando pronto.")

        # Add/Remove course buttons
        col_add, col_remove, col_spacer = st.columns([1, 1, 2])
        with col_add:
            if st.button("➕ Aggiungi Corso", key="add_course_btn"):
                st.session_state.courses_to_edit.append({
                    'title': '',
                    'short_description': '',
                    'start_date': '01/01/2023',
                    'programme': ''
                })
                st.rerun()

        with col_remove:
            if len(courses) > 1:
                if st.button("➖ Rimuovi Ultimo", key="remove_course_btn"):
                    st.session_state.courses_to_edit.pop()
                    st.rerun()

        st.divider()

        # EDITABLE FORM FOR EACH COURSE
        with st.form(key='edit_courses_form'):
            for idx, course in enumerate(courses):
                with st.expander(f"📚 Corso {idx + 1}: {course.get('title', 'Nuovo Corso') or 'Nuovo Corso'}",
                                 expanded=(idx < 3)):
                    col1, col2 = st.columns([2, 1])

                    with col1:
                        st.text_input(
                            "Titolo del Corso",
                            value=course.get('title', ''),
                            key=f"edit_title_{idx}",
                            placeholder="Inserisci il titolo del corso"
                        )

                    with col2:
                        # Handle date - could be string or date object
                        date_value = course.get('start_date', '')
                        if isinstance(date_value, date):
                            date_str = date_value.strftime("%d/%m/%Y")
                        else:
                            date_str = str(date_value) if date_value else ''

                        st.text_input(
                            "Data Pubblicazione (GG/MM/AAAA)",
                            value=date_str,
                            key=f"edit_date_{idx}",
                            placeholder="01/01/2023"
                        )

                    st.text_input(
                        "Breve Descrizione",
                        value=course.get('short_description', ''),
                        key=f"edit_desc_{idx}",
                        placeholder="Inserisci una breve descrizione"
                    )

                    st.text_area(
                        "Programma",
                        value=course.get('programme', ''),
                        key=f"edit_prog_{idx}",
                        height=80,
                        placeholder="Dettagli del programma..."
                    )

            st.divider()

            # Form submit buttons
            col1, col2, col3 = st.columns([2, 1, 1])

            with col1:
                submit = st.form_submit_button(
                    f"✅ Crea Tutti i {len(courses)} Corsi",
                    type="primary",
                    width='stretch'
                )

            with col2:
                back_to_preview = st.form_submit_button(
                    "👁️ Anteprima",
                    width='stretch'
                )

            with col3:
                cancel = st.form_submit_button(
                    "❌ Annulla",
                    width='stretch'
                )

        # Handle form actions
        if submit:
            # Validate and collect all courses
            valid_courses = []
            has_errors = False

            for idx in range(len(courses)):
                title = st.session_state.get(f"edit_title_{idx}", '').strip()
                desc = st.session_state.get(f"edit_desc_{idx}", '').strip()
                date_str = st.session_state.get(f"edit_date_{idx}", '').strip()
                prog = st.session_state.get(f"edit_prog_{idx}", '').strip()

                # Validate required fields
                if not title:
                    st.error(f"❌ Corso {idx + 1}: Il titolo è obbligatorio.")
                    has_errors = True
                    continue

                if not desc:
                    st.error(f"❌ Corso {idx + 1}: La descrizione è obbligatoria.")
                    has_errors = True
                    continue

                if not date_str:
                    st.error(f"❌ Corso {idx + 1}: La data è obbligatoria.")
                    has_errors = True
                    continue

                # Validate date format
                try:
                    date_obj = datetime.strptime(date_str, "%d/%m/%Y").date()
                except ValueError:
                    st.error(f"❌ Corso {idx + 1}: Formato data non valido. Usa GG/MM/AAAA.")
                    has_errors = True
                    continue

                valid_courses.append({
                    'title': title,
                    'short_description': desc,
                    'start_date': date_obj,
                    'programme': prog,
                    'row_number': idx + 1
                })

            if has_errors:
                st.stop()

            if not valid_courses:
                st.error("❌ Nessun corso valido da creare.")
                st.stop()

            # Prepare batch data and start creation
            batch_data = {
                'courses': valid_courses,
                'total_count': len(valid_courses),
                'skipped_count': 0,
                'file_name': 'Modificato manualmente'
            }

            st.session_state.batch_course_data = batch_data
            st.session_state.batch_continue_on_error = True
            st.session_state.app_state = "RUNNING_BATCH_COURSE"
            st.session_state.course_message = ""
            st.session_state.course_edit_mode = False
            st.session_state.courses_to_edit = []
            st.rerun()

        elif back_to_preview:
            # Save edits and go back to preview
            updated_courses = []
            for idx in range(len(courses)):
                updated_courses.append({
                    'title': st.session_state.get(f"edit_title_{idx}", ''),
                    'short_description': st.session_state.get(f"edit_desc_{idx}", ''),
                    'start_date': st.session_state.get(f"edit_date_{idx}", ''),
                    'programme': st.session_state.get(f"edit_prog_{idx}", ''),
                    'row_number': idx + 1
                })

            st.session_state.course_parsed_data = {
                'courses': updated_courses,
                'total_count': len(updated_courses),
                'skipped_count': 0,
                'file_name': 'Modificato'
            }
            st.session_state.course_show_summary = True
            st.session_state.course_edit_mode = False
            st.session_state.courses_to_edit = []
            st.rerun()

        elif cancel:
            # Reset everything
            st.session_state.course_edit_mode = False
            st.session_state.courses_to_edit = []
            st.session_state.course_parsed_data = None
            st.session_state.course_show_summary = False
            st.session_state.course_input_method = "structured"
            st.rerun()

    def _parse_excel_batch(self, uploaded_file) -> Optional[Dict[str, Any]]:
            """
            Parse uploaded Excel file with MULTIPLE courses (vertical/table format).

            NEW FORMAT (Vertical/Table):
            Row 1: NOME CORSO | DESCRIZIONE | DATA INIZIO PUBBLICAZIONE
            Row 2: Analitica  | Informatica | 1.1.2023
            Row 3: Musica     | Art         | 1.1.2023

            Returns: Dictionary with 'courses' list and metadata
            """
            try:
                # Read Excel with first row as header
                df = pd.read_excel(uploaded_file, header=0, engine='openpyxl')

                # Normalize column names
                df.columns = df.columns.str.strip().str.lower()

                st.info(f"📊 Colonne trovate: {', '.join(df.columns)}")

                # Define expected column mappings
                column_mappings = {
                    'title': ['nome corso', 'titolo', 'corso', 'nome'],
                    'description': ['descrizione', 'desc', 'breve descrizione'],
                    'date': ['data inizio pubblicazione', 'data pubblicazione', 'data inizio', 'data']
                }

                # Find actual column names in file
                found_columns = {}
                for field, possible_names in column_mappings.items():
                    for possible_name in possible_names:
                        if possible_name in df.columns:
                            found_columns[field] = possible_name
                            break

                # Validate required columns exist
                missing_columns = []
                for field in ['title', 'description', 'date']:
                    if field not in found_columns:
                        missing_columns.append(field)

                if missing_columns:
                    st.error(f"❌ Colonne mancanti: {', '.join(missing_columns)}")
                    st.info("""
                    **Formato richiesto:**
                    - Colonna 1: NOME CORSO (o TITOLO)
                    - Colonna 2: DESCRIZIONE
                    - Colonna 3: DATA INIZIO PUBBLICAZIONE (o DATA)
                    """)
                    return None

                # Extract all courses from rows
                courses_list = []
                skipped_rows = []

                for index, row in df.iterrows():
                    title_val = row[found_columns['title']]
                    desc_val = row[found_columns['description']]
                    date_val = row[found_columns['date']]

                    # Skip empty rows
                    if pd.isna(title_val) and pd.isna(desc_val) and pd.isna(date_val):
                        continue

                    # Validate row data
                    if pd.isna(title_val) or not str(title_val).strip():
                        skipped_rows.append(f"Riga {index + 2}: Titolo mancante")
                        continue

                    if pd.isna(desc_val) or not str(desc_val).strip():
                        skipped_rows.append(f"Riga {index + 2}: Descrizione mancante")
                        continue

                    if pd.isna(date_val):
                        skipped_rows.append(f"Riga {index + 2}: Data mancante")
                        continue

                    # Normalize date
                    normalized_date = normalize_date(date_val)

                    if not normalized_date:
                        skipped_rows.append(f"Riga {index + 2}: Formato data non valido ({date_val})")
                        continue

                    # Add valid course to list
                    courses_list.append({
                        'title': str(title_val).strip(),
                        'short_description': str(desc_val).strip(),
                        'start_date': normalized_date,
                        'programme': "",
                        'row_number': index + 2
                    })

                # Show summary
                if skipped_rows:
                    st.warning(f"⚠️ {len(skipped_rows)} righe saltate:")
                    for skip_msg in skipped_rows:
                        st.write(f"- {skip_msg}")

                if not courses_list:
                    st.error("❌ Nessun corso valido trovato.")
                    return None

                st.success(f"✅ {len(courses_list)} corsi estratti!")

                return {
                    'courses': courses_list,
                    'total_count': len(courses_list),
                    'skipped_count': len(skipped_rows),
                    'file_name': uploaded_file.name
                }

            except Exception as e:
                st.error(f"❌ Errore lettura Excel: {str(e)}")
                import traceback
                with st.expander("🔍 Dettagli errore"):
                    st.code(traceback.format_exc())
                return None

    def _parse_nlp_input(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Parse natural language input by finding keyword positions
        and extracting text BETWEEN them.

        Pipeline:
        1. Find keyword positions: titolo, descrizione, data, programma
        2. Sort by position, extract value between consecutive keywords
        3. Fallback: 'corso X' pattern if 'titolo' keyword not found
        4. Fallback: search for date anywhere in text if 'data' keyword missing
        5. Show partial results in UI with per-field status
        """
        if not text or not text.strip():
            return None

        try:
            import re

            parsed_data = {
                'title': "",
                'short_description': "",
                'start_date': "",
                'programme': ""
            }

            original_text = text
            text_lower = text.lower()

            # ═══════════════════════════════════════════════════
            # STEP 1: Find positions of each keyword
            # ═══════════════════════════════════════════════════
            keywords = {
                'titolo': r'\btitolo\b',
                'descrizione': r'\bdescrizione(?:\s+breve)?\b',
                'data': (r'\bdata(?:\s+(?:di\s+)?(?:inizio|pubblicazione))?\b'
                         r'|\bpubblicazione\b'),
                'programma': r'\bprogramma\b',
            }

            positions = {}
            for key, pattern in keywords.items():
                match = re.search(pattern, text_lower)
                if match:
                    positions[key] = {
                        'start': match.start(),
                        'end': match.end()
                    }

            # ═══════════════════════════════════════════════════
            # STEP 2: Sort keywords by position and extract values between them
            # ═══════════════════════════════════════════════════
            sorted_keys = sorted(positions.keys(),
                                 key=lambda k: positions[k]['start'])

            for i, key in enumerate(sorted_keys):
                value_start = positions[key]['end']
                if i + 1 < len(sorted_keys):
                    value_end = positions[sorted_keys[i + 1]]['start']
                else:
                    value_end = len(original_text)

                value = original_text[value_start:value_end].strip()
                # Strip trailing connectors and punctuation
                value = re.sub(r'\s+(con|e|ed)\s*$', '', value,
                               flags=re.IGNORECASE).strip()
                value = value.strip(' ,;:-')

                if key == 'titolo':
                    parsed_data['title'] = value
                elif key == 'descrizione':
                    parsed_data['short_description'] = value
                elif key == 'data':
                    # Find numeric date inside the slice
                    date_match = re.search(
                        r'(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4})', value)
                    if date_match:
                        parsed_data['start_date'] = (
                                normalize_date(date_match.group(1)) or '')
                    else:
                        # Try Italian month name (e.g., "12 marzo 2024")
                        italian = parse_italian_date(value)
                        if italian:
                            parsed_data['start_date'] = italian
                elif key == 'programma':
                    parsed_data['programme'] = value

            # ═══════════════════════════════════════════════════
            # STEP 3: FALLBACK — "corso X" pattern if 'titolo' keyword not used
            # Example: "Crea un corso Excel Base data 01/01/2024"
            # ═══════════════════════════════════════════════════
            if not parsed_data['title']:
                corso_match = re.search(
                    r'\bcorso\s+(.+?)'
                    r'(?=\s+descrizione|\s+data\s|\s+pubblicazione'
                    r'|\s+programma|\s+con\s+descrizione|$)',
                    text_lower, re.IGNORECASE)
                if corso_match:
                    value = original_text[
                            corso_match.start(1):corso_match.end(1)].strip()
                    value = re.sub(r'\s+(con|e|ed)\s*$', '', value,
                                   flags=re.IGNORECASE).strip()
                    value = value.strip(' ,;:-')
                    if value:
                        parsed_data['title'] = value

            # ═══════════════════════════════════════════════════
            # STEP 4: FALLBACK — find date anywhere in text
            # if 'data' keyword wasn't found at all
            # ═══════════════════════════════════════════════════
            if not parsed_data['start_date']:
                # Try Italian month names anywhere in text
                italian = parse_italian_date(text_lower)
                if italian:
                    parsed_data['start_date'] = italian
                else:
                    # Try numeric date anywhere
                    date_match = re.search(
                        r'\b(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4})\b',
                        original_text)
                    if date_match:
                        parsed_data['start_date'] = (
                                normalize_date(date_match.group(1)) or '')

            # ═══════════════════════════════════════════════════
            # STEP 5: Validate and report with detailed UI feedback
            # ═══════════════════════════════════════════════════
            missing_fields = []
            if not parsed_data['title'].strip():
                missing_fields.append("Titolo")
            if not parsed_data['short_description'].strip():
                missing_fields.append("Descrizione")
            if not parsed_data['start_date'].strip():
                missing_fields.append("Data")

            if missing_fields:
                st.warning(f"⚠️ Campi mancanti: {', '.join(missing_fields)}")

                extracted_count = sum([
                    bool(parsed_data['title'].strip()),
                    bool(parsed_data['short_description'].strip()),
                    bool(parsed_data['start_date'].strip())
                ])

                if extracted_count > 0:
                    st.success(f"✅ Estratti {extracted_count}/3 campi con successo!")
                    st.info("**Dati estratti finora:**")

                    if parsed_data['title'].strip():
                        st.write(f"- ✅ **Titolo:** `{parsed_data['title']}`")
                    else:
                        st.write(f"- ❌ **Titolo:** non trovato")

                    if parsed_data['short_description'].strip():
                        st.write(
                            f"- ✅ **Descrizione:** `{parsed_data['short_description']}`")
                    else:
                        st.write(f"- ❌ **Descrizione:** non trovata")

                    if parsed_data['start_date'].strip():
                        st.write(f"- ✅ **Data:** `{parsed_data['start_date']}`")
                    else:
                        st.write(f"- ❌ **Data:** non trovata")

                    st.info(
                        "💡 **Suggerimento:** Puoi comunque procedere. "
                        "I campi mancanti potranno essere inseriti "
                        "manualmente nel riepilogo.")

                    return parsed_data
                else:
                    return None

            return parsed_data

        except Exception as e:
            st.error(f"Errore durante l'analisi NLP: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
            return None

    def _clear_edition_activity_form_callback(self):
        """Clear all edition and activity form fields"""
        # Clear edition fields
        st.session_state.edition_course_name_key = ""
        st.session_state.edition_title_key = ""
        st.session_state.edition_start_date_str_key = ""
        st.session_state.edition_end_date_str_key = ""
        st.session_state.edition_description_key = ""
        st.session_state.edition_location_key = ""
        st.session_state.edition_supplier_key = ""
        st.session_state.edition_price_key = ""

        # Clear the "Attributi Aggiuntivi" fields too (these were missed before,
        # which is why some fields stayed filled after Pulisci).
        st.session_state.edition_centro_costo_key = ""
        st.session_state.edition_societa_pagante_key = ""
        st.session_state.edition_direzione_pagante_key = ""
        st.session_state.edition_servizio_pagante_key = ""
        st.session_state.edition_sottotipologia_key = ""
        st.session_state.edition_finanziata_key = ""

        st.session_state.num_activities = 1

        # ✅ Clear preserved data to prevent restoration of old values
        st.session_state.preserved_activity_data = {}

        # Clear ALL activity fields
        for i in range(30):
            if f"activity_title_{i}" in st.session_state:
                st.session_state[f"activity_title_{i}"] = ""
            if f"activity_desc_{i}" in st.session_state:
                st.session_state[f"activity_desc_{i}"] = ""
            if f"activity_date_{i}" in st.session_state:
                st.session_state[f"activity_date_{i}"] = ""
            if f"activity_start_time_{i}" in st.session_state:
                st.session_state[f"activity_start_time_{i}"] = "09.00"
            if f"activity_end_time_{i}" in st.session_state:
                st.session_state[f"activity_end_time_{i}"] = "11.00"
            if f"impegno_previsto_in_ore_{i}" in st.session_state:
                st.session_state[f"impegno_previsto_in_ore_{i}"] = ""

        print("Edition+Activity form cleared")

    def _clear_edition_nlp_callback(self):
        """Clear NLP input for edition - must clear the KEY-based state"""
        # Clear the widget's key-based state (this is what Streamlit uses internally)
        st.session_state.edition_nlp_text_area = ""  # ✅ Clear the KEY!

        # Also clear our tracking variables
        st.session_state.edition_nlp_input = ""
        st.session_state.edition_parsed_data = None
        st.session_state.edition_show_summary = False
        print("DEBUG: Edition NLP cleared")

    def _clear_student_form_callback(self):
        st.session_state.student_edition_code_key = ""
        st.session_state.num_students = 1
        st.session_state.student_input_method = "txt"  # <-- was "manual"
        st.session_state.student_parsed_data = None
        st.session_state.student_show_summary = False

        st.session_state.preserved_student_data = {}
        for i in range(50):
            if f"student_name_{i}" in st.session_state:
                st.session_state[f"student_name_{i}"] = ""

    # NEW HELPER METHOD - DISPLAY SUMMARY WITH EDIT/CONFIRM
    #---COURSE---
    def _render_course_summary(self):
        """
        Display parsed course data in a summary format with Edit/Confirm buttons.
        """
        if not st.session_state.course_parsed_data:
            return
            # ### HASHTAG: CHECK IF BATCH OR SINGLE ###
        if 'courses' in st.session_state.course_parsed_data:
                # Batch format - show preview table
                self._render_batch_course_preview(st.session_state.course_parsed_data)
                return
        st.success("✅ Dati estratti con successo!")

        st.subheader("Riepilogo Corso")

        # ### HASHTAG: DISPLAY PARSED DATA IN EDITABLE FORMAT ###
        with st.form(key='course_summary_form'):
            title = st.text_input(
                "Titolo del Corso",
                value=st.session_state.course_parsed_data.get('title', ''),
                key="summary_title"
            )

            short_desc = st.text_input(
                "Breve Descrizione",
                value=st.session_state.course_parsed_data.get('short_description', ''),
                key="summary_short_desc"
            )

            date_str = st.text_input(
                "Data di Pubblicazione (GG/MM/AAAA)",
                value=st.session_state.course_parsed_data.get('start_date', ''),
                key="summary_date"
            )

            programme = st.text_area(
                "Dettagli del Programma",
                value=st.session_state.course_parsed_data.get('programme', ''),
                key="summary_programme"
            )

            col1, col2, col3 = st.columns([2, 1, 1])

            with col1:
                confirm = st.form_submit_button("✅ Conferma e Crea Corso", type="primary", width='stretch')

            with col2:
                edit = st.form_submit_button("✏️ Modifica", width='stretch')

            with col3:
                cancel = st.form_submit_button("❌ Annulla", width='stretch')

        # ### HASHTAG: HANDLE FORM ACTIONS ###
        if confirm:
            # Validate and submit
            if not all([title.strip(), short_desc.strip(), date_str.strip()]):
                st.error("I campi 'Titolo', 'Breve Descrizione' e 'Data' sono obbligatori.")
                st.stop()

            try:
                start_date_obj = datetime.strptime(date_str, "%d/%m/%Y").date()

                # Update parsed data with edited values
                st.session_state.course_details = {
                    "title": title,
                    "programme": programme,
                    "short_description": short_desc,
                    "start_date": start_date_obj
                }

                # Start automation
                st.session_state.app_state = "RUNNING_COURSE"
                st.session_state.course_message = ""
                st.session_state.course_show_summary = False
                st.session_state.course_parsed_data = None
                st.rerun()

            except ValueError:
                st.error("Formato data non valido. Usa GG/MM/AAAA.")
                st.stop()

        elif edit:
            # Stay on summary page, allow editing
            st.info("Modifica i campi sopra e clicca 'Conferma' quando pronto.")

        elif cancel:
            # Reset to input selection
            st.session_state.course_show_summary = False
            st.session_state.course_parsed_data = None
            st.session_state.course_input_method = "structured"
            st.rerun()

    def _render_course_form(self, is_disabled):
        """
        Enhanced course form with three input methods:
        1. Structured input (original)
        2. Excel file upload
        3. Natural language processing
        """

        # ### CHECK FOR EDIT MODE FIRST ###
        if st.session_state.get('course_edit_mode', False) and st.session_state.get('courses_to_edit'):
            self._render_editable_courses_form()
            return

        # SHOW SUMMARY IF DATA IS PARSED
        if st.session_state.course_show_summary and st.session_state.course_parsed_data:
            self._render_course_summary()
            return  # Don't show input selection while summary is displayed

        # ### HASHTAG: INPUT METHOD SELECTION ###
        st.subheader("Scegli il Metodo di Inserimento")

        input_method = st.radio(
            "Come vuoi inserire i dati del corso?",
            options=["structured", "excel", "nlp"],
            format_func=lambda x: {
                "structured": "📝 Input Strutturato (Form)",
                "excel": "📊 Caricamento File Excel",
                "nlp": "💬 Compilazione con AI"
            }[x],
            key="course_input_method",
            horizontal=True
        )

        st.divider()

        # RENDER APPROPRIATE INPUT INTERFACE BASED ON SELECTION ###

        # ========== METHOD 1: STRUCTURED INPUT (ORIGINAL) ==========
        if input_method == "structured":
            with st.form(key='course_form'):
                course_title = st.text_input("Titolo del Corso",
                                             key="course_title_key")
                programme = st.text_area("Dettagli del Programma",
                                         key="course_programme_key")
                short_desc = st.text_input("Breve Descrizione",
                                           key="course_short_desc_key")
                date_str = st.text_input("Data di Pubblicazione (GG/MM/AAAA)", key="course_date_str_key")

                col1, col2 = st.columns([3, 1])
                with col1:
                    submitted = st.form_submit_button("Crea Corso", type="primary", disabled=is_disabled,
                                                      width='stretch')
                with col2:
                    st.form_submit_button("Pulisci 🧹", width='stretch',
                                          on_click=self._clear_course_form_callback)

            if submitted:
                missing = False
                if not course_title.strip():
                    st.markdown("<span style='color:red'>⚠️ Il campo 'Titolo corso' è obbligatorio...</span>",
                                unsafe_allow_html=True)
                    missing = True
                if not short_desc.strip():
                    st.markdown("<span style='color:red'>⚠️ Il campo 'Breve Descrizione' è obbligatorio...</span>",
                                unsafe_allow_html=True)
                    missing = True
                if not date_str.strip():
                    st.markdown("<span style='color:red'>⚠️ Il campo 'Data di Pubblicazione' è obbligatorio...</span>",
                                unsafe_allow_html=True)
                    missing = True
                if missing:
                    st.stop()

                try:
                    start_date_obj = datetime.strptime(date_str, "%d/%m/%Y").date()
                    st.session_state.course_details = {
                        "title": course_title,
                        "programme": programme,
                        "short_description": short_desc,
                        "start_date": start_date_obj
                    }
                    st.session_state.app_state = "RUNNING_COURSE"
                    st.session_state.course_message = ""
                    st.rerun()
                except ValueError:
                    st.error("Formato data non valido. Usa GG/MM/AAAA.")
                    st.stop()

        # ========== METHOD 2: EXCEL FILE UPLOAD ==========
        elif input_method == "excel":
            # ### HASHTAG: CHECK IF SHOWING BATCH PREVIEW ###
            if st.session_state.course_show_summary and st.session_state.course_parsed_data:
                # Show batch preview instead of single course summary
                if 'courses' in st.session_state.course_parsed_data:
                    self._render_batch_course_preview(st.session_state.course_parsed_data)
                else:
                    # Fallback to single course (backward compatibility)
                    self._render_course_summary()
                return

            # st.info("""
            # **Formato Excel Richiesto (Verticale/Tabella):**
            #
            # | NOME CORSO | DESCRIZIONE | DATA INIZIO PUBBLICAZIONE |
            # |------------|-------------|---------------------------|
            # | Analitica  | Informatica | 1.1.2023                  |
            # | Musica     | Art         | 1.1.2023                  |
            # | Fine art   | Art         | 1.1.2023                  |
            #
            # **Note:**
            # - La prima riga deve contenere i nomi delle colonne
            # - Ogni riga successiva rappresenta un corso
            # - Puoi includere quanti corsi desideri
            # - Le righe incomplete verranno saltate
            # """, icon="ℹ️")

            uploaded_file = st.file_uploader(
                "Carica File Excel (.xlsx, .xls)",
                type=['xlsx', 'xls'],
                help="File con uno o più corsi in formato tabella"
            )

            if uploaded_file is not None:
                col1, col2 = st.columns([1, 1])

                with col1:
                    if st.button("📊 Analizza File Excel", type="primary", width='stretch'):
                        # ### HASHTAG: PARSE EXCEL AND SHOW PREVIEW ###
                        with st.spinner("🔍 Lettura file Excel..."):
                            parsed_data = self._parse_excel_file(uploaded_file)

                        if parsed_data:
                            st.session_state.course_parsed_data = parsed_data
                            st.session_state.course_show_summary = True
                            st.rerun()
                        else:
                            st.error("❌ Impossibile estrarre i dati dal file. Verifica il formato.")

                with col2:
                    if st.button("🧹 Cancella File", width='stretch'):
                        st.rerun()

        # ========== METHOD 3: NATURAL LANGUAGE PROCESSING ==========
        elif input_method == "nlp":
            # ### HASHTAG: TEMPORARY DEBUG - REMOVE AFTER FIXING ###
            # with st.expander("🔍 Debug - Stato NLP (rimuovi dopo test)", expanded=False):
            #     st.write("**Session State Values:**")
            #     st.write(f"- `course_nlp_input`: `{st.session_state.get('course_nlp_input', 'NOT SET')}`")
            #     st.write(f"- `course_parsed_data`: `{st.session_state.get('course_parsed_data', 'NOT SET')}`")
            #     st.write(f"- `course_show_summary`: `{st.session_state.get('course_show_summary', 'NOT SET')}`")
            #     st.write(f"- `nlp_clear_requested`: `{st.session_state.get('nlp_clear_requested', 'NOT SET')}`")
            #     st.write(f"- `app_state`: `{st.session_state.get('app_state', 'NOT SET')}`")
            st.info("""
            **Scrivi una frase che descriva il corso**, ad esempio:

            - "Crea un corso titolo Analisi dei Dati con descrizione competenze digitali data inizio 15/03/2024"

            Il sistema estrarrà automaticamente le informazioni rilevanti.
            """, icon="💡")

            #Handle clear request
            if st.session_state.get('nlp_clear_requested', False):
                # Reset the input to empty string
                st.session_state.course_nlp_input = ""
                st.session_state.nlp_clear_requested = False

                # DOUBLE-CHECK OTHER STATES ARE CLEARED ###
                # (Callback should have done this, but ensure it)
                if st.session_state.course_parsed_data is not None:
                    st.session_state.course_parsed_data = None
                if st.session_state.course_show_summary:
                    st.session_state.course_show_summary = False

                #FORCE CLEAN RERUN ###
                st.rerun()

            nlp_text = st.text_area(
                "Descrivi il corso in linguaggio naturale:",
                height=150, value=st.session_state.course_nlp_input,#use value instead of key for manual holder
                placeholder="",
                help="Scrivi una frase completa con titolo, descrizione e data del corso"
            )
            #update session state manually
            st.session_state.course_nlp_input = nlp_text

            # SHOW CHARACTER COUNT TO USER ###
            text_length = len(nlp_text.strip()) if nlp_text else 0
            if text_length > 0:
                st.caption(f"✏️ {text_length} caratteri inseriti")
            else:
                st.warning("⚠️Inserisci del testo per abilitare l'analisi")

            col1, col2 = st.columns([1, 1])

            with col1:
                analyze_clicked = st.button(
                    "🤖 Analizza Testo (NLP)",
                    type="primary",
                    width='stretch',
                    key="analyze_nlp_button"  # Add unique key
                )

                if analyze_clicked:
                    # ### HASHTAG: VALIDATION CHECKS ###
                    if not nlp_text or not nlp_text.strip():
                        st.error("⚠️ Per favore, inserisci del testo prima di analizzare.")
                        st.stop()

                    if text_length < 20:
                        st.error("⚠️ Il testo è troppo corto. Scrivi una frase più completa.")
                        st.stop()

                    # ### HASHTAG: CLEAR ANY OLD PARSED DATA BEFORE NEW ANALYSIS ###
                    # This prevents the "nothing happens" issue
                    st.session_state.course_parsed_data = None
                    st.session_state.course_show_summary = False

                    # ### HASHTAG: PERFORM ANALYSIS ###
                    with st.spinner("🤖 Analisi del testo in corso..."):
                        parsed_data = self._parse_nlp_input(nlp_text)

                    # ### HASHTAG: HANDLE ANALYSIS RESULTS ###
                    if parsed_data:
                        st.session_state.course_parsed_data = parsed_data
                        st.session_state.course_show_summary = True
                        st.rerun()
                    else:
                        st.error("""
                            ❌ Impossibile estrarre le informazioni necessarie.

                            Assicurati di includere:
                            - **Titolo** del corso (es: "titolo Excel Base")
                            - **Descrizione** breve (es: "descrizione Gestione fogli di calcolo")
                            - **Data** di inizio (es: "data inizio 01/01/2023" o "pubblicazione 01/01/2023")
                            """)
            with col2:
                # ### HASHTAG: CLEAR BUTTON WITH CALLBACK ###
                if st.button("🧹 Cancella Testo", width='stretch',
                             on_click=self._clear_nlp_input_callback,
                             key="clear_nlp_text_button"):
                    pass  #callback handles the clearing

    def _parse_edition_excel_file(self, uploaded_file) -> Optional[Dict[str, Any]]:
        """
        Universal parser that auto-detects Excel format:

        Format 1: Two sheets (Edizioni + Attivita) with ID linking
        Format 2: Single sheet with TIPO column (EDIZIONE/ATTIVITA markers)
        Format 3: Single sheet with edition headers followed by activity rows
        """
        try:
            excel_file = pd.ExcelFile(uploaded_file, engine='openpyxl')
            sheet_names = excel_file.sheet_names
            sheet_names_lower = [s.lower() for s in sheet_names]

            st.info(f"📊 Fogli trovati: {', '.join(sheet_names)}")

            # === DETECT FORMAT ===

            # Check for two-sheet format
            has_editions_sheet = any('edizion' in s for s in sheet_names_lower)
            has_activities_sheet = any('attivit' in s for s in sheet_names_lower)

            if has_editions_sheet and has_activities_sheet:
                st.success("✅ Rilevato formato: Due fogli separati (Edizioni + Attività)")
                return self._parse_two_sheet_edition_excel(excel_file)

            # Single sheet - check for TIPO column or detect pattern
            df = pd.read_excel(excel_file, sheet_name=0, header=None)

            # Check first column for "TIPO" or "EDIZIONE"/"ATTIVITA" markers
            first_col_values = df.iloc[:, 0].astype(str).str.lower().tolist()

            if 'tipo' in first_col_values or any('edizione' in v for v in first_col_values):
                st.success("✅ Rilevato formato: Foglio singolo con marcatori TIPO")
                return self._parse_single_sheet_with_markers(excel_file)

            # Check for your original format (header pattern detection)
            if self._detect_original_format(df):
                st.success("✅ Rilevato formato: Foglio singolo con intestazioni ripetute")
                return self._parse_original_format(excel_file)

            st.error("❌ Formato Excel non riconosciuto")
            return None

        except Exception as e:
            st.error(f"❌ Errore: {str(e)}")
            return None

    def _parse_single_sheet_with_markers(self, excel_file) -> Optional[Dict[str, Any]]:
        """Parse single sheet with TIPO column (EDIZIONE/ATTIVITA markers)"""
        df = pd.read_excel(excel_file, sheet_name=0)
        df.columns = df.columns.str.strip().str.lower()

        editions_list = []
        current_edition = None

        for idx, row in df.iterrows():
            row_type = str(row.get('tipo', '')).strip().lower()

            if 'edizione' in row_type:
                # Save previous edition if exists
                if current_edition:
                    editions_list.append(current_edition)

                # Start new edition
                current_edition = {
                    'course_name': str(row.get('nome_corso', '')).strip(),
                    'edition_title': str(row.get('titolo', '')).strip(),
                    'start_date': normalize_date(row.get('data_inizio', '')),
                    'end_date': normalize_date(row.get('data_fine', '')),
                    'location': str(row.get('aula', '')).strip(),
                    'supplier': str(row.get('fornitore', '')).strip(),
                    'price': str(row.get('costo', '')).strip(),
                    'description': '',
                    'activities': []
                }

            elif 'attivita' in row_type and current_edition:
                # Add activity to current edition
                activity = {
                    'title': str(row.get('titolo', '')).strip(),
                    'description': str(row.get('descrizione', '')).strip(),
                    'date': normalize_date(row.get('data', '')),
                    'start_time': str(row.get('ora_inizio', '09.00')).replace(':', '.'),
                    'end_time': str(row.get('ora_fine', '11.00')).replace(':', '.'),
                    'impegno_ore': str(row.get('impegno', '')).strip()
                }
                current_edition['activities'].append(activity)

        # Don't forget the last edition
        if current_edition:
            editions_list.append(current_edition)

        return {
            'editions': editions_list,
            'total_editions': len(editions_list),
            'total_activities': sum(len(e['activities']) for e in editions_list)
        }

    def _detect_original_format(self, df) -> bool:
        """Detect if Excel uses original format with repeating headers"""
        # Look for "Nome del Corso Esistente" appearing multiple times
        first_col = df.iloc[:, 0].astype(str).str.lower()
        header_count = sum(1 for v in first_col if 'nome del corso' in v or 'titolo del attivita' in v)
        return header_count >= 2

    def _parse_original_format(self, excel_file) -> Optional[Dict[str, Any]]:
        """Parse your original format with edition headers followed by activities"""
        df = pd.read_excel(excel_file, sheet_name=0, header=None)

        editions_list = []
        current_edition = None
        reading_activities = False
        activity_header_row = None

        for idx, row in df.iterrows():
            first_cell = str(row.iloc[0]).strip().lower() if pd.notna(row.iloc[0]) else ''

            # Detect edition header row
            if 'nome del corso' in first_cell:
                # Next row will have edition data
                if current_edition:
                    editions_list.append(current_edition)
                current_edition = None
                reading_activities = False
                continue

            # Detect activity header row
            if 'titolo del attivita' in first_cell or 'titolo attivita' in first_cell:
                reading_activities = True
                activity_header_row = idx
                continue

            # Skip empty rows
            if row.isna().all() or first_cell == '' or first_cell == 'nan':
                continue

            # Parse edition data (row after edition header)
            if current_edition is None and not reading_activities:
                current_edition = {
                    'course_name': str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else '',
                    'edition_title': str(row.iloc[1]).strip() if len(row) > 1 and pd.notna(row.iloc[1]) else '',
                    'start_date': normalize_date(row.iloc[2]) if len(row) > 2 else '',
                    'end_date': normalize_date(row.iloc[3]) if len(row) > 3 else '',
                    'location': str(row.iloc[4]).strip() if len(row) > 4 and pd.notna(row.iloc[4]) else '',
                    'supplier': str(row.iloc[5]).strip() if len(row) > 5 and pd.notna(row.iloc[5]) else '',
                    'price': str(row.iloc[6]).strip() if len(row) > 6 and pd.notna(row.iloc[6]) else '',
                    'description': '',
                    'centro_costo': '',
                    'direzione_pagante': '',
                    'finanziata': '',
                    'servizio_pagante': '',
                    'sottotipologia': '',
                    'societa_pagante': '',
                    'activities': []
                }
                continue

            # Parse activity data
            if reading_activities and current_edition:
                activity = {
                    'title': str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else '',
                    'description': str(row.iloc[1]).strip() if len(row) > 1 and pd.notna(row.iloc[1]) else '',
                    'date': normalize_date(row.iloc[2]) if len(row) > 2 else '',
                    'start_time': str(row.iloc[3]).replace(':', '.') if len(row) > 3 and pd.notna(
                        row.iloc[3]) else '09.00',
                    'end_time': str(row.iloc[4]).replace(':', '.') if len(row) > 4 and pd.notna(
                        row.iloc[4]) else '11.00',
                    'impegno_ore': str(row.iloc[6]).strip() if len(row) > 6 and pd.notna(row.iloc[6]) else ''
                }
                if activity['title']:  # Only add if has title
                    current_edition['activities'].append(activity)

        # Don't forget the last edition
        if current_edition:
            editions_list.append(current_edition)

        return {
            'editions': editions_list,
            'total_editions': len(editions_list),
            'total_activities': sum(len(e['activities']) for e in editions_list)
        }

    #---EDITION + ACTIVITY---
    def _parse_two_sheet_edition_excel(self, excel_file) -> Optional[Dict[str, Any]]:
        """Parse two-sheet format (Edizioni + Attivita sheets)"""
        try:
            # Find sheet names (case-insensitive)
            edizioni_sheet = None
            attivita_sheet = None

            for sheet_name in excel_file.sheet_names:
                if 'edizion' in sheet_name.lower():
                    edizioni_sheet = sheet_name
                elif 'attivit' in sheet_name.lower():
                    attivita_sheet = sheet_name

            if not edizioni_sheet or not attivita_sheet:
                st.error("❌ File deve contenere fogli 'Edizioni' e 'Attivita'")
                return None

            # Read both sheets
            df_edizioni = pd.read_excel(excel_file, sheet_name=edizioni_sheet, header=0)
            df_attivita = pd.read_excel(excel_file, sheet_name=attivita_sheet, header=0)

            # Normalize column names
            df_edizioni.columns = df_edizioni.columns.str.strip().str.lower()
            df_attivita.columns = df_attivita.columns.str.strip().str.lower()

            st.info(f"📊 Colonne Edizioni: {', '.join(df_edizioni.columns)}")
            st.info(f"📊 Colonne Attività: {', '.join(df_attivita.columns)}")

            # Column mappings for editions
            edition_mappings = {
                'id': ['id_edizione', 'id', 'edizione_id'],
                'course_name': ['nome_corso', 'nome del corso esistente', 'corso'],
                'title': ['titolo_edizione', 'titolo (optionale)', 'titolo'],
                'start_date': ['data_inizio', 'data inizio edizione', 'data_inizio_edizione'],
                'end_date': ['data_fine', 'data fine edizione', 'data_fine_edizione'],
                'location': ['aula', 'aula principale', 'aula_principale'],
                'supplier': ['fornitore', 'fornitore formazione'],
                'price': ['costo', 'prezzo'],
                'description': ['descrizione', 'desc'],
                # NEW FIELDS:
                'centro_costo': ['centro di costo', 'centro_costo', 'cdc'],
                'direzione_pagante': ['direzione pagante', 'direzione_pagante'],
                'finanziata': ['finanziata'],
                'servizio_pagante': ['servizio pagante', 'servizio_pagante'],
                'sottotipologia': ['sottotipologia'],
                'societa_pagante': [
                    "società pagante",
                    "societa pagante",
                    "societa' pagante",
                    "societa\u2019 pagante",
                    'societa_pagante'
                ],
            }

            # Column mappings for activities
            activity_mappings = {
                'edition_id': ['id_edizione', 'edizione_id', 'id'],
                'title': ['titolo_attivita', 'titolo del attivita', 'titolo'],
                'description': ['descrizione', 'descrizione per elen', 'desc'],
                'date': ['data_attivita', "data attivita'", 'data'],
                'start_time': ['ora_inizio', 'ora inizio'],
                'end_time': ['ora_fine', 'ora fine'],
                'hours': ['impegno in ore', 'impegno_in_ore', 'impegno_ore', 'impegno ore', 'ore', 'impegno']
            }

            # Find actual column names
            def find_column(df, possible_names):
                for name in possible_names:
                    if name in df.columns:
                        return name
                return None

            def safe_val(row, col_key, cols_dict):
                """Safely extract value from row, returning empty string for None/NaN/Ellipsis"""
                col = cols_dict.get(col_key)
                if not col:
                    return ''
                val = row.get(col, '')
                if val is None or val is ...:
                    return ''
                try:
                    if pd.isna(val):
                        return ''
                except:
                    pass
                result = str(val).strip()
                # Remove "nan" strings
                return '' if result.lower() == 'nan' else result

            edition_cols = {k: find_column(df_edizioni, v) for k, v in edition_mappings.items()}
            activity_cols = {k: find_column(df_attivita, v) for k, v in activity_mappings.items()}

            # Parse editions
            editions_list = []
            for idx, row in df_edizioni.iterrows():
                edition_id = str(row[edition_cols['id']]) if edition_cols['id'] else f"E{idx + 1}"

                # Validate required fields
                course_name = row[edition_cols['course_name']] if edition_cols['course_name'] else None
                start_date = row[edition_cols['start_date']] if edition_cols['start_date'] else None
                end_date = row[edition_cols['end_date']] if edition_cols['end_date'] else None

                if pd.isna(course_name) or pd.isna(start_date) or pd.isna(end_date):
                    continue

                # Normalize dates
                start_date_str = normalize_date(start_date)
                end_date_str = normalize_date(end_date)

                if not start_date_str or not end_date_str:
                    st.warning(f"⚠️ Riga {idx + 2}: Formato data non valido")
                    continue

                edition = {
                    'id': edition_id,
                    'course_name': safe_val(row, 'course_name', edition_cols),
                    'edition_title': safe_val(row, 'title', edition_cols),
                    'start_date': start_date_str,
                    'end_date': end_date_str,
                    'location': safe_val(row, 'location', edition_cols),
                    'supplier': safe_val(row, 'supplier', edition_cols),
                    'price': safe_val(row, 'price', edition_cols),
                    'description': safe_val(row, 'description', edition_cols),
                    'centro_costo': safe_val(row, 'centro_costo', edition_cols),
                    'direzione_pagante': safe_val(row, 'direzione_pagante', edition_cols),
                    'finanziata': safe_val(row, 'finanziata', edition_cols),
                    'servizio_pagante': safe_val(row, 'servizio_pagante', edition_cols),
                    'sottotipologia': safe_val(row, 'sottotipologia', edition_cols),
                    'societa_pagante': safe_val(row, 'societa_pagante', edition_cols),
                    'activities': []
                }
                editions_list.append(edition)

            # Parse activities and link to editions
            for idx, row in df_attivita.iterrows():
                edition_id = str(row[activity_cols['edition_id']]) if activity_cols['edition_id'] else None

                if not edition_id:
                    continue

                # Find the edition this activity belongs to
                for edition in editions_list:
                    if edition['id'] == edition_id:
                        activity_date = row[activity_cols['date']] if activity_cols['date'] else None
                        date_str = normalize_date(activity_date) if activity_date else ''

                        # Format times
                        start_time = row[activity_cols['start_time']] if activity_cols['start_time'] else '09.00'
                        end_time = row[activity_cols['end_time']] if activity_cols['end_time'] else '11.00'

                        # Convert time format if needed
                        if isinstance(start_time, (int, float)):
                            hours = int(start_time)
                            minutes = int((start_time - hours) * 60)
                            start_time = f"{hours:02d}.{minutes:02d}"
                        else:
                            start_time = str(start_time).replace(':', '.')

                        if isinstance(end_time, (int, float)):
                            hours = int(end_time)
                            minutes = int((end_time - hours) * 60)
                            end_time = f"{hours:02d}.{minutes:02d}"
                        else:
                            end_time = str(end_time).replace(':', '.')

                        activity = {
                            'title': str(row[activity_cols['title']]).strip() if activity_cols['title'] and pd.notna(
                                row[activity_cols['title']]) else f'Attività {len(edition["activities"]) + 1}',
                            'description': str(row[activity_cols['description']]).strip() if activity_cols[
                                                                                                 'description'] and pd.notna(
                                row[activity_cols['description']]) else '',
                            'date': date_str,
                            'start_time': start_time,
                            'end_time': end_time,
                            'impegno_ore': str(row[activity_cols['hours']]).strip() if activity_cols[
                                                                                           'hours'] and pd.notna(
                                row[activity_cols['hours']]) else ''
                        }
                        edition['activities'].append(activity)
                        break

            if not editions_list:
                st.error("❌ Nessuna edizione valida trovata")
                return None

            st.success(f"✅ Trovate {len(editions_list)} edizioni con le loro attività!")

            try:
                file_name = getattr(excel_file, 'io', None)
                if hasattr(file_name, 'name'):
                    file_name = file_name.name
                else:
                    file_name = 'Excel'
            except Exception:
                file_name = 'Excel'

            return {
                'editions': editions_list,
                'total_editions': len(editions_list),
                'total_activities': sum(len(e['activities']) for e in editions_list),
                'file_name': file_name
            }

        except Exception as e:
            st.error(f"❌ Errore parsing: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
            return None

    def _parse_edition_nlp_input(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Parse free-text NLP input using spaCy + regex.

        HOW IT WORKS (for colleagues):

        1. spaCy tokenizes the text into words and sentences
        2. We use spaCy's Matcher to find field LABELS (like "centro di costo")
           regardless of order, capitalization, or surrounding punctuation
        3. Once we find WHERE a label is, we extract the VALUE after it using
           simple string slicing + regex cleanup
        4. This means "costo 1000 aula Roma" and "aula Roma costo 1000" both work
        """
        import re
        try:
            import spacy
            from spacy.matcher import Matcher
        except ImportError:
            st.warning("⚠️ SpaCy non disponibile. Uso regex di fallback.")
            return self._parse_edition_nlp_regex_fallback(text)

        # =========================================================
        # STEP 1: Load the Italian spaCy model

        try:
            nlp = spacy.load("it_core_news_sm")
        except OSError:
            nlp = spacy.blank("it")

        # =========================================================
        # STEP 2: Process the text
        doc = nlp(text.lower())  # lowercase for case-insensitive matching

        # =========================================================
        # STEP 3: Define field patterns using spaCy Matcher
        matcher = Matcher(nlp.vocab)

        # Define all field label patterns
        # Each tuple: (field_name, list_of_pattern_variants)
        field_patterns = {
            'corso': [
                [{"LOWER": "corso"}],
                [{"LOWER": "nome"}, {"LOWER": "corso"}],
                [{"LOWER": "per"}, {"LOWER": "corso"}],
            ],
            'titolo': [
                [{"LOWER": "titolo"}],
                [{"LOWER": "titolo"}, {"LOWER": "edizione"}],
            ],
            'data_inizio': [
                [{"LOWER": "data"}, {"LOWER": "inizio"}],
                [{"LOWER": "inizio"}],
                [{"LOWER": "dal"}],
            ],
            'data_fine': [
                [{"LOWER": "data"}, {"LOWER": "fine"}],
                [{"LOWER": "fine"}],
                [{"LOWER": "al"}],
            ],
            'aula': [
                [{"LOWER": "aula"}],
                [{"LOWER": "luogo"}],
                [{"LOWER": "sede"}],
            ],
            'fornitore': [
                [{"LOWER": "fornitore"}],
                [{"LOWER": "erogato"}, {"LOWER": "da"}],
            ],
            'costo': [
                [{"LOWER": "costo"}],
                [{"LOWER": "prezzo"}],
                [{"LOWER": "€"}],
            ],
            'descrizione': [
                [{"LOWER": "descrizione"}],
                [{"LOWER": "desc"}],
            ],
            'centro_costo': [
                [{"LOWER": "centro"}, {"LOWER": "di"}, {"LOWER": "costo"}],
                [{"LOWER": "centro"}, {"LOWER": "costo"}],
                [{"LOWER": "cdc"}],
            ],
            'societa_pagante': [
                [{"LOWER": "società"}, {"LOWER": "pagante"}],
                [{"LOWER": "societa"}, {"LOWER": "pagante"}],
                [{"LOWER": "societa'"}, {"LOWER": "pagante"}],  # with apostrophe
                [{"LOWER": "societa"}, {"IS_PUNCT": True, "OP": "?"}, {"LOWER": "pagante"}],
                [{"TEXT": {"REGEX": "socie[tà]+"}, "OP": "?"}, {"LOWER": "pagante"}],
            ],
            'direzione_pagante': [
                [{"LOWER": "direzione"}, {"LOWER": "pagante"}],
            ],
            'servizio_pagante': [
                [{"LOWER": "servizio"}, {"LOWER": "pagante"}],
            ],
            'sottotipologia': [
                [{"LOWER": "sottotipologia"}],
                [{"LOWER": "sotto"}, {"LOWER": "tipologia"}],  # keeps two-word variant
                [{"LOWER": "sottotipo"}],
            ],
            'finanziata': [
                [{"LOWER": "finanziata"}],
                [{"LOWER": "finanziato"}],
            ],
            'attivita_marker': [
                [{"LOWER": "attività"}, {"IS_PUNCT": True, "OP": "?"}],
                [{"LOWER": "attivita"}, {"IS_PUNCT": True, "OP": "?"}],
                [{"LOWER": "attività"}, {"LOWER": ":"}],
            ],
        }

        # Add all patterns to matcher
        for field_name, patterns in field_patterns.items():
            matcher.add(field_name, patterns)

        # =========================================================
        # STEP 4: Run the matcher and collect all matches with positions
        matches = matcher(doc)

        # =========================================================
        # STEP 5: Convert matches to character positions
        field_positions = {}  # {field_name: char_position_after_label}

        for match_id, start, end in matches:
            field_name = nlp.vocab.strings[match_id]
            # doc[end-1].idx = start of last token, doc[end-1].__len__ = length
            last_token = doc[end - 1]
            char_pos_after_label = last_token.idx + len(last_token.text)

            # Keep only the FIRST occurrence of each field
            if field_name not in field_positions:
                field_positions[field_name] = char_pos_after_label

        # =========================================================
        # STEP 6: Sort fields by position in text
        original_text = text

        sorted_fields = sorted(field_positions.items(), key=lambda x: x[1])

        def extract_value_between(start_pos, end_pos=None):
            if end_pos:
                raw = original_text[start_pos:end_pos]
            else:
                raw = original_text[start_pos:]
            raw = re.sub(r'^[\s:,\-–]+', '', raw)
            raw = re.sub(r'[\s,]+$', '', raw)
            if len(raw.strip()) < 2:
                return ''
            return raw.strip()

        # ✅ FUNCTION ENDS HERE — next lines are at method level

        # =========================================================
        # STEP 7: Extract simple fields using spaCy positions
        # =========================================================
        extracted = {}

        simple_fields = ['corso', 'titolo', 'data_inizio', 'data_fine',
                         'aula', 'fornitore', 'costo', 'descrizione']

        simple_positions = [(f, p) for f, p in sorted_fields
                            if f in simple_fields]

        for i, (field_name, start_pos) in enumerate(simple_positions):
            end_pos = None
            if i + 1 < len(simple_positions):
                next_field_name, _ = simple_positions[i + 1]
                next_patterns = field_patterns.get(next_field_name, [])
                for pattern in next_patterns:
                    candidate = ' '.join(
                        p.get('LOWER', '') for p in pattern
                        if p.get('LOWER'))
                    if not candidate:
                        continue
                    idx = original_text.lower().find(
                        candidate.lower(), start_pos)
                    if idx != -1:
                        end_pos = idx
                        break
            value = extract_value_between(start_pos, end_pos)
            extracted[field_name] = value

        # =========================================================
        # OVERRIDE: Extract all simple fields with regex
        # =========================================================
        corso_match = re.search(
            r'(?:per\s+)?corso\s+(.+?)'
            r'(?=\s+titolo\s+|\s+data\s+inizio|\s+data\s+fine'
            r'|\s+aula\s+|\s+fornitore\s+|\s+costo\s+|$)',
            original_text, re.IGNORECASE)
        if corso_match:
            extracted['corso'] = corso_match.group(1).strip()

        titolo_match = re.search(
            r'\btitolo\s+(.+?)'
            r'(?=\s+data\s+inizio|\s+data\s+fine'
            r'|\s+aula\s+|\s+fornitore\s+|\s+costo\s+|$)',
            original_text, re.IGNORECASE)
        if titolo_match:
            extracted['titolo'] = titolo_match.group(1).strip()

        data_inizio_match = re.search(
            r'data\s+inizio\s+(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{4})',
            original_text, re.IGNORECASE)
        if data_inizio_match:
            extracted['data_inizio'] = data_inizio_match.group(1)

        data_fine_match = re.search(
            r'data\s+fine\s+(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{4})',
            original_text, re.IGNORECASE)
        if data_fine_match:
            extracted['data_fine'] = data_fine_match.group(1)

        aula_match = re.search(
            r'\baula\s+(.+?)'
            r'(?=\s+fornitore\s+|\s+costo\s+|\s+con\s+|\s+attività|$)',
            original_text, re.IGNORECASE)
        if aula_match:
            extracted['aula'] = aula_match.group(1).strip()

        fornitore_match = re.search(
            r'\bfornitore\s+(.+?)'
            r'(?=\s+costo\s+|\s+con\s+|\s+aula\s+|\s+attività|$)',
            original_text, re.IGNORECASE)
        if fornitore_match:
            extracted['fornitore'] = fornitore_match.group(1).strip()

        costo_match_val = re.search(
            r'\bcosto\s+(\d+(?:[.,]\d+)?)',
            original_text, re.IGNORECASE)
        if costo_match_val:
            extracted['costo'] = costo_match_val.group(1)

        # =========================================================
        # STEP 8: Parse attributi aggiuntivi with REGEX
        # =========================================================
        aggiuntivi_raw = ''

        aggiuntivi_match = re.search(
            r'\bcon\b(.+?)(?=attività\s*:|attivita\s*:|$)',
            original_text, re.IGNORECASE | re.DOTALL)

        if aggiuntivi_match:
            aggiuntivi_raw = aggiuntivi_match.group(1)
        else:
            costo_fallback = re.search(
                r'costo\s+\d+(.+?)(?=attività\s*:|attivita\s*:|$)',
                original_text, re.IGNORECASE | re.DOTALL)
            if costo_fallback:
                aggiuntivi_raw = costo_fallback.group(1)

        def extract_aggiuntivi_field(pattern, text):
            m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if not m:
                return ''
            return text[m.start(1):m.end(1)].strip().strip(',').strip()

        centro_costo = extract_aggiuntivi_field(
            r'centro\s+di\s+costo\s*[-–:]\s*([^,\n]+?)(?=\s*\w+\s*pagante|,|attività|$)',
            aggiuntivi_raw)

        direzione_pagante = extract_aggiuntivi_field(
            r'direzione\s+pagante\s*[-–:]\s*([^,\n]+?)(?=,|attività|$)',
            aggiuntivi_raw)

        finanziata_raw = extract_aggiuntivi_field(
            r'finanziata\s*[-–:]\s*([^,\n]+?)(?=,|attività|$)',
            aggiuntivi_raw)

        servizio_pagante = extract_aggiuntivi_field(
            r'servizio\s+pagante\s*[-–:]\s*([^,\n]+?)(?=,|attività|$)',
            aggiuntivi_raw)

        sottotipologia = extract_aggiuntivi_field(
            r'sottotipologia\s*[-–:]\s*([^,\n]+?)(?=,|attività|$)',
            aggiuntivi_raw)

        societa_pagante = extract_aggiuntivi_field(
            r"socie(?:t[aà]['\u2019]?)\s*pagante\s*[-–:]\s*([^,\n]+?)(?=\s*attività|\s*attivita|,|$)",
            aggiuntivi_raw)

        if not societa_pagante:
            societa_fallback = re.search(
                r"socie(?:t[aà]['\u2019]?)\s*pagante\s*[-–:]\s*([^,\n]+?)(?=\s*attività|\s*attivita|,|$)",
                original_text, re.IGNORECASE)
            if societa_fallback:
                societa_pagante = original_text[
                                  societa_fallback.start(1):societa_fallback.end(1)
                                  ].strip().strip(',').strip()
        if finanziata_raw.lower() in ['si', 'sì', 'yes', 's']:
            finanziata_val = 'Sì'
        elif finanziata_raw.lower() in ['no', 'n']:
            finanziata_val = 'No'
        else:
            finanziata_val = finanziata_raw.strip()

        # =========================================================
        # STEP 9: Parse activities
        # =========================================================
        activities = []
        attivita_match = re.search(
            r'attività\s*[:\-]\s*(.+?)$',
            original_text, re.IGNORECASE | re.DOTALL)

        if attivita_match:
            activities_text = attivita_match.group(1)
            activity_pattern = re.compile(
                r'([^,]+?)'  # title
                r'(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{4})'  # date
                r'[^0-9]*ore\s*'  # 'ore' keyword
                r'(\d{1,2}[.:]\d{2})'  # start time
                r'\s*[-–]\s*'  # separator
                r'(\d{1,2}[.:]\d{2})'  # end time
                r'(?:[^,\d]*?(\d+(?:[.,]\d+)?)\s*ore)?',  # ★ optional impegno
                re.IGNORECASE)
            for match in activity_pattern.finditer(activities_text):
                title = match.group(1).strip().strip(',').strip()
                date_str = normalize_date(match.group(2))
                start_time = match.group(3).replace(':', '.')
                end_time = match.group(4).replace(':', '.')
                impegno_val = match.group(5) if match.group(5) else ''  # ★ NEW
                if title and date_str:
                    activities.append({
                        'title': title,
                        'description': '',
                        'date': date_str,
                        'start_time': start_time,
                        'end_time': end_time,
                        'impegno_ore': impegno_val  # ★ was ''
                    })
        # =========================================================
        # STEP 10: Clean and build final result
        # =========================================================
        def clean(val):
            if not val:
                return ''
            val = re.sub(r'\battività\b.*', '', val,
                         flags=re.IGNORECASE).strip()
            return val.strip(' ,;:-–')

        course_name = clean(extracted.get('corso', ''))
        start_date = clean(extracted.get('data_inizio', ''))
        end_date = clean(extracted.get('data_fine', ''))

        if not course_name:
            st.error("❌ Nome corso non trovato. Scrivi 'corso [nome]'.")
            return None

        start_date_str = normalize_date(start_date) if start_date else ''
        end_date_str = normalize_date(end_date) if end_date else ''

        if not start_date_str or not end_date_str:
            st.error("❌ Date non trovate. Usa formato GG/MM/AAAA.")
            return None

        return {
            'course_name': course_name,
            'edition_title': clean(extracted.get('titolo', '')),
            'start_date': start_date_str,
            'end_date': end_date_str,
            'location': clean(extracted.get('aula', '')),
            'supplier': clean(extracted.get('fornitore', '')),
            'price': clean(extracted.get('costo', '')),
            'description': clean(extracted.get('descrizione', '')),
            'centro_costo': centro_costo,
            'societa_pagante': societa_pagante,
            'direzione_pagante': direzione_pagante,
            'servizio_pagante': servizio_pagante,
            'sottotipologia': sottotipologia,
            'finanziata': finanziata_val,
            'activities': activities,
        }


    def _parse_edition_nlp_input_regex(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Parse natural language input to extract edition and activities with REGEX.

        Example input:
        "Crea edizione per corso Analisi dei dati titolo Analisi dei dati - Base
         data inizio 12/02/2026 data fine 20/02/2026
         aula Aula de carli fornitore AEIT costo 1000 con CENTRO DI COSTO - TP00001,
         DIREZIONE PAGANTE - Direzione Operativa - VAM,	FINANZIATA - no,
         SERVIZIO PAGANTE - Impianti di Cogenerazione UT Verona,
         SOTTOTIPOLOGIA-	Office Automation & Produttività,
         SOCIETA' PAGANTE - Magis Calore S.r.l.
         attività: primo giorno 12/02/2026 ore 09.00-11.00,
         secondo giorno 13/02/2026 ore 10.00-12.00"
        """
        import re

        parsed = {
            'course_name': '',
            'edition_title': '',
            'start_date': '',
            'end_date': '',
            'location': '',
            'supplier': '',
            'price': '',
            'description': '',
            'activities': [],
            # NEW:
            'centro_costo': '',
            'direzione_pagante': '',
            'finanziata': '',
            'servizio_pagante': '',
            'sottotipologia': '',
            'societa_pagante': '',
        }

        text_lower = text.lower()
        original_text = text

        # Extract course name
        course_patterns = [
            r'(?:corso|per corso|del corso)\s+["\']?([^"\']+?)["\']?\s+(?:titolo|data|edizione)',
            r'corso\s+([A-Za-z0-9\s]+?)(?:\s+titolo|\s+data|\s+edizione|,|$)',
        ]
        for pattern in course_patterns:
            match = re.search(pattern, text_lower)
            if match:
                parsed['course_name'] = match.group(1).strip().title()
                break

        # Extract edition title
        title_patterns = [
            r'titolo\s+["\']?([^"\']+?)["\']?\s+(?:data|aula|fornitore|attività)',
            r'titolo\s+([^,]+?)(?:,|\s+data)',
        ]
        for pattern in title_patterns:
            match = re.search(pattern, text_lower)
            if match:
                parsed['edition_title'] = match.group(1).strip().title()
                break

        # Extract dates
        date_pattern = r'(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})'
        dates = re.findall(date_pattern, text)

        # Try to identify start and end dates
        start_match = re.search(r'(?:data\s+)?inizio\s+(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})', text_lower)
        end_match = re.search(r'(?:data\s+)?fine\s+(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})', text_lower)

        if start_match:
            parsed['start_date'] = normalize_date(start_match.group(1)) or ''
        elif dates:
            parsed['start_date'] = normalize_date(dates[0]) or ''

        if end_match:
            parsed['end_date'] = normalize_date(end_match.group(1)) or ''
        elif len(dates) > 1:
            parsed['end_date'] = normalize_date(dates[1]) or ''

        # Extract location
        location_match = re.search(r'aula\s+([^,]+?)(?:,|\s+fornitore|\s+costo|\s+attività|$)', text_lower)
        if location_match:
            parsed['location'] = location_match.group(1).strip().title()

        # Extract supplier
        supplier_match = re.search(r'fornitore\s+([^,]+?)(?:,|\s+costo|\s+aula|\s+attività|$)', text_lower)
        if supplier_match:
            parsed['supplier'] = supplier_match.group(1).strip().title()

        # Extract price
        price_match = re.search(r'(?:costo|prezzo)\s+(\d+)', text_lower)
        if price_match:
            parsed['price'] = price_match.group(1)

        # --- Centro di Costo ---
        centro_costo_match = re.search(
            r'centro\s+di\s+costo\s*[-–:]\s*([^,]+?)(?:,|\s+direzione|\s+finanziata|$)',
            text_lower)
        if centro_costo_match:
            start = centro_costo_match.start(1)
            end = centro_costo_match.end(1)
            parsed['centro_costo'] = text[start:end].strip()

        # --- Direzione Pagante ---
        direzione_match = re.search(
            r'direzione\s+pagante\s*[-–:]\s*([^,]+?)(?:,|\s+finanziata|\s+servizio|$)',
            text_lower)
        if direzione_match:
            start = direzione_match.start(1)
            end = direzione_match.end(1)
            parsed['direzione_pagante'] = text[start:end].strip()

        # --- Finanziata ---
        finanziata_match = re.search(
            r'finanziata\s*[-–:]\s*(s[iì]|no)',
            text_lower)
        if finanziata_match:
            val = finanziata_match.group(1).strip().lower()
            parsed['finanziata'] = 'Sì' if val in ['si', 'sì'] else 'No'

        # --- Servizio Pagante ---
        servizio_match = re.search(
            r'servizio\s+pagante\s*[-–:]\s*([^,]+?)(?:,|\s+sottotipologia|\s+societ|$)',
            text_lower)
        if servizio_match:
            start = servizio_match.start(1)
            end = servizio_match.end(1)
            parsed['servizio_pagante'] = text[start:end].strip()

        # --- Sottotipologia ---
        sottotipologia_match = re.search(
            r'sottotipologia\s*[-–:]\s*([^,]+?)(?:,|\s+societ|$)',
            text_lower)
        if sottotipologia_match:
            start = sottotipologia_match.start(1)
            end = sottotipologia_match.end(1)
            parsed['sottotipologia'] = text[start:end].strip()

        # --- Società Pagante ---
        societa_match = re.search(
            r"societ[àa]['\u2019]?\s+pagante\s*[-–:]\s*([^,]+?)(?:,|\s+attivit|$)",
            text_lower)
        if societa_match:
            start = societa_match.start(1)
            end = societa_match.end(1)
            parsed['societa_pagante'] = text[start:end].strip()
        # Extract activities
        # Pattern: "primo giorno 12/02/2026 ore 09.00-11.00" or similar
        activity_section = re.search(r'attività[:\s]+(.+)', text_lower, re.DOTALL)
        if activity_section:
            activity_text = activity_section.group(1)

            # Find individual activities
            activity_patterns = [
                # Pattern A: "primo giorno 12/02/2026 ore 09.00-11.00 [impegno N ore]"
                r'(\w+\s+giorno)\s+(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})'
                r'\s+(?:ore\s+)?(\d{1,2}[.:]\d{2})\s*[-–]\s*(\d{1,2}[.:]\d{2})'
                r'(?:[^,\d]*?(\d+(?:[.,]\d+)?)\s*ore)?',  # ★
                # Pattern B: "giorno 1 12/02/2026 ore 09.00-11.00 [impegno N ore]"
                r'(giorno\s+\d+|day\s+\d+)\s+(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})'
                r'\s+(?:ore\s+)?(\d{1,2}[.:]\d{2})\s*[-–]\s*(\d{1,2}[.:]\d{2})'
                r'(?:[^,\d]*?(\d+(?:[.,]\d+)?)\s*ore)?',  # ★
            ]

            for pattern in activity_patterns:
                matches = re.findall(pattern, activity_text)
                for match in matches:
                    # ★ Each match now has 5 elements instead of 4
                    title, date_str, start_time, end_time, impegno_val = match
                    parsed['activities'].append({
                        'title': title.strip().title(),
                        'description': '',
                        'date': normalize_date(date_str) or '',
                        'start_time': start_time.replace(':', '.'),
                        'end_time': end_time.replace(':', '.'),
                        'impegno_ore': impegno_val  # ★ was ''
                    })
        # If no activities found, try to detect number of days
        if not parsed['activities']:
            days_match = re.search(r'(\d+)\s+(?:giorni|days|attività)', text_lower)
            if days_match and parsed['start_date']:
                num_days = int(days_match.group(1))
                start_date_obj = datetime.strptime(parsed['start_date'], "%d/%m/%Y")

                for i in range(num_days):
                    activity_date = start_date_obj + timedelta(days=i)
                    parsed['activities'].append({
                        'title': f'Giorno {i + 1}',
                        'description': '',
                        'date': activity_date.strftime("%d/%m/%Y"),
                        'start_time': '09.00',
                        'end_time': '11.00',
                        'impegno_ore': ''
                    })

        return parsed

    def _preserve_activity_data(self, num_activities):
        """Preserve current activity data before form submission"""
        # CRITICAL: Also preserve the count itself
        st.session_state.preserved_activity_data["_count"] = num_activities

        for i in range(num_activities):
            key_prefix = f"activity_{i}"
            st.session_state.preserved_activity_data[f"{key_prefix}_title"] = \
                st.session_state.get(f"activity_title_{i}", "")
            st.session_state.preserved_activity_data[f"{key_prefix}_desc"] = \
                st.session_state.get(f"activity_desc_{i}", "")
            st.session_state.preserved_activity_data[f"{key_prefix}_date"] = \
                st.session_state.get(f"activity_date_{i}", "")
            st.session_state.preserved_activity_data[f"{key_prefix}_start"] = \
                st.session_state.get(f"activity_start_time_{i}", "09.00")
            st.session_state.preserved_activity_data[f"{key_prefix}_end"] = \
                st.session_state.get(f"activity_end_time_{i}", "11.00")
            st.session_state.preserved_activity_data[f"{key_prefix}_ore"] = \
                st.session_state.get(f"impegno_previsto_in_ore_{i}", "")

    def _restore_activity_data(self, num_activities):
        """Restore preserved activity data to form fields"""
        # CRITICAL: Restore the count to show correct number of fields
        if "_count" in st.session_state.preserved_activity_data:
            restored_count = st.session_state.preserved_activity_data["_count"]
            # Update num_activities to match what was preserved
            if st.session_state.num_activities != restored_count:
                st.session_state.num_activities = restored_count

        # Use the restored count for the loop
        count_to_restore = st.session_state.num_activities
        for i in range(count_to_restore):
            key_prefix = f"activity_{i}"
            if f"{key_prefix}_title" in st.session_state.preserved_activity_data:
                st.session_state[f"activity_title_{i}"] = \
                    st.session_state.preserved_activity_data[f"{key_prefix}_title"]
                st.session_state[f"activity_desc_{i}"] = \
                    st.session_state.preserved_activity_data[f"{key_prefix}_desc"]
                st.session_state[f"activity_date_{i}"] = \
                    st.session_state.preserved_activity_data[f"{key_prefix}_date"]
                st.session_state[f"activity_start_time_{i}"] = \
                    st.session_state.preserved_activity_data[f"{key_prefix}_start"]
                st.session_state[f"activity_end_time_{i}"] = \
                    st.session_state.preserved_activity_data[f"{key_prefix}_end"]
                st.session_state[f"impegno_previsto_in_ore_{i}"] = \
                    st.session_state.preserved_activity_data[f"{key_prefix}_ore"]

    def _render_edition_form(self, is_disabled=False):
        """
        Enhanced edition form with three input methods:
        1. Structured input (original form)
        2. Excel file upload
        3. Natural language processing (NLP)
        """

        # === CHECK FOR EDIT MODE FIRST ===
        if st.session_state.get('edition_edit_mode', False) and st.session_state.get('edition_to_edit'):
            self._render_editable_edition_form()
            return

        # === CHECK FOR SUMMARY/PREVIEW MODE ===
        if st.session_state.get('edition_show_summary', False) and st.session_state.get('edition_parsed_data'):
            self._render_edition_preview(st.session_state.edition_parsed_data)
            return

        # === INPUT METHOD SELECTION ===
        st.subheader("Scegli il Metodo di Inserimento")

        input_method = st.radio(
            "Come vuoi inserire i dati dell'edizione?",
            options=["structured", "excel", "nlp"],
            format_func=lambda x: {
                "structured": "📝 Input Strutturato (Form)",
                "excel": "📊 Caricamento File Excel",
                "nlp": "💬 Compilazione con AI"
            }[x],
            key="edition_input_method",
            horizontal=True
        )

        st.divider()

        # === RENDER BASED ON SELECTED METHOD ===
        if input_method == "structured":
            self._render_edition_structured_form(is_disabled)
        elif input_method == "excel":
            self._render_edition_excel_ui(is_disabled)
        elif input_method == "nlp":
            self._render_edition_nlp_ui(is_disabled)

    def _render_edition_structured_form(self, is_disabled):
        """Original structured form for edition + activities"""

        # # Restore data BEFORE rendering the form
        # if st.session_state.preserved_activity_data:
        #     self._restore_activity_data(st.session_state.num_activities)

        num_activities = st.number_input(
            "Quanti giorni di attività?",
            min_value=1,
            max_value=30,
            key="num_activities"
        )

        with st.form(key='edition_activity_form'):
            st.subheader("Dettagli Edizione")
            st.text_input("Nome del Corso Esistente", placeholder="Nome corso esistente",
                          key="edition_course_name_key")
            st.text_input("Titolo Edizione ",
                          placeholder="Lascia vuoto per usare il nome predefinito...",
                          key="edition_title_key")
            st.text_input("Data Inizio Edizione (GG/MM/AAAA)", key="edition_start_date_str_key")
            st.text_input("Data Fine Edizione (GG/MM/AAAA)", key="edition_end_date_str_key")
            st.text_area("Descrizione Edizione ", placeholder="Descrizione...",
                         key="edition_description_key")
            st.text_area("Aula Principale ",
                         key="edition_location_key")
            st.text_area("Nome Fornitore Formazione ",
                         key="edition_supplier_key")
            st.text_input("Prezzo Edizione (€) ", placeholder="Esempio: 1000",
                          key="edition_price_key")
            st.divider()
            st.subheader("Attributi Aggiuntivi")
            st.caption("Campi opzionali — compilare se necessario")

            st.text_input("Centro di Costo",
                          placeholder="Es: TP00001",
                          key="edition_centro_costo_key")
            st.text_input("Società Pagante",
                          placeholder="Es: Magis Calore S.r.l.",
                          key="edition_societa_pagante_key")
            st.text_input("Direzione Pagante",
                          placeholder="Es: Direzione Operativa - VAM",
                          key="edition_direzione_pagante_key")
            st.text_input("Servizio Pagante",
                          placeholder="Es: Impianti di Cogenerazione",
                          key="edition_servizio_pagante_key")
            st.text_input("Sottotipologia",
                          placeholder="Es: Office Automation & Produttività",
                          key="edition_sottotipologia_key")

            finanziata_options = ["", "Sì", "No"]
            st.selectbox("Finanziata",
                         options=finanziata_options,
                         key="edition_finanziata_key")

            st.divider()
            st.subheader("Dettagli Attività")

            # ✅ Add note about mandatory fields
            st.caption("* I campi Titolo e Data sono obbligatori per ogni attività. La Descrizione è facoltativa.")

            for i in range(num_activities):
                st.markdown(f"**Giorno {i + 1}**")
                cols = st.columns([2, 1, 1, 1])
                with cols[0]:
                    st.text_input(f"Titolo Attività", key=f"activity_title_{i}")
                with cols[1]:
                    st.text_input(f"Data (GG/MM/AAAA)", key=f"activity_date_{i}",
                                  placeholder=f"Data giorno {i + 1}")
                with cols[2]:
                    st.text_input(f"Ora Inizio (HH.MM)", key=f"activity_start_time_{i}")
                with cols[3]:
                    st.text_input(f"Ora Fine (HH.MM)", key=f"activity_end_time_{i}")

                st.text_area(f"Descrizione Attività (facoltativa)", key=f"activity_desc_{i}", height=100)
                st.text_input(f"Impegno previsto in ore", key=f"impegno_previsto_in_ore_{i}")
                st.markdown("---")

            col1, col2 = st.columns([3, 1])
            with col1:
                submitted = st.form_submit_button("Crea Edizione e Attività", type="primary",
                                                  disabled=is_disabled, width='stretch')
            with col2:
                st.form_submit_button("Pulisci 🧹", width='stretch',
                                      on_click=self._clear_edition_activity_form_callback)

        if submitted:
            self._process_structured_edition_submission(num_activities)

    def _render_edition_nlp_ui(self, is_disabled):
        """UI for natural language input for edition + activities"""

        st.info("""
        **Scrivi una frase che descriva l'edizione e le attività**, ad esempio:

        "Crea edizione per corso Analisi dei dati titolo Analisi dei dati - Base
         data inizio 12/02/2026 data fine 20/02/2026
         aula Aula de carli fornitore AEIT costo 1000 con CENTRO DI COSTO - TP00001,
         DIREZIONE PAGANTE - Direzione Operativa - VAM,	FINANZIATA - no,
         SERVIZIO PAGANTE - Impianti di Cogenerazione UT Verona,
         SOTTOTIPOLOGIA-	Office Automation & Produttività,
         SOCIETA' PAGANTE - Magis Calore S.r.l.
         attività: primo giorno 12/02/2026 ore 09.00-11.00,
         secondo giorno 13/02/2026 ore 10.00-12.00"
        """, icon="💡")

        # ✅ Initialize the key-based state if not exists
        if "edition_nlp_text_area" not in st.session_state:
            st.session_state.edition_nlp_text_area = ""

        # ✅ Use key parameter - Streamlit manages state at this key
        nlp_text = st.text_area(
            "Descrivi l'edizione in linguaggio naturale:",
            height=200,
            placeholder="Crea edizione per corso [nome corso] data inizio [data] data fine [data]...",
            help="Scrivi una frase completa con i dettagli dell'edizione e delle attività",
            key="edition_nlp_text_area"  # ✅ USE KEY - Streamlit stores value here
        )

        # Show character count
        text_length = len(nlp_text.strip()) if nlp_text else 0
        if text_length > 0:
            st.caption(f"✏️ {text_length} caratteri inseriti")
        else:
            st.warning("Inserisci del testo per abilitare l'analisi", icon="⚠️")

        col1, col2 = st.columns([1, 1])

        with col1:
            if st.button("🤖 Analizza Testo (NLP)", type="primary", width='stretch',
                         key="analyze_edition_nlp_btn"):
                if not nlp_text or not nlp_text.strip():
                    st.error("⚠️ Per favore, inserisci del testo prima di analizzare.")
                    st.stop()

                if text_length < 30:
                    st.error("⚠️ Il testo è troppo corto. Scrivi una frase più completa.")
                    st.stop()

                # Clear old data
                st.session_state.edition_parsed_data = None
                st.session_state.edition_show_summary = False

                with st.spinner("🤖 Analisi del testo in corso..."):
                    parsed_data = self._parse_edition_nlp_input(nlp_text)

                if parsed_data and parsed_data.get('course_name'):
                    st.session_state.edition_parsed_data = parsed_data
                    st.session_state.edition_show_summary = True
                    st.rerun()
                else:
                    st.error("""
                    ❌ Impossibile estrarre le informazioni necessarie.

                    Assicurati di includere:
                    - **Nome del corso** esistente (es: "corso Data Science01")
                    - **Data inizio** edizione (es: "data inizio 12/02/2026")
                    - **Data fine** edizione (es: "data fine 20/02/2026")
                    - **Attività** (es: "attività: primo giorno 12/02/2026 ore 09.00-11.00")
                    """)

        with col2:
            if st.button("🧹 Cancella Testo", width='stretch',
                         on_click=self._clear_edition_nlp_callback,
                         key="clear_edition_nlp_btn"):
                pass  # Callback handles the clearing

    def _process_structured_edition_submission(self, num_activities):
        """Process the structured form submission with specific error messages"""

        # ❌ REMOVE THIS LINE - Don't preserve data before validation
        # self._preserve_activity_data(num_activities)

        # Get edition details
        course_name = st.session_state.edition_course_name_key
        edition_title = st.session_state.edition_title_key
        start_date_str = st.session_state.edition_start_date_str_key
        end_date_str = st.session_state.edition_end_date_str_key
        description = st.session_state.edition_description_key
        location = st.session_state.edition_location_key
        supplier = st.session_state.edition_supplier_key
        price = st.session_state.edition_price_key

        # ✅ SPECIFIC ERROR MESSAGES FOR EDITION FIELDS
        has_errors = False

        if not course_name.strip():
            st.error("❌ **Nome del Corso** è obbligatorio.")
            has_errors = True

        if not start_date_str.strip():
            st.error("❌ **Data Inizio Edizione** è obbligatoria.")
            has_errors = True

        if not end_date_str.strip():
            st.error("❌ **Data Fine Edizione** è obbligatoria.")
            has_errors = True

        if has_errors:
            st.stop()

        # ✅ VALIDATE DATE FORMATS WITH SPECIFIC ERRORS
        try:
            edition_start = datetime.strptime(start_date_str, "%d/%m/%Y").date()
        except ValueError:
            st.error(
                f"❌ **Data Inizio Edizione** formato non valido: '{start_date_str}'. Usa GG/MM/AAAA (es: 01/03/2026)")
            st.stop()

        try:
            edition_end = datetime.strptime(end_date_str, "%d/%m/%Y").date()
        except ValueError:
            st.error(f"❌ **Data Fine Edizione** formato non valido: '{end_date_str}'. Usa GG/MM/AAAA (es: 15/03/2026)")
            st.stop()

        if edition_end < edition_start:
            st.error("❌ La **Data Fine Edizione** non può essere precedente alla **Data Inizio Edizione**.")
            st.stop()

        # ✅ VALIDATE EACH ACTIVITY WITH SPECIFIC ERRORS
        activities_list = []
        all_valid = True

        for i in range(num_activities):
            activity_errors = []

            title = st.session_state.get(f"activity_title_{i}", "").strip()
            act_desc = st.session_state.get(f"activity_desc_{i}", "").strip()
            act_date_str = st.session_state.get(f"activity_date_{i}", "").strip()
            start_time = st.session_state.get(f"activity_start_time_{i}", "09.00").strip()
            end_time = st.session_state.get(f"activity_end_time_{i}", "11.00").strip()
            impegno_previsto_in_ore = st.session_state.get(f"impegno_previsto_in_ore_{i}", "").strip()

            # Check each field specifically
            if not title:
                activity_errors.append("**Titolo** è obbligatorio")



            if not act_date_str:
                activity_errors.append("**Data** è obbligatoria")

            # Show activity-specific errors
            if activity_errors:
                error_list = ", ".join(activity_errors)
                st.error(f"❌ **Attività Giorno {i + 1}**: {error_list}")
                all_valid = False
                continue  # Check other activities too

            # Validate date format
            try:
                act_date = datetime.strptime(act_date_str, "%d/%m/%Y").date()
            except ValueError:
                st.error(f"❌ **Attività Giorno {i + 1}**: Formato data non valido '{act_date_str}'. Usa GG/MM/AAAA")
                all_valid = False
                continue

            # ── AUTO-FIX time format (Oracle requires HH.MM, e.g. 15.45) ──
            from model import normalize_time

            start_time = normalize_time(start_time) if start_time else "09.00"
            if start_time is None:
                st.error(
                    f"❌ **Attività Giorno {i + 1}**: Ora inizio non "
                    f"riconosciuta '{st.session_state.get(f'activity_start_time_{i}')}'. "
                    f"Usa HH.MM (es: 09.00)")
                all_valid = False
                continue

            end_time = normalize_time(end_time) if end_time else "11.00"
            if end_time is None:
                st.error(
                    f"❌ **Attività Giorno {i + 1}**: Ora fine non "
                    f"riconosciuta '{st.session_state.get(f'activity_end_time_{i}')}'. "
                    f"Usa HH.MM (es: 11.00)")
                all_valid = False
                continue

            # Validate activity date is within edition range
            if act_date < edition_start or act_date > edition_end:
                st.error(
                    f"❌ **Attività Giorno {i + 1}**: La data ({act_date_str}) deve essere compresa tra "
                    f"l'inizio ({start_date_str}) e la fine ({end_date_str}) dell'edizione."
                )
                all_valid = False
                continue

            # Activity is valid - add to list
            activities_list.append({
                "title": title,
                "description": act_desc,
                "date": act_date,
                "start_time": start_time,
                "end_time": end_time,
                "impegno_previsto_in_ore": impegno_previsto_in_ore
            })

        # Stop if any activity had errors
        if not all_valid:
            st.info("💡 Correggi gli errori sopra e riprova.")
            st.stop()

        # ✅ ALL VALIDATION PASSED - Now start automation
        st.session_state.edition_details = {
            'course_name': course_name,
            'edition_title': edition_title,
            'edition_start_date': edition_start,
            'edition_end_date': edition_end,
            'location': location,
            'supplier': supplier,
            'price': price,
            'description': description,
            'activities': activities_list,
            # NEW FIELDS:
            'centro_costo': st.session_state.get('edition_centro_costo_key', ''),
            'direzione_pagante': st.session_state.get('edition_direzione_pagante_key', ''),
            'finanziata': st.session_state.get('edition_finanziata_key', ''),
            'servizio_pagante': st.session_state.get('edition_servizio_pagante_key', ''),
            'sottotipologia': st.session_state.get('edition_sottotipologia_key', ''),
            'societa_pagante': st.session_state.get('edition_societa_pagante_key', ''),
        }
        st.session_state.app_state = "RUNNING_EDITION"
        st.session_state.edition_message = ""
        st.rerun()

    def _render_edition_excel_ui(self, is_disabled):
        """UI for Excel file upload for edition + activities"""

        #st.info("""
        # **Formato Excel Supportato:**
        #
        # **Opzione 1 - Due fogli separati:**
        # - Foglio "Edizioni": ID_EDIZIONE, NOME_CORSO, TITOLO, DATA_INIZIO, DATA_FINE, AULA, FORNITORE, COSTO
        # - Foglio "Attivita": ID_EDIZIONE, TITOLO, DESCRIZIONE, DATA, ORA_INIZIO, ORA_FINE, IMPEGNO_ORE
        #
        # **Opzione 2 - Foglio singolo con marcatori:**
        # - Colonna TIPO: "EDIZIONE" o "ATTIVITA" per ogni riga
        #
        # **Opzione 3 - Formato originale:**
        # - Intestazione edizione → dati edizione → intestazione attività → dati attività
        # """, icon="ℹ️")

        uploaded_file = st.file_uploader(
            "Carica File Excel (.xlsx, .xls)",
            type=['xlsx', 'xls'],
            help="File con edizione e attività",
            key="edition_excel_uploader"
        )

        if uploaded_file is not None:
            col1, col2 = st.columns([1, 1])

            with col1:
                if st.button("📊 Analizza File Excel", type="primary", width='stretch',
                             key="analyze_edition_excel_btn"):
                    with st.spinner("🔍 Lettura file Excel..."):
                        parsed_data = self._parse_edition_excel_file(uploaded_file)

                    if parsed_data:
                        st.session_state.edition_parsed_data = parsed_data
                        st.session_state.edition_show_summary = True
                        st.rerun()
                    else:
                        st.error("❌ Impossibile estrarre i dati dal file. Verifica il formato.")

            with col2:
                if st.button("🧹 Cancella File", width='stretch', key="clear_edition_excel_btn"):
                    st.session_state.edition_parsed_data = None
                    st.session_state.edition_show_summary = False
                    st.rerun()

    def _render_edition_preview(self, edition_data: Dict[str, Any]):
        """Display parsed edition and activities for confirmation"""

        # Check if it's a list of editions (from Excel) or single edition (from NLP)
        if 'editions' in edition_data:
            # Multiple editions from Excel
            self._render_multiple_editions_preview(edition_data)
        else:
            # Single edition (from NLP or single Excel row)
            self._render_single_edition_preview(edition_data)

    def _render_single_edition_preview(self, edition_data: Dict[str, Any]):
        """Preview for a single edition with activities — 3-table layout"""

        st.success("✅ Dati estratti con successo!")
        st.subheader("📋 Anteprima Edizione + Attività")

        # === TABLE 1: Dettagli Edizione ===
        st.markdown("### 📚 Dettagli Edizione")
        dettagli = {
            'Campo': ['Corso', 'Titolo Edizione', 'Data Inizio', 'Data Fine',
                      'Aula', 'Fornitore', 'Costo', 'Descrizione'],
            'Valore': [
                edition_data.get('course_name', '-'),
                edition_data.get('edition_title', '') or 'Default (nome corso + data)',
                edition_data.get('start_date', '-'),
                edition_data.get('end_date', '-'),
                edition_data.get('location', '') or 'Non specificata',
                edition_data.get('supplier', '') or 'Non specificato',
                f"€{edition_data.get('price', '0') or '0'}",
                edition_data.get('description', '') or '-',
            ]
        }
        st.dataframe(pd.DataFrame(dettagli), hide_index=True, width='stretch')

        # === TABLE 2: Attributi Aggiuntivi (only if any filled) ===
        aggiuntivi_values = {
            'Campo': ['Centro di Costo', 'Società Pagante', 'Direzione Pagante',
                      'Servizio Pagante', 'Sottotipologia', 'Finanziata'],
            'Valore': [
                edition_data.get('centro_costo', '') or '-',
                edition_data.get('societa_pagante', '') or '-',
                edition_data.get('direzione_pagante', '') or '-',
                edition_data.get('servizio_pagante', '') or '-',
                edition_data.get('sottotipologia', '') or '-',
                edition_data.get('finanziata', '') or '-',
            ]
        }
        st.markdown("### 🗂️ Attributi Aggiuntivi")
        st.dataframe(pd.DataFrame(aggiuntivi_values), hide_index=True, width='stretch')

        # === TABLE 3: Attività ===
        st.markdown("### 📝 Attività")
        activities = edition_data.get('activities', [])
        if activities:
            activities_preview = []
            for idx, act in enumerate(activities):
                activities_preview.append({
                    '#': idx + 1,
                    'Titolo': act.get('title', ''),
                    'Data': act.get('date', ''),
                    'Ora Inizio': act.get('start_time', ''),
                    'Ora Fine': act.get('end_time', ''),
                    'Impegno (ore)': act.get('impegno_ore', '') or act.get('impegno_previsto_in_ore', '') or '-'
                })
            st.dataframe(pd.DataFrame(activities_preview), hide_index=True, width='stretch')
        else:
            st.warning("⚠️ Nessuna attività trovata.")

        st.divider()

        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            if st.button("✅ Conferma e Crea Edizione", type="primary", width='stretch',
                         key="edition_preview_confirm_btn"):
                self._start_edition_creation(edition_data)
        with col2:
            if st.button("✏️ Modifica", width='stretch', key="edition_preview_edit_btn"):
                st.session_state.edition_edit_mode = True
                st.session_state.edition_to_edit = edition_data.copy()
                st.session_state.edition_show_summary = False
                st.rerun()
        with col3:
            if st.button("❌ Annulla", width='stretch', key="edition_preview_cancel_btn"):
                st.session_state.edition_parsed_data = None
                st.session_state.edition_show_summary = False
                st.session_state.edition_input_method = "structured"
                st.rerun()

    def _render_multiple_editions_preview(self, batch_data: Dict[str, Any]):
        """
        Preview multiple editions from Excel with batch creation support.
        3-table layout inside each edition expander:
        - Table 1: Dettagli Edizione
        - Table 2: Attributi Aggiuntivi
        - Table 3: Attività
        """
        editions = batch_data.get('editions', [])
        total_editions = len(editions)
        total_activities = sum(len(e.get('activities', [])) for e in editions)

        st.subheader("📁 Anteprima Edizioni")
        st.info(f"📊 Trovate **{total_editions} edizioni** con **{total_activities} attività** totali.")

        for idx, edition in enumerate(editions):
            activities = edition.get('activities', [])
            has_errors = not edition.get('course_name') or not edition.get('start_date')

            # Expander title with quick summary and warning if data looks incomplete
            expander_label = (
                f"{'⚠️' if has_errors else '📚'} Edizione {idx + 1}: "
                f"{edition.get('course_name', 'N/A')} — "
                f"{edition.get('start_date', '?')} → {edition.get('end_date', '?')} "
                f"({len(activities)} attività)"
            )

            with st.expander(expander_label, expanded=(idx == 0)):

                # === TABLE 1: Dettagli Edizione ===
                st.markdown("**📚 Dettagli Edizione**")
                dettagli = pd.DataFrame({
                    'Campo': [
                        'Corso', 'Titolo Edizione', 'Data Inizio', 'Data Fine',
                        'Aula', 'Fornitore', 'Costo'
                    ],
                    'Valore': [
                        edition.get('course_name', '') or '—',
                        edition.get('edition_title', '') or '—',
                        edition.get('start_date', '') or '—',
                        edition.get('end_date', '') or '—',
                        edition.get('location', '') or '—',
                        edition.get('supplier', '') or '—',
                        f"€{edition.get('price', '')}" if edition.get('price') else '—',
                    ]
                })
                st.dataframe(dettagli, hide_index=True, use_container_width=True)

                # === TABLE 2: Attributi Aggiuntivi ===
                st.markdown("**🗂️ Attributi Aggiuntivi**")
                aggiuntivi = pd.DataFrame({
                    'Campo': [
                        'Centro di Costo', 'Società Pagante', 'Direzione Pagante',
                        'Servizio Pagante', 'Sottotipologia', 'Finanziata'
                    ],
                    'Valore': [
                        edition.get('centro_costo', '') or '—',
                        edition.get('societa_pagante', '') or '—',
                        edition.get('direzione_pagante', '') or '—',
                        edition.get('servizio_pagante', '') or '—',
                        edition.get('sottotipologia', '') or '—',
                        edition.get('finanziata', '') or '—',
                    ]
                })
                st.dataframe(aggiuntivi, hide_index=True, use_container_width=True)

                # === TABLE 3: Attività ===
                st.markdown("**📝 Attività**")
                if activities:
                    activity_data = []
                    for i, act in enumerate(activities):
                        activity_data.append({
                            '#': i + 1,
                            'Titolo': act.get('title', ''),
                            'Data': act.get('date', ''),
                            'Ora Inizio': act.get('start_time', ''),
                            'Ora Fine': act.get('end_time', ''),
                            'Impegno (ore)': act.get('impegno_ore', '') or '—'
                        })
                    st.dataframe(
                        pd.DataFrame(activity_data),
                        hide_index=True,
                        use_container_width=True
                    )
                else:
                    st.warning("⚠️ Nessuna attività per questa edizione.")

        st.divider()

        st.info("ℹ️ **Nota:** Le edizioni verranno create una alla volta. "
                "Questo processo potrebbe richiedere alcuni minuti.")

        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            button_text = f"✅ Crea {total_editions} Edizioni con {total_activities} Attività"
            if st.button(button_text, type="primary", use_container_width=True,
                         key="batch_edition_create_btn"):
                st.session_state.batch_edition_data = {
                    'editions': editions,
                    'total_editions': total_editions,
                    'total_activities': total_activities,
                    'current_index': 0,
                    'results': []
                }
                st.session_state.app_state = "RUNNING_BATCH_EDITION"
                st.session_state.edition_message = ""
                st.rerun()

        with col3:
            if st.button("❌ Annulla", use_container_width=True,
                         key="batch_edition_cancel_btn"):
                st.session_state.edition_parsed_data = None
                st.session_state.edition_show_summary = False
                st.rerun()

    def _start_edition_creation(self, edition_data: Dict[str, Any]):
        """Convert parsed data to model format and start automation"""
        try:
            # Convert string dates to date objects
            start_date = edition_data.get('start_date', '')
            end_date = edition_data.get('end_date', '')

            if isinstance(start_date, str):
                start_date_obj = datetime.strptime(start_date, "%d/%m/%Y").date()
            else:
                start_date_obj = start_date

            if isinstance(end_date, str):
                end_date_obj = datetime.strptime(end_date, "%d/%m/%Y").date()
            else:
                end_date_obj = end_date

            # Convert activities
            activities_list = []
            for act in edition_data.get('activities', []):
                act_date = act.get('date', '')
                if isinstance(act_date, str):
                    act_date_obj = datetime.strptime(act_date, "%d/%m/%Y").date()
                else:
                    act_date_obj = act_date

                activities_list.append({
                    'title': act.get('title', ''),
                    'description': act.get('description', ''),
                    'date': act_date_obj,
                    'start_time': act.get('start_time', '09.00'),
                    'end_time': act.get('end_time', '11.00'),
                    'impegno_previsto_in_ore': act.get('impegno_ore', '') or act.get('impegno_previsto_in_ore', '')
                })

            # Store in session state (format expected by presenter/model)
            st.session_state.edition_details = {
                'course_name': edition_data.get('course_name', ''),
                'edition_title': edition_data.get('edition_title', ''),
                'edition_start_date': start_date_obj,
                'edition_end_date': end_date_obj,
                'location': edition_data.get('location', ''),
                'supplier': edition_data.get('supplier', ''),
                'price': edition_data.get('price', ''),
                'description': edition_data.get('description', ''),
                'activities': activities_list,
                'centro_costo': edition_data.get('centro_costo', ''),
                'direzione_pagante': edition_data.get('direzione_pagante', ''),
                'finanziata': edition_data.get('finanziata', ''),
                'servizio_pagante': edition_data.get('servizio_pagante', ''),
                'sottotipologia': edition_data.get('sottotipologia', ''),
                'societa_pagante': edition_data.get('societa_pagante', ''),
            }

            # Start automation
            st.session_state.app_state = "RUNNING_EDITION"
            st.session_state.edition_message = ""
            st.session_state.edition_parsed_data = None
            st.session_state.edition_show_summary = False
            st.session_state.edition_edit_mode = False
            st.rerun()

        except ValueError as e:
            st.error(f"❌ Errore conversione dati: {str(e)}")
            import traceback
            st.code(traceback.format_exc())

    def _render_editable_edition_form(self):
        """Editable form for modifying parsed edition data before creation"""

        edition = st.session_state.edition_to_edit

        if not edition:
            st.warning("Nessun dato da modificare.")
            if st.button("⬅️ Torna indietro", key="edition_edit_back_btn"):
                st.session_state.edition_edit_mode = False
                st.rerun()
            return

        st.subheader("✏️ Modifica Edizione + Attività")
        st.info("Modifica i dettagli e clicca 'Crea Edizione' quando pronto.")

        # Activity count management (outside form)
        activities = edition.get('activities', [])

        col_add, col_remove, col_spacer = st.columns([1, 1, 2])
        with col_add:
            if st.button("➕ Aggiungi Attività", key="edition_edit_add_activity"):
                if 'activities' not in st.session_state.edition_to_edit:
                    st.session_state.edition_to_edit['activities'] = []
                st.session_state.edition_to_edit['activities'].append({
                    'title': '',
                    'description': '',
                    'date': edition.get('start_date', ''),
                    'start_time': '09.00',
                    'end_time': '11.00',
                    'impegno_ore': ''
                })
                st.rerun()

        with col_remove:
            if len(activities) > 1:
                if st.button("➖ Rimuovi Ultima", key="edition_edit_remove_activity"):
                    st.session_state.edition_to_edit['activities'].pop()
                    st.rerun()

        st.divider()

        # Main form
        with st.form(key='edit_edition_form'):
            # Edition details
            st.markdown("### 📚 Dettagli Edizione")

            col1, col2 = st.columns(2)
            with col1:
                course_name = st.text_input(
                    "Nome Corso Esistente *",
                    value=edition.get('course_name', ''),
                    key="edit_edition_course_name"
                )
                edition_title = st.text_input(
                    "Titolo Edizione",
                    value=edition.get('edition_title', ''),
                    key="edit_edition_title"
                )
                start_date = st.text_input(
                    "Data Inizio Edizione (GG/MM/AAAA) *",
                    value=edition.get('start_date', ''),
                    key="edit_edition_start_date"
                )
                end_date = st.text_input(
                    "Data Fine Edizione (GG/MM/AAAA) *",
                    value=edition.get('end_date', ''),
                    key="edit_edition_end_date"
                )

            with col2:
                location = st.text_input(
                    "Aula Principale",
                    value=edition.get('location', ''),
                    key="edit_edition_location"
                )
                supplier = st.text_input(
                    "Fornitore Formazione",
                    value=edition.get('supplier', ''),
                    key="edit_edition_supplier"
                )
                price = st.text_input(
                    "Costo (€)",
                    value=edition.get('price', ''),
                    key="edit_edition_price"
                )
                description = st.text_area(
                    "Descrizione",
                    value=edition.get('description', ''),
                    key="edit_edition_description",
                    height=100
                )
                # Attributi Aggiuntivi section
                st.markdown("### 🗂️ Attributi Aggiuntivi")
                col3, col4 = st.columns(2)
                with col3:
                    st.text_input(
                        "Centro di Costo",
                        value=edition.get('centro_costo', ''),
                        key="edit_edition_centro_costo"
                    )
                    st.text_input(
                        "Società Pagante",
                        value=edition.get('societa_pagante', ''),
                        key="edit_edition_societa_pagante"
                    )
                    st.text_input(
                        "Direzione Pagante",
                        value=edition.get('direzione_pagante', ''),
                        key="edit_edition_direzione_pagante"
                    )
                with col4:
                    st.text_input(
                        "Servizio Pagante",
                        value=edition.get('servizio_pagante', ''),
                        key="edit_edition_servizio_pagante"
                    )
                    st.text_input(
                        "Sottotipologia",
                        value=edition.get('sottotipologia', ''),
                        key="edit_edition_sottotipologia"
                    )
                    st.selectbox(
                        "Finanziata",
                        options=['', 'Sì', 'No'],
                        index=['', 'Sì', 'No'].index(edition.get('finanziata', ''))
                        if edition.get('finanziata', '') in ['', 'Sì', 'No'] else 0,
                        key="edit_edition_finanziata"
                    )

            # Activities
            st.markdown("### 📝 Attività")

            activities = edition.get('activities', [])
            for idx, activity in enumerate(activities):
                with st.expander(f"Attività {idx + 1}: {activity.get('title', 'Nuova Attività')}", expanded=True):
                    col1, col2, col3 = st.columns([2, 1, 1])

                    with col1:
                        st.text_input(
                            "Titolo *",
                            value=activity.get('title', ''),
                            key=f"edit_act_title_{idx}"
                        )
                    with col2:
                        st.text_input(
                            "Data (GG/MM/AAAA) *",
                            value=activity.get('date', ''),
                            key=f"edit_act_date_{idx}"
                        )
                    with col3:
                        st.text_input(
                            "Impegno (ore)",
                            value=activity.get('impegno_ore', '') or activity.get('impegno_previsto_in_ore', ''),
                            key=f"edit_act_hours_{idx}"
                        )

                    col1, col2 = st.columns(2)
                    with col1:
                        st.text_input(
                            "Ora Inizio (HH.MM)",
                            value=activity.get('start_time', '09.00'),
                            key=f"edit_act_start_{idx}"
                        )
                    with col2:
                        st.text_input(
                            "Ora Fine (HH.MM)",
                            value=activity.get('end_time', '11.00'),
                            key=f"edit_act_end_{idx}"
                        )

                    st.text_area(
                        "Descrizione Attività",
                        value=activity.get('description', ''),
                        key=f"edit_act_desc_{idx}",
                        height=80
                    )

            st.divider()

            # Submit buttons
            col1, col2, col3 = st.columns([2, 1, 1])

            with col1:
                submit = st.form_submit_button(
                    "✅ Crea Edizione e Attività",
                    type="primary",
                    width='stretch'
                )

            with col2:
                preview = st.form_submit_button(
                    "👁️ Anteprima",
                    width='stretch'
                )

            with col3:
                cancel = st.form_submit_button(
                    "❌ Annulla",
                    width='stretch'
                )

        # Handle form actions
        if submit:
            self._process_edited_edition(edition)
        elif preview:
            self._save_edited_edition_to_preview(edition)
        elif cancel:
            st.session_state.edition_edit_mode = False
            st.session_state.edition_to_edit = None
            st.session_state.edition_parsed_data = None
            st.session_state.edition_show_summary = False
            st.session_state.edition_input_method = "structured"
            st.rerun()

    def _process_edited_edition(self, original_edition):
        """Validate and process the edited edition form"""

        # Collect values from form
        course_name = st.session_state.get('edit_edition_course_name', '').strip()
        edition_title = st.session_state.get('edit_edition_title', '').strip()
        start_date = st.session_state.get('edit_edition_start_date', '').strip()
        end_date = st.session_state.get('edit_edition_end_date', '').strip()
        location = st.session_state.get('edit_edition_location', '').strip()
        supplier = st.session_state.get('edit_edition_supplier', '').strip()
        price = st.session_state.get('edit_edition_price', '').strip()
        description = st.session_state.get('edit_edition_description', '').strip()

        # Validate required fields
        if not course_name:
            st.error("❌ Il nome del corso è obbligatorio.")
            st.stop()
        if not start_date:
            st.error("❌ La data di inizio è obbligatoria.")
            st.stop()
        if not end_date:
            st.error("❌ La data di fine è obbligatoria.")
            st.stop()

        # Validate dates
        try:
            start_date_obj = datetime.strptime(start_date, "%d/%m/%Y").date()
            end_date_obj = datetime.strptime(end_date, "%d/%m/%Y").date()

            if end_date_obj < start_date_obj:
                st.error("❌ La data di fine non può essere prima della data di inizio.")
                st.stop()
        except ValueError:
            st.error("❌ Formato data non valido. Usa GG/MM/AAAA.")
            st.stop()

        # Collect activities
        activities_list = []
        activities = original_edition.get('activities', [])

        for idx in range(len(activities)):
            act_title = st.session_state.get(f'edit_act_title_{idx}', '').strip()
            act_date = st.session_state.get(f'edit_act_date_{idx}', '').strip()
            act_start = st.session_state.get(f'edit_act_start_{idx}', '09.00').strip()
            act_end = st.session_state.get(f'edit_act_end_{idx}', '11.00').strip()
            act_desc = st.session_state.get(f'edit_act_desc_{idx}', '').strip()
            act_hours = st.session_state.get(f'edit_act_hours_{idx}', '').strip()

            if not act_title:
                st.error(f"❌ Attività {idx + 1}: Il titolo è obbligatorio.")
                st.stop()
            if not act_date:
                st.error(f"❌ Attività {idx + 1}: La data è obbligatoria.")
                st.stop()

            # Validate activity date
            try:
                act_date_obj = datetime.strptime(act_date, "%d/%m/%Y").date()
            except ValueError:
                st.error(f"❌ Attività {idx + 1}: Formato data non valido.")
                st.stop()

            activities_list.append({
                'title': act_title,
                'description': act_desc,
                'date': act_date_obj,
                'start_time': act_start,
                'end_time': act_end,
                'impegno_previsto_in_ore': act_hours
            })

        if not activities_list:
            st.error("❌ Almeno una attività è richiesta.")
            st.stop()

        # Store and start automation
        st.session_state.edition_details = {
            'course_name': course_name,
            'edition_title': edition_title,
            'edition_start_date': start_date_obj,
            'edition_end_date': end_date_obj,
            'location': location,
            'supplier': supplier,
            'price': price,
            'description': description,
            'activities': activities_list,
            'centro_costo': original_edition.get('centro_costo', ''),
            'societa_pagante': original_edition.get('societa_pagante', ''),
            'direzione_pagante': original_edition.get('direzione_pagante', ''),
            'servizio_pagante': original_edition.get('servizio_pagante', ''),
            'sottotipologia': original_edition.get('sottotipologia', ''),
            'finanziata': original_edition.get('finanziata', ''),
        }

        st.session_state.app_state = "RUNNING_EDITION"
        st.session_state.edition_message = ""
        st.session_state.edition_edit_mode = False
        st.session_state.edition_to_edit = None
        st.session_state.edition_parsed_data = None
        st.session_state.edition_show_summary = False
        st.rerun()

    def _save_edited_edition_to_preview(self, original_edition):
        """Save edited data and return to preview"""

        activities = original_edition.get('activities', [])
        updated_activities = []

        for idx in range(len(activities)):
            updated_activities.append({
                'title': st.session_state.get(f'edit_act_title_{idx}', ''),
                'description': st.session_state.get(f'edit_act_desc_{idx}', ''),
                'date': st.session_state.get(f'edit_act_date_{idx}', ''),
                'start_time': st.session_state.get(f'edit_act_start_{idx}', '09.00'),
                'end_time': st.session_state.get(f'edit_act_end_{idx}', '11.00'),
                'impegno_ore': st.session_state.get(f'edit_act_hours_{idx}', '')
            })

        updated_edition = {
            'course_name': st.session_state.get('edit_edition_course_name', ''),
            'edition_title': st.session_state.get('edit_edition_title', ''),
            'start_date': st.session_state.get('edit_edition_start_date', ''),
            'end_date': st.session_state.get('edit_edition_end_date', ''),
            'location': st.session_state.get('edit_edition_location', ''),
            'supplier': st.session_state.get('edit_edition_supplier', ''),
            'price': st.session_state.get('edit_edition_price', ''),
            'description': st.session_state.get('edit_edition_description', ''),
            'activities': updated_activities,
            'centro_costo': original_edition.get('centro_costo', ''),
            'societa_pagante': original_edition.get('societa_pagante', ''),
            'direzione_pagante': original_edition.get('direzione_pagante', ''),
            'servizio_pagante': original_edition.get('servizio_pagante', ''),
            'sottotipologia': original_edition.get('sottotipologia', ''),
            'finanziata': original_edition.get('finanziata', ''),
        }

        st.session_state.edition_parsed_data = updated_edition
        st.session_state.edition_show_summary = True
        st.session_state.edition_edit_mode = False
        st.session_state.edition_to_edit = None
        st.rerun()

    #---STUDENT---
    def _preserve_student_data(self, num_students):
        """Preserve current student data before form submission"""
        # CRITICAL: Also preserve the count itself
        st.session_state.preserved_student_data["_count"] = num_students

        for i in range(num_students):
            st.session_state.preserved_student_data[f"student_{i}_name"] = \
                st.session_state.get(f"student_name_{i}", "")

    def _restore_student_data(self, num_students):
        """Restore preserved student data to form fields"""
        # CRITICAL: Restore the count to show correct number of fields
        if "_count" in st.session_state.preserved_student_data:
            restored_count = st.session_state.preserved_student_data["_count"]
            # Update num_students to match what was preserved
            if st.session_state.num_students != restored_count:
                st.session_state.num_students = restored_count

        # Use the restored count for the loop
        count_to_restore = st.session_state.num_students
        for i in range(count_to_restore):
            if f"student_{i}_name" in st.session_state.preserved_student_data:
                st.session_state[f"student_name_{i}"] = \
                    st.session_state.preserved_student_data[f"student_{i}_name"]

    def _parse_student_excel_file(self, uploaded_file) -> 'Optional[Dict[str, Any]]':
        """
        Parse Excel file with student data from the ALLIEVI sheet.

        The Excel workbook has 4 sheets: CORSO, EDIZIONE, ATTIVITA, ALLIEVI
        Student data is on the ALLIEVI sheet.

        EXPECTED FORMAT on ALLIEVI sheet:
        | CODICE EDIZIONE | PERSON NUMBER |
        |-----------------|---------------|
        | OLC466201       | 1168          |

        Returns:
            Dictionary with 'editions' list, each containing edition_code and students
        """
        try:
            # === STEP 1: Try to read the ALLIEVI sheet ===
            # Try multiple possible sheet names (case-insensitive matching)
            target_sheets = ['ALLIEVI', 'Allievi', 'allievi', 'STUDENTS', 'Students']

            df = None
            sheet_found = None

            # First, check what sheets exist in the file
            try:
                xls = pd.ExcelFile(uploaded_file, engine='openpyxl')
                available_sheets = xls.sheet_names
                st.info(f"📄 Fogli trovati nel file: {', '.join(available_sheets)}")
            except Exception as e:
                st.error(f"❌ Errore apertura file: {e}")
                return None

            # Try to find the ALLIEVI sheet
            for sheet_name in target_sheets:
                if sheet_name in available_sheets:
                    df = pd.read_excel(uploaded_file, sheet_name=sheet_name, header=0, engine='openpyxl')
                    sheet_found = sheet_name
                    break

            # If no known sheet name found, try the last sheet (ALLIEVI is 4th/last)
            if df is None and len(available_sheets) >= 4:
                last_sheet = available_sheets[-1]
                st.warning(f"⚠️ Foglio 'ALLIEVI' non trovato, provo ultimo foglio: '{last_sheet}'")
                df = pd.read_excel(uploaded_file, sheet_name=last_sheet, header=0, engine='openpyxl')
                sheet_found = last_sheet

            # Last resort: try first sheet
            if df is None:
                st.warning("⚠️ Foglio 'ALLIEVI' non trovato, provo il primo foglio...")
                df = pd.read_excel(uploaded_file, header=0, engine='openpyxl')
                sheet_found = available_sheets[0] if available_sheets else "default"

            st.info(f"📊 Lettura foglio: **{sheet_found}** — Colonne: {', '.join(df.columns.astype(str))}")

            # === STEP 2: Normalize column names ===
            df.columns = df.columns.str.strip().str.lower()

            # --- Find edition code column ---
            edition_col_names = [
                'codice edizione', 'codice_edizione', 'edition code',
                'edizione', 'codice', 'code'
            ]
            edition_col = None
            for name in edition_col_names:
                if name in df.columns:
                    edition_col = name
                    break

            # --- Find person number column ---
            person_col_names = [
                'person number', 'person_number', 'numero persona',
                'numero persona', 'numero_persona', 'number', 'id'
            ]
            person_col = None
            for name in person_col_names:
                if name in df.columns:
                    person_col = name
                    break

            # --- Find OPTIONAL scadenza column ---
            scadenza_col_names = [
                'data scadenza', 'data_scadenza', 'scadenza',
                'data di scadenza', 'due date'
            ]
            scadenza_col = None
            for name in scadenza_col_names:
                if name in df.columns:
                    scadenza_col = name
                    break

            # --- Validate ---
            if not edition_col:
                st.error(
                    f"❌ Colonna 'CODICE EDIZIONE' non trovata nel foglio '{sheet_found}'.\n\n"
                    f"Colonne trovate: {', '.join(df.columns)}"
                )
                st.info("**Colonne attese:** CODICE EDIZIONE, PERSON NUMBER")
                return None

            if not person_col:
                st.error(
                    f"❌ Colonna 'PERSON NUMBER' non trovata nel foglio '{sheet_found}'.\n\n"
                    f"Colonne trovate: {', '.join(df.columns)}"
                )
                st.info("**Colonne attese:** CODICE EDIZIONE, PERSON NUMBER")
                return None

            # === STEP 3: Clean and group data ===
            df = df.dropna(subset=[edition_col, person_col])

            if df.empty:
                st.error("❌ Nessun dato valido trovato nel file.")
                return None

            # Convert person numbers to clean strings (1168.0 → "1168")
            df[person_col] = df[person_col].apply(
                lambda x: str(int(x)) if isinstance(x, (int, float)) and pd.notna(x) and x == int(x)
                else str(x).strip()
            )

            # Convert edition codes to clean strings
            df[edition_col] = df[edition_col].apply(
                lambda x: str(int(x)) if isinstance(x, (int, float)) and pd.notna(x) and x == int(x)
                else str(x).strip()
            )

            # === STEP 4: Group by edition ===
            editions_list = []

            for edition_code, group in df.groupby(edition_col, sort=False):
                edition_code_str = str(edition_code).strip()
                if not edition_code_str or edition_code_str.lower() == 'nan':
                    continue

                students = [
                    str(s).strip() for s in group[person_col].tolist()
                    if str(s).strip() and str(s).strip().lower() != 'nan'
                ]

                if students:
                    # Optional scadenza: take the first non-empty value for this edition
                    edition_scadenza = None
                    if scadenza_col:
                        for v in group[scadenza_col].tolist():
                            v_str = str(v).strip()
                            if v_str and v_str.lower() != 'nan':
                                # Excel dates may come as datetime; normalize to GG/MM/AAAA
                                try:
                                    if hasattr(v, 'strftime'):
                                        edition_scadenza = v.strftime('%d/%m/%Y')
                                    else:
                                        edition_scadenza = v_str
                                except Exception:
                                    edition_scadenza = v_str
                                break

                    editions_list.append({
                        'edition_code': edition_code_str,
                        'students': students,
                        'data_scadenza': edition_scadenza
                    })
            if not editions_list:
                st.error("❌ Nessun dato valido trovato dopo il parsing.")
                return None

            total_students = sum(len(e['students']) for e in editions_list)
            st.success(
                f"✅ Foglio '{sheet_found}': "
                f"{len(editions_list)} edizioni, {total_students} allievi totali!"
            )

            return {
                'editions': editions_list,
                'total_editions': len(editions_list),
                'total_students': total_students,
                'file_name': uploaded_file.name
            }

        except Exception as e:
            st.error(f"❌ Errore lettura Excel: {str(e)}")
            import traceback
            with st.expander("🔍 Dettagli errore"):
                st.code(traceback.format_exc())
            return None

    def _parse_presenza_excel_file(self, uploaded_file,
                                   default_stato: str = "Completato") -> 'Optional[Dict[str, Any]]':
        """
        Parse ASSEGNA sheet from Excel for presenza assignment.

        Expected format (forward-fill supported):
        | CODICE EDIZIONE | PERSON NUMBER | STATO       |
        | OLC621263       | 1168          | Completato  |
        |                 | 1189          |             | ← inherits OLC621263, default stato
        |                 | 1199          | Esente      |
        | OLC621270       | 1200          | Non passato |

        Rules:
        - Empty CODICE EDIZIONE → forward-filled from previous row
        - Empty/missing STATO → uses default_stato from UI dropdown
        - STATO normalization: "compl"/"c"/"ok" → Completato, "esent"/"e" → Esente,
          "non"/"pass"/"fail" → Non passato

        Returns:
            {
                'jobs': [{'edition_code', 'students', 'stato'}, ...],
                'total_jobs': N,
                'total_editions': M,
                'total_students': K,
                'has_stato_column': bool,
                'file_name': str
            }
        Each "job" = unique (edition_code, stato) combination.
        """
        try:
            # === Find ASSEGNA sheet ===
            target_sheets = ['PRESENZA','Presenza', 'presenza', 'ASSEGNA', 'Assegna', 'assegna']

            try:
                xls = pd.ExcelFile(uploaded_file, engine='openpyxl')
                available_sheets = xls.sheet_names
                st.info(f"📄 Fogli trovati: {', '.join(available_sheets)}")
            except Exception as e:
                st.error(f"❌ Errore apertura file: {e}")
                return None

            df = None
            sheet_found = None
            for sheet_name in target_sheets:
                if sheet_name in available_sheets:
                    df = pd.read_excel(uploaded_file, sheet_name=sheet_name,
                                       header=0, engine='openpyxl')
                    sheet_found = sheet_name
                    break

            if df is None:
                st.error(
                    f"❌ Foglio **PRESENZA** non trovato.\n\n"
                    f"Fogli disponibili: {', '.join(available_sheets)}\n\n"
                    f"**Crea un foglio chiamato `PRESENZA` con le colonne:**\n"
                    f"- CODICE EDIZIONE\n"
                    f"- PERSON NUMBER\n"
                    f"- STATO (opzionale)"
                )
                return None

            st.info(f"📊 Lettura foglio: **{sheet_found}** — {len(df)} righe")

            # === Normalize column names ===
            df.columns = df.columns.str.strip().str.lower()

            edition_col_names = ['codice edizione', 'codice_edizione',
                                 'edition code', 'edizione', 'codice', 'code']
            person_col_names = ['person number', 'person_number',
                                'numero persona', 'numero_persona',
                                'matricola', 'allievo']
            stato_col_names = ['stato', 'stato completamento',
                               'stato_completamento',
                               'completion status', 'status']

            edition_col = next((n for n in edition_col_names
                                if n in df.columns), None)
            person_col = next((n for n in person_col_names
                               if n in df.columns), None)
            stato_col = next((n for n in stato_col_names
                              if n in df.columns), None)

            if not edition_col or not person_col:
                st.error(
                    f"❌ Colonne obbligatorie mancanti.\n\n"
                    f"**Servono:** CODICE EDIZIONE, PERSON NUMBER "
                    f"(STATO è opzionale)\n\n"
                    f"**Colonne trovate:** {', '.join(df.columns)}"
                )
                return None

            # === Forward-fill edition code ===
            df[edition_col] = df[edition_col].ffill()

            # Drop rows with no person number (truly empty rows)
            df = df.dropna(subset=[person_col])

            if df.empty:
                st.error("❌ Nessun dato valido trovato dopo il filtraggio.")
                return None

            # Clean person numbers (1168.0 → "1168")
            df[person_col] = df[person_col].apply(
                lambda x: str(int(x)) if isinstance(x, (int, float))
                                         and pd.notna(x) and x == int(x)
                else str(x).strip()
            )

            # Clean edition codes
            df[edition_col] = df[edition_col].apply(
                lambda x: str(int(x)) if isinstance(x, (int, float))
                                         and pd.notna(x) and x == int(x)
                else str(x).strip()
            )

            # === Stato normalization ===
            def normalize_stato(value, default=default_stato):
                if pd.isna(value):
                    return default
                value_str = str(value).strip().lower()
                if not value_str or value_str == 'nan':
                    return default
                if (value_str.startswith('compl') or
                        value_str in ['c', 'ok', 'sì', 'si', 'yes', 'y']):
                    return 'Completato'
                if (value_str.startswith('esent') or
                        value_str.startswith('exempt') or value_str == 'e'):
                    return 'Esente'
                if (value_str.startswith('non') or 'pass' in value_str or
                        value_str.startswith('fail') or value_str == 'no'):
                    return 'Non passato'
                return default  # Unknown → use default

            # === Group by (edition, stato) ===
            jobs = []
            for edition_code, group in df.groupby(edition_col, sort=False):
                edition_code_str = str(edition_code).strip()
                if not edition_code_str or edition_code_str.lower() == 'nan':
                    continue

                if stato_col:
                    stato_groups = {}
                    for _, row in group.iterrows():
                        student = str(row[person_col]).strip()
                        if not student or student.lower() == 'nan':
                            continue
                        student_stato = normalize_stato(row[stato_col])
                        stato_groups.setdefault(student_stato, []).append(student)

                    for stato_val, students in stato_groups.items():
                        jobs.append({
                            'edition_code': edition_code_str,
                            'students': students,
                            'stato': stato_val
                        })
                else:
                    students = [
                        str(s).strip() for s in group[person_col].tolist()
                        if str(s).strip() and str(s).strip().lower() != 'nan'
                    ]
                    if students:
                        jobs.append({
                            'edition_code': edition_code_str,
                            'students': students,
                            'stato': default_stato
                        })

            if not jobs:
                st.error("❌ Nessun dato valido dopo il parsing.")
                return None

            total_students = sum(len(j['students']) for j in jobs)
            unique_editions = len(set(j['edition_code'] for j in jobs))

            st.success(
                f"✅ Foglio '{sheet_found}': "
                f"{unique_editions} edizioni, {len(jobs)} gruppi (edizione+stato), "
                f"{total_students} assegnazioni totali"
            )

            return {
                'jobs': jobs,
                'total_jobs': len(jobs),
                'total_editions': unique_editions,
                'total_students': total_students,
                'has_stato_column': stato_col is not None,
                'file_name': uploaded_file.name
            }

        except Exception as e:
            st.error(f"❌ Errore lettura Excel: {str(e)}")
            import traceback
            with st.expander("🔍 Dettagli errore"):
                st.code(traceback.format_exc())
            return None

    def _render_student_form(self, is_disabled):
        """
        Student form with 3 input methods:
        A) TXT file upload (single edition: user enters codice edizione + uploads .txt)
        B) Excel file upload (multi-edition: CODICE EDIZIONE + PERSON NUMBER from ALLIEVI sheet)
        C) NLP (natural language in Italian)
        """
        # Restore preserved data
        if st.session_state.preserved_student_data:
            self._restore_student_data(st.session_state.num_students)

        # === CHECK FOR SUMMARY/PREVIEW MODE ===
        if st.session_state.get('student_show_summary') and st.session_state.get('student_parsed_data'):
            self._render_student_batch_preview(st.session_state.student_parsed_data)
            return

        # === INPUT METHOD SELECTION ===
        student_method = st.radio(
            "Come vuoi inserire gli allievi?",
            options=["txt", "excel", "nlp"],
            format_func=lambda x: {
                "txt": "📄 Caricamento File TXT",
                "excel": "📊 Caricamento File Excel",
                "nlp": "💬 Compilazione con AI"
            }[x],
            key="student_input_method",
            horizontal=True
        )

        st.divider()

        # ══════════════════════════════════════════════════
        # METHOD A: TXT FILE UPLOAD (single edition)
        # ══════════════════════════════════════════════════
        if student_method == "txt":
            st.info(
                "**Carica un file .txt** con un numero di numero persona per riga.\n\n"
                "Esempio contenuto file:\n"
                "```\n1168\n1189\n1199\n1216\n```",
                icon="📄"
            )

            with st.form(key='student_form_txt'):
                st.subheader("1. Trova Edizione")
                st.text_input(
                    "Codice Edizione (Numero Edizione)",
                    placeholder="Es: OLC466201",
                    key="student_edition_code_key"
                )

                st.text_input(
                    "Data scadenza (facoltativa, GG/MM/AAAA)",
                    placeholder="Es: 31/12/2026 — se vuoto, verrà usato domani",
                    key="student_scadenza_key"
                )

                st.divider()
                st.subheader("2. Carica Elenco Numero Persona")

                uploaded_txt = st.file_uploader(
                    "File TXT con numero persona (una per riga)",
                    type=['txt'],
                    key="student_txt_uploader"
                )


                col1, col2 = st.columns([3, 1])
                with col1:
                    submitted = st.form_submit_button(
                        "Analizza File", type="primary",
                        disabled=is_disabled, width='stretch'
                    )
                with col2:
                    st.form_submit_button(
                        "Pulisci 🧹", width='stretch',
                        on_click=self._clear_student_form_callback
                    )

            if submitted:
                import re

                edition_code = st.session_state.student_edition_code_key.strip()
                manual_scadenza = st.session_state.get("student_scadenza_key", "").strip()

                if not edition_code:
                    st.error("❌ Il campo **Codice Edizione** è obbligatorio.")
                    st.stop()

                # Optional: validate the manual date format if provided
                if manual_scadenza:
                    import re as _re
                    # accept GG/MM/AAAA, GG.MM.AAAA, GG-MM-AAAA
                    if not _re.match(r'^\d{2}[/.\-]\d{2}[/.\-]\d{4}$', manual_scadenza):
                        st.error("❌ Data scadenza non valida. Usa il formato "
                                 "GG/MM/AAAA (es: 31/12/2026).")
                        st.stop()

                uploaded_txt = st.session_state.get("student_txt_uploader")
                if uploaded_txt is None:
                    st.error("❌ Carica un file .txt con numero persona per riga.")
                    st.stop()

                # Read TXT file
                student_list = []
                try:
                    content = uploaded_txt.read().decode('utf-8')
                    lines = content.strip().split('\n')
                    for line in lines:
                        parts = re.split(r'[,;\s]+', line.strip())
                        for p in parts:
                            p = p.strip()
                            if p:
                                student_list.append(p)
                except Exception as e:
                    st.error(f"❌ Errore lettura file: {e}")
                    st.stop()

                if not student_list:
                    st.error("❌ Nessuna numero persona trovata nel file.")
                    st.stop()

                # Store parsed data and show preview (same as Excel flow)
                st.session_state.student_parsed_data = {
                    'editions': [{
                        'edition_code': edition_code,
                        'students': student_list,
                        'data_scadenza': manual_scadenza if manual_scadenza else None
                    }],
                    'total_editions': 1,
                    'total_students': len(student_list)
                }
                st.session_state.student_show_summary = True
                st.rerun()
        # ══════════════════════════════════════════════════
        # METHOD B: EXCEL FILE UPLOAD (multi-edition)
        # ══════════════════════════════════════════════════
        elif student_method == "excel":
            st.info(
                "Il file può contenere allievi per **più edizioni**.\n"
                "I dati vengono letti dal foglio **ALLIEVI** (4° foglio).",
                icon="📊"
            )

            uploaded_file = st.file_uploader(
                "Carica File Excel (.xlsx, .xls)",
                type=['xlsx', 'xls'],
                help="File con foglio ALLIEVI contenente CODICE EDIZIONE e PERSON NUMBER",
                key="student_excel_uploader"
            )

            if uploaded_file is not None:
                col1, col2 = st.columns([1, 1])

                with col1:
                    if st.button("📊 Analizza File Excel", type="primary", width='stretch',
                                 key="analyze_student_excel_btn"):
                        with st.spinner("🔍 Lettura foglio ALLIEVI..."):
                            parsed_data = self._parse_student_excel_file(uploaded_file)

                        if parsed_data:
                            st.session_state.student_parsed_data = parsed_data
                            st.session_state.student_show_summary = True
                            st.rerun()
                        else:
                            st.error("❌ Impossibile estrarre i dati dal file.")

                with col2:
                    if st.button("🧹 Cancella", width='stretch', key="clear_student_excel_btn"):
                        st.session_state.student_parsed_data = None
                        st.session_state.student_show_summary = False
                        st.rerun()

        # ══════════════════════════════════════════════════
        # METHOD C: NATURAL LANGUAGE (NLP)
        # ══════════════════════════════════════════════════
        elif student_method == "nlp":
            st.info(
                "**Scrivi una frase in italiano**, ad esempio:\n\n"
                '- "Aggiungi allievi 1168, 1189, 1199 all\'edizione OLC466201"\n'
                '- "Edizione OLC466201: numero persona 1168 1189 1199 1216"\n'
                '- "Per edizione OLC466201 inserisci 1168, 1189, 1199"\n\n'
                "Il sistema estrarrà automaticamente il codice edizione e numero persona.",
                icon="💬"
            )
            st.caption(
                "ℹ️ Con il metodo AI la **data scadenza** sarà sempre *domani*. "
                "Per impostare una data scadenza personalizzata, usa il metodo "
                "**TXT** o **Excel**."
            )
            # Initialize key state
            if "student_nlp_text_area" not in st.session_state:
                st.session_state.student_nlp_text_area = ""

            nlp_text = st.text_area(
                "Descrivi l'inserimento in linguaggio naturale:",
                height=150,
                #placeholder="Aggiungi allievi 1168, 1189, 1199 all'edizione OLC466201",
                key="student_nlp_text_area"
            )

            # Character count
            text_length = len(nlp_text.strip()) if nlp_text else 0
            if text_length > 0:
                st.caption(f"✏️ {text_length} caratteri inseriti")
            else:
                st.warning("Inserisci del testo per abilitare l'analisi", icon="⚠️")

            col1, col2 = st.columns([1, 1])

            with col1:
                if st.button("🤖 Analizza Testo", type="primary", width='stretch',
                             key="analyze_student_nlp_btn"):
                    if not nlp_text or not nlp_text.strip():
                        st.error("⚠️ Inserisci del testo prima di analizzare.")
                        st.stop()

                    if text_length < 10:
                        st.error("⚠️ Il testo è troppo corto.")
                        st.stop()

                    st.session_state.student_parsed_data = None
                    st.session_state.student_show_summary = False

                    with st.spinner("🤖 Analisi del testo in corso..."):
                        parsed = self._parse_student_nlp_input(nlp_text)

                    if parsed and parsed.get('edition_code') and parsed.get('students'):
                        batch_format = {
                            'editions': [{
                                'edition_code': parsed['edition_code'],
                                'students': parsed['students']
                            }],
                            'total_editions': 1,
                            'total_students': len(parsed['students'])
                        }
                        st.session_state.student_parsed_data = batch_format
                        st.session_state.student_show_summary = True
                        st.rerun()

                    elif parsed:
                        st.warning("⚠️ Estrazione parziale. Completa i campi mancanti:")

                        with st.form(key='student_nlp_partial_form'):
                            edition_code = st.text_input(
                                "Codice Edizione",
                                value=parsed.get('edition_code', ''),
                                key="nlp_partial_edition_code"
                            )
                            students_text = st.text_area(
                                "Numero Persona (una per riga o separate da virgola)",
                                value='\n'.join(parsed.get('students', [])),
                                key="nlp_partial_students",
                                height=100
                            )

                            if st.form_submit_button("✅ Conferma e Procedi", type="primary"):
                                import re
                                if not edition_code.strip():
                                    st.error("❌ Codice Edizione obbligatorio.")
                                    st.stop()

                                student_list = [
                                    s.strip() for s in re.split(r'[,\n]+', students_text)
                                    if s.strip()
                                ]

                                if not student_list:
                                    st.error("❌ Inserisci almeno un numero persona.")
                                    st.stop()

                                batch_format = {
                                    'editions': [{
                                        'edition_code': edition_code.strip(),
                                        'students': student_list
                                    }],
                                    'total_editions': 1,
                                    'total_students': len(student_list)
                                }
                                st.session_state.student_parsed_data = batch_format
                                st.session_state.student_show_summary = True
                                st.rerun()
                    else:
                        st.error(
                            "❌ Impossibile estrarre le informazioni.\n\n"
                            "Assicurati di includere:\n"
                            "- **Codice edizione** (es: OLC466201)\n"
                            "- **Numero persona** allievi (es: 1168, 1189, 1199)"
                        )

            with col2:
                if st.button("🧹 Cancella Testo", width='stretch', key="clear_student_nlp_btn"):
                    st.session_state.student_nlp_text_area = ""
                    st.session_state.student_parsed_data = None
                    st.session_state.student_show_summary = False
                    st.rerun()

    def _render_presenza_form(self, is_disabled: bool = False):
        """
        Form for Assegnazione Presenza.
        Three input methods: Structured, Excel, NLP.

        Pipeline:
        - User provides: edition_code + list of person numbers + stato
        - Automation: login → navigate to edition → find each student
          → click Gestisci attività → fill Data completamento + Stato → Salva
        """

        # === CHECK FOR BATCH PREVIEW MODE (Excel multi-edition) ===
        if st.session_state.get('presenza_show_batch_preview') and \
                st.session_state.get('presenza_batch_data'):
            self._render_presenza_batch_preview(
                st.session_state.presenza_batch_data)
            return

        # === CHECK FOR PREVIEW MODE ===
        if st.session_state.get('presenza_show_summary') and \
                st.session_state.get('presenza_data'):
            self._render_presenza_preview(st.session_state.presenza_data)
            return

        st.subheader("Scegli il Metodo di Inserimento")

        input_method = st.radio(
            "Come vuoi inserire i dati?",
            options=["structured", "excel", "nlp"],
            format_func=lambda x: {
                "structured": "📝 Input Strutturato (Form)",
                "excel": "📊 Caricamento File Excel",
                "nlp": "💬 Compilazione con AI"
            }[x],
            key="presenza_input_method",
            horizontal=True
        )

        st.divider()

        if input_method == "structured":
            self._render_presenza_structured(is_disabled)
        elif input_method == "excel":
            self._render_presenza_excel(is_disabled)
        elif input_method == "nlp":
            self._render_presenza_nlp(is_disabled)

    def _render_presenza_structured(self, is_disabled: bool):
        """Structured form for presenza assignment."""
        st.info(
            "Inserisci il codice edizione, i numeri persona degli allievi "
            "e lo stato di completamento.",
            icon="📝"
        )

        with st.form(key='presenza_structured_form'):
            st.subheader("Dati Presenza")

            edition_code = st.text_input(
                "Codice Edizione *",
                placeholder="Es: OLC466201",
                key="presenza_edition_code"
            )

            stato = st.selectbox(
                "Stato Completamento *",
                options=["Completato", "Esente", "Non passato"],
                index=0,
                key="presenza_stato"
            )

            st.markdown("**Numeri Persona Allievi** (uno per riga)")
            students_text = st.text_area(
                "Numeri persona",
                height=150,
                placeholder="1168\n1189\n1199\n1216",
                key="presenza_students_text"
            )

            col1, col2 = st.columns([3, 1])
            with col1:
                submitted = st.form_submit_button(
                    "📋 Anteprima", type="primary",
                    disabled=is_disabled, width='stretch')
            with col2:
                st.form_submit_button(
                    "Pulisci 🧹", width='stretch',
                    on_click=self._clear_presenza_callback)

        if submitted:
            import re
            if not edition_code.strip():
                st.error("❌ Codice Edizione obbligatorio.")
                st.stop()

            students = [
                s.strip() for s in re.split(r'[\n,;]+', students_text)
                if s.strip()
            ]

            if not students:
                st.error("❌ Inserisci almeno un numero persona.")
                st.stop()

            st.session_state.presenza_data = {
                'edition_code': edition_code.strip(),
                'students': students,
                'stato': stato
            }
            st.session_state.presenza_show_summary = True
            st.rerun()

    def _render_presenza_excel(self, is_disabled: bool):
        """Excel upload for presenza — supports multi-edition ASSEGNA sheet."""
        st.info(
            "**Formato Excel** (foglio `PRESENZA`):\n\n"
            "| CODICE EDIZIONE | PERSON NUMBER | STATO       |\n"
            "|-----------------|---------------|-------------|\n"
            "| OLC621263       | 1168          | Completato  |\n"
            "|                 | 1189          |             |\n"
            "| OLC621270       | 1200          | Non passato |\n\n"
            "💡 **Suggerimento:** Lascia vuota la cella CODICE EDIZIONE "
            "per le righe successive — verrà ereditata dall'edizione "
            "precedente (forward-fill).\n\n"
            "La colonna **STATO** è opzionale. Se omessa o vuota, "
            "verrà usato lo stato di default selezionato qui sotto.",
            icon="📊"
        )

        default_stato = st.selectbox(
            "Stato di Default (per righe senza STATO)",
            options=["Completato", "Esente", "Non passato"],
            index=0,
            key="presenza_excel_default_stato"
        )

        uploaded_file = st.file_uploader(
            "Carica File Excel (.xlsx)",
            type=['xlsx', 'xls'],
            key="presenza_excel_uploader"
        )

        if uploaded_file:
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("📊 Analizza File", type="primary",
                             width='stretch', key="presenza_analyze_excel"):
                    with st.spinner("🔍 Lettura foglio PRESENZA..."):
                        parsed = self._parse_presenza_excel_file(
                            uploaded_file, default_stato=default_stato)

                    if parsed and parsed.get('jobs'):
                        st.session_state.presenza_batch_data = parsed
                        st.session_state.presenza_show_batch_preview = True
                        st.rerun()
                    else:
                        st.error("❌ Impossibile leggere il file.")

            with col2:
                if st.button("🧹 Cancella", width='stretch',
                             key="presenza_clear_excel"):
                    st.session_state.presenza_batch_data = None
                    st.session_state.presenza_show_batch_preview = False
                    st.rerun()

    def _render_presenza_batch_preview(self, batch_data: dict):
        """Preview screen for multi-edition presenza batch."""
        jobs = batch_data.get('jobs', [])
        total_students = batch_data.get('total_students', 0)
        total_editions = batch_data.get('total_editions', 0)

        st.success(
            f"✅ **{total_editions} edizioni** • "
            f"**{len(jobs)} gruppi (edizione+stato)** • "
            f"**{total_students} allievi totali**"
        )

        # === Summary by stato ===
        stato_counts = {}
        for job in jobs:
            stato_counts[job['stato']] = \
                stato_counts.get(job['stato'], 0) + len(job['students'])

        st.markdown("### 📊 Riepilogo per Stato")
        summary_data = [
            {'Stato': stato, 'Allievi': count}
            for stato, count in stato_counts.items()
        ]
        st.dataframe(pd.DataFrame(summary_data),
                     hide_index=True, use_container_width=True)

        # === Each job in expander ===
        st.markdown("### 📋 Dettaglio per Edizione")
        for idx, job in enumerate(jobs):
            students = job['students']
            stato_icon = {
                'Completato': '✅',
                'Esente': '⚪',
                'Non passato': '❌'
            }.get(job['stato'], '📋')

            with st.expander(
                    f"{stato_icon} **{job['edition_code']}** — "
                    f"{len(students)} allievi → **{job['stato']}**",
                    expanded=(idx == 0)
            ):
                student_data = [{'#': i + 1, 'Numero Persona': s}
                                for i, s in enumerate(students)]
                st.dataframe(
                    pd.DataFrame(student_data),
                    hide_index=True,
                    use_container_width=True
                )

        st.divider()

        # === Time estimate ===
        avg_seconds_per_student = 12
        estimated_minutes = max(1, (total_students * avg_seconds_per_student) // 60)
        st.info(
            f"⏱️ **Tempo stimato:** ~{estimated_minutes} minuti "
            f"(~{avg_seconds_per_student}s per allievo). "
            f"Il tempo reale può variare in base alla velocità di Oracle."
        )

        col1, col2 = st.columns([2, 1])

        with col1:
            if st.button(
                    f"✅ Assegna Presenza — {total_students} allievi "
                    f"in {total_editions} edizioni",
                    type="primary",
                    use_container_width=True,
                    key="presenza_batch_confirm_btn"
            ):
                st.session_state.app_state = "RUNNING_BATCH_PRESENZA"
                st.session_state.presenza_message = ""
                st.session_state.presenza_show_batch_preview = False
                st.rerun()

        with col2:
            if st.button("❌ Annulla", use_container_width=True,
                         key="presenza_batch_cancel_btn"):
                st.session_state.presenza_batch_data = None
                st.session_state.presenza_show_batch_preview = False
                st.rerun()

    def _render_presenza_nlp(self, is_disabled: bool):
        """NLP input for presenza assignment."""
        st.info(
            "**Esempi di frasi accettate:**\n\n"
            '- "Edizione OLC466201 completato: 1168, 1189, 1199"\n'
            '- "Per edizione OLC466201 segna come completato i numeri 1168 1189"\n'
            '- "Assegna presenza edizione OLC466201 stato non passato allievi 1168 1199"',
            icon="💬"
        )

        if "presenza_nlp_text" not in st.session_state:
            st.session_state.presenza_nlp_text = ""

        nlp_text = st.text_area(
            "Descrivi l'assegnazione presenza:",
            height=150,
            key="presenza_nlp_text"
        )

        text_length = len(nlp_text.strip()) if nlp_text else 0
        if text_length > 0:
            st.caption(f"✏️ {text_length} caratteri inseriti")

        col1, col2 = st.columns([1, 1])

        with col1:
            if st.button("🤖 Analizza", type="primary", width='stretch',
                         key="presenza_nlp_analyze"):
                if not nlp_text.strip():
                    st.error("❌ Inserisci del testo.")
                    st.stop()

                parsed = self._parse_presenza_nlp(nlp_text)

                if parsed and parsed.get('edition_code') and parsed.get('students'):
                    st.session_state.presenza_data = parsed
                    st.session_state.presenza_show_summary = True
                    st.rerun()
                else:
                    st.error(
                        "❌ Non è stato possibile estrarre i dati.\n\n"
                        "Assicurati di includere:\n"
                        "- **Codice edizione** (es: OLC466201)\n"
                        "- **Numeri persona** allievi\n"
                        "- **Stato** (completato / non passato / esente)"
                    )

        with col2:
            if st.button("🧹 Cancella", width='stretch',
                         key="presenza_nlp_clear"):
                st.session_state.presenza_nlp_text = ""
                st.rerun()

    def _parse_presenza_nlp(self, text: str) -> 'Optional[Dict[str, Any]]':
        """
        Parse NLP input for presenza assignment.
        Extracts: edition_code, students list, stato.
        Uses pure regex — no spaCy needed for this simple structure.
        """
        import re

        result = {
            'edition_code': '',
            'students': [],
            'stato': 'Completato'  # default
        }

        # Extract edition code
        edition_patterns = [
            r"edizione\s+([A-Za-z0-9]+)",
            r'\b([A-Z]{2,5}\d{4,})\b',
            r'\b(\d{8,})\b',
        ]
        for pattern in edition_patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                result['edition_code'] = m.group(1).strip()
                break

        # Extract stato
        text_lower = text.lower()
        if 'non passato' in text_lower or 'non_passato' in text_lower:
            result['stato'] = 'Non passato'
        elif 'esente' in text_lower:
            result['stato'] = 'Esente'
        else:
            result['stato'] = 'Completato'  # default

        # Extract person numbers (3-7 digit numbers, exclude edition code)
        text_no_edition = text
        if result['edition_code']:
            text_no_edition = text_no_edition.replace(result['edition_code'], '')

        numbers = re.findall(r'\b(\d{3,7})\b', text_no_edition)
        seen = set()
        for n in numbers:
            if n not in seen:
                seen.add(n)
                result['students'].append(n)

        return result if result['edition_code'] and result['students'] else None

    def _render_presenza_preview(self, presenza_data: dict):
        """Preview screen before launching presenza automation."""

        edition_code = presenza_data.get('edition_code', '')
        students = presenza_data.get('students', [])
        stato = presenza_data.get('stato', 'Completato')

        st.success("✅ Dati pronti per l'assegnazione presenza")

        # Summary table
        st.markdown("### 📋 Riepilogo")
        summary_df = pd.DataFrame({
            'Campo': ['Codice Edizione', 'Stato Completamento', 'Numero Allievi'],
            'Valore': [edition_code, stato, str(len(students))]
        })
        st.dataframe(summary_df, hide_index=True, use_container_width=True)

        # Students list
        st.markdown("### 👥 Allievi")
        students_df = pd.DataFrame({
            '#': range(1, len(students) + 1),
            'Numero Persona': students
        })
        st.dataframe(students_df, hide_index=True, use_container_width=True)

        st.divider()

        col1, col2 = st.columns([2, 1])

        with col1:
            stato_color = {
                "Completato": "✅",
                "Esente": "⚪",
                "Non passato": "❌"
            }.get(stato, "📋")

            if st.button(
                    f"{stato_color} Assegna Presenza — {len(students)} allievi come '{stato}'",
                    type="primary", use_container_width=True,
                    key="presenza_confirm_btn"
            ):
                st.session_state.app_state = "RUNNING_PRESENZA"
                st.session_state.student_message = ""
                st.session_state.presenza_show_summary = False
                st.rerun()

        with col2:
            if st.button("❌ Annulla", use_container_width=True,
                         key="presenza_cancel_btn"):
                st.session_state.presenza_data = None
                st.session_state.presenza_show_summary = False
                st.rerun()

    def _clear_presenza_callback(self):
        """Clear all presenza form state."""
        st.session_state.presenza_data = None
        st.session_state.presenza_show_summary = False
        if "presenza_edition_code" in st.session_state:
            st.session_state.presenza_edition_code = ""
        if "presenza_students_text" in st.session_state:
            st.session_state.presenza_students_text = ""

    def _parse_student_nlp_input(self, text: str) -> 'Optional[Dict[str, Any]]':
        """
        Parse natural language input to extract edition code and student numero persona.

        SUPPORTED FORMATS:
        - "Aggiungi allievi 1168, 1189, 1199 all'edizione OLC466201"
        - "Edizione OLC466201: allievi 1168 1189 1199"
        - "OLC466201 numero persona 1168, 1189, 1199, 1216"
        - "Per edizione OLC466201 aggiungi 1168 1189 1199"

        Returns:
            Dictionary with edition_code and students list, or None if parsing fails
        """
        import re

        text_clean = text.strip()
        text_lower = text_clean.lower()

        parsed = {
            'edition_code': '',
            'students': []
        }

        # === STEP 1: Extract edition code ===
        # Look for a code pattern (letters + numbers, or just a long number)
        edition_patterns = [
            # "edizione OLC466201" or "all'edizione OLC466201"
            r"(?:all['\u2019]?)?edizione\s+([A-Za-z0-9]+)",
            # "codice OLC466201"
            r"codice\s+([A-Za-z0-9]+)",
            # Standalone alphanumeric code (like OLC466201) — at least 5 chars
            r'\b([A-Z]{2,5}\d{4,})\b',
            # Long numeric code (like 300000050460129) — at least 8 digits
            r'\b(\d{8,})\b',
        ]

        for pattern in edition_patterns:
            match = re.search(pattern, text_clean, re.IGNORECASE)
            if match:
                parsed['edition_code'] = match.group(1).strip()
                break

        # === STEP 2: Extract numero persona numbers ===
        # Strategy: find ALL numbers that are 3-7 digits (typical numero persona range)
        # but exclude the edition code itself

        # First, remove the edition code from text to avoid confusion
        text_for_numbers = text_clean
        if parsed['edition_code']:
            text_for_numbers = text_for_numbers.replace(parsed['edition_code'], '')

        # Find all numbers (3-7 digits = typical numero persona)
        all_numbers = re.findall(r'\b(\d{3,7})\b', text_for_numbers)

        # Deduplicate while preserving order
        seen = set()
        for num in all_numbers:
            if num not in seen:
                seen.add(num)
                parsed['students'].append(num)

        # === STEP 3: Validate results ===
        missing_fields = []

        if not parsed['edition_code']:
            missing_fields.append("Codice Edizione")

        if not parsed['students']:
            missing_fields.append("Numero Persona")

        if missing_fields:
            st.warning(f"⚠️ Campi mancanti: {', '.join(missing_fields)}")

            if parsed['edition_code']:
                st.write(f"- ✅ **Codice Edizione:** `{parsed['edition_code']}`")
            else:
                st.write("- ❌ **Codice Edizione:** non trovato")

            if parsed['students']:
                st.write(f"- ✅ **Allievi trovati:** {len(parsed['students'])} numero persona")
            else:
                st.write("- ❌ **Allievi:** nessuna numero persona trovata")

            # Return partial data if at least something was found
            if parsed['edition_code'] or parsed['students']:
                return parsed
            return None

        return parsed

    def _render_student_batch_preview(self, batch_data: 'Dict[str, Any]'):
        """
        Display preview of parsed student data (from Excel) with confirmation buttons.
        Supports multiple editions.
        """
        editions = batch_data.get('editions', [])
        total_editions = len(editions)
        total_students = batch_data.get('total_students', 0)

        st.subheader(f"📋 Anteprima: {total_editions} Edizioni, {total_students} Allievi")

        # Show each edition in an expander
        for idx, edition in enumerate(editions):
            students = edition.get('students', [])
            scadenza = edition.get('data_scadenza')
            with st.expander(
                    f"📚 Edizione {edition['edition_code']} — {len(students)} allievi",
                    expanded=(idx == 0)
            ):
                # Show the scadenza that will be used
                if scadenza:
                    st.info(f"📅 **Data scadenza:** {scadenza} (impostata dall'utente)")
                else:
                    st.caption("📅 Data scadenza: *domani* (predefinita — nessuna data specificata)")

                # Show students in a table
                student_data = [{'#': i + 1, 'Numero persona': s} for i, s in enumerate(students)]
                st.dataframe(
                    pd.DataFrame(student_data),
                    width='stretch',
                    hide_index=True,
                    column_config={
                        '#': st.column_config.NumberColumn('#', width='small'),
                        'Numero persona': st.column_config.TextColumn('Numero Persona', width='medium')
                    }
                )

        st.divider()


        # === ACTION BUTTONS ===
        # Verifica Allievi button removed from UI (colleagues check directly in
        # Oracle — faster). The verify code is kept but no longer exposed here.
        col1, col3 = st.columns([2, 1])

        with col1:
            btn_text = (
                f"✅ Aggiungi {total_students} Allievi a {total_editions} Edizioni"
                if total_editions > 1
                else f"✅ Aggiungi {total_students} Allievi"
            )

            if st.button(btn_text, type="primary", width='stretch', key="batch_student_confirm_btn"):
                # Store data for automation
                if total_editions == 1:
                    edition = editions[0]
                    st.session_state.student_details = {
                        "edition_code": edition['edition_code'],
                        "students": edition['students'],
                        "data_scadenza": edition.get('data_scadenza'),
                    }
                    st.session_state.app_state = "RUNNING_STUDENTS"
                else:
                    st.session_state.batch_student_data = {
                        'editions': editions,
                    }
                    st.session_state.app_state = "RUNNING_BATCH_STUDENTS"

                st.session_state.student_message = ""
                st.session_state.student_parsed_data = None
                st.session_state.student_show_summary = False
                st.rerun()

        # --- Verifica Allievi button removed from UI (kept in code, not shown) ---
        # with col2:
        #     verify_text = f"🔍 Verifica {total_students} Allievi"
        #     if st.button(verify_text, width='stretch', key="batch_student_verify_btn"):
        #         st.session_state.verify_student_data = {'editions': editions}
        #         st.session_state.app_state = "RUNNING_VERIFY_STUDENTS"
        #         st.session_state.student_message = ""
        #         st.session_state.student_parsed_data = None
        #         st.session_state.student_show_summary = False
        #         st.rerun()

        with col3:
            if st.button("❌ Annulla", width='stretch', key="batch_student_cancel_btn"):
                st.session_state.student_parsed_data = None
                st.session_state.student_show_summary = False
                st.session_state.student_input_method = "txt"
                st.rerun()

    def update_progress(self, form_type, message, percentage):
        # ── HEARTBEAT: prove this run is alive + record the current step.
        # Cheap local file write; keeps a long healthy batch from being
        # reclaimed, and records WHICH step is running for the busy page.
        try:
            automation_lock.heartbeat(step=message)
        except Exception:
            pass

        placeholder = None
        if form_type == "course":
            placeholder = getattr(self, 'course_output_placeholder', None)
        elif form_type == "edition":
            placeholder = getattr(self, 'edition_output_placeholder', None)
        elif form_type == "student":
            placeholder = getattr(self, 'student_output_placeholder', None)

        stamp = datetime.now().strftime("%H:%M:%S")

        if placeholder is not None:
            # placeholder.container() REPLACES content every call
            placeholder.empty()  # clear previous content first
            with placeholder.container():
                st.progress(percentage / 100)
                st.info(f"⏳ {message}")
                st.caption(
                    f"🫀 In corso (agg. {stamp}). Se un passo resta bloccato "
                    f"oltre ~8 min, l'automazione viene chiusa automaticamente "
                    f"e riceverai un messaggio. **Non ricaricare la pagina.**"
                )
        else:
            # Fallback — should not happen normally
            st.info(f"⏳ {message}")
            st.caption(f"🫀 In corso (agg. {stamp}). Non ricaricare la pagina.")

    def render_busy_page(self, holder: dict):
        """
        Shown to a user whose automation could NOT start because another
        session holds the VM-global lock. STATIC page (no auto-refresh) so it
        can never trigger a rerun that abandons a running automation. The user
        clicks the button to re-check when they want.
        """
        # Always apply theme so the busy page matches the app look
        try:
            self._apply_theme()
        except Exception:
            pass

        # Re-read freshest holder info
        try:
            fresh = automation_lock.current_holder()
        except Exception:
            fresh = None

        if fresh is None:
            st.success("✅ Il server è ora libero. Premi il pulsante per "
                       "avviare la tua operazione.")
            if st.button("🔄 Riprova ora"):
                st.rerun()
            return

        who = fresh.get("username", "un altro utente")
        op = fresh.get("operation", "Automazione")
        step = fresh.get("step", "")
        running = fresh.get("seconds_running", 0)
        since_hb = fresh.get("seconds_since_heartbeat", 0)
        is_stale = fresh.get("is_stale", False)

        def _fmt(sec):
            m, s = divmod(int(sec), 60)
            return f"{m} min {s} s" if m else f"{s} s"

        st.markdown("### ⏳ Server occupato — automazione in corso")
        st.info(
            f"👤 **{who}**  ·  operazione: **{op}**"
            + (f"  ·  passo: *{step}*" if step else "")
        )

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Attiva da", _fmt(running))
        with col2:
            st.metric("Ultimo progresso", f"{_fmt(since_hb)} fa")

        if is_stale:
            st.warning(
                "⚠️ L'automazione sembra bloccata (nessun progresso recente). "
                "Verrà liberata a breve. Premi il pulsante qui sotto per "
                "ricontrollare."
            )
        else:
            st.success("✅ L'automazione sta lavorando normalmente.")

        st.caption(
            "La tua richiesta partirà appena il server è libero. "
            "Premi il pulsante qui sotto per controllare se è libero."
        )

        st.markdown("---")
        if st.button("🔄 Controlla se il server è libero"):
            st.rerun()

    def show_message(self, form_type, message, show_clear_button=False):
        placeholder = None
        message_key = ""
        if form_type == "course":
            placeholder = getattr(self, 'course_output_placeholder', None)
            message_key = "course_message"
        elif form_type == "edition":
            placeholder = getattr(self, 'edition_output_placeholder', None)
            message_key = "edition_message"
        elif form_type == "student":
            placeholder = getattr(self, 'student_output_placeholder', None)
            message_key = "student_message"

        if not message_key:
            return

        st.session_state[message_key] = message

        # Use placeholder if available, otherwise show directly
        if placeholder is not None:
            with placeholder.container():
                if "✅" in message:
                    st.success(message)
                else:
                    st.error(message)
                if show_clear_button:
                    if st.button(f"🧹 Cancella Messaggio", key=f"clear_{form_type}"):
                        st.session_state[message_key] = ""
                        st.rerun()
        else:
            # Fallback: show directly without placeholder
            if "✅" in message:
                st.success(message)
            else:
                st.error(message)
            if show_clear_button:
                if st.button(f"🧹 Cancella Messaggio", key=f"clear_{form_type}"):
                    st.session_state[message_key] = ""
                    st.rerun()