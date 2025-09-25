from model import OracleAutomator
from view import CourseView
from presenter import CoursePresenter

if __name__ == "__main__":
    #path of to Edge Webdriver
    DRIVER_PATH = "/Users/ainuralmukambetova/PCDocuments/AGSM/edgedriver_mac64_m1/msedgedriver"

    view = CourseView()
    headless, debug_mode, debug_pause = view.get_user_options()

    course_details = view.render_form()

    if course_details:

        model = OracleAutomator(driver_path = DRIVER_PATH,
                            debug_mode = debug_mode, # pause for visual checks;  debug_mode=False -> all the pauses will be disabled instantly
                            debug_pause = debug_pause, # how long to pause in seconds
                            headless = headless)# set to True → browser hidden, False → browser visible

        presenter = CoursePresenter(model,view)

        #start the application
        presenter.run(course_details)
