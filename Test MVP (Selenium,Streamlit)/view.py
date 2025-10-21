# view.py
import streamlit as st
from datetime import datetime


class CourseView:
    # ... ( __init__, get_user_options, and render_ui methods are perfect and do not need to be changed) ...
    def __init__(self):
        st.set_page_config(layout='centered')
        if "app_state" not in st.session_state: st.session_state.app_state = "IDLE" #It's the default, resting state. means:The app is not busy. It's just waiting for you to fill in a form and click a button.
        if "course_message" not in st.session_state: st.session_state.course_message = ""
        if "edition_message" not in st.session_state: st.session_state.edition_message = ""
        if "activity_message" not in st.session_state:
            st.session_state.activity_message = ""
        if "num_activities" not in st.session_state:
            st.session_state.num_activities = 1

        ### THE FIX - INITIALIZE WIDGET STATE HERE ###
        # If the key for a widget doesn't exist in memory, create it with its default value.
        # This becomes the single source of truth.
        if "course_date_str_key" not in st.session_state:
            st.session_state.course_date_str_key = "01/01/2023"
        # (You can do this for all your other inputs too)
        if "edition_start_date_str_key" not in st.session_state:
            st.session_state.edition_start_date_str_key = ""
        if "edition_end_date_str_key" not in st.session_state:
            st.session_state.edition_end_date_str_key = ""

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
                if st.session_state.course_message: self.show_message("course", st.session_state.course_message,show_clear_button = True)

        # --- Edition Form Container ---
        with st.container(border=True):
            st.header("2. Creazione Nuova Edizione")
            if st.session_state.app_state == "RUNNING_EDITION":
                self.edition_output_placeholder = st.empty()
            else:
                self._render_edition_form(is_disabled=is_running)
                self.edition_output_placeholder = st.empty()
                if st.session_state.edition_message: self.show_message("edition", st.session_state.edition_message,show_clear_button = True)

        ### HASHTAG: ADD NEW CONTAINER FOR ACTIVITY FORM
        with st.container(border=True):
            st.header("3. Creazione Attività (per Edizione Esistente)")
            if st.session_state.app_state == "RUNNING_ACTIVITY":
                self.activity_output_placeholder = st.empty()
            else:
                self._render_activity_form(is_disabled=is_running)
                self.activity_output_placeholder = st.empty()
                if st.session_state.activity_message:
                    self.show_message("activity", st.session_state.activity_message, show_clear_button=True)


    def _clear_course_form_callback(self):
        st.session_state.course_title_key = ""
        st.session_state.course_programme_key = ""
        st.session_state.course_short_desc_key = ""
        st.session_state.course_date_str_key = "01/01/2023"

    def _clear_edition_form_callback(self):
        st.session_state.edition_course_name_key = ""
        st.session_state.edition_title_key = ""
        st.session_state.edition_start_date_str_key = ""
        st.session_state.edition_end_date_str_key = ""
        st.session_state.edition_description_key = ""
        st.session_state.edition_location_key = ""
        st.session_state.edition_supplier_key = ""
        st.session_state.edition_price_key = ""

    def _clear_activity_form_callback(self):
        st.session_state.activity_course_name_key = ""
        st.session_state.activity_edition_name_key = ""
        st.session_state.activity_edition_publish_date_key = ""  # <-- ADDED THIS
        st.session_state.activity_start_date_key = ""
        st.session_state.num_activities = 1
        # Clear any dynamically generated keys
        for i in range(30):  # Clear up to 30 keys just in case
            if f"activity_title_{i}" in st.session_state:
                st.session_state[f"activity_title_{i}"] = ""
            if f"activity_desc_{i}" in st.session_state:
                st.session_state[f"activity_desc_{i}"] = ""

    def _render_course_form(self, is_disabled):
        with st.form(key='course_form'):

            # The local variables are assigned again, exactly as you had them.
            # The `key` parameters now have a `_key` suffix to avoid conflicts, which is a good practice.
            course_title = st.text_input("Titolo del Corso", placeholder="Esempio: Analisi dei Dati",
                                         key="course_title_key")
            programme = st.text_area("Dettagli del Programma", placeholder="Campo opzionale...",
                                     key="course_programme_key")
            short_desc = st.text_input("Breve Descrizione", placeholder="Esempio: Analisi dei Dati Informatica",
                                       key="course_short_desc_key")
            ### HASHTAG: THE FIX - REMOVE THE CONFLICTING DEFAULT ###
            # The `value` parameter is no longer needed because the widget will
            # automatically use the value from st.session_state.course_date_str_key.
            date_str = st.text_input("Data di Pubblicazione (GG/MM/AAAA)", key="course_date_str_key")

            col1, col2 = st.columns([3, 1])
            with col1:
                submitted = st.form_submit_button("Crea Corso", type="primary", disabled=is_disabled,
                                                  use_container_width=True)
            with col2:
                st.form_submit_button("Pulisci 🧹", use_container_width=True, on_click=self._clear_course_form_callback)

        if submitted:
            # YOUR VALIDATION LOGIC NOW WORKS AGAIN, USING THE LOCAL VARIABLES.
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

            # The rest of your submission logic remains unchanged.
            try:
                start_date_obj = datetime.strptime(date_str, "%d/%m/%Y").date()
                st.session_state.course_details = {
                    "title": course_title, "programme": programme,
                    "short_description": short_desc, "start_date": start_date_obj
                }
                st.session_state.app_state = "RUNNING_COURSE"
                st.session_state.course_message = ""
                st.rerun()
            except ValueError:
                st.error("Formato data non valido. Usa GG/MM/AAAA.")
                st.stop()

    def _render_edition_form(self, is_disabled):
        with st.form(key='edition_form'):
            ### HASHTAG: VARIABLES RESTORED FOR EDITION FORM ✅
            course_name = st.text_input("Nome del Corso Esistente", placeholder="Nome corso esistente",
                                        key="edition_course_name_key")
            edition_title = st.text_input("Titolo Edizione (opzionale)", placeholder="Lascia vuoto...",
                                          key="edition_title_key")
            start_date_str = st.text_input("Data Inizio Edizione (GG/MM/AAAA)",
                                           key="edition_start_date_str_key")
            end_date_str = st.text_input("Data Fine Edizione (GG/MM/AAAA)",
                                         key="edition_end_date_str_key")
            description = st.text_area("Descrizione (opzionale)", placeholder="Descrizione...",
                                       key="edition_description_key")
            location = st.text_area("Aula Principale (opzionale)", placeholder="Esempio: AULA DE CARLI",
                                    key="edition_location_key")
            supplier = st.text_area("Nome Fornitore Formazione (opzionale)", placeholder="Esempio: AEIT",
                                    key="edition_supplier_key")
            price = st.text_input("Prezzo (€) (opzionale)", placeholder="Esempio: 1000", key="edition_price_key")

            col1, col2 = st.columns([3, 1])
            with col1:
                submitted = st.form_submit_button("Crea Edizione", type="primary", disabled=is_disabled,
                                                  use_container_width=True)
            with col2:
                st.form_submit_button("Pulisci 🧹", use_container_width=True, on_click=self._clear_edition_form_callback)

        if submitted:
            # YOUR VALIDATION LOGIC WORKS AGAIN
            missing = False
            if not course_name.strip():
                st.markdown("...", unsafe_allow_html=True)
                missing = True
            # ... (rest of your validation)
            if missing:
                st.stop()

            # The rest of your submission logic remains unchanged.
            try:
                edition_start = datetime.strptime(start_date_str, "%d/%m/%Y").date()
                edition_end = datetime.strptime(end_date_str, "%d/%m/%Y").date()
                if edition_end < edition_start:
                    st.error("La data di fine non può essere precedente alla data di inizio.")
                    st.stop()
                st.session_state.edition_details = {
                    "course_name": course_name, "edition_title": edition_title,
                    "edition_start_date": edition_start, "edition_end_date": edition_end,
                    "location": location, "supplier": supplier,
                    "price": price, "description": description
                }
                st.session_state.app_state = "RUNNING_EDITION"
                st.session_state.edition_message = ""
                st.rerun()
            except ValueError:
                st.error("Formato data non valido. Usa GG/MM/AAAA.")

        ### HASHTAG: ADD NEW RENDER METHOD FOR ACTIVITY FORM
    def _render_activity_form(self, is_disabled):
        # This number input controls how many forms are drawn
        # It's outside the form so it can trigger a rerun when changed
        num_activities = st.number_input(
            "Quanti giorni di attività?",
            min_value=1,
            max_value=35,  # Set a reasonable limit
            key="num_activities"
        )

        with st.form(key='activity_form'):
            st.subheader("1. Trova Edizione")
            st.text_input("Nome del Corso Esistente", placeholder="Corso per cui creare attività",
                          key="activity_course_name_key")
            st.text_input("Nome Esatto Edizione", placeholder="Edizione esatta a cui aggiungere attività",
                          key="activity_edition_name_key")

            ### HASHTAG: ADDED NEW PUBLISH DATE FIELD
            # This is the new field to find the unique edition, as you requested.
            st.text_input("Data Pubblicazione Edizione (GG/MM/AAAA)",
                          placeholder="La 'Publish Start Date' dell'edizione", key="activity_edition_publish_date_key")

            st.divider()

            st.subheader("2. Dettagli Attività")
            st.text_input("Data Inizio Attività (Giorno 1) (GG/MM/AAAA)", "20/10/2025", key="activity_start_date_key")

            for i in range(num_activities):
                st.markdown(f"**Giorno {i + 1}**")
                st.text_input(f"Titolo Attività Giorno {i + 1}", key=f"activity_title_{i}")
                st.text_area(f"Descrizione Attività Giorno {i + 1}", key=f"activity_desc_{i}")

            col1, col2 = st.columns([3, 1])
            with col1:
                submitted = st.form_submit_button("Crea Attività", type="primary", disabled=is_disabled,
                                                  use_container_width=True)
            with col2:
                st.form_submit_button("Pulisci 🧹", use_container_width=True,
                                      on_click=self._clear_activity_form_callback)
            if submitted:
                # Collect all data
                course_name = st.session_state.activity_course_name_key
                edition_name = st.session_state.activity_edition_name_key
                edition_publish_date_str = st.session_state.activity_edition_publish_date_key  # <-- Get new data
                start_date_str = st.session_state.activity_start_date_key

                if not all([course_name.strip(), edition_name.strip(), start_date_str.strip(),
                            edition_publish_date_str.strip()]):
                    st.error("Tutti i campi in 'Trova Edizione' e 'Data Inizio Attività' sono obbligatori.")
                    st.stop()

                try:
                    start_date = datetime.strptime(start_date_str, "%d/%m/%Y").date()
                    edition_publish_date = datetime.strptime(edition_publish_date_str,
                                                             "%d/%m/%Y").date()  # <-- Convert new data

                    activities_list = []
                    for i in range(num_activities):
                        title = st.session_state[f"activity_title_{i}"]
                        desc = st.session_state[f"activity_desc_{i}"]
                        if not title.strip() or not desc.strip():
                            st.error(f"Titolo e Descrizione sono obbligatori per il Giorno {i + 1}.")
                            st.stop()

                        activities_list.append({
                            "title": title,
                            "description": desc,
                            "date": start_date + timedelta(days=i)
                        })

                    st.session_state.activity_details = {
                        "course_name": course_name,
                        "edition_name": edition_name,
                        "edition_publish_date": edition_publish_date,  # <-- Pass new data to model
                        "activities": activities_list
                    }
                    st.session_state.app_state = "RUNNING_ACTIVITY"
                    st.session_state.activity_message = ""
                    st.rerun()
                except ValueError:
                    st.error("Formato data non valido. Usa GG/MM/AAAA.")
                except Exception as e:
                    st.error(f"Errore nella raccolta dati: {e}")

    def update_progress(self, form_type, message, percentage):
        placeholder = None
        if form_type == "course":
            placeholder = self.course_output_placeholder
        elif form_type == "edition":
            placeholder = self.edition_output_placeholder
        elif form_type == "activity":
            placeholder = self.activity_output_placeholder

        if hasattr(self, 'course_output_placeholder') and placeholder:  # Use a base attribute check
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
        elif form_type == "activity":
            placeholder = self.activity_output_placeholder
            message_key = "activity_message"

        if not placeholder or not message_key:
            return  # Safety check

        st.session_state[message_key] = message
        if hasattr(self, 'course_output_placeholder') and placeholder:  # Use a base attribute check
            with placeholder.container():
                if "✅" in message:
                    st.success(message)
                else:
                    st.error(message)
                if show_clear_button:
                    if st.button(f"🧹 Cancella Messaggio", key=f"clear_{form_type}"):
                        st.session_state[message_key] = ""
                        st.rerun()