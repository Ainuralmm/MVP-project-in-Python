import streamlit as st
import time
import os
import tempfile
from datetime import datetime
from selenium.webdriver.common.by import By


class CoursePresenter:
    def __init__(self, model, view):
        self.model = model
        self.view = view

    def _add_timestamp(self, message: str, start_time) -> str:
        """
        Wrap a result message with completion timestamp and duration.
        Used so users always know WHEN an operation finished.
        """
        elapsed = datetime.now() - start_time
        elapsed_min = int(elapsed.total_seconds() // 60)
        elapsed_sec = int(elapsed.total_seconds() % 60)
        completion_time = datetime.now().strftime("%d/%m/%Y %H:%M")
        return (
            f"🕓 **Operazione completata** il {completion_time} "
            f"(durata: {elapsed_min} min {elapsed_sec} sec)\n\n"
            f"{message}"
        )

    # ──────────────────────────────────────────────────────────────────
    # COURSE — SINGLE
    # ──────────────────────────────────────────────────────────────────
    def run_create_course(self, course_details):
        operation_start_time = datetime.now()
        result_message = ""

        try:
            oracle_url = st.secrets['ORACLE_URL']
            oracle_user = st.session_state.oracle_username
            oracle_pass = st.session_state.oracle_password
            if not oracle_user or not oracle_pass:
                raise Exception("Credenziali Oracle mancanti. Effettua nuovamente il login.")

            # === STEP 1: LOGIN ===
            self.view.update_progress("course", "Accesso a Oracle in corso...", 10)
            if not self.model.login(oracle_url, oracle_user, oracle_pass):
                raise Exception("Login fallito. Controlla le credenziali.")

            # === STEP 2: NAVIGATE TO COURSES PAGE ===
            self.view.update_progress("course", "Navigazione alla pagina corsi...", 30)
            if not self.model.navigate_to_courses_page():
                raise Exception("Navigazione alla pagina corsi fallita.")

            # === STEP 3: CHECK IF COURSE ALREADY EXISTS ===
            course_title = course_details.get('title', '')
            self.view.update_progress("course", f"Verifica se il corso '{course_title}' esiste già...", 50)

            if self.model.search_course(course_title):
                result_message = f"⚠️ Il corso '{course_title}' esiste già nel sistema. Nessuna azione eseguita."
                self.view.show_message(
                    "course",
                    self._add_timestamp(result_message, operation_start_time),
                    show_clear_button=True
                )
                return

            # === STEP 4: CREATE THE COURSE ===
            self.view.update_progress("course", f"Creazione del corso '{course_title}'...", 70)
            result_message = self.model.create_course(course_details)
            time.sleep(1)

            # === STEP 5: SHOW RESULT ===
            self.view.update_progress("course", "Processo completato!", 100)
            self.view.show_message(
                "course",
                self._add_timestamp(result_message, operation_start_time),
                show_clear_button=True
            )

        except Exception as e:
            error_message = f"‼️ Si è verificato un errore: {str(e)}"
            print(f"Presenter Error: {error_message}")
            self.view.show_message(
                "course",
                self._add_timestamp(error_message, operation_start_time),
                show_clear_button=True
            )

        finally:
            print("Presenter: Automation finished. Cleaning up.")
            self.model.close()
            st.session_state.app_state = "IDLE"
            st.rerun()

    # ──────────────────────────────────────────────────────────────────
    # COURSE — BATCH
    # ──────────────────────────────────────────────────────────────────
    def run_create_batch_courses(self, batch_data):
        """
        Create multiple courses sequentially from batch data.
        """
        operation_start_time = datetime.now()

        try:
            oracle_url = st.secrets['ORACLE_URL']
            oracle_user = st.session_state.oracle_username
            oracle_pass = st.session_state.oracle_password
            if not oracle_user or not oracle_pass:
                raise Exception("Credenziali Oracle mancanti. Effettua nuovamente il login.")

            courses = batch_data['courses']
            total_courses = len(courses)
            continue_on_error = st.session_state.get('batch_continue_on_error', True)

            results = {'successful': [], 'failed': [], 'skipped': []}

            self.view.update_progress("course", "Accesso a Oracle...", 5)
            if not self.model.login(oracle_url, oracle_user, oracle_pass):
                raise Exception("Login fallito. Controlla le credenziali.")

            self.view.update_progress("course", "Navigazione alla pagina corsi...", 10)
            if not self.model.navigate_to_courses_page():
                raise Exception("Navigazione alla pagina corsi fallita")

            for idx, course in enumerate(courses, 1):
                course_title = course['title']
                progress_pct = int((idx / total_courses) * 85) + 10

                self.view.update_progress(
                    "course",
                    f"Creazione corso {idx}/{total_courses}: '{course_title}'...",
                    progress_pct
                )

                try:
                    if self.model.search_course(course_title):
                        results['skipped'].append({
                            'course': course_title,
                            'reason': 'Corso già esistente'
                        })
                        print(f"⚠️ Corso '{course_title}' già esiste. Saltato.")
                        continue

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
                        'error': str(course_error)
                    })
                    print(f"❌ Errore con corso '{course_title}': {error_msg}")
                    if not continue_on_error:
                        break

            self.view.update_progress("course", "Processo completato!", 100)

            # Build summary
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
            self.view.show_message(
                "course",
                self._add_timestamp(final_message, operation_start_time)
            )

        except Exception as e:
            error_message = f"‼️ Errore durante la creazione batch: {str(e)}"
            print(f"Presenter Error: {error_message}")
            self.view.show_message(
                "course",
                self._add_timestamp(error_message, operation_start_time)
            )

        finally:
            print("Presenter: Batch automation finished. Cleaning up.")
            self.model.close()
            st.session_state.app_state = "IDLE"
            st.rerun()

    # ──────────────────────────────────────────────────────────────────
    # EDITION — BATCH
    # ──────────────────────────────────────────────────────────────────
    def run_batch_edition_creation(self):
        """
        Execute batch creation of multiple editions with their activities.
        """
        operation_start_time = datetime.now()
        results = []

        progress_placeholder = st.empty()
        status_placeholder = st.empty()

        def update_batch_progress(message, percentage):
            self.view.update_progress("course", message, percentage)

        try:
            oracle_url = st.secrets['ORACLE_URL']
            oracle_user = st.session_state.oracle_username
            oracle_pass = st.session_state.oracle_password
            if not oracle_user or not oracle_pass:
                raise Exception("Credenziali Oracle mancanti. Effettua nuovamente il login.")

            batch_data = st.session_state.batch_edition_data
            if not batch_data:
                raise Exception("Nessun dato batch trovato.")

            editions = batch_data.get('editions', [])
            total_editions = len(editions)

            if total_editions == 0:
                raise Exception("Nessuna edizione da creare.")

            update_batch_progress("Accesso a Oracle...", 5)
            if not self.model.login(oracle_url, oracle_user, oracle_pass):
                raise Exception("Login fallito. Controlla le credenziali.")

            update_batch_progress("Navigazione alla pagina Corsi...", 10)
            if not self.model.navigate_to_courses_page():
                raise Exception("Impossibile navigare alla pagina Corsi.")

            for idx, edition in enumerate(editions):
                edition_num = idx + 1
                course_name = edition.get('course_name', 'Unknown')
                edition_title = edition.get('edition_title', '')
                activities = edition.get('activities', [])

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
                        return_to_courses_page=True,
                        centro_costo=edition.get('centro_costo', ''),
                        direzione_pagante=edition.get('direzione_pagante', ''),
                        finanziata=edition.get('finanziata', ''),
                        servizio_pagante=edition.get('servizio_pagante', ''),
                        sottotipologia=edition.get('sottotipologia', ''),
                        societa_pagante=edition.get('societa_pagante', ''),
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
            print("Presenter: Batch edition automation finished. Cleaning up.")
            self.model.close()

            progress_placeholder.empty()
            status_placeholder.empty()

            success_count = sum(1 for r in results if '✅' in r.get('status', ''))
            fail_count = len(results) - success_count
            total_activities_created = sum(r.get('activities', 0) for r in results)
            total_editions = len(
                st.session_state.batch_edition_data.get('editions', [])
            ) if st.session_state.batch_edition_data else 0

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

            st.session_state.edition_message = self._add_timestamp(
                final_message, operation_start_time
            )

            st.session_state.batch_edition_data = None
            st.session_state.edition_parsed_data = None
            st.session_state.edition_show_summary = False
            st.session_state.show_edition_results = True

            st.session_state.app_state = "IDLE"
            st.rerun()

    # ──────────────────────────────────────────────────────────────────
    # EDITION + ACTIVITIES — SINGLE
    # ──────────────────────────────────────────────────────────────────
    def run_create_edition_and_activities(self, edition_details):
        operation_start_time = datetime.now()

        try:
            oracle_url = st.secrets['ORACLE_URL']
            oracle_user = st.session_state.oracle_username
            oracle_pass = st.session_state.oracle_password
            if not oracle_user or not oracle_pass:
                raise Exception("Credenziali Oracle mancanti. Effettua nuovamente il login.")

            course_name = edition_details['course_name']

            self.view.update_progress("edition", "Accesso a Oracle...", 10)
            if not self.model.login(oracle_url, oracle_user, oracle_pass):
                raise Exception("Login fallito.")

            self.view.update_progress("edition", "Navigazione alla pagina dei corsi...", 25)
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
            self.view.show_message(
                "edition",
                self._add_timestamp(result_message, operation_start_time)
            )

        except Exception as e:
            error_message = f"‼️ Si è verificato un errore: {str(e)}"
            print(f"Presenter Error: {error_message}")
            self.view.show_message(
                "edition",
                self._add_timestamp(error_message, operation_start_time)
            )

        finally:
            print("Presenter (Edition+Activity): Automation finished. Cleaning up.")
            self.model.close()
            st.session_state.app_state = "IDLE"
            st.rerun()

    # ──────────────────────────────────────────────────────────────────
    # STUDENTS — SINGLE EDITION
    # ──────────────────────────────────────────────────────────────────
    def run_add_students(self, student_details):
        operation_start_time = datetime.now()
        temp_file_path = None

        try:
            oracle_url = st.secrets['ORACLE_URL']
            oracle_user = st.session_state.oracle_username
            oracle_pass = st.session_state.oracle_password
            if not oracle_user or not oracle_pass:
                raise Exception("Credenziali Oracle mancanti. Effettua nuovamente il login.")

            edition_code = student_details['edition_code']
            student_list = student_details['students']
            num_students = len(student_list)

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

            self.view.update_progress("student", "Accesso a Oracle...", 10)
            if not self.model.login(oracle_url, oracle_user, oracle_pass):
                raise Exception("Login fallito.")

            self.view.update_progress("student", "Navigazione alla pagina edizioni...", 20)
            if not self.model.navigate_to_edition_page():
                raise Exception("Navigazione fallita.")

            self.view.update_progress("student", f"Ricerca edizione '{edition_code}'...", 40)
            edition_result = self.model._search_and_open_edition(edition_code)
            if not edition_result:
                raise Exception(f"Edizione '{edition_code}' non trovata.")

            edition_start_date = edition_result.get('start_date') if isinstance(edition_result, dict) else None
            edition_end_date = edition_result.get('end_date') if isinstance(edition_result, dict) else None
            print(f"Presenter: Edition dates - start: {edition_start_date}, end: {edition_end_date}")

            self.view.update_progress("student", f"Caricamento {num_students} allievi...", 65)
            success = self.model._perform_student_addition_steps(
                student_file_path=temp_file_path,
                lista_nome=lista_nome,
                edition_start_date=edition_start_date,
                edition_end_date=edition_end_date,
            )

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

            self.view.show_message(
                "student",
                self._add_timestamp(result_message, operation_start_time)
            )

        except Exception as e:
            error_message = f"‼️ Si è verificato un errore: {str(e)}"
            print(f"Presenter Error (Student Add): {error_message}")
            self.view.show_message(
                "student",
                self._add_timestamp(error_message, operation_start_time)
            )

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

    # ──────────────────────────────────────────────────────────────────
    # STUDENTS — BATCH (multiple editions)
    # ──────────────────────────────────────────────────────────────────
    def run_add_students_batch(self):
        operation_start_time = datetime.now()
        results = []
        progress_placeholder = st.empty()
        status_placeholder = st.empty()
        temp_file_paths = []
        total_editions = 0

        def update_progress(message, percentage):
            with progress_placeholder.container():
                st.progress(percentage / 100)
            with status_placeholder.container():
                st.info(f"⏳ {message}")

        try:
            oracle_url = st.secrets['ORACLE_URL']
            oracle_user = st.session_state.oracle_username
            oracle_pass = st.session_state.oracle_password
            if not oracle_user or not oracle_pass:
                raise Exception("Credenziali Oracle mancanti. Effettua nuovamente il login.")

            batch_data = st.session_state.batch_student_data
            if not batch_data:
                raise Exception("Nessun dato batch trovato.")

            editions = batch_data.get('editions', [])
            total_editions = len(editions)

            if total_editions == 0:
                raise Exception("Nessuna edizione da processare.")

            update_progress("Accesso a Oracle...", 5)
            if not self.model.login(oracle_url, oracle_user, oracle_pass):
                raise Exception("Login fallito.")

            update_progress("Navigazione alla pagina edizioni...", 10)
            if not self.model.navigate_to_edition_page():
                raise Exception("Navigazione fallita.")

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
                    temp_file = tempfile.NamedTemporaryFile(
                        mode='w', suffix='.txt', prefix=f'students_{edition_code}_',
                        delete=False, encoding='utf-8'
                    )
                    for matricola in student_list:
                        temp_file.write(f"{matricola}\n")
                    temp_file.close()
                    temp_file_paths.append(temp_file.name)

                    lista_nome = f"{edition_code}"

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
                            'students': num_students
                        })

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

                    try:
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
            print("Presenter (Batch Students): Finished. Cleaning up.")
            self.model.close()

            for path in temp_file_paths:
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except:
                        pass

            progress_placeholder.empty()
            status_placeholder.empty()

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

            st.session_state.student_message = self._add_timestamp(
                final_message, operation_start_time
            )
            st.session_state.batch_student_data = None
            st.session_state.student_parsed_data = None
            st.session_state.student_show_summary = False

            st.session_state.app_state = "IDLE"
            st.rerun()

    # ──────────────────────────────────────────────────────────────────
    # STUDENTS — VERIFY
    # ──────────────────────────────────────────────────────────────────
    def run_verify_students(self):
        operation_start_time = datetime.now()
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
            oracle_user = st.session_state.oracle_username
            oracle_pass = st.session_state.oracle_password
            if not oracle_user or not oracle_pass:
                raise Exception("Credenziali Oracle mancanti. Effettua nuovamente il login.")

            verify_data = st.session_state.verify_student_data
            if not verify_data:
                raise Exception("Nessun dato di verifica trovato.")

            editions = verify_data.get('editions', [])
            total_editions = len(editions)

            if total_editions == 0:
                raise Exception("Nessuna edizione da verificare.")

            update_progress("Accesso a Oracle...", 5)
            if not self.model.login(oracle_url, oracle_user, oracle_pass):
                raise Exception("Login fallito.")

            update_progress("Navigazione alla pagina edizioni...", 10)
            if not self.model.navigate_to_edition_page():
                raise Exception("Navigazione fallita.")

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
                    edition_result = self.model._search_and_open_edition(edition_code)
                    if not edition_result:
                        results.append({
                            'edition': edition_code,
                            'expected': num_students,
                            'found': 0,
                            'not_found': num_students,
                            'not_found_list': expected_students,
                            'status': '❌ Edizione non trovata'
                        })
                        continue

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
                not_found_list = r.get('not_found_list', [])
                if not_found_list and len(not_found_list) <= 10:
                    matricole_str = ', '.join(not_found_list)
                    summary_parts.append(f"  - Non trovati: `{matricole_str}`")
                elif not_found_list:
                    first_5 = ', '.join(not_found_list[:5])
                    summary_parts.append(
                        f"  - Non trovati: `{first_5}` ... e altri {len(not_found_list) - 5}")

            final_message = "\n".join(summary_parts)

            st.session_state.student_message = self._add_timestamp(
                final_message, operation_start_time
            )
            st.session_state.verify_student_data = None
            st.session_state.student_parsed_data = None
            st.session_state.student_show_summary = False

            st.session_state.app_state = "IDLE"
            st.rerun()

    # ──────────────────────────────────────────────────────────────────
    # PRESENZA — SINGLE EDITION
    # ──────────────────────────────────────────────────────────────────
    def run_assign_presenza(self):
        operation_start_time = datetime.now()
        results = {}
        progress_placeholder = st.empty()
        status_placeholder = st.empty()

        # Snapshot data BEFORE we clear it in finally
        presenza_snapshot = st.session_state.get('presenza_data', {})

        def update_progress(message, percentage):
            with progress_placeholder.container():
                st.progress(percentage / 100)
            with status_placeholder.container():
                st.info(f"⏳ {message}")

        try:
            oracle_url = st.secrets['ORACLE_URL']
            oracle_user = st.session_state.oracle_username
            oracle_pass = st.session_state.oracle_password
            if not oracle_user or not oracle_pass:
                raise Exception("Credenziali Oracle mancanti. Effettua nuovamente il login.")

            if not presenza_snapshot:
                raise Exception("Nessun dato presenza trovato.")

            edition_code = presenza_snapshot.get('edition_code', '')
            students = presenza_snapshot.get('students', [])
            stato = presenza_snapshot.get('stato', 'Completato')

            if not edition_code:
                raise Exception("Codice edizione mancante.")
            if not students:
                raise Exception("Nessun allievo da processare.")

            update_progress("Accesso a Oracle...", 5)
            if not self.model.login(oracle_url, oracle_user, oracle_pass):
                raise Exception("Login fallito.")

            update_progress("Navigazione alla pagina edizioni...", 10)
            if not self.model.navigate_to_edition_page():
                raise Exception("Navigazione fallita.")

            update_progress(f"Ricerca edizione '{edition_code}'...", 25)
            edition_result = self.model._search_and_open_edition(edition_code)
            if not edition_result:
                raise Exception(f"Edizione '{edition_code}' non trovata.")

            update_progress(
                f"Assegnazione presenza per {len(students)} allievi...", 40)

            results = self.model.assign_presenza_batch(
                edition_code=edition_code,
                students=students,
                stato=stato
            )

            update_progress("Processo completato!", 100)

        except Exception as e:
            error_message = f"‼️ Errore: {str(e)}"
            print(f"Presenter Error (Presenza): {error_message}")
            results = {
                'success': [],
                'failed': presenza_snapshot.get('students', []),
                'total': 0,
                'error': error_message
            }

        finally:
            print("Presenter (Presenza): Finished. Cleaning up.")
            self.model.close()

            progress_placeholder.empty()
            status_placeholder.empty()

            total = results.get('total', 0)
            success_list = results.get('success', [])
            failed_list = results.get('failed', [])

            summary_parts = [
                f"## 📊 Riepilogo Assegnazione Presenza\n",
                f"- **Edizione:** {presenza_snapshot.get('edition_code', '')}",
                f"- **Stato assegnato:** {presenza_snapshot.get('stato', 'Completato')}",
                f"- **Allievi processati:** {len(success_list)}/{total}",
                f"- **Errori:** {len(failed_list)}\n",
            ]

            if success_list:
                summary_parts.append(
                    f"✅ **Successo ({len(success_list)}):** "
                    f"{', '.join(success_list[:10])}"
                    + (f" ... e altri {len(success_list) - 10}"
                       if len(success_list) > 10 else "")
                )

            if failed_list:
                summary_parts.append(
                    f"\n❌ **Falliti ({len(failed_list)}):** "
                    f"{', '.join(failed_list[:10])}"
                    + (f" ... e altri {len(failed_list) - 10}"
                       if len(failed_list) > 10 else "")
                )

            if 'error' in results:
                summary_parts.append(f"\n‼️ **Errore generale:** {results['error']}")

            final_message = "\n".join(summary_parts)

            st.session_state.presenza_message = self._add_timestamp(
                final_message, operation_start_time
            )
            st.session_state.presenza_data = None

            st.session_state.app_state = "IDLE"
            st.rerun()

    # ──────────────────────────────────────────────────────────────────
    # PRESENZA — BATCH (multiple editions/stato groups)
    # ──────────────────────────────────────────────────────────────────
    def run_assign_presenza_batch(self):
        """
        Execute presenza assignment for MULTIPLE editions/stato groups.
        Consecutive jobs with same edition_code skip the navigate-back step.
        """
        operation_start_time = datetime.now()
        all_results = []
        progress_placeholder = st.empty()
        status_placeholder = st.empty()

        def update_progress(message, percentage):
            with progress_placeholder.container():
                st.progress(percentage / 100)
            with status_placeholder.container():
                st.info(f"⏳ {message}")

        try:
            oracle_url = st.secrets['ORACLE_URL']
            oracle_user = st.session_state.oracle_username
            oracle_pass = st.session_state.oracle_password
            if not oracle_user or not oracle_pass:
                raise Exception("Credenziali Oracle mancanti. Effettua nuovamente il login.")

            batch_data = st.session_state.presenza_batch_data
            if not batch_data:
                raise Exception("Nessun dato batch trovato.")

            jobs = batch_data.get('jobs', [])
            total_jobs = len(jobs)
            total_students = batch_data.get('total_students', 0)

            if total_jobs == 0:
                raise Exception("Nessun job da processare.")

            update_progress("Accesso a Oracle...", 5)
            if not self.model.login(oracle_url, oracle_user, oracle_pass):
                raise Exception("Login fallito.")

            update_progress("Navigazione alla pagina edizioni...", 10)
            if not self.model.navigate_to_edition_page():
                raise Exception("Navigazione fallita.")

            students_done = 0
            current_edition_open = None

            for idx, job in enumerate(jobs):
                edition_code = job['edition_code']
                students = job['students']
                stato = job['stato']
                num_students = len(students)
                job_num = idx + 1

                progress_pct = 10 + int((students_done / total_students) * 85)
                update_progress(
                    f"Job {job_num}/{total_jobs}: '{edition_code}' "
                    f"({num_students} allievi → {stato})...",
                    progress_pct
                )

                try:
                    if current_edition_open != edition_code:
                        edition_result = self.model._search_and_open_edition(
                            edition_code)
                        if not edition_result:
                            all_results.append({
                                'edition': edition_code,
                                'stato': stato,
                                'success': [],
                                'failed': students,
                                'total': num_students,
                                'note': '❌ Edizione non trovata'
                            })
                            students_done += num_students
                            continue
                        current_edition_open = edition_code

                    result = self.model.assign_presenza_batch(
                        edition_code=edition_code,
                        students=students,
                        stato=stato
                    )

                    all_results.append({
                        'edition': edition_code,
                        'stato': stato,
                        'success': result.get('success', []),
                        'failed': result.get('failed', []),
                        'total': num_students,
                    })

                    students_done += num_students

                    if idx < total_jobs - 1:
                        next_edition = jobs[idx + 1]['edition_code']
                        if next_edition != edition_code:
                            if not self.model._click_back_to_edition_search():
                                print("   ⚠️ Back failed, full navigation...")
                                try:
                                    self.model.navigate_to_edition_page()
                                    current_edition_open = None
                                except:
                                    print("   ❌ Could not return to search")
                                    current_edition_open = None
                            else:
                                current_edition_open = None

                except Exception as e:
                    error_msg = str(e)[:100]
                    print(f"   ❌ Error for job {edition_code} → {stato}: {error_msg}")
                    all_results.append({
                        'edition': edition_code,
                        'stato': stato,
                        'success': [],
                        'failed': students,
                        'total': num_students,
                        'note': f'❌ Errore: {error_msg}'
                    })
                    students_done += num_students
                    try:
                        self.model.navigate_to_edition_page()
                        current_edition_open = None
                    except:
                        pass

            update_progress("Processo completato!", 100)

        except Exception as e:
            error_message = f"‼️ Errore batch presenza: {str(e)}"
            print(f"Presenter Error: {error_message}")
            all_results.append({
                'edition': 'ERRORE GENERALE',
                'stato': '-',
                'success': [],
                'failed': [],
                'total': 0,
                'note': error_message
            })

        finally:
            print("Presenter (Batch Presenza): Finished. Cleaning up.")
            self.model.close()

            progress_placeholder.empty()
            status_placeholder.empty()

            total_success = sum(len(r.get('success', [])) for r in all_results)
            total_failed_students = sum(
                len(r.get('failed', [])) for r in all_results)
            total_processed = total_success + total_failed_students
            jobs_with_errors = sum(
                1 for r in all_results if r.get('note', '').startswith('❌'))

            summary_parts = [
                f"## 📊 Riepilogo Assegnazione Presenza Batch\n",
                f"- **Job totali:** {len(all_results)}",
                f"- **Job con errore:** {jobs_with_errors}",
                f"- **Allievi processati con successo:** "
                f"{total_success}/{total_processed}",
                f"- **Allievi falliti:** {total_failed_students}\n",
                "### Dettagli per job:"
            ]

            for r in all_results:
                note = r.get('note', '')
                stato_icon = {
                    'Completato': '✅',
                    'Esente': '⚪',
                    'Non passato': '❌'
                }.get(r['stato'], '📋')
                success_count = len(r.get('success', []))
                total = r.get('total', 0)

                line = (f"- **{r['edition']}** {stato_icon} {r['stato']}: "
                        f"{success_count}/{total}")
                if note:
                    line += f" — {note}"
                summary_parts.append(line)

                failed = r.get('failed', [])
                if failed:
                    if len(failed) <= 10:
                        summary_parts.append(
                            f"  - Falliti: `{', '.join(failed)}`")
                    else:
                        summary_parts.append(
                            f"  - Falliti: `{', '.join(failed[:10])}` "
                            f"... e altri {len(failed) - 10}"
                        )

            final_message = "\n".join(summary_parts)

            st.session_state.presenza_message = self._add_timestamp(
                final_message, operation_start_time
            )
            st.session_state.presenza_batch_data = None
            st.session_state.presenza_show_batch_preview = False

            st.session_state.app_state = "IDLE"
            st.rerun()