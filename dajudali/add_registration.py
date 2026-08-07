import sqlite3
conn = sqlite3.connect(r'C:\Users\admin\AppData\Roaming\OpenClawBrowser\openclaw-gateway\.openclaw\workspace\dajudali\dajudali.db')
conn.row_factory = sqlite3.Row

# Add activity registration KB entry
conn.execute("""
INSERT INTO knowledge_base (tenant_id, category, question, answer, keywords, priority)
VALUES (1, 'event', '活动报名入口/怎么报名参加活动', 
'大橘邻里各项活动可通过微信小程序报名：
→ 点击 #小程序://松江大橘邻里/gE9tnxIHejM5syJ 即可进入活动报名页面。
如无法打开，请微信搜索"松江大橘邻里"小程序，或前往1层服务台现场报名。', 
'报名 活动报名 小程序 报名链接', 10)
""")

# Add night school registration KB entry
conn.execute("""
INSERT INTO knowledge_base (tenant_id, category, question, answer, keywords, priority)
VALUES (1, 'event', '夜校怎么报名/夜校报名入口', 
'大橘夜校可通过微信小程序报名：
→ 点击 #小程序://松江大橘邻里/gE9tnxIHejM5syJ 进入课程报名页面，选择您想参加的课程即可。
如无法打开，请微信搜索"松江大橘邻里"小程序，或至1层服务台咨询。', 
'夜校报名 课程报名 夜校', 10)
""")

conn.commit()
conn.close()
print("Done — added 2 KB entries for activity registration")
