from app.core.database import get_db_connection

def get_all_skills():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT DISTINCT skill FROM (
            SELECT skill FROM course_skill
            UNION
            SELECT skill FROM ta_skill
        ) s
        ORDER BY skill ASC
    """)
    rows = cursor.fetchall()

    cursor.close()
    conn.close()
    return [r["skill"] for r in rows]
