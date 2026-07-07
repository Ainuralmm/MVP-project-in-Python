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
import automation_lock

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

        # Verify students in-flow after adding? Default OFF for speed.
        # The dedicated "Verifica Allievi" function can check on demand, and
        # the success message already tells users to re-check later.
        # Set to True to re-enable the in-flow check (adds ~5-6 min).
        self.verify_students_after_add = False

        # Record this driver's OS process id, so the global lock can later
        # kill EXACTLY this driver by PID if the run hangs (never a blanket kill).
        try:
            self.driver_pid = self.driver.service.process.pid
        except Exception:
            self.driver_pid = None

        mode = "Headless" if headless else "Visible"
        print(f"Model: WebDriver initialized in {mode} mode. (pid={self.driver_pid})")

    def _pause_for_visual_check(self):
        if self.debug_mode:
            time.sleep(self.debug_pause_duration)

    def login(self, url, username, password):
        """
        Log in to Oracle. Returns True ONLY if login actually succeeded.

        Fix: the old version returned True immediately after clicking the
        button, before Oracle responded — so a wrong password was reported
        as success, and the automation then hung on the next navigation.

        Now: after clicking, we wait for a definitive outcome —
          SUCCESS  → the browser leaves the login/IDCS page (URL changes
                     away from the login host), OR the Oracle homepage
                     search/menu element appears.
          FAILURE  → we are still on the login page after the timeout
                     (wrong password / MFA prompt / blocked), OR an error
                     is shown.
        This detection is URL-based and does NOT depend on matching Oracle's
        error text (which varies by language/version), so it is robust.
        """
        try:
            self.driver.get(url)
            time.sleep(3)  # let redirect to IDCS login page settle

            login_url_fragment = None
            try:
                # Remember the login host so we can detect leaving it.
                login_url_fragment = self.driver.current_url.split("/")[2]
            except Exception:
                login_url_fragment = None

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
                except Exception:
                    continue
            if not username_field:
                raise Exception("Could not find username field")
            username_field.clear()
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
                except Exception:
                    continue
            if not password_field:
                raise Exception("Could not find password field")
            password_field.clear()
            password_field.send_keys(password)

            # NEXT / SIGN IN BUTTON - multiple fallbacks
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
                except Exception:
                    continue
            if not sign_in_button:
                raise Exception("Could not find Next/Sign In button")
            sign_in_button.click()
            print("Model: Clicked sign-in. Verifying login outcome...")

            # ── VERIFY OUTCOME (bounded ~25s) ──────────────────────────────
            # Poll for success signals. If none appear in time, treat as
            # failure (wrong credentials / MFA / block) and return False.
            max_wait = 25          # seconds — bounded, never hangs forever
            poll_every = 1
            waited = 0
            still_on_password = 0

            while waited < max_wait:
                time.sleep(poll_every)
                waited += poll_every

                # 1) URL moved away from the login host → strong success signal
                try:
                    current_host = self.driver.current_url.split("/")[2]
                except Exception:
                    current_host = login_url_fragment

                if login_url_fragment and current_host and \
                        current_host != login_url_fragment:
                    print("Model: Login success (left login host).")
                    return True

                # 2) A password field is STILL present on the page → we are
                #    still stuck on login (wrong password / re-prompt).
                password_still_there = False
                for xpath in password_xpaths:
                    try:
                        if self.driver.find_elements(By.XPATH, xpath):
                            password_still_there = True
                            break
                    except Exception:
                        pass

                if password_still_there:
                    still_on_password += 1
                    # Require a few consecutive confirmations so a brief
                    # transition frame isn't mistaken for failure.
                    if still_on_password >= 5:
                        print("Model: Login FAILED — still on login page "
                              "(likely wrong credentials).")
                        return False
                else:
                    # Password field gone but URL not yet changed — likely
                    # mid-redirect. Reset the counter and keep polling.
                    still_on_password = 0

            # Timed out with no clear success → treat as failure (safe).
            print("Model: Login outcome unclear after timeout — treating as "
                  "FAILED to avoid a hung automation.")
            return False

        except Exception as e:
            print(f"Model: Error during login: {e}")
            return False

    def verify_credentials_only(self, url, username, password):
        """
        Lightweight credential check used by the LOGIN SCREEN (front door).
        Reuses login() (which now verifies its outcome) and always closes
        the browser afterward. Returns True/False.

        This runs BEFORE the main UI is shown, so a wrong password is caught
        in ~15-25s with a clear message, instead of hanging later inside an
        automation. It opens its own browser and guarantees cleanup.
        """
        try:
            result = self.login(url, username, password)
            return bool(result)
        except Exception as e:
            print(f"Model: verify_credentials_only error: {e}")
            return False
        finally:
            # Always close the verification browser — never leak it.
            try:
                self.close()
            except Exception:
                pass

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
                    (By.XPATH, COURSE_SEARCH_XPATH_INPUT)))
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

        Robust detection: looks for the course link ANYWHERE on the page,
        not just inside a specific container XPath.
        """
        try:
            cleaned_course_name = course_name.strip()
            capitalised_course_name = cleaned_course_name.title()

            # Wait for page to stabilize
            time.sleep(3)
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.invisibility_of_element_located(
                        (By.CLASS_NAME, "AFBlockingGlassPane")))
            except:
                pass

            # Fill search name
            search_box = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, COURSE_SEARCH_XPATH_INPUT)))
            search_box.clear()
            search_box.send_keys(capitalised_course_name)
            self._pause_for_visual_check()

            # Fill date filter
            date_input = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, COURSE_SEARCH_DATE_INPUT)))
            date_input.clear()
            date_input.send_keys("01/01/2000")
            self._pause_for_visual_check()
            time.sleep(3)

            # Click search
            search_button = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, COURSE_SEARCH_BUTTON)))
            search_button.click()
            print(f"Clicked Search button for course: '{capitalised_course_name}'")

            # Wait for Oracle to process (blocking overlay disappears)
            time.sleep(3)
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.invisibility_of_element_located(
                        (By.CLASS_NAME, "AFBlockingGlassPane")))
            except:
                pass
            time.sleep(2)

            course_name_lower = cleaned_course_name.lower()

            # ═══════════════════════════════════════════════════════
            # NEW ROBUST DETECTION — search the ENTIRE page, not a container
            # Handles Italian accents in translate()
            # ═══════════════════════════════════════════════════════

            # Strategy 1: exact text match on any <a> link
            exact_xpath = (
                f'//a[translate(normalize-space(.), '
                f'"ABCDEFGHIJKLMNOPQRSTUVWXYZÀÈÉÌÒÙ", '
                f'"abcdefghijklmnopqrstuvwxyzàèéìòù")="{course_name_lower}"]'
            )
            try:
                WebDriverWait(self.driver, 8).until(
                    EC.presence_of_element_located((By.XPATH, exact_xpath)))
                print(f"✅ Search result: Course '{course_name}' FOUND (exact match)")
                return True
            except TimeoutException:
                pass

            # Strategy 2: partial match
            partial_xpath = (
                f'//a[contains(translate(normalize-space(.), '
                f'"ABCDEFGHIJKLMNOPQRSTUVWXYZÀÈÉÌÒÙ", '
                f'"abcdefghijklmnopqrstuvwxyzàèéìòù"), "{course_name_lower}")]'
            )
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, partial_xpath)))
                print(f"✅ Search result: Course '{course_name}' FOUND (partial match)")
                return True
            except TimeoutException:
                pass

            # Strategy 3: check for explicit "no data" message
            try:
                WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located(
                        (By.XPATH, COURSE_NO_DATA_MESSAGE)))
                print(f"Search result: Course '{course_name}' NOT found (no data)")
                return False
            except TimeoutException:
                pass

            # No signal at all — assume not found
            print(f"Search result: Course '{course_name}' NOT found (no match on page)")
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

            # ═══════════════════════════════════════════════════════════════
            # Check for Oracle error dialog (title not unique / already exists)
            # BEFORE waiting for success confirmation
            # ═══════════════════════════════════════════════════════════════
            error_xpath = (
                "//*[contains(text(), 'non è univoco') "
                "or contains(text(), 'non è univoca') "
                "or contains(text(), 'not unique') "
                "or contains(text(), 'WLF-5145040')]"
            )

            try:
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, error_xpath)))
                print(f"⚠️ Oracle rejected: course '{course_name}' already exists")

                # Close the error dialog by clicking OK
                try:
                    ok_btn = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable(
                            (By.XPATH, "//button[normalize-space()='OK']")))
                    ok_btn.click()
                    time.sleep(1)
                except:
                    pass

                # Close the create form by clicking Annulla
                try:
                    annulla_btn = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((
                            By.XPATH,
                            "//button[normalize-space()='Annulla' "
                            "or normalize-space()='Cancel']"
                        )))
                    annulla_btn.click()
                    time.sleep(2)
                except:
                    pass

                # Wait for the Corsi list to reappear
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable(
                            (By.XPATH, COURSE_SEARCH_XPATH_INPUT)))
                except:
                    pass

                return (f"⚠️ Il corso '{course_name}' esiste già in Oracle. "
                        f"Nessuna azione eseguita.")

            except TimeoutException:
                # No error dialog appeared → proceed with success flow
                pass

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

                    # ── CHECK FOR "ATTENZIONE" ERROR POPUP FIRST ──
                    # If the activity date is outside the offer window, Oracle
                    # shows an error popup and does NOT save the activity.
                    # We must detect this and report the activity as FAILED.
                    time.sleep(1.5)  # let the error popup render if it will
                    try:
                        err_title = self.driver.find_elements(
                            By.XPATH, ACTIVITY_ERROR_POPUP_TITLE)
                        if err_title and any(e.is_displayed() for e in err_title):
                            # Read the specific reason
                            reason = "Data attività non valida (fuori dal periodo dell'offerta)."
                            try:
                                msg_els = self.driver.find_elements(
                                    By.XPATH, ACTIVITY_ERROR_POPUP_MESSAGE)
                                for m in msg_els:
                                    if m.is_displayed() and m.text.strip():
                                        reason = m.text.strip()
                                        break
                            except Exception:
                                pass

                            print(f"       ⚠️ ATTENZIONE popup: activity REJECTED — {reason}")

                            # Close the error popup (click its OK)
                            try:
                                err_ok = self.driver.find_elements(
                                    By.XPATH, ACTIVITY_ERROR_POPUP_OK)
                                for b in err_ok:
                                    if b.is_displayed():
                                        b.click()
                                        time.sleep(1)
                                        break
                            except Exception:
                                pass

                            # Also cancel/close the activity dialog so the next
                            # activity starts clean.
                            try:
                                cancel_btns = self.driver.find_elements(
                                    By.XPATH,
                                    "//button[contains(text(),'Annulla') or "
                                    "contains(text(),'Cancel') or "
                                    "contains(@id,'cancel')]")
                                for c in cancel_btns:
                                    if c.is_displayed():
                                        c.click()
                                        time.sleep(1)
                                        break
                            except Exception:
                                pass

                            # Return a structured FAILURE (not True).
                            return {
                                "success": False,
                                "title": unique_title,
                                "date": activity_date_str,
                                "reason": reason,
                            }
                    except Exception as check_err:
                        print(f"       (error-popup check skipped: {check_err})")

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
                return {"success": True, "title": unique_title,
                        "date": activity_date_str, "reason": None}

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

            return {"success": False, "title": unique_title,
                    "date": activity_date_str,
                    "reason": f"Errore tecnico: {str(e)[:100]}"}

    def _fill_edition_location(self, location):
        """
        Helper: fill the Aula/Location field in edition form.

        Hardening (fixes the 'si blocca dopo aver cercato l'aula' hang):
          - Wait for the ADF glass pane to clear AFTER clicking search, BEFORE
            checking the results table (the old code checked table presence
            while the pane was still up, so rows weren't ready → row click hung).
          - JS-click fallback on the OK button.
          - Fail fast with a clear message naming this step.
        """
        if not location:
            return

        def _wait_glass_clear(timeout=12):
            for cls in ("AFBlockingGlassPane", "AFModalGlassPane"):
                try:
                    WebDriverWait(self.driver, timeout).until(
                        EC.invisibility_of_element_located((By.CLASS_NAME, cls)))
                except Exception:
                    pass

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
            except Exception:
                continue

        if not cerca_aula_button:
            print("   ⚠️ Could not find 'Cerca/Search' button, skipping location")
            return

        cerca_aula_button.click()
        self._pause_for_visual_check()

        box_cerca_aula = self.wait.until(EC.presence_of_element_located(
            (By.XPATH, EDITION_AULA_KEYWORD_INPUT)))
        box_cerca_aula.clear()
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
            except Exception:
                continue

        if not search_button:
            raise Exception(
                "Bloccato alla ricerca aula: pulsante 'Cerca' non trovato nel "
                "popup aula.")

        search_button.click()
        print("   Clicked Aula search button")

        # ── KEY FIX: wait for the search glass pane to CLEAR before reading
        #    the results table, so the rows are actually populated. ──
        _wait_glass_clear(timeout=15)
        time.sleep(2)

        try:
            self.wait.until(EC.presence_of_element_located(
                (By.XPATH, EDITION_AULA_RESULTS_TABLE)))
        except Exception as e:
            raise Exception(
                f"Bloccato alla ricerca aula: la tabella dei risultati non si "
                f"è caricata per '{location}'. Dettaglio: {e}")

        # extra settle for row rendering
        _wait_glass_clear(timeout=5)

        location_lower = location.lower()

        # Check for "no results" first
        try:
            WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located((By.XPATH,
                                                '//*[contains(text(), "Nessuna riga") or '
                                                'contains(text(), "Nessun dato")]')))
            print(f"⚠️ Location '{location}' not found in popup.")
            try:
                annulla = self.driver.find_element(
                    By.XPATH, "//button[text()='Annulla' or text()='Cancel']")
                annulla.click()
            except Exception:
                pass
            return
        except TimeoutException:
            pass

        # Try multiple strategies to click the matching row
        found = False
        for xpath in [
            f'{EDITION_AULA_RESULTS_TABLE}//tr[.//td['
            f'translate(normalize-space(.), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", '
            f'"abcdefghijklmnopqrstuvwxyz")="{location_lower}"]]',
            f'{EDITION_AULA_RESULTS_TABLE}//tr[.//td['
            f'contains(translate(normalize-space(.), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", '
            f'"abcdefghijklmnopqrstuvwxyz"), "{location_lower}")]]',
        ]:
            try:
                row = WebDriverWait(self.driver, 8).until(
                    EC.element_to_be_clickable((By.XPATH, xpath)))
                try:
                    row.click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", row)
                print(f"   ✅ Selected location: {location}")
                found = True
                break
            except Exception:
                continue

        if not found:
            print(f"   ⚠️ Could not click row for '{location}', proceeding anyway")

        self._pause_for_visual_check()

        _wait_glass_clear(timeout=8)
        ok_button = self.wait.until(EC.element_to_be_clickable(
            (By.XPATH, EDITION_AULA_OK_BUTTON)))
        try:
            ok_button.click()
        except Exception as e:
            print(f"   Aula OK normal click failed, JS click: {e}")
            self.driver.execute_script("arguments[0].click();", ok_button)
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
        """
        Helper: fill the Price ('Determinazione prezzi') section.

        FIX for the hang at 'Aggiungi voce linea' (reported by all testers):
          - Wait for the ADF glass panes to clear after flagging the override
            (flagging fires a partial-page refresh that throws up an overlay;
            the old code clicked into that overlay).
          - Use element_to_be_clickable (not just presence) and try the LINK
            wrapping the '+' icon first, then the raw <img> as fallback.
          - scrollIntoView + normal click + JS-click fallback — the same
            robust pattern already used successfully for 'Aggiungi' activities.
          - Bounded, with clear error messages naming this step, so a failure
            fails FAST (releasing the lock) instead of hanging.
        """
        if not price:
            return

        def _wait_glass_clear():
            for cls in ("AFBlockingGlassPane", "AFModalGlassPane"):
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.invisibility_of_element_located((By.CLASS_NAME, cls)))
                except Exception:
                    pass

        # 1) Flag 'Override determinazione prezzi'
        _wait_glass_clear()
        time.sleep(1)
        flag_prezzi = self.wait.until(EC.element_to_be_clickable(
            (By.XPATH, EDITION_PRICE_FLAG_LABEL)))
        flag_prezzi.click()
        print("Flagged button 'Override determinazione prezzi'")
        self._pause_for_visual_check()

        # 2) Click 'Aggiungi voce linea' — the step that used to hang.
        #    Flagging the override triggers an ADF refresh + glass pane; wait
        #    for it to clear BEFORE clicking, then click robustly.
        _wait_glass_clear()
        time.sleep(1.5)  # let the pricing panel finish rendering the button

        # Try the clickable LINK wrapping the '+' icon first (more reliable in
        # ADF than clicking the raw <img>), then fall back to the img XPath.
        add_line_xpaths = [
            EDITION_PRICE_ADD_LINE_LINK,   # NEW in config (see note) - link/anchor
            EDITION_PRICE_ADD_LINE_BTN,    # existing - the <img> icon
        ]
        aggiungi_voce = None
        last_err = None
        for xpath in add_line_xpaths:
            try:
                aggiungi_voce = WebDriverWait(self.driver, 12).until(
                    EC.element_to_be_clickable((By.XPATH, xpath)))
                if aggiungi_voce:
                    print(f"Found 'Aggiungi voce linea' with: {xpath}")
                    break
            except Exception as e:
                last_err = e
                continue

        if not aggiungi_voce:
            # Fail FAST with a clear message instead of hanging.
            raise Exception(
                "Bloccato all'inserimento prezzo: impossibile trovare/cliccare "
                "'Aggiungi voce linea' (dopo aver flaggato override "
                f"determinazione prezzi). Dettaglio: {last_err}"
            )

        # scrollIntoView + normal click + JS fallback (proven pattern)
        try:
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", aggiungi_voce)
            time.sleep(0.5)
        except Exception:
            pass
        try:
            aggiungi_voce.click()
        except Exception as click_error:
            print(f"   Normal click failed, using JS click: {click_error}")
            self.driver.execute_script("arguments[0].click();", aggiungi_voce)
        print("Clicked on button 'Aggiungi voce linea'")
        self._pause_for_visual_check()

        # 3) Open the line-item type dropdown
        _wait_glass_clear()
        time.sleep(1)
        dropdown_voce = self.wait.until(EC.element_to_be_clickable(
            (By.XPATH, EDITION_PRICE_LINE_DROPDOWN)))
        try:
            dropdown_voce.click()
        except Exception as e:
            print(f"   Dropdown normal click failed, JS click: {e}")
            self.driver.execute_script("arguments[0].click();", dropdown_voce)
        self._pause_for_visual_check()

        # 4) Choose 'Prezzo di listino'
        prezzo_listino = self.wait.until(EC.element_to_be_clickable(
            (By.XPATH, EDITION_PRICE_LISTINO_OPTION)))
        try:
            prezzo_listino.click()
        except Exception as e:
            print(f"   Listino option normal click failed, JS click: {e}")
            self.driver.execute_script("arguments[0].click();", prezzo_listino)
        self._pause_for_visual_check()

        # 5) Enter the cost value
        _wait_glass_clear()
        costo = self.wait.until(EC.presence_of_element_located(
            (By.XPATH, EDITION_PRICE_COST_INPUT)))
        costo.clear()
        costo.send_keys(str(price))
        print(f"   ✅ Price set: {price}")

    def _fill_edition_language(self):
        """
        Helper: fill the Language field in edition form.

        Hardening: wait for glass panes, use element_to_be_clickable + JS-click
        fallback for BOTH the dropdown and the language option, and fail fast
        with a clear message naming this step.
        """
        def _wait_glass_clear():
            for cls in ("AFBlockingGlassPane", "AFModalGlassPane"):
                try:
                    WebDriverWait(self.driver, 12).until(
                        EC.invisibility_of_element_located((By.CLASS_NAME, cls)))
                except Exception:
                    pass

        _wait_glass_clear()
        time.sleep(2)

        # Open the language dropdown
        try:
            choose_lingua = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, EDITION_LANGUAGE_DROPDOWN)))
        except Exception as e:
            raise Exception(
                f"Bloccato alla lingua: impossibile trovare il menu lingua. {e}")
        try:
            choose_lingua.click()
        except Exception as e:
            print(f"   Lingua dropdown normal click failed, JS click: {e}")
            self.driver.execute_script("arguments[0].click();", choose_lingua)
        self._pause_for_visual_check()
        time.sleep(1)

        # Choose the language option (e.g. 'Italiana').
        # Prefer an exact, clickable match; fall back to JS click.
        lang_xpaths = [
            f'//li[normalize-space()="{EDITION_LANGUAGE_DEFAULT}"]',
            f'//*[contains(@id, "lngSel")]//*[normalize-space()='
            f'"{EDITION_LANGUAGE_DEFAULT}"]',
            f'//*[contains(text(), "{EDITION_LANGUAGE_DEFAULT}")]',
        ]
        find_lingua = None
        last_err = None
        for xpath in lang_xpaths:
            try:
                find_lingua = WebDriverWait(self.driver, 8).until(
                    EC.element_to_be_clickable((By.XPATH, xpath)))
                if find_lingua:
                    print(f"   Found language option with: {xpath}")
                    break
            except Exception as e:
                last_err = e
                continue

        if not find_lingua:
            raise Exception(
                f"Bloccato alla lingua: impossibile selezionare "
                f"'{EDITION_LANGUAGE_DEFAULT}'. Dettaglio: {last_err}")

        try:
            find_lingua.click()
        except Exception as e:
            print(f"   Lingua option normal click failed, JS click: {e}")
            self.driver.execute_script("arguments[0].click();", find_lingua)

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
            self._pause_for_visual_check()

            self._fill_edition_language()
            self._pause_for_visual_check()

            self._fill_edition_supplier(supplier)
            self._pause_for_visual_check()

            # wait for any dropdown overlay to fully disappear
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.invisibility_of_element_located(
                        (By.CLASS_NAME, "AFBlockingGlassPane")))
            except:
                pass
            time.sleep(2)  # extra wait for supplier dropdown to fully close

            self._fill_edition_price(price)
            self._pause_for_visual_check()

            # Fill Attributi Aggiuntivi
            self._fill_edition_attributi_aggiuntivi(
                centro_costo=centro_costo,
                direzione_pagante=direzione_pagante,
                finanziata=finanziata,
                servizio_pagante=servizio_pagante,
                sottotipologia=sottotipologia,
                societa_pagante=societa_pagante,
            )
            self._pause_for_visual_check()

            # Save and close edition
            self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, EDITION_SAVE_CLOSE_BUTTON))).click()
            self._pause_for_visual_check()

            # Wait for activity page to load
            self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, ACTIVITY_ADD_BUTTON_1)))
            print("Model: Edition saved successfully. Starting activity creation.")
            self._pause_for_visual_check()

            # Create all activities — collect successes AND failures.
            total_activities = len(activities)
            created_count = 0
            failed_activities = []  # list of {title, date, reason}

            for i, activity in enumerate(activities):
                print(f"--- Creating activity {i + 1} of {total_activities} ---")
                result = self._create_single_activity(
                    unique_title=activity['title'],
                    full_description=activity['description'],
                    activity_date_obj=activity['date'],
                    start_time_str=activity['start_time'],
                    end_time_str=activity['end_time'],
                    impegno_previsto_in_ore=activity.get('impegno_ore', '')
                )

                # Backward-compatible: accept dict OR bool
                if isinstance(result, dict):
                    ok = result.get("success", False)
                else:
                    ok = bool(result)

                if ok:
                    created_count += 1
                else:
                    reason = (result.get("reason") if isinstance(result, dict)
                              else "Errore sconosciuto")
                    failed_activities.append({
                        "title": activity['title'],
                        "date": (activity['date'].strftime('%d/%m/%Y')
                                 if hasattr(activity['date'], 'strftime')
                                 else str(activity['date'])),
                        "reason": reason or "Attività non creata",
                    })
                    print(f"   ⚠️ Activity {i + 1} FAILED: {reason}")
                    # continue to next activity (don't abort the whole edition)

            edition_display_name = (
                edition_title_optional
                if edition_title_optional and edition_title_optional.strip()
                else f"Edizione del {edition_start_date.strftime('%d/%m/%Y')}"
            )

            # Build an HONEST message: edition created, but flag failed activities.
            if not failed_activities:
                return (f"✅🤩 Successo! Edizione '{edition_display_name}' per "
                        f"'{course_name}' creata con {created_count} attività.")
            else:
                lines = [
                    f"⚠️ Edizione '{edition_display_name}' per '{course_name}' "
                    f"CREATA, ma {len(failed_activities)} attività su "
                    f"{total_activities} NON sono state create:",
                    ""
                ]
                for fa in failed_activities:
                    lines.append(f"  • '{fa['title']}' ({fa['date']}): {fa['reason']}")
                lines.append("")
                lines.append(f"✅ Attività create con successo: {created_count}/{total_activities}")
                lines.append("")
                lines.append("👉 Controlla in Oracle e correggi le date delle "
                             "attività non create (devono rientrare nel periodo "
                             "dell'offerta).")
                return "\n".join(lines)

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
        self.last_activities_created = 0
        self.last_activities_failed = []
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
            self._pause_for_visual_check()

            self._fill_edition_language()
            self._pause_for_visual_check()

            self._fill_edition_supplier(supplier)
            self._pause_for_visual_check()

            self._fill_edition_price(price)
            self._pause_for_visual_check()

            # Fill Attributi Aggiuntivi
            self._fill_edition_attributi_aggiuntivi(
                centro_costo=centro_costo,
                direzione_pagante=direzione_pagante,
                finanziata=finanziata,
                servizio_pagante=servizio_pagante,
                sottotipologia=sottotipologia,
                societa_pagante=societa_pagante,
            )
            self._pause_for_visual_check()

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
                activities_created = 0
                activities_failed = []  # {title, date, reason}

                for act_idx, activity in enumerate(activities):
                    try:
                        automation_lock.heartbeat(
                            step=f"attività {act_idx + 1}/{len(activities)}")
                    except Exception:
                        pass
                    print(f"\n--- Creating activity {act_idx + 1} of {len(activities)} ---")
                    act_date = activity.get('date', '')
                    if isinstance(act_date, str):
                        act_date_obj = datetime.strptime(act_date, '%d/%m/%Y')
                    else:
                        act_date_obj = act_date

                    result = self._create_single_activity(
                        unique_title=activity.get('title', f'Attività {act_idx + 1}'),
                        full_description=activity.get('description', ''),
                        activity_date_obj=act_date_obj,
                        start_time_str=activity.get('start_time', '09.00'),
                        end_time_str=activity.get('end_time', '11.00'),
                        impegno_previsto_in_ore=activity.get('impegno_ore', '')
                    )

                    # accept dict OR bool (backward compatible)
                    if isinstance(result, dict):
                        ok = result.get("success", False)
                        reason = result.get("reason") or "Attività non creata"
                    else:
                        ok = bool(result)
                        reason = "Attività non creata"

                    if ok:
                        activities_created += 1
                    else:
                        date_str = (act_date_obj.strftime('%d/%m/%Y')
                                    if hasattr(act_date_obj, 'strftime')
                                    else str(act_date_obj))
                        activities_failed.append({
                            "title": activity.get('title', f'Attività {act_idx + 1}'),
                            "date": date_str,
                            "reason": reason,
                        })
                        print(f"   ⚠️ Activity {act_idx + 1} FAILED: {reason}")

                # Expose the counts/failures so the presenter can report them.
                self.last_activities_created = activities_created
                self.last_activities_failed = activities_failed
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
            # EARLY EXIT: check for "no results" message
            # Prevents 40s of wasted retry attempts on invalid codes
            # ═══════════════════════════════════════════════════════
            no_data_xpaths = [
                "//*[contains(text(), 'Nessun dato da visualizzare')]",
                "//*[contains(text(), 'Nessuna riga')]",
                "//*[contains(text(), 'No data')]",
            ]
            for no_data_xpath in no_data_xpaths:
                try:
                    WebDriverWait(self.driver, 3).until(
                        EC.presence_of_element_located((By.XPATH, no_data_xpath)))
                    print(f"   ⚠️ No results for edition '{edition_code}' - "
                          f"code does not exist in Oracle")
                    return False  # Clean exit, no exception
                except TimeoutException:
                    continue  # This message not present, try next

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

    def _reset_edition_search(self):
        """
        Reset the Edizioni search form to a clean state.
        Called between editions in batch operations to avoid
        stale form data (like a stuck 'Contiene' dropdown).
        """
        try:
            # Try to find and click Reimposta button
            reimposta_xpaths = [
                "//button[normalize-space()='Reimposta']",
                "//button[normalize-space()='Reset']",
                "//a[normalize-space()='Reimposta']",
            ]
            for xpath in reimposta_xpaths:
                try:
                    btn = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, xpath)))
                    btn.click()
                    print("   ✅ Clicked Reimposta to reset search form")

                    # Wait for overlay to clear
                    try:
                        WebDriverWait(self.driver, 10).until(
                            EC.invisibility_of_element_located(
                                (By.CLASS_NAME, "AFBlockingGlassPane")))
                    except:
                        pass
                    time.sleep(2)
                    return True
                except:
                    continue

            # Fallback: navigate away and back
            print("   ⚠️ Reimposta not found, navigating fresh to Edizioni")
            self.navigate_to_edition_page()
            return True

        except Exception as e:
            print(f"   ⚠️ Could not reset search form: {e}")
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

            def _wait_glass_clear(timeout=12):
                for cls in ("AFBlockingGlassPane", "AFModalGlassPane"):
                    try:
                        WebDriverWait(self.driver, timeout).until(
                            EC.invisibility_of_element_located((By.CLASS_NAME, cls)))
                    except Exception:
                        pass

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
                raise Exception(
                    "Bloccato a 'Seleziona allievi': menu 'Aggiungi' non "
                    "trovato.")
            try:
                aggiungi_dropdown.click()
            except Exception as e:
                print(f"   'Aggiungi' normal click failed, JS click: {e}")
                self.driver.execute_script("arguments[0].click();", aggiungi_dropdown)
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
                raise Exception(
                    "Bloccato a 'Elenco numeri persona': opzione non trovata "
                    "nel menu Aggiungi.")
            try:
                elenco_option.click()
            except Exception as e:
                print(f"   'Elenco' normal click failed, JS click: {e}")
                self.driver.execute_script("arguments[0].click();", elenco_option)
            print("   ✅ Selected 'Elenco numeri persona'")
            self._pause_for_visual_check()
            _wait_glass_clear()
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
                raise Exception(
                    "Bloccato all'inserimento codice edizione: campo 'Nome' "
                    "(elenco numeri persona) non trovato.")

            _wait_glass_clear()

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

            # Step 1.4: Click '+' to add attachment row...
            print("Step 1.4: Clicking '+' to add attachment row...")
            _wait_glass_clear()
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

            # PART 2: Submit student list (stale-safe)
            print("\n=== PART 2: Submitting student list ===")

            print("Step 2.1: Clicking 'Successivo'...")
            self._click_when_ready(STUDENT_NEXT_BUTTON, "Successivo (Part 2)")
            time.sleep(3)  # let the submit screen finish rendering
            self._pause_for_visual_check()

            print("Step 2.2: Clicking 'Sottometti'...")
            self._click_when_ready(STUDENT_SUBMIT_BUTTON, "Sottometti")
            time.sleep(2)

            print("Step 2.3: Confirming submission...")
            # confirm dialog may or may not appear; try but don't hang
            try:
                self._click_when_ready(STUDENT_CONFIRM_DIALOG_OK,
                                       "Conferma invio (OK)", attempts=3)
            except Exception as confirm_err:
                # Some flows submit without a confirm dialog — don't fail the
                # whole run if the dialog simply wasn't there.
                print(f"   ℹ️ No confirm dialog to click (ok): {confirm_err}")
            time.sleep(2)

            # PART 3: Verify students were added (OPTIONAL — toggle above).
            if not getattr(self, "verify_students_after_add", False):
                print("\n=== PART 3 SKIPPED (verify_students_after_add=False) ===")
                print("   Invio completato. La verifica in-flow è disattivata "
                      "per velocità — usa 'Verifica Allievi' se vuoi controllare.")
                # Clear any overlay, then finish successfully.
                try:
                    WebDriverWait(self.driver, 5).until(
                        EC.invisibility_of_element_located(
                            (By.CLASS_NAME, "AFBlockingGlassPane")))
                except Exception:
                    pass
                print("\n" + "=" * 50)
                print("✅ COMPLETE: Students submitted.")
                print("=" * 50)
                return True

            # (in-flow verification enabled)
            print("\n=== PART 3: Verifying students were added ===")

            verification_matricole = []
            try:
                with open(student_file_path, 'r', encoding='utf-8') as f:
                    verification_matricole = [
                        line.strip() for line in f if line.strip()
                    ]
                print(f"   Will verify {len(verification_matricole)} matricole from file")
            except:
                print("   ⚠️ Could not read file for verification, skipping check")

            # Initial wait — Oracle needs time to process the file submission
            print("   ⏳ Waiting 15s for Oracle to process submission...")
            time.sleep(15)

            students_found = False
            if verification_matricole:
                # Use the same robust refresh + scroll-and-collect we use for Verifica
                result = self._refresh_and_collect_students(
                    expected_matricole=verification_matricole,
                    max_attempts=5,
                    wait_between=5
                )

                found_count = len(result['found'])
                expected_count = len(verification_matricole)

                if found_count == expected_count:
                    print(f"\n   ✅ ALL {found_count}/{expected_count} "
                          f"students verified!")
                    students_found = True
                elif found_count >= expected_count * 0.8:
                    # 80%+ found → likely succeeded, Oracle may still be processing
                    print(f"\n   ⚠️ {found_count}/{expected_count} found "
                          f"(Oracle may still be processing the rest)")
                    print(f"   Missing so far: {result['not_found'][:10]}")
                    students_found = True
                else:
                    print(f"\n   ❌ Only {found_count}/{expected_count} found.")
                    print(f"   Missing: {result['not_found'][:10]}")

            # Final overlay clear
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.invisibility_of_element_located(
                        (By.CLASS_NAME, "AFBlockingGlassPane")))
            except:
                pass

            if students_found:
                print("\n" + "=" * 50)
                print("✅ COMPLETE: Students added and verified!")
                print("=" * 50)
            else:
                print("\n" + "=" * 50)
                print("⚠️ COMPLETE: Students submitted but not all confirmed.")
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

    def _click_when_ready(self, xpath, description="element",
                          attempts=4, per_wait=10):
        """
        Click an element by XPath, tolerant of ADF re-renders:
          - waits for glass panes to clear,
          - waits for the element to be clickable,
          - retries if the element goes stale between find and click,
          - JS-click fallback.
        Raises with a clear message if it truly can't click.
        """
        last_err = None
        for i in range(1, attempts + 1):
            # clear overlays first
            for cls in ("AFBlockingGlassPane", "AFModalGlassPane"):
                try:
                    WebDriverWait(self.driver, per_wait).until(
                        EC.invisibility_of_element_located((By.CLASS_NAME, cls)))
                except Exception:
                    pass
            try:
                el = WebDriverWait(self.driver, per_wait).until(
                    EC.element_to_be_clickable((By.XPATH, xpath)))
                try:
                    el.click()
                except StaleElementReferenceException:
                    # element re-rendered between find and click → retry
                    raise
                except Exception:
                    self.driver.execute_script("arguments[0].click();", el)
                print(f"   ✅ Clicked {description}")
                return True
            except StaleElementReferenceException as e:
                last_err = e
                print(f"   ⚠️ {description} stale (attempt {i}/{attempts}), "
                      f"retrying...")
                time.sleep(2)
                continue
            except Exception as e:
                last_err = e
                time.sleep(2)
                continue
        raise Exception(
            f"Bloccato a '{description}': impossibile cliccare dopo "
            f"{attempts} tentativi. Dettaglio: {last_err}")

    def _read_all_visible_matricole(self):
        """
        Read all numero persona in the Allievi table.
        Uses small incremental scrolls so ADF has time to virtualize rows.
        """
        self._try_maximize_page_size()
        time.sleep(2)

        matricole_set = set()
        matricole_order = []
        container = self._find_scrollable_table()

        no_growth = 0
        max_iterations = 80  # safety cap

        # Get total scroll height once (if we have container)
        total_scroll_height = 0
        if container:
            try:
                total_scroll_height = self.driver.execute_script(
                    "return arguments[0].scrollHeight;", container)
                print(f"   📏 Table scroll height: {total_scroll_height}px")
            except:
                pass

        for i in range(max_iterations):
            try:
                automation_lock.heartbeat(step=f"lettura allievi (scroll {i + 1})")
            except Exception:
                pass
            # Read what's currently visible
            visible = self._read_visible_rows_once()

            before = len(matricole_set)
            for m in visible:
                if m not in matricole_set:
                    matricole_set.add(m)
                    matricole_order.append(m)
            after = len(matricole_set)

            if after > before:
                no_growth = 0
                print(f"   Iter {i + 1}: +{after - before} new "
                      f"(total: {after})")
            else:
                no_growth += 1

            # Stop after 4 consecutive no-growth iterations
            # (gives ADF more time to settle at the bottom)
            if no_growth >= 4:
                print(f"   ✅ Stable count after {i + 1} iterations")
                break

            # Scroll by 200px (small step → reliable virtualization)
            scrolled = False
            if container:
                try:
                    self.driver.execute_script(
                        "arguments[0].scrollTop = "
                        "arguments[0].scrollTop + 200;",
                        container)
                    scrolled = True
                except:
                    pass

            if not scrolled:
                self.driver.execute_script("window.scrollBy(0, 200);")

            # Wait for ADF to load the new batch
            try:
                WebDriverWait(self.driver, 3).until(
                    EC.invisibility_of_element_located(
                        (By.CLASS_NAME, "AFBlockingGlassPane")))
            except:
                pass
            time.sleep(1.5)  # extra time for virtualization to settle

        # Scroll back to top
        if container:
            try:
                self.driver.execute_script(
                    "arguments[0].scrollTop = 0;", container)
            except:
                pass

        print(f"   📋 Total unique matricole collected: {len(matricole_order)}")
        return matricole_order

    def _read_visible_rows_once(self):
        """Read matricole from rows currently in DOM — no scrolling."""
        import re
        matricole = []

        row_xpaths = [
            "//table[contains(@summary, 'llievi')]//tbody//tr",
            "//table[contains(@summary, 'learner')]//tbody//tr",
            "//table[contains(@id, 'ATt')]//tbody//tr[contains(@class, 'x')]",
            "//div[contains(@id, 'learner')]//table//tbody//tr",
        ]

        rows = []
        for xpath in row_xpaths:
            try:
                found = self.driver.find_elements(By.XPATH, xpath)
                if found:
                    rows = found
                    break
            except:
                continue

        for row in rows:
            try:
                cells = row.find_elements(By.XPATH, ".//td")
                for cell in cells:
                    text = cell.text.strip()
                    if re.fullmatch(r'\d{3,7}', text):
                        matricole.append(text)
                        break  # one matricola per row
            except:
                continue

        return matricole

    def _find_scrollable_table(self):
        """
        Find the scrollable container that wraps the Allievi table.
        Returns the WebElement, or None if not found.
        """
        container_xpaths = [
            "//div[contains(@id, 'learner') and contains(@class, 'AFListView')]",
            "//table[contains(@summary, 'llievi')]/ancestor::div"
            "[contains(@class, 'AFListView')][1]",
            "//table[contains(@summary, 'llievi')]/ancestor::div"
            "[contains(@class, 'af_table_data-region')][1]",
            # Generic fallback: any scrollable ancestor of the table
            "//table[contains(@summary, 'llievi')]/ancestor::div"
            "[contains(@style, 'overflow')][1]",
        ]

        for xpath in container_xpaths:
            try:
                elements = self.driver.find_elements(By.XPATH, xpath)
                if elements:
                    return elements[0]
            except:
                continue

        return None

    def _try_maximize_page_size(self):
        """
        Best-effort attempt to maximize rows shown per page.
        Looks for common Oracle patterns: 'Visualizza tutto' link or page size
        dropdown. Silently returns False if neither exists.
        """
        # Pattern 1: "Show all" / "Visualizza tutto" link
        show_all_xpaths = [
            "//a[normalize-space(.)='Visualizza tutto']",
            "//a[normalize-space(.)='Mostra tutto']",
            "//a[normalize-space(.)='Show all']",
            "//button[normalize-space(.)='Visualizza tutto']",
        ]

        for xpath in show_all_xpaths:
            try:
                elem = WebDriverWait(self.driver, 2).until(
                    EC.element_to_be_clickable((By.XPATH, xpath)))
                elem.click()
                print("   ✅ Clicked 'Visualizza tutto'")
                time.sleep(2)
                return True
            except:
                continue

        # Pattern 2: Page size dropdown — pick the largest option
        try:
            from selenium.webdriver.support.ui import Select
            select_elem = self.driver.find_element(
                By.XPATH,
                "//select[contains(@id, 'pageSize') or contains(@id, 'rowsPerPage')]")
            select = Select(select_elem)
            numeric_options = [
                (int(o.text), o.text) for o in select.options
                if o.text.strip().isdigit()
            ]
            if numeric_options:
                max_size = max(numeric_options)[1]
                select.select_by_visible_text(max_size)
                print(f"   ✅ Set page size to {max_size}")
                time.sleep(2)
                return True
        except:
            pass

        return False

    def _refresh_and_collect_students(self, expected_matricole,
                                      max_attempts=5, wait_between=5):
        """
        Click 'Tutto' to refresh the Allievi list, read all visible matricole,
        and check which expected ones are present. Repeats up to max_attempts
        if not all are found yet (Oracle may need time to process).

        Returns: {'found': [...], 'not_found': [...], 'total_visible': N}
        """
        expected_set = set(str(m).strip() for m in expected_matricole)
        found = set()
        total_visible = 0

        for attempt in range(1, max_attempts + 1):
            try:
                automation_lock.heartbeat(
                    step=f"verifica allievi (tentativo {attempt}/{max_attempts})")
            except Exception:
                pass
            print(f"\n   Refresh {attempt}/{max_attempts}...")

            try:
                # Wait for overlay to clear
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.invisibility_of_element_located(
                            (By.CLASS_NAME, "AFBlockingGlassPane")))
                except:
                    pass

                # Open Stato dropdown → click "Tutto"
                stato_dropdown = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, STUDENT_STATUS_DROPDOWN)))
                stato_dropdown.click()
                time.sleep(1)

                tutto = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, STUDENT_STATUS_TUTTO)))
                tutto.click()
                print("   ✅ Selected 'Tutto'")
                time.sleep(1)

                # ★ CRITICAL: click Cerca to APPLY the filter
                try:
                    cerca_btn = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable(
                            (By.XPATH, STUDENT_CERCA_BUTTON)))
                    cerca_btn.click()
                    print("   ✅ Clicked Cerca to apply filter")
                except Exception as e:
                    print(f"   ⚠️ Cerca click failed (may auto-apply): {e}")

                # Wait for list to reload after Cerca
                try:
                    WebDriverWait(self.driver, 15).until(
                        EC.invisibility_of_element_located(
                            (By.CLASS_NAME, "AFBlockingGlassPane")))
                except:
                    pass
                time.sleep(wait_between)
            except Exception as e:
                print(f"   ⚠️ Filter refresh failed: {e}")

            # Read visible matricole and accumulate across attempts
            visible = self._read_all_visible_matricole()
            total_visible = len(visible)
            found.update(visible)

            matched = len(found & expected_set)
            print(f"   Visible: {total_visible} | "
                  f"Matched: {matched}/{len(expected_set)}")

            # All expected found → stop early
            if expected_set.issubset(found):
                print(f"   ✅ All {len(expected_set)} students found!")
                break

        return {
            'found': sorted(found & expected_set),
            'not_found': sorted(expected_set - found),
            'total_visible': total_visible
        }

    def _assign_presenza_for_student(self, person_number: str,
                                     stato: str = "Completato") -> bool:
        """
        Assign presence (assegnazione presenza) for a single student.

        Assumes already on the edition detail page with the student visible
        in the Allievi tab.

        Pipeline:
        1. Find student by person_number in Allievi tab
        2. Click "Gestisci attività"
        3. For each activity row:
           - Read "Data attività" (read-only)
           - Copy it into "Data completamento"
           - Select stato (Completato / Esente / Non passato)
        4. Click "Salva e chiudi"

        Args:
            person_number: The person number to find
            stato: "Completato", "Esente", or "Non passato"

        Returns:
            True if successful, False otherwise
        """
        try:
            print(f"\n   Processing presenza for person: {person_number}")

            # ─────────────────────────────────────────────────────────
            # STEP 1: Find the student row by person number
            # ─────────────────────────────────────────────────────────
            print("   Step 1: Finding student in Allievi list...")

            # Wait for page to stabilize
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.invisibility_of_element_located(
                        (By.CLASS_NAME, "AFBlockingGlassPane")))
            except:
                pass
            time.sleep(1)

            # Find the row containing this person number
            # Oracle shows person number as text in the row
            student_row_xpath = (
                f"//tr[.//td[normalize-space(.)='{person_number}'] or "
                f".//span[normalize-space(.)='{person_number}']]"
            )

            try:
                student_row = WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located(
                        (By.XPATH, student_row_xpath)))
                print(f"   ✅ Found student row for: {person_number}")
            except TimeoutException:
                print(f"   ❌ Student '{person_number}' not found in Allievi list")
                return False

            # Click the row to select it (Oracle often requires row selection
            # before action buttons become active)
            try:
                student_row.click()
                time.sleep(1)
                print("   ✅ Clicked student row to select it")
            except:
                self.driver.execute_script(
                    "arguments[0].click();", student_row)
                time.sleep(1)

            # ─────────────────────────────────────────────────────────
            # STEP 2: Click "Gestisci attività" button
            # ─────────────────────────────────────────────────────────
            print("   Step 2: Clicking 'Gestisci attività'...")

            try:
                WebDriverWait(self.driver, 5).until(
                    EC.invisibility_of_element_located(
                        (By.CLASS_NAME, "AFBlockingGlassPane")))
            except:
                pass

            gestisci_btn = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable(
                    (By.XPATH, PRESENZA_GESTISCI_BTN)))

            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", gestisci_btn)
            time.sleep(0.5)

            try:
                gestisci_btn.click()
            except:
                self.driver.execute_script("arguments[0].click();", gestisci_btn)

            print("   ✅ Clicked 'Gestisci attività'")
            time.sleep(3)
            self._pause_for_visual_check()

            # Wait for activity table to load
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.invisibility_of_element_located(
                        (By.CLASS_NAME, "AFBlockingGlassPane")))
            except:
                pass
            time.sleep(2)

            # ─────────────────────────────────────────────────────────
            # STEP 3: Process each activity row
            # ─────────────────────────────────────────────────────────
            print("   Step 3: Processing activity rows...")

            # Find all activity rows in the table
            activity_rows_xpath = (
                '//*[@id="_FOpt1:_FOr1:0:_FONSr2:0:MAnt2:2:'
                'clDtSp1:UPsp1:r11:1:r6:0:sp1:t1::db"]/table/tbody/tr'
            )

            try:
                activity_rows = WebDriverWait(self.driver, 15).until(
                    EC.presence_of_all_elements_located(
                        (By.XPATH, activity_rows_xpath)))
                print(f"   Found {len(activity_rows)} activity rows")
            except TimeoutException:
                print("   ❌ Could not find activity rows table")
                return False


            # Determine the display text based on stato
            stato_clean = stato.strip().lower()
            if stato_clean in ['completato', 'completed', 'c']:
                stato_display = "Completato"
            elif stato_clean in ['esente', 'exempt', 'e']:
                stato_display = "Esente"
            else:  # non passato / failed
                stato_display = "Non passato"

            # Process each row
            for row_idx, row in enumerate(activity_rows):
                try:
                    automation_lock.heartbeat(
                        step=f"riga attività {row_idx + 1}/{len(activity_rows)}")
                except Exception:
                    pass
                print(f"\n   Processing activity row {row_idx + 1}...")

                try:
                    # ── Read "Data attività" (column 4, read-only) ──
                    data_attivita = ""
                    try:
                        # The date is inside a span with class x2b inside td[4]
                        date_span = row.find_element(
                            By.XPATH,
                            './/td[4]//span[contains(@class, "x2b")]')
                        data_attivita = date_span.text.strip()
                        if not data_attivita:
                            # Try reading the inner content span
                            date_span = row.find_element(
                                By.XPATH,
                                './/td[4]//*[contains(@id, "::content")]')
                            data_attivita = date_span.text.strip()
                        print(f"      Data attività: {data_attivita}")
                    except Exception as e:
                        print(f"      ⚠️ Could not read Data attività: {e}")
                        continue

                    if not data_attivita:
                        print(f"      ⚠️ Empty date for row {row_idx + 1}, skipping")
                        continue

                    # ═══════════════════════════════════════════════════════
                    # Skip rows where activity date is in the future.
                    # Oracle rejects Data completamento greater than today
                    # ("attività non ancora avvenuta")
                    # ═══════════════════════════════════════════════════════
                    try:
                        activity_date_obj = datetime.strptime(
                            data_attivita, "%d/%m/%Y").date()
                        today = date.today()
                        if activity_date_obj > today:
                            print(f"      ⚠️ Activity date {data_attivita} is in the future, "
                                  f"skipping row (attività non ancora avvenuta)")
                            continue
                    except ValueError:
                        print(f"      ⚠️ Could not parse date '{data_attivita}', "
                              f"proceeding anyway")

                    # ── Fill "Data completamento" (column 5, editable input) ──
                    # Oracle creates input fields lazily — retry until it's there
                    data_comp_input = None
                    for input_attempt in range(5):
                        try:
                            data_comp_input = row.find_element(
                                By.XPATH,
                                './/td[5]//input[contains(@id, "::content")]')
                            if data_comp_input.is_displayed():
                                break
                            data_comp_input = None
                        except:
                            pass
                        time.sleep(1)

                    if not data_comp_input:
                        print(f"      ⚠️ Data completamento input not found "
                              f"after 5 attempts, skipping row")
                        continue

                    try:
                        data_comp_input.click()
                        time.sleep(0.3)
                        data_comp_input.clear()

                        self.driver.execute_script(
                            "arguments[0].value = arguments[1];",
                            data_comp_input, data_attivita)
                        data_comp_input.send_keys(Keys.TAB)
                        time.sleep(1)

                        print(f"      ✅ Data completamento set to: {data_attivita}")

                        try:
                            WebDriverWait(self.driver, 5).until(
                                EC.invisibility_of_element_located(
                                    (By.CLASS_NAME, "AFBlockingGlassPane")))
                        except:
                            pass

                    except Exception as e:
                        print(f"      ⚠️ Could not fill Data completamento: {e}")
                        continue

                    # ── Select Stato completamento dropdown ──
                    try:
                        stato_dropdown = row.find_element(
                            By.XPATH,
                            './/td[6]//a[contains(@id, "::drop")]')

                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({block: 'center'});",
                            stato_dropdown)
                        time.sleep(0.3)

                        try:
                            stato_dropdown.click()
                        except:
                            self.driver.execute_script(
                                "arguments[0].click();", stato_dropdown)

                        time.sleep(1)
                        self._pause_for_visual_check()

                        # Click the option using the robust JS+keyboard helper
                        clicked = self._click_stato_option(stato_display)
                        if not clicked:
                            print(f"      ❌ Could not set Stato to: {stato_display}")

                        time.sleep(1)

                        # Wait for overlay
                        try:
                            WebDriverWait(self.driver, 5).until(
                                EC.invisibility_of_element_located(
                                    (By.CLASS_NAME, "AFBlockingGlassPane")))
                        except:
                            pass

                    except Exception as e:
                        print(f"      ⚠️ Could not set Stato: {e}")


                    time.sleep(1)
                    self._pause_for_visual_check()

                except Exception as row_err:
                    print(f"      ❌ Error processing row {row_idx + 1}: {row_err}")
                    continue

            # ─────────────────────────────────────────────────────────
            # STEP 4: Click "Salva e chiudi"
            # ─────────────────────────────────────────────────────────
            print("\n   Step 4: Clicking 'Salva e chiudi'...")

            try:
                salva_btn = WebDriverWait(self.driver, 15).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, PRESENZA_SALVA_CHIUDI)))

                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});", salva_btn)
                time.sleep(0.5)

                try:
                    salva_btn.click()
                except:
                    self.driver.execute_script("arguments[0].click();", salva_btn)

                print("   ✅ Clicked 'Salva e chiudi'")

                # ── Wait for the activity panel to fully disappear ──
                # The activity table is only visible when the popup is open.
                # Wait for it to become invisible before returning.
                try:
                    WebDriverWait(self.driver, 20).until(
                        EC.invisibility_of_element_located((
                            By.XPATH,
                            '//*[@id="_FOpt1:_FOr1:0:_FONSr2:0:MAnt2:2:'
                            'clDtSp1:UPsp1:r11:1:r6:0:sp1:t1::db"]'
                        )))
                    print("   ✅ Activity panel closed")
                except:
                    print("   ⚠️ Could not confirm panel closed, waiting extra...")
                    time.sleep(5)

                # ── Wait for blocking overlay ──
                try:
                    WebDriverWait(self.driver, 15).until(
                        EC.invisibility_of_element_located(
                            (By.CLASS_NAME, "AFBlockingGlassPane")))
                except:
                    pass

                # ── Extra stabilization wait ──
                # Oracle needs time to refresh the Allievi table
                time.sleep(3)

                print(f"   ✅ Presenza saved for student {person_number}")
                return True

            except Exception as e:
                print(f"   ❌ Could not click 'Salva e chiudi': {e}")
                return False

        except Exception as e:
            print(f"\n❌ ERROR in _assign_presenza_for_student: {e}")
            import traceback
            traceback.print_exc()
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                self.driver.save_screenshot(f"error_presenza_{timestamp}.png")
            except:
                pass
            return False

    def assign_presenza_batch(self, edition_code: str,
                              students: list,
                              stato: str = "Completato") -> dict:
        """
        Assign presence using keyword search per student.
        Each student is isolated to its own row before processing,
        so Oracle never has more than one row to manage.
        """
        results = {
            'success': [],
            'failed': [],
            'total': len(students)
        }

        print(f"\n{'=' * 60}")
        print(f"PRESENZA: Processing {len(students)} students "
              f"for '{edition_code}'")
        print(f"{'=' * 60}")

        # === SETUP: Click Allievi tab ===
        try:
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.invisibility_of_element_located(
                        (By.CLASS_NAME, "AFBlockingGlassPane")))
            except:
                pass
            time.sleep(2)

            allievi_tab = self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, STUDENT_ALLIEVI_TAB)))
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});",
                allievi_tab)
            time.sleep(0.5)
            try:
                allievi_tab.click()
            except:
                self.driver.execute_script(
                    "arguments[0].click();", allievi_tab)
            print("✅ On Allievi tab")
            time.sleep(3)
        except Exception as e:
            print(f"❌ Could not open Allievi tab: {e}")
            results['failed'] = list(students)
            return results

        # === Apply Tutto filter once at start ===
        self._apply_tutto_filter()

        # === PROCESS EACH STUDENT (with isolation via keyword search) ===
        for idx, person_number in enumerate(students):
            try:
                automation_lock.heartbeat(
                    step=f"presenza allievo {idx + 1}/{len(students)} "
                         f"({person_number})")
            except Exception:
                pass
            print(f"\n[{idx + 1}/{len(students)}] Student: {person_number}")

            try:
                # Isolate this student by keyword search
                if not self._isolate_student_by_search(person_number):
                    print(f"   ❌ Could not isolate student {person_number}")
                    results['failed'].append(person_number)
                    continue

                # Process this single isolated student
                success = self._assign_presenza_for_student(
                    person_number, stato)

                if success:
                    results['success'].append(person_number)
                else:
                    results['failed'].append(person_number)

                # Reset search for next student
                self._reset_student_search()

                # Extra wait for Oracle to settle before next iteration
                time.sleep(3)

            except Exception as e:
                print(f"   ❌ Error processing {person_number}: {e}")
                results['failed'].append(person_number)

                # Try to recover for the next iteration
                try:
                    self._reset_student_search()
                    time.sleep(2)
                except:
                    pass

        print(f"\n{'=' * 60}")
        print(f"PRESENZA COMPLETE: "
              f"{len(results['success'])}/{results['total']} successful")
        print(f"{'=' * 60}")
        return results

    def _isolate_student_by_search(self, person_number: str,
                                   initial_wait: float = 2.0,
                                   max_retries: int = 6,
                                   retry_wait: float = 2.0) -> bool:
        """
        Use keyword search to filter Allievi list to just one student.
        Re-applies Tutto stato filter and retries the row check multiple
        times to handle Oracle's variable response time.
        """
        try:
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.invisibility_of_element_located(
                        (By.CLASS_NAME, "AFBlockingGlassPane")))
            except:
                pass

            # Step 1: Re-apply Tutto stato filter
            try:
                stato_dropdown = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, STUDENT_STATUS_DROPDOWN)))
                stato_dropdown.click()
                time.sleep(0.5)
                tutto = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, STUDENT_STATUS_TUTTO)))
                tutto.click()
                time.sleep(0.5)
            except Exception as e:
                print(f"   ⚠️ Could not re-apply Tutto: {e}")

            # Step 2: Enter keyword
            keyword_input = None
            for xpath in [STUDENT_KEYWORD_INPUT_1, STUDENT_KEYWORD_INPUT_2]:
                try:
                    keyword_input = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, xpath)))
                    break
                except:
                    continue

            if not keyword_input:
                print(f"   ⚠️ Keyword input not found")
                return False

            keyword_input.clear()
            keyword_input.send_keys(person_number)

            # Step 3: Click Cerca
            cerca_btn = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable(
                    (By.XPATH, STUDENT_CERCA_BUTTON)))
            cerca_btn.click()

            # Initial wait
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.invisibility_of_element_located(
                        (By.CLASS_NAME, "AFBlockingGlassPane")))
            except:
                pass
            time.sleep(initial_wait)

            # ★ Step 4: Retry-based row check
            # Oracle's response time varies — keep checking up to max_retries
            for attempt in range(1, max_retries + 1):
                row = self._find_row_for_matricola(person_number)
                if row:
                    if attempt > 1:
                        print(f"   ✅ Isolated student {person_number} "
                              f"(attempt {attempt})")
                    else:
                        print(f"   ✅ Isolated student {person_number}")
                    return True

                if attempt < max_retries:
                    # Check if overlay is still showing
                    try:
                        overlays = self.driver.find_elements(
                            By.CLASS_NAME, "AFBlockingGlassPane")
                        overlay_active = any(
                            e.is_displayed() for e in overlays)
                    except:
                        overlay_active = False

                    if overlay_active:
                        print(f"   ⏳ Oracle still loading "
                              f"(attempt {attempt}/{max_retries})...")
                        try:
                            WebDriverWait(self.driver, 5).until(
                                EC.invisibility_of_element_located(
                                    (By.CLASS_NAME, "AFBlockingGlassPane")))
                        except:
                            pass
                    else:
                        print(f"   ⏳ Row not visible yet "
                              f"(attempt {attempt}/{max_retries}), waiting...")

                    time.sleep(retry_wait)

            print(f"   ⚠️ Search didn't return row for {person_number} "
                  f"after {max_retries} attempts")
            return False

        except Exception as e:
            print(f"   ⚠️ Search isolation failed: {e}")
            return False

    def _reset_student_search(self):
        """Reset the Allievi search filter (click Reimposta button)."""
        try:
            reset_btn = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable(
                    (By.XPATH, STUDENT_RESET_BUTTON)))
            reset_btn.click()
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.invisibility_of_element_located(
                        (By.CLASS_NAME, "AFBlockingGlassPane")))
            except:
                pass
            time.sleep(2)
        except Exception as e:
            # Fallback: just clear the search box
            try:
                keyword_input = self.driver.find_element(
                    By.XPATH, STUDENT_KEYWORD_INPUT_1)
                keyword_input.clear()
            except:
                pass

    def _verify_students_in_edition(self, edition_code, expected_matricole):
        """Verify students exist by reading the whole Allievi table once."""
        print(f"\n   Verifying {len(expected_matricole)} students "
              f"for edition '{edition_code}'...")

        # Click Allievi tab
        try:
            allievi_tab = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, STUDENT_ALLIEVI_TAB)))
            allievi_tab.click()
            time.sleep(3)
        except Exception as e:
            print(f"   ❌ Could not click Allievi tab: {e}")
            return {
                'found': [],
                'not_found': list(expected_matricole),
                'total_in_system': 0,
                'success': False
            }

        # Refresh and collect
        result = self._refresh_and_collect_students(
            expected_matricole=expected_matricole,
            max_attempts=5,
            wait_between=5
        )

        return {
            'found': result['found'],
            'not_found': result['not_found'],
            'total_in_system': len(result['found']),
            'success': True
        }

    def _find_row_for_matricola(self, matricola: str):
        """Find a visible row containing a specific matricola. Returns row element or None."""
        xpath_options = [
            f"//tr[.//td[normalize-space(.)='{matricola}']]",
            f"//tr[.//span[normalize-space(.)='{matricola}']]",
        ]
        for xpath in xpath_options:
            try:
                row = self.driver.find_element(By.XPATH, xpath)
                if row.is_displayed():
                    return row
            except:
                continue
        return None

    def _scroll_to_find_student_row(self, matricola: str,
                                    max_iterations: int = 80):
        """
        Scroll the Allievi table looking for a specific student's row.
        Returns the row WebElement (scrolled into view) or None.
        """
        # First: maybe it's already in viewport
        row = self._find_row_for_matricola(matricola)
        if row:
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", row)
            time.sleep(0.5)
            return row

        container = self._find_scrollable_table()

        # Reset to top, then scroll down looking for the row
        if container:
            try:
                self.driver.execute_script(
                    "arguments[0].scrollTop = 0;", container)
                time.sleep(1)
            except:
                pass

        for i in range(max_iterations):
            row = self._find_row_for_matricola(matricola)
            if row:
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});", row)
                time.sleep(0.5)
                print(f"      ✅ Row for {matricola} found after {i + 1} scrolls")
                return row

            # Scroll down 200px
            try:
                if container:
                    self.driver.execute_script(
                        "arguments[0].scrollTop += 200;", container)
                else:
                    self.driver.execute_script("window.scrollBy(0, 200);")
            except:
                pass

            try:
                WebDriverWait(self.driver, 2).until(
                    EC.invisibility_of_element_located(
                        (By.CLASS_NAME, "AFBlockingGlassPane")))
            except:
                pass
            time.sleep(1)

        print(f"      ❌ Row for {matricola} NOT found after "
              f"{max_iterations} scrolls")
        return None

    def _apply_tutto_filter(self) -> bool:
        """Apply 'Tutto' stato filter + Cerca to load all students."""
        try:
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.invisibility_of_element_located(
                        (By.CLASS_NAME, "AFBlockingGlassPane")))
            except:
                pass

            stato_dropdown = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, STUDENT_STATUS_DROPDOWN)))
            stato_dropdown.click()
            time.sleep(1)

            tutto = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, STUDENT_STATUS_TUTTO)))
            tutto.click()
            print("   ✅ Selected 'Tutto'")
            time.sleep(1)

            try:
                cerca_btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, STUDENT_CERCA_BUTTON)))
                cerca_btn.click()
                print("   ✅ Applied filter (Cerca)")
            except:
                print("   ⚠️ Cerca click skipped (filter may auto-apply)")

            try:
                WebDriverWait(self.driver, 15).until(
                    EC.invisibility_of_element_located(
                        (By.CLASS_NAME, "AFBlockingGlassPane")))
            except:
                pass
            time.sleep(2)
            return True
        except Exception as e:
            print(f"   ⚠️ Tutto filter setup failed: {e}")
            return False

    def _click_stato_option(self, stato_display: str) -> bool:
        """
        Click a Stato dropdown option using two strategies:
        1. JavaScript: find option by text, dispatch full ADF mouse sequence
        2. Keyboard: type first letter + Enter (works on most Oracle dropdowns)
        """
        # Strategy 1: JavaScript with full mouse event sequence
        js = """
        var targetText = arguments[0];
        var options = document.querySelectorAll('li[role="option"]');
        for (var i = 0; i < options.length; i++) {
            var opt = options[i];
            var text = opt.textContent.trim();
            if (text === targetText) {
                var rect = opt.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                    opt.scrollIntoView({block: 'center'});
                    var eventInit = {
                        bubbles: true, cancelable: true, view: window,
                        clientX: rect.left + rect.width/2,
                        clientY: rect.top + rect.height/2
                    };
                    // ADF listens for the full sequence — not just click
                    opt.dispatchEvent(new MouseEvent('mousedown', eventInit));
                    opt.dispatchEvent(new MouseEvent('mouseup', eventInit));
                    opt.dispatchEvent(new MouseEvent('click', eventInit));
                    return true;
                }
            }
        }
        return false;
        """
        try:
            clicked = self.driver.execute_script(js, stato_display)
            if clicked:
                print(f"      ✅ Stato set via JS: {stato_display}")
                time.sleep(1)
                return True
        except Exception as e:
            print(f"      ⚠️ JS click failed: {e}")

        # Strategy 2: Keyboard fallback
        try:
            from selenium.webdriver.common.action_chains import ActionChains
            first_letter = stato_display[0].lower()
            actions = ActionChains(self.driver)
            actions.send_keys(first_letter).pause(0.5)
            actions.send_keys(Keys.ENTER).perform()
            time.sleep(1)
            print(f"      ✅ Stato set via keyboard: {stato_display}")
            return True
        except Exception as e:
            print(f"      ⚠️ Keyboard fallback failed: {e}")

        return False

    def close(self):
        """Close the WebDriver and clean up resources."""
        try:
            if self.driver:
                self.driver.quit()
                print("Model: Closing driver.")
        except Exception as e:
            print(f"Model: Error closing driver: {e}")