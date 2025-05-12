import streamlit as st
import pandas as pd
import os
import hashlib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
USERS_FILE = os.path.join(DATA_DIR, "users.csv")
PREFS_FILE = os.path.join(DATA_DIR, "preferences.csv")
APARTMENTS_FILE = os.path.join(DATA_DIR, "krisha_cleaned.csv")
BUSINESS_FILE = os.path.join(DATA_DIR, "business_data_updated.csv")
HOUSES_FILE = os.path.join(DATA_DIR, "doma_data_updated.csv")

# ====== ХЭШИРОВАНИЕ И ПОЛЬЗОВАТЕЛИ ======
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_users():
    if os.path.exists(USERS_FILE):
        return pd.read_csv(USERS_FILE)
    else:
        return pd.DataFrame(columns=["UserID", "Login", "PasswordHash"])

def save_user(login, password):
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    users = load_users()
    if login in users["Login"].values:
        return False
    new_id = users["UserID"].max() + 1 if not users.empty else 1
    new_user = {"UserID": new_id, "Login": login, "PasswordHash": hash_password(password)}
    users = pd.concat([users, pd.DataFrame([new_user])], ignore_index=True)
    users.to_csv(USERS_FILE, index=False)
    return True

def authenticate(login, password):
    users = load_users()
    user_row = users[(users["Login"] == login) & (users["PasswordHash"] == hash_password(password))]
    return user_row.iloc[0]["UserID"] if not user_row.empty else None

# ====== ПРЕДПОЧТЕНИЯ ======
def load_preferences():
    if os.path.exists(PREFS_FILE):
        return pd.read_csv(PREFS_FILE)
    return pd.DataFrame(columns=["UserID", "Income", "PreferredFloor", "Rooms", "District", "MinArea", "MaxArea"])

def save_preferences(user_id, prefs_dict):
    prefs_df = load_preferences()
    prefs_df = prefs_df[prefs_df["UserID"] != user_id]
    prefs_dict["UserID"] = user_id
    prefs_df = pd.concat([prefs_df, pd.DataFrame([prefs_dict])], ignore_index=True)
    prefs_df.to_csv(PREFS_FILE, index=False)

def get_user_preferences(user_id):
    prefs_df = load_preferences()
    row = prefs_df[prefs_df["UserID"] == user_id]
    return row.iloc[0] if not row.empty else None

# ====== СТРАНИЦА ВХОДА ======
def login_page():
    st.markdown("<h2 style='text-align: center;'>🔐 Вход или регистрация</h2>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["Вход", "Регистрация"])

    with tab1:
        login = st.text_input("Логин")
        password = st.text_input("Пароль", type="password")
        if st.button("Войти"):
            user_id = authenticate(login, password)
            if user_id:
                st.session_state.logged_in = True
                st.session_state.user_id = user_id
                st.success("Добро пожаловать!")
            else:
                st.error("Неверный логин или пароль.")

    with tab2:
        new_login = st.text_input("Новый логин")
        new_password = st.text_input("Новый пароль", type="password")
        if st.button("Зарегистрироваться"):
            if save_user(new_login, new_password):
                st.success("Успешно! Войдите в систему.")
            else:
                st.warning("Такой логин уже существует.")

# ====== ПОИСК ПО ПРЕДПОЧТЕНИЯМ ======
def filter_properties(df, prefs):
    return df[
        (df["Rooms"] == prefs["Rooms"]) &
        (df["Area"] >= prefs["MinArea"]) &
        (df["Area"] <= prefs["MaxArea"]) &
        (df["Price"] <= prefs["Income"] * 100) &
        (abs(df["Floor"] - prefs["PreferredFloor"]) <= 1)
    ]

# ====== ОСНОВНОЕ ПРИЛОЖЕНИЕ ======
def main_app():
    st.sidebar.header("👤 Навигация")
    st.sidebar.write(f"User ID: {st.session_state.user_id}")
    if st.sidebar.button("🚪 Выйти"):
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.experimental_rerun()

    st.markdown("<h1 style='color: #3B82F6;'>🏘️ Подбор недвижимости по предпочтениям</h1>", unsafe_allow_html=True)

    prefs = get_user_preferences(st.session_state.user_id)
    st.subheader("🔧 Введите свои предпочтения:")

    with st.form("preferences_form"):
        income = st.number_input("Ваш ежемесячный доход (₸)", min_value=0)
        preferred_floor = st.slider("Предпочтительный этаж", 1, 25, 3)
        rooms = st.selectbox("Количество комнат", [1, 2, 3, 4, 5, 6])
        min_area = st.number_input("Минимальная площадь (м²)", min_value=20.0, value=50.0)
        max_area = st.number_input("Максимальная площадь (м²)", min_value=20.0, value=100.0)

        submitted = st.form_submit_button("💾 Сохранить и подобрать")
        if submitted:
            prefs_data = {
                "Income": income,
                "PreferredFloor": preferred_floor,
                "Rooms": rooms,
                "District": "NA",  # для бизнес/домов нет района
                "MinArea": min_area,
                "MaxArea": max_area
            }
            save_preferences(st.session_state.user_id, prefs_data)
            st.success("✅ Предпочтения сохранены!")

    st.subheader("📋 Результаты подбора:")

    tabs = st.tabs(["🏢 Квартиры", "🏬 Коммерция", "🏠 Дома и дачи"])

    if prefs is not None:
        # --- Квартиры ---
        with tabs[0]:
            df = pd.read_csv(APARTMENTS_FILE)
            df_filtered = df[
                (df["Rooms"] == prefs["Rooms"]) &
                (df["District"] == prefs["District"]) &
                (df["Area"] >= prefs["MinArea"]) &
                (df["Area"] <= prefs["MaxArea"]) &
                (df["Price"] <= prefs["Income"] * 100) &
                (abs(df["Floor"] - prefs["PreferredFloor"]) <= 1)
            ]
            if not df_filtered.empty:
                st.dataframe(df_filtered[["Title", "Price", "Area", "Floor", "District", "Street"]], use_container_width=True, hide_index=True)
            else:
                st.warning("❌ Квартир не найдено.")

        # --- Коммерция ---
        with tabs[1]:
            df = pd.read_csv(BUSINESS_FILE)
            df_filtered = filter_properties(df, prefs)
            if not df_filtered.empty:
                st.dataframe(df_filtered[["Title", "Price", "Area", "Floor", "Location"]], use_container_width=True, hide_index=True)
            else:
                st.warning("❌ Коммерческих помещений не найдено.")

        # --- Дома и дачи ---
        with tabs[2]:
            df = pd.read_csv(HOUSES_FILE)
            df_filtered = filter_properties(df, prefs)
            if not df_filtered.empty:
                st.dataframe(df_filtered[["Title", "Price", "Area", "Floor", "Location"]], use_container_width=True, hide_index=True)
            else:
                st.warning("❌ Домов и дач не найдено.")

# ====== ЗАПУСК ======
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = None

if st.session_state.logged_in:
    main_app()
else:
    login_page()
