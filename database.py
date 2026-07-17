import sqlite3
from datetime import datetime

from datetime import timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))

DB_NAME = "employee_checklist.db"


# =====================================================
# CONNECTION
# =====================================================
def get_connection():
    return sqlite3.connect(DB_NAME)


# =====================================================
# TABLES
# =====================================================
def create_tables():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS employees (
        employee_id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_name TEXT UNIQUE,
        department TEXT,
        password TEXT,
        role TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS checklists (
        checklist_id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER,
        checklist_date TEXT,
        month TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        task_id INTEGER PRIMARY KEY AUTOINCREMENT,
        checklist_id INTEGER,
        task_desc TEXT,
        status TEXT,
        created_time TEXT,
        completed_time TEXT
    )
    """)

    conn.commit()
    conn.close()


# =====================================================
# DEFAULT ADMIN ONLY
# =====================================================
def initialize_default_data():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM employees WHERE role='admin'")
    admin_exists = cur.fetchone()[0]

    if admin_exists == 0:
        cur.execute("""
        INSERT INTO employees (
            employee_name,
            department,
            password,
            role
        )
        VALUES (?, ?, ?, ?)
        """, (
            "Admin",
            "Management",
            "admin123",
            "admin"
        ))

    conn.commit()
    conn.close()


# =====================================================
# EMPLOYEE ENROLLMENT
# =====================================================
def register_employee(employee_name, department, password):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
        INSERT INTO employees (
            employee_name,
            department,
            password,
            role
        )
        VALUES (?, ?, ?, ?)
        """, (
            employee_name,
            department,
            password,
            "employee"
        ))

        conn.commit()
        return True, "Employee enrolled successfully"

    except sqlite3.IntegrityError:
        return False, "Employee name already exists"

    finally:
        conn.close()


# =====================================================
# LOGIN USING NAME + PASSWORD
# =====================================================
def login(employee_name, password):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT * FROM employees
    WHERE employee_name=? AND password=?
    """, (employee_name, password))

    user = cur.fetchone()

    conn.close()
    return user


# =====================================================
# CHECKLIST
# =====================================================
def get_or_create_checklist(employee_id):
    today = datetime.now(IST).strftime("%Y-%m-%d")
    month = datetime.now(IST).strftime("%B")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT checklist_id FROM checklists
    WHERE employee_id=? AND checklist_date=?
    """, (employee_id, today))

    result = cur.fetchone()

    if result:
        conn.close()
        return result[0]

    cur.execute("""
    INSERT INTO checklists (
        employee_id,
        checklist_date,
        month
    )
    VALUES (?, ?, ?)
    """, (employee_id, today, month))

    conn.commit()

    checklist_id = cur.lastrowid

    conn.close()

    return checklist_id


# =====================================================
# TASKS
# =====================================================
def add_task(checklist_id, task):
    conn = get_connection()
    cur = conn.cursor()

    now = datetime.now(IST).isoformat()

    cur.execute("""
    INSERT INTO tasks (
        checklist_id,
        task_desc,
        status,
        created_time,
        completed_time
    )
    VALUES (?, ?, 'Pending', ?, '')
    """, (checklist_id, task, now))

    conn.commit()
    conn.close()
    task_id = cur.lastrowid   
    conn.close()
    return task_id   

# =====================================================
# COMPLETE TASK
# =====================================================
def complete_task(task_id):
    conn = get_connection()
    cur = conn.cursor()

    now = datetime.now(IST).isoformat()

    cur.execute("""
    UPDATE tasks
    SET status='Completed',
        completed_time=?
    WHERE task_id=?
    """, (now, task_id))

    conn.commit()
    conn.close()


# =====================================================
# EMPLOYEE TASKS
# =====================================================
def get_tasks(employee_id):
    today = datetime.now(IST).strftime("%Y-%m-%d")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT
        t.task_id,
        t.task_desc,
        t.status,
        t.created_time,
        t.completed_time
    FROM tasks t
    JOIN checklists c
        ON t.checklist_id = c.checklist_id
    WHERE c.employee_id=?
        AND c.checklist_date=?
    ORDER BY t.task_id 
    """, (employee_id, today))

    data = cur.fetchall()

    conn.close()
    return data


# =====================================================
# ADMIN DATA
# =====================================================
def get_all_employee_status():
    today = datetime.now(IST).strftime("%Y-%m-%d")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT
        e.employee_id,
        e.employee_name,
        e.department,
        t.task_desc,
        t.status,
        t.created_time,
        t.completed_time
    FROM employees e
    LEFT JOIN checklists c
        ON e.employee_id = c.employee_id
        AND c.checklist_date = ?
    LEFT JOIN tasks t
        ON c.checklist_id = t.checklist_id
    """, (today,))

    data = cur.fetchall()

    conn.close()
    return data
# =====================================================
# UPDATE TASK DESCRIPTION
# =====================================================
def update_task_description(task_id, new_description):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    UPDATE tasks
    SET task_desc = ?
    WHERE task_id = ?
    """, (new_description, task_id))

    conn.commit()
    conn.close()
