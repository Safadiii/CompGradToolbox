from app.core.database import get_db_connection
from app.core.security import verify_password, hash_password
from typing import Optional, Dict

def authenticate_user(username: str, password: str) -> Optional[Dict]:

    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT user_id, username, password, user_type, ta_id, professor_id
            FROM `user`
            WHERE username=%s
            """,
            (username,)
        )
        user = cursor.fetchone()

        if not user:
            cursor.close()
            return None

        stored_password = user["password"]
        password_ok = False

        if stored_password and stored_password.startswith("$2"):
            password_ok = verify_password(password, stored_password)
        else:
            password_ok = password == stored_password
            if password_ok:
                new_hash = hash_password(password)
                cursor.execute(
                    "UPDATE `user` SET password=%s WHERE user_id=%s",
                    (new_hash, user["user_id"])
                )
                conn.commit()

        if not password_ok:
            cursor.close()
            return None

        name = None
        onboarding_required = False

        if user["user_type"] == "student":
            ta_id = user.get("ta_id")

            if not ta_id:
                onboarding_required = True
            else:
                cursor.execute(
                    """
                    SELECT name, program, admit_term, level
                    FROM ta
                    WHERE ta_id=%s
                    """,
                    (ta_id,)
                )
                ta_row = cursor.fetchone()

                if ta_row:
                    name = ta_row.get("name")
                    if ta_row.get("program") is None or ta_row.get("admit_term") is None:
                        onboarding_required = True
                else:
                    onboarding_required = True

        elif user["user_type"] == "faculty":
            professor_id = user.get("professor_id")

            if not professor_id:
                onboarding_required = True
            else:
                cursor.execute(
                    "SELECT name FROM professor WHERE professor_id=%s",
                    (professor_id,)
                )
                prof_row = cursor.fetchone()
                if prof_row:
                    name = prof_row.get("name")

                cursor.execute(
                    "SELECT COUNT(*) AS cnt FROM professor_preferred_ta WHERE professor_id=%s",
                    (professor_id,)
                )
                cnt_row = cursor.fetchone()
                if not cnt_row or cnt_row["cnt"] == 0:
                    onboarding_required = True

        elif user["user_type"] == "admin":
            name = "Admin User"
            onboarding_required = False

        cursor.close()

        return {
            "user_id": user["user_id"],
            "username": user["username"],
            "user_type": user["user_type"],
            "name": name,
            "ta_id": user.get("ta_id"),
            "professor_id": user.get("professor_id"),
            "onboarding_required": onboarding_required
        }
