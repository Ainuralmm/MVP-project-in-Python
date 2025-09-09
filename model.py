import sqlite3

class Model:
    def __init__(self):-> None:
        self.connection = sqlite3.connect('tasks.db')
        self.cursor = self.connection.cursor()
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS tasks (title text)''')

    def add_task(self, title: str) -> None:
        self.cursor.execute('''INSERT INTO tasks VALUES (?)''', (task,))
        self.connection.commit()

    def  delete_task(self, title: str) -> None:
        self.cursor.execute('''DELETE FROM tasks WHERE title=?''', (title,))
        self.connection.commit()

    def get_task(self) ->list [str]:
        tasks: list[str]=[]
        for row in self.cursor.execute('SELECT title from tasks'):
            tasks.append(row[0])
        return tasks

