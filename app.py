import streamlit as st
import pandas as pd
import sqlite3
import random
import time

# --- НАСТРОЙКА ПЛАТФОРМЫ ---
COMMISSION_RATE = 0.10

# --- РАБОТА С БАЗОЙ ДАННЫХ (SQL) ---
def init_db():
    conn = sqlite3.connect("taskearn_v20.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY, role TEXT NOT NULL, username TEXT UNIQUE,
            name TEXT NOT NULL, phone TEXT UNIQUE NOT NULL, about TEXT,
            balance REAL DEFAULT 0.0, rating REAL DEFAULT 5.0,
            tasks_created INTEGER DEFAULT 0, tasks_canceled INTEGER DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
            reward REAL NOT NULL, status TEXT NOT NULL, city TEXT NOT NULL,
            village TEXT NOT NULL, category TEXT NOT NULL, client_id INTEGER NOT NULL,
            worker_id INTEGER DEFAULT NULL, cancel_reason TEXT DEFAULT '',
            worker_evidence TEXT DEFAULT '', appeal_text TEXT DEFAULT '',
            FOREIGN KEY(client_id) REFERENCES users(id), FOREIGN KEY(worker_id) REFERENCES users(id)
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
        cursor.execute("INSERT INTO users (id, role, username, name, phone, about, balance) VALUES (?, 'user', ?, ?, ?, ?, ?)",
                       (user_id, f"user_{user_id}", name, phone, about, init_balance))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    conn.close()
    return success

def get_user_by_id(user_id):
    conn = sqlite3.connect("taskearn_v20.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, phone, about, balance, rating FROM users WHERE id=?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    if res:
        return {"id": res[0], "name": res[1], "phone": res[2], "about": res[3], "balance": res[4], "rating": res[5]}
    return None

def get_user_by_phone(phone):
    conn = sqlite3.connect("taskearn_v20.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE phone=?", (phone.strip(),))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else None

def update_profile(user_id, name, about):
    conn = sqlite3.connect("taskearn_v20.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET name=?, about=? WHERE id=?", (name, about, user_id))
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
    conn = sqlite3.connect("taskearn_v20.db")
    df = pd.read_sql_query("SELECT t.*, c.name AS client_name, w.name AS worker_name FROM tasks t JOIN users c ON t.client_id = c.id LEFT JOIN users w ON t.worker_id = w.id", conn)
    conn.close()
    return df

def worker_accept_task(task_id, worker_id):
    conn = sqlite3.connect("taskearn_v20.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='В работе', worker_id=? WHERE id=?", (worker_id, task_id))
    conn.commit()
    conn.close()

def worker_abandon_task(task_id):
    conn = sqlite3.connect("taskearn_v20.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='Доступно', worker_id=NULL WHERE id=?", (task_id,))
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

# --- APP ---
init_db()
st.set_page_config(page_title="TaskEarn", layout="centered")

if "logged_in_user_id" not in st.session_state: st.session_state["logged_in_user_id"] = None
if "sms_code" not in st.session_state: st.session_state["sms_code"] = None
if "pending_phone" not in st.session_state: st.session_state["pending_phone"] = None

# ВХОД / РЕГИСТРАЦИЯ
if st.session_state["logged_in_user_id"] is None:
    tab_login, tab_register = st.tabs(["🔑 Вход", "✨ Регистрация"])
    
    with tab_login:
        login_phone = st.text_input("Ваш телефон:", key="login_phone_in")
        if st.button("Войти", key="btn_login"):
            uid = get_user_by_phone(login_phone)
            if uid:
                st.session_state["logged_in_user_id"] = uid
                st.rerun()
            else: st.error("Не найден")

    with tab_register:
        reg_name = st.text_input("Имя:", key="reg_name_in")
        reg_phone = st.text_input("Телефон:", key="reg_phone_in")
        if st.button("Зарегистрироваться", key="btn_reg"):
            uid = generate_unique_id()
            if register_user(uid, reg_name, reg_phone, ""):
                st.session_state["logged_in_user_id"] = uid
                st.rerun()
    st.stop()

# --- ОСНОВНАЯ ЛОГИКА ---
user_data = get_user_by_id(st.session_state["logged_in_user_id"])
st.sidebar.write(f"👤 {user_data['name']} | 💰 {user_data['balance']} MDL")
if st.sidebar.button("Выйти", key="logout_btn"):
    st.session_state["logged_in_user_id"] = None
    st.rerun()

tab1, tab2, tab3 = st.tabs(["📋 Мои Заказы (Заказчик)", "🛠️ Биржа задач (Исполнитель)", "👤 Профиль"])

with tab1:
    st.subheader("Создать заказ")
    with st.form("new_task_form"):
        title = st.text_input("Что нужно сделать?", key="task_title_in")
        reward = st.number_input("Бюджет", min_value=20, key="task_reward_in")
        if st.form_submit_button("Опубликовать"):
            add_task(title, reward, "Кишинев", "Центр", "Другое", user_data['id'])
            st.rerun()
    
    st.subheader("Ваши заказы")
    tasks = get_tasks_with_names()
    my_tasks = tasks[tasks["client_id"] == user_data['id']]
    for _, t in my_tasks.iterrows():
        st.write(f"**{t['title']}** - {t['status']}")

with tab2:
    st.subheader("Актуальные задания")
    tasks = get_tasks_with_names()
    # Фильтр: Доступно И клиент НЕ вы
    available = tasks[(tasks["status"] == "Доступно") & (tasks["client_id"] != user_data['id'])]
    for _, t in available.iterrows():
        st.write(f"**{t['title']}** - {t['reward']} MDL")
        if st.button(f"Взять заказ {t['id']}", key=f"take_{t['id']}"):
            worker_accept_task(t['id'], user_data['id'])
            st.rerun()

with tab3:
    st.write("Настройки профиля")
    new_name = st.text_input("Имя", value=user_data['name'], key="prof_name")
    if st.button("Сохранить", key="save_prof"):
        update_profile(user_data['id'], new_name, user_data['about'])
        st.rerun()
