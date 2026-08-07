import sqlite3
conn = sqlite3.connect('dajudali.db')
# 更新知识库
conn.execute("UPDATE knowledge_base SET question = REPLACE(question, '大橘', '海江'), answer = REPLACE(answer, '大橘', '海江'), keywords = REPLACE(keywords, '大橘', '海江') WHERE tenant_id = 1")
conn.execute("UPDATE knowledge_base SET answer = REPLACE(answer, '小橘', '小江') WHERE tenant_id = 1")
print(f"Knowledge base updated, {conn.total_changes} changes")
# 更新 settings
conn.execute("UPDATE settings SET value = REPLACE(value, '大橘邻里', '海江新天地')")
conn.execute("UPDATE settings SET value = REPLACE(value, '大橘', '海江') WHERE value IS NOT NULL")
conn.commit()
conn.close()
print("DB done")
