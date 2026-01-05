from app.core.database import get_db_connection
from app.models import FacultyOnboardingRequest

def onboard_faculty(data: FacultyOnboardingRequest):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 1) Validate user and fetch existing stub professor_id
        cursor.execute(
            """
            SELECT professor_id FROM `user`
            WHERE user_id=%s
              AND user_type='faculty'
              AND professor_id IS NOT NULL
            """,
            (data.user_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError("Invalid user or missing Professor stub (finish registration first)")

        professor_id = row[0]

        # 2) Update professor name (in case onboarding form includes it)
        cursor.execute(
            "UPDATE professor SET name=%s WHERE professor_id=%s",
            (data.name, professor_id)
        )

        # 3) Idempotent preferred TAs
        cursor.execute(
            "DELETE FROM professor_preferred_ta WHERE professor_id=%s",
            (professor_id,)
        )

        for ta_id in data.preferred_tas:
            cursor.execute(
                """
                INSERT INTO professor_preferred_ta (professor_id, ta_id)
                VALUES (%s,%s)
                """,
                (professor_id, ta_id)
            )

        conn.commit()
        return professor_id

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()
