import streamlit as st
import pandas as pd

st.set_page_config(page_title="TaskEarn MDL", page_icon="🇲🇩", layout="centered")

if "tasks" not in st.session_state:
    st.session_state.tasks = [
        {"id": 1, "title": "Купить и привезти продукты (Кишинев)", "reward": 150, "status": "Доступно", "worker": None},
        {"id": 2, "title": "Перевести текст с румынского на русский", "reward": 200, "status": "Доступно", "worker": None},
    ]
if "user_balance" not in st.session_state:
    st.session_state.user_balance = 0.0

st.title("🇲🇩 TaskEarn — Заработок на микрозадачах в Молдове")

role = st.sidebar.radio("Выберите вашу роль:", ["🧑‍💻 Исполнитель", "💼 Заказчик"])
st.sidebar.metric(label="Ваш баланс", value=f"{st.session_state.user_balance} MDL")

if role == "💼 Заказчик":
    st.header("Разместить новое задание")
    with st.form("new_task_form", clear_on_submit=True):
        task_title = st.text_input("Что нужно сделать?")
        task_reward = st.number_input("Оплата (MDL)", min_value=20, value=100)
        submit = st.form_submit_button("Опубликовать")
        if submit and task_title:
            st.session_state.tasks.append({"id": len(st.session_state.tasks) + 1, "title": task_title, "reward": task_reward, "status": "Доступно", "worker": None})
            st.success("Опубликовано в леях!")
    st.dataframe(pd.DataFrame(st.session_state.tasks)[["id", "title", "reward", "status"]])

elif role == "🧑‍💻 Исполнитель":
    st.header("Доступные задания для заработка")
    for task in [t for t in st.session_state.tasks if t["status"] == "Доступно"]:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(f"{task['title']} ({task['reward']} MDL)")
        with col2:
            if st.button(f"Выполнить", key=f"b_{task['id']}"):
                task["status"] = "Выполнено"
                st.session_state.user_balance += task["reward"]
                st.success("Леи зачислены на ваш баланс!")
                st.rerun()