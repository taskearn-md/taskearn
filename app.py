import streamlit as st
import pandas as pd
import sqlite3

# --- РАБОТА С БАЗОЙ ДАННЫХ (SQL) ---
def init_db():
    """Создает чистую базу данных с отзывами, штрафами заказчиков и мягким падением рейтинга"""
    conn = sqlite3.connect("taskearn_v14.db")
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
            rating_count INTEGER DEFAULT 1,
            tasks_created INTEGER DEFAULT 0,
            tasks_canceled INTEGER DEFAULT 0
        )
    """)
    cursor.execute("INSERT OR IGNORE INTO profiles (role, name, phone, about, rating, rating_count, tasks_created, tasks_canceled) VALUES ('client', 'Ион Чебан', '+373 68 123 456', 'Заказчик из Кишинева.', 5.0, 1, 0, 0)")
    cursor.execute("INSERT OR IGNORE INTO profiles (role, name, phone, about, rating, rating_count, tasks_created, tasks_canceled) VALUES ('worker', 'Михаил Лупу', '+373 79 987 654', 'Иполнитель из Комрата.', 5.0, 1, 0, 0)")
    
    # Таблица для текстовых отзывов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_name TEXT NOT NULL,
            author_name TEXT NOT NULL,
            score REAL NOT NULL,
            comment TEXT NOT NULL
        )
    """)
    
    conn.commit()
    conn.close()

def get_profile(role_type):
    conn = sqlite3.connect("taskearn_v14.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name, phone, about, rating, tasks_created, tasks_canceled FROM profiles WHERE role=?", (role_type,))
    res = cursor.fetchone()
    conn.close()
    if res:
        return {
            "name": res[0], "phone": res[1], "about": res[2], 
            "rating": round(res[3], 1), "created": res[4], "canceled": res[5]
        }
    return {"name": "Не указано", "phone": "", "about": "", "rating": 5.0, "created": 0, "canceled": 0}

def get_profile_by_name(name):
    conn = sqlite3.connect("taskearn_v14.db")
    cursor = conn.cursor()
    cursor.execute("SELECT phone, rating, role FROM profiles WHERE name=?", (name,))
    res = cursor.fetchone()
    conn.close()
    if res:
        return {"phone": res[0], "rating": round(res[1], 1), "role": res[2]}
    return {"phone": "Не указан", "rating": 5.0, "role": "worker"}

def update_profile(role_type, name, phone, about):
    conn = sqlite3.connect("taskearn_v14.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE profiles SET name=?, phone=?, about=? WHERE role=?", (name, phone, about, role_type))
    conn.commit()
    conn.close()

def change_rating_flat(profile_name, penalty):
    """Мягкое изменение рейтинга на фиксированное число"""
    conn = sqlite3.connect("taskearn_v14.db")
    cursor = conn.cursor()
    cursor.execute("SELECT rating FROM profiles WHERE name=?", (profile_name,))
    res = cursor.fetchone()
    if res:
        new_rating = max(1.0, min(5.0, res[0] + penalty))
        cursor.execute("UPDATE profiles SET rating=? WHERE name=?", (new_rating, profile_name))
    conn.commit()
    conn.close()

def update_rating_stars(role_type, new_score):
    """Классический пересчет рейтинга по звездам (1-5) при успешном выполнении"""
    conn = sqlite3.connect("taskearn_v14.db")
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

def add_review(target_name, author_name, score, comment):
    conn = sqlite3.connect("taskearn_v14.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO reviews (target_name, author_name, score, comment) VALUES (?, ?, ?, ?)", 
                   (target_name, author_name, score, comment))
    conn.commit()
    conn.close()

def get_reviews_for(name):
    conn = sqlite3.connect("taskearn_v14.db")
    df = pd.read_sql_query("SELECT author_name, score, comment FROM reviews WHERE target_name=?", conn, params=(name,))
    conn.close()
    return df

def get_balance(role_type):
    conn = sqlite3.connect("taskearn_v14.db")
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM balances WHERE role=?", (role_type,))
    res = cursor.fetchone()
    balance = res[0] if res else 0.0
    conn.close()
    return balance

def update_balance(role_type, amount):
    conn = sqlite3.connect("taskearn_v14.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE balances SET balance = balance + ? WHERE role=?", (amount, role_type))
    conn.commit()
    conn.close()

def add_task(title, reward, city, village, category, client_name):
    conn = sqlite3.connect("taskearn_v14.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tasks (title, reward, status, city, village, category, client_name) 
        VALUES (?, ?, 'Доступно', ?, ?, ?, ?)
    """, (title, reward, city, village, category, client_name))
    cursor.execute("UPDATE profiles SET tasks_created = tasks_created + 1 WHERE name=?", (client_name,))
    conn.commit()
    conn.close()

def get_tasks():
    conn = sqlite3.connect("taskearn_v14.db")
    df = pd.read_sql_query("SELECT * FROM tasks", conn)
    conn.close()
    return df

def revoke_free_task(task_id):
    conn = sqlite3.connect("taskearn_v14.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()
    conn.close()

def worker_abandon_task(task_id):
    """Исполнитель отказывается от задачи, она снова возвращается в ленту свободной"""
    conn = sqlite3.connect("taskearn_v14.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='Доступно', worker_name='' WHERE id=?", (task_id,))
    conn.commit()
    conn.close()

def send_to_review(task_id, worker_name):
    conn = sqlite3.connect("taskearn_v14.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='На проверке', worker_name=? WHERE id=?", (worker_name, task_id))
    conn.commit()
    conn.close()

def approve_task(task_id, reward):
    conn = sqlite3.connect("taskearn_v14.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='Выполнено' WHERE id=?", (task_id,))
    cursor.execute("UPDATE balances SET balance = balance + ? WHERE role='worker'", (reward,))
    conn.commit()
    conn.close()

def cancel_task_with_reason(task_id, reward, reason, client_name):
    conn = sqlite3.connect("taskearn_v14.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='Отменено', cancel_reason=? WHERE id=?", (reason, task_id))
    cursor.execute("UPDATE balances SET balance = balance + ? WHERE role='client'", (reward,))
    cursor.execute("UPDATE profiles SET tasks_canceled = tasks_canceled + 1 WHERE name=?", (client_name,))
    conn.commit()
    conn.close()

# Запуск БД
init_db()

CITIES = ["Все регионы", "Кишинёв", "Бельцы", "Комрат", "Кагул", "Оргеев", "Унгены", "Сороки", "Тирасполь"]
CATEGORIES = ["Все категории", "📦 Доставка", "🛠️ Ремонт и дом", "💻 IT и Тексты", "🚗 Автоуслуги", "Другое"]

# --- ИНТЕРФЕЙС STREAMLIT ---
st.set_page_config(page_title="TaskEarn MDL", page_icon="🇲🇩", layout="centered")

st.title("🇲🇩 TaskEarn — Микрозадачи и Рейтинг")
st.write("---")

role = st.sidebar.radio("Выберите вашу роль:", ["💼 Заказчик", "🧑‍💻 Исполнитель"])

balance_client = get_balance("client")
balance_worker = get_balance("worker")
profile_data = get_profile("client" if role == "💼 Заказчик" else "worker")

# Сайдбар профиля
st.sidebar.metric(label="Ваш баланс", value=f"{balance_client if role == '💼 Заказчик' else balance_worker} MDL")
st.sidebar.write(f"👤 Имя: **{profile_data['name']}**")
st.sidebar.write(f"⭐ Рейтинг: `{profile_data['rating']} / 5.0`")
if role == "💼 Заказчик" and profile_data['created'] > 0:
    cancel_rate = (profile_data['canceled'] / profile_data['created']) * 100
    st.sidebar.caption(f"📊 Отменено заказов: {profile_data['canceled']} из {profile_data['created']} ({int(cancel_rate)}%)")
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
                            if task['status'] == 'Доступно':
                                if st.button("❌ Отозвать", key=f"rev_{task['id']}", use_container_width=True):
                                    revoke_free_task(task['id'])
                                    update_balance("client", task['reward'])
                                    st.success("Задание отозвано, деньги вернулись на баланс!")
                                    st.rerun()
                            elif task['status'] == 'На проверке':
                                st.button("🔒 В работе", key=f"lock_{task['id']}", disabled=True, use_container_width=True)
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
                            rating_score = st.slider("Оцените работу звездочками:", 1, 5, 5, key=f"score_{task['id']}")
                            review_text = st.text_input("Напишите отзыв исполнителю:", key=f"rev_txt_{task['id']}", placeholder="Отличная работа, всё быстро...")
                            
                            if st.button("✅ Принять работу", key=f"app_{task['id']}", use_container_width=True):
                                approve_task(task["id"], task["reward"])
                                update_rating_stars("worker", rating_score)
                                if review_text.strip():
                                    add_review(task['worker_name'], profile_data['name'], rating_score, review_text.strip())
                                st.success("Работа принята, оплата переведена и отзыв сохранен!")
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
                                    evidence = st.text_area("Доказательства (почему отменяете?):", placeholder="Исполнитель не справился с задачей...")
                                    submit_cancel = st.form_submit_button("🚨 Подтвердить отмену")
                                    
                                    if submit_cancel:
                                        if len(evidence.strip()) < 5:
                                            st.error("Пожалуйста, укажите причину отмены!")
                                        else:
                                            cancel_task_with_reason(task["id"], task["reward"], evidence.strip(), profile_data['name'])
                                            change_rating_flat(task['worker_name'], -0.6)
                                            
                                            # Заказчик наказывается, если создано > 2 задач и процент отмен выше 35%
                                            if profile_data['created'] > 2:
                                                current_rate = ((profile_data['canceled'] + 1) / profile_data['created']) * 100
                                                if current_rate > 35:
                                                    change_rating_flat(profile_data['name'], -0.4)
                                                    st.warning("Личный рейтинг заказчика снижен на -0.4 за частые отмены!")
                                                    
                                            st.success("Задание отменено, рейтинг исполнителя снижен на 0.6.")
                                            st.session_state[show_form_key] = False
                                            st.rerun()
                        st.write("---")

    with tab_profile:
        st.header("👤 Мой профиль Заказчика")
        with st.form("c_prof"):
            n = st.text_input("Имя:", value=profile_data['name'])
            p = st.text_input("Телефон:", value=profile_data['phone'])
            a = st.text_area("О себе:", value=profile_data['about'])
            if st.form_submit_button("Сохранить"):
                update_profile("client", n, p, a)
                st.rerun()
                
        st.subheader("💬 Отзывы обо мне от Исполнителей")
        df_revs = get_reviews_for(profile_data['name'])
        if df_revs.empty:
            st.caption("Отзывов пока нет.")
        else:
            for r in df_revs.to_dict(orient="records"):
                st.info(f"⭐ {r['score']} | **{r['author_name']}**: {r['comment']}")

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
                            st.write(f"**{task['title']}** — 💰 {task['reward']} MDL")
                            st.caption(f"📍 {task['city']} ({task['village']}) | 📁 {task['category']}")
                            
                            if task['status'] == "На проверке":
                                client_info = get_profile_by_name(task['client_name'])
                                st.warning("Ожидает проверки заказчиком")
                                st.info(f"📞 Связаться с Заказчиком ({task['client_name']}): **{client_info['phone']}** (Рейтинг: ⭐ {client_info['rating']})")
