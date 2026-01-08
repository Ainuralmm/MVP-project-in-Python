import streamlit as st
import time
from datetime import datetime

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

    def run_create_batch_courses(self, batch_data):
        """
        Create multiple courses sequentially from batch data.

        WHY: Process multiple courses from Excel in one operation.
        Shows progress and handles errors gracefully.

        Args:
            batch_data: Dictionary with 'courses' list from Excel parser
        """
        try:
            oracle_url = st.secrets['ORACLE_URL']
            oracle_user = st.secrets['ORACLE_USER']
            oracle_pass = st.secrets['ORACLE_PASS']

            courses = batch_data['courses']
            total_courses = len(courses)
            continue_on_error = st.session_state.get('batch_continue_on_error', True)

            # INITIALIZE RESULTS TRACKING ###
            results = {
                'successful': [],
                'failed': [],
                'skipped': []
            }

            # LOGIN ONCE FOR ALL COURSES ###
            self.view.update_progress("course", f"Accesso a Oracle...", 5)
            if not self.model.login(oracle_url, oracle_user, oracle_pass):
                raise Exception("Login fallito. Controlla le credenziali.")

            # ### NAVIGATE TO COURSES PAGE ONCE ###
            self.view.update_progress("course", "Navigazione alla pagina corsi...", 10)
            if not self.model.navigate_to_courses_page():
                raise Exception("Navigazione alla pagina corsi fallita")

            # ### PROCESS EACH COURSE ###
            for idx, course in enumerate(courses, 1):
                course_title = course['title']
                progress_pct = int((idx / total_courses) * 85) + 10

                self.view.update_progress(
                    "course",
                    f"Creazione corso {idx}/{total_courses}: '{course_title}'...",
                    progress_pct
                )

                try:
                    # ### CHECK IF COURSE EXISTS (search resets after each search) ###
                    if self.model.search_course(course_title):
                        results['skipped'].append({
                            'course': course_title,
                            'reason': 'Corso già esistente'
                        })
                        print(f"⚠️ Corso '{course_title}' già esiste. Saltato.")
                        continue

                    # ### CREATE COURSE
                    # search_course leaves us on the Corsi page, ready to create
                    course_details = {
                        'title': course['title'],
                        'programme': course.get('programme', ''),
                        'short_description': course['short_description'],
                        'start_date': course['start_date']
                    }

                    result_message = self.model.create_course(course_details)

                    if "✅" in result_message or "Successo" in result_message:
                        results['successful'].append(course_title)
                        print(f"✅ Corso '{course_title}' creato con successo.")


                    else:
                        results['failed'].append({
                            'course': course_title,
                            'error': result_message
                        })
                        if not continue_on_error:
                            raise Exception(f"Creazione fallita: {result_message}")

                    time.sleep(0.5)

                except Exception as course_error:
                    error_msg = str(course_error)
                    results['failed'].append({
                        'course': course_title,
                        'error': str(course_error) #error_msg
                    })

                    print(f"❌ Errore con corso '{course_title}': {error_msg}")

                    if not continue_on_error:
                        # Stop processing if user chose not to continue on error
                        break

            # ### HASHTAG: FINAL PROGRESS UPDATE ###
            self.view.update_progress("course", "Processo completato!", 100)

            # ### HASHTAG: GENERATE SUMMARY MESSAGE ###
            summary_parts = []

            if results['successful']:
                summary_parts.append(
                    f"✅ **{len(results['successful'])} corsi creati con successo:**\n" +
                    "\n".join([f"  - {c}" for c in results['successful']])
                )

            if results['skipped']:
                summary_parts.append(
                    f"\n⚠️ **{len(results['skipped'])} corsi saltati:**\n" +
                    "\n".join([f"  - {r['course']}: {r['reason']}" for r in results['skipped']])
                )

            if results['failed']:
                summary_parts.append(
                    f"\n❌ **{len(results['failed'])} corsi falliti:**\n" +
                    "\n".join([f"  - {r['course']}: {r['error']}" for r in results['failed']])
                )

            final_message = "\n\n".join(summary_parts)

            self.view.show_message("course", final_message)

        except Exception as e:
            error_message = f"‼️ Errore durante la creazione batch: {str(e)}"
            print(f"Presenter Error: {error_message}")
            self.view.show_message("course", error_message)

        finally:
            print("Presenter: Batch automation finished. Cleaning up.")
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