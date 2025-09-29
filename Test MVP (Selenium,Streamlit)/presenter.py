#presenter connects the View and the Model
import streamlit as st

class CoursePresenter:
    def __init__(self,model,view):
        #the presenter holds references to the model and the view
        self.model = model
        self.view = view

    def run(self,course_details):
        #main method that runs the application
        #1.render the form and wait for user input after clicking submit
        if not course_details:
            return
        #course_details = self.view.render_form()
        #2.if the form was submitted
        #if course_details:
            #get the credentials securely from Streamlit's secrets management
        oracle_url=st.secrets['ORACLE_URL']
        oracle_user=st.secrets['ORACLE_USER']
        oracle_pass=st.secrets['ORACLE_PASS']

        #UI elements for progress and status updates
        progress = st.progress(0)
        status = st.empty()

        #3.A spinner to show the user that process is proceeding
        with st.spinner('Automazione in corso... Attendere prego'):
            try:
                #---Step1: Login ---
                status.info("🔑Accesso a Oracle in corso...")
                progress.progress(10)
                #telling the model to perform the authorising process
                login_success = self.model.login(oracle_url,oracle_user,oracle_pass)
                if login_success:
                    #self.view.display_message('Logged in Successfully')
                    status.success('✅🤩Accesso effettuato con successo')
                else:
                    self.view.display_message('Login Failed. Please check your credentials.')
                    status.error('❌😭 Accesso fallito. Si prega di controllare le credenziali.')
                    return
                #---Step2:Navigate to course creation ---
                status.info('🧭🚶Navigazione verso la pagina di creazione del corso in corso...')
                progress.progress(30)
                nav_success = self.model.navigate_to_course_creation()
                if nav_success:
                    #self.view.display_message(result_message)
                    status.success('👣💃🕺Pagina di creazione del corso raggiunta')
                else:
                    st.view.display_message('Failed to navigate to the course page')
                    status.error('❌😭Impossibile navigare verso la pagina del corso')
                    return
                progress.progress(50)
                #---Step3: Create the course---
                course_name=course_details['title']
                status.info(f"🔍 Ricerca del corso:: '**{course_name}**'in corso. 👌🏻😎Altrimenti il corso verrà creato")
                progress.progress(70)
                result_message = self.model.create_course(course_details)

                #handle model message
                if result_message and "Error" in result_message:
                    status.error(f'❌😭{result_message}')
                else:
                    status.success(f"{result_message or 'Corso creato con successo!'}")

                progress.progress(100)

            except Exception as e:
                self.view.display_message(f"⚠️👩🏻‍✈️An unexpected error occurred: {e}")

            finally:
                try:
                    self.model.close_driver()
                except Exception:
                    pass

                    # Reset session flags so the UI becomes interactive again
                st.session_state["automation_running"] = False
                st.session_state["start_automation"] = False
                # optionally keep course_details or remove it:
                # st.session_state["course_details"] = None

                # Force a rerun so the button re-enables and the UI refreshes
                st.rerun()
