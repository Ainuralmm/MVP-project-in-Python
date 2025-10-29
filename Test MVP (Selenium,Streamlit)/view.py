# view.py
import streamlit as st
from datetime import datetime, timedelta # <-- Add timedelta here



class CourseView:
    # ... ( __init__, get_user_options, and render_ui methods are perfect and do not need to be changed) ...
    def __init__(self):
        st.set_page_config(layout='centered')
        # --- Basic App State ---
        if "app_state" not in st.session_state: st.session_state.app_state = "IDLE" #It's the default, resting state. means:The app is not busy. It's just waiting for you to fill in a form and click a button.
        if "course_message" not in st.session_state: st.session_state.course_message = ""
        if "edition_message" not in st.session_state: st.session_state.edition_message = ""

        if "num_activities" not in st.session_state:
            st.session_state.num_activities = 1

        # --- Initialize Widget States (Single Source of Truth) ---
        # If the key for a widget doesn't exist in memory, create it with its default value.
        # This becomes the single source of truth.
        if "course_date_str_key" not in st.session_state:
            st.session_state.course_date_str_key = "01/01/2023"
        # (You can do this for all your other inputs too)
        # if "edition_start_date_str_key" not in st.session_state:
        #     st.session_state.edition_start_date_str_key = ""
        # if "edition_end_date_str_key" not in st.session_state:
        #     st.session_state.edition_end_date_str_key = ""
        # if "activity_start_date_key" not in st.session_state:
        #     st.session_state.activity_start_date_key = ""

        # Initialize activity time defaults (important for consistency)
        for i in range(30):  # Loop up to your max
            if f"activity_start_time_{i}" not in st.session_state:
                st.session_state[f"activity_start_time_{i}"] = "09.00"
            if f"activity_end_time_{i}" not in st.session_state:
                st.session_state[f"activity_end_time_{i}"] = "11.00"
            # Dates and others can start empty implicitly

            st.image("logo-agsm.jpg", width=200)

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

            # --- Combined Edition + Activity Form Container ---
            ### HASHTAG: Simplified UI - Only 2 Forms Now
        with st.container(border=True):
            st.header("2. Creazione Nuova Edizione + Attività")
            if st.session_state.app_state == "RUNNING_EDITION":
                self.edition_output_placeholder = st.empty()
            else:
                self._render_edition_form(is_disabled=is_running)  # This now includes activities
                self.edition_output_placeholder = st.empty()
                if st.session_state.edition_message:
                    self.show_message("edition", st.session_state.edition_message,
                                              show_clear_button=True)  # Use 'edition' message key

    def _clear_course_form_callback(self):
        st.session_state.course_title_key = ""
        st.session_state.course_programme_key = ""
        st.session_state.course_short_desc_key = ""
        st.session_state.course_date_str_key = "01/01/2023"

    ### HASHTAG: Updated Clear Callback for Combined Form
    def _clear_edition_activity_form_callback(self):
        st.session_state.edition_course_name_key = ""
        st.session_state.edition_title_key = ""
        st.session_state.edition_start_date_str_key = ""
        st.session_state.edition_end_date_str_key = ""
        st.session_state.edition_description_key = ""
        st.session_state.edition_location_key = ""
        st.session_state.edition_supplier_key = ""
        st.session_state.edition_price_key = ""
        st.session_state.num_activities = 1  # Reset number of activities
    # Clear dynamic activity fields
        for i in range(30):  # Adjust limit if needed
            if f"activity_title_{i}" in st.session_state: st.session_state[f"activity_title_{i}"] = ""
            if f"activity_desc_{i}" in st.session_state: st.session_state[f"activity_desc_{i}"] = ""
            if f"activity_date_{i}" in st.session_state: st.session_state[f"activity_date_{i}"] = ""
            if f"activity_start_time_{i}" in st.session_state: st.session_state[f"activity_start_time_{i}"] = "00.00"
            if f"activity_end_time_{i}" in st.session_state: st.session_state[f"activity_end_time_{i}"] = "00.00"
            if f"activity_future_field_{i}" in st.session_state: st.session_state[f"activity_future_field_{i}"] = ""

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

        ### HASHTAG: COMBINED EDITION AND ACTIVITY RENDER METHOD
    def _render_edition_form(self, is_disabled):  # Renamed for clarity, handles both now
            # Number input outside the form
            num_activities = st.number_input(
                "Quanti giorni di attività?",
                min_value=1,
                max_value=30,  # Sensible limit
                key="num_activities"
            )

            with st.form(key='edition_activity_form'):  # Renamed key
                # --- Edition Details ---
                st.subheader("Dettagli Edizione")
                st.text_input("Nome del Corso Esistente", placeholder="Nome corso esistente",
                              key="edition_course_name_key")
                st.text_input("Titolo Edizione (opzionale)",
                              placeholder="Lascia vuoto per usare il nome predefinito...", key="edition_title_key")
                st.text_input("Data Inizio Edizione (GG/MM/AAAA)", key="edition_start_date_str_key")
                st.text_input("Data Fine Edizione (GG/MM/AAAA)", key="edition_end_date_str_key")
                st.text_area("Descrizione Edizione (opzionale)", placeholder="Descrizione...",
                             key="edition_description_key")
                st.text_area("Aula Principale (opzionale)", placeholder="Esempio: AULA DE CARLI", key="edition_location_key")
                st.text_area("Nome Fornitore Formazione (opzionale)", placeholder="Esempio: AEIT",
                             key="edition_supplier_key")
                st.text_input("Prezzo Edizione (€) (opzionale)", placeholder="Esempio: 1000", key="edition_price_key")

                st.divider()

                # --- Activity Details (Dynamic) ---
                st.subheader("Dettagli Attività")
                for i in range(num_activities):
                    st.markdown(f"**Giorno {i + 1}**")
                    cols = st.columns([2, 1, 1, 1])  # Layout columns
                    with cols[0]:
                        st.text_input(f"Titolo Attività", key=f"activity_title_{i}")
                    with cols[1]:
                        st.text_input(f"Data (GG/MM/AAAA)", key=f"activity_date_{i}",
                                      placeholder=f"Data giorno {i + 1}")
                    with cols[2]:
                        st.text_input(f"Ora Inizio (HH:MM)", key=f"activity_start_time_{i}")
                    with cols[3]:
                        st.text_input(f"Ora Fine (HH:MM)", key=f"activity_end_time_{i}")

                    st.text_area(f"Descrizione Attività", key=f"activity_desc_{i}", height=100)

                    ### HASHTAG: PLACEHOLDER FOR FUTURE INPUT ###
                    # st.text_input(f"Campo Futuro Giorno {i+1}", key=f"activity_future_field_{i}")

                    st.markdown("---")  # Separator between days

                # --- Buttons ---
                col1, col2 = st.columns([3, 1])
                with col1:
                    submitted = st.form_submit_button("Crea Edizione e Attività", type="primary", disabled=is_disabled,
                                                      use_container_width=True)
                with col2:
                    st.form_submit_button("Pulisci 🧹", use_container_width=True,
                                          on_click=self._clear_edition_activity_form_callback)  # Use updated callback

            # --- Submission Logic ---
            if submitted:
                # --- 1. Collect ALL string inputs first ---
                course_name = st.session_state.edition_course_name_key
                edition_title = st.session_state.edition_title_key
                start_date_str = st.session_state.edition_start_date_str_key
                end_date_str = st.session_state.edition_end_date_str_key
                description = st.session_state.edition_description_key
                location = st.session_state.edition_location_key
                supplier = st.session_state.edition_supplier_key
                price = st.session_state.edition_price_key

                # --- 2. Basic Required Field Validation ---
                if not all([course_name.strip(), start_date_str.strip(), end_date_str.strip()]):
                    st.error("I campi 'Nome Corso', 'Data Inizio Edizione' e 'Data Fine Edizione' sono obbligatori.")
                    st.stop()
                # --- 3. Parse Dates & Perform ALL Validations within a try/except ---
                try:
                    # Parse Edition Dates
                    edition_start = datetime.strptime(start_date_str, "%d/%m/%Y").date()
                    edition_end = datetime.strptime(end_date_str, "%d/%m/%Y").date()
                    # Validate Edition Date Range
                    if edition_end < edition_start:
                        st.error("La data di fine edizione non può essere precedente alla data di inizio.")
                        st.stop()
                    # --- Loop for Activity Validation ---
                        # Collect Activity Data
                    activities_list = []

                    for i in range(num_activities):
                            title = st.session_state.get(f"activity_title_{i}", "")
                            act_desc = st.session_state.get(f"activity_desc_{i}", "")
                            act_date_str = st.session_state.get(f"activity_date_{i}", "")
                            start_time = st.session_state.get(f"activity_start_time_{i}", "09:00")
                            end_time = st.session_state.get(f"activity_end_time_{i}", "11:00")
                            future_val = st.session_state.get(f"activity_future_field_{i}", "")  # Get future value

                            # 1. Validate required fields for *this* activity
                            if not all([title.strip(), act_desc.strip(), act_date_str.strip()]):
                                st.error(
                                    f"Titolo, Descrizione e Data sono obbligatori per l'attività del Giorno {i + 1}.")
                                st.stop()  # Stop validation on first error
                            # 2. Try parsing and validating date/time formats AND range

                            act_date = datetime.strptime(act_date_str, "%d/%m/%Y").date()
                            # Basic time format check (HH:MM) - could be more robust
                            datetime.strptime(start_time, "%H.%M")
                            datetime.strptime(end_time, "%H.%M")
                            # Check if activity date is outside the edition start/end range.
                            if act_date < edition_start or act_date > edition_end:
                                    st.error(
                                        f"La data dell'attività (Giorno {i + 1}: {act_date_str}) deve essere compresa tra l'inizio ({start_date_str}) e la fine ({end_date_str}) dell'edizione.")
                                    # all_activities_valid = False
                                    st.stop()  # Stop checking further activities if one is invalid
                            # 3. If validation passes for this activity, append it
                            activities_list.append({
                                        "title": title,
                                        "description": act_desc,
                                        "date": act_date,
                                        "start_time": start_time,
                                        "end_time": end_time,
                                        "future_field": future_val  # Include future value
                                    })
                except ValueError:
                    # This catches errors from ANY strptime call (edition or activity)
                    st.error("Formato data o ora non valido. Usa GG/MM/AAAA e HH.MM (con il punto).")
                    st.stop()  # Stop if any date/time format is wrong


                #  If the loop completes without stopping, all activities are valid. Proceed.
                st.session_state.edition_details = {
                    "course_name": course_name, "edition_title": edition_title,
                    "edition_start_date": edition_start, "edition_end_date": edition_end,
                    "location": location, "supplier": supplier, "price": price, "description": description,
                    "activities": activities_list  # Add the collected activities
                }
                st.session_state.app_state = "RUNNING_EDITION"  # Still use EDITION state
                st.session_state.edition_message = ""
                st.rerun()

    def update_progress(self, form_type, message, percentage):
        placeholder = None
        if form_type == "course":
            placeholder = self.course_output_placeholder
        elif form_type == "edition":
            placeholder = self.edition_output_placeholder

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