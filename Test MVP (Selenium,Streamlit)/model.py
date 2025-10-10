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
from selenium.common.exceptions import TimeoutException, NoSuchElementException


# This is a special function called the constructor.
# It automatically runs once when you first create a robot from the blueprint.
# Its job is to do all the initial setup.
class OracleAutomator:
    # This class encapsulates all the browser automation steps.
    def __init__(self, driver_path, debug_mode=False, debug_pause=1, headless=False):
        options = Options()
        # Allow switching between headless and visible mode
        if headless:
            # Required flags for Edge headless mode
            options.add_argument("--headless=new")  # modern flag
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--no-sandbox")
        else:
            # force a visible browser with defined size
            options.add_argument("--window-size=1920,1080")

        # selenium driver configuration
        service = Service(executable_path=driver_path)
        self.driver = webdriver.Edge(service=service, options=options)
        self.wait = WebDriverWait(self.driver, 40)

        # debug settings
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

    def navigate_to_courses_page(self):
        """
               Navigate from homepage to the 'Corsi' list page.
               Used by both course creation and edition flows.
               """

        try:
            miogruppodilavoro = self.wait.until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="groupNode_workforce_management"]')))
            miogruppodilavoro.click()
            apprendimento = self.wait.until(EC.presence_of_element_located((By.ID, 'WLF_FUSE_LEARN_ADMIN')))
            apprendimento.click()
            corsi = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//a[@title="Corsi" and text()="Corsi"]')))
            corsi.click()
            print("Model: Clicked through to Corsi page.")
            return {"ok": True}
        except Exception as e:
            print(f"Model: Error navigating to 'Corsi' page: {e}")
            return {"ok": False, "error": str(e)}

        # SEARCH: perform the search in the Corsi list and return:
        #    True  => course appears in result list
        #   False => "Nessun dato da visualizzare." (no results)
        #   None  => unexpected error occurred

    def search_course(self, course_name):
        try:
            # Ensure we are on the Corsi page (caller should typically call navigate_to_courses_page)
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
            print("Model: Searching for existing course.")
            self._pause_for_visual_check()  # <-- PAUSE HERE

            # quick check for the "no data" message using a short wait
            short_wait = WebDriverWait(self.driver, 4)
            try:
                short_wait.until(
                    EC.presence_of_element_located((By.XPATH, '//*[contains(text(),"Nessun dato da visualizzare.")]')))
                print("Model: Search result -> NO DATA (course not found).")
                return {"ok": True, "found": False}
            except TimeoutException:
                # no 'no data' message: try to detect the course link in the results
                try:
                    # use normalize-space to avoid whitespace mismatches
                    link_xpath = f'//table[@summary="Corsi"]//a[contains(normalize-space(.), "{course_name}")]'
                    self.wait.until(EC.presence_of_element_located((By.XPATH, link_xpath)))
                    print("Model: Course appears in search results.")
                    return True
                except TimeoutException:
                    print("Model: Course not found (no explicit 'no data' message and link missing).")
                    return {"ok": True, "found": False}
        except Exception as e:
            print(f"Model: Error during navigation : {e}")
            return {"ok": False, "error": str(e)}

    # Click (open) the course in the list (returns True if clicked)
    def open_course_from_list(self, course_name):
        # Click (open) the course in the list (returns True if clicked)
        try:
            link_xpath = f'//table[@summary="Corsi"]//a[contains(normalize-space(.), "{course_name}")]'
            link = self.wait.until(EC.element_to_be_clickable((By.XPATH, link_xpath)))
            link.click()
            self._pause_for_visual_check()
            print(f"Model: Clicked on existing course '{course_name}' in list.")
            return {"ok": True}
        except TimeoutException:
            print(f"Model: Could not find/click the course link for '{course_name}'.")
            return {"ok": False, "error": "course-link-missing"}
        except Exception as e:
            print(f"Model: Unexpected error in open_course_from_list: {e}")
            return {"ok": False, "error": str(e)}

    # CREATE COURSE flow (uses the search behaviour)
    def create_course(self, course_details):

        try:
            course_name = course_details['title']
            print(f"Model: Starting create_course for '{course_name}'")

            # Navigate to page
            nav = self.navigate_to_courses_page()
            if not nav["ok"]:
                return {"ok": False, "error": "navigation_failed", "message": nav.get("error")}

            search = self.search_course(course_name)
            if not search["ok"]:
                return {"ok": False, "error": "search_failed", "message": search.get("error")}
            if search["found"]:
                return {"ok": True, "created": False, "message": f"‼️ Il corso '{course_name}' esiste già."}
            # Not found -> create new
            crea_button = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, '//*[@id="pt1:_FOr1:1:_FONSr2:0:MAnt2:1:MgCrUpl:UPsp1:r2:0:srAtbl:_ATp:crtBtn"]/a/span')))
            crea_button.click()
            print("Model: Clicked 'Crea' button to start course creation.")
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
            publication_date_str = course_details['start_date'].strftime("%d/%m/%Y")
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

            return {"ok": True, "created": True, "message": f"✅ Successo! Il corso '{course_name}' è stato creato."}
        except Exception as e:
            print(f"Model: Error creating course: {e}")
            return {"ok": False, "error": "create_course_failed", "message": str(e)}

    # CREATE EDITION flow (assumes caller opened the course detail page)
    def create_edition(self, edition_details):
        """
        ADDED: CREATE EDITION METHOD
        edition_details keys:
          - course_name (str) : name of existing course
          - edition_start_date (date or str %d/%m/%Y)
          - duration_days (int)
          - location (str)
          - supplier (str)
          - price (str)
          - language (str)
          - moderator_type (str)
        """
        try:
            course_name = edition_details['course_name']
            # parse start date
            start = edition_details.get('edition_start_date')
            if isinstance(start, str):
                edition_start_date = datetime.strptime(start, "%d/%m/%Y")
            else:
                edition_start_date = start

            duration_days = int(edition_details.get('duration_days', 1))

            location = edition_details.get('location', "")
            supplier = edition_details.get('supplier', "")
            price = edition_details.get('price', "")
            language = edition_details.get('language', "")
            moderator_type = edition_details.get('moderator_type', "")

            print(
                f"Model (EDITION): Creating edition for {course_name} start {edition_start_date.strftime('%d/%m/%Y')}")
            self._pause_for_visual_check()

            # Assumes we are on course detail page; if not, try to click the course from list
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

            # description
            descirione_edizione = self.wait.until(
                EC.presence_of_element_located((By.XPATH, '//div[contains(@aria-label, "main") and @role="textbox"]')))
            descirione_edizione.send_keys(f"{course_name}-{edition_start_date.strftime('%d/%m/%Y')}-details")
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
            edition_end_date_obj = edition_start_date + timedelta(days=duration_days - 1)
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
                self._pause_for_visual_check()

                try:
                    self.wait.until(EC.presence_of_element_located((By.XPATH,
                                                                    f'//div[contains(@id, "primaryClassroomName1Id_afrLovInternalTableId::db")]//tr[.//text()[contains(., "Nessuna riga da visualizzare")]]')))
                    print(f"⚠️ The location '{location}' was not found.")
                except TimeoutException:
                    list_aula_option_row = self.wait.until(EC.element_to_be_clickable((By.XPATH,
                                                                                       f'//div[contains(@id, "primaryClassroomName1Id_afrLovInternalTableId::db")]//td[contains(@class, "xen") and .//span[text()="{location}"]]')))
                    list_aula_option_row.click()
                    self._pause_for_visual_check()

                ok_button = self.wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//button[text()='OK' and contains(@id, 'primaryClassroomName1Id')]")))
                ok_button.click()
                self._pause_for_visual_check()

            # language
            if language:
                choose_lingua = self.wait.until(
                    EC.presence_of_element_located((By.XPATH, "//a[contains(@id, ':lsVwCls:lngSel::drop')]")))
                choose_lingua.click()
                self._pause_for_visual_check()
                find_lingua = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, f'//*[contains(text(), \"{language}\")]')))
                find_lingua.click()
                self._pause_for_visual_check()

            # moderator type
            if moderator_type:
                choose_tipo_moderatore = self.wait.until(
                    EC.presence_of_element_located((By.XPATH, "//a[contains(@id, ':lsVwCls:socFaciType::drop')]")))
                choose_tipo_moderatore.click()
                self._pause_for_visual_check()
                find_tipo_moderatore = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, f'//*[contains(text(), \"{moderator_type}\")]')))
                find_tipo_moderatore.click()
                self._pause_for_visual_check()

            # supplier lookup & select
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
                    find_nome_fornitore_in_list = self.wait.until(EC.element_to_be_clickable((By.XPATH,
                                                                                              f'//*[contains(@id, "lsVwCls:supplierNameId_afrLovInternalTableId::db")]//tr[.//text()[contains(., \"{supplier}\")]]')))
                    find_nome_fornitore_in_list.click()
                    self._pause_for_visual_check()

                ok_button_nome_fornitore = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//button[text()='OK' and contains(@id, 'supplierNameId')]")))
                ok_button_nome_fornitore.click()
                self._pause_for_visual_check()

            # add price
            if price:
                add_costo_di_edizione = self.wait.until(EC.presence_of_element_located(
                    (By.XPATH, "//input[contains(@id, ':lsVwCls:rPrc:0:srAtbl:_ATp:t1:0:it1::content')]")))
                add_costo_di_edizione.clear()
                add_costo_di_edizione.send_keys(price)
                self._pause_for_visual_check()

            # save and close
            button_salva_e_chiudi_info_di_edizioni = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[text()='Salva e chiudi']")))
            button_salva_e_chiudi_info_di_edizioni.click()
            self._pause_for_visual_check()

            # confirm by waiting for edizioni tab (page navigated to details)
            button_aggiungi_attivita = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, "//div[contains(@id, ':actPce:iltBtn') and @title='Aggiungi']")))
            self.wait.until(EC.presence_of_element_located((By.XPATH, button_aggiungi_attivita)))

            return {"ok": True,
                    "message": f"✅ Edizione per '{course_name}' creata: {edition_start_date.strftime('%d/%m/%Y')}"}
        except Exception as e:
            print(f"Model (EDITION) Error: {e}")
            return {"ok": False, "error": "create_edition_failed", "message": str(e)}

    def close_driver(self):
        try:
            self.driver.quit()
        except Exception:
            pass