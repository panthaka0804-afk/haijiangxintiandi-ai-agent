import sqlite3
conn = sqlite3.connect(r'C:\Users\admin\AppData\Roaming\OpenClawBrowser\openclaw-gateway\.openclaw\workspace\dajudali\dajudali.db')
conn.row_factory = sqlite3.Row

# Update the event registration KB entries with clickable links
conn.execute("""
UPDATE knowledge_base SET answer = 
'各项活动可通过小程序报名：点这里 → <a href="#小程序://松江大橘邻里/gE9tnxIHejM5syJ">打开报名页面</a>

如无法打开，请微信搜索"松江大橘邻里"小程序，或前往1层服务台现场报名。'
WHERE question LIKE '%活动报名%' AND tenant_id=1
""")

conn.execute("""
UPDATE knowledge_base SET answer = 
'大橘夜校可通过小程序报名：点这里 → <a href="#小程序://松江大橘邻里/gE9tnxIHejM5syJ">打开课程报名</a>

选择想参加的课程即可。也可微信搜索"松江大橘邻里"小程序，或至1层服务台咨询。'
WHERE question LIKE '%夜校怎么报名%' AND tenant_id=1
""")

conn.commit()
conn.close()
print("Done — updated KB answers with clickable links")
