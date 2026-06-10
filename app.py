import streamlit as st
import pandas as pd
import sqlite3

# --- НАСТРОЙКА ПЛАТФОРМЫ ---
COMMISSION_RATE = 0.10  # 10% комиссия сервиса

# --- РАБОТА С БАЗОЙ ДАННЫХ (SQL) ---
def init_db():
    conn = sqlite3.connect("taskearn_v17.db")
    cursor = conn.cursor()
    
    # 1. Таблица пользователей (Объединяет профиль и баланс)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,         -- 'client', 'worker', 'admin'
            username TEXT UNIQUE,       -- Логин для системы
            name TEXT NOT NULL,         -- Отображаемое имя
            phone TEXT NOT NULL,
            about TEXT,
            balance REAL DEFAULT 0.0,
            rating REAL DEFAULT 5.0,
            rating_count INTEGER DEFAULT 1,
            tasks_created INTEGER DEFAULT 0,
            tasks_canceled INTEGER DEFAULT 0
        )
    """)
    
    # Наполняем тестовыми пользователями (демо-данные)
    cursor.execute("""
        INSERT OR IGNORE INTO users (id, role, username, name, phone, about, balance) 
        VALUES (1, 'client', 'ion_cheban', 'Ион Чебан', '+373 68 123 456', 'Заказчик из Кишинева.', 1000.0)
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO users (id, role, username, name, phone, about, balance) 
        VALUES (2, 'worker', 'mihail_lupu', 'Михаил Лупу', '+373 79 987 654', 'Исполнитель из Комрата.', 0.0)
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO users (id, role, username, name, phone, about, balance) 
        VALUES (3, 'admin', 'platform_owner', 'Администратор', '000', 'Владелец платформы', 0.0)
    """)
    
    # 2. Таблица для заданий (Связи через ID)
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

# --- ФУНКЦИИ ДЛЯ СИСТЕМЫ ПОЛЬЗОВАТЕЛЕЙ ---

def get_all_users_by_role(role_type):
    conn = sqlite3.connect("taskearn_v17.db")
    df = pd.read_sql_query("SELECT id, name FROM users WHERE role=?", conn, params=(role_type,))
    conn.close()
    return df.to_dict(orient="records")

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
    # Теперь имя менять можно! Так как связь идет по ID, ничего не сломается.
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

# --- ФУНКЦИИ ДЛЯ ЗАДАЧ ---

def add_task(title, reward, city, village, category, client_id):
    conn = sqlite3.connect("taskearn_v17.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tasks (title, reward, status, city, village, category, client_id) 
        VALUES (?, ?, 'Доступно', ?, ?, ?, ?)
    """, (title, reward, city, village, category, client_id))
    cursor.execute("UPDATE users SET tasks_created = tasks_created + 1 WHERE id=?", (client_id,))
    conn.commit()
    conn.close()

def get_tasks_with_names():
    # Сложный запрос с JOIN, чтобы вытащить имена создателей и исполнителей по их ID
    query = """
        SELECT 
            t.*, 
            c.name AS client_name, 
            w.name AS worker_name,
            w.phone AS worker_phone,
            w.rating AS worker_rating
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
    # Начисляем конкретному воркеру на его ID
    cursor.execute("UPDATE users SET balance = balance + ? WHERE id=?", (worker_cut, worker_id))
    # Начисляем админу (у него ID = 3)
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

# --- ИНИЦИАЛИЗАЦИЯ И ИНТЕРФЕЙС ---
init_db()

CITIES = ["Все регионы", "Кишинёв", "Бельцы", "Комрат", "Кагул", "Оргеев", "Унгены", "Сороки", "Тирасполь"]
CATEGORIES = ["Все категории", "📦 Доставка", "🛠️ Ремонт и дом", "💻 IT и Тексты", "🚗 Автоуслуги", "Другое"]

st.set_page_config(page_title="TaskEarn ID v2", page_icon="🇲🇩", layout="centered")
st.title("🇲🇩 TaskEarn — Реляционная Архитектура (ID)")
st.write("---")

# Выбор роли в Сайдбаре
role_selection = st.sidebar.radio("Выберите роль экрана:", ["💼 Заказчик", "🧑‍💻 Исполнитель", "⚖️ Арбитраж (Админ)"])

# Имитация авторизации через ID для MVP
st.sidebar.subheader("🔑 Симуляция аккаунта")
if role_selection == "💼 Заказчик":
    current_user_id = 1  # Ион Чебан
elif role_selection == "🧑‍💻 Исполнитель":
    current_user_id = 2  # Михаил Лупу
else:
    current_user_id = 3  # Админ

user_data = get_user_by_id(current_user_id)

# Отрендерить метрики пользователя в сайдбаре
if user_data and user_data['role'] != 'admin':
    st.sidebar.metric(label="Ваш личный баланс", value=f"{user_data['balance']} MDL")
    st.sidebar.caption(f"🆔 Ваш ID в системе: `{user_data['id']}`")
    st.sidebar.write(f"👤 Имя: **{user_data['name']}**")
    st.sidebar.write(f"⭐ Рейтинг: `{user_data['rating']} / 5.0`")
    
    if user_data['role'] == 'client':
        if st.sidebar.button("Пополнить баланс на +500 MDL"):
            update_balance(user_data['id'], 500.0)
            st.rerun()
elif user_data and user_data['role'] == 'admin':
    st.sidebar.metric(label="Доход платформы (ID: 3)", value=f"{user_data['balance']} MDL")

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
            submit = st.form_submit_button("Опубликовать и заморозить оплату")
            
            if submit and task_title:
                if user_data['balance'] >= task_reward:
                    loc_village = task_village.strip() if task_village.strip() else "город"
                    update_balance(user_data['id'], -task_reward)
                    add_task(task_title, task_reward, task_city, loc_village, task_category, user_data['id'])
                    st.success("Опубликовано! Деньги зарезервированы.")
                    st.rerun()
                else:
                    st.error("Недостаточно средств на вашем балансе!")

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
                                st.caption(f"🟢 В ленте | Исполнитель получит: {task['reward'] * (1 - COMMISSION_RATE)} MDL")
                            elif task['status'] == 'В работе':
                                st.info(f"🔵 **В работе** у: **{task['worker_name']}** (⭐ {task['worker_rating']})\n\n📞 Связь: {task['worker_phone']}")
                            elif task['status'] == 'На проверке':
                                st.warning(f"🟡 **На проверке!** Перейдите во вторую вкладку.")
                            elif task['status'] == 'Оспорено':
                                st.error(f"🟠 **Вы отклонили работу.** Ждем ответа исполнителя.")
                            elif task['status'] == 'Арбитраж':
                                st.info(f"⚖️ Спор рассматривает Администрация платформы.")
                            else:
                                st.caption(f"⚫ Статус: `{task['status']}`")
                        
                        with col_t2:
                            if task['status'] == 'Доступно':
                                if st.button("❌ Отозвать", key=f"rev_{task['id']}", use_container_width=True):
                                    revoke_free_task(task['id'])
                                    update_balance(user_data['id'], task['reward'])
                                    st.rerun()
                        st.write("-" * 10)

    with tab_review:
        st.header("🔍 Задания на проверке")
        df_tasks = get_tasks_with_names()
        
        if df_tasks.empty:
            st.info("Нет задач.")
        else:
            review_tasks = df_tasks[(df_tasks["status"] == "На проверке") & (df_tasks["client_id"] == user_data['id'])].to_dict(orient="records")
            if not review_tasks:
                st.info("Нет новых работ на проверку.")
            else:
                for task in review_tasks:
                    with st.container():
                        st.write(f"### Задание: {task['title']} ({task['reward']} MDL)")
                        st.warning(f"📌 **Отчёт исполнителя {task['worker_name']}:** {task['worker_evidence']}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("✅ Принять и оплатить", key=f"app_{task['id']}", use_container_width=True):
                                approve_task(task["id"], task["reward"], task["worker_id"])
                                st.success("Оплачено!")
                                st.rerun()
                        with col2:
                            with st.popover("❌ Отклонить", use_container_width=True):
                                with st.form(key=f"dispute_form_{task['id']}"):
                                    reason_text = st.text_area("Причина отказа:")
                                    if st.form_submit_button("🚨 Подтвердить отказ"):
                                        if len(reason_text.strip()) >= 5:
                                            client_dispute_task(task["id"], reason_text.strip())
                                            st.rerun()
                        st.write("---")

    with tab_profile:
        st.header("👤 Профиль")
        with st.form("c_prof"):
            # Имя теперь можно безопасно редактировать!
            new_name = st.text_input("Ваше Имя:", value=user_data['name'])
            p = st.text_input("Телефон:", value=user_data['phone'])
            a = st.text_area("О себе:", value=user_data['about'])
            if st.form_submit_button("Сохранить"):
                update_profile(user_data['id'], new_name, p, a)
                st.success("Обновлено!")
                st.rerun()

# --- ЛОГИКА ИСПОЛНИТЕЛЯ ---
elif user_data and user_data['role'] == 'worker':
    tab_tasks, tab_withdraw, tab_profile = st.tabs(["📋 Лента заданий", "💸 Вывод средств", "👤 Мой профиль"])
    
    with tab_tasks:
        st.header("Лента микрозадач")
        df_tasks = get_tasks_with_names()
        
        if df_tasks.empty:
            st.info("Лента пуста.")
        else:
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
                            st.write(f"💰 Оплата на руки: **{clean_reward} MDL**")
                            st.caption(f"📍 Локация: {task['city']}, {task['village']}")
                            
                            if task['status'] == "Оспорено":
                                st.error(f"⚠️ **Заказчик отклонил отчёт!**\n\nПричина: «{task['cancel_reason']}»")
                            elif task['status'] == "На проверке":
                                st.warning("⏳ На проверке у заказчика.")
                            elif task['status'] == "Арбитраж":
                                st.info("⚖️ Дело отправлено независимому арбитру.")
                        
                        with col2:
                            if task['status'] == "Доступно":
                                if st.button("🤝 Взять в работу", key=f"take_{task['id']}", use_container_width=True):
                                    worker_accept_task(task['id'], user_data['id'])
                                    st.rerun()
                            
                            elif task['status'] == "В работе":
                                with st.popover("📤 Отправить отчет", use_container_width=True):
                                    with st.form(key=f"ev_form_{task['id']}"):
                                        ev_text = st.text_area("Что было сделано:")
                                        if st.form_submit_button("Отправить на проверку"):
                                            if ev_text.strip():
                                                send_to_review(task['id'], ev_text.strip())
                                                st.rerun()
                                
                                if st.button("🚫 Отказаться", key=f"abandon_{task['id']}", use_container_width=True):
                                    worker_abandon_task(task['id'])
                                    st.rerun()
                            
                            elif task['status'] == "Оспорено":
                                if st.button("👍 Согласиться с отменой", key=f"agree_{task['id']}", use_container_width=True):
                                    worker_confirm_cancel(task['id'], task['reward'], task['client_id'], user_data['id'])
                                    st.rerun()
                                
                                with st.popover("⚖️ Подать апелляцию", use_container_width=True):
                                    with st.form(key=f"appeal_form_{task['id']}"):
                                        appeal_text = st.text_area("Ваши аргументы для админа:")
                                        if st.form_submit_button("🚨 Отправить в Арбитраж"):
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
                    st.success("Успешно выведено!")
                    st.rerun()

    with tab_profile:
        st.header("👤 Профиль Исполнителя")
        with st.form("w_prof"):
            new_name = st.text_input("Ваше Имя:", value=user_data['name'])
            p = st.text_input("Телефон:", value=user_data['phone'])
            a = st.text_area("О себе:", value=user_data['about'])
            if st.form_submit_button("Сохранить изменения"):
                update_profile(user_data['id'], new_name, p, a)
                st.success("Профиль успешно обновлен!")
                st.rerun()

# --- ПАНЕЛЬ АДМИНИСТРАТОРА ---
elif user_data and user_data['role'] == 'admin':
    st.header("👑 Панель Администратора")
    df_tasks = get_tasks_with_names()
    
    if df_tasks.empty:
        st.info("Нет активных споров.")
    else:
        arbitration_tasks = df_tasks[df_tasks["status"] == "Арбитраж"].to_dict(orient="records")
        if not arbitration_tasks:
            st.info("Все споры урегулированы.")
        else:
            for task in arbitration_tasks:
                with st.expander(f"⚖️ Спор по задаче: {task['title']}"):
                    st.write(f"**Заказчик:** {task['client_name']} (ID: {task['client_id']})")
                    st.write(f"**Исполнитель:** {task['worker_name']} (ID: {task['worker_id']})")
                    st.write(f"📋 **Текст отчета:** {task['worker_evidence']}")
                    st.write(f"❌ **Претензия заказчика:** {task['cancel_reason']}")
                    st.write(f"🚨 **Контр-аргумент воркера:** {task['appeal_text']}")
                    
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
