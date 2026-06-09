import streamlit as st
import pandas as pd
import sqlite3

# --- РАБОТА С БАЗОЙ ДАННЫХ (SQL) ---
def init_db():
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
            cancel_reason TEXT DEFAULT '',
            worker_evidence TEXT DEFAULT '',
            appeal_text TEXT DEFAULT ''
        )
    """)
    
    # Миграции
    cursor.execute("PRAGMA table_info(tasks)")
    columns = [col[1] for col in cursor.fetchall()]
    if "worker_evidence" not in columns:
        cursor.execute("ALTER TABLE tasks ADD COLUMN worker_evidence TEXT DEFAULT ''")
    if "appeal_text" not in columns:
        cursor.execute("ALTER TABLE tasks ADD COLUMN appeal_text TEXT DEFAULT ''")
    
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
    cursor.execute("INSERT OR IGNORE INTO profiles (role, name, phone, about, rating, rating_count, tasks_created, tasks_canceled) VALUES ('worker', 'Михаил Лупу', '+373 79 987 654', 'Исполнитель из Комрата.', 5.0, 1, 0, 0)")
    
    # Таблица для отзывов
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

def worker_accept_task(task_id, worker_name):
    conn = sqlite3.connect("taskearn_v14.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='В работе', worker_name=? WHERE id=?", (worker_name, task_id))
    conn.commit()
    conn.close()

def worker_abandon_task(task_id):
    conn = sqlite3.connect("taskearn_v14.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='Доступно', worker_name='', worker_evidence='' WHERE id=?", (task_id,))
    conn.commit()
    conn.close()

def send_to_review(task_id, worker_name, evidence):
    conn = sqlite3.connect("taskearn_v14.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='На проверке', worker_name=?, worker_evidence=? WHERE id=?", (worker_name, evidence, task_id))
    conn.commit()
    conn.close()

def approve_task(task_id, reward):
    conn = sqlite3.connect("taskearn_v14.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='Выполнено' WHERE id=?", (task_id,))
    cursor.execute("UPDATE balances SET balance = balance + ? WHERE role='worker'", (reward,))
    conn.commit()
    conn.close()

def client_dispute_task(task_id, reason):
    conn = sqlite3.connect("taskearn_v14.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='Оспорено', cancel_reason=? WHERE id=?", (reason, task_id))
    conn.commit()
    conn.close()

def worker_confirm_cancel(task_id, reward, client_name, worker_name):
    conn = sqlite3.connect("taskearn_v14.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='Отменено' WHERE id=?", (task_id,))
    cursor.execute("UPDATE balances SET balance = balance + ? WHERE role='client'", (reward,))
    cursor.execute("UPDATE profiles SET tasks_canceled = tasks_canceled + 1 WHERE name=?", (client_name,))
    conn.commit()
    conn.close()
    change_rating_flat(worker_name, -0.6)

def worker_send_to_arbitration(task_id, appeal_text):
    conn = sqlite3.connect("taskearn_v14.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='Арбитраж', appeal_text=? WHERE id=?", (appeal_text, task_id))
    conn.commit()
    conn.close()

# Запуск БД
init_db()

CITIES = ["Все регионы", "Кишинёв", "Бельцы", "Комрат", "Кагул", "Оргеев", "Унгены", "Сороки", "Тирасполь"]
CATEGORIES = ["Все категории", "📦 Доставка", "🛠️ Ремонт и дом", "💻 IT и Тексты", "🚗 Автоуслуги", "Другое"]

# --- ИНТЕРФЕЙС ---
st.set_page_config(page_title="TaskEarn MDL", page_icon="🇲🇩", layout="centered")

st.title("🇲🇩 TaskEarn — Микрозадачи и Безопасный Арбитраж")
st.write("---")

role = st.sidebar.radio("Выберите вашу роль:", ["💼 Заказчик", "🧑‍💻 Исполнитель", "⚖️ Арбитраж (Демо)"])

balance_client = get_balance("client")
balance_worker = get_balance("worker")
profile_data = get_profile("client" if role == "💼 Заказчик" else "worker")

# Сайдбар профиля
if role != "⚖️ Арбитраж (Демо)":
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
    tab_tasks, tab_review, tab_profile = st.tabs(["📋 Создать и Управлять", "🔍 Проверка работ", "👤 Мой профиль"])
    
    with tab_tasks:
        st.header("Новое задание")
        with st.form("new_task_form", clear_on_submit=True):
            task_title = st.text_input("Что необходимо сделать?")
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
        st.subheader("⚡ Управление и уведомления (В процессе)")
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
                            
                            # ЛОГИКА УВЕДОМЛЕНИЙ И СВЯЗИ ДЛЯ ЗАКАЗЧИКА
                            if task['status'] == 'Доступно':
                                st.caption(f"🟢 Статус: `В ленте (Свободно)` | 📍 {task['city']}")
                            elif task['status'] == 'В работе':
                                worker_p = get_profile_by_name(task['worker_name'])
                                st.info(f"🔵 **Задание принято в работу!**\n\n🧑‍💻 Исполнитель: **{task['worker_name']}** (⭐ {worker_p['rating']})\n\n📞 Связаться: **{worker_p['phone']}**")
                            elif task['status'] == 'На проверке':
                                st.warning(f"🟡 **На проверке!** Зайдите во вкладку 'Проверка работ'. Исполнитель: {task['worker_name']}")
                            elif task['status'] == 'Оспорено':
                                st.caption(f"🟠 Статус: `Оспорено вами (Ожидает ответа исполнителя)`")
                            elif task['status'] == 'Арбитраж':
                                st.caption(f"⚖️ Статус: `В Арбитраже (На рассмотрении системы)`")
                            else:
                                st.caption(f"⚫ Статус: `{task['status']}`")
                        
                        with col_t2:
                            if task['status'] == 'Доступно':
                                if st.button("❌ Отозвать", key=f"rev_{task['id']}", use_container_width=True):
                                    revoke_free_task(task['id'])
                                    update_balance("client", task['reward'])
                                    st.success("Задание отозвано, деньги вернулись на баланс!")
                                    st.rerun()
                        st.write("-" * 10)

    with tab_review:
        st.header("🔍 Задания, ожидающие вашей проверки")
        df_tasks = get_tasks()
        
        if df_tasks.empty:
            st.info("Нет задач для проверки.")
        else:
            review_tasks = df_tasks[(df_tasks["status"] == "На проверке") & (df_tasks["client_name"] == profile_data['name'])].to_dict(orient="records")
            if not review_tasks:
                st.info("Пока никто не прислал новых работ на проверку.")
            else:
                for task in review_tasks:
                    with st.container():
                        st.write(f"### Задание: {task['title']} ({task['reward']} MDL)")
                        worker_info = get_profile_by_name(task['worker_name'])
                        st.success(f"🧑‍💻 Выполнил: **{task['worker_name']}** (⭐ {worker_info['rating']})")
                        st.warning(f"📌 **Отчёт исполнителя:** {task['worker_evidence']}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.subheader("Успешное выполнение")
                            rating_score = st.slider("Оцените работу:", 1, 5, 5, key=f"score_{task['id']}")
                            review_text = st.text_input("Отзыв:", key=f"rev_txt_{task['id']}", placeholder="Всё отлично...")
                            if st.button("✅ Принять и оплатить", key=f"app_{task['id']}", use_container_width=True):
                                approve_task(task["id"], task["reward"])
                                update_rating_stars("worker", rating_score)
                                if review_text.strip():
                                    add_review(task['worker_name'], profile_data['name'], rating_score, review_text.strip())
                                st.success("Работа принята, деньги переведены!")
                                st.rerun()
                                
                        with col2:
                            st.subheader("Отказ / Претензия")
                            show_form_key = f"show_form_{task['id']}"
                            if show_form_key not in st.session_state:
                                st.session_state[show_form_key] = False
                                
                            if st.button("❌ Работа не выполнена", key=f"btn_fail_{task['id']}", use_container_width=True):
                                st.session_state[show_form_key] = True
                                
                            if st.session_state[show_form_key]:
                                with st.form(key=f"cancel_form_{task['id']}"):
                                    evidence = st.text_area("Опишите претензию (почему не принимаете?):", placeholder="Работа сделана не по инструкции...")
                                    submit_cancel = st.form_submit_button("🚨 Отправить на оспаривание")
                                    
                                    if submit_cancel:
                                        if len(evidence.strip()) < 5:
                                            st.error("Укажите вескую причину!")
                                        else:
                                            client_dispute_task(task["id"], evidence.strip())
                                            st.warning("Заказ оспорен! Деньги удержаны системой до ответа исполнителя.")
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

# --- ЛОГИКА ИСПОЛНИТЕЛЯ ---
elif role == "🧑‍💻 Исполнитель":
    tab_tasks, tab_withdraw, tab_profile = st.tabs(["📋 Лента заданий", "💸 Вывод средств", "👤 Мой профиль"])
    
    with tab_tasks:
        st.header("Ваша лента задач")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            filter_city = st.selectbox("📍 Регион:", CITIES)
        with col_f2:
            filter_cat = st.selectbox("📁 Категория:", CATEGORIES)

        df_tasks = get_tasks()
        if df_tasks.empty:
            st.info("Заданий пока нет.")
        else:
            my_current_tasks = df_tasks[
                (df_tasks["status"] == "Доступно") | 
                ((df_tasks["worker_name"] == profile_data['name']) & (df_tasks["status"].isin(["В работе", "На проверке", "Оспорено", "Арбитраж"])))
            ]
            
            if filter_city != "Все регионы":
                my_current_tasks = my_current_tasks[my_current_tasks["city"] == filter_city]
            if filter_cat != "Все категории":
                my_current_tasks = my_current_tasks[my_current_tasks["category"] == filter_cat]
            
            for task in my_current_tasks.to_dict(orient="records"):
                with st.container():
                    col1, col2 = st.columns([3, 2])
                    with col1:
                        st.write(f"**{task['title']}** — 💰 **{task['reward']} MDL**")
                        st.caption(f"📍 {task['city']} ({task['village']}) | Категория: {task['category']}")
                        
                        client_info = get_profile_by_name(task['client_name'])
                        st.caption(f"👤 Заказчик: {task['client_name']} (⭐ {client_info['rating']})")
                        
                        if task['status'] == "В работе":
                            st.info(f"📞 Связь с Заказчиком: **{client_info['phone']}**")
                        elif task['status'] == "На проверке":
                            st.warning("⏳ Ожидает проверки заказчиком.")
                        elif task['status'] == "Арбитраж":
                            st.info("⚖️ Дело передано в Арбитраж. Ожидайте решения.")
                        elif task['status'] == "Оспорено":
                            st.error(f"⚠️ Заказчик отклонил работу! Причина: «{task['cancel_reason']}»")
                    
                    with col2:
                        if task['status'] == "Доступно":
                            if st.button("🤝 Взять в работу", key=f"take_{task['id']}", use_container_width=True):
                                worker_accept_task(task['id'], profile_data['name'])
                                st.rerun()
                        
                        elif task['status'] == "В работе":
                            with st.popover("📤 Отправить отчет", use_container_width=True):
                                with st.form(key=f"ev_form_{task['id']}"):
                                    ev_text = st.text_area("Доказательства выполнения:")
                                    if st.form_submit_button("Отправить"):
                                        if len(ev_text.strip()) > 5:
                                            send_to_review(task['id'], profile_data['name'], ev_text.strip())
                                            st.rerun()
                                        else:
                                            st.error("Напишите отчет!")
                            
                            # ВЕРНУЛИ КНОПКУ ОТМЕНЫ (ОТКАЗА) ДЛЯ ИСПОЛНИТЕЛЯ
                            if st.button("🚫 Отказаться от задачи", key=f"abandon_{task['id']}", use_container_width=True):
                                worker_abandon_task(task['id'])
                                st.warning("Вы отказались от задания.")
                                st.rerun()
                        
                        elif task['status'] == "Оспорено":
                            if st.button("👍 Согласиться с отменой", key=f"agree_{task['id']}", use_container_width=True):
                                worker_confirm_cancel(task['id'], task['reward'], task['client_name'], profile_data['name'])
                                st.success("Вы согласились с отменой.")
                                st.rerun()
                                
                            with st.popover("⚖️ Оспорить (В арбитраж)", use_container_width=True):
                                with st.form(key=f"appeal_form_{task['id']}"):
                                    appeal_text = st.text_area("Ваша апелляция:", placeholder="Я всё сделал верно...")
                                    if st.form_submit_button("🚨 Направить в Арбитраж"):
                                        if len(appeal_text.strip()) < 10:
                                            st.error("Опишите подробнее!")
                                        else:
                                            worker_send_to_arbitration(task['id'], appeal_text.strip())
                                            st.rerun()
                    st.write("---")

    with tab_withdraw:
        st.header("💸 Вывод средств")
        st.write(f"Доступно для вывода: **{balance_worker} MDL**")
        with st.form("withdraw_form"):
            withdraw_amount = st.number_input("Сумма вывода (MDL):", min_value=50, max_value=int(balance_worker) if balance_worker >= 50 else 50, step=10)
            card_number = st.text_input("Номер карты (MDL / Visa / Mastercard):", placeholder="4111 1111 1111 1111")
            submit_w = st.form_submit_button("Запросить выплату")
            
            if submit_w:
                if balance_worker >= withdraw_amount:
                    if len(card_number.strip()) >= 16:
                        update_balance("worker", -withdraw_amount)
                        st.success(f"Заявка на вывод {withdraw_amount} MDL принята!")
                        st.rerun()
                    else:
                        st.error("Введите корректный номер карты!")
                else:
                    st.error("Недостаточно средств!")

    with tab_profile:
        st.header("👤 Мой профиль Исполнителя")
        with st.form("w_prof"):
            n = st.text_input("Имя:", value=profile_data['name'])
            p = st.text_input("Телефон:", value=profile_data['phone'])
            a = st.text_area("О себе:", value=profile_data['about'])
            if st.form_submit_button("Сохранить изменения"):
                update_profile("worker", n, p, a)
                st.rerun()
                
        st.subheader("💬 Отзывы о моей работе")
        df_revs = get_reviews_for(profile_data['name'])
        if df_revs.empty:
            st.caption("Отзывов от заказчиков пока нет.")
        else:
            for r in df_revs.to_dict(orient="records"):
                st.info(f"⭐ {r['score']} | **{r['author_name']}**: {r['comment']}")

# --- ДЕМО ПАНЕЛЬ АРБИТРАЖА ---
elif role == "⚖️ Арбитраж (Демо)":
    st.header("⚖️ Панель независимого Арбитража")
    df_tasks = get_tasks()
    if df_tasks.empty:
        st.info("Нет активных споров.")
    else:
        arbitration_tasks = df_tasks[df_tasks["status"] == "Арбитраж"].to_dict(orient="records")
        if not arbitration_tasks:
            st.info("Нет задач, требующих вмешательства арбитра.")
        else:
            for task in arbitration_tasks:
                with st.expander(f"Спор по задаче: {task['title']} ({task['reward']} MDL)"):
                    st.write(f"**Заказчик:** {task['client_name']} | **Исполнитель:** {task['worker_name']}")
                    st.info(f"📋 **Задача:** {task['title']}")
                    st.success(f"🧑‍💻 **Отчёт исполнителя:** {task['worker_evidence']}")
                    st.error(f"💼 **Претензия заказчика:** {task['cancel_reason']}")
                    st.warning(f"🚨 **Апелляция исполнителя:** {task['appeal_text']}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Победа Исполнителя ✅", key=f"win_w_{task['id']}", use_container_width=True):
                            approve_task(task['id'], task['reward'])
                            update_rating_stars("worker", 5)
                            st.success("Выплачено исполнителю!")
                            st.rerun()
                    with col2:
                        if st.button("Победа Заказчика ❌", key=f"win_c_{task['id']}", use_container_width=True):
                            conn = sqlite3.connect("taskearn_v14.db")
                            cursor = conn.cursor()
                            cursor.execute("UPDATE tasks SET status='Отменено' WHERE id=?", (task['id'],))
                            cursor.execute("UPDATE balances SET balance = balance + ? WHERE role='client'", (task['reward'],))
                            conn.commit()
                            conn.close()
                            change_rating_flat(task['worker_name'], -0.8)
                            st.error("Возвращено заказчику!")
                            st.rerun()
