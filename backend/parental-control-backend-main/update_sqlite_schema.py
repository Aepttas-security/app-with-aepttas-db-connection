import sqlite3
import datetime

def update_db():
    conn = sqlite3.connect("parentcontrol.db")
    cursor = conn.cursor()

    # Helper function to safely add column if missing
    def add_column_if_missing(table_name, col_name, col_type):
        cursor.execute(f"PRAGMA table_info([{table_name}])")
        columns = [info[1] for info in cursor.fetchall()]
        if col_name not in columns:
            print(f"Adding column '{col_name}' ({col_type}) to table '{table_name}'...")
            cursor.execute(f"ALTER TABLE [{table_name}] ADD COLUMN {col_name} {col_type};")

    # 1. apt_device_pairing_b
    add_column_if_missing("apt_device_pairing_b", "child_id", "INTEGER")
    add_column_if_missing("apt_device_pairing_b", "pairing_uuid", "TEXT")
    add_column_if_missing("apt_device_pairing_b", "device_identifier", "TEXT")
    add_column_if_missing("apt_device_pairing_b", "paired_date", "DATETIME")
    add_column_if_missing("apt_device_pairing_b", "is_active", "BOOLEAN DEFAULT 1")
    add_column_if_missing("apt_device_pairing_b", "last_updated_by", "TEXT DEFAULT 'SYSTEM'")
    add_column_if_missing("apt_device_pairing_b", "last_updated_date", "DATETIME")
    add_column_if_missing("apt_device_pairing_b", "last_dml_by", "TEXT DEFAULT 'SYSTEM'")
    add_column_if_missing("apt_device_pairing_b", "last_dml_date", "DATETIME")
    add_column_if_missing("apt_device_pairing_b", "last_ddl_by", "TEXT DEFAULT 'SYSTEM'")
    add_column_if_missing("apt_device_pairing_b", "last_ddl_date", "DATETIME")

    # 2. apt_screen_time_b
    add_column_if_missing("apt_screen_time_b", "record_date", "DATE")

    # 3. apt_child_location_b
    add_column_if_missing("apt_child_location_b", "pairing_id", "INTEGER")

    # 4. apt_sos_alerts_b
    add_column_if_missing("apt_sos_alerts_b", "sos_alert_uuid", "TEXT")
    add_column_if_missing("apt_sos_alerts_b", "child_id", "INTEGER")

    # 5. apt_children_b
    add_column_if_missing("apt_children_b", "child_id", "INTEGER")
    add_column_if_missing("apt_children_b", "date_of_birth", "DATE")

    # 6. daily_app_usage_reports table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_app_usage_reports (
            report_id INTEGER PRIMARY KEY AUTOINCREMENT,
            child_id INTEGER,
            app_name TEXT,
            category TEXT,
            duration_minutes INTEGER,
            usage_date DATE
        );
    """)

    # 7. recent_blocked_activities table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recent_blocked_activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            child_id INTEGER,
            app_name TEXT,
            blocked_time DATETIME
        );
    """)

    # 8. limit_breaches_summary table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS limit_breaches_summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            child_id INTEGER,
            breach_type TEXT,
            breach_time DATETIME
        );
    """)

    # 9. apt_sos_preferences_b table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS apt_sos_preferences_b (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            child_id INTEGER,
            child_uuid TEXT,
            emergency_contacts TEXT,
            auto_dial BOOLEAN DEFAULT 0,
            sound_alarm BOOLEAN DEFAULT 1,
            notify_guardians BOOLEAN DEFAULT 1,
            created_date DATETIME,
            last_updated_date DATETIME
        );
    """)

    # 10. apt_caller_intel_blocked_b table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS apt_caller_intel_blocked_b (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            child_id INTEGER,
            phone_number TEXT NOT NULL,
            caller_name TEXT,
            block_reason TEXT,
            date_added TEXT
        );
    """)

    # 11. apt_caller_intel_reports_b table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS apt_caller_intel_reports_b (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            child_id INTEGER,
            phone_number TEXT NOT NULL,
            report_type TEXT,
            description TEXT,
            timestamp TEXT
        );
    """)

    # 12. apt_caller_intel_settings_b table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS apt_caller_intel_settings_b (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            child_id INTEGER UNIQUE,
            auto_block_enabled BOOLEAN DEFAULT 1,
            notifications_enabled BOOLEAN DEFAULT 1
        );
    """)

    # 13. apt_blacklisted_urls_b table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS apt_blacklisted_urls_b (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            child_id INTEGER,
            url TEXT NOT NULL,
            added_date DATETIME
        );
    """)

    # 14. apt_scans_b table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS apt_scans_b (
            scan_id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT NOT NULL,
            package_name TEXT,
            threat_level TEXT,
            risk_score INTEGER,
            status TEXT,
            created_at DATETIME
        );
    """)

    # 15. apt_quarantine_b table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS apt_quarantine_b (
            quarantine_id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_id INTEGER,
            file_name TEXT NOT NULL,
            package_name TEXT,
            threat_level TEXT,
            quarantined_at DATETIME
        );
    """)

    # 16. apt_installed_apps_b table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS apt_installed_apps_b (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            child_id INTEGER,
            package_name TEXT,
            app_name TEXT,
            category TEXT,
            is_blocked BOOLEAN DEFAULT 0,
            daily_limit_minutes INTEGER DEFAULT -1,
            is_always_allowed BOOLEAN DEFAULT 0,
            minutes_used_today INTEGER DEFAULT 0,
            last_reset_date DATE,
            UNIQUE(child_id, package_name)
        );
    """)

    conn.commit()
    conn.close()
    print("[SUCCESS] SQLite database schema updated successfully!")


if __name__ == "__main__":
    update_db()
