import streamlit as st
from model import OracleAutomator
from view import CourseView
from presenter import CoursePresenter

if __name__ == "__main__":
    #path of to Edge Webdriver
    DRIVER_PATH = "/Users/ainuralmukambetova/PCDocuments/AGSM/edgedriver_mac64_m1/msedgedriver"

    view = CourseView()
    headless, debug_mode, debug_pause = view.get_user_options()

    # Render the form (this will return None normally; submission triggers a rerun)
    _ = view.render_form()

    # Start automation only when the user submitted and the form set this flag
    if st.session_state.get("start_automation"):

        course_details = st.session_state.get("course_details")
        if  course_details:
            model = OracleAutomator(driver_path = DRIVER_PATH,
                            debug_mode = debug_mode, # pause for visual checks;  debug_mode=False -> all the pauses will be disabled instantly
                            debug_pause = debug_pause, # how long to pause in seconds
                            headless = headless)# set to True → browser hidden, False → browser visible

            presenter = CoursePresenter(model,view)

            #start the application
            presenter.run(course_details)

        # The presenter finished, which set automation_running = False and
        # needs_rerun = True. We now trigger the final rerun immediately.
        if st.session_state.get("needs_rerun"):
            st.session_state["needs_rerun"] = False
            st.rerun()  # <--- THIS IS THE FINAL RERUN THAT REDRAWS THE BUTTON
    else:
        # safety: clear flag to avoid loop if something missing
        st.session_state["start_automation"] = False

