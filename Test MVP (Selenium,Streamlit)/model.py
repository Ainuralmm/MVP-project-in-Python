# model.py

# --- IMPORTS ---
import time
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys


#This is a special function called the constructor.
# It automatically runs once when you first create a robot from the blueprint.
# Its job is to do all the initial setup.
class OracleAutomator:
    # This class encapsulates all the browser automation steps.
    def __init__(self, driver_path):
        # The constructor initializes the web driver.
        # It's called once when we create an instance of this class.
        service = Service(executable_path=driver_path)
        self.driver = webdriver.Edge(service=service)
        self.wait = WebDriverWait(self.driver, 40)
        print("Model: WebDriver initialized.")

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

    def navigate_to_course_creation(self):
        #navigation and search part
        try:
            miogruppodilavoro = self.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="groupNode_workforce_management"]')))
            miogruppodilavoro.click()
            print("Model: Clicked 'Mio gruppo di lavoro'")

            apprendimento = self.wait.until(EC.presence_of_element_located((By.ID, 'WLF_FUSE_LEARN_ADMIN')))
            apprendimento.click()
            print("Model: Clicked 'Apprendimento'")

            corsi = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//a[@title="Corsi" and text()="Corsi"]')))
            corsi.click()
            print("Model: Clicked 'Corsi'")
            return True
        except Exception as e:
            print(f"Model: Error during navigation to course creation: {e}")
            return False

    def create_course(self,course_details):
        #main method that creates the course
        try:
            course_name = course_details['title']
            print(f'Model: Starting course creation for "{course_name}"')

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

        except Exception as e:
            print(f"Model: An error occurred during course creation: {e}")
            return f"Error: An error occurred during automation. Check the console for details."



    def close_driver(self):
        print("Model: Closing driver.")
        self.driver.quit()