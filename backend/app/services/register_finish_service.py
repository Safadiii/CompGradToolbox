from app.core.database import get_db_connection


def finish_registration(token: str) -> int:
    """
    Finalizes a pending registration by token:
    - Validates token exists and has not expired
    - Creates a real user row
    - Immediately creates minimal TA/Professor row to persist name (no user.name needed)
    - Links the TA/Professor row to the user
    - Deletes the pending row
    Returns the new user_id (int)
    """

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Lock the pending row so token can't be used twice concurrently
        cursor.execute(
            """
            SELECT pending_id, name, username, password_hash, role
            FROM pending_registration
            WHERE token = %s
              AND expires_at > UTC_TIMESTAMP()
            FOR UPDATE
            """,
            (token,)
        )
        pending = cursor.fetchone()

        if not pending:
            raise ValueError("Invalid, expired, or already-used registration token")

        name = pending["name"]
        username = pending["username"]
        password_hash = pending["password_hash"]
        role = pending["role"]  # 'student' | 'faculty' | 'admin'

        # Create the real user (note: user table has no name field)
        cursor.execute(
            """
            INSERT INTO `user` (username, password, user_type)
            VALUES (%s, %s, %s)
            """,
            (username, password_hash, role)
        )
        user_id = cursor.lastrowid

        # Persist the name by creating the role record immediately
        if role == "student":
            cursor.execute("INSERT INTO ta (name) VALUES (%s)", (name,))
            ta_id = cursor.lastrowid
            cursor.execute(
                "UPDATE `user` SET ta_id=%s WHERE user_id=%s",
                (ta_id, user_id)
            )

        elif role == "faculty":
            cursor.execute("INSERT INTO professor (name) VALUES (%s)", (name,))
            professor_id = cursor.lastrowid
            cursor.execute(
                "UPDATE `user` SET professor_id=%s WHERE user_id=%s",
                (professor_id, user_id)
            )

        elif role == "admin":
            # No linked record needed; login can show "Admin User"
            pass

        else:
            raise ValueError("Unsupported role")

        # Delete pending row now that user is created
        cursor.execute(
            "DELETE FROM pending_registration WHERE pending_id=%s",
            (pending["pending_id"],)
        )

        conn.commit()
        return user_id

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()
