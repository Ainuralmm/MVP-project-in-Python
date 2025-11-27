import streamlit as st
import time

class CoursePresenter:
    def __init__(self, model, view):
        self.model = model
        self.view = view

    def run_create_course(self, course_details):
        try:
            oracle_url = st.secrets['ORACLE_URL']
            oracle_user = st.secrets['ORACLE_USER']
            oracle_pass = st.secrets['ORACLE_PASS']

            ### HASHTAG: DECOUPLED UI COMMANDS (MVP PATTERN)
            # The presenter now TELLS the view what to show, instead of creating UI itself.
            self.view.update_progress("course", "Accesso a Oracle in corso...", 10)
            if not self.model.login(oracle_url, oracle_user, oracle_pass):
                raise Exception("Login fallito. Controlla le credenziali.")

            self.view.update_progress("course", "Creazione del corso...", 50)
            result_message = self.model.create_course(course_details)
            time.sleep(1)

            self.view.update_progress("course", "Processo completato!", 100)
            self.view.show_message("course", result_message)

        except Exception as e:
            error_message = f"‼️ Si è verificato un errore: {str(e)}"
            print(f"Presenter Error: {error_message}")
            self.view.show_message("course", error_message)

        finally:
            print("Presenter: Automation finished. Cleaning up.")
            self.model.close_driver()
            st.session_state.app_state = "IDLE"
            st.rerun()

    def run_create_edition_and_activities(self, edition_details):
        try:
            oracle_url = st.secrets['ORACLE_URL']
            oracle_user = st.secrets['ORACLE_USER']
            oracle_pass = st.secrets['ORACLE_PASS']
            course_name = edition_details['course_name']

            num_activities = len(edition_details.get('activities', []))
            # Use "edition" for UI updates, as it's one combined form
            self.view.update_progress("edition", "Accesso a Oracle...", 10)
            if not self.model.login(oracle_url, oracle_user, oracle_pass):
                raise Exception("Login fallito.")

            self.view.update_progress("edition", "Navigazione alla pagina dei corsi...", 25)
            ### HASHTAG: CORRECTED MODEL CALLS
            # The original code called model methods incorrectly. These are now fixed
            # to match the corrected model.py.
            if not self.model.navigate_to_courses_page():
                raise Exception("Navigazione fallita.")

            self.view.update_progress("edition", f"Ricerca del corso '{course_name}'...", 40)
            if not self.model.search_course(course_name):
                raise Exception(f"Corso '{course_name}' non trovato. Crealo prima.")

            self.view.update_progress("edition", f"Apertura del corso '{course_name}'...", 55)
            if not self.model.open_course_from_list(course_name):
                raise Exception("Impossibile aprire la pagina dei dettagli del corso.")

            self.view.update_progress("edition", "Creazione della nuova edizione...", 70)
            result_message = self.model.create_edition_and_activities(edition_details)
            time.sleep(1)

            self.view.update_progress("edition", "Processo completato!", 100)
            self.view.show_message("edition", result_message)

        except Exception as e:
            error_message = f"‼️ Si è verificato un errore: {str(e)}"
            print(f"Presenter Error: {error_message}")
            self.view.show_message("edition", error_message)

        finally:
            print("Presenter (Edition+Activity): Automation finished. Cleaning up.")
            self.model.close_driver()
            st.session_state.app_state = "IDLE"
            st.rerun()

    ### HASHTAG: ADDED METHOD FOR STUDENT FLOW ###
    def run_add_students(self, student_details):
        try:
            oracle_url = st.secrets['ORACLE_URL']
            oracle_user = st.secrets['ORACLE_USER']
            oracle_pass = st.secrets['ORACLE_PASS']

            # Unpack details for function calls
            course_name = student_details['course_name']
            edition_name = student_details['edition_name']
            edition_publish_date = student_details['edition_publish_date']
            student_list = student_details['students']
            conv_online = student_details['convocazione_online']
            conv_presenza = student_details['convocazione_presenza']
            num_students = len(student_list)

            # Use "student" placeholder for UI updates
            self.view.update_progress("student", "Accesso a Oracle...", 10)
            if not self.model.login(oracle_url, oracle_user, oracle_pass):
                raise Exception("Login fallito.")

            self.view.update_progress("student", f"Navigazione alla pagina dei corsi...", 20)
            if not self.model.navigate_to_courses_page():
                raise Exception("Navigazione fallita.")

            self.view.update_progress("student", f"Ricerca del corso '{course_name}'...", 30)
            if not self.model.search_course(course_name):
                raise Exception(f"Corso '{course_name}' non trovato. Crealo prima.")

            self.view.update_progress("student", f"Apertura del corso '{course_name}'...", 40)
            if not self.model.open_course_from_list(course_name):
                raise Exception("Impossibile aprire la pagina dei dettagli del corso.")

            self.view.update_progress("student", "Apertura scheda 'Edizioni'...", 50)
            # This new helper function just clicks the tab
            if not self.model.open_edizioni_tab():
                raise Exception("Impossibile fare clic sulla scheda 'Edizioni'.")

            self.view.update_progress("student", f"Ricerca dell'edizione '{edition_name}'...", 60)
            ### HASHTAG: THIS IS THE FIX FOR YOUR TypeError ✅ ###
            # Now calling the *correct* model function with the *correct* arguments
            if not self.model._search_and_open_edition(edition_name, edition_publish_date):
                raise Exception(
                    f"Edizione '{edition_name}' (pubbl. {edition_publish_date.strftime('%d/%m/%Y')}) non trovata.")

            self.view.update_progress("student", f"Aggiunta di {num_students} allievi...", 75)
            # Call the model method that *only* adds students
            success = self.model._perform_student_addition_steps(student_list, conv_online, conv_presenza)

            if not success:
                raise Exception("Errore durante l'aggiunta degli allievi.")

            self.view.update_progress("student", "Processo completato!", 100)
            result_message = f"✅🤩 Successo! {len(student_list)} allievi aggiunti all'edizione '{edition_name}'."
            self.view.show_message("student", result_message)

        except Exception as e:
            error_message = f"‼️ Si è verificato un errore: {str(e)}"
            print(f"Presenter Error (Student Add): {error_message}")
            self.view.show_message("student", error_message)

        finally:
            print("Presenter (Student Add): Automation finished. Cleaning up.")
            # Ensure model driver is closed even if login happens inside model method
            if hasattr(self.model, 'driver') and self.model.driver:
                self.model.close_driver()
            st.session_state.app_state = "IDLE"
            st.rerun()