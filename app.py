import streamlit as st
import pandas as pd
import sqlite3
import random
import time

# --- НАСТРОЙКА ПЛАТФОРМЫ ---
COMMISSION_RATE = 0.10  # 10% комиссия сервиса

# --- РАБОТА С БАЗОЙ ДАННЫХ (SQL) ---
def init_db():
    conn = sqlite3.connect("taskearn_v20.db")
    cursor = conn.cursor()
    
    # Таблица пользователей (Теперь UNIQUE стоит на номере телефона!)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,     
            role TEXT NOT NULL,
            username TEXT UNIQUE,
            name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL, -- Вход по уникальному телефону
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
        VALUES (482910, 'client', 'ion_cheban', 'Ион Чебан (Заказчик)', '+37368123456', 'Заказчик из Кишинева.', 1000.0)
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO users (id, role, username, name, phone, about, balance) 
        VALUES (730145, 'worker', 'mihail_lupu', 'Михаил Лупу (Воркер)', '+37379987654', 'Исполнитель из Комрата.', 0.0)
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
            FOREIGN KEY(client_id) REFERENCES users(id),
            FOREIGN KEY(worker_id) REFERENCES users(id)
        )
    """)
    conn.commit()
    conn.close()

def generate_unique_id():
    conn = sqlite3.connect("taskearn_v20.db")
    cursor = conn.cursor()
    while True:
        new_id = random.randint(100000, 999999)
        cursor.execute("SELECT id FROM users WHERE id = ?", (new_id,))
        if not cursor.fetchone():
            conn.close()
            return new_id

def register_user(user_id, role, name, phone, about, init_balance=0.0):
    conn = sqlite3.connect("taskearn_v20.db")
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
    conn = sqlite3.connect("taskearn_v20.db")
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
    conn = sqlite3.connect("taskearn_v20.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE phone=?", (phone.strip(),))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else None

def update_profile(user_id, name, phone, about):
    conn = sqlite3.connect("taskearn_v20.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET name=?, phone=?, about=? WHERE id=?", (name, phone, about, user_id))
    conn.commit()
    conn.close()

def update_balance(user_id, amount):
    conn = sqlite3.connect("taskearn_v20.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ? WHERE id=?", (amount, user_id))
    conn.commit()
    conn.close()

def change_rating_flat(user_id, penalty):
    conn = sqlite3.connect("taskearn_v20.db")
    cursor = conn.cursor()
    cursor.execute("SELECT rating FROM users WHERE id=?", (user_id,))
    res = cursor.fetchone()
    if res:
        new_rating = max(1.0, min(5.0, res[0] + penalty))
        cursor.execute("UPDATE users SET rating=? WHERE id=?", (new_rating, user_id))
    conn.commit()
    conn.close()

def add_task(title, reward, city, village, category, client_id):
    conn = sqlite3.connect("taskearn_v20.db")
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
    conn = sqlite3.connect("taskearn_v20.db")
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def revoke_free_task(task_id):
    conn = sqlite3.connect("taskearn_v20.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()
    conn.close()

def worker_accept_task(task_id, worker_id):
    conn = sqlite3.connect("taskearn_v20.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='В работе', worker_id=? WHERE id=?", (worker_id, task_id))
    conn.commit()
    conn.close()

def worker_abandon_task(task_id):
    conn = sqlite3.connect("taskearn_v20.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='Доступно', worker_id=NULL, worker_evidence='' WHERE id=?", (task_id,))
    conn.commit()
    conn.close()

def send_to_review(task_id, evidence):
    conn = sqlite3.connect("taskearn_v20.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='На проверке', worker_evidence=? WHERE id=?", (evidence, task_id))
    conn.commit()
    conn.close()

def approve_task(task_id, total_reward, worker_id):
    admin_cut = total_reward * COMMISSION_RATE
    worker_cut = total_reward - admin_cut
    conn = sqlite3.connect("taskearn_v20.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='Выполнено' WHERE id=?", (task_id,))
    cursor.execute("UPDATE users SET balance = balance + ? WHERE id=?", (worker_cut, worker_id))
    cursor.execute("UPDATE users SET balance = balance + ? WHERE id=999111", (admin_cut,))
    conn.commit()
    conn.close()

def client_dispute_task(task_id, reason):
    conn = sqlite3.connect("taskearn_v20.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='Оспорено', cancel_reason=? WHERE id=?", (reason, task_id))
    conn.commit()
    conn.close()

def worker_confirm_cancel(task_id, reward, client_id, worker_id):
    conn = sqlite3.connect("taskearn_v20.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='Отменено' WHERE id=?", (task_id,))
    cursor.execute("UPDATE users SET balance = balance + ? WHERE id=?", (reward, client_id))
    cursor.execute("UPDATE users SET tasks_canceled = tasks_canceled + 1 WHERE id=?", (client_id,))
    conn.commit()
    conn.close()
    change_rating_flat(worker_id, -0.6)

def worker_send_to_arbitration(task_id, appeal_text):
    conn = sqlite3.connect("taskearn_v20.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status='Арбитраж', appeal_text=? WHERE id=?", (appeal_text, task_id))
    conn.commit()
    conn.close()

# --- ИНИЦИАЛИЗАЦИЯ И СЕССИИ ---
init_db()

CITIES = ["Все регионы", "Кишинёв", "Бельцы", "Комрат", "Кагул", "Оргеев", "Унгены", "Сороки", "Тирасполь"]
CATEGORIES = ["Все категории", "📦 Доставка", "🛠️ Ремонт и дом", "💻 IT и Тексты", "🚗 Автоуслуги", "Другое"]

st.set_page_config(page_title="TaskEarn SMS Auth", page_icon="🇲🇩", layout="centered")

# Переменные сессии для авторизации
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
    st.title("🇲🇩 Вход в TaskEarn по номеру телефона")
    st.write("Введите свой номер мобильного. Система отправит вам проверочный SMS-код.")
    
    # Сценарий 1: Ожидание ввода SMS-кода
    if st.session_state["sms_code"] is not None:
        st.info(f"Код верификации отправлен на номер: **{st.session_state['pending_phone']}**")
        input_sms = st.text_input("Введите 4-значный код из SMS:", max_chars=4)
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("🔄 Отправить код повторно", use_container_width=True):
                st.session_state["sms_code"] = str(random.randint(1000, 9999))
                st.toast(f"💬 Новое SMS на {st.session_state['pending_phone']}: Код {st.session_state['sms_code']}", icon="💬")
                st.rerun()
        with col_btn2:
            if st.button("❌ Сбросить / Назад", use_container_width=True):
                st.session_state["sms_code"] = None
                st.session_state["pending_phone"] = None
                st.session_state["pending_user_data"] = None
                st.rerun()

        if input_sms:
            if input_sms.strip() == st.session_state["sms_code"]:
                # Проверяем, это вход существующего или регистрация нового
                if st.session_state["pending_user_data"] is None:
                    # ВХОД
                    user_id = get_user_by_phone(st.session_state["pending_phone"])
                    st.session_state["logged_in_user_id"] = user_id
                    st.session_state["sms_code"] = None
                    st.session_state["pending_phone"] = None
                    st.success("Успешный вход!")
                    st.rerun()
                else:
                    # РЕГИСТРАЦИЯ НОВОГО
                    p_data = st.session_state["pending_user_data"]
                    new_id = generate_unique_id()
                    if register_user(new_id, p_data['role'], p_data['name'], p_data['phone'], p_data['about'], p_data['balance']):
                        st.session_state["logged_in_user_id"] = new_id
                        st.session_state["sms_code"] = None
                        st.session_state["pending_phone"] = None
                        st.session_state["pending_user_data"] = None
                        st.success("Регистрация успешно завершена!")
                        st.rerun()
            elif len(input_sms.strip()) == 4:
                st.error("Неверный код безопасности. Попробуйте еще раз.")
        st.stop()

    # Сценарий 2: Первичный ввод телефона или регистрация
    tab_login, tab_register = st.tabs(["🔑 Войти", "✨ Зарегистрироваться"])
    
    with tab_login:
        login_phone = st.text_input("Ваш телефон (например, +37368123456):", key="log_p")
        st.caption("Тестовые номера в системе: Заказчик `+37368123456`, Воркер `+37379987654`, Админ `000`")
        
        if st.button("Получить код по SMS", key="log_submit", use_container_width=True):
            cleaned_phone = login_phone.strip().replace(" ", "")
            if cleaned_phone:
                user_id = get_user_by_phone(cleaned_phone)
                if user_id:
                    # Генерируем SMS-код
                    st.session_state["sms_code"] = str(random.randint(1000, 9999))
                    st.session_state["pending_phone"] = cleaned_phone
                    st.session_state["pending_user_data"] = None
                    
                    # Симуляция отправки SMS через Toast-уведомление Streamlit
                    st.toast(f"💬 SMS на {cleaned_phone}: Ваш код подтверждения {st.session_state['sms_code']}", icon="💬")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Пользователь с таким номером телефона не зарегистрирован.")
            else:
                st.error("Пожалуйста, укажите корректный номер телефона.")
                
    with tab_register:
        reg_role = st.selectbox("Ваш статус на платформе:", ["client", "worker"], format_func=lambda x: "💼 Заказчик (Публикую задания)" if x == "client" else "🧑‍💻 Исполнитель (Выполняю задания)")
        reg_name = st.text_input("Имя и Фамилия:")
        reg_phone = st.text_input("Номер мобильного (например, +37377799999):")
        reg_about = st.text_area("Пара слов о себе:")
        
        if st.button("Зарегистрироваться по SMS", use_container_width=True):
            cl_phone = reg_phone.strip().replace(" ", "")
            if not reg_name.strip() or not cl_phone:
                st.error("Имя и номер телефона обязательны для заполнения.")
            elif get_user_by_phone(cl_phone) is not None:
                st.error("Этот номер телефона уже занят другим аккаунтом!")
            else:
                # Сохраняем временные данные, ждем подтверждения SMS
                st.session_state["sms_code"] = str(random.randint(1000, 9999))
                st.session_state["pending_phone"] = cl_phone
                st.session_state["pending_user_data"] = {
                    "role": reg_role,
                    "name": reg_name.strip(),
                    "phone": cl_phone,
                    "about": reg_about.strip(),
                    "balance": 500.0 if reg_role == "client" else 0.0  # Бонус заказчикам
                }
                st.toast(f"💬 SMS на {cl_phone}: Код подтверждения регистрации {st.session_state['sms_code']}", icon="💬")
                time.sleep(0.5)
                st.rerun()
    st.stop()

# --- ОСНОВНОЙ ЖИЗНЕННЫЙ ЦИКЛ ПРИЛОЖЕНИЯ ---
user_data = get_user_by_id(st.session_state["logged_in_user_id"])

if not user_data:
    st.session_state["logged_in_user_id"] = None
    st.rerun()

st.title("🇲🇩 Платформа микрозадач TaskEarn")
st.write(f"Добро пожаловать, **{user_data['name']}**")
st.write("---")

# Боковая панель (Сайдбар)
st.sidebar.header("👤 Личный Кабинет")
st.sidebar.write(f"🆔 **Ваш ID:** `{user_data['id']}`")
st.sidebar.write(f"📞 **Телефон:** `{user_data['phone']}`")

if user_data['role'] != 'admin':
    st.sidebar.metric(label="Баланс счета", value=f"{user_data['balance']} MDL")
    st.sidebar.write(f"⭐ Текущий рейтинг: `{user_data['rating']} / 5.0`")
    if user_data['role'] == 'client':
        if st.sidebar.button("👛 Пополнить баланс (+500 MDL)"):
            update_balance(user_data['id'], 500.0)
            st.rerun()
else:
    st.sidebar.metric(label="Оборот сервиса (Комиссия)", value=f"{user_data['balance']} MDL")

if st.sidebar.button("🚪 Выйти из системы", use_container_width=True):
    st.session_state["logged_in_user_id"] = None
    st.rerun()

# --- ЛОГИКА ЗАКАЗЧИКА ---
if user_data['role'] == 'client':
    tab_tasks, tab_review, tab_profile = st.tabs(["📋 Мои Задания", "🔍 Контроль выполнения", "👤 Настройки"])
    
    with tab_tasks:
        st.header("Разместить новый заказ")
        with st.form("new_task_form", clear_on_submit=True):
            task_title = st.text_input("Что нужно сделать (Краткое описание):")
            task_city = st.selectbox("Регион/Город:", CITIES[1:])
            task_village = st.text_input("Укажите село/улицу (если нужно):")
            task_category = st.selectbox("Категория работы:", CATEGORIES[1:])
            task_reward = st.number_input("Бюджет задания (MDL)", min_value=20, value=150, step=10)
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
                        with st.popover("❌ Отклонить отчет", use_container_width=True):
                            with st.form(key=f"dis_form_{task['id']}"):
                                reason_text = st.text_area("Опишите, что именно не сделано:")
                                if st.form_submit_button("🚨 Отправить отказ"):
                                    if len(reason_text.strip()) >= 5:
                                        client_dispute_task(task["id"], reason_text.strip())
                                        st.rerun()

    with tab_profile:
        st.header("👤 Данные аккаунта")
        with st.form("c_prof"):
            new_name = st.text_input("Отображаемое Имя:", value=user_data['name'])
            p = st.text_input("Телефон связи:", value=user_data['phone'], disabled=True)
            st.caption("Номер телефона является логином, его нельзя изменить самостоятельно.")
            a = st.text_area("Дополнительно о вас:", value=user_data['about'])
            if st.form_submit_button("Обновить"):
                update_profile(user_data['id'], new_name, p, a)
                st.rerun()

# --- ЛОГИКА ИСПОЛНИТЕЛЯ ---
elif user_data['role'] == 'worker':
    tab_tasks, tab_withdraw, tab_profile = st.tabs(["📋 Доступная Работа", "💸 Вывод баланса", "👤 Профиль"])
    
    with tab_tasks:
        st.header("Лента актуальных заданий Молдавии")
        df_tasks = get_tasks_with_names()
        if not df_tasks.empty:
            my_current_tasks = df_tasks[
                (df_tasks["status"] == "Доступно") | 
                ((df_tasks["worker_id"] == user_data['id']) & (df_tasks["status"].isin(["В работе", "На проверке", "Оспорено", "Арбитраж"])))
            ]
            if my_current_tasks.empty:
                st.info("Лента пуста. Как только появятся новые заказы, они отобразятся здесь.")
            else:
                for task in my_current_tasks.to_dict(orient="records"):
                    clean_reward = task['reward'] * (1 - COMMISSION_RATE)
                    with st.container():
                        col1, col2 = st.columns([3, 2])
                        with col1:
                            st.write(f"**{task['title']}**")
                            st.write(f"💰 Оплата (чистая): **{clean_reward} MDL**")
                            st.caption(f"📍 Локация: {task['city']}, {task['village']}")
                            if task['status'] == "Оспорено":
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
                                with st.popover("📤 Сдать готовую работу", use_container_width=True):
                                    with st.form(key=f"ev_f_{task['id']}"):
                                        ev_text = st.text_area("Опишите результаты (ссылки/текст):")
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
                                with st.popover("⚖️ Передать спор админу", use_container_width=True):
                                    with st.form(key=f"ap_f_{task['id']}"):
                                        appeal_text = st.text_area("Напишите ваши аргументы:")
                                        if st.form_submit_button("🚨 Начать арбитраж"):
                                            if len(appeal_text.strip()) >= 5:
                                                worker_send_to_arbitration(task['id'], appeal_text.strip())
                                                st.rerun()
                        st.write("---")

    with tab_withdraw:
        st.header("💸 Заявка на выплату")
        st.write(f"Доступные средства: **{user_data['balance']} MDL**")
        with st.form("withdraw_form"):
            withdraw_amount = st.number_input("Какую сумму вывести:", min_value=50, value=50, step=10)
            card_number = st.text_input("Номер банковской карты MD (16 цифр):")
            if st.form_submit_button("Подтвердить выплату"):
                if user_data['balance'] >= withdraw_amount and len(card_number.strip()) >= 16:
                    update_balance(user_data['id'], -withdraw_amount)
                    st.success("Выплата успешно отправлена в обработку банк-партнер!")
                    st.rerun()

    with tab_profile:
        st.header("👤 Настройки исполнителя")
        with st.form("w_prof"):
            new_name = st.text_input("Ваше Имя / Никнейм:", value=user_data['name'])
            p = st.text_input("Телефон:", value=user_data['phone'], disabled=True)
            a = st.text_area("Навыки, инструменты, опыт работы:", value=user_data['about'])
            if st.form_submit_button("Сохранить"):
                update_profile(user_data['id'], new_name, p, a)
                st.rerun()

# --- ПАНЕЛЬ АДМИНИСТРАТОРА (АРБИТРАЖ) ---
elif user_data['role'] == 'admin':
    st.header("👑 Судейство и Арбитраж Системы")
    df_tasks = get_tasks_with_names()
    if not df_tasks.empty:
        arbitration_tasks = df_tasks[df_tasks["status"] == "Арбитраж"].to_dict(orient="records")
        if not arbitration_tasks:
            st.info("Нет открытых споров между пользователями.")
        else:
            for task in arbitration_tasks:
                with st.expander(f"⚖️ Разбор спора: {task['title']}"):
                    st.write(f"**Заказчик (ID: {task['client_id']}):** {task['client_name']}")
                    st.write(f"**Исполнитель (ID: {task['worker_id']}):** {task['worker_name']}")
                    st.write(f"📋 **Что прислал воркер:** {task['worker_evidence']}")
                    st.write(f"❌ **Причина претензии клиента:** {task['cancel_reason']}")
                    st.write(f"🚨 **Апелляция воркера:** {task['appeal_text']}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Победа Исполнителя (Выплатить) ✅", key=f"win_w_{task['id']}", use_container_width=True):
                            approve_task(task['id'], task['reward'], task['worker_id'])
                            st.rerun()
                    with col2:
                        if st.button("Победа Заказчика (Вернуть) ❌", key=f"win_c_{task['id']}", use_container_width=True):
                            conn = sqlite3.connect("taskearn_v20.db")
                            cursor = conn.cursor()
                            cursor.execute("UPDATE tasks SET status='Отменено' WHERE id=?", (task['id'],))
                            cursor.execute("UPDATE users SET balance = balance + ? WHERE id=?", (task['reward'], task['client_id']))
                            conn.commit()
                            conn.close()
                            st.rerun()
