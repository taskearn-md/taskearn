import streamlit as st
import pandas as pd
import sqlite3

# --- РАБОТА С БАЗОЙ ДАННЫХ (SQL) ---
def init_db():
    """Создает базу данных v5 с системой проверки задач, контактами, отменой и отзывом свободных задач"""
    conn = sqlite3.connect("taskearn_v5.db")
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
            client_name TEXT DEFAULT 'Аноним',
            worker_name TEXT DEFAULT '',
            cancel_reason TEXT DEFAULT ''
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
    
    # Таблица для профилей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            role TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            about TEXT,
            rating REAL DEFAULT 5.0,
            rating_count INTEGER DEFAULT 1
        )
    """)
    cursor.execute("INSERT OR IGNORE INTO profiles (role, name, phone, about, rating, rating_count) VALUES ('client', 'Ион Чебан', '+373 68 123 456', 'Заказчик из Кишинева.', 5.0, 1)")
    cursor.execute("INSERT OR IGNORE INTO profiles (role, name, phone, about, rating, rating_count) VALUES ('worker', 'Михаил Лупу', '+373 79 987 654', 'Исполнитель из Комрата.', 5.0, 1)")
    
    conn.commit()
    conn.close()

def get_profile(role_type):
    conn = sqlite3.connect("taskearn_v5.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name, phone, about, rating FROM profiles WHERE role=?", (role_type,))
    res = cursor.fetchone()
    conn.close()
    if res:
        return {"name": res[0], "phone": res[1], "about": res[2], "rating": round(res[3], 1)}
    return {"name": "Не указано", "phone": "", "about": "", "rating": 5.0}

def get_profile_by_name(name):
    conn = sqlite3.connect("taskearn_v5.db")
    cursor = conn.cursor()
    cursor.execute("SELECT phone, rating FROM profiles WHERE name=?", (name,))
    res = cursor.fetchone()
    conn.close()
    if res:
        return {"phone": res[0], "rating": round(res[1], 1)}
    return {"phone": "Не указан", "rating": 5.0}

def update_profile(role_type, name, phone, about):
    conn = sqlite3.connect("taskearn_v5.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE profiles SET name=?, phone=?, about=? WHERE role=?", (name, phone, about, role_type))
    conn.commit()
    conn.close()

def update_rating(role_type, new_score):
    conn = sqlite3.connect("taskearn_v5.db")
    cursor = conn.cursor()
    cursor.execute("SELECT rating, rating_count FROM profiles WHERE role=?", (role_type,))
    res = cursor.fetchone()
    if res:
        current_rating, count = res[0], res[1]
        new_count = count + 1
        updated_rating = ((current_rating * count) + new_score) / new_count
        cursor.execute("UPDATE profiles SET rating=?, rating_count=? WHERE role=?", (updated_rating, new_count, role_type))
    conn.commit()
    conn.close()

def get_balance(role_type):
    conn = sqlite3.connect("taskearn_v5.db")
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM balances WHERE role=?", (role_type,))
    res = cursor.fetchone()
    balance = res[0] if res else 0.0
    conn.close()
    return balance

def update_balance(role_type, amount):
    conn = sqlite3.connect("taskearn_v5.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE balances SET balance = balance + ? WHERE role=?", (amount, role_type))
    conn.commit()
    conn.close()

def add_task(title, reward, city, village, category, client_name):
    conn = sqlite3.connect("taskearn_v5.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tasks (title, reward, status, city, village, category, client_name) 
        VALUES (?, ?, 'Доступно', ?, ?, ?, ?)
    """, (title, reward, city, village, category, client_name))
    conn.commit()
    conn.close()

def get_tasks():
    conn = sqlite3.connect("taskearn_v5.db")
    df = pd.read_sql_query("SELECT * FROM tasks", conn)
    conn.close()
    return df

def revoke_free_task(task_id):
    """Полное удаление свободного задания из базы данных"""
    conn = sqlite3.connect("taskearn_v5.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()
    conn.close()

def send_to_review(task_id, worker_name):
    conn = sqlite3.connect("taskearn_v5.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='На проверке', worker_name=? WHERE id=?", (worker_name, task_id))
    conn.commit()
    conn.close()

def approve_task(task_id, reward):
    conn = sqlite3.connect("taskearn_v5.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='Выполнено' WHERE id=?", (task_id,))
    cursor.execute("UPDATE balances SET balance = balance + ? WHERE role='worker'", (reward,))
    conn.commit()
    conn.close()

def cancel_task_with_reason(task_id, reward, reason):
    conn = sqlite3.connect("taskearn_v5.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='Отменено', cancel_reason=? WHERE id=?", (reason, task_id))
    cursor.execute("UPDATE balances SET balance = balance + ? WHERE role='client'", (reward,))
    conn.commit()
    conn.close()

# Запуск БД
init_db()

CITIES = ["Все регионы", "Кишинёв", "Бельцы", "Комрат", "Кагул", "Оргеев", "Унгены", "Сороки", "Тирасполь"]
CATEGORIES = ["Все категории", "📦 Доставка", "🛠️ Ремонт и дом", "💻 IT и Тексты", "🚗 Автоуслуги", "Другое"]

# --- ИНТЕРФЕЙС ---
st.set_page_config(page_title="TaskEarn MDL", page_icon="🇲🇩", layout="centered")

st.title("🇲🇩 TaskEarn — Микрозадачи и Заработок")
st.write("---")

role = st.sidebar.radio("Выберите вашу роль:", ["💼 Заказчик", "🧑‍💻 Исполнитель"])

balance_client = get_balance("client")
balance_worker = get_balance("worker")
profile_data = get_profile("client" if role == "💼 Заказчик" else "worker")

# Сайдбар профиля
st.sidebar.metric(label="Ваш баланс", value=f"{balance_client if role == '💼 Заказчик' else balance_worker} MDL")
st.sidebar.write(f"👤 Имя: **{profile_data['name']}**")
st.sidebar.write(f"⭐ Рейтинг: `{profile_data['rating']} / 5.0`")
st.sidebar.write("---")

if role == "💼 Заказчик":
    if st.sidebar.button("Пополнить баланс на +500 MDL"):
        update_balance("client", 500.0)
        st.sidebar.success("Баланс пополнен!")
        st.rerun()

# --- ЛОГИКА ЗАКАЗЧИКА ---
if role == "💼 Заказчик":
    tab_tasks, tab_review, tab_profile = st.tabs(["📋 Создать задание", "🔍 Проверка работ", "👤 Мой профиль"])
    
    with tab_tasks:
        st.header("Новое задание")
        with st.form("new_task_form", clear_on_submit=True):
            task_title = st.text_input("Что нужно сделать?")
            task_city = st.selectbox("Ближайший город/райцентр:", CITIES[1:])
            task_village = st.text_input("Уточните населённый пункт (село, коммуна, улица):")
            task_category = st.selectbox("Категория:", CATEGORIES[1:])
            task_reward = st.number_input("Оплата исполнителю (MDL)", min_value=20, value=100, step=10)
            submit = st.form_submit_button("Опубликовать и заблокировать оплату")
            
            if submit and task_title:
                if balance_client >= task_reward:
                    loc_village = task_village.strip() if task_village.strip() else "город"
                    update_balance("client", -task_reward)
                    add_task(task_title, task_reward, task_city, loc_village, task_category, profile_data['name'])
                    st.success("Опубликовано! Деньги заморожены системой.")
                    st.rerun()
                else:
                    st.error("Недостаточно средств!")

        st.write("---")
        st.subheader("Управление вашими задачами")
        df_tasks = get_tasks()
        
        if df_tasks.empty:
            st.info("Вы ещё не создавали заданий.")
        else:
            # Отфильтруем только задачи этого заказчика
            my_tasks = df_tasks[df_tasks["client_name"] == profile_data['name']].to_dict(orient="records")
            if not my_tasks:
                st.info("У вас нет активных заданий.")
            else:
                for task in my_tasks:
                    with st.container():
                        col_t1, col_t2 = st.columns([3, 1])
                        with col_t1:
                            st.write(f"**{task['title']}** — 💰 {task['reward']} MDL")
                            if task['status'] == 'Доступно':
                                st.caption(f"🟢 Статус: `В ленте (Свободно)` | 📍 {task['city']}")
                            elif task['status'] == 'На проверке':
                                st.caption(f"🟡 Статус: `В работе / На проверке` | Исполнитель: {task['worker_name']}")
                            else:
                                st.caption(f"⚫ Статус: `{task['status']}`")
                        
                        with col_t2:
                            # КНОПКА ОТЗЫВА ЗАДАНИЯ (Активна ТОЛЬКО если статус 'Доступно')
                            if task['status'] == 'Доступно':
                                if st.button("❌ Отозвать", key=f"rev_{task['id']}", use_container_width=True):
                                    revoke_free_task(task['id'])
                                    update_balance("client", task['reward']) # Возвращаем деньги назад на баланс
                                    st.success("Задание отозвано, деньги вернулись на баланс!")
                                    st.rerun()
                            elif task['status'] == 'На проверке':
                                st.button("🔒 Принято в работу", key=f"lock_{task['id']}", disabled=True, use_container_width=True)
                        st.write("-" * 10)

    with tab_review:
        st.header("🔍 Задания, ожидающие вашей проверки")
        df_tasks = get_tasks()
        
        if df_tasks.empty:
            st.info("Нет задач для проверки.")
        else:
            review_tasks = df_tasks[df_tasks["status"] == "На проверке"].to_dict(orient="records")
            if not review_tasks:
                st.info("Пока никто не прислал работы на проверку.")
            else:
                for task in review_tasks:
                    with st.container():
                        st.write(f"**{task['title']}** ({task['reward']} MDL)")
                        
                        worker_info = get_profile_by_name(task['worker_name'])
                        st.success(f"🧑‍💻 Выполнил: **{task['worker_name']}** (⭐ {worker_info['rating']})")
                        st.info(f"📞 Телефон для связи с исполнителем: **{worker_info['phone']}**")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.subheader("Успешное выполнение")
                            rating_score = st.slider("Оцените качество работы:", 1, 5, 5, key=f"score_{task['id']}")
                            if st.button("✅ Принять работу", key=f"app_{task['id']}", use_container_width=True):
                                approve_task(task["id"], task["reward"])
                                update_rating("worker", rating_score)
                                st.success("Работа принята, оплата переведена!")
                                st.rerun()
                                
                        with col2:
                            st.subheader("Отказ и Спор")
                            show_form_key = f"show_form_{task['id']}"
                            if show_form_key not in st.session_state:
                                st.session_state[show_form_key] = False
                                
                            if st.button("❌ Работа не выполнена", key=f"btn_fail_{task['id']}", use_container_width=True):
                                st.session_state[show_form_key] = True
                                
                            if st.session_state[show_form_key]:
                                with st.form(key=f"cancel_form_{task['id']}"):
                                    evidence = st.text_area("Доказательства (почему отменяете?):", 
                                                           placeholder="Например: Исполнитель не приехал на объект...")
                                    submit_cancel = st.form_submit_button("🚨 Подтвердить отмену и снизить ему рейтинг")
                                    
                                    if submit_cancel:
                                        if len(evidence.strip()) < 10:
                                            st.error("Пожалуйста, распишите доказательства подробнее!")
                                        else:
                                            cancel_task_with_reason(task["id"], task["reward"], evidence.strip())
                                            update_rating("worker", 1.0)
                                            st.success("Задание отменено, леи вернулись к вам. Рейтинг исполнителя снижен!")
                                            st.session_state[show_form_key] = False
                                            st.rerun()
                        st.write("---")

    with tab_profile:
        st.header("👤 Профиль")
        with st.form("c_prof"):
            n = st.text_input("Имя:", value=profile_data['name'])
            p = st.text_input("Телефон:", value=profile_data['phone'])
            a = st.text_area("О себе:", value=profile_data['about'])
            if st.form_submit_button("Сохранить"):
                update_profile("client", n, p, a)
                st.rerun()

# --- ЛОГИКА ИСПОЛНИТЕЛЯ ---
elif role == "🧑‍💻 Исполнитель":
    tab_tasks, tab_withdraw, tab_profile = st.tabs(["📋 Лента заданий", "💸 Вывод средств", "👤 Мой профиль"])
    
    with tab_tasks:
        st.header("Доступные задания")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            filter_city = st.selectbox("📍 Регион:", CITIES)
        with col_f2:
            filter_cat = st.selectbox("📁 Категория:", CATEGORIES)
            
        df_tasks = get_tasks()
        if df_tasks.empty:
            st.info("Заданий нет.")
        else:
            df_filtered = df_tasks[(df_tasks["status"] == "Доступно") | ((df_tasks["status"] == "На проверке") & (df_tasks["worker_name"] == profile_data['name']))]
            
            if filter_city != "Все регионы":
                df_filtered = df_filtered[df_filtered["city"] == filter_city]
            if filter_cat != "Все категории":
                df_filtered = df_filtered[df_filtered["category"] == filter_cat]
                
            available_tasks = df_filtered.to_dict(orient="records")
            if not available_tasks:
                st.info("Нет подходящих заданий.")
            else:
                for task in available_tasks:
                    with st.container():
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"**{task['title']}**")
                            st.caption(f"📍 {task['city']} ({task['village']}) | 📁 {task['category']}")
                            
                            if task['status'] == "На проверке":
                                client_info = get_profile_by_name(task['client_name'])
                                st.warning("Ожидает проверки заказчиком")
                                st.info(f"📞 Связаться с Заказчиком ({task['client_name']}): **{client_info['phone']}**")
                            else:
                                st.write(f"💼 Заказчик: {task['client_name']}")
                                
                            st.write(f"💰 Награда: `{task['reward']} MDL`")
                        with col2:
                            if task['status'] == "Доступно":
                                if st.button(f"Выполнить", key=f"b_{task['id']}", use_container_width=True):
                                    send_to_review(task["id"], profile_data['name'])
                                    st.warning("Отправлено на проверку!")
                                    st.rerun()
                            else:
                                st.button(f"⏳ Проверка", key=f"b_{task['id']}", disabled=True, use_container_width=True)
                        st.write("---")

    with tab_withdraw:
        st.header("💸 Вывод средств")
        st.write(f"Баланс: **{balance_worker} MDL**")
        with st.form("with_f"):
            card = st.text_input("Номер карты:")
            amount = st.number_input("Сумма:", min_value=50, value=100)
            if st.form_submit_button("Вывести"):
                if card and balance_worker >= amount:
                    update_balance("worker", -amount)
                    st.success("Заявка создана!")
                    st.rerun()
                else:
                    st.error("Ошибка параметров вывода.")

    with tab_profile:
        st.header("👤 Профиль")
        with st.form("w_prof"):
            n = st.text_input("Имя:", value=profile_data['name'])
            p = st.text_input("Телефон:", value=profile_data['phone'])
            a = st.text_area("Навыки:", value=profile_data['about'])
            if st.form_submit_button("Сохранить"):
                update_profile("worker", n, p, a)
                st.rerun()
                                
