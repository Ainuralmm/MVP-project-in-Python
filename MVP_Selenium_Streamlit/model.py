import time
from datetime import timedelta, datetime
from dateutil.relativedelta import relativedelta
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.edge.options import Options
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException


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
        """
        Search for a course by name.

        IMPORTANT: This method assumes you're already on the 'Corsi' page.
        Call navigate_to_courses_page() first if you're not sure.

        Returns:
            True if course exists
            False if course does not exist
        """
        try:
            # ### HASHTAG: ENSURE WE'RE ON THE COURSES PAGE ###
            # If we just created a course, we're on the details page
            # We need to navigate back to the courses list
            current_url = self.driver.current_url
            if "lsCrDtl" in current_url or "lsVwCrs" in current_url:
                # We're on a course details or edit page, go back to list
                print("Currently on course details page, navigating back to courses list...")
                if not self.navigate_to_courses_page():
                    print("Failed to navigate back to courses page")
                    return False

            # Clean and capitalize course name
            cleaned_course_name = course_name.strip()
            capitalised_course_name = cleaned_course_name.title()

            # ### HASHTAG: FILL SEARCH FORM ###
            search_box_locator = (By.NAME, 'pt1:_FOr1:1:_FONSr2:0:MAnt2:1:MgCrUpl:UPsp1:r2:0:crsQry2:value00')
            search_box = self.wait.until(EC.element_to_be_clickable(search_box_locator))
            search_box.clear()
            search_box.send_keys(capitalised_course_name)
            self._pause_for_visual_check()

            # ### HASHTAG: SEARCH DATE - FIND ALL COURSES AFTER THIS DATE ###
            # This is the FILTER date (find courses published after 01/01/2000)
            # NOT the course's actual publication date!
            date_input = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, '//*[@id="pt1:_FOr1:1:_FONSr2:0:MAnt2:1:MgCrUpl:UPsp1:r2:0:crsQry2:value10::content"]')))
            date_input.clear()
            date_input.send_keys("01/01/2000")  # Search filter - find all courses after this date
            self._pause_for_visual_check()

            # Click search
            search_button_locator = (By.XPATH,
                                     '//*[@id="pt1:_FOr1:1:_FONSr2:0:MAnt2:1:MgCrUpl:UPsp1:r2:0:crsQry2::search"]')
            search_button = self.wait.until(EC.element_to_be_clickable(search_button_locator))
            search_button.click()
            print(f"Clicked Search button for course: '{capitalised_course_name}'")

            # ### HASHTAG: WAIT FOR RESULTS OR 'NO DATA' MESSAGE ###
            short_wait = WebDriverWait(self.driver, 7)
            try:
                # Check for "no data" message first
                short_wait.until(
                    EC.presence_of_element_located((By.XPATH, '//*[contains(text(),"Nessun dato da visualizzare.")]')))
                print(f"Search result: Course '{course_name}' NOT found (no data message)")
                return False  # Course does not exist
            except TimeoutException:
                # No "no data" message, look for exact match
                course_name_lower = cleaned_course_name.lower()
                case_insensitive_xpath = f"//table[@summary='Corsi']//a[translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='{course_name_lower}']"

                try:
                    short_wait.until(EC.presence_of_element_located((By.XPATH, case_insensitive_xpath)))
                    print(f"Search result: Course '{course_name}' FOUND (exact match)")
                    return True  # Exact match found
                except TimeoutException:
                    print(f"Search result: Course '{course_name}' NOT found (no exact match)")
                    return False  # Exact match not found

        except Exception as e:
            print(f"Error during search_course for '{course_name}': {e}")
            # Save screenshot on error
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                ss_path = f"error_search_course_{timestamp}.png"
                self.driver.save_screenshot(ss_path)
                print(f"Saved screenshot: {ss_path}")
            except Exception as ss_e:
                print(f"Could not save screenshot: {ss_e}")
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
            ### HASHTAG: THE FIX - WAIT FOR THE NEXT PAGE TO LOAD ✅ ###
            # Add a wait here for an element that ONLY exists on the course details page.
            # Waiting for the "Edizioni" tab itself to be clickable is a robust choice.
            edizioni_tab_xpath_on_details_page = '//div[contains(@id, ":lsCrDtl:UPsp1:classTile::text")]'
            self.wait.until(EC.element_to_be_clickable((By.XPATH, edizioni_tab_xpath_on_details_page)))
            print(f"Model: Course details page loaded successfully (found Edizioni tab).")
            # You can keep or remove the _pause_for_visual_check here, this explicit wait is better.
            # self._pause_for_visual_check()
            # Only return True AFTER the next page is confirmed loaded.
            return True

        except Exception as e:
            print(f"Model: Could not find or click the link for '{course_name}'. Error: {e}")
            return False

    def create_course(self, course_details):
        """
        Create a SINGLE course in Oracle.

        IMPORTANT: This assumes you're already on the Corsi page
        (either from navigation or after a search).
        """
        try:
            course_name = course_details['title'].title()
            print(f"Creating course: '{course_name}'")

            # ### FIXED: DON'T RE-NAVIGATE - JUST WAIT FOR PAGE TO BE READY ###
            # We should already be on the Corsi page from search_course()
            # Just wait for any loading to complete
            time.sleep(1)

            # Wait for blocking overlay to disappear (if any)
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.invisibility_of_element_located((By.CLASS_NAME, "AFBlockingGlassPane")))
            except:
                pass

            # ### CLICK CREATE BUTTON WITH ROBUST XPATH ###
            crea_button_xpaths = [
                "//a[.//span[text()='Create']]",  # English
                "//a[.//span[text()='Crea']]",  # Italian
                "//a[contains(@id, 'crtBtn')]",  # By ID fragment
            ]

            crea_button = None
            for xpath in crea_button_xpaths:
                try:
                    crea_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, xpath)))
                    print(f"Found Create button with XPath: {xpath}")
                    break
                except TimeoutException:
                    continue

            if not crea_button:
                self.driver.save_screenshot("error_create_button_not_found.png")
                raise Exception("Could not find 'Create/Crea' button")

            crea_button.click()
            print(f"Clicked 'Create' button for '{course_name}'")
            self._pause_for_visual_check()

            # ### FILL COURSE TITLE ###
            title_field = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, '//*[@id="pt1:_FOr1:1:_FONSr2:0:MAnt2:2:lsVwCrs:ttlInp::content"]')))
            title_field.send_keys(course_details['title'])
            title_field.send_keys(Keys.TAB)
            self._pause_for_visual_check()

            # ### HASHTAG: FILL PROGRAMME (OPTIONAL) ###
            programma_field = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, '//*[@id="pt1:_FOr1:1:_FONSr2:0:MAnt2:2:lsVwCrs:slbsRte::_cic"]/div[1]/div[2]/div')))
            programma_field.send_keys(course_details.get('programme', ''))
            programma_field.send_keys(Keys.TAB)
            self._pause_for_visual_check()

            # ### HASHTAG: FILL SHORT DESCRIPTION ###
            desc_breve = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, '//input[contains(@id, ":MAnt2:2:lsVwCrs:shdsInp::content")]')))
            desc_breve.send_keys(course_details.get('short_description', ''))
            desc_breve.send_keys(Keys.TAB)
            self._pause_for_visual_check()

            # ### HASHTAG: FILL PUBLICATION DATE (FROM EXCEL!) ###
            data_inizio_pubblic = self.wait.until(EC.visibility_of_element_located(
                (By.XPATH, '//input[contains(@id, ":MAnt2:2:lsVwCrs:sdDt::content")]')))
            data_inizio_pubblic.clear()

            # Convert date object to string format DD/MM/YYYY
            publication_date_str = course_details['start_date'].strftime("%d/%m/%Y")
            print(f"Setting publication date for '{course_name}': {publication_date_str}")

            data_inizio_pubblic.send_keys(publication_date_str)
            data_inizio_pubblic.send_keys(Keys.TAB)
            self._pause_for_visual_check()

            # ### HASHTAG: SAVE AND CLOSE ###
            salve_chiude = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="pt1:_FOr1:1:_FONSr2:0:MAnt2:2:lsVwCrs:svcBtn"]')))
            salve_chiude.click()
            print(f"Clicked 'Salva e Chiudi' for '{course_name}'")
            self._pause_for_visual_check()

            # ### HASHTAG: WAIT FOR CONFIRMATION (EDIZIONI TAB APPEARS) ###
            edizioni_tab_xpath = '//div[contains(@id, ":lsCrDtl:UPsp1:classTile::text")]'
            self.wait.until(EC.presence_of_element_located((By.XPATH, edizioni_tab_xpath)))
            print(f"✅ Course '{course_name}' created successfully!")

            # ### NEW: CLICK BACK BUTTON TO RETURN TO CORSI LIST ###
            if not self._click_back_button():
                print("Warning: Could not click back button, but course was created")

            return f"✅🤩 Successo! Il corso '{course_name}' è stato creato."

        except Exception as e:
            error_msg = f"‼️👩🏻‍✈️ Errore durante la creazione del corso '{course_details.get('title', 'UNKNOWN')}': {str(e)}"
            print(error_msg)

            # # Save screenshot on error
            # try:
            #     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            #     course_title_safe = course_details.get('title', 'unknown').replace(' ', '_')
            #     ss_path = f"error_create_{course_title_safe}_{timestamp}.png"
            #     self.driver.save_screenshot(ss_path)
            #     print(f"Saved error screenshot: {ss_path}")
            # except:
            #     pass

            return error_msg

    def _click_back_button(self):
        """
        Click the 'Indietro' (Back) button to return to the Corsi list.

        This is needed after creating a course, as 'Salva e Chiudi'
        takes us to the course details page.
        """
        try:
            # Multiple XPaths for the back button
            back_button_xpaths = [
                "//svg[@aria-label='Indietro']/ancestor::a",  # SVG with aria-label
                "//svg[contains(@id, 'SPdonei::icon')]/parent::a",  # By ID fragment
                "//a[.//svg[@aria-label='Indietro']]",  # Anchor containing the SVG
                "//span[text()='Indietro']/ancestor::a",  # If there's a text span
                "//a[contains(@id, 'SPdonei')]",  # By partial ID
            ]

            back_button = None
            for xpath in back_button_xpaths:
                try:
                    back_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, xpath)))
                    print(f"Found 'Indietro' button with XPath: {xpath}")
                    break
                except TimeoutException:
                    continue

            if not back_button:
                # Try clicking the parent element directly
                try:
                    back_button = self.driver.find_element(
                        By.XPATH, "//*[contains(@aria-label, 'Indietro')]")
                    print("Found back button via aria-label")
                except:
                    self.driver.save_screenshot("error_back_button_not_found.png")
                    raise Exception("Could not find 'Indietro' (Back) button")

            back_button.click()
            print("Clicked 'Indietro' button to return to Corsi list")

            # Wait for Corsi page to load (search box appears)
            self.wait.until(EC.presence_of_element_located(
                (By.NAME, 'pt1:_FOr1:1:_FONSr2:0:MAnt2:1:MgCrUpl:UPsp1:r2:0:crsQry2:value00')))
            print("Successfully returned to Corsi list page")

            self._pause_for_visual_check()
            return True

        except Exception as e:
            print(f"Error clicking back button: {e}")
            return False

    ### HASHTAG: UPDATED HELPER FOR ACTIVITY CREATION
    def _create_single_activity(self, unique_title, full_description, activity_date_obj, start_time_str, end_time_str,impegno_previsto_in_ore):
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
            if impegno_previsto_in_ore: # Check if user provided input
                 impeg_pre_in_ore = self.wait.until(EC.presence_of_element_located((By.XPATH, '//input[@aria-label="Impegno previsto in ore"]')))
                 impeg_pre_in_ore.clear()
                 impeg_pre_in_ore.send_keys(impegno_previsto_in_ore)
                 print(f"Entered future field value: {impegno_previsto_in_ore}")
                 self._pause_for_visual_check()

            # Save and press OK button
            ok_button_attivita = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, '//a[./span[text()="OK"]]')))
            ok_button_attivita.click()
            print(f"Clicked OK for activity '{unique_title}' on {activity_date_str}")
            # Wait for the OK button popup to disappear before proceeding
            self.wait.until(EC.invisibility_of_element_located((By.XPATH, '//a[./span[text()="OK"]]')))
            self._pause_for_visual_check()  # Short pause after popup closes
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

            print(
                f"Model (EDITION): Creating edition for {course_name} start {edition_start_date.strftime('%d/%m/%Y')}")
            self._pause_for_visual_check()

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
                full_description_text = f"{course_name}-{edition_start_date.strftime('%d/%m/%Y')}-/n{description}"
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
            self.wait.until(EC.presence_of_element_located((By.XPATH,"//a[contains(@id, ':lsVwCls:lngSel::drop')]")))
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
                    impegno_previsto_in_ore=activity.get('impegno_previsto_in_ore', '')  # Safely get future value
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

        ### --- START: NEW METHODS FOR STUDENT INSERTION --- ###

        # Helper to find and open the specific edition using search

    ### HASHTAG: NEW HELPER FUNCTION FOR PRESENTER ✅ ###
    # This simple function is called by the presenter after opening the course.
    def open_edizioni_tab(self):
            try:
                edizioni_tab_xpath = '//div[contains(@id, ":lsCrDtl:UPsp1:classTile::text")]'
                edizioni_tab_element = self.wait.until(EC.element_to_be_clickable((By.XPATH, edizioni_tab_xpath)))
                #self.driver.execute_script("arguments[0].click();", edizioni_tab_element)
                edizioni_tab_element.click()
                print("Model:Clicked 'Edizioni' tab ")
                # Wait for the search box on the editions page to confirm load
                self.wait.until(
                    EC.presence_of_element_located((By.XPATH, "//input[contains(@aria-label, 'Titolo edizione')]")))
                print("Model:Search box on the editions page is loaded")
                return True
            except Exception as e:
                print(f"Errore: Impossibile fare clic sulla scheda 'Edizioni'. Error: {e}")
                return False

    def _search_and_open_edition(self, edition_name, edition_publish_date_obj):
            try:
                date_str = edition_publish_date_obj.strftime('%d/%m/%Y')
                print(
                    f"Model: Searching for edition '{edition_name}' with publish date {edition_publish_date_obj.strftime('%d/%m/%Y')}")
                time.sleep(2) #remove it after bugging solved

                # --- Fill Search Form (This part is correct) ---
                title_input_edizione = self.wait.until(
                    EC.presence_of_element_located((By.XPATH, "//input[@aria-label=' Titolo edizione']")))
                # title_input_edizione.clear()
                title_input_edizione.send_keys(edition_name)

                date_input_edizione = self.wait.until(
                    EC.presence_of_element_located((By.XPATH, "//input[@aria-label=' Data inizio pubblicazione']")))
                date_str = edition_publish_date_obj.strftime('%d/%m/%Y')
                self.driver.execute_script("arguments[0].value=arguments[1];", date_input_edizione, date_str)
                date_input_edizione.send_keys(Keys.TAB)
                time.sleep(2)  # remove it after bugging solved

                search_button_edizione = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//button[text()='Cerca']")))
                search_button_edizione.click()
                print("Model: Search submitted. Waiting for results.")
                #time.sleep(2)  # remove it after bugging solved

                #checing for appeared results and choosing it
                # It waits for the search to finish AND for that specific link to become clickable.
                link_xpath = "//a[contains(@id, ':_ATp:srTbl:') and contains(@id, ':clnmLnk')]"
                link = self.wait.until(EC.element_to_be_clickable((By.XPATH, link_xpath)))
                print("Model: Found first result link. Clicking it...")
                link.click()
                self._pause_for_visual_check()
                print(f"Model: Clicked on edition link.")
                return True

            except Exception as e:
                print(f"Model: Could not find/click edition '{edition_name}' with date {date_str}. Error: {e}")
                # Try to save a screenshot to help debug
                try:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    ss_path = f"error_search_edition_{timestamp}.png"
                    self.driver.save_screenshot(ss_path)
                    print(f"Saved screenshot on search error: {ss_path}")
                except Exception as ss_e:
                    print(f"Could not save screenshot: {ss_e}")
                return False

            # model.py (Corrected function)

    def _perform_student_addition_steps(self, student_list, conv_online, conv_presenza):
        try:
            # --- PART 1: ADD STUDENTS ---
            # (This part for adding students and clicking 'OK' is working)

            allievi_tab = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//div[contains(@id, ':clDtSp1:UPsp1:learnerTile::text')]"))
            )
            allievi_tab.click()
            print("Clicked on 'Allievi' tab")
            self._pause_for_visual_check()

            self.wait.until(EC.element_to_be_clickable((By.XPATH, "//a[normalize-space()='Aggiungi allievi']"))).click()
            print("Clicked on 'Aggiungi allievi' button")
            self._pause_for_visual_check()

            self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, '//td[contains(@class, "xo2") and normalize-space()="Assegnazione volontaria"]'))).click()
            print("Clicked on 'Assegnazione volontaria' option")
            self._pause_for_visual_check()

            list_assegna_come = "Team Organizzazione & Sviluppo"
            print(f"Attempting to select '{list_assegna_come}' from dropdown.")
            try:
                assegna_come_input_xpath = '//input[contains(@id, ":clDtSp1:UPsp1:r11:1:r5:0:SP2:r1:0:soc2::content")]'
                assegna_come_trigger = self.wait.until(EC.element_to_be_clickable((By.XPATH, assegna_come_input_xpath)))
                assegna_come_trigger.click()
            except ElementClickInterceptedException:
                print("Click intercepted. Trying JavaScript click.")
                assegna_come_trigger = self.wait.until(
                    EC.presence_of_element_located((By.XPATH, assegna_come_input_xpath)))
                self.driver.execute_script("arguments[0].click();", assegna_come_trigger)
            self._pause_for_visual_check()

            option_xpath = f"//li[contains(text(), '{list_assegna_come}')]"
            self.wait.until(EC.element_to_be_clickable((By.XPATH, option_xpath))).click()
            print(f"Selected '{list_assegna_come}'.")
            self._pause_for_visual_check()

            self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[text()='Successivo']"))).click()
            print("Clicked first 'Successivo' button")
            time.sleep(2)  # Wait for next page

            print(f"--- Adding {len(student_list)} students ---")
            person_input_xpath = '//input[@aria-label="Aggiungi una persona"]'
            for i, persona in enumerate(student_list):
                try:
                    aggiungi_una_persona = self.wait.until(EC.element_to_be_clickable((By.XPATH, person_input_xpath)))
                    aggiungi_una_persona.clear()
                    aggiungi_una_persona.send_keys(persona)
                    time.sleep(1)
                    aggiungi_una_persona.send_keys(Keys.ENTER)
                    self.wait.until(
                        EC.visibility_of_element_located((By.XPATH, f"//span[contains(text(), '{persona}')]")))
                    print(f"({i + 1}/{len(student_list)}) Added and verified '{persona}'.")
                except Exception as e:
                    print(f"Could not add '{persona}'. Maybe not found or error: {e}")
                    return False  # Stop if one student fails

            self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[text()='Successivo']"))).click()
            print("Clicked second 'Successivo' button")
            time.sleep(2)

            self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[text()='Sottometti']"))).click()
            print("Clicked 'Sottometti' button")
            time.sleep(2)

            print("Waiting for overlay...")
            self.wait.until(EC.invisibility_of_element_located((By.CLASS_NAME, "AFBlockingGlassPane")))
            self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@id,':1:cfmDlg::ok')]"))).click()
            print("Clicked 'OK' after submission")
            time.sleep(2)

            # --- PART 2: Visualise all added people ---
            # (This part is also working, waiting for the table to load)
            found_results = False
            attempts = 0
            max_attempts = 10
            try:
                print("Clicking on 'Stato_assegnazione' dropdown")
                stato_assegnazione_allievi = WebDriverWait(self.driver, 15).until(EC.element_to_be_clickable(
                    (By.XPATH, "//span[contains(@class, 'x1kn')]/a[contains(@id, ':lrasQry:value20::drop')]")))
                stato_assegnazione_allievi.click()
                print("Clicking on 'Tutto' option")
                stato_assegnazione_allievi_tutto = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, '//*[contains(text(),"Tutto")]')))
                stato_assegnazione_allievi_tutto.click()
                print("Successfully clicked 'Tutto'.")
            except Exception as e:
                print(f"Initial setup (filter) failed. Cannot continue. Error: {e}")
                return False

            while not found_results and attempts < max_attempts:
                attempts += 1
                print(f"Attempt {attempts} to find search results...")
                try:
                    print("Clicking on 'Cerca' button")
                    cerca_button_allievi = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[text()='Cerca']")))
                    cerca_button_allievi.click()
                    print("Clicked on 'Cerca' button")
                    time.sleep(3)
                    print("Waiting for search results to load...")
                    dynamic_xpath = "//td[@class='xen'][1]"  # Wait for first data cell
                    WebDriverWait(self.driver, 20).until(EC.presence_of_element_located((By.XPATH, dynamic_xpath)))
                    print("Search results table has reloaded. Breaking the loop.")
                    found_results = True
                except Exception as e:
                    print(f"Search results not found on attempt {attempts}. Retrying... Error: {e}")
                    time.sleep(2)

            # --- PART 3: Send Notifications ---
            if not found_results:
                print("Failed to find search results after maximum attempts. Skipping notifications.")
                return False
            else:
                ### HASHTAG: REPLACED FAULTY LOGIC WITH YOUR WORKING SCRIPT ✅ ###

                # Wait for the blocking pane to disappear before clicking
                print("Results are visible. Waiting for blocking pane to disappear...")
                self.wait.until(EC.invisibility_of_element_located(
                    (By.CLASS_NAME, "AFBlockingGlassPane")
                ))
                print("Blocking pane has disappeared. Proceeding to notifications.")
                time.sleep(2)

                print("--- Starting notification process ---")
                # Click 'Azione di massa'
                azione_di_massa_button_allievi = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//a[text()='Azione di massa']")))
                azione_di_massa_button_allievi.click()
                print("Clicked on 'Azione di massa' button")
                self._pause_for_visual_check()

                # Choose 'Invia avviso'
                print("Attempting to click on 'Invia avviso' option.")
                # Your working list of XPaths
                invia_avviso_xpaths = [
                    "//tr[contains(@id,':masUpdt:itr9:1:cmi1') and .//td[normalize-space()='Invia avviso']]",
                    "//td[normalize-space()='Invia avviso']",
                    "//*[text()='Invia avviso']"
                ]
                found = False
                # Your working loop
                for xpath in invia_avviso_xpaths:
                    try:
                        invia_avviso_allievi = self.wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
                        print(f"Found 'Invia avviso' using XPath: {xpath}. Now attempting a JavaScript click.")
                        self.driver.execute_script("arguments[0].click();", invia_avviso_allievi)
                        print("Clicked on 'Invia avviso' option using JavaScript.")
                        found = True
                        break  # Success! Exit the loop
                    except Exception as e:
                        print(f"Failed to click with XPath: {xpath}. Trying next one. Error: {e}")

                if not found:
                    print("Failed to find or click 'Invia avviso' option with all methods.")
                    return False  # Fail the function

                self._pause_for_visual_check()
                time.sleep(2)  # pause_long()

                # in opened window choose 'Utilizzare tutti i # risultati dei criteri di ricerca'
                print("Attempting to click 'Utilizzare tutti i # risultati dei criteri di ricerca'.")
                try:
                    utilizzare_tutti = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH,
                                                    "//label[contains(normalize-space(),'Utilizzare tutti i') and contains(normalize-space(),'risultati dei criteri di ricerca')]"))
                    )
                    utilizzare_tutti.click()
                    print("Successfully clicked on 'Utilizzare tutti i ...' label.")

                except Exception as e:
                    print(f"Failed to click the label. Trying to click the radio button directly. Error: {e}")
                    try:
                        utilizzare_tutti_fallback = self.wait.until(
                            EC.element_to_be_clickable((By.XPATH, "//*[contains(@id,':masUpdt:dc_r1:0:SP2:sor1:_1')]"))
                        )
                        utilizzare_tutti_fallback.click()
                        print("Clicked on radio button via fallback method.")
                    except Exception as e_fallback:
                        print(f"Failed to click 'Utilizzare tutti...' even with fallback. Error: {e_fallback}")
                        return False  # Fail the function

                self._pause_for_visual_check()
                time.sleep(2)  # pause_long()

                # press on button 'Successivo'
                self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[text()='Successivo']"))).click()
                print("Clicked on 'Successivo' button")
                self._pause_for_visual_check()
                time.sleep(2)  # pause_long()

                ### HASHTAG: REPLACED HARDCODED CLICKS WITH VARIABLES ✅ ###
                # This now uses the boolean variables passed from the Streamlit form
                if conv_online:
                    self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, "//label[contains(@id,':itt1:5:sbc1::Label1')]"))).click()
                    print("Successfully flagged on 'CONVOCAZIONE PARTECIPANTE - ONLINE' option.")
                    self._pause_for_visual_check()

                if conv_presenza:
                    self.wait.until(
                        EC.element_to_be_clickable(
                            (By.XPATH, "//label[contains(@id,':itt1:6:sbc1::Label1')]"))).click()
                    print("Successfully flagged on 'CONVOCAZIONE PARTECIPANTE - PRESENTE' option.")
                    self._pause_for_visual_check()

                # press sottometti button
                self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[text()='Sottometti']"))).click()
                print("Clicked on 'Sottometti' button")
                self._pause_for_visual_check()

                # press Ok button
                self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(@id,'masUpdt:dc_d11::ok')]"))).click()
                print("Clicked on 'OK' button")
                self._pause_for_visual_check()
                time.sleep(2)  # pause_long()

            return True  # Indicate success

        except Exception as e:
            print(f"An error occurred during student addition steps: {e}")
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                ss_path = f"error_add_students_{timestamp}.png"
                self.driver.save_screenshot(ss_path)
                print(f"Saved screenshot on student add error: {ss_path}")
            except Exception as ss_e:
                print(f"Could not save screenshot: {ss_e}")
            return False  # Indicate failure

    def close_driver(self):
        print("Model: Closing driver.")
        self.driver.quit()