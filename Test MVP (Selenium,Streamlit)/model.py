# model.py
# --- IMPORTS ---
import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.edge.options import Options
from selenium.common.exceptions import TimeoutException


#This is a special function called the constructor.
# It automatically runs once when you first create a robot from the blueprint.
# Its job is to do all the initial setup.
class OracleAutomator:
    # This class encapsulates all the browser automation steps.
    def __init__(self, driver_path,debug_mode = False,debug_pause=1,headless=False):
        options = Options()
        # Allow switching between headless and visible mode
        if headless:
            #Required flags for Edge headless mode
            options.add_argument("--headless=new")  # modern flag
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--no-sandbox")
        else:
            # force a visible browser with defined size
            options.add_argument("--window-size=1920,1080")

        #selenium driver configuration
        service = Service(executable_path=driver_path)
        self.driver = webdriver.Edge(service=service, options=options)
        self.wait = WebDriverWait(self.driver, 40)

        #debug settings
        self.debug_mode = debug_mode
        self.debug_pause_duration = debug_pause

        mode = "Headless" if headless else "Visible"
        print(f"Model: WebDriver initialized in {mode} mode.")


    # a new private helper method for pausing
    # The underscore '_' at the beginning is a Python convention for internal/helper methods
    def _pause_for_visual_check(self):
        # This method will only pause if debug_mode is set to True
        if self.debug_mode:
            time.sleep(self.debug_pause_duration)

    def login(self, url, username, password):
        # This method handles the login process.
        # It now takes the url, username, and password as arguments
        # instead of having them hardcoded.
        try:
            self.driver.get(url)
            username_field = self.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="userid"]')))
            password_field = self.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="password"]')))
            signin_btn = self.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="btnActive"]')))

            username_field.send_keys(username)
            password_field.send_keys(password)
            signin_btn.click()
            print("Model: Logged in successfully.")
            return True
        except Exception as e:
            print(f"Model: Error during login: {e}")
            return False

    def navigate_to_course_creation(self,course_details):
        """
               Navigate from homepage to the 'Corsi' list page.
               Used by both course creation and edition flows.
               """

        try:
            course_name = course_details['title']
            miogruppodilavoro = self.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="groupNode_workforce_management"]')))
            miogruppodilavoro.click()
            print("Model: Clicked 'Mio gruppo di lavoro'")

            apprendimento = self.wait.until(EC.presence_of_element_located((By.ID, 'WLF_FUSE_LEARN_ADMIN')))
            apprendimento.click()
            print("Model: Clicked 'Apprendimento'")

            corsi = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//a[@title="Corsi" and text()="Corsi"]')))
            corsi.click()
            print("Model: Clicked 'Corsi'")
            #self._pause_for_visual_check()  # <-- PAUSE HERE

            print(f'Model: Starting course creation for "{course_name}"')
            self._pause_for_visual_check()  # <-- PAUSE HERE

            # 1.search for the course
            search_box = self.wait.until(EC.presence_of_element_located(
                (By.NAME, 'pt1:_FOr1:1:_FONSr2:0:MAnt2:1:MgCrUpl:UPsp1:r2:0:crsQry2:value00')))
            search_box.clear()
            search_box.send_keys(course_name)

            date_input = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, '//*[@id="pt1:_FOr1:1:_FONSr2:0:MAnt2:1:MgCrUpl:UPsp1:r2:0:crsQry2:value10::content"]')))
            date_input.clear()
            date_input.send_keys("01/01/2000")

            cerca_button = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, '//*[@id="pt1:_FOr1:1:_FONSr2:0:MAnt2:1:MgCrUpl:UPsp1:r2:0:crsQry2::search"]')))
            cerca_button.click()
            print("Model: Searched for existing course.")
            self._pause_for_visual_check()  # <-- PAUSE HERE

            # ---Check if the course exists ot create new one ---
            try:
                # if it founds 'no data' message,it means Selenium will start to create a new course
                self.print("Existing course found. Proceeding to create an edition.")

            # click on the course name
                existed_course_name = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, f'//table[@summary="Corsi"]//a[contains(text(), "{course_name}")]')))
                existed_course_name.click()
                self.print(f"Clicked on the existing course name: {course_name}")
            except TimeoutException:
                self.print(f'Course: {course_name} not found. Please create a course in above form.')


           # return True

        except Exception as e:
            print(f"Model: Error during navigation : {e}")
            return False

    def create_course(self,course_details):
        #main method that creates the course
        try:
            course_name = course_details['title']
            print(f'Model: Starting course creation for "{course_name}"')
            self._pause_for_visual_check()  # <-- PAUSE HERE

            #1.search for the course
            search_box = self.wait.until(EC.presence_of_element_located(
                (By.NAME, 'pt1:_FOr1:1:_FONSr2:0:MAnt2:1:MgCrUpl:UPsp1:r2:0:crsQry2:value00')))
            search_box.clear()
            search_box.send_keys(course_name)

            date_input = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, '//*[@id="pt1:_FOr1:1:_FONSr2:0:MAnt2:1:MgCrUpl:UPsp1:r2:0:crsQry2:value10::content"]')))
            date_input.clear()
            date_input.send_keys("01/01/2000")

            cerca_button = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, '//*[@id="pt1:_FOr1:1:_FONSr2:0:MAnt2:1:MgCrUpl:UPsp1:r2:0:crsQry2::search"]')))
            cerca_button.click()
            print("Model: Searched for existing course.")
            self._pause_for_visual_check()  # <-- PAUSE HERE

            #---Check if the course exists ot create new one ---
            try:
                #if it founds 'no data' message,it means Selenium will start to create a new course
                self.wait.until(EC.presence_of_element_located((By.XPATH, '//*[contains(text(),"Nessun dato da visualizzare.")]')))
                print("Model:No course found. Proceeding to create new course.")

                crea_button = self.wait.until(EC.element_to_be_clickable(
                    (By.XPATH, '//*[@id="pt1:_FOr1:1:_FONSr2:0:MAnt2:1:MgCrUpl:UPsp1:r2:0:srAtbl:_ATp:crtBtn"]/a/span')))
                crea_button.click()
                print("Model: Clicked 'Crea' button.")
                self._pause_for_visual_check()  #<-- PAUSE HERE

                # --- Fill the new course form using data from course_details ---
                title_field = self.wait.until(EC.presence_of_element_located(
                    (By.XPATH, '//*[@id="pt1:_FOr1:1:_FONSr2:0:MAnt2:2:lsVwCrs:ttlInp::content"]')))
                title_field.send_keys(course_details['title'])
                title_field.send_keys(Keys.TAB)
                self._pause_for_visual_check()

                programma_field = self.wait.until(EC.presence_of_element_located(
                    (By.XPATH, '//*[@id="pt1:_FOr1:1:_FONSr2:0:MAnt2:2:lsVwCrs:slbsRte::_cic"]/div[1]/div[2]/div')))
                programma_field.send_keys(course_details['programme'])
                programma_field.send_keys(Keys.TAB)
                self._pause_for_visual_check()

                desc_breve = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, '//input[contains(@id, ":MAnt2:2:lsVwCrs:shdsInp::content")]')))
                desc_breve.send_keys(course_details['short_description'])
                desc_breve.send_keys(Keys.TAB)
                self._pause_for_visual_check()

                data_inizio_pubblic = self.wait.until(EC.visibility_of_element_located(
                    (By.XPATH, '//input[contains(@id, ":MAnt2:2:lsVwCrs:sdDt::content")]')))
                data_inizio_pubblic.clear()
                self._pause_for_visual_check()

                # The date is formatted to the required DD/MM/YYYY format.
                publication_date_str = course_details['start_date'].strftime("%d/%m/%Y")
                data_inizio_pubblic.send_keys(publication_date_str)
                data_inizio_pubblic.send_keys(Keys.TAB)
                self._pause_for_visual_check()

                salve_chiude = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="pt1:_FOr1:1:_FONSr2:0:MAnt2:2:lsVwCrs:svcBtn"]')))
                salve_chiude.click()
                self._pause_for_visual_check()

                # Now wait until the edizioni tab appears (this confirms save & navigation are done)
                edizioni_tab_xpath = '//div[contains(@id, ":lsCrDtl:UPsp1:classTile::text")]'
                edizioni_tab = self.wait.until(EC.presence_of_element_located((By.XPATH, edizioni_tab_xpath)))

                print(f"Model: New course '{course_details['title']}' created successfully.")
                return f"✅🤩 Successo! Il corso '{course_details['title']}' è stato creato."

            except TimeoutException:
            # If the "no data" message is NOT found, we assume the course already exists.
                print(f"Model: Course '{course_name}' already exists.")
                return f"‼️🕵🏻 ️Attenzione: Il corso '{course_name}' esiste già e non è stato creato di nuovo."

        except Exception as e:
            print(f"Model: An error occurred during course creation: {e}")
            return f"‼️👩🏻‍✈️ Errore: Si è verificato un errore durante l'automazione. Controlla la console per i dettagli."

    #---Script for creation edition ---
    def create_edition(self, edition_details):
        """
        edition_details: dict:
         - course_name, edition_start_date (str dd/mm/YYYY), duration_days, location, supplier, price, language, moderator_type
        Assumes we are currently on the course detail page (edizioni tab reachable).
        """
        try:
            course_name = edition_details['course_name']
            if isinstance(edition_details['edition_start_date'], str):
                edition_start_date = datetime.strptime(edition_details['edition_start_date'], "%d/%m/%Y")
            else:
                edition_start_date = edition_details['edition_start_date']

            duration_days = int(edition_details.get('duration_days', 1))
            supplier = edition_details.get('supplier', "")
            location = edition_details.get('location', "")
            price = edition_details.get('price', "0")
            language = edition_details.get('language', "")
            moderator_type = edition_details.get('moderator_type', "")

            print(
                f"Model (EDITION): Creating edition for {course_name}, start {edition_start_date.strftime('%d/%m/%Y')}")
            self._pause_for_visual_check()

            # Click 'Edizioni' tab
            edizioni_tab_xpath = '//div[contains(@id, ":lsCrDtl:UPsp1:classTile::text")]'
            edizioni_tab = self.wait.until(EC.presence_of_element_located((By.XPATH, edizioni_tab_xpath)))
            edizioni_tab.click()
            self._pause_for_visual_check()

            # Click Crea -> Edizione guidata da docente
            button_crea_edizioni = self.wait.until(EC.presence_of_element_located((By.XPATH, "//a[text()='Crea']")))
            button_crea_edizioni.click()
            self._pause_for_visual_check()

            option_of_button_crea_edizioni = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//td[text()='Edizione guidata da docente']")))
            option_of_button_crea_edizioni.click()
            self._pause_for_visual_check()

            # titolo edizione
            titolo_edizione = self.wait.until(
                EC.presence_of_element_located((By.XPATH, '//input[contains(@id, ":lsVwCls:ttlInp::content")]')))
            titolo_edizione.send_keys("-" + edition_start_date.strftime("%d/%m/%Y"))
            self._pause_for_visual_check()

            # description (rich textbox area)
            descirione_edizione = self.wait.until(
                EC.presence_of_element_located((By.XPATH, '//div[contains(@aria-label, "main") and @role="textbox"]')))
            descirione_edizione.send_keys(f"{course_name}-{edition_start_date.strftime('%d/%m/%Y')}-details")
            self._pause_for_visual_check()

            # publication start: 2 months before
            two_months_before = edition_start_date - relativedelta(months=2)
            pubblicazione_edition_date_2month_before = two_months_before.strftime("%d/%m/%Y")
            edizione_data_inizio_pubblicazione = self.wait.until(
                EC.presence_of_element_located((By.XPATH, '//input[contains(@id, ":lsVwCls:sdDt::content")]')))
            edizione_data_inizio_pubblicazione.clear()
            edizione_data_inizio_pubblicazione.send_keys(pubblicazione_edition_date_2month_before)
            self._pause_for_visual_check()

            # publication end date
            edition_end_date_obj = edition_start_date + timedelta(days=duration_days - 1)
            pubblicazione_end_date_str = (edition_end_date_obj + timedelta(days=1)).strftime("%d/%m/%Y")
            edizione_data_fine_pubblicazione = self.wait.until(
                EC.presence_of_element_located((By.XPATH, '//input[contains(@id,"lsVwCls:edDt::content")]')))
            edizione_data_fine_pubblicazione.clear()
            edizione_data_fine_pubblicazione.send_keys(pubblicazione_end_date_str)
            self._pause_for_visual_check()

            # set edition start and end
            dettagli_ed_data_inizio_edizione = self.wait.until(
                EC.presence_of_element_located((By.XPATH, '//input[contains(@id, ":lsVwCls:liSdDt::content")]')))
            dettagli_ed_data_inizio_edizione.clear()
            dettagli_ed_data_inizio_edizione.send_keys(edition_start_date.strftime("%d/%m/%Y"))
            self._pause_for_visual_check()

            dettagli_ed_data_fine_edizione = self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//input[contains(@id, ':lsVwCls:liEdDt::content')]")))
            dettagli_ed_data_fine_edizione.clear()
            dettagli_ed_data_fine_edizione.send_keys(edition_end_date_obj.strftime("%d/%m/%Y"))
            self._pause_for_visual_check()

            # select aula principale via lookup
            aula_prince_xpath = '//*[contains(@id, "primaryClassroomName1Id::lovIconId")]'
            select_aula_principale = self.wait.until(EC.element_to_be_clickable((By.XPATH, aula_prince_xpath)))
            select_aula_principale.click()
            self._pause_for_visual_check()

            # search location inside lookup
            cerca_aula_button = self.wait.until(EC.visibility_of_element_located((By.XPATH, "//a[text()='Cerca...']")))
            cerca_aula_button.click()
            self._pause_for_visual_check()

            box_cerca_aula_parole_chiave = self.wait.until(EC.presence_of_element_located(
                (By.XPATH,
                 '//input[contains(@id, "primaryClassroomName1Id::_afrLovInternalQueryId:value00::content")]')))
            box_cerca_aula_parole_chiave.send_keys(location)
            self._pause_for_visual_check()

            button_parole_chiave_cerca = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[text()='Cerca' and contains(@id, 'primaryClassroomName1Id')]")))
            button_parole_chiave_cerca.click()
            self._pause_for_visual_check()

            # try to select location
            try:
                self.wait.until(EC.presence_of_element_located((By.XPATH,
                                                                f'//div[contains(@id, "primaryClassroomName1Id_afrLovInternalTableId::db")]//tr[.//text()[contains(., "Nessuna riga da visualizzare")]]')))
                print(f"⚠️ The location '{location}' was not found.")
            except TimeoutException:
                list_aula_option_row = self.wait.until(EC.element_to_be_clickable((
                    By.XPATH,
                    f'//div[contains(@id, "primaryClassroomName1Id_afrLovInternalTableId::db")]//td[contains(@class, "xen") and .//span[text()="{location}"]]'
                )))
                list_aula_option_row.click()
                self._pause_for_visual_check()

            ok_button = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[text()='OK' and contains(@id, 'primaryClassroomName1Id')]")))
            ok_button.click()
            self._pause_for_visual_check()

            # choose language
            if language:
                choose_lingua = self.wait.until(
                    EC.presence_of_element_located((By.XPATH, "//a[contains(@id, ':lsVwCls:lngSel::drop')]")))
                choose_lingua.click()
                self._pause_for_visual_check()
                find_lingua = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, f'//*[contains(text(), \"{language}\")]')))
                find_lingua.click()
                self._pause_for_visual_check()

            # choose moderator type
            if moderator_type:
                choose_tipo_moderatore = self.wait.until(
                    EC.presence_of_element_located((By.XPATH, "//a[contains(@id, ':lsVwCls:socFaciType::drop')]")))
                choose_tipo_moderatore.click()
                self._pause_for_visual_check()
                find_tipo_moderatore = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, f'//*[contains(text(), \"{moderator_type}\")]')))
                find_tipo_moderatore.click()
                self._pause_for_visual_check()

            # choose supplier
            if supplier:
                choose_nome_fornitore_formazione = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(@id, ':lsVwCls:supplierNameId::lovIconId')]")))
                choose_nome_fornitore_formazione.click()
                self._pause_for_visual_check()
                button_cerca_nome_fornitore_formazione = self.wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//a[contains(@id, ':lsVwCls:supplierNameId::dropdownPopup::popupsearch')]")))
                button_cerca_nome_fornitore_formazione.click()
                self._pause_for_visual_check()
                box = self.wait.until(EC.presence_of_element_located((By.XPATH,
                                                                      "//input[contains(@id, ':lsVwCls:supplierNameId::_afrLovInternalQueryId:value00::content')]")))
                box.send_keys(supplier)
                self._pause_for_visual_check()
                search_btn = self.wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//button[text()='Cerca' and contains(@id, 'supplierNameId')]")))
                search_btn.click()
                self._pause_for_visual_check()

                try:
                    self.wait.until(EC.presence_of_element_located((By.XPATH,
                                                                    '//*[contains(@id, "lsVwCls:supplierNameId_afrLovInternalTableId::db")]//tr[.//text()[contains(., "Nessuna riga da visualizzare")]]')))
                    print(f"⚠️ The supplier '{supplier}' was not found.")
                except TimeoutException:
                    find_nome_fornitore_in_list = self.wait.until(EC.element_to_be_clickable((
                        By.XPATH,
                        f'//*[contains(@id, "lsVwCls:supplierNameId_afrLovInternalTableId::db")]//tr[.//text()[contains(., \"{supplier}\")]]'
                    )))
                    find_nome_fornitore_in_list.click()
                    self._pause_for_visual_check()

                ok_button_nome_fornitore = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//button[text()='OK' and contains(@id, 'supplierNameId')]")))
                ok_button_nome_fornitore.click()
                self._pause_for_visual_check()

            # add price: find price input
            if price:
                add_costo_di_edizione = self.wait.until(EC.presence_of_element_located(
                    (By.XPATH, "//input[contains(@id, ':lsVwCls:rPrc:0:srAtbl:_ATp:t1:0:it1::content')]")))
                add_costo_di_edizione.clear()
                add_costo_di_edizione.send_keys(price)
                self._pause_for_visual_check()

            # press save and close
            button_salva_e_chiudi_info_di_edizioni = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[text()='Salva e chiudi']")))
            button_salva_e_chiudi_info_di_edizioni.click()
            self._pause_for_visual_check()

            print(f"Model (EDITION): Saved edition for {course_name} - {edition_start_date.strftime('%d/%m/%Y')}")
            return f"✅🤩 Successo! Edizione per '{course_name}' creata: {edition_start_date.strftime('%d/%m/%Y')}"

        except Exception as e:
            print(f"Model (EDITION) Error: {e}")
            return f"‼️👩🏻‍✈️ Errore durante creazione edizione: {e}"

    def close_driver(self):
        print("Model: Closing driver.")
        self.driver.quit()