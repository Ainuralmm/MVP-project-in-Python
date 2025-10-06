import streamlit as st
from datetime import datetime

#to clean previous screen messages
# def clear_last_message():
#     """Clear store persistent UI feedback (progress/message).)"""
#     st.session_state['last_message'] = None
#     st.session_state['last_progress'] = None

class CourseView:
    def __init__(self):
        st.set_page_config(layout='centered')
        st.image("logo-agsm.jpg", width=200)  # Always at the top
        st.title("Automatore per la Gestione dei Corsi Oracle")

    def get_user_options(self):
        #toggle for headless mode
        headless = st.toggle ("😎 Headless (browser automatare nascosto)", value = True)

        debug_mode = False
        debug_pause = 0

        #only show debug if headless is OFF
        if not headless:
            debug_mode = st.toggle("⏸️ Modalità lenta (pausa durante la compilazione dei campi)", value = False)
            #only show pause slider if debug_mode is ON
            if debug_mode:
                debug_pause = st.slider("⏱️Tempo di pausa (secondi)", min_value = 1, max_value = 3, value = 1,step = 1)

        return headless, debug_mode, debug_pause


    def render_form(self):
        # This method displays the input form and returns the collected data.
        st.header("Inserisci Dettagli del Corso")

        # --Init session_state if not set--
        if "automation_running" not in st.session_state:
            st.session_state["automation_running"] = False
        if "start_automation" not in st.session_state:
            st.session_state["start_automation"] = False
        if "course_details" not in st.session_state:
            st.session_state["course_details"] = None
        if "last_progress" not in st.session_state:
            st.session_state["last_progress"] = None
        if "last_status" not in st.session_state:
            st.session_state["last_status"] = None



        # We use a Streamlit form to group the inputs.
        # The code inside 'with form:' will only run when the submit button is pressed.
        with st.form(key='course_creation_form'):
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
                #st.success(f"📅 Data selezionata: {start_date.strftime('%d/%m/%Y')}")
            except ValueError:
                start_date = None
                date_valid = False

            # Button becomes disabled while automation is running
            submitted = st.form_submit_button(
                "Crea Corso in Oracle",type="primary", disabled=st.session_state["automation_running"])


        #when the button is pressed,'submitted' becomes True
        if submitted:

            if not date_valid:
                st.error("Formato non valido. Usa GG/MM/AAAA.")
                return None

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
                st.stop() # stops here, doesn’t launch automation

            #only runs if all required fields are filled
            st.success("✅ Tutti i campi richiesti compilati.Avvio automazione...")
            st.session_state["automation_running"] = True
            #return None



            st.session_state["automation_running"] = True
            st.session_state["course_details"] = {
                "title": course_title,
                "programme": programme,
                "short_description": short_desc,
                "start_date": start_date
            }
            st.session_state["start_automation"] = True
            #st.session_state["needs_rerun"] = True

            # IMPORTANT: force an immediate rerun so the UI re-renders with button disabled
            st.rerun()

        # ---STATUS DISPLAY---
        # After handling rerun logic, render persistent progress/status if present
        if st.session_state.get("last_progress") is not None:
            # show a progress bar at the saved value
            st.progress(st.session_state["last_progress"])
        # Show last status message
        if st.session_state.get("last_status"):
            st.markdown(st.session_state["last_status"])

        # --- SHOW CLEAR HISTORY BUTTON ONLY IF THERE'S HISTORY ---
        if st.session_state.get("last_progress") is not None or st.session_state.get("last_status"):
            st.divider()
            #st.markdown("### 🧹 Gestione Messaggi")
            if st.button("🧹 Cancella Cronologia Messaggi", type="secondary", use_container_width=True):
                for key in ["last_progress", "last_status", "course_details"]:
                    if key in st.session_state:
                        st.session_state[key] = None
                st.success("✅ Tutti i messaggi precedenti sono stati cancellati.")
                st.rerun()

        return None

    def display_message(self,message):
        #this method show a message to the user-->Presenter call this method to provide feedback
        if not message:
            return

        if 'Success' in message:
            st.success(message)
        elif 'Error' in message:
            st.error(message)
        else:
            st.info(message)