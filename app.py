import streamlit as st
import pandas as pd
import sqlite3
import random

# --- НАСТРОЙКА ---
DB_NAME = "taskearn_final.db"
COMMISSION_RATE = 0.10

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            about TEXT,
            balance REAL DEFAULT 0.0,
            role TEXT DEFAULT 'user'
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            reward REAL NOT NULL,
            status TEXT NOT NULL,
            client_id INTEGER NOT NULL,
            worker_id INTEGER,
            FOREIGN KEY(client_id) REFERENCES users(id),
            FOREIGN KEY(worker_id) REFERENCES users(id)
        )
    """)
    # Тестовые данные
    cursor.execute("INSERT OR IGNORE INTO users (id, name, phone, balance, role) VALUES (1, 'Ион (Тест)', '+37368123456', 1000.0, 'user')")
    cursor.execute("INSERT OR IGNORE INTO users (id, name, phone, balance, role) VALUES (2, 'Михаил (Тест)', '+37379987654', 0.0, 'user')")
    conn.commit()
    conn.close()

# --- ФУНКЦИИ ---
def get_user_by_id(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    return {"id": res[0], "name": res[1], "phone": res[2], "about": res[3], "balance": res[4]} if res else None

def get_tasks():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM tasks", conn)
    conn.close()
    return df

# --- ИНИЦИАЛИЗАЦИЯ ---
init_db()
st.set_page_config(page_title="TaskEarn", layout="centered")

# Состояния сессии
if "logged_in_user_id" not in st.session_state: st.session_state["logged_in_user_id"] = None
if "active_mode" not in st.session_state: st.session_state["active_mode"] = "Заказчик"

# --- ЛОГИКА ВХОДА ---
if st.session_state["logged_in_user_id"] is None:
    st.title("🇲🇩 Вход в TaskEarn")
    phone = st.text_input("Введите телефон (для теста: +37368123456 или +37379987654):")
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

# --- ОСНОВНОЙ ИНТЕРФЕЙС ---
user_data = get_user_by_id(st.session_state["logged_in_user_id"])

# ИСПРАВЛЕНИЕ ОШИБКИ: Проверка на существование данных
if user_data is None:
    st.error("Ошибка: Пользователь не найден. Пожалуйста, перезалогиньтесь.")
    if st.button("Выйти и войти снова"):
        st.session_state["logged_in_user_id"] = None
        st.rerun()
    st.stop()

# Сайдбар
st.sidebar.header("Панель управления")
st.sidebar.write(f"👤 **{user_data['name']}**")
st.sidebar.write(f"💰 Баланс: {user_data['balance']} MDL")

# Переключатель режимов
st.session_state["active_mode"] = st.sidebar.radio(
    "Выберите режим:", ["Заказчик", "Исполнитель"], key="mode_switch"
)

if st.sidebar.button("Выйти из системы"):
    st.session_state["logged_in_user_id"] = None
    st.rerun()

# --- РОЛЕВАЯ ЛОГИКА ---
if st.session_state["active_mode"] == "Заказчик":
    st.header("📋 Режим Заказчика")
    with st.form("new_task"):
        title = st.text_input("Название задания")
        reward = st.number_input("Оплата (MDL)", value=100)
        if st.form_submit_button("Опубликовать"):
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO tasks (title, reward, status, client_id) VALUES (?, ?, 'Доступно', ?)", 
                           (title, reward, user_data['id']))
            conn.commit()
            conn.close()
            st.success("Задание в ленте!")
            st.rerun()
    
    st.subheader("Ваши заказы")
    df = get_tasks()
    my_tasks = df[df["client_id"] == user_data['id']]
    st.dataframe(my_tasks)

elif st.session_state["active_mode"] == "Исполнитель":
    st.header("🧑‍💻 Режим Исполнителя")
    st.subheader("Лента заданий")
    
    df = get_tasks()
    tasks = df[df["status"] == "Доступно"].to_dict(orient="records")
    
    for task in tasks:
        with st.container():
            st.write(f"**{task['title']}** — {task['reward']} MDL")
            
            # --- ЗАЩИТА ОТ САМОИСПОЛНЕНИЯ ---
            if task['client_id'] == user_data['id']:
                st.info("🔒 Это ваш заказ. Вы не можете выполнить его сами.")
            else:
                if st.button(f"Взять заказ №{task['id']}", key=f"btn_{task['id']}"):
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute("UPDATE tasks SET status='В работе', worker_id=? WHERE id=?", 
                                   (user_data['id'], task['id']))
                    conn.commit()
                    conn.close()
                    st.success("Заказ взят в работу!")
                    st.rerun()
            st.divider()
