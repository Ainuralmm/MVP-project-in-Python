#import pandas as pd
import streamlit as st
import time
#from datetime import datetime
import os
import tempfile

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
            - convocazione_online (bool)
            - convocazione_presenza (bool)
        """
        temp_file_path = None

        try:
            oracle_url = st.secrets['ORACLE_URL']
            oracle_user = st.secrets['ORACLE_USER']
            oracle_pass = st.secrets['ORACLE_PASS']

            edition_code = student_details['edition_code']
            student_list = student_details['students']
            conv_online = student_details['convocazione_online']
            conv_presenza = student_details['convocazione_presenza']
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
            if not self.model._search_and_open_edition(edition_code):
                raise Exception(f"Edizione '{edition_code}' non trovata.")

            # === ADD STUDENTS ===
            self.view.update_progress("student", f"Caricamento {num_students} allievi...", 65)
            success = self.model._perform_student_addition_steps(
                student_file_path=temp_file_path,
                lista_nome=lista_nome,
                conv_online=conv_online,
                conv_presenza=conv_presenza
            )

            # Replace the current success message block with:
            if not success:
                # Don't raise — students may have been submitted but notifications failed
                result_message = (
                    f"⚠️ {num_students} allievi inviati per edizione '{edition_code}'.\n\n"
                    f"L'invio è stato completato ma le notifiche non sono state confermate. "
                    f"Oracle potrebbe impiegare qualche minuto per elaborare il file. "
                    f"Controlla manualmente tra 5-10 minuti."
                )
                self.view.show_message("student", result_message)
            else:
                self.view.update_progress("student", "Processo completato!", 100)
                result_message = (
                    f"✅🤩 Successo! {num_students} allievi caricati "
                    f"per edizione '{edition_code}'."
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
            - convocazione_online (bool)
            - convocazione_presenza (bool)
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
            conv_online = batch_data.get('convocazione_online', True)
            conv_presenza = batch_data.get('convocazione_presenza', True)
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
                    if not self.model._search_and_open_edition(edition_code):
                        results.append({
                            'edition': edition_code,
                            'status': '❌ Edizione non trovata',
                            'students': 0
                        })
                        continue

                    # Add students
                    success = self.model._perform_student_addition_steps(
                        student_file_path=temp_file.name,
                        lista_nome=lista_nome,
                        conv_online=conv_online,
                        conv_presenza=conv_presenza
                    )

                    if success:
                        results.append({
                            'edition': edition_code,
                            'status': '✅ Successo',
                            'students': num_students
                        })
                    else:
                        results.append({
                            'edition': edition_code,
                            'status': '❌ Errore durante aggiunta',
                            'students': 0
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
                    results.append({
                        'edition': edition_code,
                        'status': f'❌ Errore: {str(e)[:50]}',
                        'students': 0
                    })

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
                f"- **Allievi totali aggiunti:** {total_students_added}",
                f"- **Errori:** {fail_count}\n",
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