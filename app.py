import streamlit as st
import pandas as pd
import sqlite3

# --- РАБОТА С БАЗОЙ ДАННЫХ (SQL) ---
def init_db():
    """Создает файл базы данных и таблицы, если их еще нет"""
    conn = sqlite3.connect("taskearn.db")
    cursor = conn.cursor()
    # Таблица для заданий
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            reward REAL NOT NULL,
            status TEXT NOT NULL
        )
    """)
    # Таблица для балансов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS balances (
            role TEXT PRIMARY KEY,
            balance REAL
        )
    """)
    # Заполняем стартовые балансы, если таблица пустая
    cursor.execute("INSERT OR IGNORE INTO balances (role, balance) VALUES ('client', 500.0)")
    cursor.execute("INSERT OR IGNORE INTO balances (role, balance) VALUES ('worker', 0.0)")
    
    # Добавим тестовые задачи, если база совсем пустая
    cursor.execute("SELECT COUNT(*) FROM tasks")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO tasks (title, reward, status) VALUES ('Купить и привезти продукты (Кишинев)', 150.0, 'Доступно')")
        cursor.execute("INSERT INTO tasks (title, reward, status) VALUES ('Перевести текст с румынского на русский', 200.0, 'Доступно')")
        
    conn.commit()
    conn.close()

def get_balance(role_type):
    conn = sqlite3.connect("taskearn.db")
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM balances WHERE role=?", (role_type,))
    res = cursor.fetchone()
    balance = res[0] if res else 0.0
    conn.close()
    return balance

def update_balance(role_type, amount):
    conn = sqlite3.connect("taskearn.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE balances SET balance = balance + ? WHERE role=?", (amount, role_type))
    conn.commit()
    conn.close()

def add_task(title, reward):
    conn = sqlite3.connect("taskearn.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (title, reward, status) VALUES (?, ?, 'Доступно')", (title, reward))
    conn.commit()
    conn.close()

def get_tasks():
    conn = sqlite3.connect("taskearn.db")
    df = pd.read_sql_query("SELECT * FROM tasks", conn)
    conn.close()
    return df

def complete_task(task_id, reward):
    conn = sqlite3.connect("taskearn.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='Выполнено' WHERE id=?", (task_id,))
    cursor.execute("UPDATE balances SET balance = balance + ? WHERE role='worker'", (reward,))
    conn.commit()
    conn.close()

# Инициализируем базу при запуске приложения
init_db()

# --- ИНТЕРФЕЙС STREAMLIT ---
st.set_page_config(page_title="TaskEarn MDL", page_icon="🇲🇩", layout="centered")

st.title("🇲🇩 TaskEarn — Заработок на микрозадачах в Молдове")
st.write("---")

role = st.sidebar.radio("Выберите вашу роль:", ["💼 Заказчик", "🧑‍💻 Исполнитель"])

# Подтягиваем балансы напрямую из SQL
balance_client = get_balance("client")
balance_worker = get_balance("worker")

if role == "💼 Заказчик":
    st.sidebar.metric(label="Баланс Заказчика", value=f"{balance_client} MDL")
    st.sidebar.write("---")
    st.sidebar.subheader("💳 Тест оплаты")
    if st.sidebar.button("Пополнить баланс на +500 MDL"):
        update_balance("client", 500.0)
        st.sidebar.success("Карта имитирована: +500 MDL!")
        st.rerun()
else:
    st.sidebar.metric(label="Баланс Исполнителя", value=f"{balance_worker} MDL")

# --- ЛОГИКА ЗАКАЗЧИКА ---
if role == "💼 Заказчик":
    st.header("Управление заданиями")
    
    with st.form("new_task_form", clear_on_submit=True):
        st.subheader("➕ Разместить новое задание")
        task_title = st.text_input("Что нужно сделать?")
        task_reward = st.number_input("Оплата исполнителю (MDL)", min_value=20, value=100, step=10)
        submit = st.form_submit_button("Опубликовать и заблокировать оплату")
        
        if submit and task_title:
            if balance_client >= task_reward:
                update_balance("client", -task_reward)
                add_task(task_title, task_reward)
                st.success(f"Задание опубликовано! {task_reward} MDL заморожены в БД.")
                st.rerun()
            else:
                st.error("Недостаточно средств на балансе!")

    st.write("---")
    st.subheader("📋 Ваши задания в системе (из Базы Данных)")
    df_tasks = get_tasks()
    if not df_tasks.empty:
        st.dataframe(df_tasks[["id", "title", "reward", "status"]], use_container_width=True)

# --- ЛОГИКА ИСПОЛНИТЕЛЯ ---
elif role == "🧑‍💻 Исполнитель":
    st.header("Доступные задания для заработка")
    
    df_tasks = get_tasks()
    if df_tasks.empty:
        available_tasks = []
    else:
        available_tasks = df_tasks[df_tasks["status"] == "Доступно"].to_dict(orient="records")
    
    if not available_tasks:
        st.info("На данный момент нет доступных заданий.")
    else:
        for task in available_tasks:
            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"{task['title']}")
                    st.write(f"💰 Награда: {task['reward']} MDL (ID: {task['id']})")
                with col2:
                    if st.button(f"Выполнить", key=f"b_{task['id']}", use_container_width=True):
                        complete_task(task["id"], task["reward"])
                        st.success(f"Зачислено {task['reward']} MDL.")
                        st.rerun()
                st.write("---")
