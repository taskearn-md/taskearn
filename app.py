import streamlit as st
import pandas as pd
import sqlite3
import random
import time

# --- НАСТРОЙКА ---
COMMISSION_RATE = 0.10
DB_NAME = "taskearn_monolith.db"

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            about TEXT,
            balance REAL DEFAULT 0.0,
            rating REAL DEFAULT 5.0,
            tasks_created INTEGER DEFAULT 0,
            tasks_canceled INTEGER DEFAULT 0
        )
    """)
    
    # Таблица заданий
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

# --- ХЕЛПЕРЫ БАЗЫ ДАННЫХ ---
def get_user_by_id(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    if res:
        return {"id": res[0], "name": res[1], "phone": res[2], "about": res[3], "balance": res[4], "rating": res[5]}
    return None

def get_tasks_with_names():
    query = """
        SELECT t.*, c.name AS client_name, w.name AS worker_name, w.phone AS worker_phone
        FROM tasks t
        JOIN users c ON t.client_id = c.id
        LEFT JOIN users w ON t.worker_id = w.id
    """
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# (Остальные функции: update_balance, add_task, approve_task и т.д. — аналогичны вашим)
def update_balance(user_id, amount):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ? WHERE id=?", (amount, user_id))
    conn.commit()
    conn.close()

def add_task(title, reward, city, village, category, client_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (title, reward, status, city, village, category, client_id) VALUES (?, ?, 'Доступно', ?, ?, ?, ?)", 
                   (title, reward, city, village, category, client_id))
    conn.commit()
    conn.close()

# --- ИНИЦИАЛИЗАЦИЯ ---
init_db()
st.set_page_config(page_title="TaskEarn", layout="centered")

# Состояния сессии
if "logged_in_user_id" not in st.session_state: st.session_state["logged_in_user_id"] = None
if "active_mode" not in st.session_state: st.session_state["active_mode"] = "Заказчик"

# --- ЛОГИКА ВХОДА ---
if st.session_state["logged_in_user_id"] is None:
    st.title("🇲🇩 Вход в TaskEarn")
    phone = st.text_input("Введите номер шлухи:")
    if st.button("Войти"):
        # Упрощенная логика входа для примера
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE phone=?", (phone,))
        user = cursor.fetchone()
        conn.close()
        if user:
            st.session_state["logged_in_user_id"] = user[0]
            st.rerun()
        else:
            st.error("Пользователь не найден.")
    st.stop()

# --- ОСНОВНОЙ ИНТЕРФЕЙС ---
user_data = get_user_by_id(st.session_state["logged_in_user_id"])

# Сайдбар
st.sidebar.header("Панель управления")
st.sidebar.write(f"👤 **{user_data['name']}**")
st.sidebar.write(f"💰 Баланс: {user_data['balance']} MDL")

# Переключатель ролей
st.session_state["active_mode"] = st.sidebar.radio(
    "Выберите режим работы:", 
    ["Заказчик", "Исполнитель"],
    key="mode_radio"
)

if st.sidebar.button("Выйти"):
    st.session_state["logged_in_user_id"] = None
    st.rerun()

# --- ОТОБРАЖЕНИЕ В ЗАВИСИМОСТИ ОТ РЕЖИМА ---
if st.session_state["active_mode"] == "Заказчик":
    st.header("📋 Режим Заказчика")
    # Код для размещения заказов (ваша форма)
    with st.form("new_task"):
        title = st.text_input("Название задания")
        reward = st.number_input("Оплата", value=100)
        if st.form_submit_button("Создать"):
            add_task(title, reward, "Кишинёв", "Центр", "Доставка", user_data['id'])
            st.success("Задание создано!")

elif st.session_state["active_mode"] == "Исполнитель":
    st.header("🧑‍💻 Режим Исполнителя")
    st.subheader("Лента заданий")
    
    df = get_tasks_with_names()
    tasks = df[df["status"] == "Доступно"].to_dict(orient="records")
    
    for task in tasks:
        with st.container():
            st.write(f"**{task['title']}** — {task['reward']} MDL")
            
            # --- ЗАЩИТА: Нельзя взять свой заказ ---
            if task['client_id'] == user_data['id']:
                st.caption("🔒 Это ваш заказ, его нельзя выполнить самостоятельно.")
            else:
                if st.button(f"Взять заказ #{task['id']}", key=f"btn_{task['id']}"):
                    # Логика принятия задания
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute("UPDATE tasks SET status='В работе', worker_id=? WHERE id=?", (user_data['id'], task['id']))
                    conn.commit()
                    conn.close()
                    st.success("Заказ взят!")
                    st.rerun()
            st.divider()
