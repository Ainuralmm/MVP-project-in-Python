import streamlit as st
from datetime import datetime, timedelta


class CourseView:
    def __init__(self):
        st.set_page_config(layout='centered')
        # --- Basic App State ---
        if "app_state" not in st.session_state:
            st.session_state.app_state = "IDLE"

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

        # --- NEW: Preserved form data storage ---
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

        # --- Combined Edition + Activity Form Container ---
        with st.container(border=True):
            st.header("2. Creazione Nuova Edizione + Attività")
            if st.session_state.app_state == "RUNNING_EDITION":
                self.edition_output_placeholder = st.empty()
            else:
                self._render_edition_form(is_disabled=is_running)
                self.edition_output_placeholder = st.empty()
                if st.session_state.edition_message:
                    self.show_message("edition", st.session_state.edition_message, show_clear_button=True)

        # --- Student Form Container ---
        with st.container(border=True):
            st.header("3. Aggiungi Allievi (a Edizione Esistente)")
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
            st.checkbox("Invia Convocazione Online", key="student_convocazione_online", value=True)
            st.checkbox("Invia Convocazione Presenza", key="student_convocazione_presenza", value=True)

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