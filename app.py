import streamlit as st
import pandas as pd
import sqlite3

# --- РАБОТА С БАЗОЙ ДАННЫХ (SQL) ---
def init_db():
    """Создает файл базы данных v4 с поддержкой профилей"""
    conn = sqlite3.connect("taskearn_v4.db")
    cursor = conn.cursor()
    
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
            client_name TEXT DEFAULT 'Аноним'
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
    
    # Таблица для профилей пользователей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            role TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            about TEXT,
            rating REAL DEFAULT 5.0
        )
    """)
    # Заполняем дефолтные профили, если их нет
    cursor.execute("INSERT OR IGNORE INTO profiles (role, name, phone, about, rating) VALUES ('client', 'Ион Чебан', '+373 68 XXXXXX', 'Заказчик из Кишинева. Ценю скорость.', 5.0)")
    cursor.execute("INSERT OR IGNORE INTO profiles (role, name, phone, about, rating) VALUES ('worker', 'Михаил Лупу', '+373 79 XXXXXX', 'Студент, берусь за любую подработку. Есть машина.', 5.0)")
    
    # Стартовые задачи
    cursor.execute("SELECT COUNT(*) FROM tasks")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO tasks (title, reward, status, city, village, category, client_name) 
            VALUES ('Помочь собрать урожай черешни', 300.0, 'Доступно', 'Комрат', 'село Конгаз', '🛠️ Ремонт и дом', 'Ион Чебан')
        """)
        cursor.execute("""
            INSERT INTO tasks (title, reward, status, city, village, category, client_name) 
            VALUES ('Привезти лекарства из аптеки', 120.0, 'Доступно', 'Оргеев', 'село Пересечино', '📦 Доставка', 'Ион Чебан')
        """)
        
    conn.commit()
    conn.close()

# Функции для профилей
def get_profile(role_type):
    conn = sqlite3.connect("taskearn_v4.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name, phone, about, rating FROM profiles WHERE role=?", (role_type,))
    res = cursor.fetchone()
    conn.close()
    if res:
        return {"name": res[0], "phone": res[1], "about": res[2], "rating": res[3]}
    return {"name": "Не указано", "phone": "", "about": "", "rating": 5.0}

def update_profile(role_type, name, phone, about):
    conn = sqlite3.connect("taskearn_v4.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE profiles SET name=?, phone=?, about=? WHERE role=?", (name, phone, about, role_type))
    conn.commit()
    conn.close()

# Базовые функции балансов и задач
def get_balance(role_type):
    conn = sqlite3.connect("taskearn_v4.db")
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM balances WHERE role=?", (role_type,))
    res = cursor.fetchone()
    balance = res[0] if res else 0.0
    conn.close()
    return balance

def update_balance(role_type, amount):
    conn = sqlite3.connect("taskearn_v4.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE balances SET balance = balance + ? WHERE role=?", (amount, role_type))
    conn.commit()
    conn.close()

def add_task(title, reward, city, village, category, client_name):
    conn = sqlite3.connect("taskearn_v4.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tasks (title, reward, status, city, village, category, client_name) 
        VALUES (?, ?, 'Доступно', ?, ?, ?, ?)
    """, (title, reward, city, village, category, client_name))
    conn.commit()
    conn.close()

def get_tasks():
    conn = sqlite3.connect("taskearn_v4.db")
    df = pd.read_sql_query("SELECT * FROM tasks", conn)
    conn.close()
    return df

def complete_task(task_id, reward):
    conn = sqlite3.connect("taskearn_v4.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='Выполнено' WHERE id=?", (task_id,))
    cursor.execute("UPDATE balances SET balance = balance + ? WHERE role='worker'", (reward,))
    conn.commit()
    conn.close()

# Инициализируем базу данных v4
init_db()

CITIES = ["Все регионы", "Кишинёв", "Бельцы", "Комрат", "Кагул", "Оргеев", "Унгены", "Сороки", "Тирасполь"]
CATEGORIES = ["Все категории", "📦 Доставка", "🛠️ Ремонт и дом", "💻 IT и Тексты", "🚗 Автоуслуги", "Другое"]

# --- ИНТЕРФЕЙС STREAMLIT ---
st.set_page_config(page_title="TaskEarn MDL", page_icon="🇲🇩", layout="centered")

st.title("🇲🇩 TaskEarn — Микрозадачи с Профилями")
st.write("---")

role = st.sidebar.radio("Выберите вашу роль:", ["💼 Заказчик", "🧑‍💻 Исполнитель"])

balance_client = get_balance("client")
balance_worker = get_balance("worker")

# Получаем текущий профиль в зависимости от роли
profile_data = get_profile("client" if role == "💼 Заказчик" else "worker")

if role == "💼 Заказчик":
    st.sidebar.metric(label="Баланс Заказчика", value=f"{balance_client} MDL")
    st.sidebar.write(f"👤 Профиль: **{profile_data['name']}**")
    st.sidebar.write(f"⭐ Рейтинг: `{profile_data['rating']} / 5.0`")
    st.sidebar.write("---")
    st.sidebar.subheader("💳 Тест оплаты")
    if st.sidebar.button("Пополнить баланс на +500 MDL"):
        update_balance("client", 500.0)
        st.sidebar.success("Карта имитирована: +500 MDL!")
        st.rerun()
else:
    st.sidebar.metric(label="Баланс Исполнителя", value=f"{balance_worker} MDL")
    st.sidebar.write(f"👤 Профиль: **{profile_data['name']}**")
    st.sidebar.write(f"⭐ Рейтинг: `{profile_data['rating']} / 5.0`")

# --- ЛОГИКА ЗАКАЗЧИКА ---
if role == "💼 Заказчик":
    tab_tasks, tab_profile = st.tabs(["📋 Мои задания", "👤 Настройка профиля"])
    
    with tab_tasks:
        st.header("Управление заданиями")
        with st.form("new_task_form", clear_on_submit=True):
            st.subheader("➕ Разместить новое задание")
            task_title = st.text_input("Что нужно сделать?")
            task_city = st.selectbox("Ближайший город/райцентр:", CITIES[1:])
            task_village = st.text_input("Уточните населённый пункт (село, коммуна, улица):", placeholder="Например: село Копчак")
            task_category = st.selectbox("Категория:", CATEGORIES[1:])
            task_reward = st.number_input("Оплата исполнителю (MDL)", min_value=20, value=100, step=10)
            submit = st.form_submit_button("Опубликовать и заблокировать оплату")
            
            if submit and task_title:
                if balance_client >= task_reward:
                    loc_village = task_village.strip() if task_village.strip() else "город"
                    update_balance("client", -task_reward)
                    # Передаем имя заказчика из его профиля
                    add_task(task_title, task_reward, task_city, loc_village, task_category, profile_data['name'])
                    st.success("Задание успешно опубликовано!")
                    st.rerun()
                else:
                    st.error("Недостаточно средств!")

        st.write("---")
        st.subheader("📋 Все задания в системе")
        df_tasks = get_tasks()
        if not df_tasks.empty:
            st.dataframe(df_tasks[["id", "title", "city", "village", "category", "reward", "status", "client_name"]], use_container_width=True)

    with tab_profile:
        st.header("👤 Редактировать профиль Заказчика")
        with st.form("client_profile_form"):
            new_name = st.text_input("Ваше имя / Название компании:", value=profile_data['name'])
            new_phone = st.text_input("Телефон для связи:", value=profile_data['phone'])
            new_about = st.text_area("О себе / Описание:", value=profile_data['about'])
            save_profile = st.form_submit_button("Сохранить изменения")
            
            if save_profile:
                update_profile("client", new_name, new_phone, new_about)
                st.success("Профиль заказчика успешно обновлен!")
                st.rerun()

# --- ЛОГИКА ИСПОЛНИТЕЛЯ ---
elif role == "🧑‍💻 Исполнитель":
    tab_tasks, tab_withdraw, tab_profile = st.tabs(["📋 Доступные задания", "💸 Вывод средств", "👤 Настройка профиля"])
    
    with tab_tasks:
        st.header("Доступные задания для заработка")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            filter_city = st.selectbox("📍 Фильтр по региону:", CITIES)
        with col_f2:
            filter_cat = st.selectbox("📁 Фильтр по категории:", CATEGORIES)
        
        df_tasks = get_tasks()
        if df_tasks.empty:
            st.info("В базе данных пока нет заданий.")
        else:
            df_filtered = df_tasks[df_tasks["status"] == "Доступно"]
            if filter_city != "Все регионы":
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
                            st.caption(f"📍 {task['city']} ({task['village']}) | 📁 {task['category']}")
                            st.write(f"💼 Заказчик: **{task['client_name']}**")
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
            card_number = st.text_input("Номер карты Молдовы:", placeholder="4000 1234 5678 9010")
            withdraw_amount = st.number_input("Сумма для вывода (MDL):", min_value=50, max_value=5000, value=100, step=50)
            submit_withdraw = st.form_submit_button("Запросить вывод средств")
            
            if submit_withdraw:
                if not card_number:
                    st.error("Пожалуйста, введите номер карты!")
                elif balance_worker < withdraw_amount:
                    st.error("На вашем балансе недостаточно средств!")
                else:
                    update_balance("worker", -withdraw_amount)
                    st.success(f"🎉 Заявка на вывод {withdraw_amount} MDL успешно создана!")
                    st.rerun()

    with tab_profile:
        st.header("👤 Редактировать профиль Исполнителя")
        with st.form("worker_profile_form"):
            new_name = st.text_input("Ваше имя / Никнейм:", value=profile_data['name'])
            new_phone = st.text_input("Телефон для связи:", value=profile_data['phone'])
            new_about = st.text_area("Ваши навыки / О себе:", value=profile_data['about'])
            save_profile = st.form_submit_button("Сохранить изменения")
            
            if save_profile:
                update_profile("worker", new_name, new_phone, new_about)
                st.success("Профиль исполнителя успешно обновлен!")
                st.rerun()
    
