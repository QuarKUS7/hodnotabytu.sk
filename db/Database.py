import mysql.connector


class Database:
    def __init__(self, log, config=None):

        self.log = log
        self.cnx = mysql.connector.connect(
                host='localhost',
                user='scraper',
                password='password',
                database='zakolko'
            )
        self.cursor = self.cnx.cursor()

    def select_one(self, query, args=()):
        self.cursor.execute(query, args)
        return self.cursor.fetchone()

    def execute(self, query):
        self.cursor.execute(query,)
        self.cnx.commit()
        return self.cursor.rowcount
