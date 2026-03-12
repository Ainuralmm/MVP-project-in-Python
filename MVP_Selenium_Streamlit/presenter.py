#import pandas as pd
import streamlit as st
import time
#from datetime import datetime
import os
import tempfile

from selenium.webdriver.common.by import By


class CoursePresenter:
    def __init__(self, model, view):
        self.model = model
        self.view = view

    def run_create_course(self, course_details):
        try:
            oracle_url = st.secrets['ORACLE_URL']
            oracle_user = st.secrets['ORACLE_USER']
            oracle_pass = st.secrets['ORACLE_PASS']

            # === STEP 1: LOGIN ===
            self.view.update_progress("course", "Accesso a Oracle in corso...", 10)
            if not self.model.login(oracle_url, oracle_user, oracle_pass):
                raise Exception("Login fallito. Controlla le credenziali.")

            # === STEP 2: NAVIGATE TO COURSES PAGE ===  ✅ ADDED THIS!
            self.view.update_progress("course", "Navigazione alla pagina corsi...", 30)
            if not self.model.navigate_to_courses_page():
                raise Exception("Navigazione alla pagina corsi fallita.")

            # === STEP 3: CHECK IF COURSE ALREADY EXISTS ===  ✅ ADDED THIS!
            course_title = course_details.get('title', '')
            self.view.update_progress("course", f"Verifica se il corso '{course_title}' esiste già...", 50)

            if self.model.search_course(course_title):
                # Course already exists
                result_message = f"⚠️ Il corso '{course_title}' esiste già nel sistema. Nessuna azione eseguita."
                self.view.show_message("course", result_message, show_clear_button=True)
                return

            # === STEP 4: CREATE THE COURSE ===
            self.view.update_progress("course", f"Creazione del corso '{course_title}'...", 70)
            result_message = self.model.create_course(course_details)
            time.sleep(1)

            # === STEP 5: SHOW RESULT ===
            self.view.update_progress("course", "Processo completato!", 100)
            self.view.show_message("course", result_message, show_clear_button=True)

        except Exception as e:
            error_message = f"‼️ Si è verificato un errore: {str(e)}"
            print(f"Presenter Error: {error_message}")
            self.view.show_message("course", error_message, show_clear_button=True)

        finally:
            print("Presenter: Automation finished. Cleaning up.")
            self.model.close()
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
            self.model.close()
            st.session_state.app_state = "IDLE"
            st.rerun()

    def run_batch_edition_creation(self):
        """
        Execute batch creation of multiple editions with their activities.

        FIXED:
        - Uses single progress placeholder
        - Shows results with clear button
        - Automatically returns to IDLE state
        """
        results = []

        # === CREATE SINGLE PROGRESS PLACEHOLDER AT START ===
        progress_placeholder = st.empty()
        status_placeholder = st.empty()

        def update_batch_progress(message, percentage):
            """Helper to update single progress bar"""
            with progress_placeholder.container():
                st.progress(percentage / 100)
            with status_placeholder.container():
                st.info(f"⏳ {message}")

        try:
            oracle_url = st.secrets['ORACLE_URL']
            oracle_user = st.secrets['ORACLE_USER']
            oracle_pass = st.secrets['ORACLE_PASS']

            batch_data = st.session_state.batch_edition_data
            if not batch_data:
                raise Exception("Nessun dato batch trovato.")

            editions = batch_data.get('editions', [])
            total_editions = len(editions)

            if total_editions == 0:
                raise Exception("Nessuna edizione da creare.")

            # === LOGIN ===
            update_batch_progress("Accesso a Oracle...", 5)
            if not self.model.login(oracle_url, oracle_user, oracle_pass):
                raise Exception("Login fallito. Controlla le credenziali.")

            # === NAVIGATE TO COURSES PAGE ===
            update_batch_progress("Navigazione alla pagina Corsi...", 10)
            if not self.model.navigate_to_courses_page():
                raise Exception("Impossibile navigare alla pagina Corsi.")

            # === PROCESS EACH EDITION ===
            for idx, edition in enumerate(editions):
                edition_num = idx + 1
                course_name = edition.get('course_name', 'Unknown')
                edition_title = edition.get('edition_title', '')
                activities = edition.get('activities', [])

                # Calculate progress percentage (10% to 95%)
                progress_pct = int((idx / total_editions) * 85) + 10

                display_name = f"{course_name} - {edition_title}" if edition_title else course_name
                update_batch_progress(
                    f"Creazione edizione {edition_num}/{total_editions}: {display_name}...",
                    progress_pct
                )

                try:
                    success = self.model.create_edition_with_activities_batch(
                        course_name=course_name,
                        edition_title=edition_title,
                        start_date=edition.get('start_date'),
                        end_date=edition.get('end_date'),
                        location=edition.get('location', ''),
                        supplier=edition.get('supplier', ''),
                        price=edition.get('price', ''),
                        description=edition.get('description', ''),
                        activities=activities,
                        return_to_courses_page=True
                    )

                    if success:
                        results.append({
                            'edition': display_name,
                            'status': '✅ Successo',
                            'activities': len(activities)
                        })
                    else:
                        results.append({
                            'edition': display_name,
                            'status': '❌ Creazione fallita',
                            'activities': 0
                        })

                except Exception as e:
                    results.append({
                        'edition': display_name,
                        'status': f'❌ Errore: {str(e)[:50]}',
                        'activities': 0
                    })

            # === FINAL PROGRESS ===
            update_batch_progress("Processo completato!", 100)

        except Exception as e:
            error_message = f"‼️ Errore durante la creazione batch edizioni: {str(e)}"
            print(f"Presenter Error: {error_message}")
            results.append({
                'edition': 'ERRORE GENERALE',
                'status': error_message,
                'activities': 0
            })

        finally:
            # === CLEANUP ===
            print("Presenter: Batch edition automation finished. Cleaning up.")
            self.model.close()

            # Clear progress placeholders
            progress_placeholder.empty()
            status_placeholder.empty()

            # === BUILD SUMMARY MESSAGE ===
            success_count = sum(1 for r in results if '✅' in r.get('status', ''))
            fail_count = len(results) - success_count
            total_activities_created = sum(r.get('activities', 0) for r in results)
            total_editions = len(
                st.session_state.batch_edition_data.get('editions', [])) if st.session_state.batch_edition_data else 0

            summary_parts = [
                f"## 📊 Riepilogo Creazione Batch Edizioni\n",
                f"- **Edizioni create:** {success_count}/{total_editions}",
                f"- **Attività totali create:** {total_activities_created}",
                f"- **Errori:** {fail_count}\n",
                "### Dettagli per edizione:"
            ]

            for r in results:
                summary_parts.append(
                    f"- **{r['edition']}**: {r['status']} ({r['activities']} attività)"
                )

            final_message = "\n".join(summary_parts)

            # Store message in session state for display
            st.session_state.edition_message = final_message

            # Clear batch-specific states
            st.session_state.batch_edition_data = None
            st.session_state.edition_parsed_data = None
            st.session_state.edition_show_summary = False

            # Set flag to show results on Edition tab
            st.session_state.show_edition_results = True

            # Return to IDLE
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
            self.model.close()
            st.session_state.app_state = "IDLE"
            st.rerun()

    ### METHOD FOR STUDENT FLOW
    def run_add_students(self, student_details):
        """
        Execute student addition for a SINGLE edition.

        student_details keys:
            - edition_code (str)
            - students (list[str])

        """
        temp_file_path = None

        try:
            oracle_url = st.secrets['ORACLE_URL']
            oracle_user = st.secrets['ORACLE_USER']
            oracle_pass = st.secrets['ORACLE_PASS']

            edition_code = student_details['edition_code']
            student_list = student_details['students']
            num_students = len(student_list)

            # === CREATE TEMP FILE ===
            self.view.update_progress("student", f"Preparazione elenco {num_students} allievi...", 5)

            temp_file = tempfile.NamedTemporaryFile(
                mode='w', suffix='.txt', prefix='students_',
                delete=False, encoding='utf-8'
            )
            for matricola in student_list:
                temp_file.write(f"{matricola}\n")
            temp_file.close()
            temp_file_path = temp_file.name
            print(f"Presenter: Created temp file: {temp_file_path} ({num_students} students)")

            lista_nome = f"{edition_code}"

            # === LOGIN ===
            self.view.update_progress("student", "Accesso a Oracle...", 10)
            if not self.model.login(oracle_url, oracle_user, oracle_pass):
                raise Exception("Login fallito.")

            # === NAVIGATE TO EDITIONS PAGE ===
            self.view.update_progress("student", "Navigazione alla pagina edizioni...", 20)
            if not self.model.navigate_to_edition_page():
                raise Exception("Navigazione fallita.")

            # === SEARCH EDITION ===
            self.view.update_progress("student", f"Ricerca edizione '{edition_code}'...", 40)
            edition_result = self.model._search_and_open_edition(edition_code)
            if not edition_result:
                raise Exception(f"Edizione '{edition_code}' non trovata.")

            # Extract dates from edition search
            edition_start_date = edition_result.get('start_date') if isinstance(edition_result, dict) else None
            edition_end_date = edition_result.get('end_date') if isinstance(edition_result, dict) else None
            print(f"Presenter: Edition dates - start: {edition_start_date}, end: {edition_end_date}")

            # === ADD STUDENTS ===
            self.view.update_progress("student", f"Caricamento {num_students} allievi...", 65)
            success = self.model._perform_student_addition_steps(
                student_file_path=temp_file_path,
                lista_nome=lista_nome,
                edition_start_date=edition_start_date,
                edition_end_date=edition_end_date,
            )

            # Replace the current success message block with:
            self.view.update_progress("student", "Processo completato!", 100)

            if success:
                result_message = (
                    f"✅🤩 Successo! {num_students} allievi inviati "
                    f"per edizione '{edition_code}'.\n\n"
                    f"Se gli allievi non appaiono subito nella lista, "
                    f"ricontrolla tra qualche minuto — Oracle potrebbe "
                    f"necessitare di tempo per elaborare il file."
                )
            else:
                result_message = (
                    f"⚠️ Processo completato per edizione '{edition_code}', "
                    f"ma non è stato possibile confermare l'aggiunta di {num_students} allievi.\n\n"
                    f"Ricontrolla la lista allievi manualmente tra qualche minuto."
                )
            self.view.show_message("student", result_message)

        except Exception as e:
            error_message = f"‼️ Si è verificato un errore: {str(e)}"
            print(f"Presenter Error (Student Add): {error_message}")
            self.view.show_message("student", error_message)

        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                    print(f"Presenter: Deleted temp file: {temp_file_path}")
                except:
                    pass

            print("Presenter (Student Add): Finished. Cleaning up.")
            if hasattr(self.model, 'driver') and self.model.driver:
                self.model.close()
            st.session_state.app_state = "IDLE"
            st.rerun()

    # Multiple editions — used by Excel with multiple edition codes
    def run_add_students_batch(self):
        """
        Execute student addition for MULTIPLE editions sequentially.

        Reads from st.session_state.batch_student_data:
            - editions: list of {edition_code, students}

        """
        results = []
        progress_placeholder = st.empty()
        status_placeholder = st.empty()
        temp_file_paths = []  # Track all temp files for cleanup

        def update_progress(message, percentage):
            with progress_placeholder.container():
                st.progress(percentage / 100)
            with status_placeholder.container():
                st.info(f"⏳ {message}")

        try:
            oracle_url = st.secrets['ORACLE_URL']
            oracle_user = st.secrets['ORACLE_USER']
            oracle_pass = st.secrets['ORACLE_PASS']

            batch_data = st.session_state.batch_student_data
            if not batch_data:
                raise Exception("Nessun dato batch trovato.")

            editions = batch_data.get('editions', [])
            total_editions = len(editions)

            if total_editions == 0:
                raise Exception("Nessuna edizione da processare.")

            # === LOGIN (once for all editions) ===
            update_progress("Accesso a Oracle...", 5)
            if not self.model.login(oracle_url, oracle_user, oracle_pass):
                raise Exception("Login fallito.")

            # === NAVIGATE (once) ===
            update_progress("Navigazione alla pagina edizioni...", 10)
            if not self.model.navigate_to_edition_page():
                raise Exception("Navigazione fallita.")

            # === PROCESS EACH EDITION ===
            for idx, edition in enumerate(editions):
                edition_code = edition['edition_code']
                student_list = edition['students']
                num_students = len(student_list)
                edition_num = idx + 1

                progress_pct = int((idx / total_editions) * 80) + 15
                update_progress(
                    f"Edizione {edition_num}/{total_editions}: '{edition_code}' "
                    f"({num_students} allievi)...",
                    progress_pct
                )

                try:
                    # Create temp file for this edition
                    temp_file = tempfile.NamedTemporaryFile(
                        mode='w', suffix='.txt', prefix=f'students_{edition_code}_',
                        delete=False, encoding='utf-8'
                    )
                    for matricola in student_list:
                        temp_file.write(f"{matricola}\n")
                    temp_file.close()
                    temp_file_paths.append(temp_file.name)

                    lista_nome = f"{edition_code}"

                    # Search for edition
                    edition_result = self.model._search_and_open_edition(edition_code)
                    if not edition_result:
                        results.append({
                            'edition': edition_code,
                            'status': '❌ Edizione non trovata',
                            'students': 0
                        })
                        continue

                    edition_start_date = edition_result.get('start_date') if isinstance(edition_result, dict) else None
                    edition_end_date = edition_result.get('end_date') if isinstance(edition_result, dict) else None

                    success = self.model._perform_student_addition_steps(
                        student_file_path=temp_file.name,
                        lista_nome=lista_nome,
                        edition_start_date=edition_start_date,
                        edition_end_date=edition_end_date,
                    )


                    if success:
                        results.append({
                            'edition': edition_code,
                            'status': '✅ Inviato',
                            'students': num_students
                        })
                    else:
                        results.append({
                            'edition': edition_code,
                            'status': '⚠️ Invio non confermato',
                            'students': num_students  # still num_students, may have been submitted
                        })

                    # Navigate back to edition search page for next iteration
                    if idx < total_editions - 1:
                        if not self.model._click_back_to_edition_search():
                            print("   ⚠️ Back button failed, trying full navigation...")
                            try:
                                self.model.navigate_to_edition_page()
                            except:
                                print("   ❌ Could not return to edition search")


                except Exception as e:
                                error_msg = str(e)[:80]
                                print(f"   ❌ Error for edition '{edition_code}': {error_msg}")
                                results.append({

                                    'edition': edition_code,
                                    'status': f'❌ Errore: {error_msg}',
                                    'students': 0

                                })

                                # Try to recover: close any dialogs and go back

                                try:
                                    # Close any open dialog
                                    cancel_xpaths = [

                                        "//button[contains(@id, ':d3::cancel')]",
                                        "//button[text()='Annulla' or text()='Cancel']",
                                        "//button[contains(@id, '::cancel')]",

                                    ]

                                    for xpath in cancel_xpaths:

                                        try:

                                            cancel_btn = self.model.driver.find_element(By.XPATH, xpath)
                                            cancel_btn.click()
                                            print("   🔄 Closed open dialog")
                                            time.sleep(2)
                                            break

                                        except:
                                            continue

                                except:

                                    pass



            # === FINAL PROGRESS ===
            update_progress("Processo completato!", 100)

        except Exception as e:
            error_message = f"‼️ Errore batch: {str(e)}"
            print(f"Presenter Error: {error_message}")
            results.append({
                'edition': 'ERRORE GENERALE',
                'status': error_message,
                'students': 0
            })

        finally:
            # === CLEANUP ===
            print("Presenter (Batch Students): Finished. Cleaning up.")
            self.model.close()

            # Delete all temp files
            for path in temp_file_paths:
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except:
                        pass

            # Clear progress
            progress_placeholder.empty()
            status_placeholder.empty()

            # === BUILD SUMMARY ===
            success_count = sum(1 for r in results if '✅' in r.get('status', ''))
            fail_count = len(results) - success_count
            total_students_added = sum(r.get('students', 0) for r in results)

            summary_parts = [
                f"## 📊 Riepilogo Aggiunta Allievi Batch\n",
                f"- **Edizioni processate:** {success_count}/{total_editions}",
                f"- **Allievi totali inviati:** {total_students_added}",
                f"- **Errori:** {fail_count}\n",
                f"Oracle potrebbe impiegare qualche minuto per elaborare i file.\n",
                "### Dettagli:"
            ]

            for r in results:
                summary_parts.append(
                    f"- **{r['edition']}**: {r['status']} ({r['students']} allievi)"
                )

            final_message = "\n".join(summary_parts)

            # Store and display
            st.session_state.student_message = final_message
            st.session_state.batch_student_data = None
            st.session_state.student_parsed_data = None
            st.session_state.student_show_summary = False

            st.session_state.app_state = "IDLE"
            st.rerun()

    def run_verify_students(self):
        """
        Verify that students exist in Oracle editions.
        Reads from st.session_state.verify_student_data (same format as batch).
        """
        results = []
        progress_placeholder = st.empty()
        status_placeholder = st.empty()

        def update_progress(message, percentage):
            with progress_placeholder.container():
                st.progress(percentage / 100)
            with status_placeholder.container():
                st.info(f"⏳ {message}")

        try:
            oracle_url = st.secrets['ORACLE_URL']
            oracle_user = st.secrets['ORACLE_USER']
            oracle_pass = st.secrets['ORACLE_PASS']

            verify_data = st.session_state.verify_student_data
            if not verify_data:
                raise Exception("Nessun dato di verifica trovato.")

            editions = verify_data.get('editions', [])
            total_editions = len(editions)

            if total_editions == 0:
                raise Exception("Nessuna edizione da verificare.")

            # === LOGIN ===
            update_progress("Accesso a Oracle...", 5)
            if not self.model.login(oracle_url, oracle_user, oracle_pass):
                raise Exception("Login fallito.")

            # === NAVIGATE ===
            update_progress("Navigazione alla pagina edizioni...", 10)
            if not self.model.navigate_to_edition_page():
                raise Exception("Navigazione fallita.")

            # === VERIFY EACH EDITION ===
            for idx, edition in enumerate(editions):
                edition_code = edition['edition_code']
                expected_students = edition['students']
                num_students = len(expected_students)
                edition_num = idx + 1

                progress_pct = int((idx / total_editions) * 80) + 15
                update_progress(
                    f"Verifica edizione {edition_num}/{total_editions}: '{edition_code}' "
                    f"({num_students} allievi)...",
                    progress_pct
                )

                try:
                    # Search and open edition
                    if not self.model._search_and_open_edition(edition_code):
                        results.append({
                            'edition': edition_code,
                            'expected': num_students,
                            'found': 0,
                            'not_found': num_students,
                            'not_found_list': expected_students,
                            'status': '❌ Edizione non trovata'
                        })
                        continue

                    # Verify students
                    verify_result = self.model._verify_students_in_edition(
                        edition_code, expected_students)

                    found_count = len(verify_result['found'])
                    not_found_count = len(verify_result['not_found'])

                    if not_found_count == 0:
                        status = f'✅ Tutti {found_count} trovati'
                    elif found_count == 0:
                        status = f'❌ Nessuno trovato (0/{num_students})'
                    else:
                        status = f'⚠️ {found_count}/{num_students} trovati'

                    results.append({
                        'edition': edition_code,
                        'expected': num_students,
                        'found': found_count,
                        'not_found': not_found_count,
                        'not_found_list': verify_result['not_found'],
                        'found_list': verify_result['found'],
                        'status': status
                    })

                    # Navigate back for next edition
                    if idx < total_editions - 1:
                        if not self.model._click_back_to_edition_search():
                            print("   ⚠️ Back button failed, trying full navigation...")
                            try:
                                self.model.navigate_to_edition_page()
                            except:
                                print("   ❌ Could not return to edition search")

                except Exception as e:
                    results.append({
                        'edition': edition_code,
                        'expected': num_students,
                        'found': 0,
                        'not_found': num_students,
                        'not_found_list': expected_students,
                        'status': f'❌ Errore: {str(e)[:50]}'
                    })

            # === FINAL ===
            update_progress("Verifica completata!", 100)

        except Exception as e:
            error_message = f"‼️ Errore verifica: {str(e)}"
            print(f"Presenter Error: {error_message}")
            results.append({
                'edition': 'ERRORE GENERALE',
                'expected': 0,
                'found': 0,
                'not_found': 0,
                'not_found_list': [],
                'status': error_message
            })

        finally:
            print("Presenter (Verify Students): Finished. Cleaning up.")
            self.model.close()

            progress_placeholder.empty()
            status_placeholder.empty()

            # === BUILD SUMMARY ===
            total_expected = sum(r.get('expected', 0) for r in results)
            total_found = sum(r.get('found', 0) for r in results)
            total_not_found = sum(r.get('not_found', 0) for r in results)
            all_ok = all('✅' in r.get('status', '') for r in results)

            summary_parts = [
                f"## 🔍 Riepilogo Verifica Allievi\n",
                f"- **Edizioni verificate:** {len(results)}",
                f"- **Allievi totali attesi:** {total_expected}",
                f"- **Trovati nel sistema:** {total_found}",
                f"- **Non trovati:** {total_not_found}\n",
            ]

            if all_ok:
                summary_parts.append("### ✅ Tutti gli allievi sono presenti nel sistema!\n")
            elif total_not_found > 0:
                summary_parts.append(
                    "### ⚠️ Alcuni allievi non sono stati trovati.\n"
                    "Oracle potrebbe necessitare di più tempo per elaborare. "
                    "Riprova tra qualche minuto.\n"
                )

            summary_parts.append("### Dettagli per edizione:")

            for r in results:
                summary_parts.append(
                    f"- **{r['edition']}**: {r['status']}"
                )
                # Show not-found matricole if any
                not_found_list = r.get('not_found_list', [])
                if not_found_list and len(not_found_list) <= 10:
                    matricole_str = ', '.join(not_found_list)
                    summary_parts.append(f"  - Non trovati: `{matricole_str}`")
                elif not_found_list:
                    first_5 = ', '.join(not_found_list[:5])
                    summary_parts.append(
                        f"  - Non trovati: `{first_5}` ... e altri {len(not_found_list) - 5}")

            final_message = "\n".join(summary_parts)

            st.session_state.student_message = final_message
            st.session_state.verify_student_data = None
            st.session_state.student_parsed_data = None
            st.session_state.student_show_summary = False

            st.session_state.app_state = "IDLE"
            st.rerun()