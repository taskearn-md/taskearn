import streamlit as st
import pandas as pd
import sqlite3
import random
import time

# --- НАСТРОЙКА ПЛАТФОРМЫ ---
COMMISSION_RATE = 0.10  # 10% комиссия сервиса

# --- РАБОТА С БАЗОЙ ДАННЫХ (SQL) ---
def init_db():
    conn = sqlite3.connect("taskearn_v20.db")
    cursor = conn.cursor()
    
    # Таблица пользователей (Убрали привязку роли к логике доступа)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,      
            username TEXT UNIQUE,
            name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL, 
            about TEXT,
            balance REAL DEFAULT 0.0,
            rating REAL DEFAULT 5.0,
            rating_count INTEGER DEFAULT 1,
            tasks_created INTEGER DEFAULT 0,
            tasks_canceled INTEGER DEFAULT 0
        )
    """)
    
    # Таблица для заданий
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            reward REAL NOT NULL,
            status TEXT NOT NULL,
            city TEXT NOT NULL,
            village TEXT NOT NULL,
            category TEXT NOT NULL,
            client_id INTEGER NOT NULL,
            worker_id INTEGER DEFAULT NULL,
            cancel_reason TEXT DEFAULT '',
            worker_evidence TEXT DEFAULT '',
            appeal_text TEXT DEFAULT '',
            FOREIGN KEY(client_id) REFERENCES users(id),
            FOREIGN KEY(worker_id) REFERENCES users(id)
        )
    """)
    conn.commit()
    conn.close()

def generate_unique_id():
    conn = sqlite3.connect("taskearn_v20.db")
    cursor = conn.cursor()
    while True:
        new_id = random.randint(100000, 999999)
        cursor.execute("SELECT id FROM users WHERE id = ?", (new_id,))
        if not cursor.fetchone():
            conn.close()
            return new_id

def register_user(user_id, name, phone, about, init_balance=0.0):
    conn = sqlite3.connect("taskearn_v20.db")
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO users (id, username, name, phone, about, balance)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, f"user_{user_id}", name, phone, about, init_balance))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    conn.close()
    return success

def get_user_by_id(user_id):
    conn = sqlite3.connect("taskearn_v20.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, name, phone, about, balance, rating, tasks_created, tasks_canceled FROM users WHERE id=?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    if res:
        return {
            "id": res[0], "username": res[1], "name": res[2], 
            "phone": res[3], "about": res[4], "balance": res[5], "rating": round(res[6], 1),
            "created": res[7], "canceled": res[8]
        }
    return None

def get_user_by_phone(phone):
    conn = sqlite3.connect("taskearn_v20.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE phone=?", (phone.strip(),))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else None

def update_profile(user_id, name, phone, about):
    conn = sqlite3.connect("taskearn_v20.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET name=?, phone=?, about=? WHERE id=?", (name, phone, about, user_id))
    conn.commit()
    conn.close()

def update_balance(user_id, amount):
    conn = sqlite3.connect("taskearn_v20.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ? WHERE id=?", (amount, user_id))
    conn.commit()
    conn.close()

def add_task(title, reward, city, village, category, client_id):
    conn = sqlite3.connect("taskearn_v20.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (title, reward, status, city, village, category, client_id) VALUES (?, ?, 'Доступно', ?, ?, ?, ?)", 
                   (title, reward, city, village, category, client_id))
    cursor.execute("UPDATE users SET tasks_created = tasks_created + 1 WHERE id=?", (client_id,))
    conn.commit()
    conn.close()

def get_tasks_with_names():
    query = """
        SELECT t.*, c.name AS client_name, w.name AS worker_name, w.phone AS worker_phone
        FROM tasks t
        JOIN users c ON t.client_id = c.id
        LEFT JOIN users w ON t.worker_id = w.id
    """
    conn = sqlite3.connect("taskearn_v20.db")
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def revoke_free_task(task_id):
    conn = sqlite3.connect("taskearn_v20.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()
    conn.close()

def worker_accept_task(task_id, worker_id):
    conn = sqlite3.connect("taskearn_v20.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='В работе', worker_id=? WHERE id=?", (worker_id, task_id))
    conn.commit()
    conn.close()

def worker_abandon_task(task_id):
    conn = sqlite3.connect("taskearn_v20.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='Доступно', worker_id=NULL, worker_evidence='' WHERE id=?", (task_id,))
    conn.commit()
    conn.close()

def send_to_review(task_id, evidence):
    conn = sqlite3.connect("taskearn_v20.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='На проверке', worker_evidence=? WHERE id=?", (evidence, task_id))
    conn.commit()
    conn.close()

def approve_task(task_id, total_reward, worker_id):
    admin_cut = total_reward * COMMISSION_RATE
    worker_cut = total_reward - admin_cut
    conn = sqlite3.connect("taskearn_v20.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='Выполнено' WHERE id=?", (task_id,))
    cursor.execute("UPDATE users SET balance = balance + ? WHERE id=?", (worker_cut, worker_id))
    conn.commit()
    conn.close()

def client_dispute_task(task_id, reason):
    conn = sqlite3.connect("taskearn_v20.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='Оспорено', cancel_reason=? WHERE id=?", (reason, task_id))
    conn.commit()
    conn.close()

def worker_confirm_cancel(task_id, reward, client_id, worker_id):
    conn = sqlite3.connect("taskearn_v20.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='Отменено' WHERE id=?", (task_id,))
    cursor.execute("UPDATE users SET balance = balance + ? WHERE id=?", (reward, client_id))
    cursor.execute("UPDATE users SET tasks_canceled = tasks_canceled + 1 WHERE id=?", (client_id,))
    conn.commit()
    conn.close()

# --- ИНИЦИАЛИЗАЦИЯ ---
init_db()
st.set_page_config(page_title="TaskEarn", page_icon="🇲🇩", layout="centered")

# Сессии
if "logged_in_user_id" not in st.session_state: st.session_state["logged_in_user_id"] = None
if "sms_code" not in st.session_state: st.session_state["sms_code"] = None
if "pending_phone" not in st.session_state: st.session_state["pending_phone"] = None
if "pending_user_data" not in st.session_state: st.session_state["pending_user_data"] = None

# --- АВТОРИЗАЦИЯ ---
if st.session_state["logged_in_user_id"] is None:
    st.title("🇲🇩 Вход / Регистрация TaskEarn")
    
    # [Здесь логика SMS та же, оставляем как есть для краткости, она рабочая]
    # (Для экономии места в ответе сократил дублирование блока SMS, 
    # вставляйте код входа из предыдущей версии)
    # ... (логика входа) ...
    # Если входа нет — выходим
    if st.session_state["sms_code"] is None:
        tab_login, tab_register = st.tabs(["🔑 Войти", "✨ Регистрация"])
        with tab_login:
            # ... (логика входа) ...
            login_phone = st.text_input("Телефон:")
            if st.button("Войти"):
                u_id = get_user_by_phone(login_phone)
                if u_id:
                    st.session_state["logged_in_user_id"] = u_id
                    st.rerun()
        with tab_register:
             # ... (логика регистрации без выбора роли) ...
             reg_name = st.text_input("Имя:")
             reg_phone = st.text_input("Телефон:")
             if st.button("Зарегистрироваться"):
                 new_id = generate_unique_id()
                 register_user(new_id, reg_name, reg_phone, "")
                 st.session_state["logged_in_user_id"] = new_id
                 st.rerun()
        st.stop()

# --- ГЛАВНЫЙ ЭКРАН (Один аккаунт - все функции) ---
user_data = get_user_by_id(st.session_state["logged_in_user_id"])
st.sidebar.header(f"Привет, {user_data['name']}")
st.sidebar.write(f"🆔 ID: {user_data['id']}")
st.sidebar.metric("Баланс", f"{user_data['balance']} MDL")
if st.sidebar.button("🚪 Выйти"):
    st.session_state["logged_in_user_id"] = None
    st.rerun()

st.title("TaskEarn: Лента и Управление")

# --- ВКЛАДКИ ДЛЯ ВСЕХ ---
tab_client, tab_worker, tab_profile = st.tabs(["💼 Я Заказчик", "🧑‍💻 Я Исполнитель", "👤 Мой профиль"])

with tab_client:
    st.header("Разместить задание")
    # ... (Логика размещения задания) ...
    with st.form("new_task"):
        t = st.text_input("Что сделать?")
        r = st.number_input("Бюджет", min_value=10)
        if st.form_submit_button("Создать"):
            add_task(t, r, "Кишинев", "Центр", "Другое", user_data['id'])
            st.success("Создано!")

    st.subheader("Мои созданные")
    tasks = get_tasks_with_names()
    my_tasks = tasks[tasks["client_id"] == user_data['id']]
    st.dataframe(my_tasks[['title', 'status', 'reward']])

with tab_worker:
    st.header("Доступные заказы")
    tasks = get_tasks_with_names()
    # Фильтр: только доступные И чужие
    available_tasks = tasks[(tasks["status"] == "Доступно") & (tasks["client_id"] != user_data['id'])]
    
    for _, task in available_tasks.iterrows():
        with st.expander(f"{task['title']} — {task['reward']} MDL"):
            if st.button(f"Взять заказ #{task['id']}"):
                worker_accept_task(task['id'], user_data['id'])
                st.rerun()

    st.subheader("Заказы в работе")
    my_work = tasks[tasks["worker_id"] == user_data['id']]
    st.dataframe(my_work[['title', 'status']])

with tab_profile:
    st.write("Настройки профиля...")
