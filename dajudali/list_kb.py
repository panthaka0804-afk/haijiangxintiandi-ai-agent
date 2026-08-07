import sqlite3
conn = sqlite3.connect(r'C:\Users\admin\AppData\Roaming\OpenClawBrowser\openclaw-gateway\.openclaw\workspace\dajudali\dajudali.db')
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT * FROM knowledge_base WHERE tenant_id=1").fetchall()
for r in rows:
    print(f"[{r['id']}] cat={r['category']} | {r['question'][:40]} | {r['answer'][:50]}")
conn.close()
