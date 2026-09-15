import sqlite3


def create_database():

    connection = sqlite3.connect("health_data.db")
    cursor = connection.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            age INTEGER,
            gender TEXT,
            height REAL,
            weight REAL,
            bmi REAL
        )
    """)

    # Daily health table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_health (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            water REAL,
            exercise INTEGER,
            sleep REAL,
            steps INTEGER DEFAULT 0,
            date TEXT
        )
    """)

    # Meals table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS meals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            meal_type TEXT,
            food_name TEXT,
            quantity TEXT,
            calories INTEGER,
            date TEXT
        )
    """)

    # Add steps column to old database if it does not exist
    try:
        cursor.execute(
            "ALTER TABLE daily_health ADD COLUMN steps INTEGER DEFAULT 0"
        )
    except sqlite3.OperationalError:
        pass

    connection.commit()
    connection.close()


if __name__ == "__main__":
    create_database()
    print("Database created/updated successfully!")