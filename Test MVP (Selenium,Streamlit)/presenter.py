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

            #UI elements for progress and status updates
            progress = st.progress(0)
            status = st.empty()

            #3.A spinner to show the user that process is proceeding
            with st.spinner('Automation in progress...Please wait'):
                try:
                    #---Step1: Login ---
                    status.info("🔑Logging into Oracle...")
                    progress.progress(10)
                    #telling the model to perform the authorising process
                    login_success = self.model.login(oracle_url,oracle_user,oracle_pass)
                    if login_success:
                        #self.view.display_message('Logged in Successfully')
                        status.success('✅🤩Logged in Successfully')
                    else:
                        self.view.display_message('Login Failed. Please check your credentials.')
                        status.error('❌😭Login Failed. Please check your credentials.')
                        return
                    #---Step2:Navigate to course creation ---
                    status.info('🧭🚶Navigating to Course Creation Page...')
                    progress.progress(30)
                    nav_success = self.model.navigate_to_course_creation()
                    if nav_success:
                        #self.view.display_message(result_message)
                        status.success('👣💃🕺Reached Course Creation Page')
                    else:
                        st.view.display_message('Failed to navigate to the course page')
                        status.error('❌😭Failed to navigate to the course page')
                        return
                    progress.progress(50)
                    #---Step3: Create the course---
                    course_name=course_details['title']
                    status.info(f"📝 Creating the course: **{course_name}** ...")
                    progress.progress(70)
                    result_message = self.model.create_course(course_details)

                    #handle model message
                    if result_message and "Error" in result_message:
                        status.error(f'❌😭{result_message}')
                    else:
                        status.success(f"{result_message or 'Course created successfully!'}")

                    progress.progress(100)



                except Exception as e:
                    self.view.display_message(f"⚠️👩🏻‍✈️An unexpected error occurred: {e}")

                finally:
                    self.model.close_driver()


