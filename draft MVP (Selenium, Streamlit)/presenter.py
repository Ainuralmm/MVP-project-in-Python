# presenter.py
# --- THE PRESENTER ---
# This is the middleman that connects the View and the Model.
# It takes user actions from the View (e.g., button click).
# It tells the Model what to do (e.g., run the automation).
# It takes the result from the Model and tells the View what to display.

import streamlit as st


class CoursePresenter:
    def __init__(self, model, view):
        # The presenter holds references to the model and the view.
        self.model = model
        self.view = view

    def run(self):
        # This is the main method that runs the application logic.

        # 1. Render the form and wait for user input.
        # The view.render_form() will return the data dictionary
        # only when the user clicks the submit button.
        course_details = self.view.render_form()

        # 2. Check if the form was submitted.
        if course_details:
            # If we have details, it means the user clicked the button.
            # We get the credentials securely from Streamlit's secrets management.
            # You need to create a .streamlit/secrets.toml file for this.
            oracle_url = st.secrets["ORACLE_URL"]
            oracle_user = st.secrets["ORACLE_USER"]
            oracle_pass = st.secrets["ORACLE_PASS"]

            # 3. Use a spinner to show the user that something is happening.
            with st.spinner("Automation in progress... Please wait."):
                try:
                    # 4. Tell the model to perform the automation steps.
                    login_success = self.model.login(oracle_url, oracle_user, oracle_pass)
                    if login_success:
                        nav_success = self.model.navigate_to_course_creation()
                        if nav_success:
                            # Pass the course data from the View to the Model.
                            result_message = self.model.create_course(course_details)
                            # 5. Get the result from the Model and tell the View to display it.
                            self.view.display_message(result_message)
                        else:
                            self.view.display_message("Error: Failed to navigate to the course page.")
                    else:
                        self.view.display_message("Error: Login failed. Please check credentials.")

                except Exception as e:
                    # Handle any unexpected errors during the process.
                    self.view.display_message(f"An unexpected error occurred: {e}")

                finally:
                    # 6. Crucially, always ensure the browser is closed.
                    self.model.close_driver()