import time
import os
import sys
import tempfile
from datetime import timedelta, datetime, date
from dateutil.relativedelta import relativedelta
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.edge.options import Options
from selenium.common.exceptions import (TimeoutException,
    ElementClickInterceptedException, StaleElementReferenceException)

# === IMPORT ALL XPATHS FROM CONFIG ===
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import *




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

            # Wait for redirect to IDCS login page to complete
            time.sleep(3)

            # USERNAME - multiple fallbacks
            username_xpaths = [
                LOGIN_USERNAME_INPUT,
                LOGIN_USERNAME_FALLBACK_1,
                LOGIN_USERNAME_FALLBACK_2,
            ]
            username_field = None
            for xpath in username_xpaths:
                try:
                    username_field = self.wait.until(
                        EC.presence_of_element_located((By.XPATH, xpath)))
                    print(f"Found username field with: {xpath}")
                    break
                except:
                    continue
            if not username_field:
                raise Exception("Could not find username field")
            username_field.send_keys(username)

            # PASSWORD - multiple fallbacks
            password_xpaths = [
                LOGIN_PASSWORD_INPUT,
                LOGIN_PASSWORD_FALLBACK_1,
                LOGIN_PASSWORD_FALLBACK_2,
            ]
            password_field = None
            for xpath in password_xpaths:
                try:
                    password_field = self.wait.until(
                        EC.presence_of_element_located((By.XPATH, xpath)))
                    print(f"Found password field with: {xpath}")
                    break
                except:
                    continue
            if not password_field:
                raise Exception("Could not find password field")
            password_field.send_keys(password)

            # NEXT BUTTON - multiple fallbacks
            button_xpaths = [
                LOGIN_SUBMIT_BUTTON,
                LOGIN_SUBMIT_FALLBACK_1,
                LOGIN_SUBMIT_FALLBACK_2,
                LOGIN_SUBMIT_FALLBACK_3,
            ]
            sign_in_button = None
            for xpath in button_xpaths:
                try:
                    sign_in_button = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, xpath)))
                    print(f"Found sign in button with: {xpath}")
                    break
                except:
                    continue
            if not sign_in_button:
                raise Exception("Could not find Next/Sign In button")
            sign_in_button.click()

            print("Model: Logged in successfully.")
            return True

        except Exception as e:
            print(f"Model: Error during login: {e}")
            return False

    def navigate_to_courses_page(self):
        try:
            # Click new homepage button if present
            try:
                new_home_btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, NAV_NEW_HOMEPAGE_BUTTON)))
                new_home_btn.click()
                print("Model: Clicked new homepage button")
                time.sleep(2)
            except:
                pass  # Button not present, continue normally

            self.wait.until(EC.presence_of_element_located(
                (By.XPATH, NAV_WORKFORCE_MENU))).click()
            self.wait.until(EC.presence_of_element_located(
                (By.ID, NAV_LEARN_ADMIN))).click()
            self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, NAV_CORSI_LINK))).click()

            #Wait for courses page to fully load
            print("Model: Waiting for Corsi page to load...")
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located(
                    (By.NAME, COURSE_SEARCH_NAME_INPUT)))
            print("Model: Navigated to 'Corsi' page.")
            return True
        except Exception as e:
            print(f"Model: Error navigating to 'Corsi' page: {e}")
            return False

    def navigate_to_edition_page(self):
        try:
            # Click new homepage button if present
            try:
                new_home_btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, NAV_NEW_HOMEPAGE_BUTTON)))
                new_home_btn.click()
                print("Model: Clicked new homepage button")
                time.sleep(2)
            except:
                pass  # Button not present, continue normally

            self.wait.until(EC.presence_of_element_located(
                (By.XPATH, NAV_WORKFORCE_MENU))).click()
            self.wait.until(EC.presence_of_element_located(
                (By.ID, NAV_LEARN_ADMIN))).click()
            self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, NAV_EDIZIONI_LINK))).click()
            print("Model: Navigated to 'Edizioni' page.")
            return True
        except Exception as e:
            print(f"Model: Error navigating to 'Edizioni' page: {e}")
            return False

    def search_course(self, course_name):
        """
        Search for a course by name.
        Returns True if course exists, False if not.
        """
        try:
            cleaned_course_name = course_name.strip()
            capitalised_course_name = cleaned_course_name.title()

            # Wait for page to fully stabilize
            time.sleep(3)
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.invisibility_of_element_located(
                        (By.CLASS_NAME, "AFBlockingGlassPane")))
            except:
                pass

            # Fill search name
            search_box_locator = (By.NAME, COURSE_SEARCH_NAME_INPUT)
            search_box = self.wait.until(EC.element_to_be_clickable(search_box_locator))
            search_box.clear()
            search_box.send_keys(capitalised_course_name)
            self._pause_for_visual_check()

            # Fill search date filter
            date_input = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, COURSE_SEARCH_DATE_INPUT)))
            date_input.clear()
            date_input.send_keys("01/01/2000")
            self._pause_for_visual_check()
            time.sleep(3)

            # Click search button
            search_button = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, COURSE_SEARCH_BUTTON)))
            search_button.click()
            print(f"Clicked Search button for course: '{capitalised_course_name}'")

            result_container_xpath = COURSE_TABLE_SUMMARY

            # Wait for Oracle to process the search (blocking overlay)
            time.sleep(2)
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.invisibility_of_element_located(
                        (By.CLASS_NAME, "AFBlockingGlassPane")))
            except:
                pass
            time.sleep(1)


            try:
                # Wait for result container to be present
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located(
                        (By.XPATH, COURSE_TABLE_SUMMARY)))
            except:
                print("   ⚠️ Could not find result container")

            # Check for "no data" message
            short_wait = WebDriverWait(self.driver, 5)
            try:
                short_wait.until(EC.presence_of_element_located(
                    (By.XPATH, COURSE_NO_DATA_MESSAGE)))
                print(f"Search result: Course '{course_name}' NOT found")
                return False
            except TimeoutException:
                pass

            # Look for the course name as a link inside the result container
            course_name_lower = cleaned_course_name.lower()
            course_link_xpath = (
                f'{result_container_xpath}//a'
                f'[translate(normalize-space(.), "ABCDEFGHIJKLMNOPQRSTUVWXYZ",'
                f' "abcdefghijklmnopqrstuvwxyz")="{course_name_lower}"]'
            )
            try:
                short_wait.until(EC.presence_of_element_located(
                    (By.XPATH, course_link_xpath)))
                print(f"Search result: Course '{course_name}' FOUND")
                return True
            except TimeoutException:
                # Fallback: check if any link in the container contains the name
                fallback_xpath = (
                    f'{result_container_xpath}//a'
                    f'[contains(translate(normalize-space(.), "ABCDEFGHIJKLMNOPQRSTUVWXYZ",'
                    f' "abcdefghijklmnopqrstuvwxyz"), "{course_name_lower}")]'
                )
                try:
                    short_wait.until(EC.presence_of_element_located(
                        (By.XPATH, fallback_xpath)))
                    print(f"Search result: Course '{course_name}' FOUND (partial match)")
                    return True
                except TimeoutException:
                    print(f"Search result: Course '{course_name}' NOT found")
                    return False
        except Exception as e:
            print(f"Error during course search: {e}")
            return False

    def open_course_from_list(self, course_name):
        try:
            result_container_xpath = COURSE_TABLE_SUMMARY
            course_name_lower = course_name.lower()

            # Exact match first
            course_link_xpath = (
                f'{result_container_xpath}//a'
                f'[translate(normalize-space(.), "ABCDEFGHIJKLMNOPQRSTUVWXYZ",'
                f' "abcdefghijklmnopqrstuvwxyz")="{course_name_lower}"]'
            )

            try:
                link = self.wait.until(EC.element_to_be_clickable(
                    (By.XPATH, course_link_xpath)))
            except:
                # Fallback: partial match
                course_link_xpath = (
                    f'{result_container_xpath}//a'
                    f'[contains(translate(normalize-space(.), "ABCDEFGHIJKLMNOPQRSTUVWXYZ",'
                    f' "abcdefghijklmnopqrstuvwxyz"), "{course_name_lower}")]'
                )
                link = self.wait.until(EC.element_to_be_clickable(
                    (By.XPATH, course_link_xpath)))

            link.click()
            self._pause_for_visual_check()
            print(f"Model: Clicked on course '{course_name}' in list.")

            self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, COURSE_DETAIL_EDIZIONI_TAB)))
            print(f"Model: Course details page loaded.")
            return True

        except Exception as e:
            print(f"Model: Could not open course '{course_name}'. Error: {e}")
            return False

    def create_course(self, course_details):
        """
        Create a SINGLE course in Oracle.
        Assumes already on the Corsi page.
        """
        try:
            course_name = course_details['title'].title()
            print(f"Creating course: '{course_name}'")

            time.sleep(1)

            # Wait for blocking overlay to disappear
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.invisibility_of_element_located((By.CLASS_NAME, "AFBlockingGlassPane")))
            except:
                pass

            # Click Create button with fallbacks
            crea_button_xpaths = [
                COURSE_CREATE_BUTTON_EN,
                COURSE_CREATE_BUTTON_IT,
                COURSE_CREATE_BUTTON_ID,
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

            # Fill course title
            title_field = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, COURSE_TITLE_INPUT)))
            title_field.send_keys(course_details['title'])
            title_field.send_keys(Keys.TAB)
            self._pause_for_visual_check()

            # Fill programme (optional)
            programma_field = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, COURSE_PROGRAMME_INPUT)))
            programma_field.send_keys(course_details.get('programme', ''))
            programma_field.send_keys(Keys.TAB)
            self._pause_for_visual_check()

            # Fill short description
            desc_breve = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, COURSE_SHORT_DESC_INPUT)))
            desc_breve.send_keys(course_details.get('short_description', ''))
            desc_breve.send_keys(Keys.TAB)
            self._pause_for_visual_check()

            # Fill publication date
            data_inizio_pubblic = self.wait.until(EC.visibility_of_element_located(
                (By.XPATH, COURSE_DATE_INPUT)))
            data_inizio_pubblic.clear()
            publication_date_str = course_details['start_date'].strftime("%d/%m/%Y")
            print(f"Setting publication date for '{course_name}': {publication_date_str}")
            data_inizio_pubblic.send_keys(publication_date_str)
            data_inizio_pubblic.send_keys(Keys.TAB)
            self._pause_for_visual_check()

            # Save and close
            salve_chiude = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, COURSE_SAVE_CLOSE_BUTTON)))
            salve_chiude.click()
            print(f"Clicked 'Salva e Chiudi' for '{course_name}'")
            self._pause_for_visual_check()

            # Wait for confirmation (Edizioni tab appears)
            self.wait.until(EC.presence_of_element_located(
                (By.XPATH, COURSE_DETAIL_EDIZIONI_TAB)))
            print(f"✅ Course '{course_name}' created successfully!")

            # Click back button to return to Corsi list
            if not self._click_back_button():
                print("Warning: Could not click back button, but course was created")

            return f"✅🤩 Successo! Il corso '{course_name}' è stato creato."

        except Exception as e:
            error_msg = (f"‼️👩🏻‍✈️ Errore durante la creazione del corso "
                         f"'{course_details.get('title', 'UNKNOWN')}': {str(e)}")
            print(error_msg)
            return error_msg

    def _click_back_button(self):
        """Click the 'Indietro' (Back) button to return to the Corsi list."""
        try:
            back_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, BACK_FROM_COURSE_DETAIL)))
            back_button.click()
            print("Clicked 'Indietro' button")
            WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable(
                    (By.XPATH, f"{COURSE_CREATE_BUTTON_EN} | {COURSE_CREATE_BUTTON_IT}")))
            print("Back on Corsi list")
            return True
        except Exception as e:
            print(f"Error clicking back button: {e}")
            return False

    def _click_back_to_edition_search(self):
        """
        Click the 'Indietro' (Back) button to return from edition detail page
        to the edition search page.
        """
        try:
            print("Model: Clicking 'Indietro' to return to edition search...")

            back_button_xpaths = [
                EDITION_BACK_BTN_TO_SEARCH_1,
                EDITION_BACK_BTN_TO_SEARCH_2,
                EDITION_BACK_BTN_TO_SEARCH_3,
            ]

            back_button = None
            for xpath in back_button_xpaths:
                try:
                    back_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, xpath)))
                    print(f"   Found back button with: {xpath}")
                    break
                except:
                    continue

            if not back_button:
                raise Exception("Could not find 'Indietro' back button")

            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", back_button)
            time.sleep(0.5)

            try:
                back_button.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", back_button)
            time.sleep(3)

            # Clear previous search input
            try:
                search_input = self.driver.find_element(
                    By.XPATH, EDITION_SEARCH_NUMBER_INPUT_1)
                search_input.clear()
                print("   ✅ Cleared previous search input")
            except:
                pass
            print("   ✅ Clicked 'Indietro' back button")

            # Wait for edition search page to load
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.element_to_be_clickable((By.XPATH, EDITION_SEARCH_SUBMIT_BTN)))
                print("   ✅ Back on edition search page")
            except:
                print("   ⚠️ Could not confirm edition search page loaded, waiting...")
                time.sleep(3)

            self._pause_for_visual_check()
            return True

        except Exception as e:
            print(f"   ❌ Error clicking back button: {e}")
            return False

    def _create_single_activity(self, unique_title, full_description, activity_date_obj,
                                start_time_str, end_time_str, impegno_previsto_in_ore):
        """Create a single activity in Oracle."""
        try:
            activity_date_str = activity_date_obj.strftime('%d/%m/%Y')
            print(f"  Preparing to create activity '{unique_title}' on {activity_date_str}...")

            # Wait for blocking overlay
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.invisibility_of_element_located((By.CLASS_NAME, "AFBlockingGlassPane")))
            except:
                pass
            time.sleep(2)

            # Click Aggiungi button with retry
            print(f"  Looking for 'Aggiungi' button...")
            aggiungi_xpaths = [
                ACTIVITY_ADD_BUTTON_1,
                ACTIVITY_ADD_BUTTON_2,
                ACTIVITY_ADD_BUTTON_3,
            ]

            button_aggiungi_attivita = None
            max_retries = 3

            for attempt in range(max_retries):
                for xpath in aggiungi_xpaths:
                    try:
                        WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, xpath)))
                        button_aggiungi_attivita = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, xpath)))
                        print(f"  Found 'Aggiungi' button with: {xpath}")
                        break
                    except:
                        continue

                if button_aggiungi_attivita:
                    break
                else:
                    print(f"  Retry {attempt + 1}/{max_retries}: 'Aggiungi' button not found, waiting...")
                    time.sleep(2)

            if not button_aggiungi_attivita:
                raise Exception("Could not find 'Aggiungi' button after multiple attempts")

            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", button_aggiungi_attivita)
            time.sleep(0.5)

            try:
                button_aggiungi_attivita.click()
            except Exception as click_error:
                print(f"  Normal click failed, trying JavaScript click: {click_error}")
                self.driver.execute_script("arguments[0].click();", button_aggiungi_attivita)

            print(f"Clicked 'Aggiungi' button for activity on {activity_date_str}")
            time.sleep(2)
            self._pause_for_visual_check()

            # 1. TITOLO
            print("  [1/7] Filling Titolo...")
            try:
                box_attivita_titolo = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, ACTIVITY_TITLE_INPUT)))
                box_attivita_titolo.clear()
                box_attivita_titolo.send_keys(unique_title)
                print(f"       ✓ Entered title: {unique_title}")
            except Exception as e:
                print(f"       ✗ FAILED on Titolo: {e}")
                raise

            # 2. DESCRIZIONE PER ELENCO
            print("  [2/7] Filling Descrizione per elenco...")
            try:
                desc_per_elenco_attivita = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, ACTIVITY_DESC_ELENCO_INPUT)))
                desc_per_elenco_attivita.clear()
                desc_per_elenco_attivita.send_keys(f"{unique_title}-{activity_date_str}")
                print(f"       ✓ Entered desc per elenco: {unique_title}-{activity_date_str}")
            except Exception as e:
                print(f"       ✗ FAILED on Descrizione per elenco: {e}")
                raise

            # 3. DESCRIZIONE DETTAGLIATA (CKEditor)
            print("  [3/7] Filling Descrizione dettagliata (CKEditor)...")
            try:
                ckeditor_xpaths = [
                    ACTIVITY_DESC_DETAIL_CK_1,
                    ACTIVITY_DESC_DETAIL_CK_2,
                    ACTIVITY_DESC_DETAIL_CK_3,
                ]
                desc_dettagliata = None
                for xpath in ckeditor_xpaths:
                    try:
                        desc_dettagliata = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, xpath)))
                        print(f"       Found CKEditor with: {xpath}")
                        break
                    except:
                        continue

                if desc_dettagliata:
                    desc_dettagliata.click()
                    time.sleep(0.3)
                    description_text = (full_description if full_description
                                        else f"Attività: {unique_title}")
                    self.driver.execute_script(
                        "arguments[0].innerHTML = '<p>' + arguments[1] + '</p>';",
                        desc_dettagliata, description_text)
                    desc_dettagliata.send_keys(" ")
                    print(f"       ✓ Entered detailed description")
                else:
                    print("       ⚠ WARNING: Could not find CKEditor, skipping")
            except Exception as e:
                print(f"       ⚠ WARNING on Descrizione dettagliata (continuing): {e}")

            # 4. DATA ATTIVITÀ
            print("  [4/7] Filling Data attività...")
            try:
                data_attivita = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, ACTIVITY_DATE_INPUT)))
                data_attivita.clear()
                self.driver.execute_script(
                    "arguments[0].value = arguments[1];", data_attivita, activity_date_str)
                data_attivita.send_keys(Keys.TAB)
                print(f"       ✓ Entered date: {activity_date_str}")
            except Exception as e:
                print(f"       ✗ FAILED on Data attività: {e}")
                raise

            # 5. ORA INIZIO
            print("  [5/7] Filling Ora inizio...")
            try:
                ora_inizio_attivita = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, ACTIVITY_START_TIME_INPUT)))
                ora_inizio_attivita.clear()
                ora_inizio_attivita.send_keys(start_time_str)
                print(f"       ✓ Entered start time: {start_time_str}")
            except Exception as e:
                print(f"       ✗ FAILED on Ora inizio: {e}")
                raise

            # 6. ORA FINE
            print("  [6/7] Filling Ora fine...")
            try:
                ora_fine_attivita = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, ACTIVITY_END_TIME_INPUT)))
                ora_fine_attivita.clear()
                ora_fine_attivita.send_keys(end_time_str)
                print(f"       ✓ Entered end time: {end_time_str}")
            except Exception as e:
                print(f"       ✗ FAILED on Ora fine: {e}")
                raise

            # 7. IMPEGNO PREVISTO IN ORE (optional)
            print("  [7/7] Filling Impegno previsto in ore...")
            if impegno_previsto_in_ore:
                try:
                    impeg_pre_in_ore = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, ACTIVITY_HOURS_INPUT)))
                    impeg_pre_in_ore.clear()
                    impeg_pre_in_ore.send_keys(str(impegno_previsto_in_ore))
                    print(f"       ✓ Entered impegno: {impegno_previsto_in_ore}")
                except Exception as e:
                    print(f"       ⚠ WARNING on Impegno (optional field): {e}")
            else:
                print("       - Skipped (no value provided)")

            self._pause_for_visual_check()

            # 8. CLICK OK BUTTON
            print("  [OK] Clicking OK button...")
            try:
                ok_button_xpaths = [
                    ACTIVITY_OK_BUTTON_1,
                    ACTIVITY_OK_BUTTON_2,
                    ACTIVITY_OK_BUTTON_3,
                ]
                ok_button = None
                for xpath in ok_button_xpaths:
                    try:
                        ok_button = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.XPATH, xpath)))
                        print(f"       Found OK button with: {xpath}")
                        break
                    except:
                        continue

                if not ok_button:
                    print("       Trying to find any visible OK button...")
                    ok_elements = self.driver.find_elements(
                        By.XPATH, '//span[text()="OK"]/parent::a')
                    for elem in ok_elements:
                        if elem.is_displayed():
                            ok_button = elem
                            print(f"       Found visible OK button")
                            break

                if not ok_button:
                    raise Exception("Could not find OK button with any strategy")

                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});", ok_button)
                time.sleep(0.5)

                click_success = False
                try:
                    ok_button.click()
                    click_success = True
                    print(f"       ✓ Clicked OK button (normal click)")
                except Exception as e1:
                    print(f"       Normal click failed: {e1}")

                if not click_success:
                    try:
                        self.driver.execute_script("arguments[0].click();", ok_button)
                        click_success = True
                        print(f"       ✓ Clicked OK button (JavaScript click)")
                    except Exception as e2:
                        print(f"       JavaScript click failed: {e2}")

                if not click_success:
                    try:
                        from selenium.webdriver.common.action_chains import ActionChains
                        actions = ActionChains(self.driver)
                        actions.move_to_element(ok_button).click().perform()
                        click_success = True
                        print(f"       ✓ Clicked OK button (ActionChains)")
                    except Exception as e3:
                        print(f"       ActionChains click failed: {e3}")

                if not click_success:
                    raise Exception("All click strategies failed for OK button")

                # Wait for popup to close
                print("       Waiting for popup to close...")
                popup_closed = False

                try:
                    WebDriverWait(self.driver, 15).until(
                        EC.invisibility_of_element_located(
                            (By.XPATH, '//h1[contains(text(), "Aggiungi attività")]')))
                    popup_closed = True
                    print("       - Popup title disappeared")
                except:
                    pass

                if not popup_closed:
                    try:
                        WebDriverWait(self.driver, 10).until(
                            EC.invisibility_of_element_located(
                                (By.XPATH, ACTIVITY_TITLE_INPUT)))
                        popup_closed = True
                        print("       - Titolo field disappeared")
                    except:
                        pass

                try:
                    WebDriverWait(self.driver, 5).until(
                        EC.invisibility_of_element_located(
                            (By.CLASS_NAME, "AFBlockingGlassPane")))
                    print("       - Blocking pane gone")
                except:
                    pass

                if not popup_closed:
                    try:
                        WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located(
                                (By.XPATH, ACTIVITY_ADD_BUTTON_1)))
                        popup_closed = True
                        print("       - 'Aggiungi' button visible again")
                    except:
                        pass

                if not popup_closed:
                    print("       - Using fallback wait (5 seconds)")
                    time.sleep(5)
                else:
                    time.sleep(2)

                self._pause_for_visual_check()
                print(f"  ✅ Activity '{unique_title}' on {activity_date_str} created successfully!")
                return True

            except Exception as e:
                print(f"       ✗ FAILED during OK/close: {e}")
                raise

        except Exception as e:
            print(f"\n❌ ERROR creating activity '{unique_title}' on {activity_date_str}")
            print(f"   Exception type: {type(e).__name__}")
            print(f"   Exception message: {str(e)}")

            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_title = unique_title.replace(' ', '_')[:20]
                ss_path = f"error_activity_{safe_title}_{timestamp}.png"
                self.driver.save_screenshot(ss_path)
                print(f"   Screenshot saved: {ss_path}")
            except:
                pass

            # Try to click Cancel/Annulla
            try:
                cancel_xpaths = [ACTIVITY_CANCEL_BTN_1, ACTIVITY_CANCEL_BTN_2]
                for cancel_xpath in cancel_xpaths:
                    try:
                        cancel_button = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.XPATH, cancel_xpath)))
                        cancel_button.click()
                        print("   Clicked Cancel button.")
                        time.sleep(1)
                        break
                    except:
                        continue
            except:
                pass

            return False

    def _fill_edition_location(self, location):
        """Helper: fill the Aula/Location field in edition form."""
        if not location:
            return

        select_aula = self.wait.until(EC.element_to_be_clickable(
            (By.XPATH, EDITION_AULA_LOV_ICON)))
        select_aula.click()
        self._pause_for_visual_check()

        cerca_aula_xpaths = [
            EDITION_AULA_SEARCH_LINK_1,
            EDITION_AULA_SEARCH_LINK_2,
            EDITION_AULA_SEARCH_LINK_3,
        ]
        cerca_aula_button = None
        for xpath in cerca_aula_xpaths:
            try:
                cerca_aula_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, xpath)))
                print(f"   Found 'Cerca/Search' button with: {xpath}")
                break
            except:
                continue

        if not cerca_aula_button:
            print(f"   ⚠️ Could not find 'Cerca/Search' button, skipping location")
            return

        cerca_aula_button.click()
        self._pause_for_visual_check()

        box_cerca_aula = self.wait.until(EC.presence_of_element_located(
            (By.XPATH, EDITION_AULA_KEYWORD_INPUT)))
        box_cerca_aula.send_keys(location)
        self._pause_for_visual_check()

        search_button_xpaths = [
            EDITION_AULA_SEARCH_BTN_1,
            EDITION_AULA_SEARCH_BTN_2,
            EDITION_AULA_SEARCH_BTN_3,
        ]
        search_button = None
        for xpath in search_button_xpaths:
            try:
                search_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, xpath)))
                print(f"   Found Aula search button with: {xpath}")
                break
            except:
                continue

        if not search_button:
            raise Exception("Could not find Search/Cerca button in Aula popup")

        search_button.click()
        print("   Clicked Aula search button")

        self.wait.until(EC.presence_of_element_located(
            (By.XPATH, EDITION_AULA_RESULTS_TABLE)))

        # Wait for results to load
        time.sleep(2)
        try:
            WebDriverWait(self.driver, 5).until(
                EC.invisibility_of_element_located(
                    (By.CLASS_NAME, "AFBlockingGlassPane")))
        except:
            pass

        location_lower = location.lower()

        # Check for "no results" first
        try:
            WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located((By.XPATH,
                                                '//*[contains(text(), "Nessuna riga") or '
                                                'contains(text(), "Nessun dato")]')))
            print(f"⚠️ Location '{location}' not found in popup.")
            # Click Annulla to close popup gracefully
            try:
                annulla = self.driver.find_element(
                    By.XPATH, "//button[text()='Annulla' or text()='Cancel']")
                annulla.click()
            except:
                pass
            return
        except TimeoutException:
            pass

        # Try multiple strategies to click the matching row
        found = False

        # Strategy 1: exact match on td text (direct text, no span required)
        for xpath in [
            # Exact match anywhere in the row's text
            f'{EDITION_AULA_RESULTS_TABLE}//tr[.//td['
            f'translate(normalize-space(.), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", '
            f'"abcdefghijklmnopqrstuvwxyz")="{location_lower}"]]',
            # Contains match (more lenient)
            f'{EDITION_AULA_RESULTS_TABLE}//tr[.//td['
            f'contains(translate(normalize-space(.), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", '
            f'"abcdefghijklmnopqrstuvwxyz"), "{location_lower}")]]',
        ]:
            try:
                row = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, xpath)))
                row.click()
                print(f"   ✅ Selected location: {location}")
                found = True
                break
            except:
                continue

        if not found:
            print(f"   ⚠️ Could not click row for '{location}', proceeding anyway")

        self._pause_for_visual_check()

        ok_button = self.wait.until(EC.element_to_be_clickable(
            (By.XPATH, EDITION_AULA_OK_BUTTON)))
        ok_button.click()
        print("Confirmed the selected course location")
        self._pause_for_visual_check()

    def _fill_edition_supplier(self, supplier):
        """Helper: fill the Supplier/Fornitore field in edition form."""
        if not supplier:
            return

        print(f"   Setting supplier: {supplier}")
        choose_tipo_moderatore = self.wait.until(EC.element_to_be_clickable(
            (By.XPATH, EDITION_MODERATOR_DROPDOWN)))
        choose_tipo_moderatore.click()
        find_tipo_moderatore = self.wait.until(EC.element_to_be_clickable(
            (By.XPATH, f'//li[text()="{EDITION_MODERATOR_TYPE}"]')))
        find_tipo_moderatore.click()

        self.wait.until(EC.element_to_be_clickable(
            (By.XPATH, EDITION_SUPPLIER_LOV_ICON))).click()

        supplier_cerca_link_xpaths = [
            EDITION_SUPPLIER_SEARCH_LINK_1,
            EDITION_SUPPLIER_SEARCH_LINK_2,
            EDITION_SUPPLIER_SEARCH_LINK_3,
        ]
        supplier_cerca_link = None
        for xpath in supplier_cerca_link_xpaths:
            try:
                supplier_cerca_link = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, xpath)))
                print(f"   Found supplier 'Cerca/Search' link with: {xpath}")
                break
            except:
                continue

        if supplier_cerca_link:
            supplier_cerca_link.click()
            self._pause_for_visual_check()

            box = self.wait.until(EC.visibility_of_element_located(
                (By.XPATH, EDITION_SUPPLIER_INPUT)))
            box.send_keys(supplier)

            supplier_search_xpaths = [
                EDITION_SUPPLIER_SEARCH_BTN_1,
                EDITION_SUPPLIER_SEARCH_BTN_2,
                EDITION_SUPPLIER_SEARCH_BTN_3,
            ]
            supplier_search_btn = None
            for xpath in supplier_search_xpaths:
                try:
                    supplier_search_btn = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, xpath)))
                    print(f"   Found supplier search button with: {xpath}")
                    break
                except:
                    continue

            if supplier_search_btn:
                supplier_search_btn.click()
                print("   Clicked supplier search button")

                try:
                    supplier_row_xpath = (
                        f'//div[contains(@id, "supplierNameId_afrLovInternalTableId::db")]'
                        f'//tr[contains(translate(., "ABCDEFGHIJKLMNOPQRSTUVWXYZ",'
                        f' "abcdefghijklmnopqrstuvwxyz"), "{supplier.lower()}")]'
                    )
                    find_nome_fornitore = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, supplier_row_xpath)))
                    find_nome_fornitore.click()

                    ok_button_xpaths = [
                        EDITION_SUPPLIER_OK_BTN_1,
                        EDITION_SUPPLIER_OK_BTN_2,
                    ]
                    for xpath in ok_button_xpaths:
                        try:
                            ok_btn = WebDriverWait(self.driver, 5).until(
                                EC.element_to_be_clickable((By.XPATH, xpath)))
                            ok_btn.click()
                            print(f"   ✅ Supplier set: {supplier}")
                            break
                        except:
                            continue
                    self._pause_for_visual_check()

                except TimeoutException:
                    print(f"   ⚠️ Supplier '{supplier}' not found in results")
            else:
                print(f"   ⚠️ Could not find supplier Search button")
        else:
            print(f"   ⚠️ Could not find supplier Cerca/Search link")

    def _fill_edition_price(self, price):
        """Helper: fill the Price field in edition form."""
        if not price:
            return

        flag_prezzi = self.wait.until(EC.presence_of_element_located(
            (By.XPATH, EDITION_PRICE_FLAG_LABEL)))
        flag_prezzi.click()
        print("Flagged button 'Override determinazione prezzi'")
        self._pause_for_visual_check()

        aggiungi_voce = self.wait.until(EC.presence_of_element_located(
            (By.XPATH, EDITION_PRICE_ADD_LINE_BTN)))
        aggiungi_voce.click()
        print("Clicked on button 'Aggiungi voce linea'")
        self._pause_for_visual_check()

        dropdown_voce = self.wait.until(EC.presence_of_element_located(
            (By.XPATH, EDITION_PRICE_LINE_DROPDOWN)))
        dropdown_voce.click()
        self._pause_for_visual_check()

        prezzo_listino = self.wait.until(EC.presence_of_element_located(
            (By.XPATH, EDITION_PRICE_LISTINO_OPTION)))
        prezzo_listino.click()
        self._pause_for_visual_check()

        costo = self.wait.until(EC.presence_of_element_located(
            (By.XPATH, EDITION_PRICE_COST_INPUT)))
        costo.send_keys(str(price))
        print(f"   ✅ Price set: {price}")

    def _fill_edition_language(self):
        """Helper: fill the Language field in edition form."""
        self.wait.until(EC.presence_of_element_located(
            (By.XPATH, EDITION_LANGUAGE_DROPDOWN)))
        choose_lingua = self.wait.until(EC.presence_of_element_located(
            (By.XPATH, EDITION_LANGUAGE_DROPDOWN)))
        choose_lingua.click()
        self._pause_for_visual_check()
        find_lingua = self.wait.until(EC.element_to_be_clickable(
            (By.XPATH, f'//*[contains(text(), "{EDITION_LANGUAGE_DEFAULT}")]')))
        find_lingua.click()
        print(f"Confirmed the selected language: {EDITION_LANGUAGE_DEFAULT}")
        self._pause_for_visual_check()

    def _fill_edition_attributi_aggiuntivi(self, centro_costo, direzione_pagante,
                                           finanziata, servizio_pagante,
                                           sottotipologia, societa_pagante):
        """Helper: fill the Attributi Aggiuntivi fields after price section."""

        # --- Centro di Costo ---
        if centro_costo:
            try:
                field = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located(
                        (By.XPATH, EDITION_CENTRO_COSTO_INPUT)))
                field.clear()
                field.send_keys(centro_costo)
                print(f"   ✅ Centro di Costo: {centro_costo}")
            except Exception as e:
                print(f"   ⚠️ Could not fill Centro di Costo: {e}")

        # --- Direzione Pagante ---
        if direzione_pagante:
            try:
                field = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located(
                        (By.XPATH, EDITION_DIREZIONE_PAG_INPUT)))
                field.clear()
                field.send_keys(direzione_pagante)
                print(f"   ✅ Direzione Pagante: {direzione_pagante}")
            except Exception as e:
                print(f"   ⚠️ Could not fill Direzione Pagante: {e}")

        # --- Finanziata (dropdown: Sì / No) ---
        if finanziata:
            try:
                # Click the LOV icon to open dropdown
                lov_icon = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, EDITION_FINANZIATA_LOV)))
                lov_icon.click()
                self._pause_for_visual_check()

                # Select Sì or No
                finanziata_clean = finanziata.strip().lower()
                if finanziata_clean in ['si', 'sì', 'yes', 's']:
                    option_xpath = EDITION_FINANZIATA_SI
                else:
                    option_xpath = EDITION_FINANZIATA_NO

                option = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, option_xpath)))
                option.click()
                print(f"   ✅ Finanziata: {finanziata}")
                self._pause_for_visual_check()
            except Exception as e:
                print(f"   ⚠️ Could not fill Finanziata: {e}")

        # --- Servizio Pagante ---
        if servizio_pagante:
            try:
                field = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located(
                        (By.XPATH, EDITION_SERVIZIO_PAG_INPUT)))
                field.clear()
                field.send_keys(servizio_pagante)
                print(f"   ✅ Servizio Pagante: {servizio_pagante}")
            except Exception as e:
                print(f"   ⚠️ Could not fill Servizio Pagante: {e}")

        # --- Sottotipologia ---
        if sottotipologia:
            try:
                field = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located(
                        (By.XPATH, EDITION_SOTTOTIPOLOGIA_INPUT)))
                field.clear()
                field.send_keys(sottotipologia)
                print(f"   ✅ Sottotipologia: {sottotipologia}")
            except Exception as e:
                print(f"   ⚠️ Could not fill Sottotipologia: {e}")

        # --- Società Pagante ---
        if societa_pagante:
            try:
                field = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located(
                        (By.XPATH, EDITION_SOCIETA_PAG_INPUT)))
                field.clear()
                field.send_keys(societa_pagante)
                print(f"   ✅ Società Pagante: {societa_pagante}")
            except Exception as e:
                print(f"   ⚠️ Could not fill Società Pagante: {e}")

    def create_edition_and_activities(self, edition_details):
        """
        Create edition and its activities.
        edition_details keys:
          - course_name, edition_title, edition_start_date, edition_end_date,
            location, supplier, price, description, activities
        """
        try:
            course_name = edition_details['course_name'].title()
            edition_title_optional = edition_details.get('edition_title', '')
            edition_start_date = edition_details.get('edition_start_date')
            edition_end_date_obj = edition_details.get('edition_end_date')
            location = edition_details.get('location', "")
            supplier = edition_details.get('supplier', "")
            price = edition_details.get('price', "")
            description = edition_details.get('description', "")
            centro_costo = edition_details.get('centro_costo', '')
            direzione_pagante = edition_details.get('direzione_pagante', '')
            finanziata = edition_details.get('finanziata', '')
            servizio_pagante = edition_details.get('servizio_pagante', '')
            sottotipologia = edition_details.get('sottotipologia', '')
            societa_pagante = edition_details.get('societa_pagante', '')
            activities = edition_details.get('activities', [])

            print(f"Model (EDITION): Creating edition for {course_name} "
                  f"start {edition_start_date.strftime('%d/%m/%Y')}")
            self._pause_for_visual_check()

            # Click Edizioni tab
            edizioni_tab = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, COURSE_DETAIL_EDIZIONI_TAB)))
            edizioni_tab.click()

            # Click Crea -> Edizione guidata da docente
            self.wait.until(EC.presence_of_element_located(
                (By.XPATH, EDITION_CREA_BUTTON))).click()
            self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, EDITION_GUIDATA_OPTION))).click()
            self._pause_for_visual_check()

            # Edition title
            titolo_edizione_field = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, EDITION_TITLE_INPUT)))
            if edition_title_optional and edition_title_optional.strip():
                print(f"Using custom edition title: {edition_title_optional}")
                titolo_edizione_field.clear()
                titolo_edizione_field.send_keys(edition_title_optional)
            else:
                print("Using default edition title logic (course name + date)")
                titolo_edizione_field.send_keys(
                    "-" + edition_start_date.strftime("%d/%m/%Y"))
            self._pause_for_visual_check()

            # Description
            if description:
                desc_edizione = self.wait.until(EC.presence_of_element_located(
                    (By.XPATH, EDITION_DESCRIPTION_INPUT)))
                full_desc = (f"{course_name}-{edition_start_date.strftime('%d/%m/%Y')}"
                             f"-\n{description}")
                desc_edizione.send_keys(full_desc)
                self._pause_for_visual_check()

            # Publication start date (2 months before)
            two_months_before = edition_start_date - relativedelta(months=2)
            pub_start_str = two_months_before.strftime("%d/%m/%Y")
            pub_start_field = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, EDITION_PUB_START_DATE_INPUT)))
            pub_start_field.clear()
            pub_start_field.send_keys(pub_start_str)
            self._pause_for_visual_check()

            # Publication end date (edition end + 1 day)
            pub_end_str = (edition_end_date_obj + timedelta(days=1)).strftime("%d/%m/%Y")
            pub_end_field = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, EDITION_PUB_END_DATE_INPUT)))
            pub_end_field.clear()
            pub_end_field.send_keys(pub_end_str)
            self._pause_for_visual_check()

            # Edition start date
            ed_start_field = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, EDITION_START_DATE_INPUT)))
            ed_start_field.clear()
            ed_start_field.send_keys(edition_start_date.strftime("%d/%m/%Y"))
            self._pause_for_visual_check()

            # Edition end date
            ed_end_field = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, EDITION_END_DATE_INPUT)))
            ed_end_field.clear()
            ed_end_field.send_keys(edition_end_date_obj.strftime("%d/%m/%Y"))
            self._pause_for_visual_check()

            # Location, Language, Supplier, Price via helpers
            self._fill_edition_location(location)
            self._fill_edition_language()
            self._fill_edition_supplier(supplier)
            self._fill_edition_price(price)

            # Fill Attributi Aggiuntivi
            self._fill_edition_attributi_aggiuntivi(
                centro_costo=centro_costo,
                direzione_pagante=direzione_pagante,
                finanziata=finanziata,
                servizio_pagante=servizio_pagante,
                sottotipologia=sottotipologia,
                societa_pagante=societa_pagante,
            )

            time.sleep(1)
            # Save and close edition
            self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, EDITION_SAVE_CLOSE_BUTTON))).click()
            self._pause_for_visual_check()

            # Wait for activity page to load
            self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, ACTIVITY_ADD_BUTTON_1)))
            print("Model: Edition saved successfully. Starting activity creation.")
            self._pause_for_visual_check()

            # Create all activities
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
                    impegno_previsto_in_ore=activity.get('impegno_ore', '')
                )
                if not success:
                    return (f"‼️👩🏻‍✈️ Errore durante la creazione dell'attività {i + 1} "
                            f"('{activity['title']}'). Le attività precedenti potrebbero "
                            f"essere state create.")
                created_count += 1

            edition_display_name = (
                edition_title_optional
                if edition_title_optional and edition_title_optional.strip()
                else f"Edizione del {edition_start_date.strftime('%d/%m/%Y')}"
            )
            return (f"✅🤩 Successo! Edizione '{edition_display_name}' per '{course_name}' "
                    f"creata con {created_count} attività.")

        except Exception as e:
            print(f"ERROR in create_edition_and_activities: {e}")
            return (f"‼️👩🏻‍✈️ Errore generale durante la creazione dell'edizione "
                    f"o delle attività: {e}")

    def create_edition_with_activities_batch(
            self,
            course_name: str,
            edition_title: str,
            start_date,
            end_date,
            location: str = "",
            supplier: str = "",
            price: str = "",
            description: str = "",
            activities: list = None,
            return_to_courses_page: bool = True,
            # NEW PARAMETERS:
            centro_costo: str = "",
            direzione_pagante: str = "",
            finanziata: str = "",
            servizio_pagante: str = "",
            sottotipologia: str = "",
            societa_pagante: str = "",
    ) -> bool:
        """Create a single edition with activities for BATCH processing."""
        try:
            print(f"\n{'=' * 60}")
            print(f"BATCH: Creating edition '{edition_title}' for course '{course_name}'")
            print(f"{'=' * 60}")

            # Parse dates
            if isinstance(start_date, str):
                edition_start_date = datetime.strptime(start_date, '%d/%m/%Y').date()
            else:
                edition_start_date = start_date

            if isinstance(end_date, str):
                edition_end_date_obj = datetime.strptime(end_date, '%d/%m/%Y').date()
            else:
                edition_end_date_obj = end_date

            # Step 1: Search course
            print(f"\n[1] Searching for course: {course_name}")
            if not self.search_course(course_name):
                print(f"   ❌ Course '{course_name}' not found")
                return False
            print(f"   ✅ Course '{course_name}' found")

            # Step 2: Open course
            print(f"\n[2] Opening course: {course_name}")
            if not self.open_course_from_list(course_name):
                print(f"   ❌ Could not open course '{course_name}'")
                return False
            print(f"   ✅ Course '{course_name}' opened")

            # Step 3: Click Edizioni tab
            print(f"\n[3] Clicking 'Edizioni' tab...")
            edizioni_tab = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, COURSE_DETAIL_EDIZIONI_TAB)))
            edizioni_tab.click()
            print(f"   ✅ Clicked 'Edizioni' tab")
            self._pause_for_visual_check()

            # Step 4: Click Crea -> Edizione guidata da docente
            print(f"\n[4] Creating new edition...")
            self.wait.until(EC.presence_of_element_located(
                (By.XPATH, EDITION_CREA_BUTTON))).click()
            self._pause_for_visual_check()
            self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, EDITION_GUIDATA_OPTION))).click()
            print(f"   ✅ Clicked 'Crea' -> 'Edizione guidata da docente'")
            self._pause_for_visual_check()

            # Step 5: Fill edition form
            print(f"\n[5] Filling edition form...")

            # Title
            titolo_field = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, EDITION_TITLE_INPUT)))
            if edition_title and edition_title.strip():
                print(f"   Using custom edition title: {edition_title}")
                titolo_field.clear()
                titolo_field.send_keys(edition_title)
            else:
                print(f"   Using default edition title (course name + date)")
                titolo_field.send_keys("-" + edition_start_date.strftime("%d/%m/%Y"))
            self._pause_for_visual_check()

            # Description
            if description:
                desc_edizione = self.wait.until(EC.presence_of_element_located(
                    (By.XPATH, EDITION_DESCRIPTION_INPUT)))
                full_desc = (f"{course_name}-{edition_start_date.strftime('%d/%m/%Y')}"
                             f"-/n{description}")
                desc_edizione.send_keys(full_desc)
                self._pause_for_visual_check()

            # Publication start (2 months before)
            two_months_before = edition_start_date - relativedelta(months=2)
            pub_start_str = two_months_before.strftime("%d/%m/%Y")
            pub_start_field = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, EDITION_PUB_START_DATE_INPUT)))
            pub_start_field.clear()
            pub_start_field.send_keys(pub_start_str)
            print(f"   ✅ Publication start: {pub_start_str}")
            self._pause_for_visual_check()

            # Publication end (edition end + 1 day)
            pub_end_str = (edition_end_date_obj + timedelta(days=1)).strftime("%d/%m/%Y")
            pub_end_field = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, EDITION_PUB_END_DATE_INPUT)))
            pub_end_field.clear()
            pub_end_field.send_keys(pub_end_str)
            print(f"   ✅ Publication end: {pub_end_str}")
            self._pause_for_visual_check()

            # Edition start
            ed_start_field = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, EDITION_START_DATE_INPUT)))
            ed_start_field.clear()
            ed_start_field.send_keys(edition_start_date.strftime("%d/%m/%Y"))
            print(f"   ✅ Edition start: {edition_start_date.strftime('%d/%m/%Y')}")
            self._pause_for_visual_check()

            # Edition end
            ed_end_field = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, EDITION_END_DATE_INPUT)))
            ed_end_field.clear()
            ed_end_field.send_keys(edition_end_date_obj.strftime("%d/%m/%Y"))
            print(f"   ✅ Edition end: {edition_end_date_obj.strftime('%d/%m/%Y')}")
            self._pause_for_visual_check()

            # Location, Language, Supplier, Price via helpers
            self._fill_edition_location(location)
            self._fill_edition_language()
            self._fill_edition_supplier(supplier)
            self._fill_edition_price(price)

            # Fill Attributi Aggiuntivi
            self._fill_edition_attributi_aggiuntivi(
                centro_costo=centro_costo,
                direzione_pagante=direzione_pagante,
                finanziata=finanziata,
                servizio_pagante=servizio_pagante,
                sottotipologia=sottotipologia,
                societa_pagante=societa_pagante
            )

            # Step 6: Save edition
            print(f"\n[6] Saving edition...")
            time.sleep(1)
            self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, EDITION_SAVE_CLOSE_BUTTON))).click()
            print(f"   ✅ Clicked 'Salva e chiudi'")
            self._pause_for_visual_check()

            # Wait for activity page
            self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, ACTIVITY_ADD_BUTTON_1)))
            print(f"   ✅ Edition saved! Activity page loaded.")
            self._pause_for_visual_check()

            # Step 7: Create all activities
            if activities and len(activities) > 0:
                print(f"\n[7] Creating {len(activities)} activities...")
                for act_idx, activity in enumerate(activities):
                    print(f"\n--- Creating activity {act_idx + 1} of {len(activities)} ---")
                    act_date = activity.get('date', '')
                    if isinstance(act_date, str):
                        act_date_obj = datetime.strptime(act_date, '%d/%m/%Y')
                    else:
                        act_date_obj = act_date

                    success = self._create_single_activity(
                        unique_title=activity.get('title', f'Attività {act_idx + 1}'),
                        full_description=activity.get('description', ''),
                        activity_date_obj=act_date_obj,
                        start_time_str=activity.get('start_time', '09.00'),
                        end_time_str=activity.get('end_time', '11.00'),
                        impegno_previsto_in_ore=activity.get('impegno_ore', '')
                    )
                    if not success:
                        print(f"   ⚠️ Activity may have failed, continuing...")
            else:
                print(f"\n[7] No activities to create")

            # Step 8: Navigate back to courses page
            if return_to_courses_page:
                print(f"\n[8] Navigating back to courses search page...")

                try:
                    back_button_1 = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable(
                            (By.XPATH, BACK_FROM_ACTIVITY_TO_EDITION)))
                    back_button_1.click()
                    time.sleep(3)
                    print(f"   ✅ Clicked back (activity → edition page)")
                except Exception as e:
                    print(f"   ⚠️ Back button 1 failed: {e}, using browser back")
                    self.driver.back()
                    time.sleep(3)
                self._pause_for_visual_check()

                try:
                    back_button_2 = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable(
                            (By.XPATH, BACK_FROM_EDITION_TO_COURSE)))
                    back_button_2.click()
                    time.sleep(3)
                    print(f"   ✅ Clicked back (edition → courses search)")
                except Exception as e:
                    print(f"   ⚠️ Back button 2 failed: {e}, using browser back")
                    self.driver.back()
                    time.sleep(3)
                self._pause_for_visual_check()

                try:
                    search_box_locator = (By.NAME, COURSE_SEARCH_NAME_INPUT)
                    WebDriverWait(self.driver, 15).until(
                        EC.presence_of_element_located(search_box_locator))
                    print(f"   ✅ Back on courses search page!")
                except:
                    print(f"   ⚠️ May not be on courses search page, trying navigation...")
                    try:
                        self.navigate_to_courses_page()
                        print(f"   ✅ Navigated to courses page manually")
                    except Exception as nav_error:
                        print(f"   ❌ Navigation failed: {nav_error}")

            print(f"\n{'=' * 60}")
            print(f"✅ BATCH: Edition '{edition_title}' for '{course_name}' completed!")
            print(f"   Created {len(activities) if activities else 0} activities")
            print(f"{'=' * 60}\n")
            return True


        except Exception as e:
            print(f"\n❌ BATCH ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                self.driver.save_screenshot(f"batch_error_{timestamp}.png")

            except:
                pass

            # Try to navigate back to courses page for next iteration

            try:
                print("   Attempting recovery: navigating back to Corsi page...")
                self.navigate_to_courses_page()
                print("   ✅ Recovery successful")

            except:
                print("   ❌ Recovery failed")
            return False

    def open_edizioni_tab(self):
        try:
            edizioni_tab_element = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, COURSE_DETAIL_EDIZIONI_TAB)))
            edizioni_tab_element.click()
            print("Model: Clicked 'Edizioni' tab")
            self.wait.until(EC.presence_of_element_located(
                (By.XPATH, "//input[contains(@aria-label, 'Titolo edizione')]")))
            print("Model: Search box on the editions page is loaded")
            return True
        except Exception as e:
            print(f"Errore: Impossibile fare clic sulla scheda 'Edizioni'. Error: {e}")
            return False

    def _search_and_open_edition(self, edition_code):
        """Search for an edition by code, extract dates, and open it."""
        try:
            print(f"Model: Searching for edition with code '{edition_code}'")
            time.sleep(1)

            try:
                WebDriverWait(self.driver, 5).until(
                    EC.invisibility_of_element_located((By.CLASS_NAME, "AFBlockingGlassPane")))
            except:
                pass

            # Set date filter
            try:
                data_pub = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located(
                        (By.XPATH, EDITION_SEARCH_DATE_FILTER)))
                data_pub.clear()
                data_pub.send_keys('13/09/2020')
            except:
                print("   ⚠️ Could not set publication date filter")

            # Click 'Numero edizione' dropdown
            numero_edizione_dropdown = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, EDITION_SEARCH_OPERATOR_DROP)))
            numero_edizione_dropdown.click()
            self._pause_for_visual_check()

            # Select 'Contains'
            self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, EDITION_SEARCH_OPERATOR_OPT))).click()
            self._pause_for_visual_check()
            time.sleep(2)

            # Enter edition code
            numero_edizione_input_xpaths = [
                EDITION_SEARCH_NUMBER_INPUT_1,
                EDITION_SEARCH_NUMBER_INPUT_2,
            ]
            numero_edizione_input = None
            for xpath in numero_edizione_input_xpaths:
                try:
                    numero_edizione_input = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, xpath)))
                    print(f"   Found edition input with: {xpath}")
                    break
                except:
                    continue

            if not numero_edizione_input:
                raise Exception("Could not find 'Numero edizione' input field")

            numero_edizione_input.clear()
            numero_edizione_input.send_keys(edition_code)
            print(f"   Entered edition code: {edition_code}")
            self._pause_for_visual_check()

            # Click Search
            self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, EDITION_SEARCH_SUBMIT_BTN))).click()
            print("Model: Search submitted. Waiting for results.")

            try:
                WebDriverWait(self.driver, 15).until(
                    EC.invisibility_of_element_located((By.CLASS_NAME, "AFBlockingGlassPane")))
            except:
                pass
            time.sleep(2)

            # ═══════════════════════════════════════════════════════
            # STEP 1: EXTRACT DATES FROM SEARCH RESULTS ROW
            # (do this BEFORE clicking, while row is still visible)
            # ═══════════════════════════════════════════════════════
            edition_start_date = None
            edition_end_date = None

            try:
                result_row = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located(
                        (By.XPATH, EDITION_RESULT_ROW)))

                # Strategy 1: Find span with publication start date by ID
                try:
                    pub_start_span = result_row.find_element(
                        By.XPATH, EDITION_RESULT_PUB_START)
                    val = pub_start_span.text.strip()
                    if val:
                        edition_start_date = val
                        print(f"   ✅ Publication start date: {edition_start_date}")
                except:
                    pass

                # Strategy 2: Find span with publication end date by ID
                try:
                    pub_end_span = result_row.find_element(
                        By.XPATH, EDITION_RESULT_PUB_END)
                    val = pub_end_span.text.strip()
                    if val:
                        edition_end_date = val
                        print(f"   ✅ Publication end date: {edition_end_date}")
                except:
                    pass

                # Strategy 3: If still missing, get ALL date spans from the row
                if not edition_start_date or not edition_end_date:
                    print("   ⚠️ Trying to read all date spans from result row...")
                    import re
                    date_spans = result_row.find_elements(
                        By.XPATH, EDITION_RESULT_DATE_SPAN)
                    dates_found = []
                    for span in date_spans:
                        val = span.text.strip()
                        if re.match(r'\d{2}/\d{2}/\d{4}', val):
                            dates_found.append(val)
                    print(f"   Dates found in row: {dates_found}")
                    if len(dates_found) >= 1 and not edition_start_date:
                        edition_start_date = dates_found[0]
                    if len(dates_found) >= 2 and not edition_end_date:
                        edition_end_date = dates_found[1]

            except Exception as e:
                print(f"   ⚠️ Could not extract dates from search results: {e}")

            # ═══════════════════════════════════════════════════════
            # STEP 2: CLICK THE EDITION LINK TO OPEN IT
            # (this runs ALWAYS — after date extraction, not inside it)
            # ═══════════════════════════════════════════════════════
            print(f"   Clicking edition link to open it...")
            link_xpath = EDITION_SEARCH_RESULT_LINK
            link_clicked = False

            for attempt in range(3):
                try:
                    link = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, link_xpath)))
                    print(f"   Found result link (attempt {attempt + 1}). Clicking...")
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({block: 'center'});", link)
                    time.sleep(0.5)
                    try:
                        link.click()
                        link_clicked = True
                    except (StaleElementReferenceException,
                            ElementClickInterceptedException):
                        print(f"   ⚠️ Click failed, retrying...")
                        time.sleep(2)
                        link = self.driver.find_element(By.XPATH, link_xpath)
                        self.driver.execute_script("arguments[0].click();", link)
                        link_clicked = True
                    if link_clicked:
                        break
                except Exception as e:
                    print(f"   ⚠️ Attempt {attempt + 1} failed: {e}")
                    time.sleep(3)

            if not link_clicked:
                raise Exception("Could not click edition link after 3 attempts")

            # ═══════════════════════════════════════════════════════
            # STEP 3: WAIT FOR EDITION DETAIL PAGE TO LOAD
            # ═══════════════════════════════════════════════════════
            print("   Waiting for edition detail page to load...")
            time.sleep(3)

            try:
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.XPATH,
                                                    f"{EDITION_DETAIL_CONFIRM_1} | "
                                                    f"{EDITION_DETAIL_CONFIRM_2} | "
                                                    f"{EDITION_DETAIL_CONFIRM_3}")))
                print("   ✅ Edition detail page loaded")
            except:
                print("   ⚠️ Could not confirm page load, waiting extra...")
                time.sleep(5)

            self._pause_for_visual_check()
            print(f"Model: Opened edition '{edition_code}'. "
                  f"Dates: start={edition_start_date}, end={edition_end_date}")

            return {
                'success': True,
                'start_date': edition_start_date,
                'end_date': edition_end_date
            }

        except Exception as e:
            print(f"Model: Could not find/click edition '{edition_code}'. Error: {e}")
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                self.driver.save_screenshot(f"error_search_edition_{timestamp}.png")
            except:
                pass
            return False

    def _perform_student_addition_steps(self, student_file_path, lista_nome,
                                        edition_start_date=None, edition_end_date=None):
        try:
            # PART 0: Navigate to Seleziona Allievi page
            print("\n=== PART 0: Navigating to Seleziona Allievi page ===")

            # Step 0.1: Click Allievi tab
            print("Step 0.1: Clicking 'Allievi' tab...")
            # Wait longer for page to fully stabilize after navigation
            #time.sleep(5)

            # Wait for blocking overlay to disappear first
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.invisibility_of_element_located(
                        (By.CLASS_NAME, "AFBlockingGlassPane")))
            except:
                pass

            # Extra wait for page to be fully interactive
            time.sleep(3)

            allievi_tab = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, STUDENT_ALLIEVI_TAB)))
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", allievi_tab)
            time.sleep(1)
            try:
                allievi_tab.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", allievi_tab)
            print("   ✅ Clicked 'Allievi' tab")
            self._pause_for_visual_check()

            # Step 0.2: Click Aggiungi allievi
            print("Step 0.2: Clicking 'Aggiungi allievi'...")
            self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, STUDENT_ADD_ALLIEVI_BUTTON))).click()
            print("   ✅ Clicked 'Aggiungi allievi'")
            self._pause_for_visual_check()

            # Step 0.3: Click Assegnazione obbligatoria
            print("Step 0.3: Clicking 'Assegnazione obbligatoria'...")
            assegnazione_obb_xpaths = [
                STUDENT_ASSEGNAZIONE_OBB_1,
                STUDENT_ASSEGNAZIONE_OBB_2,
            ]
            assegnazione_btn = None
            for xpath in assegnazione_obb_xpaths:
                try:
                    assegnazione_btn = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, xpath)))
                    break
                except:
                    continue

            if not assegnazione_btn:
                raise Exception("Could not find 'Assegnazione obbligatoria' option")
            assegnazione_btn.click()
            print("   ✅ Clicked 'Assegnazione obbligatoria'")
            self._pause_for_visual_check()

            # Step 0.4: Select team from dropdown
            print("Step 0.4: Selecting team from dropdown...")
            try:
                assegna_come_trigger = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, STUDENT_TEAM_DROPDOWN)))
                assegna_come_trigger.click()
            except ElementClickInterceptedException:
                assegna_come_trigger = self.wait.until(
                    EC.presence_of_element_located((By.XPATH, STUDENT_TEAM_DROPDOWN)))
                self.driver.execute_script("arguments[0].click();", assegna_come_trigger)
            self._pause_for_visual_check()

            option_xpath = f"//li[contains(text(), '{STUDENT_TEAM_NAME}')]"
            self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, option_xpath))).click()
            print(f"   ✅ Selected '{STUDENT_TEAM_NAME}'")
            self._pause_for_visual_check()

            # Step 0.5: Fill 'Con questa nota' field
            print("Step 0.5: Filling 'Con questa nota' with '.'...")
            nota_xpaths = [
                STUDENT_NOTA_FIELD_1,
                STUDENT_NOTA_FIELD_2,
            ]
            nota_field = None
            for xpath in nota_xpaths:
                try:
                    nota_field = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, xpath)))
                    break
                except:
                    continue

            if nota_field:
                nota_field.clear()
                nota_field.send_keys(".")
                print("   ✅ Filled 'Con questa nota' with '.'")
            else:
                print("   ⚠️ Could not find 'Con questa nota' field")
            self._pause_for_visual_check()

            # Step 0.6: Fill Data scadenza
            print("Step 0.6: Calculating and filling 'Data scadenza'...")
            today = datetime.now().date()
            data_scadenza_str = ""

            if edition_start_date and edition_end_date:
                try:
                    start_date_obj = datetime.strptime(edition_start_date, "%d/%m/%Y").date()
                    end_date_obj = datetime.strptime(edition_end_date, "%d/%m/%Y").date()
                    if start_date_obj > today:
                        data_scadenza = end_date_obj + timedelta(days=1)
                        print(f"   Edition is FUTURE → Scadenza = end + 1 = "
                              f"{data_scadenza.strftime('%d/%m/%Y')}")
                    else:
                        data_scadenza = today + timedelta(days=1)
                        print(f"   Edition is PAST → Scadenza = today + 1 = "
                              f"{data_scadenza.strftime('%d/%m/%Y')}")
                    data_scadenza_str = data_scadenza.strftime("%d/%m/%Y")
                except Exception as date_calc_err:
                    print(f"   ⚠️ Error calculating scadenza: {date_calc_err}")
                    data_scadenza_str = (today + timedelta(days=1)).strftime("%d/%m/%Y")
            else:
                data_scadenza_str = (today + timedelta(days=1)).strftime("%d/%m/%Y")
                print(f"   ⚠️ Edition dates not available, using fallback: {data_scadenza_str}")

            scadenza_xpaths = [
                STUDENT_SCADENZA_FIELD_1,
                STUDENT_SCADENZA_FIELD_2,
            ]
            scadenza_field = None
            for xpath in scadenza_xpaths:
                try:
                    scadenza_field = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, xpath)))
                    break
                except:
                    continue

            if scadenza_field:
                scadenza_field.clear()
                scadenza_field.send_keys(data_scadenza_str)
                scadenza_field.send_keys(Keys.TAB)
                print(f"   ✅ Filled 'Data scadenza' with: {data_scadenza_str}")
            else:
                print("   ⚠️ Could not find 'Data scadenza' field")
            self._pause_for_visual_check()

            # Step 0.7: Click Successivo
            print("Step 0.7: Clicking 'Successivo'...")
            time.sleep(2)
            successivo_xpaths = [STUDENT_SUCCESSIVO_BUTTON]
            successivo_btn = None
            for xpath in successivo_xpaths:
                try:
                    successivo_btn = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, xpath)))
                    break
                except:
                    continue

            if not successivo_btn:
                raise Exception("Could not find 'Successivo' button")

            try:
                successivo_btn.click()
            except StaleElementReferenceException:
                print("   ⚠️ Stale element, re-finding Successivo...")
                time.sleep(2)
                for xpath in successivo_xpaths:
                    try:
                        successivo_btn = WebDriverWait(self.driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, xpath)))
                        successivo_btn.click()
                        break
                    except:
                        continue
            print("   ✅ Clicked 'Successivo'")
            self._pause_for_visual_check()

            # PART 1: Upload student list
            print("\n=== PART 1: Uploading student list ===")

            # Step 1.1: Click Aggiungi dropdown
            print("Step 1.1: Clicking 'Aggiungi' dropdown...")
            aggiungi_dropdown_xpaths = [STUDENT_AGGIUNGI_DROPDOWN_1]
            aggiungi_dropdown = None
            for xpath in aggiungi_dropdown_xpaths:
                try:
                    aggiungi_dropdown = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, xpath)))
                    print(f"   Found 'Aggiungi' dropdown with: {xpath}")
                    break
                except:
                    continue

            if not aggiungi_dropdown:
                raise Exception("Could not find 'Aggiungi' dropdown on Seleziona allievi page")
            aggiungi_dropdown.click()
            print("   ✅ Clicked 'Aggiungi' dropdown")
            self._pause_for_visual_check()

            # Step 1.2: Select Elenco numeri persona
            print("Step 1.2: Selecting 'Elenco numeri persona'...")
            elenco_xpaths = [STUDENT_ELENCO_OPTION_1]
            elenco_option = None
            for xpath in elenco_xpaths:
                try:
                    elenco_option = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, xpath)))
                    print(f"   Found 'Elenco numeri persona' with: {xpath}")
                    break
                except:
                    continue

            if not elenco_option:
                raise Exception("Could not find 'Elenco numeri persona' option")
            elenco_option.click()
            print("   ✅ Selected 'Elenco numeri persona'")
            self._pause_for_visual_check()
            time.sleep(2)

            # Step 1.3: Fill Nome field
            print(f"Step 1.3: Filling 'Nome' field with: {lista_nome}")
            nome_xpaths = [STUDENT_NOME_FIELD_1, STUDENT_NOME_FIELD_2]
            nome_field = None
            for xpath in nome_xpaths:
                try:
                    nome_field = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, xpath)))
                    print(f"   Found 'Nome' field with: {xpath}")
                    break
                except:
                    continue

            if not nome_field:
                raise Exception("Could not find 'Nome' field")

            time.sleep(2)
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", nome_field)
            time.sleep(0.5)

            try:
                nome_field.clear()
                nome_field.send_keys(lista_nome)
            except Exception:
                print("   ⚠️ Standard input failed, using JavaScript...")
                self.driver.execute_script(
                    "arguments[0].value = ''; arguments[0].value = arguments[1]; "
                    "arguments[0].dispatchEvent(new Event('change', {bubbles: true})); "
                    "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));",
                    nome_field, lista_nome)
            print(f"   ✅ Filled 'Nome' field with: {lista_nome}")

            # Step 1.4: Click + button
            print("Step 1.4: Clicking '+' to add attachment row...")
            plus_button_xpaths = [STUDENT_PLUS_BUTTON]
            plus_button = None
            for xpath in plus_button_xpaths:
                try:
                    plus_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, xpath)))
                    print(f"   Found '+' button with: {xpath}")
                    break
                except:
                    continue

            if not plus_button:
                raise Exception("Could not find '+' (Aggiungi) button for attachment")

            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", plus_button)
            time.sleep(0.5)
            try:
                plus_button.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", plus_button)
            print("   ✅ Clicked '+' button")
            self._pause_for_visual_check()
            time.sleep(2)

            # Step 1.5: Upload file
            print(f"Step 1.5: Uploading file: {student_file_path}")
            file_input_xpaths = [STUDENT_FILE_INPUT]
            file_input = None
            for xpath in file_input_xpaths:
                try:
                    file_input = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, xpath)))
                    print(f"   Found file input with: {xpath}")
                    break
                except:
                    continue

            if not file_input:
                raise Exception("Could not find file input element for upload")
            file_input.send_keys(student_file_path)
            print(f"   ✅ File uploaded: {student_file_path}")
            time.sleep(4)
            self._pause_for_visual_check()

            # Step 1.6: Click OK
            print("Step 1.6: Clicking 'OK'...")
            ok_button_xpaths = [STUDENT_OK_BUTTON]
            ok_button = None
            for xpath in ok_button_xpaths:
                try:
                    ok_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, xpath)))
                    print(f"   Found OK button with: {xpath}")
                    break
                except:
                    continue

            if not ok_button:
                raise Exception("Could not find OK button in Elenco numeri persona dialog")
            ok_button.click()
            print("   ✅ Clicked 'OK'")

            try:
                WebDriverWait(self.driver, 15).until(
                    EC.invisibility_of_element_located((By.CLASS_NAME, "AFBlockingGlassPane")))
            except:
                pass
            time.sleep(3)
            self._pause_for_visual_check()

            # PART 2: Submit student list
            print("\n=== PART 2: Submitting student list ===")

            print("Step 2.1: Clicking 'Successivo'...")
            self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, STUDENT_NEXT_BUTTON))).click()
            print("   ✅ Clicked 'Successivo'")
            time.sleep(2)
            self._pause_for_visual_check()

            print("Step 2.2: Clicking 'Sottometti'...")
            self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, STUDENT_SUBMIT_BUTTON))).click()
            print("   ✅ Clicked 'Sottometti'")
            time.sleep(2)

            print("Step 2.3: Confirming submission...")
            self.wait.until(EC.invisibility_of_element_located(
                (By.CLASS_NAME, "AFBlockingGlassPane")))
            self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, STUDENT_CONFIRM_DIALOG_OK))).click()
            print("   ✅ Confirmed submission")
            time.sleep(2)

            # PART 3: Verify students were added
            print("\n=== PART 3: Verifying students were added ===")
            verification_matricole = []
            try:
                with open(student_file_path, 'r', encoding='utf-8') as f:
                    verification_matricole = [line.strip() for line in f if line.strip()]
                print(f"   Will verify {len(verification_matricole)} matricole from file")
            except:
                print("   ⚠️ Could not read file for verification, skipping check")

            # Wait for Oracle to process — longer initial wait
            time.sleep(15)

            students_found = False
            max_attempts = 4

            for attempt in range(1, max_attempts + 1):
                try:
                    print(f"   Attempt {attempt}/{max_attempts}: Checking for students...")
                    student_row_xpaths = [
                        "//table[contains(@summary, 'llievi') or "
                        "contains(@summary, 'learner')]//tbody//tr",
                        "//table[contains(@id, 'ATt')]//tbody//tr[contains(@class, 'x')]",
                        "//div[contains(@id, 'learner')]//table//tbody//tr",
                    ]
                    rows = []
                    for xpath in student_row_xpaths:
                        rows = self.driver.find_elements(By.XPATH, xpath)
                        if rows:
                            break

                    if rows and len(rows) > 0:
                        print(f"   ✅ Found {len(rows)} student rows in the list")
                        students_found = True
                        if verification_matricole:
                            page_text = self.driver.page_source
                            found_count = sum(
                                1 for m in verification_matricole if m in page_text)
                            print(f"   ✅ Verified {found_count}/"
                                  f"{len(verification_matricole)} matricole on page")
                        break
                    else:
                        wait_time = 10
                        print(f"   Attempt {attempt}/{max_attempts}: no rows yet, "
                              f"waiting {wait_time}s...")
                        time.sleep(wait_time)

                except Exception as verify_err:
                    print(f"   Attempt {attempt}/{max_attempts}: "
                          f"verification error: {verify_err}")
                    time.sleep(10)

            try:
                WebDriverWait(self.driver, 5).until(
                    EC.invisibility_of_element_located((By.CLASS_NAME, "AFBlockingGlassPane")))
            except:
                pass

            if students_found:
                print("\n" + "=" * 50)
                print("✅ COMPLETE: Students added and verified!")
                print("=" * 50)
            else:
                print("\n" + "=" * 50)
                print("⚠️ COMPLETE: Students submitted but not yet visible in list.")
                print("   Oracle may need a few minutes to process the file.")
                print("=" * 50)

            return True

        except Exception as e:
            print(f"\n❌ ERROR during student addition: {e}")

            try:
                cancel_xpaths = [
                    "//button[contains(@id, ':d3::cancel')]",
                    "//button[text()='Annulla' or text()='Cancel']",
                    "//button[contains(@id, '::cancel')]",
                ]
                for xpath in cancel_xpaths:
                    try:
                        cancel_btn = self.driver.find_element(By.XPATH, xpath)
                        cancel_btn.click()
                        print("   🔄 Closed open dialog (Cancel)")
                        time.sleep(2)
                        break
                    except:
                        continue
            except:
                pass

            try:
                self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                time.sleep(1)
            except:
                pass

            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                ss_path = f"error_add_students_{timestamp}.png"
                self.driver.save_screenshot(ss_path)
                print(f"   Screenshot saved: {ss_path}")
            except:
                pass
            return False

    def _verify_students_in_edition(self, edition_code, expected_matricole):
        """Verify that students exist in an edition's Allievi tab."""
        result = {
            'found': [],
            'not_found': [],
            'total_in_system': 0,
            'success': False
        }

        try:
            print(f"\n   Verifying students for edition '{edition_code}'...")

            allievi_tab = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, STUDENT_ALLIEVI_TAB)))
            allievi_tab.click()
            print("   ✅ Clicked 'Allievi' tab")
            time.sleep(3)

            # Set filter to Tutto
            print("   Setting filter to 'Tutto'...")
            try:
                stato_dropdown = WebDriverWait(self.driver, 15).until(
                    EC.element_to_be_clickable((By.XPATH, STUDENT_STATUS_DROPDOWN)))
                stato_dropdown.click()
                tutto_option = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, STUDENT_STATUS_TUTTO)))
                tutto_option.click()
                print("Successfully clicked 'Tutto'.")
            except Exception as e:
                print(f"Initial setup (filter) failed. Cannot continue. Error: {e}")
                return False

            # Search each matricola
            for matricola in expected_matricole:
                matricola_clean = str(matricola).strip()

                try:
                    keyword_xpaths = [
                        STUDENT_KEYWORD_INPUT_1,
                        STUDENT_KEYWORD_INPUT_2,
                    ]
                    keyword_input = None
                    for xpath in keyword_xpaths:
                        try:
                            keyword_input = WebDriverWait(self.driver, 5).until(
                                EC.presence_of_element_located((By.XPATH, xpath)))
                            break
                        except:
                            continue

                    if not keyword_input:
                        print(f"   ⚠️ Could not find search input, "
                              f"skipping {matricola_clean}")
                        result['not_found'].append(matricola_clean)
                        continue

                    keyword_input.clear()
                    keyword_input.send_keys(matricola_clean)

                    cerca_btn = self.driver.find_element(
                        By.XPATH, STUDENT_CERCA_BUTTON)
                    cerca_btn.click()

                    try:
                        WebDriverWait(self.driver, 10).until(
                            EC.invisibility_of_element_located(
                                (By.CLASS_NAME, "AFBlockingGlassPane")))
                    except:
                        pass
                    time.sleep(2)

                    try:
                        WebDriverWait(self.driver, 3).until(
                            EC.presence_of_element_located((By.XPATH,
                                "//*[contains(text(),'Nessun dato') or "
                                "contains(text(),'Nessuna riga') or "
                                "contains(text(),'No data')]")))
                        print(f"   ❌ Matricola {matricola_clean}: NOT FOUND")
                        result['not_found'].append(matricola_clean)
                    except TimeoutException:
                        try:
                            self.driver.find_element(By.XPATH,
                                f"//td[normalize-space(.)='{matricola_clean}'] | "
                                f"//span[normalize-space(.)='{matricola_clean}']")
                            print(f"   ✅ Matricola {matricola_clean}: FOUND")
                            result['found'].append(matricola_clean)
                        except:
                            page_text = self.driver.find_element(
                                By.TAG_NAME, 'body').text
                            if matricola_clean in page_text:
                                print(f"   ✅ Matricola {matricola_clean}: "
                                      f"FOUND (in page text)")
                                result['found'].append(matricola_clean)
                            else:
                                print(f"   ❌ Matricola {matricola_clean}: NOT FOUND")
                                result['not_found'].append(matricola_clean)

                    # Reset search for next matricola
                    try:
                        reset_btn = self.driver.find_element(
                            By.XPATH, STUDENT_RESET_BUTTON)
                        reset_btn.click()
                        time.sleep(1)
                    except:
                        try:
                            keyword_input.clear()
                        except:
                            pass

                except Exception as e:
                    print(f"   ⚠️ Error checking matricola {matricola_clean}: {e}")
                    result['not_found'].append(matricola_clean)

            result['total_in_system'] = len(result['found'])
            result['success'] = True
            found_count = len(result['found'])
            total_expected = len(expected_matricole)
            print(f"   ✅ Verification complete: {found_count}/{total_expected} found")
            self._pause_for_visual_check()
            return result

        except Exception as e:
            print(f"   ❌ Error verifying students: {e}")
            result['not_found'] = [m for m in expected_matricole
                                   if m not in result['found']]
            return result

    def close(self):
        """Close the WebDriver and clean up resources."""
        try:
            if self.driver:
                self.driver.quit()
                print("Model: Closing driver.")
        except Exception as e:
            print(f"Model: Error closing driver: {e}")