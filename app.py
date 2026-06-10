import streamlit as st
import pandas as pd
import sqlite3
import random
import time

# --- КОНФИГУРАЦИЯ ---
DB_NAME = "taskearn_v20.db"
COMMISSION_RATE = 0.10  # 10% комиссия сервиса

# --- РАБОТА С БАЗОЙ ДАННЫХ (SQL) ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,     
            role TEXT NOT NULL,
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
    
    # Создаем дефолтных пользователей для тестов
    cursor.execute("INSERT OR IGNORE INTO users (id, role, username, name, phone, about, balance) VALUES (482910, 'client', 'ion_cheban', 'Ион Чебан (Заказчик)', '+37368123456', 'Заказчик из Кишинева.', 1000.0)")
    cursor.execute("INSERT OR IGNORE INTO users (id, role, username, name, phone, about, balance) VALUES (730145, 'worker', 'mihail_lupu', 'Михаил Лупу (Воркер)', '+37379987654', 'Исполнитель из Комрата.', 0.0)")
    cursor.execute("INSERT OR IGNORE INTO users (id, role, username, name, phone, about, balance) VALUES (999111, 'admin', 'platform_owner', 'Администратор', '000', 'Владелец платформы', 0.0)")
    
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
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    while True:
        new_id = random.randint(100000, 999999)
        cursor.execute("SELECT id FROM users WHERE id = ?", (new_id,))
        if not cursor.fetchone():
            conn.close()
            return new_id

def register_user(user_id, role, name, phone, about, init_balance=0.0):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO users (id, role, username, name, phone, about, balance)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, role, f"user_{user_id}", name, phone, about, init_balance))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    conn.close()
    return success

def get_user_by_id(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, role, username, name, phone, about, balance, rating, tasks_created, tasks_canceled FROM users WHERE id=?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    if res:
        return {
            "id": res[0], "role": res[1], "username": res[2], "name": res[3], 
            "phone": res[4], "about": res[5], "balance": res[6], "rating": round(res[7], 1),
            "created": res[8], "canceled": res[9]
        }
    return None

def get_user_by_phone(phone):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE phone=?", (phone.strip(),))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else None

def update_profile(user_id, name, phone, about):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET name=?, phone=?, about=? WHERE id=?", (name, phone, about, user_id))
    conn.commit()
    conn.close()

def update_balance(user_id, amount):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ? WHERE id=?", (amount, user_id))
    conn.commit()
    conn.close()

def change_rating_flat(user_id, penalty):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT rating FROM users WHERE id=?", (user_id,))
    res = cursor.fetchone()
    if res:
        new_rating = max(1.0, min(5.0, res[0] + penalty))
        cursor.execute("UPDATE users SET rating=? WHERE id=?", (new_rating, user_id))
    conn.commit()
    conn.close()

def add_task(title, reward, city, village, category, client_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (title, reward, status, city, village, category, client_id) VALUES (?, ?, 'Доступно', ?, ?, ?, ?)", 
                   (title, reward, city, village, category, client_id))
    cursor.execute("UPDATE users SET tasks_created = tasks_created + 1 WHERE id=?", (client_id,))
    conn.commit()
    conn.close()

def get_tasks_with_names():
    query = """
        SELECT t.*, c.name AS client_name, w.name AS worker_name, w.phone AS worker_phone, w.rating AS worker_rating
        FROM tasks t
        JOIN users c ON t.client_id = c.id
        LEFT JOIN users w ON t.worker_id = w.id
    """
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def revoke_free_task(task_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()
    conn.close()

def worker_accept_task(task_id, worker_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='В работе', worker_id=? WHERE id=?", (worker_id, task_id))
    conn.commit()
    conn.close()

def worker_abandon_task(task_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='Доступно', worker_id=NULL, worker_evidence='' WHERE id=?", (task_id,))
    conn.commit()
    conn.close()

def send_to_review(task_id, evidence):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='На проверке', worker_evidence=? WHERE id=?", (evidence, task_id))
    conn.commit()
    conn.close()

def approve_task(task_id, total_reward, worker_id):
    admin_cut = total_reward * COMMISSION_RATE
    worker_cut = total_reward - admin_cut
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='Выполнено' WHERE id=?", (task_id,))
    cursor.execute("UPDATE users SET balance = balance + ? WHERE id=?", (worker_cut, worker_id))
    cursor.execute("UPDATE users SET balance = balance + ? WHERE id=999111", (admin_cut,))
    conn.commit()
    conn.close()

def client_dispute_task(task_id, reason):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='Оспорено', cancel_reason=? WHERE id=?", (reason, task_id))
    conn.commit()
    conn.close()

def worker_confirm_cancel(task_id, reward, client_id, worker_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='Отменено' WHERE id=?", (task_id,))
    cursor.execute("UPDATE users SET balance = balance + ? WHERE id=?", (reward, client_id))
    cursor.execute("UPDATE users SET tasks_canceled = tasks_canceled + 1 WHERE id=?", (client_id,))
    conn.commit()
    conn.close()
    change_rating_flat(worker_id, -0.6)

def worker_send_to_arbitration(task_id, appeal_text):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='Арбитраж', appeal_text=? WHERE id=?", (appeal_text, task_id))
    conn.commit()
    conn.close()

# --- ОСНОВНАЯ ЧАСТЬ ---
init_db()

CITIES = ["Все регионы", "Кишинёв", "Бельцы", "Комрат", "Кагул", "Оргеев", "Унгены", "Сороки", "Тирасполь"]
CATEGORIES = ["Все категории", "📦 Доставка", "🛠️ Ремонт и дом", "💻 IT и Тексты", "🚗 Автоуслуги", "Другое"]

st.set_page_config(page_title="TaskEarn SMS Auth", page_icon="🇲🇩", layout="centered")

# Состояния сессии
if "logged_in_user_id" not in st.session_state: st.session_state["logged_in_user_id"] = None
if "sms_code" not in st.session_state: st.session_state["sms_code"] = None
if "pending_phone" not in st.session_state: st.session_state["pending_phone"] = None
if "pending_user_data" not in st.session_state: st.session_state["pending_user_data"] = None

# --- ВХОД И РЕГИСТРАЦИЯ ---
if st.session_state["logged_in_user_id"] is None:
    st.title("🇲🇩 Вход в TaskEarn")
    
    if st.session_state["sms_code"] is not None:
        st.info(f"Код отправлен на: **{st.session_state['pending_phone']}**")
        input_sms = st.text_input("Введите 4-значный код:", max_chars=4)
        if input_sms:
            if input_sms.strip() == st.session_state["sms_code"]:
                if st.session_state["pending_user_data"] is None:
                    user_id = get_user_by_phone(st.session_state["pending_phone"])
                    st.session_state["logged_in_user_id"] = user_id
                else:
                    p_data = st.session_state["pending_user_data"]
                    new_id = generate_unique_id()
                    register_user(new_id, p_data['role'], p_data['name'], p_data['phone'], p_data['about'], p_data['balance'])
                    st.session_state["logged_in_user_id"] = new_id
                st.session_state["sms_code"] = None
                st.rerun()
            else:
                st.error("Неверный код.")
        st.stop()

    tab_login, tab_register = st.tabs(["🔑 Войти", "✨ Регистрация"])
    with tab_login:
        login_phone = st.text_input("Телефон:", key="log_p")
        if st.button("Получить SMS-код", key="log_submit"):
            if get_user_by_phone(login_phone):
                st.session_state["sms_code"] = "1234" # Для тестов статичный код
                st.session_state["pending_phone"] = login_phone
                st.toast(f"Код: 1234")
                st.rerun()
    with tab_register:
        reg_role = st.selectbox("Роль:", ["client", "worker"])
        reg_name = st.text_input("Имя:")
        reg_phone = st.text_input("Телефон (reg):")
        reg_about = st.text_area("О себе:")
        if st.button("Зарегистрироваться"):
            st.session_state["sms_code"] = "1234"
            st.session_state["pending_phone"] = reg_phone
            st.session_state["pending_user_data"] = {"role": reg_role, "name": reg_name, "phone": reg_phone, "about": reg_about, "balance": 500.0 if reg_role == "client" else 0.0}
            st.rerun()
    st.stop()

# --- ОСНОВНОЙ ИНТЕРФЕЙС ---
user_data = get_user_by_id(st.session_state["logged_in_user_id"])
if not user_data:
    st.session_state["logged_in_user_id"] = None
    st.rerun()

st.title("🇲🇩 TaskEarn")
st.sidebar.header("Кабинет")
st.sidebar.write(f"👤 {user_data['name']}")
if st.sidebar.button("Выход"):
    st.session_state["logged_in_user_id"] = None
    st.rerun()

# ЛОГИКА РОЛЕЙ
if user_data['role'] == 'client':
    st.header("Заказчик")
    # ... логика заказчика ...
    tab_tasks, tab_review = st.tabs(["Заказы", "Контроль"])
    with tab_tasks:
        # Форма добавления задачи
        with st.form("task_f"):
            title = st.text_input("Задача")
            reward = st.number_input("Цена", value=100)
            if st.form_submit_button("Создать"):
                add_task(title, reward, "Кишинёв", "Центр", "Доставка", user_data['id'])
                st.rerun()

elif user_data['role'] == 'worker':
    st.header("Исполнитель")
    # ... логика воркера ...
    st.dataframe(get_tasks_with_names())

elif user_data['role'] == 'admin':
    st.header("Админ-панель")
    # ... логика арбитража ...
