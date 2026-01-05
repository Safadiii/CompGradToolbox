from app.core.database import get_db_connection

def onboard_ta(data):
    """
    Updates the TA stub created during finish_registration and completes onboarding.
    (No new TA row is inserted here.)
    """

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 1) Validate user and fetch the existing stub ta_id
        cursor.execute(
            """
            SELECT ta_id FROM `user`
            WHERE user_id=%s
              AND user_type='student'
              AND ta_id IS NOT NULL
            """,
            (data.user_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError("Invalid user or missing TA stub (finish registration first)")

        # cursor is not dictionary=True, so row is a tuple
        ta_id = row[0]

        # 2) Update the existing TA record (persist name + onboarding fields)
        cursor.execute(
            """
            UPDATE ta
            SET name=%s,
                program=%s,
                level=%s,
                background=%s,
                admit_term=%s,
                standing=%s,
                max_hours=%s
            WHERE ta_id=%s
            """,
            (
                data.name,
                data.program,
                data.level,
                data.background,
                data.admit_term,
                data.standing,
                data.max_hours,
                ta_id
            )
        )

        # 3) Make onboarding idempotent: clear & re-insert skills/preferences
        cursor.execute("DELETE FROM ta_skill WHERE ta_id=%s", (ta_id,))
        cursor.execute("DELETE FROM ta_preferred_professor WHERE ta_id=%s", (ta_id,))

        for skill in data.skills:
            cursor.execute(
                "INSERT INTO ta_skill (ta_id, skill) VALUES (%s,%s)",
                (ta_id, skill)
            )

        for professor_id in data.preferred_professors:
            cursor.execute(
                """
                INSERT INTO ta_preferred_professor (ta_id, professor_id)
                VALUES (%s,%s)
                """,
                (ta_id, professor_id)
            )

        conn.commit()
        return ta_id

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()
