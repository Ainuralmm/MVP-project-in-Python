#import sys
import streamlit as st
from model import OracleAutomator
from view import CourseView
from presenter import CoursePresenter

#st.write("PYTHON EXECUTABLE:", sys.executable)
### HASHTAG: SIMPLIFIED AND CORRECTED LOGIC
# The main script now initializes the view and lets it handle all rendering.
# The controller logic only runs when the app is busy, creating the model
# and presenter only when needed.

if __name__ == "__main__":
    DRIVER_PATH = "/Users/ainuralmukambetova/PCDocuments/AGSM/edgedriver_mac64_m1 /msedgedriver"

    # 1. Initialize the View. It handles all state setup.
    view = CourseView()
    headless, debug_mode, debug_pause = view.get_user_options()

    # 2. Let the View render the entire user interface.
    view.render_ui()

    # 3. Controller Logic: Only run this block if an automation has been started.
    if st.session_state.app_state != "IDLE":
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