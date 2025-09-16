# view.py
# --- THE VIEW ---
# This file is responsible for the User Interface (UI).
# It's built using Streamlit.
# Its only job is to display widgets (like text boxes and buttons)
# and collect input from the user. It does not know about Selenium.

import streamlit as st
from datetime import date


class CourseView:
    def __init__(self):
        # The constructor sets up the page title and layout.
        st.set_page_config(layout="centered")
        st.title("Oracle Course Creation Automator 🤖")

    def render_form(self):
        # This method displays the input form and returns the collected data.

        st.header("Enter Course Details")

        # We use a Streamlit form to group the inputs.
        # The code inside 'with form:' will only run when the submit button is pressed.
        with st.form(key='course_form'):
            # These are the input fields for the user.
            course_title = st.text_input("Course Title", "Data Analytics")
            programme = st.text_area("Programme Details", "OPTIONAL FIELD, IF NEEDED INSERT IMPORTANT INFORMATION")
            short_desc = st.text_input("Short Description", "Data Analytics Informatica")
            start_date = st.date_input("Publication Start Date", date(2023, 1, 1))

            # This is the button that will trigger the automation.
            submitted = st.form_submit_button("Create Course in Oracle")

        # When the button is pressed, 'submitted' becomes True.
        if submitted:
            # We package the collected data into a dictionary.
            # This structured data is easy to pass to the Presenter.
            course_details = {
                "title": course_title,
                "programme": programme,
                "short_description": short_desc,
                "start_date": start_date
            }
            return course_details

        # If the button has not been pressed, we return None.
        return None

    def display_message(self, message):
        # This method shows a message to the user.
        # The Presenter will call this method to provide feedback.
        if "Success" in message:
            st.success(message)
        elif "Error" in message:
            st.error(message)
        else:
            st.info(message)