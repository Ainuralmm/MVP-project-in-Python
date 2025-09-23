from model import OracleAutomator
from view import CourseView
from presenter import CoursePresenter

if __name__ == "__main__":
    #path of to Edge Webdriver
    DRIVER_PATH = "/Users/ainuralmukambetova/PCDocuments/AGSM/edgedriver_mac64_m1/msedgedriver"

    model = OracleAutomator(driver_path = DRIVER_PATH,
                            debug_mode = True,# pause for visual checks
                            debug_pause = 2, # how long to pause in seconds
                            headless = False)# set to True → browser hidden, False → browser visible
    view = CourseView()
    presenter = CoursePresenter(model,view)

    #start the application
    presenter.run()
