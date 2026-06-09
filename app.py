import streamlit as st
import pandas as pd
import sqlite3

# --- НАСТРОЙКА ПЛАТФОРМЫ ---
COMMISSION_RATE = 0.10  # 10% комиссия сервиса

# --- РАБОТА С БАЗОЙ ДАННЫХ (SQL) ---
def init_db():
    conn = sqlite3.connect("taskearn_v16.db")
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
    
    # Таблица для балансов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS balances (
            role TEXT PRIMARY KEY,
            balance REAL
        )
    """)
    cursor.execute("INSERT OR IGNORE INTO balances (role, balance) VALUES ('client', 500.0)")
    cursor.execute("INSERT OR IGNORE INTO balances (role, balance) VALUES ('worker', 0.0)")
    cursor.execute("INSERT OR IGNORE INTO balances (role, balance) VALUES ('admin', 0.0)")
    
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
    conn = sqlite3.connect("taskearn_v16.db")
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
    conn = sqlite3.connect("taskearn_v16.db")
    cursor = conn.cursor()
    cursor.execute("SELECT phone, rating, role FROM profiles WHERE name=?", (name,))
    res = cursor.fetchone()
    conn.close()
    if res:
        return {"phone": res[0], "rating": round(res[1], 1), "role": res[2]}
    return {"phone": "Не указан", "rating": 5.0, "role": "worker"}

def update_profile(role_type, name, phone, about):
    conn = sqlite3.connect("taskearn_v16.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE profiles SET name=?, phone=?, about=? WHERE role=?", (name, phone, about, role_type))
    conn.commit()
    conn.close()

def change_rating_flat(profile_name, penalty):
    conn = sqlite3.connect("taskearn_v16.db")
    cursor = conn.cursor()
    cursor.execute("SELECT rating FROM profiles WHERE name=?", (profile_name,))
    res = cursor.fetchone()
    if res:
        new_rating = max(1.0, min(5.0, res[0] + penalty))
        cursor.execute("UPDATE profiles SET rating=? WHERE name=?", (new_rating, profile_name))
    conn.commit()
    conn.close()

def update_rating_stars(role_type, new_score):
    conn = sqlite3.connect("taskearn_v16.db")
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
    conn = sqlite3.connect("taskearn_v16.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO reviews (target_name, author_name, score, comment) VALUES (?, ?, ?, ?)", 
                   (target_name, author_name, score, comment))
    conn.commit()
    conn.close()

def get_reviews_for(name):
    conn = sqlite3.connect("taskearn_v16.db")
    df = pd.read_sql_query("SELECT author_name, score, comment FROM reviews WHERE target_name=?", conn, params=(name,))
    conn.close()
    return df

def get_balance(role_type):
    conn = sqlite3.connect("taskearn_v16.db")
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM balances WHERE role=?", (role_type,))
    res = cursor.fetchone()
    balance = res[0] if res else 0.0
    conn.close()
    return balance

def update_balance(role_type, amount):
    conn = sqlite3.connect("taskearn_v16.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE balances SET balance = balance + ? WHERE role=?", (amount, role_type))
    conn.commit()
    conn.close()

def add_task(title, reward, city, village, category, client_name):
    conn = sqlite3.connect("taskearn_v16.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tasks (title, reward, status, city, village, category, client_name) 
        VALUES (?, ?, 'Доступно', ?, ?, ?, ?)
    """, (title, reward, city, village, category, client_name))
    cursor.execute("UPDATE profiles SET tasks_created = tasks_created + 1 WHERE name=?", (client_name,))
    conn.commit()
    conn.close()

def get_tasks():
    conn = sqlite3.connect("taskearn_v16.db")
    df = pd.read_sql_query("SELECT * FROM tasks", conn)
    conn.close()
    return df

def revoke_free_task(task_id):
    conn = sqlite3.connect("taskearn_v16.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()
    conn.close()

def worker_accept_task(task_id, worker_name):
    conn = sqlite3.connect("taskearn_v16.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='В работе', worker_name=? WHERE id=?", (worker_name, task_id))
    conn.commit()
    conn.close()

def worker_abandon_task(task_id):
    conn = sqlite3.connect("taskearn_v16.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='Доступно', worker_name='', worker_evidence='' WHERE id=?", (task_id,))
    conn.commit()
    conn.close()

def send_to_review(task_id, worker_name, evidence):
    conn = sqlite3.connect("taskearn_v16.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='На проверке', worker_name=?, worker_evidence=? WHERE id=?", (worker_name, evidence, task_id))
    conn.commit()
    conn.close()

def approve_task(task_id, total_reward):
    admin_cut = total_reward * COMMISSION_RATE
    worker_cut = total_reward - admin_cut
    
    conn = sqlite3.connect("taskearn_v16.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='Выполнено' WHERE id=?", (task_id,))
    cursor.execute("UPDATE balances SET balance = balance + ? WHERE role='worker'", (worker_cut,))
    cursor.execute("UPDATE balances SET balance = balance + ? WHERE role='admin'", (admin_cut,))
    conn.commit()
    conn.close()

def client_dispute_task(task_id, reason):
    conn = sqlite3.connect("taskearn_v16.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='Оспорено', cancel_reason=? WHERE id=?", (reason, task_id))
    conn.commit()
    conn.close()

def worker_confirm_cancel(task_id, reward, client_name, worker_name):
    conn = sqlite3.connect("taskearn_v16.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='Отменено' WHERE id=?", (task_id,))
    cursor.execute("UPDATE balances SET balance = balance + ? WHERE role='client'", (reward,))
    cursor.execute("UPDATE profiles SET tasks_canceled = tasks_canceled + 1 WHERE name=?", (client_name,))
    conn.commit()
    conn.close()
    change_rating_flat(worker_name, -0.6)

def worker_send_to_arbitration(task_id, appeal_text):
    conn = sqlite3.connect("taskearn_v16.db")
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

st.title("🇲🇩 TaskEarn — Микрозадачи и Монетизация")
st.write("---")

role = st.sidebar.radio("Выберите вашу роль:", ["💼 Заказчик", "🧑‍💻 Исполнитель", "⚖️ Арбитраж и Доход (Вы)"])

balance_client = get_balance("client")
balance_worker = get_balance("worker")
balance_admin = get_balance("admin")
profile_data = get_profile("client" if role == "💼 Заказчик" else "worker")

# Сайдбар профиля
if role != "⚖️ Арбитраж и Доход (Вы)":
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
    tab_tasks, tab_review, tab_profile = st.tabs(["📋 Создать и Управлять", "🔍 Проверка работ", "👤 Мой профиль"])
    
    with tab_tasks:
        st.header("Новое задание")
        with st.form("new_task_form", clear_on_submit=True):
            task_title = st.text_input("Что необходимо сделать?")
            task_city = st.selectbox("Ближайший город/райцентр:", CITIES[1:])
            task_village = st.text_input("Уточните населённый пункт (село, коммуна, улица):")
            task_category = st.selectbox("Категория:", CATEGORIES[1:])
            task_reward = st.number_input("Стоимость задачи для вас (MDL)", min_value=20, value=100, step=10)
            submit = st.form_submit_button("Опубликовать и заблокировать оплату")
            
            if submit and task_title:
                if balance_client >= task_reward:
                    loc_village = task_village.strip() if task_village.strip() else "город"
                    update_balance("client", -task_reward)
                    add_task(task_title, task_reward, task_city, loc_village, task_category, profile_data['name'])
                    st.success("Опубликовано! Средства заморожены системой.")
                    st.rerun()
                else:
                    st.error("Недостаточно средств!")

        st.write("---")
        st.subheader("⚡ Управление и уведомления")
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
                                st.caption(f"🟢 Статус: `В ленте` | Исполнитель получит: {task['reward'] * (1 - COMMISSION_RATE)} MDL")
                            elif task['status'] == 'В работе':
                                worker_p = get_profile_by_name(task['worker_name'])
                                st.info(f"🔵 **Задание принято!**\n\n🧑‍💻 Исполнитель: **{task['worker_name']}** (⭐ {worker_p['rating']})\n\n📞 Связь: **{worker_p['phone']}**")
                            elif task['status'] == 'На проверке':
                                st.warning(f"🟡 **На проверке!** Зайдите во вкладку 'Проверка работ'.")
                            elif task['status'] == 'Оспорено':
                                st.error(f"🟠 **Вы оспорили эту задачу.** Ожидаем решения исполнителя.")
                            elif task['status'] == 'Арбитраж':
                                st.info(f"⚖️ **В Арбитраже.** Ожидайте решения Администрации.")
                            else:
                                st.caption(f"⚫ Статус: `{task['status']}`")
                        
                        with col_t2:
                            if task['status'] == 'Доступно':
                                if st.button("❌ Отозвать", key=f"rev_{task['id']}", use_container_width=True):
                                    revoke_free_task(task['id'])
                                    update_balance("client", task['reward'])
                                    st.rerun()
                        st.write("-" * 10)

    with tab_review:
        st.header("🔍 Задания на проверке")
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
                        st.warning(f"📌 **Отчёт исполнителя:** {task['worker_evidence']}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("✅ Принять и оплатить", key=f"app_{task['id']}", use_container_width=True):
                                approve_task(task["id"], task["reward"])
                                st.success("Принято! Деньги распределены.")
                                st.rerun()
                        with col2:
                            # ВСПЛЫВАЮЩЕЕ ОКНО С ФОРМОЙ АРГУМЕНТАЦИИ ПРИ ОТКЛОНЕНИИ
                            with st.popover("❌ Отклонить и оспорить", use_container_width=True):
                                with st.form(key=f"dispute_form_{task['id']}"):
                                    reason_text = st.text_area("Укажите причину отказа (аргумент):", placeholder="Работа выполнена не до конца / не по инструкции...")
                                    submit_dispute = st.form_submit_button("🚨 Подтвердить отказ")
                                    if submit_dispute:
                                        if len(reason_text.strip()) >= 5:
                                            client_dispute_task(task["id"], reason_text.strip())
                                            st.warning("Заказ оспорен! Деньги удержаны.")
                                            st.rerun()
                                        else:
                                            st.error("Пожалуйста, напишите развернутую причину!")
                        st.write("---")

    with tab_profile:
        st.header("👤 Мой профиль Заказчика")
        with st.form("c_prof"):
            n = st.text_input("Имя:", value=profile_data['name'])
            p = st.text_input("Телефон:", value=profile_data['phone'])
            a = st.text_area("О себе:", value=profile_data['about'])
            if st.form_submit_button("Сохранить"):
                update_profile("client", n, p, a)
                st.success("Профиль успешно сохранен!")
                st.rerun()

# --- ЛОГИКА ИСПОЛНИТЕЛЯ ---
elif role == "🧑‍💻 Исполнитель":
    tab_tasks, tab_withdraw, tab_profile = st.tabs(["📋 Лента заданий", "💸 Вывод средств", "👤 Мой профиль"])
    
    with tab_tasks:
        st.header("Ваша лента задач")
        df_tasks = get_tasks()
        
        if df_tasks.empty:
            st.info("Лента пуста.")
        else:
            my_current_tasks = df_tasks[
                (df_tasks["status"] == "Доступно") | 
                ((df_tasks["worker_name"] == profile_data['name']) & (df_tasks["status"].isin(["В работе", "На проверке", "Оспорено", "Арбитраж"])))
            ]
            
            if my_current_tasks.empty:
                st.info("Нет доступных или активных задач.")
            else:
                for task in my_current_tasks.to_dict(orient="records"):
                    clean_reward = task['reward'] * (1 - COMMISSION_RATE)
                    
                    with st.container():
                        col1, col2 = st.columns([3, 2])
                        with col1:
                            st.write(f"**{task['title']}**")
                            st.write(f"💰 Оплата вам на руки: **{clean_reward} MDL**")
                            st.caption(f"📍 Локация: {task['city']}, {task['village']}")
                            
                            if task['status'] == "Оспорено":
                                st.error(f"⚠️ **Заказчик отклонил работу!**\n\nПричина заказчика: «{task['cancel_reason']}»")
                            elif task['status'] == "На проверке":
                                st.warning("⏳ Ожидает проверки заказчиком.")
                            elif task['status'] == "Арбитраж":
                                st.info("⚖️ Спор передан Администратору.")
                        
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
                                            if ev_text.strip():
                                                send_to_review(task['id'], profile_data['name'], ev_text.strip())
                                                st.rerun()
                                            else:
                                                st.error("Поле отчета не может быть пустым.")
                                
                                if st.button("🚫 Отказаться от задачи", key=f"abandon_{task['id']}", use_container_width=True):
                                    worker_abandon_task(task['id'])
                                    st.rerun()
                            
                            elif task['status'] == "Оспорено":
                                if st.button("👍 Согласиться с отменой", key=f"agree_{task['id']}", use_container_width=True):
                                    worker_confirm_cancel(task['id'], task['reward'], task['client_name'], profile_data['name'])
                                    st.rerun()
                                
                                with st.popover("⚖️ Оспорить в Арбитраж", use_container_width=True):
                                    with st.form(key=f"appeal_form_{task['id']}"):
                                        appeal_text = st.text_area("Ваша апелляция (контр-аргумент):", placeholder="Я сделал всё по ТЗ...")
                                        if st.form_submit_button("🚨 Передать дело админу"):
                                            if len(appeal_text.strip()) >= 5:
                                                worker_send_to_arbitration(task['id'], appeal_text.strip())
                                                st.rerun()
                                            else:
                                                st.error("Опишите свою позицию!")
                        st.write("---")

    with tab_withdraw:
        st.header("💸 Вывод средств")
        st.write(f"Доступно для вывода: **{balance_worker} MDL**")
        with st.form("withdraw_form"):
            withdraw_amount = st.number_input("Сумма вывода (MDL):", min_value=50, value=50, step=10)
            card_number = st.text_input("Номер карты:", placeholder="4111 1111 1111 1111")
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
                st.success("Профиль успешно обновлен!")
                st.rerun()

# --- ПАНЕЛЬ АДМИНИСТРАТОРА (ВЫ) ---
elif role == "⚖️ Арбитраж и Доход (Вы)":
    st.header("👑 Панель Управления и Дохода Владельца")
    
    st.metric(label="💰 Чистый доход вашей платформы", value=f"{balance_admin} MDL")
    st.write("---")
    st.subheader("⚖️ Заявки в Арбитраже")
    
    df_tasks = get_tasks()
    if df_tasks.empty:
        st.info("Нет активных споров.")
    else:
        arbitration_tasks = df_tasks[df_tasks["status"] == "Арбитраж"].to_dict(orient="records")
        if not arbitration_tasks:
            st.info("Все споры урегулированы.")
        else:
            for task in arbitration_tasks:
                with st.expander(f"Спор по задаче: {task['title']}"):
                    st.write(f"**Заказчик:** {task['client_name']} | **Исполнитель:** {task['worker_name']}")
                    st.write(f"📋 **Задача:** {task['title']} ({task['reward']} MDL)")
                    st.success(f"🧑‍💻 **Отчёт исполнителя:** {task['worker_evidence']}")
                    st.error(f"💼 **Претензия заказчика:** {task['cancel_reason']}")
                    st.warning(f"🚨 **Апелляция исполнителя:** {task['appeal_text']}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Победа Исполнителя ✅", key=f"win_w_{task['id']}", use_container_width=True):
                            approve_task(task['id'], task['reward'])
                            st.success("Выплачено воркеру!")
                            st.rerun()
                    with col2:
                        if st.button("Победа Заказчика ❌", key=f"win_c_{task['id']}", use_container_width=True):
                            conn = sqlite3.connect("taskearn_v16.db")
                            cursor = conn.cursor()
                            cursor.execute("UPDATE tasks SET status='Отменено' WHERE id=?", (task['id'],))
                            cursor.execute("UPDATE balances SET balance = balance + ? WHERE role='client'", (task['reward'],))
                            conn.commit()
                            conn.close()
                            st.error("Возвращено заказчику!")
                            st.rerun()
