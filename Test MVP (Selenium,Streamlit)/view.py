import streamlit as st
from datetime import datetime

class CourseView:
    def __init__(self):
        st.set_page_config(layout='centered')
        st.image("logo-agsm.jpg", width=200)  # Always at the top
        st.title("Automatore per la Gestione dei Corsi Oracle")

        # INITIALIZE NEEDED KEYS
        if "automation_running_course" not in st.session_state:
            st.session_state["automation_running_course"] = False
        if "automation_running_edition" not in st.session_state:
            st.session_state["automation_running_edition"] = False
        if "course_last_progress" not in st.session_state:
            st.session_state["course_last_progress"] = None
        if "course_last_status" not in st.session_state:
            st.session_state["course_last_status"] = None
        if "edition_last_progress" not in st.session_state:
            st.session_state["edition_last_progress"] = None
        if "edition_last_status" not in st.session_state:
            st.session_state["edition_last_status"] = None


def get_user_options(self):
    headless = st.toggle("Headless (browser automatare nascosto)", value=True)
    debug_mode = False
    debug_pause = 0
    if not headless:
        debug_mode = st.toggle("⏸️ Modalità lenta (pausa durante la compilazione dei campi)", value=False)
        if debug_mode:
            debug_pause = st.slider("⏱️Tempo di pausa (secondi)", min_value=1, max_value=3, value=1, step=1)
    return headless, debug_mode, debug_pause

    # --- COURSE FORM ---


def render_course_form(self):
    st.header("Inserisci Dettagli del Corso")
    with st.form(key="course_creation_form"):
        course_title = st.text_input("Titolo del Corso", value="", placeholder="Esempio: Analisi dei Dati",
                                     key="cf_title")
        programme = st.text_area("Dettagli del Programma", value="", placeholder="Opzionale", key="cf_programme")
        short_desc = st.text_input("Breve Descrizione", value="", placeholder="Esempio", key="cf_short_desc")
        date_str = st.text_input("Data di Pubblicazione (GG/MM/AAAA)", value="01/01/2023", key="cf_date")
        submit_course = st.form_submit_button("Crea Corso in Oracle",
                                              disabled=st.session_state["automation_running_course"])

    # Validation on submit
    if submit_course:
        # simple validation
        try:
            start_date = datetime.strptime(st.session_state["cf_date"], "%d/%m/%Y").date()
            date_valid = True
        except Exception:
            date_valid = False
        missing = False
        if not st.session_state["cf_title"].strip():
            st.markdown("<span style='color:red'>⚠️ Titolo corso obbligatorio</span>", unsafe_allow_html=True)
            missing = True
        if not st.session_state["cf_short_desc"].strip():
            st.markdown("<span style='color:red'>⚠️ Breve descrizione obbligatoria</span>", unsafe_allow_html=True)
            missing = True
        if not date_valid:
            st.error("Formato data non valido. Usa GG/MM/AAAA.")
            missing = True
        if missing:
            return None
        # set state for main to pick up and run presenter
        st.session_state["automation_running_course"] = True
        st.session_state["course_details"] = {
            "title": st.session_state["cf_title"],
            "programme": st.session_state["cf_programme"],
            "short_description": st.session_state["cf_short_desc"],
            "start_date": start_date
        }
        st.session_state["start_automation_course"] = True
        st.rerun()

    # PROGRESS DISPLAY for course
    if st.session_state.get("course_last_progress") is not None:
        st.progress(st.session_state["course_last_progress"])
    if st.session_state.get("course_last_status"):
        st.markdown(st.session_state["course_last_status"])

    # CLEAR button for course history (only visible after a run)
    if st.session_state.get("course_last_status") or st.session_state.get("course_last_progress") is not None:
        if st.button("🧹 Cancella cronologia corso", key="clear_course"):
            st.session_state["course_last_progress"] = None
            st.session_state["course_last_status"] = None
            st.rerun()

    # --- EDITION FORM ---


def render_edition_form(self):
    st.divider()
    st.header("📘 Creazione Edizione (corso esistente)")
    with st.form(key="edition_creation_form"):
        course_name = st.text_input("Nome del Corso Esistente", value="", key="ef_course_name")
        location = st.text_input("Sede (Location)", value="", key="ef_location")
        supplier = st.text_input("Fornitore (opzionale)", value="", key="ef_supplier")
        price = st.text_input("Prezzo (€) (opzionale)", value="", key="ef_price")
        start_date_str = st.text_input("Data Inizio Edizione (GG/MM/AAAA)", value="15/10/2025", key="ef_start")
        duration_days = st.number_input("Durata edizione (giorni)", min_value=1, max_value=365, value=3,
                                        key="ef_duration")
        submit_ed = st.form_submit_button("Crea Edizione in Oracle",
                                          disabled=st.session_state["automation_running_edition"])

    if submit_ed:
        try:
            edition_start = datetime.strptime(st.session_state["ef_start"], "%d/%m/%Y").date()
            edition_valid = True
        except Exception:
            edition_valid = False

        missing = False
        if not st.session_state["ef_course_name"].strip():
            st.markdown("<span style='color:red'>⚠️ Nome del corso obbligatorio</span>", unsafe_allow_html=True)
            missing = True
        if not edition_valid:
            st.error("Formato data non valido. Usa GG/MM/AAAA.")
            missing = True
        if missing:
            return None

        st.session_state["automation_running_edition"] = True
        st.session_state["edition_details"] = {
            "course_name": st.session_state["ef_course_name"],
            "edition_start_date": edition_start,
            "duration_days": int(st.session_state["ef_duration"]),
            "location": st.session_state["ef_location"],
            "supplier": st.session_state["ef_supplier"],
            "price": st.session_state["ef_price"]
        }
        st.session_state["start_automation_edition"] = True
        st.rerun()

    # PROGRESS DISPLAY for edition
    if st.session_state.get("edition_last_progress") is not None:
        st.progress(st.session_state["edition_last_progress"])
    if st.session_state.get("edition_last_status"):
        st.markdown(st.session_state["edition_last_status"])

    # CLEAR button for edition history
    if st.session_state.get("edition_last_status") or st.session_state.get("edition_last_progress") is not None:
        if st.button("🧹 Cancella cronologia edizione", key="clear_edition"):
            st.session_state["edition_last_progress"] = None
            st.session_state["edition_last_status"] = None
            st.rerun()

    # --- CALLBACKS USED BY PRESENTER VIA MAIN ---
    # PROGRESS: value is 0..100, which is "course" or "edition"


def progress_callback(self, value, which):
    key = "course_last_progress" if which == "course" else "edition_last_progress"
    st.session_state[key] = int(value)


def status_callback(self, text, which):
    key = "course_last_status" if which == "course" else "edition_last_status"
    st.session_state[key] = text

    # DONE callback: presenter calls when finished (success or failure)


def done_callback(self, result_dict, which):
    # Ensure buttons get re-enabled and final messages are stored
    if which == "course":
        st.session_state["automation_running_course"] = False
        st.session_state["start_automation_course"] = False
        st.session_state["course_last_status"] = result_dict.get("message", str(result_dict))
        st.session_state["course_last_progress"] = 100 if result_dict.get("ok") else 0
    else:
        st.session_state["automation_running_edition"] = False
        st.session_state["start_automation_edition"] = False
        st.session_state["edition_last_status"] = result_dict.get("message", str(result_dict))
        st.session_state["edition_last_progress"] = 100 if result_dict.get("ok") else 0
    # trigger UI refresh
    st.rerun()

    # small helper for view-only display message use by presenter if needed


def display_message(self, msg):
    st.info(msg)