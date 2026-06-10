import streamlit as st
import pandas as pd
import sqlite3

# --- КОНФИГУРАЦИЯ ---
DB_NAME = "taskearn_full.db"

# --- БАЗА ДАННЫХ (ФУНКЦИИ) ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Таблица пользователей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            balance REAL DEFAULT 0.0,
            role TEXT DEFAULT 'user'
        )
    """)
    # Таблица заданий
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            reward REAL NOT NULL,
            status TEXT DEFAULT 'Доступно',
            client_id INTEGER NOT NULL,
            worker_id INTEGER,
            FOREIGN KEY(client_id) REFERENCES users(id)
        )
    """)
    # Тестовые пользователи (для старта)
    cursor.execute("INSERT OR IGNORE INTO users (id, name, phone, balance) VALUES (1, 'Иван', '+37368123456', 500.0)")
    cursor.execute("INSERT OR IGNORE INTO users (id, name, phone, balance) VALUES (2, 'Мария', '+37379987654', 100.0)")
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    return {"id": res[0], "name": res[1], "phone": res[2], "balance": res[3]} if res else None

def update_user_balance(user_id, amount):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ? WHERE id=?", (amount, user_id))
    conn.commit()
    conn.close()

def get_all_tasks():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM tasks", conn)
    conn.close()
    return df

# --- ИНИЦИАЛИЗАЦИЯ ---
init_db()
st.set_page_config(page_title="TaskEarn PRO", layout="wide")

# --- СЕССИЯ ---
if "logged_in_user_id" not in st.session_state: st.session_state["logged_in_user_id"] = None
if "active_mode" not in st.session_state: st.session_state["active_mode"] = "Заказчик"

# --- ЭКРАН ВХОДА ---
if st.session_state["logged_in_user_id"] is None:
    st.title("Вход в TaskEarn")
    phone = st.text_input("Введите номер телефона:")
    if st.button("Войти"):
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

# --- ОСНОВНАЯ ЛОГИКА ---
user_data = get_user(st.session_state["logged_in_user_id"])

if not user_data:
    st.error("Ошибка сессии. Пожалуйста, перезагрузите страницу.")
    if st.button("Выйти"):
        st.session_state["logged_in_user_id"] = None
        st.rerun()
    st.stop()

# --- САЙДБАР ---
st.sidebar.title("Панель управления")
st.sidebar.write(f"👤 **{user_data['name']}**")
st.sidebar.write(f"💰 Баланс: **{user_data['balance']} MDL**")
st.sidebar.divider()

# Переключатель
mode = st.sidebar.radio("Ваш режим:", ["Заказчик", "Исполнитель"])
st.session_state["active_mode"] = mode

if st.sidebar.button("Выйти из аккаунта"):
    st.session_state["logged_in_user_id"] = None
    st.rerun()

# --- ИНТЕРФЕЙС ЗАКАЗЧИКА ---
if st.session_state["active_mode"] == "Заказчик":
    st.header("📋 Режим Заказчика")
    
    with st.expander("➕ Создать новое задание", expanded=True):
        with st.form("task_form"):
            title = st.text_input("Название")
            reward = st.number_input("Оплата", min_value=1.0)
            if st.form_submit_button("Опубликовать"):
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute("INSERT INTO tasks (title, reward, client_id) VALUES (?, ?, ?)", 
                               (title, reward, user_data['id']))
                conn.commit()
                conn.close()
                st.success("Задание создано!")
                st.rerun()

    st.subheader("Ваши заказы")
    tasks = get_all_tasks()
    my_tasks = tasks[tasks['client_id'] == user_data['id']]
    st.dataframe(my_tasks, use_container_width=True)

# --- ИНТЕРФЕЙС ИСПОЛНИТЕЛЯ ---
else:
    st.header("🧑‍💻 Режим Исполнителя")
    tasks = get_all_tasks()
    available_tasks = tasks[tasks['status'] == 'Доступно']

    if available_tasks.empty:
        st.info("Нет доступных заданий.")
    
    for idx, row in available_tasks.iterrows():
        with st.container(border=True):
            cols = st.columns([3, 1])
            cols[0].write(f"**{row['title']}** — {row['reward']} MDL")
            
            # Логика кнопки
            if row['client_id'] == user_data['id']:
                cols[1].info("Ваш заказ")
            else:
                if cols[1].button("Взять", key=f"btn_{row['id']}"):
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute("UPDATE tasks SET status='В работе', worker_id=? WHERE id=?", 
                                   (user_data['id'], row['id']))
                    # Снимаем деньги с заказчика или блокируем их (логика зависит от вас)
                    conn.commit()
                    conn.close()
                    st.success("Заказ взят!")
                    st.rerun()
