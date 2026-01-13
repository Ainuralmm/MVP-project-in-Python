import streamlit as st
from datetime import datetime, date, timedelta
import pandas as pd
import spacy
from typing import Optional, Dict, Any, Tuple, List

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
        st.set_page_config(layout='centered')
        # --- Basic App State ---
        if "app_state" not in st.session_state:
            st.session_state.app_state = "IDLE"

        # --- Message States: COURSE ---
        if "course_message" not in st.session_state:
            st.session_state.course_message = ""
        # NEW STATE VARIABLES FOR COURSE INPUT METHOD
        if "course_input_method" not in st.session_state:
            st.session_state.course_input_method = "structured"  # Options: "structured", "excel", "nlp"

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
        #add clear flag
        if "nlp_clear_requested" not in st.session_state:
            st.session_state.nlp_clear_requested = False

        # INITIALIZE SPACY MODEL
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
        if "student_convocazione_presenza" not in st.session_state:
            st.session_state.student_convocazione_presenza = True

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

        if "student_convocazione_online" not in st.session_state:
            st.session_state.student_convocazione_online = True
        if "student_convocazione_presenza" not in st.session_state:
            st.session_state.student_convocazione_presenza = True

        st.image("logo-agsm.jpg", width=200)
        st.title("Automatore per la Gestione dei Corsi Oracle")

    def _update_nlp_text(self):
        """
        Callback function for NLP text area.
        Streamlit automatically updates session_state when key is used.
        """
        # ### HASHTAG: CALLBACK TO ENSURE TEXT AREA UPDATES ARE CAPTURED ###
        pass  # No action needed, key parameter handles state update

    # NEW METHOD - CLEAR NLP INPUT SAFELY
    def _clear_nlp_input_callback(self):
        """
        Safely clear NLP input and ALL related states.

        WHY: When user clicks "clear", we must reset:
        - The text input itself
        - Any parsed data from previous analysis
        - The summary display flag
        - The clear request flag

        This ensures a clean slate for the next analysis.
        """
        #COMPREHENSIVE STATE RESET
        st.session_state.nlp_clear_requested = True
        st.session_state.course_parsed_data = None
        st.session_state.course_show_summary = False

        # OPTIONAL - ADD DEBUG LOG
        # Uncomment this to debug state issues:
        print("DEBUG: NLP cleared - all states reset")

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

    def render_ui(self):
        is_running = st.session_state.app_state != "IDLE"

        # Create three tabs
        tab1, tab2, tab3 = st.tabs([
            "1. Creazione Corso",
            "2. Creazione Edizione + Attività",
            "3. Aggiungi Allievi"
        ])

        # --- Tab1:Course Form Container ---
        with tab1:
            st.header("Creazione Nuovo Corso")
            if st.session_state.app_state == "RUNNING_COURSE":
                self.course_output_placeholder = st.empty()
            else:
                self._render_course_form(is_disabled=is_running)
                self.course_output_placeholder = st.empty()
                if st.session_state.course_message:
                    self.show_message("course", st.session_state.course_message, show_clear_button=True)

        # --- Tab2: Combined Edition + Activity Form Container ---
        with tab2:
            st.header("Creazione Nuova Edizione + Attività")
            if st.session_state.app_state == "RUNNING_EDITION":
                self.edition_output_placeholder = st.empty()
            else:
                self._render_edition_form(is_disabled=is_running)
                self.edition_output_placeholder = st.empty()
                if st.session_state.edition_message:
                    self.show_message("edition", st.session_state.edition_message, show_clear_button=True)

        # --- Tab3:Student Form Container ---
        with tab3:
            st.header("Aggiungi Allievi (a Edizione Esistente)")
            if st.session_state.app_state == "RUNNING_STUDENTS":
                self.student_output_placeholder = st.empty()
            else:
                self._render_student_form(is_disabled=is_running)
                self.student_output_placeholder = st.empty()
                if st.session_state.student_message:
                    self.show_message("student", st.session_state.student_message, True)

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

    def _render_batch_course_preview(self, batch_data: Dict[str, Any], course):
        """
        Display preview table of all courses from Excel with selection options.

        WHY: Users need to review and optionally select which courses to create.
        Prevents accidental bulk creation and allows quality control.

        Args:
            batch_data: Dictionary from _parse_excel_file() with 'courses' list
        """
        if not batch_data or 'courses' not in batch_data:
            return

        st.success(f"✅ {batch_data['total_count']} corsi pronti per la creazione!")

        if batch_data.get('skipped_count', 0) > 0:
            st.info(f"ℹ️ {batch_data['skipped_count']} righe saltate (dati incompleti)")

        st.subheader("📋 Anteprima Corsi da Creare")

        # ### HASHTAG: FORMAT DATE FOR DISPLAY ###
        # Convert date object to string for preview table
        date_display = course['start_date']
        if isinstance(date_display, (datetime, date)):
            date_display = date_display.strftime("%d/%m/%Y")
        elif isinstance(date_display, str):
            # Already a string, use as-is
            pass
        else:
            # Unknown type, try to convert
            date_display = str(date_display)

        # ### HASHTAG: CREATE PREVIEW DATAFRAME ###
        preview_data = []
        for idx, course in enumerate(batch_data['courses']):
            preview_data.append({
                '#': idx + 1,
                'Titolo': course['title'],
                'Descrizione': course['short_description'],
                'Data Pubblicazione': date_display,
                'Riga Excel': course.get('row_number', '-')
            })

        preview_df = pd.DataFrame(preview_data)

        # ### HASHTAG: DISPLAY AS INTERACTIVE TABLE ###
        st.dataframe(
            preview_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                '#': st.column_config.NumberColumn('#', width='small'),
                'Titolo': st.column_config.TextColumn('Titolo', width='medium'),
                'Descrizione': st.column_config.TextColumn('Descrizione', width='large'),
                'Data Pubblicazione': st.column_config.TextColumn('Data', width='small'),
                'Riga Excel': st.column_config.NumberColumn('Riga', width='small')
            }
        )

        # ### HASHTAG: SELECTION OPTIONS ###
        st.divider()

        with st.form(key='batch_course_confirmation_form'):
            st.subheader("⚙️ Opzioni di Creazione")

            # ### HASHTAG: OPTION TO SELECT SPECIFIC COURSES (FUTURE ENHANCEMENT) ###
            create_all = st.checkbox(
                f"Crea tutti i {len(batch_data['courses'])} corsi",
                value=True,
                help="Deseleziona per scegliere singolarmente"
            )

            if not create_all:
                st.info("🚧 Selezione individuale - Funzionalità in sviluppo")
                st.write("Per ora, puoi creare tutti i corsi o annullare.")

            # ### HASHTAG: PROCESSING OPTIONS ###
            st.write("**Comportamento in caso di errore:**")
            continue_on_error = st.checkbox(
                "Continua anche se un corso fallisce",
                value=True,
                help="Se deselezionato, si ferma al primo errore"
            )

            col1, col2, col3 = st.columns([2, 1, 1])

            with col1:
                confirm = st.form_submit_button(
                    f"✅ Conferma e Crea {len(batch_data['courses'])} Corsi",
                    type="primary",
                    use_container_width=True
                )

            with col2:
                edit = st.form_submit_button(
                    "✏️ Modifica File",
                    use_container_width=True
                )

            with col3:
                cancel = st.form_submit_button(
                    "❌ Annulla",
                    use_container_width=True
                )

        # ### HASHTAG: HANDLE USER ACTIONS ###
        if confirm:
            # ### HASHTAG: CONVERT STRING DATES TO DATE OBJECTS ###
            # This is the FIX for  datetime error
            for course in batch_data['courses']:
                # Convert string date to datetime object
                date_str = course['start_date']  # e.g., "01/01/2023"
                try:
                    # Option 2: One-liner
                    date_obj = date_str if isinstance(date_str, date) else datetime.strptime(date_str,"%d/%m/%Y").date()
                    course['start_date'] = date_obj  # Replace string with object
                except ValueError as e:
                    st.error(f"❌ Errore conversione data per '{course['title']}': {date_str}")
                    st.stop()

            # Store data for batch processing
            st.session_state.batch_course_data = batch_data
            st.session_state.batch_continue_on_error = continue_on_error
            st.session_state.app_state = "RUNNING_BATCH_COURSE"
            st.session_state.course_message = ""
            st.rerun()

        elif edit:
            # Go back to file upload
            st.session_state.course_parsed_data = None
            st.session_state.course_show_summary = False
            st.rerun()

        elif cancel:
            # Reset everything
            st.session_state.course_parsed_data = None
            st.session_state.course_show_summary = False
            st.session_state.course_input_method = "structured"
            st.rerun()

        # NEW HELPER METHOD - PARSE EXCEL FILE FOR BATCH (VERTICAL FORMAT)

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
        ENHANCED VERSION: Parse natural language input with maximum robustness.

        IMPROVEMENTS:
        1. Safe text extraction (handles normalization)
        2. Italian month name support
        3. Two-digit year handling
        4. spaCy Matcher for word order flexibility
        5. Partial extraction (returns what was found + missing fields)
        6. Centralized date normalization
        """
        if not st.session_state.nlp_model:
            st.error("Modello NLP non caricato. Installa spacy con: python -m spacy download it_core_news_sm")
            return None

        try:
            import re

            parsed_data = {
                'title': "",
                'short_description': "",
                'start_date': "",
                'programme': ""
            }

            # STEP 1 - NORMALIZE TEXT SAFELY ###
            original_text = text
            normalized_text = ' '.join(text.split())  # Remove extra whitespace
            text_lower = normalized_text.lower()

            # STEP 2 - TRY SPACY MATCHER FIRST (MOST ROBUST) ###
            try:
                spacy_results = extract_with_spacy_matcher(normalized_text, st.session_state.nlp_model)
                if spacy_results['title']:
                    parsed_data['title'] = spacy_results['title']
                if spacy_results['description']:
                    parsed_data['short_description'] = spacy_results['description']
                if spacy_results['date']:
                    # Use centralized date normalizer
                    normalized_date = normalize_date(spacy_results['date'])
                    if normalized_date:
                        parsed_data['start_date'] = normalized_date
            except Exception as spacy_error:
                # If spaCy fails, fall back to regex
                st.warning(f"spaCy Matcher fallback attivo: {spacy_error}")

            # STEP 3 - REGEX FALLBACK WITH SAFE EXTRACTION ###
            # Only fill in missing fields from Step 2

            if not parsed_data['title']:
                title_patterns = [
                    r'titolo\s*:?\s*([^,]+?)(?:\s*,|\s*$)',
                    r'corso\s+([^,]+?)(?:\s*,|\s*con\s+descrizione|\s*descrizione|\s*$)',
                ]

                for pattern in title_patterns:
                    match = re.search(pattern, text_lower, re.IGNORECASE)
                    if match:
                        # ### HASHTAG: USE SAFE EXTRACTION ###
                        extracted = safe_extract_text(
                            original_text,
                            text_lower,
                            match.start(1),
                            match.end(1)
                        )
                        if extracted:
                            parsed_data['title'] = extracted
                            break

            if not parsed_data['short_description']:
                desc_patterns = [
                    r'descrizione\s*:?\s*([^,]+?)(?:\s*,|\s*$)',
                    r'descrizione\s+breve\s*:?\s*([^,]+?)(?:\s*,|\s*$)',
                ]

                for pattern in desc_patterns:
                    match = re.search(pattern, text_lower, re.IGNORECASE)
                    if match:
                        extracted = safe_extract_text(
                            original_text,
                            text_lower,
                            match.start(1),
                            match.end(1)
                        )
                        if extracted:
                            parsed_data['short_description'] = extracted
                            break

            # ### HASHTAG: STEP 4 - DATE EXTRACTION WITH MULTIPLE STRATEGIES ###
            if not parsed_data['start_date']:
                # Strategy 1: Try Italian month names (e.g., "12 gennaio 2024")
                italian_date = parse_italian_date(normalized_text)
                if italian_date:
                    parsed_data['start_date'] = italian_date
                else:
                    # Strategy 2: Numeric date patterns
                    date_patterns = [
                        r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{4})\b',  # DD/MM/YYYY
                        r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2})\b',  # DD/MM/YY
                    ]

                    for pattern in date_patterns:
                        match = re.search(pattern, normalized_text)
                        if match:
                            raw_date = match.group(1)
                            # ### HASHTAG: USE CENTRALIZED NORMALIZER ###
                            normalized_date = normalize_date(raw_date)
                            if normalized_date:
                                parsed_data['start_date'] = normalized_date
                                break

            # ### HASHTAG: STEP 5 - PARTIAL EXTRACTION SUPPORT ###
            # Instead of returning None, we return partial results + missing fields
            missing_fields = []
            if not parsed_data.get('title') or not parsed_data['title'].strip():
                missing_fields.append("Titolo")
            if not parsed_data.get('short_description') or not parsed_data['short_description'].strip():
                missing_fields.append("Descrizione")
            if not parsed_data.get('start_date') or not parsed_data['start_date'].strip():
                missing_fields.append("Data")

            # ### HASHTAG: SHOW PARTIAL RESULTS (BETTER UX) ###
            if missing_fields:
                st.warning(f"⚠️ Campi mancanti: {', '.join(missing_fields)}")

                # Show what WAS extracted
                extracted_count = sum([
                    bool(parsed_data.get('title', '').strip()),
                    bool(parsed_data.get('short_description', '').strip()),
                    bool(parsed_data.get('start_date', '').strip())
                ])

                if extracted_count > 0:
                    st.success(f"✅ Estratti {extracted_count}/3 campi con successo!")
                    st.info("**Dati estratti finora:**")

                    if parsed_data.get('title') and parsed_data['title'].strip():
                        st.write(f"- ✅ **Titolo:** `{parsed_data['title']}`")
                    else:
                        st.write(f"- ❌ **Titolo:** non trovato")

                    if parsed_data.get('short_description') and parsed_data['short_description'].strip():
                        st.write(f"- ✅ **Descrizione:** `{parsed_data['short_description']}`")
                    else:
                        st.write(f"- ❌ **Descrizione:** non trovata")

                    if parsed_data.get('start_date') and parsed_data['start_date'].strip():
                        st.write(f"- ✅ **Data:** `{parsed_data['start_date']}`")
                    else:
                        st.write(f"- ❌ **Data:** non trovata")

                    # ### HASHTAG: OFFER TO PROCEED WITH PARTIAL DATA ###
                    st.info(
                        "💡 **Suggerimento:** Puoi comunque procedere. I campi mancanti potranno essere inseriti manualmente nel riepilogo.")

                    # ### HASHTAG: RETURN PARTIAL DATA INSTEAD OF None ###
                    # This allows the summary form to pre-fill what was found
                    return parsed_data  # Return even if incomplete!
                else:
                    # Nothing was extracted at all
                    return None

            # ### HASHTAG: ALL FIELDS SUCCESSFULLY EXTRACTED ###
            return parsed_data

        except Exception as e:
            st.error(f"Errore durante l'analisi NLP: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
            return None

    def _clear_edition_activity_form_callback(self):
        st.session_state.edition_course_name_key = ""
        st.session_state.edition_title_key = ""
        st.session_state.edition_start_date_str_key = ""
        st.session_state.edition_end_date_str_key = ""
        st.session_state.edition_description_key = ""
        st.session_state.edition_location_key = ""
        st.session_state.edition_supplier_key = ""
        st.session_state.edition_price_key = ""
        st.session_state.num_activities = 1

        # Clear ALL activity fields AND preserved data
        st.session_state.preserved_activity_data = {}
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

    def _clear_edition_nlp_callback(self):
        """Clear NLP input for edition"""
        st.session_state.edition_nlp_clear_requested = True
        st.session_state.edition_parsed_data = None
        st.session_state.edition_show_summary = False
        print("DEBUG: Edition NLP cleared")

    def _clear_student_form_callback(self):
        st.session_state.student_course_name_key = ""
        st.session_state.student_edition_name_key = ""
        st.session_state.student_edition_publish_date_key = ""
        st.session_state.num_students = 1
        st.session_state.student_convocazione_online = True
        st.session_state.student_convocazione_presenza = True

        # Clear ALL student fields AND preserved data
        st.session_state.preserved_student_data = {}
        for i in range(50):
            if f"student_name_{i}" in st.session_state:
                st.session_state[f"student_name_{i}"] = ""

    # NEW HELPER METHOD - DISPLAY SUMMARY WITH EDIT/CONFIRM
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
                "Dettagli del Programma (opzionale)",
                value=st.session_state.course_parsed_data.get('programme', ''),
                key="summary_programme"
            )

            col1, col2, col3 = st.columns([2, 1, 1])

            with col1:
                confirm = st.form_submit_button("✅ Conferma e Crea Corso", type="primary", use_container_width=True)

            with col2:
                edit = st.form_submit_button("✏️ Modifica", use_container_width=True)

            with col3:
                cancel = st.form_submit_button("❌ Annulla", use_container_width=True)

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
                course_title = st.text_input("Titolo del Corso", placeholder="Esempio: Analisi dei Dati",
                                             key="course_title_key")
                programme = st.text_area("Dettagli del Programma", placeholder="Campo opzionale...",
                                         key="course_programme_key")
                short_desc = st.text_input("Breve Descrizione", placeholder="Esempio: Analisi dei Dati - Informatica",
                                           key="course_short_desc_key")
                date_str = st.text_input("Data di Pubblicazione (GG/MM/AAAA)", key="course_date_str_key")

                col1, col2 = st.columns([3, 1])
                with col1:
                    submitted = st.form_submit_button("Crea Corso", type="primary", disabled=is_disabled,
                                                      use_container_width=True)
                with col2:
                    st.form_submit_button("Pulisci 🧹", use_container_width=True,
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
                    if st.button("📊 Analizza File Excel", type="primary", use_container_width=True):
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
                    if st.button("🧹 Cancella File", use_container_width=True):
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

            - "Crea un corso titolo Analisi dei Dati con descrizione Informatica avanzata data inizio 15/03/2024"

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
                st.warning("⚠️ Inserisci del testo per abilitare l'analisi", icon="⚠️")

            col1, col2 = st.columns([1, 1])

            with col1:
                analyze_clicked = st.button(
                    "🤖 Analizza Testo (NLP)",
                    type="primary",
                    use_container_width=True,
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
                if st.button("🧹 Cancella Testo", use_container_width=True,
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
                return self._parse_two_sheet_format(excel_file)

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
                'description': ['descrizione', 'desc']
            }

            # Column mappings for activities
            activity_mappings = {
                'edition_id': ['id_edizione', 'edizione_id', 'id'],
                'title': ['titolo_attivita', 'titolo del attivita', 'titolo'],
                'description': ['descrizione', 'descrizione per elen', 'desc'],
                'date': ['data_attivita', "data attivita'", 'data'],
                'start_time': ['ora_inizio', 'ora inizio'],
                'end_time': ['ora_fine', 'ora fine'],
                'hours': ['impegno_ore', 'impegno in ore', 'ore']
            }

            # Find actual column names
            def find_column(df, possible_names):
                for name in possible_names:
                    if name in df.columns:
                        return name
                return None

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
                    'course_name': str(course_name).strip(),
                    'edition_title': str(row[edition_cols['title']]).strip() if edition_cols['title'] and pd.notna(
                        row[edition_cols['title']]) else '',
                    'start_date': start_date_str,
                    'end_date': end_date_str,
                    'location': str(row[edition_cols['location']]).strip() if edition_cols['location'] and pd.notna(
                        row[edition_cols['location']]) else '',
                    'supplier': str(row[edition_cols['supplier']]).strip() if edition_cols['supplier'] and pd.notna(
                        row[edition_cols['supplier']]) else '',
                    'price': str(row[edition_cols['price']]).strip() if edition_cols['price'] and pd.notna(
                        row[edition_cols['price']]) else '',
                    'description': str(row[edition_cols['description']]).strip() if edition_cols[
                                                                                        'description'] and pd.notna(
                        row[edition_cols['description']]) else '',
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

            return {
                'editions': editions_list,
                'total_editions': len(editions_list),
                'total_activities': sum(len(e['activities']) for e in editions_list),
                'file_name': excel_file.io.name if hasattr(excel_file.io, 'name') else 'Excel'
            }

        except Exception as e:
            st.error(f"❌ Errore parsing: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
            return None

    def _parse_edition_nlp_input(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Parse natural language input to extract edition and activities.

        Example input:
        "Crea edizione per corso Data Science01 titolo Winter Edition
         data inizio 12/02/2026 data fine 20/02/2026
         aula Aula de carli fornitore Aeit costo 1000
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
            'activities': []
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

        # Extract activities
        # Pattern: "primo giorno 12/02/2026 ore 09.00-11.00" or similar
        activity_section = re.search(r'attività[:\s]+(.+)', text_lower, re.DOTALL)
        if activity_section:
            activity_text = activity_section.group(1)

            # Find individual activities
            activity_patterns = [
                r'(\w+\s+giorno)\s+(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})\s+(?:ore\s+)?(\d{1,2}[.:]\d{2})\s*[-–]\s*(\d{1,2}[.:]\d{2})',
                r'(giorno\s+\d+|day\s+\d+)\s+(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})\s+(?:ore\s+)?(\d{1,2}[.:]\d{2})\s*[-–]\s*(\d{1,2}[.:]\d{2})',
            ]

            for pattern in activity_patterns:
                matches = re.findall(pattern, activity_text)
                for match in matches:
                    title, date_str, start_time, end_time = match
                    parsed['activities'].append({
                        'title': title.strip().title(),
                        'description': '',
                        'date': normalize_date(date_str) or '',
                        'start_time': start_time.replace(':', '.'),
                        'end_time': end_time.replace(':', '.'),
                        'impegno_ore': ''
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

    def _render_edition_form(self, is_disabled):
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

        # Restore data BEFORE rendering the form
        if st.session_state.preserved_activity_data:
            self._restore_activity_data(st.session_state.num_activities)

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
            st.text_input("Titolo Edizione (opzionale)",
                          placeholder="Lascia vuoto per usare il nome predefinito...",
                          key="edition_title_key")
            st.text_input("Data Inizio Edizione (GG/MM/AAAA)", key="edition_start_date_str_key")
            st.text_input("Data Fine Edizione (GG/MM/AAAA)", key="edition_end_date_str_key")
            st.text_area("Descrizione Edizione (opzionale)", placeholder="Descrizione...",
                         key="edition_description_key")
            st.text_area("Aula Principale (opzionale)", placeholder="Esempio: AULA DE CARLI",
                         key="edition_location_key")
            st.text_area("Nome Fornitore Formazione (opzionale)", placeholder="Esempio: AEIT",
                         key="edition_supplier_key")
            st.text_input("Prezzo Edizione (€) (opzionale)", placeholder="Esempio: 1000",
                          key="edition_price_key")

            st.divider()
            st.subheader("Dettagli Attività")

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

                st.text_area(f"Descrizione Attività", key=f"activity_desc_{i}", height=100)
                st.text_input(f"Impegno previsto in ore", key=f"impegno_previsto_in_ore_{i}")
                st.markdown("---")

            col1, col2 = st.columns([3, 1])
            with col1:
                submitted = st.form_submit_button("Crea Edizione e Attività", type="primary",
                                                  disabled=is_disabled, use_container_width=True)
            with col2:
                st.form_submit_button("Pulisci 🧹", use_container_width=True,
                                      on_click=self._clear_edition_activity_form_callback)

        if submitted:
            self._process_structured_edition_submission(num_activities)

    def _render_edition_nlp_ui(self, is_disabled):
        """UI for natural language input for edition + activities"""

        st.info("""
        **Scrivi una frase che descriva l'edizione e le attività**, ad esempio:

        "Crea edizione per corso Data Science01 titolo Winter Edition
        data inizio 12/02/2026 data fine 20/02/2026
        aula Aula de carli fornitore Aeit costo 1000
        attività: primo giorno 12/02/2026 ore 09.00-11.00,
        secondo giorno 13/02/2026 ore 10.00-12.00"

        Oppure più semplice:
        "Edizione per corso Python Base dal 15/03/2026 al 17/03/2026, 3 giorni di attività"
        """, icon="💡")

        # Handle clear request
        if st.session_state.get('edition_nlp_clear_requested', False):
            st.session_state.edition_nlp_input = ""
            st.session_state.edition_nlp_clear_requested = False
            st.rerun()

        nlp_text = st.text_area(
            "Descrivi l'edizione in linguaggio naturale:",
            height=200,
            value=st.session_state.edition_nlp_input,
            placeholder="Crea edizione per corso [nome corso] data inizio [data] data fine [data]...",
            help="Scrivi una frase completa con i dettagli dell'edizione e delle attività",
            key="edition_nlp_text_area"
        )

        # Update session state
        st.session_state.edition_nlp_input = nlp_text

        # Show character count
        text_length = len(nlp_text.strip()) if nlp_text else 0
        if text_length > 0:
            st.caption(f"✏️ {text_length} caratteri inseriti")
        else:
            st.warning("⚠️ Inserisci del testo per abilitare l'analisi", icon="⚠️")

        col1, col2 = st.columns([1, 1])

        with col1:
            if st.button("🤖 Analizza Testo (NLP)", type="primary", use_container_width=True,
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
            if st.button("🧹 Cancella Testo", use_container_width=True,
                         on_click=self._clear_edition_nlp_callback,
                         key="clear_edition_nlp_btn"):
                pass

    def _process_structured_edition_submission(self, num_activities):
        """Process the structured form submission"""
        # PRESERVE DATA BEFORE PROCESSING
        self._preserve_activity_data(num_activities)

        course_name = st.session_state.edition_course_name_key
        edition_title = st.session_state.edition_title_key
        start_date_str = st.session_state.edition_start_date_str_key
        end_date_str = st.session_state.edition_end_date_str_key
        description = st.session_state.edition_description_key
        location = st.session_state.edition_location_key
        supplier = st.session_state.edition_supplier_key
        price = st.session_state.edition_price_key

        if not all([course_name.strip(), start_date_str.strip(), end_date_str.strip()]):
            st.error("I campi 'Nome Corso', 'Data Inizio Edizione' e 'Data Fine Edizione' sono obbligatori.")
            st.stop()

        try:
            edition_start = datetime.strptime(start_date_str, "%d/%m/%Y").date()
            edition_end = datetime.strptime(end_date_str, "%d/%m/%Y").date()

            if edition_end < edition_start:
                st.error("La data di fine edizione non può essere precedente alla data di inizio.")
                st.stop()

            activities_list = []
            for i in range(num_activities):
                title = st.session_state.get(f"activity_title_{i}", "")
                act_desc = st.session_state.get(f"activity_desc_{i}", "")
                act_date_str = st.session_state.get(f"activity_date_{i}", "")
                start_time = st.session_state.get(f"activity_start_time_{i}", "09.00")
                end_time = st.session_state.get(f"activity_end_time_{i}", "11.00")
                impegno_previsto_in_ore = st.session_state.get(f"impegno_previsto_in_ore_{i}", "")

                if not all([title.strip(), act_desc.strip(), act_date_str.strip()]):
                    st.error(f"Titolo, Descrizione e Data sono obbligatori per l'attività del Giorno {i + 1}.")
                    st.stop()

                act_date = datetime.strptime(act_date_str, "%d/%m/%Y").date()
                datetime.strptime(start_time, "%H.%M")
                datetime.strptime(end_time, "%H.%M")

                if act_date < edition_start or act_date > edition_end:
                    st.error(
                        f"La data dell'attività (Giorno {i + 1}: {act_date_str}) deve essere compresa tra l'inizio ({start_date_str}) e la fine ({end_date_str}) dell'edizione.")
                    st.stop()

                activities_list.append({
                    "title": title,
                    "description": act_desc,
                    "date": act_date,
                    "start_time": start_time,
                    "end_time": end_time,
                    "impegno_previsto_in_ore": impegno_previsto_in_ore
                })

        except ValueError:
            st.error("Formato data o ora non valido. Usa GG/MM/AAAA e HH.MM (con il punto).")
            st.stop()

        st.session_state.edition_details = {
            "course_name": course_name,
            "edition_title": edition_title,
            "edition_start_date": edition_start,
            "edition_end_date": edition_end,
            "location": location,
            "supplier": supplier,
            "price": price,
            "description": description,
            "activities": activities_list
        }
        st.session_state.app_state = "RUNNING_EDITION"
        st.session_state.edition_message = ""
        st.rerun()

    def _preserve_student_data(self, num_students):
        """Preserve current student data before form submission"""
        # CRITICAL: Also preserve the count itself
        st.session_state.preserved_student_data["_count"] = num_students

        for i in range(num_students):
            st.session_state.preserved_student_data[f"student_{i}_name"] = \
                st.session_state.get(f"student_name_{i}", "")

    def _render_edition_excel_ui(self, is_disabled):
        """UI for Excel file upload for edition + activities"""

        st.info("""
        **Formato Excel Supportato:**

        **Opzione 1 - Due fogli separati:**
        - Foglio "Edizioni": ID_EDIZIONE, NOME_CORSO, TITOLO, DATA_INIZIO, DATA_FINE, AULA, FORNITORE, COSTO
        - Foglio "Attivita": ID_EDIZIONE, TITOLO, DESCRIZIONE, DATA, ORA_INIZIO, ORA_FINE, IMPEGNO_ORE

        **Opzione 2 - Foglio singolo con marcatori:**
        - Colonna TIPO: "EDIZIONE" o "ATTIVITA" per ogni riga

        **Opzione 3 - Formato originale:**
        - Intestazione edizione → dati edizione → intestazione attività → dati attività
        """, icon="ℹ️")

        uploaded_file = st.file_uploader(
            "Carica File Excel (.xlsx, .xls)",
            type=['xlsx', 'xls'],
            help="File con edizione e attività",
            key="edition_excel_uploader"
        )

        if uploaded_file is not None:
            col1, col2 = st.columns([1, 1])

            with col1:
                if st.button("📊 Analizza File Excel", type="primary", use_container_width=True,
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
                if st.button("🧹 Cancella File", use_container_width=True, key="clear_edition_excel_btn"):
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
        """Preview for a single edition with activities"""

        st.success("✅ Dati estratti con successo!")
        st.subheader("📋 Anteprima Edizione + Attività")

        # Edition details card
        st.markdown("### 📚 Dettagli Edizione")

        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Corso:** {edition_data.get('course_name', '-')}")
            st.write(f"**Titolo Edizione:** {edition_data.get('edition_title', '-') or 'Default (nome corso + data)'}")
            st.write(f"**Data Inizio:** {edition_data.get('start_date', '-')}")
            st.write(f"**Data Fine:** {edition_data.get('end_date', '-')}")
        with col2:
            st.write(f"**Aula:** {edition_data.get('location', '-') or 'Non specificata'}")
            st.write(f"**Fornitore:** {edition_data.get('supplier', '-') or 'Non specificato'}")
            st.write(f"**Costo:** €{edition_data.get('price', '-') or '0'}")
            if edition_data.get('description'):
                st.write(f"**Descrizione:** {edition_data.get('description', '')}")

        # Activities table
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
                    'Impegno (ore)': act.get('impegno_ore', '') or act.get('impegno_previsto_in_ore', '')
                })

            activities_df = pd.DataFrame(activities_preview)
            st.dataframe(activities_df, use_container_width=True, hide_index=True)
        else:
            st.warning("⚠️ Nessuna attività trovata. Aggiungi attività nella modalità Modifica.")

        st.divider()

        # Action buttons (NO FORM - regular buttons)
        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            if st.button("✅ Conferma e Crea Edizione", type="primary", use_container_width=True,
                         key="edition_preview_confirm_btn"):
                self._start_edition_creation(edition_data)

        with col2:
            if st.button("✏️ Modifica", use_container_width=True, key="edition_preview_edit_btn"):
                st.session_state.edition_edit_mode = True
                st.session_state.edition_to_edit = edition_data.copy()
                st.session_state.edition_show_summary = False
                st.rerun()

        with col3:
            if st.button("❌ Annulla", use_container_width=True, key="edition_preview_cancel_btn"):
                st.session_state.edition_parsed_data = None
                st.session_state.edition_show_summary = False
                st.session_state.edition_input_method = "structured"
                st.rerun()

    def _render_multiple_editions_preview(self, data: Dict[str, Any]):
        """Preview for multiple editions from Excel"""

        editions = data.get('editions', [])

        st.success(f"✅ {len(editions)} edizioni trovate con {data.get('total_activities', 0)} attività totali!")

        st.subheader("📋 Anteprima Edizioni")

        # Show each edition
        for idx, edition in enumerate(editions):
            with st.expander(
                    f"📚 Edizione {idx + 1}: {edition.get('course_name', '')} - {edition.get('edition_title', 'Default')}",
                    expanded=(idx == 0)):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Corso:** {edition.get('course_name', '-')}")
                    st.write(f"**Titolo:** {edition.get('edition_title', '-') or 'Default'}")
                    st.write(f"**Date:** {edition.get('start_date', '-')} → {edition.get('end_date', '-')}")
                with col2:
                    st.write(f"**Aula:** {edition.get('location', '-') or 'N/A'}")
                    st.write(f"**Fornitore:** {edition.get('supplier', '-') or 'N/A'}")
                    st.write(f"**Costo:** €{edition.get('price', '0')}")

                # Activities for this edition
                activities = edition.get('activities', [])
                if activities:
                    st.markdown("**Attività:**")
                    act_df = pd.DataFrame([{
                        '#': i + 1,
                        'Titolo': a.get('title', ''),
                        'Data': a.get('date', ''),
                        'Orario': f"{a.get('start_time', '')} - {a.get('end_time', '')}"
                    } for i, a in enumerate(activities)])
                    st.dataframe(act_df, use_container_width=True, hide_index=True)
                else:
                    st.warning("⚠️ Nessuna attività per questa edizione")

        st.divider()

        st.info(
            "ℹ️ **Nota:** Le edizioni verranno create una alla volta. Questo processo potrebbe richiedere alcuni minuti.")

        # For now, only support creating first edition (batch would need presenter changes)
        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            if st.button(f"✅ Crea Prima Edizione ({editions[0].get('course_name', '')})",
                         type="primary", use_container_width=True, key="edition_multi_confirm_btn"):
                # Create only the first edition
                self._start_edition_creation(editions[0])

        with col2:
            if st.button("✏️ Modifica Prima", use_container_width=True, key="edition_multi_edit_btn"):
                st.session_state.edition_edit_mode = True
                st.session_state.edition_to_edit = editions[0].copy()
                st.session_state.edition_show_summary = False
                st.rerun()

        with col3:
            if st.button("❌ Annulla", use_container_width=True, key="edition_multi_cancel_btn"):
                st.session_state.edition_parsed_data = None
                st.session_state.edition_show_summary = False
                st.session_state.edition_input_method = "structured"
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
                'activities': activities_list
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

    def _render_student_form(self, is_disabled):
        # Restore data BEFORE rendering the form
        if st.session_state.preserved_student_data:
            self._restore_student_data(st.session_state.num_students)

        num_students = st.number_input(
            "Quanti allievi da aggiungere?",
            min_value=1,
            max_value=50,
            key="num_students"
        )

        with st.form(key='student_form'):
            st.subheader("1. Trova Edizione Esistente")
            st.text_input("Nome del Corso Esistente",
                          placeholder="Corso a cui appartiene l'edizione",
                          key="student_course_name_key")
            st.text_input("Nome Esatto Edizione",
                          placeholder="Inserisci il nome esatto e completo dell'edizione (non troncato)",
                          key="student_edition_name_key")
            st.text_input("Data Pubblicazione Edizione (GG/MM/AAAA)",
                          placeholder="La 'Publish Start Date' dell'edizione",
                          key="student_edition_publish_date_key")

            st.divider()
            st.subheader("2. Dettagli Allievi")
            st.info(
                "**Importante:** Per trovare l'allievo corretto, il metodo più sicuro è "
                "inserire **Numero di matricola** (es. **2413**). "
                "Inserire solo il nome o l'email può causare errori se esistono duplicati.",
                icon="💡"
            )

            for i in range(num_students):
                st.text_input(f"Numero di matricola {i + 1}", key=f"student_name_{i}")

            st.divider()
            st.subheader("3. Opzioni Convocazione")
            st.checkbox("Invia Convocazione Online", key="student_convocazione_online")
            st.checkbox("Invia Convocazione Presenza", key="student_convocazione_presenza")

            col1, col2 = st.columns([3, 1])
            with col1:
                submitted = st.form_submit_button("Aggiungi Allievi", type="primary",
                                                  disabled=is_disabled, use_container_width=True)
            with col2:
                st.form_submit_button("Pulisci 🧹", use_container_width=True,
                                      on_click=self._clear_student_form_callback)

        if submitted:
            # PRESERVE DATA BEFORE PROCESSING
            self._preserve_student_data(num_students)

            course_name = st.session_state.student_course_name_key
            edition_name = st.session_state.student_edition_name_key
            edition_publish_date_str = st.session_state.student_edition_publish_date_key
            conv_online = st.session_state.student_convocazione_online
            conv_presenza = st.session_state.student_convocazione_presenza

            if not all([course_name.strip(), edition_name.strip(), edition_publish_date_str.strip()]):
                st.error("I campi 'Nome Corso', 'Nome Edizione' e 'Data Pubblicazione' sono obbligatori.")
                st.stop()

            if not conv_online and not conv_presenza:
                st.error("Selezionare almeno un tipo di convocazione (Online o Presenza).")
                st.stop()

            try:
                edition_publish_date = datetime.strptime(edition_publish_date_str, "%d/%m/%Y").date()
            except ValueError:
                st.error("Formato Data Pubblicazione Edizione non valido. Usa GG/MM/AAAA.")
                st.stop()

            student_list = []
            all_students_valid = True
            for i in range(num_students):
                name = st.session_state.get(f"student_name_{i}", "").strip()
                if not name:
                    st.error(f"Il nome per l'Allievo {i + 1} è obbligatorio.")
                    all_students_valid = False
                    break
                student_list.append(name)

            if not all_students_valid:
                st.stop()

            st.session_state.student_details = {
                "course_name": course_name,
                "edition_name": edition_name,
                "edition_publish_date": edition_publish_date,
                "students": student_list,
                "convocazione_online": conv_online,
                "convocazione_presenza": conv_presenza
            }
            st.session_state.app_state = "RUNNING_STUDENTS"
            st.session_state.student_message = ""
            st.rerun()

    def update_progress(self, form_type, message, percentage):
        placeholder = None
        if form_type == "course":
            placeholder = self.course_output_placeholder
        elif form_type == "edition":
            placeholder = self.edition_output_placeholder
        elif form_type == "student":
            placeholder = self.student_output_placeholder

        if placeholder and hasattr(self, f"{form_type}_output_placeholder"):
            with placeholder.container():
                st.info(f"⏳ {message}")
                st.progress(percentage)

    def show_message(self, form_type, message, show_clear_button=False):
        placeholder = None
        message_key = ""
        if form_type == "course":
            placeholder = self.course_output_placeholder
            message_key = "course_message"
        elif form_type == "edition":
            placeholder = self.edition_output_placeholder
            message_key = "edition_message"
        elif form_type == "student":
            placeholder = self.student_output_placeholder
            message_key = "student_message"

        if not placeholder or not message_key:
            return

        st.session_state[message_key] = message
        if placeholder and hasattr(self, f"{form_type}_output_placeholder"):
            with placeholder.container():
                if "✅" in message:
                    st.success(message)
                else:
                    st.error(message)
                if show_clear_button:
                    if st.button(f"🧹 Cancella Messaggio", key=f"clear_{form_type}"):
                        st.session_state[message_key] = ""
                        st.rerun()