import sqlite3
conn = sqlite3.connect('/opt/dajudali/dajudali.db')
# Add columns if not exist
for col, default in [('wx_openid', ''), ('headimgurl', ''), ('discount', '98')]:
    try:
        conn.execute(f'ALTER TABLE users ADD COLUMN {col} TEXT DEFAULT "{default}"')
        print(f'Added column {col}')
    except sqlite3.OperationalError as e:
        print(f'Skipped {col}: {e}')
conn.commit()
print('Done')
conn.close()
