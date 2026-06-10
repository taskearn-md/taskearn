import streamlit as st
import pandas as pd
import sqlite3

# --- НАСТРОЙКА ПЛАТФОРМЫ ---
COMMISSION_RATE = 0.10  # 10% комиссия сервиса

# --- РАБОТА С БАЗОЙ ДАННЫХ (SQL) ---
def init_db():
    conn = sqlite3.connect("taskearn_v17.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            username TEXT UNIQUE,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            about TEXT,
            balance REAL DEFAULT 0.0,
            rating REAL DEFAULT 5.0,
            rating_count INTEGER DEFAULT 1,
            tasks_created INTEGER DEFAULT 0,
            tasks_canceled INTEGER DEFAULT 0
        )
    """)
    cursor.execute("INSERT OR IGNORE INTO users (id, role, username, name, phone, about, balance) VALUES (1, 'client', 'ion_cheban', 'Ион Чебан', '+373 68 123 456', 'Заказчик из Кишинева.', 1000.0)")
    cursor.execute("INSERT OR IGNORE INTO users (id, role, username, name, phone, about, balance) VALUES (2, 'worker', 'mihail_lupu', 'Михаил Лупу', '+373 79 987 654', 'Исполнитель из Комрата.', 0.0)")
    cursor.execute("INSERT OR IGNORE INTO users (id, role, username, name, phone, about, balance) VALUES (3, 'admin', 'platform_owner', 'Администратор', '000', 'Владелец платформы', 0.0)")
    
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

def get_user_by_id(user_id):
    conn = sqlite3.connect("taskearn_v17.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, role, username, name, phone, about, balance, rating, tasks_created, tasks_canceled FROM users WHERE id=?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    if res:
        return {
            "id": res[0], "role": res[1], "username": res[2], "name": res[3], 
            "phone": res[4], "about": res[5], "balance": res[6], "rating": round(res[7], 1),
            "created": res[8], "canceled": res[9]
        }
    return None

def update_profile(user_id, name, phone, about):
    conn = sqlite3.connect("taskearn_v17.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET name=?, phone=?, about=? WHERE id=?", (name, phone, about, user_id))
    conn.commit()
    conn.close()

def update_balance(user_id, amount):
    conn = sqlite3.connect("taskearn_v17.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ? WHERE id=?", (amount, user_id))
    conn.commit()
    conn.close()

def change_rating_flat(user_id, penalty):
    conn = sqlite3.connect("taskearn_v17.db")
    cursor = conn.cursor()
    cursor.execute("SELECT rating FROM users WHERE id=?", (user_id,))
    res = cursor.fetchone()
    if res:
        new_rating = max(1.0, min(5.0, res[0] + penalty))
        cursor.execute("UPDATE users SET rating=? WHERE id=?", (new_rating, user_id))
    conn.commit()
    conn.close()

def add_task(title, reward, city, village, category, client_id):
    conn = sqlite3.connect("taskearn_v17.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (title, reward, status, city, village, category, client_id) VALUES (?, ?, 'Доступно', ?, ?, ?, ?)", 
                   (title, reward, city, village, category, client_id))
    cursor.execute("UPDATE users SET tasks_created = tasks_created + 1 WHERE id=?", (client_id,))
    conn.commit()
    conn.close()

def get_tasks_with_names():
    query = """
        SELECT t.*, c.name AS client_name, w.name AS worker_name, w.phone AS worker_phone, w.rating AS worker_rating
        FROM tasks t
        JOIN users c ON t.client_id = c.id
        LEFT JOIN users w ON t.worker_id = w.id
    """
    conn = sqlite3.connect("taskearn_v17.db")
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def revoke_free_task(task_id):
    conn = sqlite3.connect("taskearn_v17.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()
    conn.close()

def worker_accept_task(task_id, worker_id):
    conn = sqlite3.connect("taskearn_v17.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='В работе', worker_id=? WHERE id=?", (worker_id, task_id))
    conn.commit()
    conn.close()

def worker_abandon_task(task_id):
    conn = sqlite3.connect("taskearn_v17.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='Доступно', worker_id=NULL, worker_evidence='' WHERE id=?", (task_id,))
    conn.commit()
    conn.close()

def send_to_review(task_id, evidence):
    conn = sqlite3.connect("taskearn_v17.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='На проверке', worker_evidence=? WHERE id=?", (evidence, task_id))
    conn.commit()
    conn.close()

def approve_task(task_id, total_reward, worker_id):
    admin_cut = total_reward * COMMISSION_RATE
    worker_cut = total_reward - admin_cut
    conn = sqlite3.connect("taskearn_v17.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='Выполнено' WHERE id=?", (task_id,))
    cursor.execute("UPDATE users SET balance = balance + ? WHERE id=?", (worker_cut, worker_id))
    cursor.execute("UPDATE users SET balance = balance + ? WHERE id=3", (admin_cut,))
    conn.commit()
    conn.close()

def client_dispute_task(task_id, reason):
    conn = sqlite3.connect("taskearn_v17.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='Оспорено', cancel_reason=? WHERE id=?", (reason, task_id))
    conn.commit()
    conn.close()

def worker_confirm_cancel(task_id, reward, client_id, worker_id):
    conn = sqlite3.connect("taskearn_v17.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='Отменено' WHERE id=?", (task_id,))
    cursor.execute("UPDATE users SET balance = balance + ? WHERE id=?", (reward, client_id))
    cursor.execute("UPDATE users SET tasks_canceled = tasks_canceled + 1 WHERE id=?", (client_id,))
    conn.commit()
    conn.close()
    change_rating_flat(worker_id, -0.6)

def worker_send_to_arbitration(task_id, appeal_text):
    conn = sqlite3.connect("taskearn_v17.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='Арбитраж', appeal_text=? WHERE id=?", (appeal_text, task_id))
    conn.commit()
    conn.close()

# --- ИНИЦИАЛИЗАЦИЯ СТАТУСА ПРИЛОЖЕНИЯ ---
init_db()

CITIES = ["Все регионы", "Кишинёв", "Бельцы", "Комрат", "Кагул", "Оргеев", "Унгены", "Сороки", "Тирасполь"]
CATEGORIES = ["Все категории", "📦 Доставка", "🛠️ Ремонт и дом", "💻 IT и Тексты", "🚗 Автоуслуги", "Другое"]

st.set_page_config(page_title="TaskEarn Fixed", page_icon="🇲🇩", layout="centered")
st.title("🇲🇩 TaskEarn — Стабильная версия (ID)")
st.write("---")

role_selection = st.sidebar.radio("Выберите роль экрана:", ["💼 Заказчик", "🧑‍💻 Исполнитель", "⚖️ Арбитраж (Админ)"])

if role_selection == "💼 Заказчик":
    current_user_id = 1
elif role_selection == "🧑‍💻 Исполнитель":
    current_user_id = 2
else:
    current_user_id = 3

user_data = get_user_by_id(current_user_id)

if user_data and user_data['role'] != 'admin':
    st.sidebar.metric(label="Ваш личный баланс", value=f"{user_data['balance']} MDL")
    st.sidebar.markdown(f"🆔 **Ваш ID в системе:** `{user_data['id']}`")
    st.sidebar.write(f"👤 Имя: **{user_data['name']}**")
    st.sidebar.write(f"⭐ Рейтинг: `{user_data['rating']} / 5.0`")
    if user_data['role'] == 'client':
        if st.sidebar.button("Пополнить баланс на +500 MDL"):
            update_balance(user_data['id'], 500.0)
            st.rerun()
elif user_data and user_data['role'] == 'admin':
    st.sidebar.metric(label="Доход платформы", value=f"{user_data['balance']} MDL")
st.sidebar.write("---")

# --- ЛОГИКА ЗАКАЗЧИКА ---
if user_data and user_data['role'] == 'client':
    tab_tasks, tab_review, tab_profile = st.tabs(["📋 Создать и Управлять", "🔍 Проверка работ", "👤 Мой профиль"])
    
    with tab_tasks:
        st.header("Новое задание")
        with st.form("new_task_form", clear_on_submit=True):
            task_title = st.text_input("Что необходимо сделать?")
            task_city = st.selectbox("Ближайший город/райцентр:", CITIES[1:])
            task_village = st.text_input("Уточните населённый пункт:")
            task_category = st.selectbox("Категория:", CATEGORIES[1:])
            task_reward = st.number_input("Стоимость задачи для вас (MDL)", min_value=20, value=100, step=10)
            submit = st.form_submit_button("Опубликовать")
            
            if submit and task_title:
                if user_data['balance'] >= task_reward:
                    loc_village = task_village.strip() if task_village.strip() else "город"
                    update_balance(user_data['id'], -task_reward)
                    add_task(task_title, task_reward, task_city, loc_village, task_category, user_data['id'])
                    st.success("Опубликовано!")
                    st.rerun()
                else:
                    st.error("Недостаточно средств!")

        st.write("---")
        st.subheader("⚡ Ваши задания")
        df_tasks = get_tasks_with_names()
        
        if df_tasks.empty:
            st.info("Вы ещё не создавали заданий.")
        else:
            my_tasks = df_tasks[df_tasks["client_id"] == user_data['id']].to_dict(orient="records")
            if not my_tasks:
                st.info("У вас нет активных заданий.")
            else:
                for task in my_tasks:
                    with st.container():
                        col_t1, col_t2 = st.columns([3, 1])
                        with col_t1:
                            st.write(f"**{task['title']}** — 💰 {task['reward']} MDL")
                            if task['status'] == 'Доступно':
                                st.caption(f"🟢 В ленте")
                            elif task['status'] == 'В работе':
                                st.info(f"🔵 **В работе** у: **{task['worker_name']}** (⭐ {task['worker_rating']}) | 📞 {task['worker_phone']}")
                            elif task['status'] == 'На проверке':
                                st.warning(f"🟡 **На проверке!** Перейдите во вкладку 'Проверка работ'")
                            elif task['status'] == 'Оспорено':
                                st.error(f"🟠 Вы отклонили работу. Ждем ответа.")
                            elif task['status'] == 'Арбитраж':
                                st.info(f"⚖️ Спор у Администрации.")
                        with col_t2:
                            if task['status'] == 'Доступно':
                                if st.button("❌ Отозвать", key=f"rev_{task['id']}", use_container_width=True):
                                    revoke_free_task(task['id'])
                                    update_balance(user_data['id'], task['reward'])
                                    st.rerun()
                        st.write("---")

    with tab_review:
        st.header("🔍 Задания на проверке")
        df_tasks = get_tasks_with_names()
        if not df_tasks.empty:
            review_tasks = df_tasks[(df_tasks["status"] == "На проверке") & (df_tasks["client_id"] == user_data['id'])].to_dict(orient="records")
            if not review_tasks:
                st.info("Нет новых работ на проверку.")
            else:
                for task in review_tasks:
                    st.write(f"### Задание: {task['title']} ({task['reward']} MDL)")
                    st.markdown(f"> **Отчёт {task['worker_name']}:** {task['worker_evidence']}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Принять и оплатить", key=f"app_{task['id']}", use_container_width=True):
                            approve_task(task["id"], task["reward"], task["worker_id"])
                            st.rerun()
                    with col2:
                        with st.popover("❌ Отклонить", use_container_width=True):
                            with st.form(key=f"dis_form_{task['id']}"):
                                reason_text = st.text_area("Причина отказа:")
                                if st.form_submit_button("🚨 Отклонить"):
                                    if len(reason_text.strip()) >= 5:
                                        client_dispute_task(task["id"], reason_text.strip())
                                        st.rerun()

    with tab_profile:
        st.header("👤 Профиль")
        with st.form("c_prof"):
            new_name = st.text_input("Ваше Имя:", value=user_data['name'])
            p = st.text_input("Телефон:", value=user_data['phone'])
            a = st.text_area("О себе:", value=user_data['about'])
            if st.form_submit_button("Сохранить"):
                update_profile(user_data['id'], new_name, p, a)
                st.rerun()

# --- ЛОГИКА ИСПОЛНИТЕЛЯ ---
elif user_data and user_data['role'] == 'worker':
    tab_tasks, tab_withdraw, tab_profile = st.tabs(["📋 Лента заданий", "💸 Вывод средств", "👤 Мой профиль"])
    
    with tab_tasks:
        st.header("Лента микрозадач")
        df_tasks = get_tasks_with_names()
        if not df_tasks.empty:
            my_current_tasks = df_tasks[
                (df_tasks["status"] == "Доступно") | 
                ((df_tasks["worker_id"] == user_data['id']) & (df_tasks["status"].isin(["В работе", "На проверке", "Оспорено", "Арбитраж"])))
            ]
            if my_current_tasks.empty:
                st.info("Нет доступных задач.")
            else:
                for task in my_current_tasks.to_dict(orient="records"):
                    clean_reward = task['reward'] * (1 - COMMISSION_RATE)
                    with st.container():
                        col1, col2 = st.columns([3, 2])
                        with col1:
                            st.write(f"**{task['title']}** (от {task['client_name']})")
                            st.write(f"💰 К выплате: **{clean_reward} MDL**")
                            st.caption(f"📍 {task['city']}, {task['village']}")
                            if task['status'] == "Оспорено":
                                st.error(f"⚠️ Отклонено! Причина: «{task['cancel_reason']}»")
                            elif task['status'] == "На проверке":
                                st.warning("⏳ Ожидает проверки.")
                            elif task['status'] == "Арбитраж":
                                st.info("⚖️ В Арбитраже.")
                        with col2:
                            if task['status'] == "Доступно":
                                if st.button("🤝 Взять", key=f"take_{task['id']}", use_container_width=True):
                                    worker_accept_task(task['id'], user_data['id'])
                                    st.rerun()
                            elif task['status'] == "В работе":
                                with st.popover("📤 Отчет", use_container_width=True):
                                    with st.form(key=f"ev_f_{task['id']}"):
                                        ev_text = st.text_area("Что сделано:")
                                        if st.form_submit_button("Отправить"):
                                            if ev_text.strip():
                                                send_to_review(task['id'], ev_text.strip())
                                                st.rerun()
                                if st.button("🚫 Отказаться", key=f"abd_{task['id']}", use_container_width=True):
                                    worker_abandon_task(task['id'])
                                    st.rerun()
                            elif task['status'] == "Оспорено":
                                if st.button("👍 Согласиться", key=f"agr_{task['id']}", use_container_width=True):
                                    worker_confirm_cancel(task['id'], task['reward'], task['client_id'], user_data['id'])
                                    st.rerun()
                                with st.popover("⚖️ В арбитраж", use_container_width=True):
                                    with st.form(key=f"ap_f_{task['id']}"):
                                        appeal_text = st.text_area("Аргументы:")
                                        if st.form_submit_button("🚨 Оспорить"):
                                            if len(appeal_text.strip()) >= 5:
                                                worker_send_to_arbitration(task['id'], appeal_text.strip())
                                                st.rerun()
                        st.write("---")

    with tab_withdraw:
        st.header("💸 Вывод денег")
        st.write(f"Доступно: **{user_data['balance']} MDL**")
        with st.form("withdraw_form"):
            withdraw_amount = st.number_input("Сумма:", min_value=50, value=50, step=10)
            card_number = st.text_input("Карта:")
            if st.form_submit_button("Вывести"):
                if user_data['balance'] >= withdraw_amount and len(card_number.strip()) >= 16:
                    update_balance(user_data['id'], -withdraw_amount)
                    st.success("Успешно!")
                    st.rerun()

    with tab_profile:
        st.header("👤 Профиль")
        with st.form("w_prof"):
            new_name = st.text_input("Ваше Имя:", value=user_data['name'])
            p = st.text_input("Телефон:", value=user_data['phone'])
            a = st.text_area("О себе:", value=user_data['about'])
            if st.form_submit_button("Сохранить изменения"):
                update_profile(user_data['id'], new_name, p, a)
                st.rerun()

# --- ПАНЕЛЬ АДМИНИСТРАТОРА ---
elif user_data and user_data['role'] == 'admin':
    st.header("👑 Панель Администратора")
    df_tasks = get_tasks_with_names()
    if not df_tasks.empty:
        arbitration_tasks = df_tasks[df_tasks["status"] == "Арбитраж"].to_dict(orient="records")
        if not arbitration_tasks:
            st.info("Нет активных споров.")
        else:
            for task in arbitration_tasks:
                with st.expander(f"⚖️ Спор: {task['title']}"):
                    st.write(f"**Заказчик:** {task['client_name']} | **Исполнитель:** {task['worker_name']}")
                    st.write(f"📋 **Отчет воркера:** {task['worker_evidence']}")
                    st.write(f"❌ **Жалоба клиента:** {task['cancel_reason']}")
                    st.write(f"🚨 **Апелляция воркера:** {task['appeal_text']}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Победа Исполнителя ✅", key=f"win_w_{task['id']}", use_container_width=True):
                            approve_task(task['id'], task['reward'], task['worker_id'])
                            st.rerun()
                    with col2:
                        if st.button("Победа Заказчика ❌", key=f"win_c_{task['id']}", use_container_width=True):
                            conn = sqlite3.connect("taskearn_v17.db")
                            cursor = conn.cursor()
                            cursor.execute("UPDATE tasks SET status='Отменено' WHERE id=?", (task['id'],))
                            cursor.execute("UPDATE users SET balance = balance + ? WHERE id=?", (task['reward'], task['client_id']))
                            conn.commit()
                            conn.close()
                            st.rerun()
