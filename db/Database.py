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

    def insert(self, query):
        self.cursor.execute(query,)
        self.cnx.commit()
        self.log.info("{} record inserted.".format(self.cursor.rowcount))

