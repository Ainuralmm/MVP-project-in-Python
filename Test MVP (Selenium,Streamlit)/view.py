# view.py
import streamlit as st
from datetime import datetime


class CourseView:
    def __init__(self):
        self.course_output_placeholder = None
        st.set_page_config(layout='centered')
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

    def render_ui(self):
        is_running = st.session_state.app_state != "IDLE"

        # --- Course Form Container ---
        with st.container(border=True):
            st.header("1. Creazione Nuovo Corso")
            if st.session_state.app_state == "RUNNING_COURSE":
                self.course_output_placeholder = st.empty()
            else:
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
            course_title = st.text_input("Titolo del Corso", placeholder="Esempio: Analisi dei Dati")
            programme = st.text_area("Dettagli del Programma", placeholder="Campo opzionale...")
            short_desc = st.text_input("Breve Descrizione", placeholder="Esempio: Analisi dei Dati Informatica")
            date_str = st.text_input("Data di Pubblicazione (GG/MM/AAAA)", "01/01/2023")

            submitted = st.form_submit_button("Crea Corso", type="primary", disabled=is_disabled)

            ### HASHTAG: CORRECTED INDENTATION AND LOGIC
            # This entire 'if submitted' block has been moved inside the `_render_course_form`
            # method and the `with st.form(...)` block, where it belongs.
            # It now uses the correct `app_state` logic.
            if submitted:
                # to show a red warning directly under the field that is missing.
                missing = False

                if not course_title.strip():
                    st.markdown("<span style ='color:red'> "
                                "⚠️ Il campo 'Titolo corso' è obbligatorio. Si prega di compilarlo </span>",
                                unsafe_allow_html=True)
                    missing = True
                if not short_desc.strip():
                    st.markdown("<span style ='color:red'> "
                                "⚠️ Il campo 'Breve Descrizione' è obbligatorio. Si prega di compilarlo",
                                unsafe_allow_html=True)
                    missing = True
                if not date_str.strip():
                    st.markdown("<span style ='color:red'> "
                                "⚠️ Il campo 'Data di Pubblicazione' è obbligatorio. Si prega di compilarlo </span>",
                                unsafe_allow_html=True)
                    missing = True
                if missing:
                    st.stop()  # stops here, doesn’t launch automation
                try:
                    # Convert the user's string into a real date object
                    start_date_obj = datetime.strptime(date_str, "%d/%m/%Y").date()
                except ValueError:
                    st.error("Formato data non valido. Usa GG/MM/AAAA.")
                    st.stop()  # Stop if the date format is wrong

                    # If all validation passes, set the state and rerun
                st.session_state.course_details = {
                    "title": course_title,
                    "programme": programme,
                    "short_description": short_desc,
                    "start_date": start_date_obj  # Pass the DATE OBJECT, not the string
                }
                st.session_state.app_state = "RUNNING_COURSE"
                st.session_state.course_message = ""
                st.rerun()

    def _render_edition_form(self, is_disabled):
        with st.form(key='edition_form'):
            course_name = st.text_input("Nome del Corso Esistente", placeholder="Nome corso esistente")
            ### HASHTAG: ADDED OPTIONAL EDITION TITLE INPUT
            # This new field allows the user to specify a custom title.
            # The placeholder explains the default behavior if left empty.
            edition_title = st.text_input(
                "Titolo Edizione (opzionale)",
                placeholder="Lascia il campo vuoto per utilizzare automaticamente il nome predefinito (Nome corso - Data)"
            )
            start_date_str = st.text_input("Data Inizio Edizione (GG/MM/AAAA)", "15/10/2025")
            duration_days = st.number_input("Durata edizione (giorni)", min_value=1, value=3)
            # Other optional fields
            description = st.text_area("Descrizione (opzionale)", placeholder="Descrizione di Edizione")
            location = st.text_area("Aula Principale (opzionale)", placeholder="Esempio: AULA DE CARLI. Attenzione: È possibile inserire solo Aule Principali già esistenti nel database Oracle. Per inserire una nuova aula, è necessario prima crearla nel sistema Oracle.")
            supplier = st.text_area("Nome Fornitore Formazione (opzionale)", placeholder="Esempio: ACCADEMIA EUROPEA. Attenzione: È possibile inserire solo Fornitori di Formazione già esistenti nel database Oracle. Per inserire un nuovo fornitore, è necessario prima crearlo nel sistema Oracle ")
            price = st.text_input("Prezzo (€) (opzionale)", placeholder="Esempio: 1000")
            submitted = st.form_submit_button("Crea Edizione", type="primary", disabled=is_disabled)

            if submitted:
                # to show a red warning directly under the field that is missing.
                missing = False

                if not course_name.strip():
                    st.markdown("<span style ='color:red'> "
                                "⚠️ Il campo 'Nome corso esistente' è obbligatorio. Si prega di compilarlo </span>",
                                unsafe_allow_html=True)
                    missing = True

                if not start_date_str.strip():
                    st.markdown("<span style ='color:red'> "
                                "⚠️ Il campo 'Data Inizio Edizione' è obbligatorio. Si prega di compilarlo </span>",
                                unsafe_allow_html=True)
                    missing = True
                if missing:
                    st.stop()
                try:
                    edition_start = datetime.strptime(start_date_str, "%d/%m/%Y").date()
                    st.session_state.edition_details = {
                        "course_name": course_name,
                        "edition_title": edition_title,
                        "edition_start_date": edition_start,
                        "duration_days": int(duration_days),
                        "location": location,
                        "supplier": supplier,
                        "price": price,
                        "description": description
                    }
                    st.session_state.app_state = "RUNNING_EDITION"
                    st.session_state.edition_message = ""  # Clear old message
                    st.rerun()
                except ValueError:
                    st.error("Formato data non valido. Usa GG/MM/AAAA.")

    def update_progress(self, form_type, message, percentage):
        placeholder = self.course_output_placeholder if form_type == "course" else self.edition_output_placeholder
        with placeholder.container():
            st.info(f"⏳ {message}")
            st.progress(percentage)

    def show_message(self, form_type, message, show_clear_button=False):
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