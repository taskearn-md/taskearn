import streamlit as st
import pandas as pd

st.set_page_config(page_title="TaskEarn MDL", page_icon="🇲🇩", layout="centered")

if "tasks" not in st.session_state:
    st.session_state.tasks = [
        {"id": 1, "title": "Купить и привезти продукты (Кишинев)", "reward": 150, "status": "Доступно", "worker": None},
        {"id": 2, "title": "Перевести текст с румынского на русский", "reward": 200, "status": "Доступно", "worker": None},
    ]

if "balance_client" not in st.session_state:
    st.session_state.balance_client = 500.0
if "balance_worker" not in st.session_state:
    st.session_state.balance_worker = 0.0

st.title("🇲🇩 TaskEarn — Заработок на микрозадачах в Молдове")
st.write("---")

role = st.sidebar.radio("Выберите вашу роль:", ["💼 Заказчик", "🧑‍💻 Исполнитель"])

if role == "💼 Заказчик":
    st.sidebar.metric(label="Баланс Заказчика", value=f"{st.session_state.balance_client} MDL")
    st.sidebar.write("---")
    st.sidebar.subheader("💳 Тест оплаты")
    if st.sidebar.button("Пополнить баланс на +500 MDL"):
        st.session_state.balance_client += 500.0
        st.sidebar.success("Карта имитирована: +500 MDL!")
        st.rerun()
else:
    st.sidebar.metric(label="Баланс Исполнителя", value=f"{st.session_state.balance_worker} MDL")

if role == "💼 Заказчик":
    st.header("Управление заданиями")
    with st.form("new_task_form", clear_on_submit=True):
        st.subheader("➕ Разместить новое задание")
        task_title = st.text_input("Что нужно сделать?")
        task_reward = st.number_input("Оплата исполнителю (MDL)", min_value=20, value=100, step=10)
        submit = st.form_submit_button("Опубликовать и заблокировать оплату")
        
        if submit and task_title:
            if st.session_state.balance_client >= task_reward:
                st.session_state.balance_client -= task_reward
                new_id = len(st.session_state.tasks) + 1
                st.session_state.tasks.append({
                    "id": new_id, "title": task_title, "reward": task_reward, "status": "Доступно", "worker": None
                })
                st.success(f"Задание опубликовано! {task_reward} MDL заморожены.")
                st.rerun()
            else:
                st.error("Недостаточно средств на балансе!")

    st.write("---")
    st.subheader("📋 Ваши задания в системе")
    if st.session_state.tasks:
        df = pd.DataFrame(st.session_state.tasks)
        st.dataframe(df[["id", "title", "reward", "status"]], use_container_width=True)

elif role == "🧑‍💻 Исполнитель":
    st.header("Доступные задания для заработка")
    available_tasks = [t for t in st.session_state.tasks if t["status"] == "Доступно"]
    
    if not available_tasks:
        st.info("На данный момент нет доступных заданий.")
    else:
        for task in available_tasks:
            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"{task['title']}")
                    st.write(f"💰 Награда: {task['reward']} MDL")
                with col2:
                    if st.button(f"Выполнить", key=f"b_{task['id']}", use_container_width=True):
                        task["status"] = "Выполнено"
                        st.session_state.balance_worker += task["reward"]
                        st.success(f"Зачислено {task['reward']} MDL.")
                        st.rerun()
                st.write("---")
