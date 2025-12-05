import streamlit as st
from datetime import datetime
import pandas as pd # pandas: To read Excel files
import spacy # spacy: For NLP sentence parsing
from dateutil import parser as date_parser # dateutil.parser: For flexible date parsing from text
import re # re: For regex pattern matching in sentences


class CourseView:
    def __init__(self):
        st.set_page_config(layout='centered')

        ### HASHTAG: NEW - Load spaCy model for NLP ###
        # This loads the Italian language model for better parsing
        # Install with: python -m spacy download it_core_news_sm
        try:
            self.nlp = spacy.load("it_core_news_sm")
        except:
            st.warning("⚠️ Modello spaCy italiano non trovato. Installa con: python -m spacy download it_core_news_sm")
            self.nlp = None

        # --- Basic App State ---
        if "app_state" not in st.session_state:
            st.session_state.app_state = "IDLE"

        ### HASHTAG: NEW - Input method selection state ###
        # Tracks which input method the user selected (structured/excel/nlp)
        if "course_input_method" not in st.session_state:
            st.session_state.course_input_method = "structured"

        ### HASHTAG: NEW - Parsed data from Excel/NLP ###
        # Stores the extracted data before confirmation
        if "course_parsed_data" not in st.session_state:
            st.session_state.course_parsed_data = None

        # --- Message States ---
        if "course_message" not in st.session_state:
            st.session_state.course_message = ""
        if "edition_message" not in st.session_state:
            st.session_state.edition_message = ""
        if "student_message" not in st.session_state:
            st.session_state.student_message = ""

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

    ### HASHTAG: NEW METHOD - Parse Excel file for course data ###
    def _parse_excel_course(self, uploaded_file):
        """
        Extracts course data from uploaded Excel file.
        Expected format: Column A = field names (TITOLO, DESCRIZIONE, etc.)
                        Column B = values (EXCEL, INFORMATICA, etc.)
        Returns: dict with parsed course data or None if parsing fails
        """
        try:
            # Read Excel file into DataFrame
            df = pd.read_excel(uploaded_file, header=None)

            # Initialize result dictionary
            parsed = {
                "title": "",
                "programme": "",
                "short_description": "",
                "start_date": None
            }

            # Iterate through rows to find matching fields
            for idx, row in df.iterrows():
                if len(row) < 2:
                    continue

                field_name = str(row[0]).strip().upper() if pd.notna(row[0]) else ""
                field_value = str(row[1]).strip() if pd.notna(row[1]) else ""

                # Map Excel fields to our structure
                if "TITOLO" in field_name:
                    parsed["title"] = field_value
                elif "DESCRIZIONE" in field_name or "DESCRIZIONE" in field_name:
                    parsed["short_description"] = field_value
                elif "PROGRAMMA" in field_name:
                    parsed["programme"] = field_value
                elif "DATA" in field_name and "INIZIO" in field_name:
                    # Parse date from various formats
                    try:
                        if "/" in field_value or "-" in field_value:
                            parsed["start_date"] = datetime.strptime(field_value, "%d/%m/%y").date()
                        else:
                            parsed["start_date"] = date_parser.parse(field_value, dayfirst=True).date()
                    except:
                        st.warning(f"⚠️ Impossibile interpretare la data: {field_value}")

            # Validate that we got at least the required fields
            if not parsed["title"] or not parsed["start_date"]:
                st.error("❌ Il file Excel deve contenere almeno TITOLO e DATA INIZIO")
                return None

            return parsed

        except Exception as e:
            st.error(f"❌ Errore nella lettura del file Excel: {str(e)}")
            return None

    ### HASHTAG: NEW METHOD - Parse natural language sentence for course data ###
    def _parse_nlp_course(self, sentence):
        """
        Extracts course data from natural language sentence using spaCy.
        Example: "Crea un corso di computer vision, descrizione breve informatica, data pubblicazione 1.1.2023"
        Returns: dict with parsed course data or None if parsing fails
        """
        try:
            if not self.nlp:
                st.error("❌ Modello NLP non disponibile")
                return None

            # Initialize result
            parsed = {
                "title": "",
                "programme": "",
                "short_description": "",
                "start_date": None
            }

            # Clean the sentence
            sentence = sentence.strip()

            # Extract title using patterns
            # Pattern 1: "corso di X" or "corso X"
            title_patterns = [
                r"corso\s+(?:di\s+)?([^,\.]+?)(?:\s*,|\s+descrizione|\s+data|\s*$)",
                r"(?:crea|creare)\s+(?:un\s+)?(?:corso\s+)?(?:di\s+)?([^,\.]+?)(?:\s*,|\s+descrizione|\s+data)"
            ]
            for pattern in title_patterns:
                match = re.search(pattern, sentence, re.IGNORECASE)
                if match:
                    parsed["title"] = match.group(1).strip()
                    break

            # Extract short description
            # Pattern: "descrizione [breve] X" or "breve descrizione X"
            desc_patterns = [
                r"(?:descrizione\s+(?:breve\s+)?|breve\s+descrizione\s+)(?:è\s+)?['\"]?([^,\.\"']+)['\"]?",
                r"descrizione[:\s]+['\"]?([^,\.\"']+)['\"]?"
            ]
            for pattern in desc_patterns:
                match = re.search(pattern, sentence, re.IGNORECASE)
                if match:
                    parsed["short_description"] = match.group(1).strip()
                    break

            # Extract date
            # Pattern: various date formats
            date_patterns = [
                r"data\s+(?:di\s+)?pubblicazione[:\s]+(\d{1,2}[\/\.\-]\d{1,2}[\/\.\-]\d{2,4})",
                r"pubblicazione[:\s]+(\d{1,2}[\/\.\-]\d{1,2}[\/\.\-]\d{2,4})",
                r"(\d{1,2}[\/\.\-]\d{1,2}[\/\.\-]\d{2,4})"
            ]
            for pattern in date_patterns:
                match = re.search(pattern, sentence, re.IGNORECASE)
                if match:
                    date_str = match.group(1)
                    try:
                        # Try different date formats
                        for fmt in ["%d/%m/%Y", "%d.%m.%Y", "%d-%m-%Y", "%d/%m/%y"]:
                            try:
                                parsed["start_date"] = datetime.strptime(date_str, fmt).date()
                                break
                            except:
                                continue
                        if not parsed["start_date"]:
                            parsed["start_date"] = date_parser.parse(date_str, dayfirst=True).date()
                    except:
                        pass
                    break

            # Validate minimum required fields
            if not parsed["title"]:
                st.error("❌ Non riesco a identificare il titolo del corso nella frase")
                return None

            if not parsed["start_date"]:
                st.warning("⚠️ Non riesco a identificare la data. Usa formato GG/MM/AAAA")
                return None

            return parsed

        except Exception as e:
            st.error(f"❌ Errore nell'analisi della frase: {str(e)}")
            return None

    def render_ui(self):
        is_running = st.session_state.app_state != "IDLE"

        # Create three tabs
        tab1, tab2, tab3 = st.tabs([
            "1. Creazione Corso",
            "2. Creazione Edizione + Attività",
            "3. Aggiungi Allievi"
        ])

        # --- Tab1: Course Form Container ---
        with tab1:
            st.header("Creazione Nuovo Corso")

            ### HASHTAG: NEW - Input method selector ###
            # Radio buttons to choose between 3 input methods
            if st.session_state.app_state == "IDLE":
                st.subheader("📋 Scegli il metodo di inserimento dati:")
                input_method = st.radio(
                    "Metodo",
                    options=["structured", "excel", "nlp"],
                    format_func=lambda x: {
                        "structured": "✍️ Compilazione Manuale (Form Strutturato)",
                        "excel": "📊 Carica File Excel",
                        "nlp": "💬 Scrivi una Frase"
                    }[x],
                    key="course_input_method",
                    horizontal=False
                )

            if st.session_state.app_state == "RUNNING_COURSE":
                self.course_output_placeholder = st.empty()
            else:
                ### HASHTAG: NEW - Render different UIs based on input method ###
                if st.session_state.course_input_method == "structured":
                    self._render_course_form(is_disabled=is_running)
                elif st.session_state.course_input_method == "excel":
                    self._render_course_excel_upload(is_disabled=is_running)
                elif st.session_state.course_input_method == "nlp":
                    self._render_course_nlp_input(is_disabled=is_running)

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

        # --- Tab3: Student Form Container ---
        with tab3:
            st.header("Aggiungi Allievi (a Edizione Esistente)")
            if st.session_state.app_state == "RUNNING_STUDENTS":
                self.student_output_placeholder = st.empty()
            else:
                self._render_student_form(is_disabled=is_running)
                self.student_output_placeholder = st.empty()
                if st.session_state.student_message:
                    self.show_message("student", st.session_state.student_message, True)

    ### HASHTAG: NEW METHOD - Render Excel upload UI ###
    def _render_course_excel_upload(self, is_disabled):
        """
        Renders the Excel file upload interface for course creation.
        Shows upload widget -> Parse button -> Confirmation UI
        """
        st.markdown("---")
        st.subheader("📊 Carica File Excel")
        st.info("Il file deve contenere i campi: TITOLO, DESCRIZIONE INFORMATICA, DATA INIZIO (formato: GG/MM/AA)")

        uploaded_file = st.file_uploader(
            "Seleziona file Excel (.xlsx, .xls)",
            type=["xlsx", "xls"],
            key="course_excel_file",
            disabled=is_disabled
        )

        col1, col2 = st.columns([1, 3])
        with col1:
            parse_button = st.button("📖 Leggi File", disabled=not uploaded_file or is_disabled, type="primary")
        with col2:
            if st.button("🧹 Cancella", disabled=is_disabled):
                st.session_state.course_parsed_data = None
                st.rerun()

        ### HASHTAG: Parse Excel when button clicked ###
        if parse_button and uploaded_file:
            parsed_data = self._parse_excel_course(uploaded_file)
            if parsed_data:
                st.session_state.course_parsed_data = parsed_data
                st.success("✅ File letto con successo!")
                st.rerun()

        ### HASHTAG: Show parsed data for confirmation ###
        if st.session_state.course_parsed_data:
            self._render_course_confirmation_ui(st.session_state.course_parsed_data, is_disabled)

    ### HASHTAG: NEW METHOD - Render NLP sentence input UI ###
    def _render_course_nlp_input(self, is_disabled):
        """
        Renders the natural language input interface for course creation.
        Shows text area -> Parse button -> Confirmation UI
        """
        st.markdown("---")
        st.subheader("💬 Scrivi una Frase")
        st.info(
            'Esempio: "Crea un corso di computer vision, descrizione breve informatica, data pubblicazione 1.1.2023"')

        sentence = st.text_area(
            "Inserisci la descrizione del corso:",
            height=100,
            key="course_nlp_sentence",
            disabled=is_disabled,
            placeholder="Scrivi qui la frase che descrive il corso da creare..."
        )

        col1, col2 = st.columns([1, 3])
        with col1:
            parse_button = st.button("🤖 Analizza Frase", disabled=not sentence or is_disabled, type="primary")
        with col2:
            if st.button("🧹 Cancella", disabled=is_disabled):
                st.session_state.course_parsed_data = None
                st.rerun()

        ### HASHTAG: Parse sentence when button clicked ###
        if parse_button and sentence:
            with st.spinner("🤔 Analisi in corso..."):
                parsed_data = self._parse_nlp_course(sentence)
                if parsed_data:
                    st.session_state.course_parsed_data = parsed_data
                    st.success("✅ Frase analizzata con successo!")
                    st.rerun()

        ### HASHTAG: Show parsed data for confirmation ###
        if st.session_state.course_parsed_data:
            self._render_course_confirmation_ui(st.session_state.course_parsed_data, is_disabled)

    ### HASHTAG: NEW METHOD - Render confirmation UI with Edit/Confirm buttons ###
    def _render_course_confirmation_ui(self, parsed_data, is_disabled):
        """
        Shows the parsed data in an editable form with Edit/Confirm buttons.
        This is the common UI for both Excel and NLP methods.
        """
        st.markdown("---")
        st.subheader("📝 Dati Estratti - Verifica e Conferma")

        with st.form(key="course_confirmation_form"):
            st.markdown("**Puoi modificare i dati prima di confermare:**")

            title = st.text_input(
                "Titolo del Corso",
                value=parsed_data.get("title", ""),
                key="parsed_title"
            )

            programme = st.text_area(
                "Programma (opzionale)",
                value=parsed_data.get("programme", ""),
                key="parsed_programme"
            )

            short_desc = st.text_input(
                "Breve Descrizione",
                value=parsed_data.get("short_description", ""),
                key="parsed_short_desc"
            )

            date_value = parsed_data.get("start_date")
            date_str = date_value.strftime("%d/%m/%Y") if date_value else ""

            publication_date = st.text_input(
                "Data di Pubblicazione (GG/MM/AAAA)",
                value=date_str,
                key="parsed_date"
            )

            col1, col2 = st.columns(2)
            with col1:
                confirm_button = st.form_submit_button("✅ Conferma e Crea Corso", type="primary", disabled=is_disabled,
                                                       use_container_width=True)
            with col2:
                cancel_button = st.form_submit_button("❌ Annulla", use_container_width=True)

        ### HASHTAG: Handle confirmation ###
        if confirm_button:
            # Validate fields
            if not title.strip():
                st.error("❌ Il titolo è obbligatorio")
                st.stop()
            if not short_desc.strip():
                st.error("❌ La descrizione breve è obbligatoria")
                st.stop()
            if not publication_date.strip():
                st.error("❌ La data di pubblicazione è obbligatoria")
                st.stop()

            try:
                start_date_obj = datetime.strptime(publication_date, "%d/%m/%Y").date()

                # Store in session state for automation
                st.session_state.course_details = {
                    "title": title,
                    "programme": programme,
                    "short_description": short_desc,
                    "start_date": start_date_obj
                }
                st.session_state.app_state = "RUNNING_COURSE"
                st.session_state.course_message = ""
                st.session_state.course_parsed_data = None  # Clear parsed data
                st.rerun()
            except ValueError:
                st.error("❌ Formato data non valido. Usa GG/MM/AAAA")
                st.stop()

        ### HASHTAG: Handle cancellation ###
        if cancel_button:
            st.session_state.course_parsed_data = None
            st.rerun()

    def _clear_course_form_callback(self):
        st.session_state.course_title_key = ""
        st.session_state.course_programme_key = ""
        st.session_state.course_short_desc_key = ""
        st.session_state.course_date_str_key = "01/01/2023"

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

    def _render_course_form(self, is_disabled):
        """Original structured form - unchanged from your code"""
        with st.form(key='course_form'):
            course_title = st.text_input("Titolo del Corso", placeholder="Esempio: Analisi dei Dati",
                                         key="course_title_key")
            programme = st.text_area("Dettagli del Programma", placeholder="Campo opzionale...",
                                     key="course_programme_key")
            short_desc = st.text_input("Breve Descrizione", placeholder="Esempio: Analisi dei Dati Informatica",
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

    def _preserve_activity_data(self, num_activities):
        """Preserve current activity data before form submission"""
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