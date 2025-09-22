import streamlit as st
from datetime import date

class CourseView:
    def __init__(self):
        st.set_page_config(layout='centered')
        st.image("logo-agsm.jpg", width=200)  # Always at the top
        st.title("Oracle Course Management Automator")

    def render_form(self):
        # This method displays the input form and returns the collected data.
        st.header("Enter Course Details")

        # We use a Streamlit form to group the inputs.
        # The code inside 'with form:' will only run when the submit button is pressed.
        with st.form(key='course_creation_form'):
            # These are the input fields for the user.
            course_title = st.text_input("Course Title", "Example: Data Analytics")
            programme = st.text_area("Programme Details", "OPTIONAL FIELD: IF NEEDED, INSERT IMPORTANT INFORMATION about the course")
            short_desc = st.text_input("Short Description", "Example: Data Analytics Informatica")
            start_date = st.date_input("Publication Start Date", date(2023, 1, 1))

            # This is the button that will trigger the automation.
            submitted = st.form_submit_button("Create Course in Oracle")

        #when the button is pressed,'submitted' becomes True
        if submitted:
            #package the ollected data into a dict
            course_details = {
                "title": course_title,
                "programme": programme,
                "short_description": short_desc,
                "start_date": start_date
            }
            st.session_state["course_details"] = course_details
            return course_details

        #if the button has not been pressed,return None
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

#view=CourseView()
#view.render_form()#call the method that renders the form