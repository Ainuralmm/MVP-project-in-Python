import time
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.edge.options import Options
from selenium.common.exceptions import TimeoutException

class OracleAutomator:
    def __init__(self, driver_path, debug_mode=False, debug_pause=1, headless=False):
        options = Options()
        if headless:
            options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
        else:
            options.add_argument("--window-size=1920,1080")
        service = Service(executable_path=driver_path)
        self.driver = webdriver.Edge(service=service, options=options)
        self.wait = WebDriverWait(self.driver, 40)
        self.debug_mode = debug_mode
        self.debug_pause_duration = debug_pause
        mode = "Headless" if headless else "Visible"
        print(f"Model: WebDriver initialized in {mode} mode.")

    def _pause_for_visual_check(self):
        if self.debug_mode:
            time.sleep(self.debug_pause_duration)

    def login(self, url, username, password):
        try:
            self.driver.get(url)
            self.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="userid"]'))).send_keys(username)
            self.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="password"]'))).send_keys(password)
            self.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="btnActive"]'))).click()
            print("Model: Logged in successfully.")
            return True
        except Exception as e:
            print(f"Model: Error during login: {e}")
            return False

    def navigate_to_courses_page(self):
        try:
            self.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="groupNode_workforce_management"]'))).click()
            self.wait.until(EC.presence_of_element_located((By.ID, 'WLF_FUSE_LEARN_ADMIN'))).click()
            self.wait.until(EC.element_to_be_clickable((By.XPATH, '//a[@title="Corsi" and text()="Corsi"]'))).click()
            print("Model: Navigated to 'Corsi' page.")
            return True
        except Exception as e:
            print(f"Model: Error navigating to 'Corsi' page: {e}")
            return False

    def search_course(self, course_name):
        try:
            capitalised_course_name = course_name.title()
            search_box = self.wait.until(EC.presence_of_element_located(
                (By.NAME, 'pt1:_FOr1:1:_FONSr2:0:MAnt2:1:MgCrUpl:UPsp1:r2:0:crsQry2:value00')))
            search_box.clear()
            search_box.send_keys(capitalised_course_name)
            date_input = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, '//*[@id="pt1:_FOr1:1:_FONSr2:0:MAnt2:1:MgCrUpl:UPsp1:r2:0:crsQry2:value10::content"]')))
            date_input.clear()
            date_input.send_keys("01/01/2000")
            self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, '//*[@id="pt1:_FOr1:1:_FONSr2:0:MAnt2:1:MgCrUpl:UPsp1:r2:0:crsQry2::search"]'))).click()

            short_wait = WebDriverWait(self.driver, 5)
            try:
                # First, check for the "no data" message. If it appears, the course definitely doesn't exist.
                short_wait.until(
                    EC.presence_of_element_located((By.XPATH, '//*[contains(text(),"Nessun dato da visualizzare.")]')))
                return False  # Course does not exist
            except TimeoutException:
                # If there's no "no data" message, we now look for an EXACT match.
                course_name_lower = course_name.lower()
                # Switched from `contains()` to an exact match `normalize-space(.)=` for precision.
                # This XPath converts the link text to lowercase and compares it to our lowercase variable.
                case_insensitive_xpath = f"//table[@summary='Corsi']//a[translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='{course_name_lower}']"
                self.wait.until(EC.presence_of_element_located((By.XPATH, case_insensitive_xpath)))
                print(f"Course '{course_name}' found in search results.")
                return True
        except Exception as e:
            # If any other error occurs, safely assume it was not found.
            print(f"An error occurred during search_course: {e}")
            return False

    def open_course_from_list(self, course_name):
        try:
            ### HASHTAG: THE FIX IS HERE
            # Switched from `contains()` to an exact match `normalize-space(.)=` to target the correct link.
            # This XPath now finds the link even if use
            course_name_lower = course_name.lower()
            # Switched from `contains()` to an exact match `normalize-space(.)=` to target the correct link.
            case_insensitive_xpath = f"//table[@summary='Corsi']//a[translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='{course_name_lower}']"

            link = self.wait.until(EC.element_to_be_clickable((By.XPATH, case_insensitive_xpath)))
            link.click()
            self._pause_for_visual_check()
            print(f"Model: Clicked on existing course '{course_name}' in list.")
            return True
        except Exception as e:
            print(f"Model: Could not find or click the link for '{course_name}'. Error: {e}")
            return False

    def create_course(self, course_details):
        try:
            course_name = course_details['title'].title()
            if not self.navigate_to_courses_page():
                return f"‼️ Error: Cannot reach the Corsi page."
            if self.search_course(course_name):
                return f"‼️🕵🏻️ Attenzione: Il corso '{course_name}' esiste già."

            crea_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="pt1:_FOr1:1:_FONSr2:0:MAnt2:1:MgCrUpl:UPsp1:r2:0:srAtbl:_ATp:crtBtn"]/a/span')))
            crea_button.click()
            self._pause_for_visual_check()

            # fill form fields (as before)
            title_field = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, '//*[@id="pt1:_FOr1:1:_FONSr2:0:MAnt2:2:lsVwCrs:ttlInp::content"]')))
            title_field.send_keys(course_details['title'])
            title_field.send_keys(Keys.TAB)
            self._pause_for_visual_check()

            programma_field = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, '//*[@id="pt1:_FOr1:1:_FONSr2:0:MAnt2:2:lsVwCrs:slbsRte::_cic"]/div[1]/div[2]/div')))
            programma_field.send_keys(course_details.get('programme', ''))
            programma_field.send_keys(Keys.TAB)
            self._pause_for_visual_check()

            desc_breve = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, '//input[contains(@id, ":MAnt2:2:lsVwCrs:shdsInp::content")]')))
            desc_breve.send_keys(course_details.get('short_description', ''))
            desc_breve.send_keys(Keys.TAB)
            self._pause_for_visual_check()

            data_inizio_pubblic = self.wait.until(EC.visibility_of_element_located(
                (By.XPATH, '//input[contains(@id, ":MAnt2:2:lsVwCrs:sdDt::content")]')))
            data_inizio_pubblic.clear()

            # This line will now work because 'start_date' is a proper date object
            publication_date_str = course_details['start_date'].strftime("%d/%m/%Y")

            ### HASHTAG: THE SECOND FIX IS HERE
            # You must send the formatted STRING to send_keys, not the original object.
            data_inizio_pubblic.send_keys(publication_date_str)
            data_inizio_pubblic.send_keys(Keys.TAB)
            self._pause_for_visual_check()

            salve_chiude = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="pt1:_FOr1:1:_FONSr2:0:MAnt2:2:lsVwCrs:svcBtn"]')))
            salve_chiude.click()
            self._pause_for_visual_check()

            # confirm by waiting for edizioni tab (page navigated to details)
            edizioni_tab_xpath = '//div[contains(@id, ":lsCrDtl:UPsp1:classTile::text")]'
            self.wait.until(EC.presence_of_element_located((By.XPATH, edizioni_tab_xpath)))

            return f"✅🤩 Successo! Il corso '{course_name}' è stato creato."
        except Exception as e:
            return f"‼️👩🏻‍✈️ Errore durante la creazione del corso. Controlla la console."

    ### HASHTAG: UPDATED HELPER FOR ACTIVITY CREATION
    def _create_single_activity(self, unique_title, full_description, activity_date_obj, start_time_str, end_time_str, future_input_value):
        try:
            activity_date_str = activity_date_obj.strftime('%d/%m/%Y')
            button_aggiungi_attivita = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//div[contains(@id, ':actPce:iltBtn') and @title='Aggiungi']"))
            )
            button_aggiungi_attivita.click()
            print(f"Clicked 'Aggiungi' button for activity on {activity_date_str}")
            self._pause_for_visual_check()

            # --- Fill Activity Details ---
            box_attivita_titolo = self.wait.until(
                EC.presence_of_element_located((By.XPATH, '//input[@aria-label="Titolo"]')))
            box_attivita_titolo.send_keys(unique_title)

            desc_per_elenco_attivita = self.wait.until(
                EC.presence_of_element_located((By.XPATH, '//input[@aria-label="Descrizione per elenco"]')))
            desc_per_elenco_attivita.send_keys(f"{unique_title}-{activity_date_str}")

            desc_dettagliata_attivita = self.wait.until(
                EC.presence_of_element_located((By.XPATH, '//div[@aria-label="Editor editing area: main"]')))
            desc_dettagliata_attivita.send_keys(full_description)

            data_attivita = self.wait.until(
                EC.presence_of_element_located((By.XPATH, '//input[@aria-label="Data attività"]')))
            self.driver.execute_script("arguments[0].value=arguments[1];", data_attivita, activity_date_str)
            data_attivita.send_keys(Keys.TAB)  # Trigger potential validation

            ora_inizio_attivita = self.wait.until(
                EC.presence_of_element_located((By.XPATH, '//input[@aria-label="Ora inizio"]')))
            ora_inizio_attivita.clear()
            ora_inizio_attivita.send_keys(start_time_str)

            ora_fine_attivita = self.wait.until(
                EC.presence_of_element_located((By.XPATH, '//input[@aria-label="Ora fine"]')))
            ora_fine_attivita.clear()
            ora_fine_attivita.send_keys(end_time_str)

            ### HASHTAG: PLACEHOLDER FOR FUTURE INPUT FIELD ###
            # Replace 'YOUR_FUTURE_FIELD_XPATH_SELECTOR' with the actual XPATH
            # Replace 'future_input_value' with the data from the view
            # If future_input_value: # Check if user provided input
            #     future_field = self.wait.until(EC.presence_of_element_located((By.XPATH, 'YOUR_FUTURE_FIELD_XPATH_SELECTOR')))
            #     future_field.clear()
            #     future_field.send_keys(future_input_value)
            #     print(f"Entered future field value: {future_input_value}")
            #     self._pause_for_visual_check()

            # Save and press OK button
            ok_button_attivita = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, '//a[./span[text()="OK"]]')))
            ok_button_attivita.click()
            print(f"Clicked OK for activity '{unique_title}' on {activity_date_str}")
            # Wait for the OK button popup to disappear before proceeding
            self.wait.until(EC.invisibility_of_element_located((By.XPATH, '//a[./span[text()="OK"]]')))
            self._pause_for_visual_check(0.5)  # Short pause after popup closes
            return True

        except Exception as e:
            print(f"Error creating activity '{unique_title}' on {activity_date_str}: {e}")
            # Try to click Cancel if OK fails, to avoid getting stuck
            try:
                cancel_button = self.driver.find_element(By.XPATH, '//a[./span[text()="Annulla"]]')
                cancel_button.click()
                self.wait.until(EC.invisibility_of_element_located((By.XPATH, '//a[./span[text()="Annulla"]]')))
                print("Clicked Cancel button after error.")
            except:
                print("Could not click Cancel button after error.")  # Ignore if cancel fails too
            return False




    # CREATE EDITION flow (assumes caller opened the course detail page)
    def create_edition_and_activities(self, edition_details):
        """
        ADDED: CREATE EDITION METHOD
        edition_details keys:
          - course_name (str) : name of existing course
          - edition_start_date (date or str %d/%m/%Y)
          - edition_end_date (date) : PREFERRED
          - duration_days (int) : FALLBACK
          - description (str) : description of edition
          - location (str)
          - supplier (str)
          - price (str)
          - language (str)
          - moderator_type (str)
        """
        try:
            course_name = edition_details['course_name'].title()
            # Use .get() for the optional title to prevent errors if it's missing
            edition_title_optional = edition_details.get('edition_title', '')
            # parse start date and end date
            edition_start_date = edition_details.get('edition_start_date')
            edition_end_date_obj = edition_details.get('edition_end_date')
            location = edition_details.get('location', "")
            supplier = edition_details.get('supplier', "")
            price = edition_details.get('price', "")
            description = edition_details.get('description', "")
            #language = edition_details.get('language', "")
            #moderator_type = edition_details.get('moderator_type', "")
            #duration_days = int(edition_details.get('duration_days', 1))
            activities = edition_details.get('activities', [])  # Get the list of activities

            print(f"Model (EDITION+ACTIVITY): Starting creation for {course_name}")

            # --- PART 1: Create Edition (Navigate, Find Course, Fill Form) ---
            if not self.navigate_to_courses_page():
                return "‼️ Errore: Navigazione alla pagina corsi fallita."
            if not self.search_course(course_name):
                return f"‼️ Errore: Corso '{course_name}' non trovato. Crealo prima."
            if not self.open_course_from_list(course_name):
                return f"‼️ Errore: Impossibile aprire il corso '{course_name}'."

            # Assumes we are on course detail page; if not, try to click the course from list
            # Click 'Edizioni' tab
            edizioni_tab_xpath = '//div[contains(@id, ":lsCrDtl:UPsp1:classTile::text")]'
            edizioni_tab = self.wait.until(EC.presence_of_element_located((By.XPATH, edizioni_tab_xpath)))
            edizioni_tab.click()
            #self._pause_for_visual_check()

            # Click Crea -> Edizione guidata da docente
            button_crea_edizioni = self.wait.until(EC.presence_of_element_located((By.XPATH, "//a[text()='Crea']")))
            button_crea_edizioni.click()
            #self._pause_for_visual_check()

            option_of_button_crea_edizioni = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//td[text()='Edizione guidata da docente']")))
            option_of_button_crea_edizioni.click()
            self._pause_for_visual_check()

            # titolo edizione
            titolo_edizione_field= self.wait.until(
                EC.presence_of_element_located((By.XPATH, '//input[contains(@id, ":lsVwCls:ttlInp::content")]')))

            ### HASHTAG: NEW CONDITIONAL LOGIC FOR THE EDITION TITLE
            # This block checks if the user provided a non-empty custom title.
            if edition_title_optional and edition_title_optional.strip():
                # CASE 1: User provided a custom title.
                print(f"Using custom edition title: {edition_title_optional}")
                # Clear the field first, as it's likely pre-filled with the course name.
                titolo_edizione_field.clear()
                titolo_edizione_field.send_keys(edition_title_optional)
            else:
                # CASE 2: User left the field blank. Use the default behavior.
                print("Using default edition title logic (course name + date)")
                # This appends the date to the existing course name in the field.
                titolo_edizione_field.send_keys("-" + edition_start_date.strftime("%d/%m/%Y"))

            self._pause_for_visual_check()

            # description
            if description:
                descirione_edizione = self.wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, '//div[contains(@aria-label, "main") and @role="textbox"]')))

                # Combine everything into a single f-string before sending
                full_description_text = f"{course_name}-{edition_start_date.strftime('%d/%m/%Y')}-{description}"
                descirione_edizione.send_keys(full_description_text)

                # Removed the extra dot at the end of this line
                self._pause_for_visual_check()

            # publication start: 2 months before (by months, as requested)
            two_months_before = edition_start_date - relativedelta(months=2)
            publication_start_str = two_months_before.strftime("%d/%m/%Y")
            edizione_data_inizio_pubblicazione = self.wait.until(
                EC.presence_of_element_located((By.XPATH, '//input[contains(@id, ":lsVwCls:sdDt::content")]')))
            edizione_data_inizio_pubblicazione.clear()
            edizione_data_inizio_pubblicazione.send_keys(publication_start_str)
            self._pause_for_visual_check()

            # publication end = edition_end + 1 day
            # This line now works perfectly with the dynamically sourced edition_end_date_obj
            publication_end_str = (edition_end_date_obj + timedelta(days=1)).strftime("%d/%m/%Y")
            edizione_data_fine_pubblicazione = self.wait.until(
                EC.presence_of_element_located((By.XPATH, '//input[contains(@id,"lsVwCls:edDt::content")]')))
            edizione_data_fine_pubblicazione.clear()
            edizione_data_fine_pubblicazione.send_keys(publication_end_str)
            self._pause_for_visual_check()

            # set edition start and end
            dettagli_ed_data_inizio_edizione = self.wait.until(
                EC.presence_of_element_located((By.XPATH, '//input[contains(@id, ":lsVwCls:liSdDt::content")]')))
            dettagli_ed_data_inizio_edizione.clear()
            dettagli_ed_data_inizio_edizione.send_keys(edition_start_date.strftime("%d/%m/%Y"))
            self._pause_for_visual_check()

            # set edition end
            # This line also works perfectly with the new logic
            dettagli_ed_data_fine_edizione = self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//input[contains(@id, ':lsVwCls:liEdDt::content')]")))
            dettagli_ed_data_fine_edizione.clear()
            dettagli_ed_data_fine_edizione.send_keys(edition_end_date_obj.strftime("%d/%m/%Y"))
            self._pause_for_visual_check()

            # Aula principale lookup
            if location:
                aula_prince_xpath = '//*[contains(@id, "primaryClassroomName1Id::lovIconId")]'
                select_aula_principale = self.wait.until(EC.element_to_be_clickable((By.XPATH, aula_prince_xpath)))
                select_aula_principale.click()
                self._pause_for_visual_check()

                cerca_aula_button = self.wait.until(
                    EC.visibility_of_element_located((By.XPATH, "//a[text()='Cerca...']")))
                cerca_aula_button.click()
                self._pause_for_visual_check()

                box_cerca_aula_parole_chiave = self.wait.until(EC.presence_of_element_located((By.XPATH,
                                                                                               '//input[contains(@id, "primaryClassroomName1Id::_afrLovInternalQueryId:value00::content")]')))
                box_cerca_aula_parole_chiave.send_keys(location)
                self._pause_for_visual_check()

                button_parole_chiave_cerca = self.wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//button[text()='Cerca' and contains(@id, 'primaryClassroomName1Id')]")))
                button_parole_chiave_cerca.click()

                ### HASHTAG: FIX  - ADDED EXPLICIT WAIT FOR RESULTS
                # Instead of a fixed pause,  now explicitly wait for the results table to appear after searching.

                results_table_xpath = '//div[contains(@id, "primaryClassroomName1Id_afrLovInternalTableId::db")]'
                self.wait.until(EC.presence_of_element_located((By.XPATH, results_table_xpath)))

                try:
                    # Use a shorter wait time to check for the "No results" message
                    short_wait = WebDriverWait(self.driver, 3)
                    short_wait.until(EC.presence_of_element_located((By.XPATH,
                                                                     f'{results_table_xpath}//tr[.//text()[contains(., "Nessuna riga da visualizzare")]]')))
                    print(f"⚠️ The location '{location}' was not found.")
                except TimeoutException:
                    ### HASHTAG: FIX 2 - CASE-INSENSITIVE XPATH
                    # The translate() function in XPath converts the text to lowercase before comparing it.
                    # We also convert the user's input to lowercase with .lower() to ensure a match.
                    location_lower = location.lower()
                    case_insensitive_xpath = f"//td[contains(@class, 'xen') and .//span[translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='{location_lower}']]"

                    list_aula_option_row = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, case_insensitive_xpath)))
                    list_aula_option_row.click()
                    self._pause_for_visual_check()

                ok_button = self.wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//button[text()='OK' and contains(@id, 'primaryClassroomName1Id')]")))
                ok_button.click()
                print("Confirmed the selected course location")
                self._pause_for_visual_check()

            # language
            language = ("Italiana")

            choose_lingua = self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//a[contains(@id, ':lsVwCls:lngSel::drop')]")))
            choose_lingua.click()
            self._pause_for_visual_check()
            find_lingua = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, f'//*[contains(text(), \"{language}\")]')))
            find_lingua.click()
            print("Confirmed the selected language:", language)
            self._pause_for_visual_check()

            # supplier lookup & select
            if supplier:
                # Set moderator type to 'Fornitore formazione' first
                moderator_type = 'Fornitore formazione'
                choose_tipo_moderatore = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(@id, ':lsVwCls:socFaciType::drop')]"))
                )
                choose_tipo_moderatore.click()
                find_tipo_moderatore = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, f'//li[text()="{moderator_type}"]'))
                    # More specific than contains()
                )
                find_tipo_moderatore.click()
                print(f"Set moderator type to: {moderator_type}")

                # Now, handle the supplier lookup
                # 1. Click the icon to open the search popup.
                self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(@id, ':lsVwCls:supplierNameId::lovIconId')]"))
                ).click()

                # 2. Inside the popup, click the 'Search...' link to reveal the input field.
                self.wait.until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//a[contains(@id, ':lsVwCls:supplierNameId::dropdownPopup::popupsearch')]"))
                ).click()

                # 3. Wait for the search box, enter the supplier name, and click the search button.
                # We combine these actions as they happen quickly.
                box = self.wait.until(EC.visibility_of_element_located((By.XPATH,
                                                                        "//input[contains(@id, ':lsVwCls:supplierNameId::_afrLovInternalQueryId:value00::content')]")))
                box.send_keys(supplier)

                self.driver.find_element(By.XPATH,
                                         "//button[text()='Cerca' and contains(@id, 'supplierNameId')]").click()

                # 4. CRITICAL STEP: Now wait for the result using the robust, case-insensitive XPath.
                # This single wait checks for either the desired result or a "no results" message.
                print(f"Searching for supplier '{supplier}'...")
                try:
                    # Use the new case-insensitive XPath to find the correct row
                    supplier_row_xpath = (
                        f'//div[contains(@id, "lsVwCls:supplierNameId_afrLovInternalTableId::db")]'
                        f'//tr[contains(translate(., "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "{supplier.lower()}")]'
                    )

                    find_nome_fornitore_in_list = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, supplier_row_xpath))
                    )

                    print(f"Found supplier '{supplier}'. Clicking...")
                    find_nome_fornitore_in_list.click()

                    # 5. Finally, click the 'OK' button to confirm the selection.
                    self.wait.until(
                        EC.element_to_be_clickable(
                            (By.XPATH, "//button[text()='OK' and contains(@id, 'supplierNameId')]"))
                    ).click()
                    print(f"Successfully selected supplier: {supplier}")
                    self._pause_for_visual_check()

                except TimeoutException:
                    # This block runs only if the case-insensitive search fails to find the row.
                    print(f"⚠️ The supplier '{supplier}' was not found after search.")
                    # Optional: Click a 'Cancel' button here to close the popup gracefully
                    # self.driver.find_element(By.XPATH, "//button[text()='Annulla']").click()



            # add price
            if price:
                # flag button 'Override determinazione prezzi'
                flag_determinzaione_prezzi = self.wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, '//label[text()="Override determinazione prezzi"]')))
                flag_determinzaione_prezzi.click()
                print("Flagged button 'Override determinazione prezzi'")
                self._pause_for_visual_check()

                # pressing on button aggiungi voce linea
                aggiungi_voce_linea = self.wait.until(EC.presence_of_element_located(
                    (By.XPATH, "//img[contains(@id, ':lsVwCls:rPrc:0:srAtbl:_ATp:addBtn::icon')]")))
                aggiungi_voce_linea.click()
                print("Clicked on button 'Aggiungi voce linea'")
                self._pause_for_visual_check()

                # choose prezzo di listino from VOCE LINEA
                dropdown_voce_linea =self.wait.until(EC.presence_of_element_located(
                    (By.XPATH, "//a[contains(@id, ':lsVwCls:rPrc:0:srAtbl:_ATp:t1:0:soc2::drop')]")))
                dropdown_voce_linea.click()
                print("Clicked on dropdown button 'Choose voce linea'")
                self._pause_for_visual_check()

                choose_prezzo_di_listino = self.wait.until(
                    EC.presence_of_element_located((By.XPATH, '//*[contains(text(),"Prezzo di listino")]')))
                choose_prezzo_di_listino.click()
                print("Clicked and chosen 'Prezzo di listino'")
                self._pause_for_visual_check()

                # add the price of the course: in the Costo enter taxable edition (e.g.: if the course costs € 1000.00 + VAT put 1000.00)
                #costo_di_edizione = ('1000')
                add_costo_di_edizione = self.wait.until(EC.presence_of_element_located(
                    (By.XPATH, "//input[contains(@id, ':lsVwCls:rPrc:0:srAtbl:_ATp:t1:0:it1::content')]")))
                add_costo_di_edizione.send_keys(price)
                print("Costo di edizione was inserted correctly")

            time.sleep(1)
            # save and close
            button_salva_e_chiudi_info_di_edizioni = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[text()='Salva e chiudi']")))
            button_salva_e_chiudi_info_di_edizioni.click()
            self._pause_for_visual_check()

            # --- PART 2: Create Activities (Loop after saving edition) ---
            # Wait for the activity 'Aggiungi' button to appear, confirming the edition save was successful
            # and we are on the correct page to add activities.
            confirmation_xpath = "//div[contains(@id, ':actPce:iltBtn') and @title='Aggiungi']"
            self.wait.until(EC.element_to_be_clickable((By.XPATH, confirmation_xpath)))
            print("Model: Edition saved successfully. Starting activity creation.")
            self._pause_for_visual_check()

            total_activities = len(activities)
            created_count = 0
            for i, activity in enumerate(activities):
                print(f"--- Creating activity {i + 1} of {total_activities} ---")
                success = self._create_single_activity(
                    unique_title=activity['title'],
                    full_description=activity['description'],
                    activity_date_obj=activity['date'],
                    start_time_str=activity['start_time'],
                    end_time_str=activity['end_time'],
                    future_input_value=activity.get('future_field', '')  # Safely get future value
                )
                if not success:
                    # If one activity fails, report the error and stop
                    return f"‼️👩🏻‍✈️ Errore durante la creazione dell'attività {i + 1} ('{activity['title']}'). Le attività precedenti potrebbero essere state create."
                created_count += 1

            # --- Final Success Message ---
            edition_display_name = edition_title_optional if edition_title_optional and edition_title_optional.strip() else f"Edizione del {edition_start_date.strftime('%d/%m/%Y')}"
            return f"✅🤩 Successo! Edizione '{edition_display_name}' per '{course_name}' creata con {created_count} attività."

        except Exception as e:
            print(f"ERROR in create_edition_and_activities: {e}")
            return f"‼️👩🏻‍✈️ Errore generale durante la creazione dell'edizione o delle attività: {e}"

    def close_driver(self):
        print("Model: Closing driver.")
        self.driver.quit()