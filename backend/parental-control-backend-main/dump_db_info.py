import sqlite3

def detailed_dump():
    conn = sqlite3.connect('parentcontrol.db')
    cursor = conn.cursor()
    
    tables = [t[0] for t in cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
    print(f"=== ALL TABLES IN DATABASE ({len(tables)}) ===")
    for t in sorted(tables):
        print(f" - {t}")
    print("\n" + "="*60 + "\n")
    
    for t_name in sorted(tables):
        if t_name == "sqlite_sequence":
            continue
        count = cursor.execute(f"SELECT count(*) FROM [{t_name}]").fetchone()[0]
        columns = [col[1] for col in cursor.execute(f"PRAGMA table_info([{t_name}])").fetchall()]
        print(f"TABLE: {t_name} ({count} rows)")
        print(f"COLUMNS: {columns}")
        rows = cursor.execute(f"SELECT * FROM [{t_name}]").fetchall()
        if rows:
            for idx, r in enumerate(rows, 1):
                print(f"  Row {idx}: {r}")
        else:
            print("  (Empty Table)")
        print("-" * 60)

if __name__ == "__main__":
    detailed_dump()
