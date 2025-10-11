import streamlit as st
from datetime import datetime

class CourseView:
    def __init__(self):
        st.set_page_config(layout='centered')
        ### HASHTAG: CENTRALIZED STATE INITIALIZATION
        # All state variables are now initialized cleanly in one place using isolated keys.
        if "app_state" not in st.session_state:
            st.session_state.app_state = "IDLE"  # Can be: IDLE, RUNNING_COURSE, RUNNING_EDITION
        if "course_message" not in st.session_state:
            st.session_state.course_message = ""
        if "edition_message" not in st.session_state:
            st.session_state.edition_message = ""

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

        ### HASHTAG: NEW UNIFIED RENDER METHOD
        # This single method controls the entire UI. It decides whether to show a form
        # or a progress bar based on the central `app_state`.

    def render_ui(self):
        is_running = st.session_state.app_state != "IDLE"

        # --- Course Form Container ---
        with st.container(border=True):
            st.header("1. Creazione Nuovo Corso")
            if st.session_state.app_state == "RUNNING_COURSE":
                # If this process is running, show its progress bar here
                self.course_output_placeholder = st.empty()
            else:
                # Otherwise, show the form and its persistent message
                self._render_course_form(is_disabled=is_running)
                self.course_output_placeholder = st.empty()
                if st.session_state.course_message:
                    self.show_message("course", st.session_state.course_message, show_clear_button=True)

        # --- Edition Form Container ---
        with st.container(border=True):
            st.header("2. Creazione Nuova Edizione")
            if st.session_state.app_state == "RUNNING_EDITION":
                self.edition_output_placeholder = st.empty()
            else:
                self._render_edition_form(is_disabled=is_running)
                self.edition_output_placeholder = st.empty()
                if st.session_state.edition_message:
                    self.show_message("edition", st.session_state.edition_message, show_clear_button=True)

    def _render_course_form(self, is_disabled):
        with st.form(key='course_form'):
            # These are the input fields for the user.
            course_title = st.text_input("Titolo del Corso",
                                         value="",
                                         placeholder="Esempio: Analisi dei Dati",
                                         key="input_title",
                                         )
            programme = st.text_area(
                "Dettagli del Programma",
                value="",
                placeholder="Campo opzionale: informazioni importanti sul corso",
                key="input_programme",
            )
            short_desc = st.text_input(
                "Breve Descrizione",
                value="",
                placeholder="Esempio: Analisi dei Dati Informatica",
                key="input_short_desc",

            )

            # Custom date input in Italian format
            date_str = st.text_input("Data di Pubblicazione (GG/MM/AAAA)", "01/01/2023")

            try:
                start_date = datetime.strptime(date_str, "%d/%m/%Y").date()
                date_valid = True
                # st.success(f"📅 Data selezionata: {start_date.strftime('%d/%m/%Y')}")
            except ValueError:
                start_date = None
                date_valid = False

            submitted = st.form_submit_button("Crea Corso", type="primary", disabled=is_disabled)

            if submitted:
                if not course_title.strip() or not short_desc.strip():
                    st.error("I campi 'Titolo' e 'Breve Descrizione' sono obbligatori.")
                    return
                try:
                    start_date = datetime.strptime(date_str, "%d/%m/%Y").date()
                    st.session_state.course_details = {
                        "title": course_title, "short_description": short_desc,
                        "start_date": start_date, "programme": "Test Programme"
                    }
                    st.session_state.app_state = "RUNNING_COURSE"
                    st.session_state.course_message = ""  # Clear old message
                    st.rerun()
                except ValueError:
                    st.error("Formato data non valido. Usa GG/MM/AAAA.")

    def _render_edition_form(self, is_disabled):
        with st.form(key='edition_form'):
            course_name = st.text_input("Nome Corso Esistente", "TEST AUTOMAZIONE")
            start_date_str = st.text_input("Data Inizio Edizione (GG/MM/AAAA)", "10/10/2025")
            duration_days = st.number_input("Durata (giorni)", min_value=1, value=1)
            submitted = st.form_submit_button("Crea Edizione", type="primary", disabled=is_disabled)

            if submitted:
                if not course_name.strip():
                    st.error("Il campo 'Nome Corso Esistente' è obbligatorio.")
                    return
                try:
                    edition_start = datetime.strptime(start_date_str, "%d/%m/%Y").date()
                    st.session_state.edition_details = {
                        "course_name": course_name, "edition_start_date": edition_start,
                        "duration_days": int(duration_days), "location": "SEDE01",
                        "supplier": "FORNITORE01", "price": "100"
                    }
                    st.session_state.app_state = "RUNNING_EDITION"
                    st.session_state.edition_message = ""  # Clear old message
                    st.rerun()
                except ValueError:
                    st.error("Formato data non valido. Usa GG/MM/AAAA.")

        ### HASHTAG: DECOUPLED METHODS FOR PRESENTER
        # The presenter will call these methods to update the UI without
        # needing to know about st.progress or st.success.

    def update_progress(self, form_type, message, percentage):
        placeholder = self.course_output_placeholder if form_type == "course" else self.edition_output_placeholder
        with placeholder.container():
            st.info(f"⏳ {message}")
            st.progress(percentage)

    def show_message(self, form_type, message, show_clear_button=False):
        # Determine which placeholder and session_state key to use
        placeholder = self.course_output_placeholder if form_type == "course" else self.edition_output_placeholder
        message_key = "course_message" if form_type == "course" else "edition_message"

        st.session_state[message_key] = message

        with placeholder.container():
            if "✅" in message:
                st.success(message)
            else:
                st.error(message)

            if show_clear_button:
                if st.button(f"🧹 Cancella Messaggio", key=f"clear_{form_type}"):
                    st.session_state[message_key] = ""
                    st.rerun()