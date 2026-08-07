import sqlite3
conn = sqlite3.connect('dajudali.db')
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM knowledge_base")
print(c.fetchone()[0])
conn.close()
