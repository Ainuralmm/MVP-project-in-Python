import streamlit as st
from model import OracleAutomator
from view import CourseView
from presenter import CoursePresenter

if __name__ == "__main__":
    # path of to Edge Webdriver
    DRIVER_PATH = "/Users/ainuralmukambetova/PCDocuments/AGSM/edgedriver_mac64_m1/msedgedriver"

    view = CourseView()
    headless, debug_mode, debug_pause = view.get_user_options()

    # Render the form (this will return None normally; submission triggers a rerun)
    view.render_course_form()
    view.render_edition_form()


    # Instantiate presenter/model when an automation starts
    def get_presenter_and_model():
        model = OracleAutomator(driver_path=DRIVER_PATH, debug_mode=debug_mode, debug_pause=debug_pause,
                                headless=headless)
        presenter = CoursePresenter(model)
        return presenter, model


    # Prepare secrets for presenter (no Streamlit inside presenter)
    secrets = {
        "ORACLE_URL": st.secrets.get("ORACLE_URL"),
        "ORACLE_USER": st.secrets.get("ORACLE_USER"),
        "ORACLE_PASS": st.secrets.get("ORACLE_PASS"),
    }

    # START COURSE FLOW
    if st.session_state.get("start_automation_course"):
        details = st.session_state.get("course_details")
        if details:
            presenter, model = get_presenter_and_model()
            # CALL PRESENTER with callbacks into view
            presenter.run_create_course(
                details,
                secrets,
                progress_cb=view.progress_callback,
                status_cb=view.status_callback,
                done_cb=view.done_callback
            )

    # START EDITION FLOW
    if st.session_state.get("start_automation_edition"):
        details = st.session_state.get("edition_details")
        if details:
            presenter, model = get_presenter_and_model()
            presenter.run_create_edition(
                details,
                secrets,
                progress_cb=view.progress_callback,
                status_cb=view.status_callback,
                done_cb=view.done_callback
            )

