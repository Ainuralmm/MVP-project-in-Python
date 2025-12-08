import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import spacy
from typing import Optional, Dict, Any


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

        # INITIALIZE SPACY MODEL #
        if "nlp_model" not in st.session_state:
            try:
                st.session_state.nlp_model = spacy.load("it_core_news_sm")  # Italian model
            except OSError:
                st.session_state.nlp_model = None  # Will show error in UI if not loaded

        # --- Message States: EDITION and STUDENTS ---
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

    # NEW HELPER METHOD - PARSE EXCEL FILE ###
    def _parse_excel_file(self, uploaded_file) -> Optional[Dict[str, Any]]:
        """
        Parse uploaded Excel file and extract course information.
        Expected Excel format:
        - Row 1: TITOLO | [Course Title]
        - Row 2: DESCRIZIONE | [Short Description]
        - Row 3: DATA INIZIO | [DD/MM/YYYY]

        Returns: Dictionary with parsed data or None if parsing fails
        """
        try:
            # Read Excel file
            df = pd.read_excel(uploaded_file, header=None)

            # Extract data from specific cells (assuming structure shown in excel image)
            # Column A contains labels (TITOLO, DESCRIZIONE, DATA INIZIO)
            # Column B contains values (EXCEL, INFORMATICA, 01/01/23)

            parsed_data = {}

            # EXTRACT TITLE (Row 1, Column B) ###
            if len(df) > 0 and len(df.columns) > 1:
                parsed_data['title'] = str(df.iloc[0, 1]).strip() if pd.notna(df.iloc[0, 1]) else ""

            # EXTRACT SHORT DESCRIPTION (Row 2, Column B) ###
            if len(df) > 1 and len(df.columns) > 1:
                parsed_data['short_description'] = str(df.iloc[1, 1]).strip() if pd.notna(df.iloc[1, 1]) else ""

            # EXTRACT DATE (Row 3, Column B) ###
            if len(df) > 2 and len(df.columns) > 1:
                date_value = df.iloc[2, 1]

                # Handle different date formats
                if pd.notna(date_value):
                    if isinstance(date_value, datetime):
                        parsed_data['start_date'] = date_value.strftime("%d/%m/%Y")
                    else:
                        # Try to parse as string
                        date_str = str(date_value).strip()
                        # Handle both DD/MM/YY and DD/MM/YYYY formats
                        try:
                            parsed_date = datetime.strptime(date_str, "%d/%m/%y")
                        except ValueError:
                            try:
                                parsed_date = datetime.strptime(date_str, "%d/%m/%Y")
                            except ValueError:
                                parsed_date = None

                        if parsed_date:
                            parsed_data['start_date'] = parsed_date.strftime("%d/%m/%Y")

            # PROGRAMME FIELD IS OPTIONAL - SET EMPTY ###
            parsed_data['programme'] = ""

            # Validate that required fields are present
            if not all([parsed_data.get('title'), parsed_data.get('short_description'), parsed_data.get('start_date')]):
                return None

            return parsed_data

        except Exception as e:
            st.error(f"Errore durante la lettura del file Excel: {str(e)}")
            return None

    # NEW HELPER METHOD - PARSE NLP INPUT
    def _parse_nlp_input(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Parse natural language input to extract course information.
        Expected format: "Create a course titled [X] with description [Y] starting on [date]"

        Returns: Dictionary with parsed data or None if parsing fails
        """
        if not st.session_state.nlp_model:
            st.error("Modello NLP non caricato. Installa spacy con: python -m spacy download it_core_news_sm")
            return None

        try:
            doc = st.session_state.nlp_model(text)

            parsed_data = {
                'title': "",
                'short_description': "",
                'start_date': "",
                'programme': ""
            }

            # ### HASHTAG: EXTRACT TITLE - LOOK FOR QUOTED TEXT OR PROPER NOUNS ###
            # Simple pattern: text between "titolo" and keywords like "con", "e", "che"
            text_lower = text.lower()

            # Pattern 1: Look for "titolo [X]"
            if "titolo" in text_lower:
                start_idx = text_lower.find("titolo") + 6
                # Find end markers
                end_markers = [" con ", " e ", " che ", " descrizione", " data"]
                end_idx = len(text)
                for marker in end_markers:
                    marker_idx = text_lower.find(marker, start_idx)
                    if marker_idx != -1 and marker_idx < end_idx:
                        end_idx = marker_idx

                parsed_data['title'] = text[start_idx:end_idx].strip().strip('"').strip("'")

            # EXTRACT DESCRIPTION
            if "descrizione" in text_lower:
                start_idx = text_lower.find("descrizione") + 11
                end_markers = [" data", " inizio", " dal ", " a partire"]
                end_idx = len(text)
                for marker in end_markers:
                    marker_idx = text_lower.find(marker, start_idx)
                    if marker_idx != -1 and marker_idx < end_idx:
                        end_idx = marker_idx

                parsed_data['short_description'] = text[start_idx:end_idx].strip().strip('"').strip("'")

            # EXTRACT DATE - LOOK FOR DATE PATTERNS ###
            # Look for dates in format DD/MM/YYYY or DD/MM/YY
            import re
            date_pattern = r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b'
            date_matches = re.findall(date_pattern, text)

            if date_matches:
                date_str = date_matches[0].replace('-', '/')
                # Normalize to DD/MM/YYYY format
                try:
                    parsed_date = datetime.strptime(date_str, "%d/%m/%y")
                    parsed_data['start_date'] = parsed_date.strftime("%d/%m/%Y")
                except ValueError:
                    try:
                        parsed_date = datetime.strptime(date_str, "%d/%m/%Y")
                        parsed_data['start_date'] = parsed_date.strftime("%d/%m/%Y")
                    except ValueError:
                        pass

            # Validate that required fields are present
            if not all([parsed_data.get('title'), parsed_data.get('short_description'), parsed_data.get('start_date')]):
                return None

            return parsed_data

        except Exception as e:
            st.error(f"Errore durante l'analisi NLP: {str(e)}")
            return None

    # ### HASHTAG: ADD CALLBACK TO UPDATE STATE WHEN TEXT CHANGES ###
    def _update_nlp_text():
        """Callback to ensure text is captured in session state"""
        pass  # The key parameter automatically updates session state

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

    # NEW HELPER METHOD - DISPLAY SUMMARY WITH EDIT/CONFIRM
    def _render_course_summary(self):
        """
        Display parsed course data in a summary format with Edit/Confirm buttons.
        """
        if not st.session_state.course_parsed_data:
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

        # ### HASHTAG: SHOW SUMMARY IF DATA IS PARSED ###
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
            st.info("""
            **Formato Excel Richiesto:**
            - **Riga 1:** TITOLO | [Nome del Corso]
            - **Riga 2:** DESCRIZIONE | [Breve Descrizione]
            - **Riga 3:** DATA INIZIO | [GG/MM/AAAA]

            Le etichette devono essere nella Colonna A, i valori nella Colonna B.
            """, icon="ℹ️")

            uploaded_file = st.file_uploader(
                "Carica File Excel (.xlsx, .xls)",
                type=['xlsx', 'xls'],
                help="Il file deve seguire il formato specificato sopra"
            )

            if uploaded_file is not None:
                col1, col2 = st.columns([1, 1])

                with col1:
                    if st.button("📊 Analizza File Excel", type="primary", use_container_width=True):
                        # ### HASHTAG: PARSE EXCEL AND SHOW SUMMARY ###
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
            st.info("""
            **Scrivi una frase che descriva il corso**, ad esempio:

            - "Crea un corso titolo Analisi dei Dati con descrizione Informatica avanzata data inizio 01/01/2023"
            - "Nuovo corso Excel Base, descrizione breve: Gestione fogli di calcolo, pubblicazione 01/01/2023"

            Il sistema estrarrà automaticamente le informazioni rilevanti.
            """, icon="💡")

            nlp_text = st.text_area(
                "Descrivi il corso in linguaggio naturale:",
                height=150,
                placeholder="Esempio: Crea un corso dal titolo 'Python Avanzato' con descrizione 'Programmazione orientata agli oggetti' che inizia il 20/05/2024",
                key="course_nlp_input",
                on_change=self._update_nlp_text
            )

            col1, col2 = st.columns([1, 1])

            with col1:
                if st.button("🤖 Analizza Testo (NLP)", type="primary", use_container_width=True,
                             disabled=not nlp_text.strip()):
                    # ### HASHTAG: PARSE NLP INPUT AND SHOW SUMMARY ###
                    parsed_data = self._parse_nlp_input(nlp_text)

                    if parsed_data:
                        st.session_state.course_parsed_data = parsed_data
                        st.session_state.course_show_summary = True
                        st.rerun()
                    else:
                        st.error(
                            "❌ Impossibile estrarre abbastanza informazioni dal testo. Assicurati di includere: titolo, descrizione e data.")

            with col2:
                if st.button("🧹 Cancella Testo", use_container_width=True):
                    st.session_state.course_nlp_input = ""
                    st.rerun()

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