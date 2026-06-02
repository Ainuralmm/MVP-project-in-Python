#import sys
import streamlit as st
from model import OracleAutomator
from view import CourseView
from presenter import CoursePresenter

import logging
import os
from datetime import datetime

# === BASIC SESSION LOGGING ===
# Creates a new log file each day in logs/ folder
# Captures all print() output and errors automatically
log_dir = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(log_dir, exist_ok=True)

log_file = os.path.join(
    log_dir,
    f"session_{datetime.now().strftime('%Y%m%d')}.log"
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()  # still shows in terminal too
    ]
)

# Redirect uncaught exceptions to log file
import sys

def log_exception(exc_type, exc_value, exc_traceback):
    logging.error(
        "UNCAUGHT EXCEPTION",
        exc_info=(exc_type, exc_value, exc_traceback)
    )
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

sys.excepthook = log_exception

# Only log app start once per session, not on every Streamlit rerun
if 'session_logged' not in st.session_state:
    logging.info(f"=== APP STARTED === User: {os.environ.get('USERNAME', 'unknown')}")
    st.session_state.session_logged = True

# Redirect all print() statements to the log file too
import builtins

# Only redirect once — guard against multiple Streamlit reruns
if not hasattr(builtins, '_logging_redirected'):
    _original_print = builtins.print

    def _logging_print(*args, **kwargs):
        message = ' '.join(str(a) for a in args)
        logging.info(message)
        _original_print(*args, **kwargs)

    builtins.print = _logging_print
    builtins._logging_redirected = True

if __name__ == "__main__":
    DRIVER_PATH = "/Users/ainuralmukambetova/PCDocuments/AGSM/edgedriver_mac64_m1/msedgedriver"

    # 1. Initialize the View. It handles all state setup.
    view = CourseView()
    headless, debug_mode, debug_pause = view.get_user_options()

    # 2. Get current state BEFORE rendering UI
    current_state = st.session_state.get('app_state', 'IDLE')

    # 2. Let the View render the entire user interface.
    #view.render_ui()

    # 3. Controller Logic: Only run this block if an automation has been started.
    if current_state != "IDLE":
        model = OracleAutomator(driver_path=DRIVER_PATH,
                                debug_mode=debug_mode,
                                debug_pause=debug_pause,
                                headless=headless)
        presenter = CoursePresenter(model, view)

        # Run the correct process based on the state
        if st.session_state.app_state == "RUNNING_COURSE":
            presenter.run_create_course(st.session_state.get("course_details"))

        elif st.session_state.app_state == "RUNNING_BATCH_COURSE":
            presenter.run_create_batch_courses(st.session_state.get("batch_course_data"))

        elif st.session_state.app_state == "RUNNING_EDITION":
            presenter.run_create_edition_and_activities(st.session_state.get("edition_details"))

        # === NEW STATE ===
        elif st.session_state.app_state == "RUNNING_BATCH_EDITION":
            presenter.run_batch_edition_creation()

        elif st.session_state.app_state == "RUNNING_STUDENTS":
            presenter.run_add_students(st.session_state.get("student_details"))
        elif st.session_state.app_state == "RUNNING_BATCH_STUDENTS":
             presenter.run_add_students_batch()
        elif st.session_state.app_state == "RUNNING_VERIFY_STUDENTS":
            presenter.run_verify_students()
        elif st.session_state.app_state == "RUNNING_PRESENZA":
            presenter.run_assign_presenza()
    else: # 4. Only render UI when NOT running automation
        view.render_ui()