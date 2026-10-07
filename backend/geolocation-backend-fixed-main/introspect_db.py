import os
from urllib.parse import urlparse
import psycopg2
from dotenv import load_dotenv

# Load .env from project root
load_dotenv('.env')
url = os.getenv('DATABASE_URL')
print('DATABASE_URL', url)
if not url:
    raise SystemExit('No DATABASE_URL')
parsed = urlparse(url)
conn = psycopg2.connect(host=parsed.hostname, port=parsed.port, user=parsed.username, password=parsed.password, dbname=parsed.path.lstrip('/'), options='-c search_path=apt')
cur = conn.cursor()
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='apt';")
print('Tables in apt schema:', cur.fetchall())
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='apt' AND table_name='apt_users_b';")
print('apt_users_b columns:', cur.fetchall())
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='apt' AND table_name='apt_programs_b';")
print('apt_programs_b columns:', cur.fetchall())
conn.close()
