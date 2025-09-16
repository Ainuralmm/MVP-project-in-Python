# main.py
# This is the main entry point of your application.

from model import OracleAutomator
from view import CourseView
from presenter import CoursePresenter

if __name__ == "__main__":
    # This is the path to your Edge WebDriver. Update it if necessary.
    DRIVER_PATH = "/Users/ainuralmukambetova/PCDocuments/AGSM/edgedriver_mac64_m1/msedgedriver"

    # 1. Create an instance of the Model.
    model = OracleAutomator(driver_path=DRIVER_PATH)

    # 2. Create an instance of the View.
    view = CourseView()

    # 3. Create the Presenter, passing it the model and the view.
    presenter = CoursePresenter(model, view)

    # 4. Start the application by calling the presenter's run method.
    presenter.run()