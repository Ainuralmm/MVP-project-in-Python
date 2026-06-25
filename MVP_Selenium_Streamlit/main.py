import sys
import streamlit as st
from model import OracleAutomator
from view import CourseView
from presenter import CoursePresenter

import logging
import os
import builtins
from datetime import datetime

# === LOG DIRECTORY SETUP ===
log_dir = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"session_{datetime.now().strftime('%Y%m%d')}.log")

# === SAVE THE TRUE ORIGINAL PRINT ONCE (survives Streamlit reruns) ===
if not hasattr(builtins, '_true_original_print'):
    builtins._true_original_print = builtins.print

# === RESET LOGGER COMPLETELY ON EVERY RERUN ===
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Remove ALL existing handlers (prevents duplicates on Streamlit reruns)
for handler in logger.handlers[:]:
    logger.removeHandler(handler)
    handler.close()

# Add fresh handlers
formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')

file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

# === REDIRECT print() TO LOGGING (always use the TRUE original) ===
def _logging_print(*args, **kwargs):
    message = ' '.join(str(a) for a in args)
    logging.info(message)
    builtins._true_original_print(*args, **kwargs)

builtins.print = _logging_print

if __name__ == "__main__":
    DRIVER_PATH = "/Users/ainuralmukambetova/PCDocuments/AGSM/edgedriver_mac64_m1/msedgedriver"

    # 1. Initialize the View. It handles all state setup.
    view = CourseView()

    # 2. AUTH GATE — show login screen until user is authenticated
    if not view._render_login_screen():
        st.stop()  # Don't render anything else
    headless, debug_mode, debug_pause = view.get_user_options()

    # 3. Get current state BEFORE rendering UI
    current_state = st.session_state.get('app_state', 'IDLE')

    # 4. Let the View render the entire user interface.
    view.render_ui()

    # 5. Controller Logic: Only run this block if an automation has been started.
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
        elif st.session_state.app_state == "RUNNING_PRESENZA":
            presenter.run_assign_presenza()
        elif st.session_state.app_state == "RUNNING_BATCH_PRESENZA":  # ← NEW
            presenter.run_assign_presenza_batch()

