# presenter connects the View and the Model
import streamlit as st


class CoursePresenter:
    def __init__(self, model, view):
        # the presenter holds references to the model and the view
        self.model = model
        self.view = view

    # =============================
    #  COURSE CREATION
    # =============================
    def run_create_course(self, course_details):
        # main method that runs the application
        # 1.render the form and wait for user input after clicking submit
        if not course_details:
            return

        # get the credentials securely from Streamlit's secrets management
        oracle_url = st.secrets['ORACLE_URL']
        oracle_user = st.secrets['ORACLE_USER']
        oracle_pass = st.secrets['ORACLE_PASS']

        # UI elements for progress and status updates
        progress = st.progress(0)
        status = st.empty()

        # 3.A spinner to show the user that process is proceeding
        with st.spinner('Automazione in corso... Attendere prego'):
            try:
                # BEFORE starting steps - initialize
                st.session_state["last_progress"] = 0
                st.session_state["last_status"] = "Ready to start..."
                # ---Step1: Login ---
                status.info("🔑Accesso a Oracle in corso...")
                progress.progress(10)
                # telling the model to perform the authorising process
                login_success = self.model.login(oracle_url, oracle_user, oracle_pass)
                if login_success:
                    # self.view.display_message('Logged in Successfully')
                    status.success('✅🤩Accesso effettuato con successo')
                else:
                    self.view.display_message('Login Failed. Please check your credentials.')
                    status.error('❌😭 Accesso fallito. Si prega di controllare le credenziali.')
                    return
                # ---Step2:Navigate to course creation ---
                status.info('🧭🚶Navigazione verso la pagina di creazione del corso in corso...')
                progress.progress(30)
                nav_success = self.model.navigate_to_course_creation()
                if nav_success:
                    # self.view.display_message(result_message)
                    status.success('👣💃🕺Pagina di creazione del corso raggiunta')
                else:
                    st.view.display_message('Failed to navigate to the course page')
                    status.error('❌😭Impossibile navigare verso la pagina del corso')
                    return
                progress.progress(50)
                # ---Step3: Create the course---
                course_name = course_details['title']
                status.info(f"🔍 Ricerca del corso:: '**{course_name}**'in corso. 👌🏻😎Altrimenti il corso verrà creato")
                progress.progress(70)
                result_message = self.model.create_course(course_details)

                # handle model message
                if result_message and "Error" in result_message:
                    status.error(f'❌😭{result_message}')
                # else:
                #     status.success(f"{result_message or 'Corso creato con successo!'}")

                # in finally, set final state (example)
                progress.progress(100)
                st.session_state["last_progress"] = 100
                st.session_state["last_status"] = result_message or "Corso creato con successo!"

                # reset running flags etc.
                st.session_state["automation_running"] = False
                st.session_state["start_automation"] = False
                st.session_state["course_details"] = None

                # then rerun:
                st.rerun()


            except Exception as e:
                self.view.display_message(f"⚠️👩🏻‍✈️Errore inatteso:: {e}")
                status.error(result_message)



            finally:
                try:
                    self.model.close_driver()
                except Exception:
                    pass

    # =============================
    #  EDITION CREATION
    # =============================
    def run_create_edition(self, edition_details):
        if not edition_details:
            return

        oracle_url = st.secrets['ORACLE_URL']
        oracle_user = st.secrets['ORACLE_USER']
        oracle_pass = st.secrets['ORACLE_PASS']

        progress = st.progress(0)
        status = st.empty()

        with st.spinner("Automazione in corso... Attendere prego"):
            try:
                status.info("🔑 Accesso a Oracle in corso...")
                progress.progress(10)
                if not self.model.login(oracle_url, oracle_user, oracle_pass):
                    status.error("❌ Accesso fallito.")
                    return

                progress.progress(25)
                status.info("🧭 Navigazione verso la pagina dei corsi...")
                if not self.model.navigate_to_courses_page():
                    status.error("❌ Impossibile raggiungere la pagina corsi.")
                    return

                course_name = edition_details['course_name']
                status.info(f"🔍 Ricerca del corso '{course_name}'...")
                progress.progress(40)

                found = self.model.search_course(course_name)
                if found is None:
                    status.error("⚠️ Errore nella ricerca del corso.")
                    return
                if not found:
                    status.warning(f"❌ Il corso '{course_name}' non esiste. Crealo prima di procedere.")
                    return

                progress.progress(60)
                status.info(f"📂 Apertura del corso '{course_name}'...")
                if not self.model.open_course_from_list(course_name):
                    status.error("❌ Impossibile aprire la pagina del corso.")
                    return

                progress.progress(80)
                status.info("🧾 Creazione della nuova edizione...")
                res = self.model.create_edition(edition_details)

                progress.progress(100)
                status.success(res or "✅ Edizione creata con successo!")

            except Exception as e:
                status.error(f"⚠️ Errore inatteso: {e}")
            finally:
                self.model.close_driver()