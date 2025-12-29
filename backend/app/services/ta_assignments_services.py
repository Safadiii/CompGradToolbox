from app.core.database import get_db_connection

def get_assignments_for_ta(ta_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Get assigned courses + course_code
    cursor.execute("""
        SELECT a.assignment_id, c.course_id, c.course_code
        FROM ta_assignment a
        JOIN course c ON c.course_id = a.course_id
        WHERE a.ta_id = %s
        ORDER BY c.course_code ASC
    """, (ta_id,))
    rows = cursor.fetchall()

    if not rows:
        cursor.close()
        conn.close()
        return []

    course_ids = [r["course_id"] for r in rows]

    # Professors for each course
    cursor.execute(f"""
        SELECT cp.course_id, p.name
        FROM course_professor cp
        JOIN professor p ON p.professor_id = cp.professor_id
        WHERE cp.course_id IN ({",".join(["%s"] * len(course_ids))})
    """, course_ids)
    prof_rows = cursor.fetchall()
    prof_map = {}
    for r in prof_rows:
        prof_map.setdefault(r["course_id"], []).append(r["name"])

    # Required skills for each course
    cursor.execute(f"""
        SELECT course_id, skill
        FROM course_skill
        WHERE course_id IN ({",".join(["%s"] * len(course_ids))})
    """, course_ids)
    skill_rows = cursor.fetchall()
    skill_map = {}
    for r in skill_rows:
        skill_map.setdefault(r["course_id"], []).append(r["skill"])

    # Merge
    out = []
    for r in rows:
        out.append({
            "assignment_id": r["assignment_id"],
            "course_id": r["course_id"],
            "course_code": r["course_code"],
            "professors": prof_map.get(r["course_id"], []),
            "required_skills": skill_map.get(r["course_id"], []),
        })

    cursor.close()
    conn.close()
    return out
