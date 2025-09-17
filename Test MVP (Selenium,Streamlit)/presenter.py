#presenter connects the View and the Model
import streamlit as st

class CoursePresenter:
    def __init__(self,model,view):
        #the presenter holds references to the model and the view
        self.model = model
        self.view = view

    def run(self):
        #main method that runs the application
        #1.render the form and wait for user input after clicking submit
        course_details = self.view.render_form()
        #2.if the form was submitted
        if course_details:
            #get the credentials securely from Streamlit's secrets management
            oracle_url=st.secrets['ORACLE_URL']
            oracle_user=st.secrets['ORACLE_USER']
            oracle_pass=st.secrets['ORACLE_PASS']

            #3.A spinner to show the user that process is proceeding
            with st.spinner('Automation in progress...Please wait'):
                try:
                    #telling the model to perform the authorising process
                    login_success = self.model.login(oracle_url,oracle_user,oracle_pass)
                    if login_success:
                        self.view.display_message('Login Successful')
                        nav_success = self.model.navigate_to_course_creation()
                        if nav_success:
                            #result_message = self.model.create_course(course_details)
                            self.view.display_message('Navigation to course page went successfully')
                        else:
                            st.view.display_message('Failed to navigate to the course page')
                    else:
                        self.view.display_message('Login Failed')
                except Exception as e:
                    self.view.display_message(f"An unexpected error occurred: {e}")

                finally:
                    self.model.close_driver()


