import streamlit as st
import pandas as pd
import sqlite3

# --- РАБОТА С БАЗОЙ ДАННЫХ (SQL) ---
def init_db():
    """Создает абсолютно новый файл базы данных v2 и таблицы без конфликтов структуры"""
    conn = sqlite3.connect("taskearn_v2.db")
    cursor = conn.cursor()
    # Таблица для заданий (сразу со всеми нужными колонками)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            reward REAL NOT NULL,
            status TEXT NOT NULL,
            city TEXT NOT NULL,
            category TEXT NOT NULL
        )
    """)
    # Таблица для балансов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS balances (
            role TEXT PRIMARY KEY,
            balance REAL
        )
    """)
    cursor.execute("INSERT OR IGNORE INTO balances (role, balance) VALUES ('client', 500.0)")
    cursor.execute("INSERT OR IGNORE INTO balances (role, balance) VALUES ('worker', 0.0)")
    
    # Стартовые задачи для демонстрации
    cursor.execute("SELECT COUNT(*) FROM tasks")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO tasks (title, reward, status, city, category) VALUES ('Купить и привезти продукты', 150.0, 'Доступно', 'Кишинёв', '📦 Доставка')")
        cursor.execute("INSERT INTO tasks (title, reward, status, city, category) VALUES ('Перевести текст с румынского', 200.0, 'Доступно', 'Бельцы', '💻 IT и Тексты')")
        
    conn.commit()
    conn.close()

def get_balance(role_type):
    conn = sqlite3.connect("taskearn_v2.db")
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM balances WHERE role=?", (role_type,))
    res = cursor.fetchone()
    balance = res[0] if res else 0.0
    conn.close()
    return balance

def update_balance(role_type, amount):
    conn = sqlite3.connect("taskearn_v2.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE balances SET balance = balance + ? WHERE role=?", (amount, role_type))
    conn.commit()
    conn.close()

def add_task(title, reward, city, category):
    conn = sqlite3.connect("taskearn_v2.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (title, reward, status, city, category) VALUES (?, ?, 'Доступно', ?, ?)", (title, reward, city, category))
    conn.commit()
    conn.close()

def get_tasks():
    conn = sqlite3.connect("taskearn_v2.db")
    df = pd.read_sql_query("SELECT * FROM tasks", conn)
    conn.close()
    return df

def complete_task(task_id, reward):
    conn = sqlite3.connect("taskearn_v2.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='Выполнено' WHERE id=?", (task_id,))
    cursor.execute("UPDATE balances SET balance = balance + ? WHERE role='worker'", (reward,))
    conn.commit()
    conn.close()

# Инициализируем чистую базу
init_db()

CITIES = ["Все города", "Кишинёв", "Бельцы", "Комрат", "Кагул", "Тирасполь", "Бендеры", "Оргеев"]
CATEGORIES = ["Все категории", "📦 Доставка", "🛠️ Ремонт и дом", "💻 IT и Тексты", "🚗 Автоуслуги", "Другое"]

# --- ИНТЕРФЕЙС STREAMLIT ---
st.set_page_config(page_title="TaskEarn MDL", page_icon="🇲🇩", layout="centered")

st.title("🇲🇩 TaskEarn — Микрозадачи в Молдове")
st.write("---")

role = st.sidebar.radio("Выберите вашу роль:", ["💼 Заказчик", "🧑‍💻 Исполнитель"])

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
        task_city = st.selectbox("Город выполнения:", CITIES[1:])
        task_category = st.selectbox("Категория:", CATEGORIES[1:])
        task_reward = st.number_input("Оплата исполнителю (MDL)", min_value=20, value=100, step=10)
        submit = st.form_submit_button("Опубликовать и заблокировать оплату")
        
        if submit and task_title:
            if balance_client >= task_reward:
                update_balance("client", -task_reward)
                add_task(task_title, task_reward, task_city, task_category)
                st.success(f"Задание опубликовано для г. {task_city}!")
                st.rerun()
            else:
                st.error("Недостаточно средств!")

    st.write("---")
    st.subheader("📋 Все задания в системе")
    df_tasks = get_tasks()
    if not df_tasks.empty:
        st.dataframe(df_tasks[["id", "title", "city", "category", "reward", "status"]], use_container_width=True)

# --- ЛОГИКА ИСПОЛНИТЕЛЯ ---
elif role == "🧑‍💻 Исполнитель":
    tab_tasks, tab_withdraw = st.tabs(["📋 Доступные задания", "💸 Вывод средств"])
    
    with tab_tasks:
        st.header("Доступные задания для заработка")
        
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            filter_city = st.selectbox("📍 Фильтр по городу:", CITIES)
        with col_f2:
            filter_cat = st.selectbox("📁 Фильтр по категории:", CATEGORIES)
        
        df_tasks = get_tasks()
        
        if df_tasks.empty:
            st.info("В базе данных пока нет заданий.")
        else:
            df_filtered = df_tasks[df_tasks["status"] == "Доступно"]
            if filter_city != "Все города":
                df_filtered = df_filtered[df_filtered["city"] == filter_city]
            if filter_cat != "Все категории":
                df_filtered = df_filtered[df_filtered["category"] == filter_cat]
                
            available_tasks = df_filtered.to_dict(orient="records")
            
            if not available_tasks:
                st.info("Нет заданий, соответствующих выбранным фильтрам.")
            else:
                for task in available_tasks:
                    with st.container():
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"**{task['title']}**")
                            st.caption(f"📍 {task['city']} | 📁 {task['category']}")
                            st.write(f"💰 Награда: `{task['reward']} MDL`")
                        with col2:
                            if st.button(f"Выполнить", key=f"b_{task['id']}", use_container_width=True):
                                complete_task(task["id"], task["reward"])
                                st.success(f"Выполнено! Получено {task['reward']} MDL.")
                                st.rerun()
                        st.write("---")
                        
    with tab_withdraw:
        st.header("💸 Вывод заработанных леев")
        st.write(f"Ваш текущий баланс: **{balance_worker} MDL**")
        
        with st.form("withdraw_form", clear_on_submit=True):
            card_number = st.text_input("Номер карты Молдовы (или кошелька RunPay/BPay):", placeholder="4000 1234 5678 9010")
            withdraw_amount = st.number_input("Сумма для вывода (MDL):", min_value=50, max_value=5000, value=100, step=50)
            submit_withdraw = st.form_submit_button("Запросить вывод средств")
            
            if submit_withdraw:
                if not card_number:
                    st.error("Пожалуйста, введите номер карты или кошелька!")
                elif balance_worker < withdraw_amount:
                    st.error("На вашем балансе недостаточно средств!")
                else:
                    update_balance("worker", -withdraw_amount)
                    st.success(f"🎉 Заявка на вывод {withdraw_amount} MDL успешно создана! Деньги будут зачислены на карту {card_number[:4]}**** в течение 15 минут.")
                    st.rerun()
                    
