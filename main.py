from model import Model
from presenter import Presenter
from view import TodoList

def main():-> None:
    model = Model()
    presenter = Presenter(model,view)
    view = TodoList()
    presenter.run

if __name__ == '__main__':
    main()



