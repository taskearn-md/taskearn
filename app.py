import streamlit as st
import pandas as pd
import sqlite3
import random
import time
import datetime

# --- НАСТРОЙКА ПЛАТФОРМЫ ---
COMMISSION_RATE = 0.10  # 10% комиссия сервиса

# --- РАБОТА С БАЗОЙ ДАННЫХ (SQL) ---
def init_db():
    conn = sqlite3.connect("taskearn_v23.db")
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,     
            role TEXT NOT NULL,
            username TEXT UNIQUE,
            name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL, 
            about TEXT,
            balance REAL DEFAULT 0.0,
            rating REAL DEFAULT 5.0,
            rating_count INTEGER DEFAULT 1,
            tasks_created INTEGER DEFAULT 0,
            tasks_canceled INTEGER DEFAULT 0
        )
    """)
    
    # Создаем дефолтных пользователей для тестов
    cursor.execute("""
        INSERT OR IGNORE INTO users (id, role, username, name, phone, about, balance)  
        VALUES (482910, 'user', 'ion_cheban', 'Ион Чебан (Универсал)', '+37368123456', 'Пользователь из Кишинева.', 1000.0)
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO users (id, role, username, name, phone, about, balance)  
        VALUES (730145, 'user', 'mihail_lupu', 'Михаил Лупу (Универсал)', '+37379987654', 'Исполнитель из Комрата.', 0.0)
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO users (id, role, username, name, phone, about, balance)  
        VALUES (999111, 'admin', 'platform_owner', 'Администратор', '000', 'Владелец платформы', 0.0)
    """)
    
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
            client_id INTEGER NOT NULL,
            worker_id INTEGER DEFAULT NULL,
            cancel_reason TEXT DEFAULT '',
            worker_evidence TEXT DEFAULT '',
            appeal_text TEXT DEFAULT '',
            created_at TEXT,
            completed_at TEXT,
            FOREIGN KEY(client_id) REFERENCES users(id),
            FOREIGN KEY(worker_id) REFERENCES users(id)
        )
    """)
    
    # Автоматическая миграция колонок дат
    try:
        cursor.execute("ALTER TABLE tasks ADD COLUMN created_at TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE tasks ADD COLUMN completed_at TEXT")
    except sqlite3.OperationalError:
        pass
        
    conn.commit()
    conn.close()

def generate_unique_id():
    conn = sqlite3.connect("taskearn_v23.db")
    cursor = conn.cursor()
    while True:
        new_id = random.randint(100000, 999999)
        cursor.execute("SELECT id FROM users WHERE id = ?", (new_id,))
        if not cursor.fetchone():
            conn.close()
            return new_id

def register_user(user_id, role, name, phone, about, init_balance=0.0):
    conn = sqlite3.connect("taskearn_v23.db")
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO users (id, role, username, name, phone, about, balance)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, role, f"user_{user_id}", name, phone, about, init_balance))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    conn.close()
    return success

def get_user_by_id(user_id):
    conn = sqlite3.connect("taskearn_v23.db")
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

def get_user_by_phone(phone):
    conn = sqlite3.connect("taskearn_v23.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE phone=?", (phone.strip(),))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else None

def update_profile(user_id, name, phone, about):
    conn = sqlite3.connect("taskearn_v23.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET name=?, phone=?, about=? WHERE id=?", (name, phone, about, user_id))
    conn.commit()
    conn.close()

def update_balance(user_id, amount):
    conn = sqlite3.connect("taskearn_v23.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ? WHERE id=?", (amount, user_id))
    conn.commit()
    conn.close()

def change_rating_flat(user_id, penalty):
    conn = sqlite3.connect("taskearn_v23.db")
    cursor = conn.cursor()
    cursor.execute("SELECT rating FROM users WHERE id=?", (user_id,))
    res = cursor.fetchone()
    if res:
        new_rating = max(1.0, min(5.0, res[0] + penalty))
        cursor.execute("UPDATE users SET rating=? WHERE id=?", (new_rating, user_id))
    conn.commit()
    conn.close()

def add_task(title, reward, city, village, category, client_id):
    now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = sqlite3.connect("taskearn_v23.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tasks (title, reward, status, city, village, category, client_id, created_at) 
        VALUES (?, ?, 'Доступно', ?, ?, ?, ?, ?)
    """, (title, reward, city, village, category, client_id, now_str))
    cursor.execute("UPDATE users SET tasks_created = tasks_created + 1 WHERE id=?", (client_id,))
    conn.commit()
    conn.close()

# 📞 ДОБАВИЛИ В ВЫБОРКУ c.phone КАК client_phone
def get_tasks_with_names():
    query = """
        SELECT t.*, c.name AS client_name, c.phone AS client_phone, w.name AS worker_name, w.phone AS worker_phone, w.rating AS worker_rating
        FROM tasks t
        JOIN users c ON t.client_id = c.id
        LEFT JOIN users w ON t.worker_id = w.id
    """
    conn = sqlite3.connect("taskearn_v23.db")
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def revoke_free_task(task_id):
    conn = sqlite3.connect("taskearn_v23.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()
    conn.close()

def worker_accept_task(task_id, worker_id):
    conn = sqlite3.connect("taskearn_v23.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='В работе', worker_id=? WHERE id=?", (worker_id, task_id))
    conn.commit()
    conn.close()

def worker_abandon_task(task_id):
    conn = sqlite3.connect("taskearn_v23.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='Доступно', worker_id=NULL, worker_evidence='' WHERE id=?", (task_id,))
    conn.commit()
    conn.close()

def send_to_review(task_id, evidence):
    conn = sqlite3.connect("taskearn_v23.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='На проверке', worker_evidence=? WHERE id=?", (evidence, task_id))
    conn.commit()
    conn.close()

def approve_task(task_id, total_reward, worker_id):
    now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    admin_cut = total_reward * COMMISSION_RATE
    worker_cut = total_reward - admin_cut
    conn = sqlite3.connect("taskearn_v23.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='Выполнено', completed_at=? WHERE id=?", (now_str, task_id))
    cursor.execute("UPDATE users SET balance = balance + ? WHERE id=?", (worker_cut, worker_id))
    cursor.execute("UPDATE users SET balance = balance + ? WHERE id=999111", (admin_cut,))
    conn.commit()
    conn.close()

def client_dispute_task(task_id, reason):
    conn = sqlite3.connect("taskearn_v23.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='Оспорено', cancel_reason=? WHERE id=?", (reason, task_id))
    conn.commit()
    conn.close()

def worker_confirm_cancel(task_id, reward, client_id, worker_id):
    conn = sqlite3.connect("taskearn_v23.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='Отменено' WHERE id=?", (task_id,))
    cursor.execute("UPDATE users SET balance = balance + ? WHERE id=?", (reward, client_id))
    cursor.execute("UPDATE users SET tasks_canceled = tasks_canceled + 1 WHERE id=?", (client_id,))
    conn.commit()
    conn.close()
    change_rating_flat(worker_id, -0.6)

def worker_send_to_arbitration(task_id, appeal_text):
    conn = sqlite3.connect("taskearn_v23.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='Арбитраж', appeal_text=? WHERE id=?", (appeal_text, task_id))
    conn.commit()
    conn.close()

def get_monthly_stats(user_id):
    current_month = datetime.datetime.now().strftime('%Y-%m')
    conn = sqlite3.connect("taskearn_v23.db")
    cursor = conn.cursor()
    
    # 1. Исполнитель
    cursor.execute("""
        SELECT SUM(reward), COUNT(id) FROM tasks 
        WHERE worker_id = ? AND status = 'Выполнено' AND completed_at LIKE ?
    """, (user_id, f"{current_month}%"))
    worker_res = cursor.fetchone()
    raw_income = worker_res[0] if worker_res[0] else 0.0
    worker_income = raw_income * (1 - COMMISSION_RATE)
    completed_tasks_count = worker_res[1] if worker_res[1] else 0
    
    # 2. Заказчик
    cursor.execute("""
        SELECT SUM(reward) FROM tasks 
        WHERE client_id = ? AND status = 'Выполнено' AND completed_at LIKE ?
    """, (user_id, f"{current_month}%"))
    client_res = cursor.fetchone()
    client_expenses = client_res[0] if client_res[0] else 0.0
    
    conn.close()
    return {
        "worker_income": round(worker_income, 2),
        "completed_tasks": completed_tasks_count,
        "client_expenses": round(client_expenses, 2)
    }

# --- ИНИЦИАЛИЗАЦИЯ И СЕССИИ ---
init_db()

CITIES = ["Все регионы", "Кишинёв", "Бельцы", "Комрат", "Кагул", "Оргеев", "Унгены", "Сороки", "Тирасполь"]
CATEGORIES = ["Все категории", "📦 Доставка", "🛠️ Ремонт и дом", "💻 IT и Тексты", "🚗 Автоуслуги", "Другое"]

st.set_page_config(page_title="TaskEarn MD", page_icon="🇲🇩", layout="centered")

# ВОССТАНОВЛЕНИЕ СЕССИИ ПРИ ПЕРЕЗАГРУЗКЕ СТРАНИЦЫ
if "user_id" in st.query_params and "logged_in_user_id" not in st.session_state:
    try:
        st.session_state["logged_in_user_id"] = int(st.query_params["user_id"])
    except ValueError:
        st.session_state["logged_in_user_id"] = None

if "logged_in_user_id" not in st.session_state:
    st.session_state["logged_in_user_id"] = None
if "sms_code" not in st.session_state:
    st.session_state["sms_code"] = None
if "pending_phone" not in st.session_state:
    st.session_state["pending_phone"] = None
if "pending_user_data" not in st.session_state:
    st.session_state["pending_user_data"] = None

# --- ЭКРАН ВХОДА И SMS ПОДТВЕРЖДЕНИЯ ---
if st.session_state["logged_in_user_id"] is None:
    st.title("🇲🇩 Вход в TaskEarn")
    st.write("Введите свой номер мобильного для получения проверочного кода.")
    
    if st.session_state["sms_code"] is not None:
        st.info(f"Код верификации отправлен на номер: **{st.session_state['pending_phone']}**")
        input_sms = st.text_input("Введите 4-значный код из SMS:", max_chars=4, key="verification_sms_input")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("🔄 Отправить код повторно", use_container_width=True, key="resend_sms_global"):
                st.session_state["sms_code"] = str(random.randint(1000, 9999))
                st.toast(f"💬 Новое SMS на {st.session_state['pending_phone']}: Код {st.session_state['sms_code']}", icon="💬")
                st.rerun()
        with col_btn2:
            if st.button("❌ Сбросить / Назад", use_container_width=True, key="reset_sms_global"):
                st.session_state["sms_code"] = None
                st.session_state["pending_phone"] = None
                st.session_state["pending_user_data"] = None
                st.rerun()

        if input_sms:
            if input_sms.strip() == st.session_state["sms_code"]:
                if st.session_state["pending_user_data"] is None:
                    user_id = get_user_by_phone(st.session_state["pending_phone"])
                    st.session_state["logged_in_user_id"] = user_id
                    st.query_params["user_id"] = str(user_id)
                    st.session_state["sms_code"] = None
                    st.session_state["pending_phone"] = None
                    st.success("Успешный вход!")
                    st.rerun()
                else:
                    p_data = st.session_state["pending_user_data"]
                    new_id = generate_unique_id()
                    if register_user(new_id, p_data['role'], p_data['name'], p_data['phone'], p_data['about'], p_data['balance']):
                        st.session_state["logged_in_user_id"] = new_id
                        st.query_params["user_id"] = str(new_id)
                        st.session_state["sms_code"] = None
                        st.session_state["pending_phone"] = None
                        st.session_state["pending_user_data"] = None
                        st.success("Регистрация успешно завершена!")
                        st.rerun()
            elif len(input_sms.strip()) == 4:
                st.error("Неверный код безопасности. Попробуйте еще раз.")
        st.stop()

    tab_login, tab_register = st.tabs(["🔑 Войти", "✨ Зарегистрироваться"])
    
    with tab_login:
        login_phone = st.text_input("Ваш телефон (например, +37368123456):", key="log_p")
        st.caption("Тестовые номера: Пользователи `+37368123456`, `+37379987654`, Админ `000`")
        
        if st.button("Получить код по SMS", key="log_submit", use_container_width=True):
            cleaned_phone = login_phone.strip().replace(" ", "")
            if cleaned_phone:
                user_id = get_user_by_phone(cleaned_phone)
                if user_id:
                    st.session_state["sms_code"] = str(random.randint(1000, 9999))
                    st.session_state["pending_phone"] = cleaned_phone
                    st.session_state["pending_user_data"] = None
                    st.toast(f"💬 SMS на {cleaned_phone}: Ваш код подтверждения {st.session_state['sms_code']}", icon="💬")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Пользователь с таким номером телефона не зарегистрирован.")
            else:
                st.error("Пожалуйста, укажите корректный номер телефона.")
                
    with tab_register:
        reg_name = st.text_input("Имя и Фамилия:", key="reg_fullname")
        reg_phone = st.text_input("Номер мобильного (например, +37377799999):", key="reg_phone_num")
        reg_about = st.text_area("Пара слов о себе:", key="reg_about_text")
        
        if st.button("Зарегистрироваться по SMS", use_container_width=True, key="reg_submit_btn"):
            cl_phone = reg_phone.strip().replace(" ", "")
            if not reg_name.strip() or not cl_phone:
                st.error("Имя и номер телефона обязательны для заполнения.")
            elif get_user_by_phone(cl_phone) is not None:
                st.error("Этот номер телефона уже занят другим аккаунтом!")
            else:
                st.session_state["sms_code"] = str(random.randint(1000, 9999))
                st.session_state["pending_phone"] = cl_phone
                st.session_state["pending_user_data"] = {
                    "role": "user", "name": reg_name.strip(), "phone": cl_phone,
                    "about": reg_about.strip(), "balance": 250.0
                }
                st.toast(f"💬 SMS на {cl_phone}: Код подтверждения регистрации {st.session_state['sms_code']}", icon="💬")
                time.sleep(0.5)
                st.rerun()
    st.stop()

# --- ТЕКУЩИЙ СЕАНС ПОЛЬЗОВАТЕЛЯ ---
user_data = get_user_by_id(st.session_state["logged_in_user_id"])
if not user_data:
    st.session_state["logged_in_user_id"] = None
    st.query_params.clear()
    st.rerun()

# --- БОКОВАЯ ПАНЕЛЬ С ПРОФИЛЕМ, БАЛАНСОМ И АНАЛИТИКОЙ ---
st.sidebar.header("👤 Личный Кабинет")
st.sidebar.write(f"👋 Привет, **{user_data['name']}**")
st.sidebar.write(f"🆔 **ID:** `{user_data['id']}`")
st.sidebar.write(f"📞 **Логин:** `{user_data['phone']}`")

if user_data['role'] != 'admin':
    st.sidebar.write(f"⭐ **Рейтинг:** `{user_data['rating']} / 5.0`")
    st.sidebar.metric(label="Текущий Баланс", value=f"{user_data['balance']} MDL")
    
    col_s1, col_s2 = st.sidebar.columns(2)
    with col_s1:
        if st.button("👛 +500 MDL", key="sb_deposit_btn", use_container_width=True):
            update_balance(user_data['id'], 500.0)
            st.rerun()
    with col_s2:
        if st.button("🚪 Выйти", key="sb_logout_btn", use_container_width=True):
            st.session_state["logged_in_user_id"] = None
            st.query_params.clear()
            st.rerun()
            
    st.sidebar.write("---")
    
    with st.sidebar.expander("📊 Аналитика за месяц", expanded=False):
        stats = get_monthly_stats(user_data['id'])
        st.metric(label="💰 Заработано воркером", value=f"{stats['worker_income']} MDL")
        st.metric(label="✅ Выполнено задач", value=f"{stats['completed_tasks']} шт.")
        st.metric(label="📉 Затраты заказчика", value=f"{stats['client_expenses']} MDL")

    with st.sidebar.expander("⚙️ Редактировать профиль", expanded=False):
        with st.form("sidebar_profile_form", clear_on_submit=False):
            new_name = st.text_input("Ваше имя / ник:", value=user_data['name'])
            new_about = st.text_area("О себе (навыки):", value=user_data['about'])
            if st.form_submit_button("Сохранить"):
                update_profile(user_data['id'], new_name, user_data['phone'], new_about)
                st.success("Данные обновлены!")
                st.rerun()
else:
    st.sidebar.metric(label="Доход сервиса (Комиссия)", value=f"{user_data['balance']} MDL")
    if st.sidebar.button("🚪 Выйти из панели", key="sb_logout_admin", use_container_width=True):
        st.session_state["logged_in_user_id"] = None
        st.query_params.clear()
        st.rerun()

# --- ГЛАВНЫЙ ЭКРАН ПЛАТФОРМЫ ---
st.title("🇲🇩 Платформа микрозадач TaskEarn")
st.write("---")

if user_data['role'] != 'admin':
    tab_tasks, tab_review, tab_market, tab_withdraw = st.tabs([
        "📋 Мои Задания (Заказчик)", 
        "🔍 Контроль выполнения", 
        "🛠️ Биржа задач (Исполнитель)", 
        "💸 Вывод баланса"
    ])
    
    # 1. ВКЛАДКА: СОЗДАНИЕ ЗАДАНИЙ (ЗАКАЗЧИК)
    with tab_tasks:
        st.header("Разместить новый заказ")
        with st.form("new_task_form", clear_on_submit=True):
            task_title = st.text_input("Что нужно сделать (Краткое описание):", key="form_task_title")
            task_city = st.selectbox("Регион/Город:", CITIES[1:], key="form_task_city")
            task_village = st.text_input("Укажите село/улицу (если нужно):", key="form_task_village")
            task_category = st.selectbox("Категория работы:", CATEGORIES[1:], key="form_task_category")
            task_reward = st.number_input("Бюджет задания (MDL)", min_value=20, value=150, step=10, key="form_task_reward")
            submit = st.form_submit_button("Запустить в ленту")
            
            if submit and task_title:
                fresh_user = get_user_by_id(user_data['id'])
                if fresh_user['balance'] >= task_reward:
                    loc_village = task_village.strip() if task_village.strip() else "город"
                    update_balance(user_data['id'], -task_reward)
                    add_task(task_title, task_reward, task_city, loc_village, task_category, user_data['id'])
                    st.success("Задание успешно добавлено в общую ленту!")
                    st.rerun()
                else:
                    st.error("Ошибка: Баланс вашего счета ниже стоимости задания. Пополните счет.")

        st.write("---")
        st.subheader("📋 История ваших заказов")
        df_tasks = get_tasks_with_names()
        
        if df_tasks.empty:
            st.info("Вы еще не создавали заказов.")
        else:
            my_tasks = df_tasks[df_tasks["client_id"] == user_data['id']].to_dict(orient="records")
            if not my_tasks:
                st.info("Нет активных заказов.")
            else:
                for task in my_tasks:
                    with st.container():
                        col_t1, col_t2 = st.columns([3, 1])
                        with col_t1:
                            st.write(f"**{task['title']}** — 💰 {task['reward']} MDL")
                            if task['status'] == 'Доступно':
                                st.caption(f"🟢 Свободно. Ожидает отклика исполнителей.")
                            elif task['status'] == 'В работе':
                                st.info(f"🔵 **Исполняется:** {task['worker_name']} | 📞 {task['worker_phone']}")
                            elif task['status'] == 'На проверке':
                                st.warning(f"🟡 **Контроль:** Исполнитель сдал работу. Проверьте её.")
                            elif task['status'] == 'Оспорено':
                                st.error(f"🟠 Задание отклонено вами. Ожидание апелляции.")
                            elif task['status'] == 'Арбитраж':
                                st.info(f"⚖️ Спор рассматривается модератором.")
                        with col_t2:
                            if task['status'] == 'Доступно':
                                if st.button("❌ Удалить", key=f"rev_{task['id']}", use_container_width=True):
                                    revoke_free_task(task['id'])
                                    update_balance(user_data['id'], task['reward'])
                                    st.rerun()
                        st.write("---")

    # 2. ВКЛАДКА: КОНТРОЛЬ ЗАКАЗЧИКА
    with tab_review:
        st.header("🔍 Проверка присланных работ")
        df_tasks = get_tasks_with_names()
        if not df_tasks.empty:
            review_tasks = df_tasks[(df_tasks["status"] == "На проверке") & (df_tasks["client_id"] == user_data['id'])].to_dict(orient="records")
            if not review_tasks:
                st.info("Нет задач, требующих вашего утверждения.")
            else:
                for task in review_tasks:
                    st.write(f"### Задача: {task['title']}")
                    st.markdown(f"> 📄 **Текст отчета от исполнителя:** {task['worker_evidence']}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Подтвердить выполнение", key=f"app_{task['id']}", use_container_width=True):
                            approve_task(task["id"], task["reward"], task["worker_id"])
                            st.success("Оплата переведена воркеру!")
                            st.rerun()
                    with col2:
                        with st.popover("❌ Отклонить отчет", use_container_width=True, key=f"pop_dispute_{task['id']}"):
                            with st.form(key=f"dis_form_{task['id']}"):
                                reason_text = st.text_area("Опишите, что именно не сделано:", key=f"reason_text_input_{task['id']}")
                                if st.form_submit_button("🚨 Отправить отказ"):
                                    if len(reason_text.strip()) >= 5:
                                        client_dispute_task(task["id"], reason_text.strip())
                                        st.rerun()

    # 3. ВКЛАДКА: БИРЖА ТРУДА (ИСПОЛНИТЕЛЬ)
    with tab_market:
        st.header("Лента актуальных заданий Молдавии")
        df_tasks = get_tasks_with_names()
        if not df_tasks.empty:
            my_current_tasks = df_tasks[
                ((df_tasks["status"] == "Доступно") & (df_tasks["client_id"] != user_data['id'])) | 
                ((df_tasks["worker_id"] == user_data['id']) & (df_tasks["status"].isin(["В работе", "На проверке", "Оспорено", "Арбитраж"])))
            ]
            if my_current_tasks.empty:
                st.info("Лента пуста или содержит только ваши собственные задания.")
            else:
                for task in my_current_tasks.to_dict(orient="records"):
                    clean_reward = task['reward'] * (1 - COMMISSION_RATE)
                    with st.container():
                        col1, col2 = st.columns([3, 2])
                        with col1:
                            st.write(f"**{task['title']}**")
                            st.write(f"💰 Оплата (чистая): **{clean_reward} MDL**")
                            st.caption(f"📍 Локация: {task['city']}, {task['village']}")
                            
                            # 🔄 СТРОКА СВЯЗИ С ЗАКАЗЧИКОМ ПРИ СТАТУСЕ "В РАБОТЕ"
                            if task['status'] == "В работе":
                                st.info(f"📞 **Связаться с заказчиком:** {task['client_name']} ({task['client_phone']})")
                            elif task['status'] == "Оспорено":
                                st.error(f"⚠️ Отклонено! Причина заказчика: «{task['cancel_reason']}»")
                            elif task['status'] == "На проверке":
                                st.warning("⏳ Проверяется заказчиком. Ожидайте.")
                            elif task['status'] == "Арбитраж":
                                st.info("⚖️ Дело передано независимому арбитру.")
                        with col2:
                            if task['status'] == "Доступно":
                                if st.button("🤝 Взять заказ", key=f"take_{task['id']}", use_container_width=True):
                                    worker_accept_task(task['id'], user_data['id'])
                                    st.rerun()
                            elif task['status'] == "В работе":
                                with st.popover("📤 Сдать готовую работу", use_container_width=True, key=f"pop_review_{task['id']}"):
                                    with st.form(key=f"ev_f_{task['id']}"):
                                        ev_text = st.text_area("Опишите результаты (ссылки/текст):", key=f"evidence_input_{task['id']}")
                                        if st.form_submit_button("Сдать заказ"):
                                            if ev_text.strip():
                                                send_to_review(task['id'], ev_text.strip())
                                                st.rerun()
                                if st.button("🚫 Отказаться от задачи", key=f"abd_{task['id']}", use_container_width=True):
                                    worker_abandon_task(task['id'])
                                    st.rerun()
                            elif task['status'] == "Оспорено":
                                if st.button("👍 Согласиться с отменой", key=f"agr_{task['id']}", use_container_width=True):
                                    worker_confirm_cancel(task['id'], task['reward'], task['client_id'], user_data['id'])
                                    st.rerun()
                                with st.popover("⚖️ Передать спор админу", use_container_width=True, key=f"pop_arbitration_{task['id']}"):
                                    with st.form(key=f"ap_f_{task['id']}"):
                                        appeal_text = st.text_area("Напишите ваши аргументы:", key=f"appeal_input_{task['id']}")
                                        if st.form_submit_button("🚨 Начать арбитраж"):
                                            if len(appeal_text.strip()) >= 5:
                                                worker_send_to_arbitration(task['id'], appeal_text.strip())
                                                st.rerun()
                        st.write("---")

    # 4. ВКЛАДКА: ВЫВОД СРЕДСТВ
    with tab_withdraw:
        st.header("💸 Заявка на выплату")
        st.write(f"Доступные средства: **{user_data['balance']} MDL**")
        with st.form("withdraw_form"):
            withdraw_amount = st.number_input("Какую сумму вывести:", min_value=50, value=50, step=10, key="w_amount_input")
            card_number = st.text_input("Номер банковской карты MD (16 цифр):", key="w_card_input")
            if st.form_submit_button("Подтвердить выплату"):
                if user_data['balance'] >= withdraw_amount and len(card_number.strip()) >= 16:
                    update_balance(user_data['id'], -withdraw_amount)
                    st.success("Выплата успешно отправлена в обработку банк-партнер!")
                    st.rerun()
                else:
                    st.error("Ошибка: Проверьте баланс или корректность номера карты.")

# --- ПАНЕЛЬ АДМИНИСТРАТОРА (АРБИТРАЖ) ---
elif user_data['role'] == 'admin':
    st.header("👑 Панель Арбитража")
    df_tasks = get_tasks_with_names()
    
    arbitration_tasks = df_tasks[df_tasks["status"] == "Арбитраж"].to_dict(orient="records")
    if not arbitration_tasks:
        st.info("Активных споров в системе нет. Всё работает стабильно.")
    else:
        for task in arbitration_tasks:
            with st.expander(f"⚖️ Спор по заданию #{task['id']}: {task['title']}"):
                st.write(f"**Заказчик:** {task['client_name']} (ID: {task['client_id']})")
                st.write(f"**Исполнитель:** {task['worker_name']} (ID: {task['worker_id']})")
                
                st.info(f"📄 **Отчет воркера:** {task['worker_evidence']}")
                st.warning(f"❌ **Претензия заказчика:** {task['cancel_reason']}")
                st.error(f"🚨 **Апелляция воркера:** {task['appeal_text']}")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("✅ Выплатить Исполнителю", key=f"win_w_{task['id']}", use_container_width=True):
                        approve_task(task['id'], task['reward'], task['worker_id'])
                        st.success("Решение принято: деньги отправлены исполнителю.")
                        st.rerun()
                
                with col2:
                    if st.button("🔙 Вернуть Заказчику", key=f"win_c_{task['id']}", use_container_width=True):
                        conn = sqlite3.connect("taskearn_v23.db")
                        cursor = conn.cursor()
                        cursor.execute("UPDATE tasks SET status='Отменено' WHERE id=?", (task['id'],))
                        cursor.execute("UPDATE users SET balance = balance + ? WHERE id=?", (task['reward'], task['client_id']))
                        conn.commit()
                        conn.close()
                        st.success("Решение принято: деньги возвращены заказчику.")
                        st.rerun()
