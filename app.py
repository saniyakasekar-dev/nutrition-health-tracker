import streamlit as st
import sqlite3
import hashlib
import pandas as pd
import os
from datetime import date


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="Nutrition & Health Tracker",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =========================================================
# SETTINGS
# =========================================================

DB_FILE = "health_data.db"
SURVEY_FILE = "data/survey_responses.xlsx"

DEVELOPER_PIN = "1234"
MAX_DEVELOPERS = 2


# =========================================================
# PURPLE THEME
# =========================================================

st.markdown("""
<style>

.stApp {
    background-color: #f8f5ff;
}

.main .block-container {
    max-width: 1400px;
    padding-top: 2rem;
    padding-bottom: 3rem;
}

/* SIDEBAR */

section[data-testid="stSidebar"] {
    background-color: #eee7ff;
    border-right: 1px solid #d8c9ff;
}

section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    color: #5b21b6 !important;
}

/* HEADINGS */

h1 {
    color: #5b21b6 !important;
    font-weight: 700 !important;
}

h2 {
    color: #6d28d9 !important;
}

h3 {
    color: #7c3aed !important;
}

/* TEXT */

p {
    color: #374151;
}

/* BUTTONS */

.stButton > button {
    background-color: #7c3aed !important;
    color: white !important;
    border: 1px solid #7c3aed !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}

.stButton > button p {
    color: white !important;
    font-weight: 600 !important;
}

.stButton > button:hover {
    background-color: #6d28d9 !important;
    border-color: #6d28d9 !important;
}

.stButton > button:hover p {
    color: white !important;
}

/* INPUTS */

.stTextInput input,
.stNumberInput input,
.stTextArea textarea {
    border: 1px solid #c4b5fd !important;
    border-radius: 8px !important;
}

div[data-baseweb="select"] {
    border-radius: 8px !important;
}

/* METRIC CARDS */

div[data-testid="stMetric"] {
    background-color: white;
    border: 1px solid #ddd6fe;
    padding: 18px;
    border-radius: 14px;
    box-shadow: 0 3px 10px rgba(91, 33, 182, 0.08);
}

div[data-testid="stMetricLabel"] {
    color: #6b7280 !important;
}

div[data-testid="stMetricValue"] {
    color: #5b21b6 !important;
    font-weight: 700 !important;
}

/* TABS */

button[data-baseweb="tab"] {
    color: #6d28d9 !important;
    font-weight: 600 !important;
}

/* ALERTS */

div[data-testid="stAlert"] {
    border-radius: 12px;
}

/* EXPANDERS */

div[data-testid="stExpander"] {
    border: 1px solid #ddd6fe;
    border-radius: 12px;
    background-color: white;
}

/* DOWNLOAD BUTTON */

.stDownloadButton > button {
    background-color: #8b5cf6 !important;
    color: white !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}

.stDownloadButton > button p {
    color: white !important;
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_connection():
    return sqlite3.connect(DB_FILE)


# =========================================================
# CREATE / UPDATE DATABASE
# =========================================================

def ensure_database():

    conn = get_connection()
    cur = conn.cursor()

    # USERS TABLE
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            password_hash TEXT,
            name TEXT,
            age INTEGER,
            gender TEXT,
            height REAL,
            weight REAL,
            bmi REAL,
            activity_level TEXT,
            food_preference TEXT,
            health_goal TEXT,
            role TEXT DEFAULT 'User'
        )
    """)

    # Check old columns
    cur.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in cur.fetchall()]

    required_columns = {
        "username": "TEXT",
        "password_hash": "TEXT",
        "name": "TEXT",
        "age": "INTEGER",
        "gender": "TEXT",
        "height": "REAL",
        "weight": "REAL",
        "bmi": "REAL",
        "activity_level": "TEXT",
        "food_preference": "TEXT",
        "health_goal": "TEXT",
        "role": "TEXT DEFAULT 'User'"
    }

    for column, data_type in required_columns.items():

        if column not in columns:

            cur.execute(
                f"ALTER TABLE users ADD COLUMN {column} {data_type}"
            )

    cur.execute("""
        UPDATE users
        SET role = 'User'
        WHERE role IS NULL OR role = ''
    """)

    # DAILY HEALTH TABLE
    cur.execute("""
        CREATE TABLE IF NOT EXISTS daily_health (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            water REAL,
            exercise INTEGER,
            sleep REAL,
            steps INTEGER DEFAULT 0,
            date TEXT
        )
    """)

    cur.execute("PRAGMA table_info(daily_health)")
    health_columns = [row[1] for row in cur.fetchall()]

    if "steps" not in health_columns:

        cur.execute("""
            ALTER TABLE daily_health
            ADD COLUMN steps INTEGER DEFAULT 0
        """)

    # MEALS TABLE
    cur.execute("""
        CREATE TABLE IF NOT EXISTS meals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            meal_type TEXT,
            food_name TEXT,
            quantity TEXT,
            calories INTEGER,
            date TEXT
        )
    """)

    conn.commit()
    conn.close()


ensure_database()


# =========================================================
# PASSWORD HASHING
# =========================================================

def hash_password(password):

    return hashlib.sha256(
        password.encode()
    ).hexdigest()


# =========================================================
# USER FUNCTIONS
# =========================================================

def user_exists(username):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id
        FROM users
        WHERE username = ?
    """, (username,))

    result = cur.fetchone()

    conn.close()

    return result is not None


def create_user(username, password, role):

    conn = get_connection()
    cur = conn.cursor()

    password_hash = hash_password(password)

    cur.execute("""
        INSERT INTO users
        (username, password_hash, role)
        VALUES (?, ?, ?)
    """, (
        username,
        password_hash,
        role
    ))

    user_id = cur.lastrowid

    conn.commit()
    conn.close()

    return user_id


def login_user(username, password):

    conn = get_connection()
    cur = conn.cursor()

    password_hash = hash_password(password)

    cur.execute("""
        SELECT
            id,
            username,
            name,
            age,
            gender,
            height,
            weight,
            bmi,
            activity_level,
            food_preference,
            health_goal,
            role
        FROM users
        WHERE username = ?
        AND password_hash = ?
    """, (
        username,
        password_hash
    ))

    row = cur.fetchone()

    conn.close()

    if row is None:
        return None

    return {
        "id": row[0],
        "username": row[1],
        "name": row[2],
        "age": row[3],
        "gender": row[4],
        "height": row[5],
        "weight": row[6],
        "bmi": row[7],
        "activity_level": row[8],
        "food_preference": row[9],
        "health_goal": row[10],
        "role": row[11] or "User"
    }


def developer_count():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*)
        FROM users
        WHERE role = 'Developer'
    """)

    count = cur.fetchone()[0]

    conn.close()

    return count


# =========================================================
# PROFILE FUNCTIONS
# =========================================================

def get_profile(user_id):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            id,
            username,
            name,
            age,
            gender,
            height,
            weight,
            bmi,
            activity_level,
            food_preference,
            health_goal,
            role
        FROM users
        WHERE id = ?
    """, (user_id,))

    row = cur.fetchone()

    conn.close()

    if row is None:
        return None

    return {
        "id": row[0],
        "username": row[1],
        "name": row[2],
        "age": row[3],
        "gender": row[4],
        "height": row[5],
        "weight": row[6],
        "bmi": row[7],
        "activity_level": row[8],
        "food_preference": row[9],
        "health_goal": row[10],
        "role": row[11] or "User"
    }


def save_profile(
    user_id,
    name,
    age,
    gender,
    height,
    weight,
    bmi,
    activity_level,
    food_preference,
    health_goal
):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE users
        SET
            name = ?,
            age = ?,
            gender = ?,
            height = ?,
            weight = ?,
            bmi = ?,
            activity_level = ?,
            food_preference = ?,
            health_goal = ?
        WHERE id = ?
    """, (
        name,
        age,
        gender,
        height,
        weight,
        bmi,
        activity_level,
        food_preference,
        health_goal,
        user_id
    ))

    conn.commit()
    conn.close()


# =========================================================
# DAILY HEALTH
# =========================================================

def save_daily_health(
    user_id,
    water,
    exercise,
    sleep,
    steps
):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO daily_health
        (
            user_id,
            water,
            exercise,
            sleep,
            steps,
            date
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        water,
        exercise,
        sleep,
        steps,
        str(date.today())
    ))

    conn.commit()
    conn.close()


# =========================================================
# MEALS
# =========================================================

def save_meal(
    user_id,
    meal_type,
    food_name,
    quantity,
    calories
):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO meals
        (
            user_id,
            meal_type,
            food_name,
            quantity,
            calories,
            date
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        meal_type,
        food_name,
        quantity,
        calories,
        str(date.today())
    ))

    conn.commit()
    conn.close()


# =========================================================
# SESSION STATE
# =========================================================

defaults = {
    "logged_in": False,
    "user_id": None,
    "username": "",
    "role": "",
    "bmi": None
}

for key, value in defaults.items():

    if key not in st.session_state:

        st.session_state[key] = value


# =========================================================
# LOGIN / REGISTER
# =========================================================

if not st.session_state.logged_in:

    left, center, right = st.columns([1, 2, 1])

    with center:

        st.markdown(
            "<h1 style='text-align:center;'>🥗 Nutrition & Health</h1>",
            unsafe_allow_html=True
        )

        st.markdown(
            "<p style='text-align:center;'>"
            "Your Personal Health Tracking System"
            "</p>",
            unsafe_allow_html=True
        )

        login_tab, register_tab = st.tabs(
            ["🔐 Login", "📝 Register"]
        )

        # -------------------------------------------------
        # LOGIN
        # -------------------------------------------------

        with login_tab:

            st.subheader("Welcome Back 👋")

            st.write(
                "Sign in to continue to your health dashboard."
            )

            username = st.text_input(
                "Username",
                key="login_username"
            )

            password = st.text_input(
                "Password",
                type="password",
                key="login_password"
            )

            if st.button(
                "➡️ Login",
                use_container_width=True
            ):

                username = username.strip()

                if username == "":
                    st.warning("Please enter your username.")

                elif password == "":
                    st.warning("Please enter your password.")

                else:

                    user = login_user(
                        username,
                        password
                    )

                    if user:

                        st.session_state.logged_in = True
                        st.session_state.user_id = user["id"]
                        st.session_state.username = user["username"]
                        st.session_state.role = user["role"]
                        st.session_state.bmi = user["bmi"]

                        st.rerun()

                    else:

                        st.error(
                            "❌ Incorrect username or password."
                        )

        # -------------------------------------------------
        # REGISTER
        # -------------------------------------------------

        with register_tab:

            st.subheader("Create New Account 📝")

            new_username = st.text_input(
                "Choose Username",
                key="register_username"
            )

            new_password = st.text_input(
                "Create Password",
                type="password",
                key="register_password"
            )

            confirm_password = st.text_input(
                "Confirm Password",
                type="password",
                key="confirm_password"
            )

            account_type = st.selectbox(
                "Account Type",
                ["User", "Developer"],
                key="account_type"
            )

            developer_pin = ""

            if account_type == "Developer":

                st.warning(
                    f"Developer access is restricted. "
                    f"Maximum {MAX_DEVELOPERS} developer accounts."
                )

                developer_pin = st.text_input(
                    "Developer PIN",
                    type="password",
                    key="developer_pin"
                )

            if st.button(
                "🎉 Create Account",
                use_container_width=True
            ):

                username_clean = new_username.strip()

                if username_clean == "":
                    st.warning("Please enter a username.")

                elif new_password == "":
                    st.warning("Please enter a password.")

                elif len(new_password) < 4:
                    st.warning(
                        "Password should contain at least 4 characters."
                    )

                elif new_password != confirm_password:
                    st.error(
                        "❌ Passwords do not match."
                    )

                elif user_exists(username_clean):
                    st.error(
                        "❌ Username already exists."
                    )

                elif (
                    account_type == "Developer"
                    and developer_pin != DEVELOPER_PIN
                ):

                    st.error(
                        "❌ Incorrect Developer PIN."
                    )

                elif (
                    account_type == "Developer"
                    and developer_count() >= MAX_DEVELOPERS
                ):

                    st.error(
                        "❌ Maximum developer accounts already exist."
                    )

                else:

                    create_user(
                        username_clean,
                        new_password,
                        account_type
                    )

                    st.success(
                        f"✅ {account_type} account created successfully!"
                    )

                    st.info(
                        "Now open the Login tab and login."
                    )

    st.stop()


# =========================================================
# LOAD PROFILE
# =========================================================

profile = get_profile(
    st.session_state.user_id
)

if profile is None:

    st.error("Unable to load your account.")

    st.stop()


profile_name = profile["name"] or ""
profile_age = profile["age"] or 18
profile_gender = profile["gender"] or "Female"
profile_height = profile["height"] or 160.0
profile_weight = profile["weight"] or 50.0
profile_bmi = profile["bmi"]
profile_activity = profile["activity_level"] or "Moderate"
profile_food = profile["food_preference"] or "Vegetarian"
profile_goal = profile["health_goal"] or "Maintain Weight"
profile_role = profile["role"] or st.session_state.role or "User"


# =========================================================
# ROLE SECURITY
# =========================================================

if profile_role != st.session_state.role:

    st.session_state.role = profile_role


# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.markdown(
    "## 🥗 Nutrition & Health"
)

st.sidebar.write(
    f"Welcome, **{st.session_state.username}** 👋"
)

st.sidebar.caption(
    f"Account Type: **{st.session_state.role}**"
)

st.sidebar.divider()


# =========================================================
# USER MENU
# =========================================================

if st.session_state.role == "User":

    menu_items = [
        "🏠 Dashboard",
        "👤 Health Profile",
        "🍎 Meal Tracker",
        "💧 Water Tracker",
        "🏃 Activity & Sleep",
        "🤖 AI Diet Recommendation"
    ]

# =========================================================
# DEVELOPER MENU
# =========================================================

else:

    menu_items = [
        "🏠 Developer Dashboard",
        "📊 Survey Insights",
        "👥 Users & Profiles",
        "🍎 Meals & Calories",
        "💧 Water & Activity",
        "😴 Sleep & Steps",
        "🗄️ Database Overview"
    ]


page = st.sidebar.radio(
    "Navigation",
    menu_items
)

st.sidebar.divider()


# =========================================================
# LOGOUT
# =========================================================

if st.sidebar.button(
    "🚪 Logout",
    use_container_width=True
):

    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.username = ""
    st.session_state.role = ""
    st.session_state.bmi = None

    st.rerun()


# =========================================================
# USER DASHBOARD
# =========================================================

if page == "🏠 Dashboard":

    st.title("🏠 My Health Dashboard")

    st.write(
        "Track your health, nutrition and daily habits."
    )

    # Profile status
    if profile_name:

        st.success(
            f"Welcome back, {profile_name}! 👋"
        )

    else:

        st.info(
            "Complete your Health Profile to get personalized recommendations."
        )

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        if profile_bmi:

            st.metric(
                "BMI",
                f"{float(profile_bmi):.1f}"
            )

        else:

            st.metric(
                "BMI",
                "Not Set"
            )

    with col2:

        st.metric(
            "Age",
            profile_age
        )

    with col3:

        st.metric(
            "Food",
            profile_food
        )

    with col4:

        st.metric(
            "Goal",
            profile_goal
        )

    st.divider()

    st.subheader("📌 Quick Health Tips")

    c1, c2, c3 = st.columns(3)

    with c1:

        st.info(
            "💧 Drink enough water throughout the day."
        )

    with c2:

        st.info(
            "🥗 Include fruits and vegetables in your meals."
        )

    with c3:

        st.info(
            "🏃 Stay physically active."
        )


# =========================================================
# HEALTH PROFILE
# =========================================================

elif page == "👤 Health Profile":

    st.header("👤 Health Profile")

    st.write(
        "Enter your details to calculate BMI and personalize recommendations."
    )

    col1, col2 = st.columns(2)

    with col1:

        name = st.text_input(
            "Full Name",
            value=profile_name
        )

        age = st.number_input(
            "Age",
            min_value=1,
            max_value=100,
            value=int(profile_age)
        )

        gender = st.selectbox(
            "Gender",
            ["Female", "Male", "Other"],
            index=(
                ["Female", "Male", "Other"].index(profile_gender)
                if profile_gender in ["Female", "Male", "Other"]
                else 0
            )
        )

        height = st.number_input(
            "Height (cm)",
            min_value=50.0,
            max_value=250.0,
            value=float(profile_height),
            step=0.5
        )

    with col2:

        weight = st.number_input(
            "Weight (kg)",
            min_value=10.0,
            max_value=300.0,
            value=float(profile_weight),
            step=0.5
        )

        activity_level = st.selectbox(
            "Activity Level",
            ["Low", "Light", "Moderate", "High"],
            index=(
                ["Low", "Light", "Moderate", "High"].index(profile_activity)
                if profile_activity in ["Low", "Light", "Moderate", "High"]
                else 2
            )
        )

        food_preference = st.selectbox(
            "Food Preference",
            ["Vegetarian", "Non-Vegetarian", "Vegan"],
            index=(
                ["Vegetarian", "Non-Vegetarian", "Vegan"].index(profile_food)
                if profile_food in [
                    "Vegetarian",
                    "Non-Vegetarian",
                    "Vegan"
                ]
                else 0
            )
        )

        health_goal = st.selectbox(
            "Health Goal",
            [
                "Weight Loss",
                "Maintain Weight",
                "Weight Gain"
            ],
            index=(
                [
                    "Weight Loss",
                    "Maintain Weight",
                    "Weight Gain"
                ].index(profile_goal)
                if profile_goal in [
                    "Weight Loss",
                    "Maintain Weight",
                    "Weight Gain"
                ]
                else 1
            )
        )

    st.divider()

    if st.button(
        "💾 Save Health Profile",
        use_container_width=True
    ):

        bmi = weight / ((height / 100) ** 2)

        save_profile(
            st.session_state.user_id,
            name,
            int(age),
            gender,
            height,
            weight,
            bmi,
            activity_level,
            food_preference,
            health_goal
        )

        st.session_state.bmi = bmi

        st.success(
            f"✅ Health profile saved successfully! BMI = {bmi:.1f}"
        )

        st.rerun()


# =========================================================
# MEAL TRACKER
# =========================================================

elif page == "🍎 Meal Tracker":

    st.header("🍎 Meal Tracker")

    st.write(
        "Record your daily meals and calories."
    )

    meal_type = st.selectbox(
        "Meal Type",
        [
            "Breakfast",
            "Lunch",
            "Snack",
            "Dinner"
        ]
    )

    food_name = st.text_input(
        "Food Name",
        placeholder="Example: Roti, Rice, Dal, Apple"
    )

    quantity = st.text_input(
        "Quantity",
        placeholder="Example: 2 roti"
    )

    calories = st.number_input(
        "Calories",
        min_value=0,
        max_value=5000,
        value=100,
        step=10
    )

    if st.button(
        "➕ Add Meal",
        use_container_width=True
    ):

        if food_name.strip() == "":

            st.warning(
                "Please enter the food name."
            )

        else:

            save_meal(
                st.session_state.user_id,
                meal_type,
                food_name,
                quantity,
                int(calories)
            )

            st.success(
                "✅ Meal added successfully!"
            )

    st.divider()

    conn = get_connection()

    meals_df = pd.read_sql_query(
        """
        SELECT
            meal_type AS "Meal Type",
            food_name AS "Food",
            quantity AS "Quantity",
            calories AS "Calories",
            date AS "Date"
        FROM meals
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        conn,
        params=(st.session_state.user_id,)
    )

    conn.close()

    if len(meals_df) > 0:

        st.subheader("📋 My Meal History")

        st.dataframe(
            meals_df,
            use_container_width=True,
            hide_index=True
        )

        total_calories = int(
            meals_df["Calories"].sum()
        )

        st.metric(
            "Total Recorded Calories",
            total_calories
        )

    else:

        st.info(
            "No meals recorded yet."
        )


# =========================================================
# WATER TRACKER
# =========================================================

elif page == "💧 Water Tracker":

    st.header("💧 Water Tracker")

    st.write(
        "Track your water intake for today."
    )

    water_amount = st.selectbox(
        "Select Water Amount",
        [
            250,
            500,
            1000
        ],
        format_func=lambda x: f"{x} ml"
    )

    if "water_today" not in st.session_state:

        st.session_state.water_today = 0

    if st.button(
        "💧 Add Water",
        use_container_width=True
    ):

        st.session_state.water_today += water_amount

        st.success(
            f"Added {water_amount} ml of water."
        )

    st.metric(
        "Today's Water Intake",
        f"{st.session_state.water_today} ml"
    )

    progress = min(
        st.session_state.water_today / 2000,
        1.0
    )

    st.progress(progress)

    if st.session_state.water_today >= 2000:

        st.success(
            "🎉 Good! You reached the 2 litre target."
        )

    else:

        remaining = 2000 - st.session_state.water_today

        st.info(
            f"💧 {remaining} ml remaining to reach the 2 litre target."
        )


# =========================================================
# ACTIVITY & SLEEP
# =========================================================

elif page == "🏃 Activity & Sleep":

    st.header("🏃 Activity & Sleep")

    st.write(
        "Record your daily activity, sleep and steps."
    )

    exercise = st.number_input(
        "Exercise Duration (minutes)",
        min_value=0,
        max_value=600,
        value=30,
        step=5
    )

    sleep = st.number_input(
        "Sleep (hours)",
        min_value=0.0,
        max_value=24.0,
        value=7.0,
        step=0.5
    )

    steps = st.number_input(
        "Steps",
        min_value=0,
        max_value=100000,
        value=5000,
        step=500
    )

    if sleep >= 7:

        st.success(
            "😊 Good sleep duration!"
        )

    elif sleep > 0:

        st.warning(
            "😴 Try to improve your sleep duration."
        )

    if steps >= 8000:

        st.success(
            "🚶 Great! Your step count is good."
        )

    elif steps > 0:

        st.info(
            "🚶 Try to gradually increase your daily steps."
        )

    if st.button(
        "💾 Save Today's Activity",
        use_container_width=True
    ):

        save_daily_health(
            st.session_state.user_id,
            0,
            int(exercise),
            sleep,
            int(steps)
        )

        st.success(
            "✅ Today's activity saved!"
        )


# =========================================================
# AI DIET RECOMMENDATION
# =========================================================

elif page == "🤖 AI Diet Recommendation":

    st.header("🤖 AI Diet Recommendation")

    st.write(
        "Your recommendation is based on your BMI, "
        "activity level, food preference and health goal."
    )

    # -----------------------------------------------------
    # CHECK PROFILE
    # -----------------------------------------------------

    if not profile_name or not profile_bmi:

        st.warning(
            "⚠️ Please complete your Health Profile first."
        )

        st.info(
            "Go to 👤 Health Profile and save your details."
        )

    else:

        bmi = float(profile_bmi)

        food_preference = profile_food
        health_goal = profile_goal
        activity_level = profile_activity

        # -------------------------------------------------
        # BMI CATEGORY
        # -------------------------------------------------

        if bmi < 18.5:

            bmi_category = "Underweight"

        elif bmi < 25:

            bmi_category = "Normal"

        elif bmi < 30:

            bmi_category = "Overweight"

        else:

            bmi_category = "High BMI"

        # -------------------------------------------------
        # GOAL RECOMMENDATION
        # -------------------------------------------------

        if health_goal == "Weight Loss":

            goal_message = (
                "Focus on balanced meals, vegetables, "
                "adequate protein and controlled portions."
            )

        elif health_goal == "Weight Gain":

            goal_message = (
                "Focus on nutritious calorie-dense foods, "
                "protein and regular meals."
            )

        else:

            goal_message = (
                "Focus on balanced meals and maintaining "
                "a healthy daily routine."
            )

        # -------------------------------------------------
        # ACTIVITY RECOMMENDATION
        # -------------------------------------------------

        if activity_level == "Low":

            activity_message = (
                "Try to gradually increase your daily physical activity."
            )

        elif activity_level == "Light":

            activity_message = (
                "Maintain light activity and include regular walking."
            )

        elif activity_level == "Moderate":

            activity_message = (
                "Continue regular exercise and maintain your active routine."
            )

        else:

            activity_message = (
                "Maintain your active lifestyle with proper nutrition."
            )

        # -------------------------------------------------
        # FOOD RECOMMENDATION
        # -------------------------------------------------

        if food_preference == "Vegetarian":

            breakfast = (
                "Oats with milk/curd + banana + nuts"
            )

            lunch = (
                "Roti + dal + vegetables + salad + curd"
            )

            snack = (
                "Fruit + roasted chana or nuts"
            )

            dinner = (
                "Roti + paneer/tofu + vegetables"
            )

        elif food_preference == "Vegan":

            breakfast = (
                "Oats with soy milk + banana + nuts"
            )

            lunch = (
                "Brown rice + dal + vegetables + salad"
            )

            snack = (
                "Fruit + roasted chickpeas"
            )

            dinner = (
                "Roti + tofu + mixed vegetables"
            )

        else:

            breakfast = (
                "Oats + eggs + fruit"
            )

            lunch = (
                "Roti/rice + dal + chicken/fish + vegetables"
            )

            snack = (
                "Fruit + boiled egg or nuts"
            )

            dinner = (
                "Roti + grilled chicken/fish + vegetables"
            )

        # -------------------------------------------------
        # PROFILE CARDS
        # -------------------------------------------------

        st.subheader("👤 Your Recommendation Profile")

        col1, col2, col3, col4 = st.columns(4)

        with col1:

            st.metric(
                "BMI",
                f"{bmi:.1f}"
            )

        with col2:

            st.metric(
                "BMI Category",
                bmi_category
            )

        with col3:

            st.metric(
                "Food",
                food_preference
            )

        with col4:

            st.metric(
                "Goal",
                health_goal
            )

        st.divider()

        # -------------------------------------------------
        # RECOMMENDATION
        # -------------------------------------------------

        st.subheader("🎯 Personalized Recommendation")

        st.success(
            f"🎯 {goal_message}"
        )

        st.info(
            f"🏃 {activity_message}"
        )

        # -------------------------------------------------
        # MEAL PLAN
        # -------------------------------------------------

        st.subheader("🍽️ Suggested Daily Meal Plan")

        col1, col2 = st.columns(2)

        with col1:

            st.markdown(
                f"### 🌅 Breakfast\n{breakfast}"
            )

            st.markdown(
                f"### 🍛 Lunch\n{lunch}"
            )

        with col2:

            st.markdown(
                f"### 🍎 Snack\n{snack}"
            )

            st.markdown(
                f"### 🌙 Dinner\n{dinner}"
            )

        st.divider()

        # -------------------------------------------------
        # LIFESTYLE
        # -------------------------------------------------

        st.subheader("💧 Daily Lifestyle Suggestions")

        st.write(
            "💧 Drink water regularly throughout the day."
        )

        st.write(
            "🥗 Include fruits and vegetables regularly."
        )

        st.write(
            "🏃 Maintain regular physical activity."
        )

        st.write(
            "😴 Maintain a consistent sleep schedule."
        )

        st.write(
            "🍽️ Avoid skipping meals."
        )

        st.divider()

        st.subheader("📌 BMI Information")

        if bmi < 18.5:

            st.warning(
                "Your BMI is in the Underweight range."
            )

        elif bmi < 25:

            st.success(
                "Your BMI is in the Normal range."
            )

        elif bmi < 30:

            st.warning(
                "Your BMI is in the Overweight range."
            )

        else:

            st.warning(
                "Your BMI is in a higher range."
            )

        st.caption(
            "⚠️ This is a general educational recommendation, "
            "not a medical diagnosis or treatment."
        )


# =========================================================
# DEVELOPER DASHBOARD
# =========================================================

elif page == "🏠 Developer Dashboard":

    st.header("🛠️ Developer Dashboard")

    st.info(
        "This section is available only to authorized developer accounts."
    )

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*)
        FROM users
        WHERE role = 'Developer'
    """)
    total_developers = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*)
        FROM users
        WHERE name IS NOT NULL
        AND name != ''
    """)
    completed_profiles = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM meals")
    total_meals = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM daily_health")
    total_health_records = cur.fetchone()[0]

    cur.execute("""
        SELECT COALESCE(SUM(water), 0)
        FROM daily_health
    """)
    total_water = cur.fetchone()[0]

    cur.execute("""
        SELECT COALESCE(SUM(exercise), 0)
        FROM daily_health
    """)
    total_exercise = cur.fetchone()[0]

    cur.execute("""
        SELECT COALESCE(SUM(steps), 0)
        FROM daily_health
    """)
    total_steps = cur.fetchone()[0]

    cur.execute("""
        SELECT AVG(sleep)
        FROM daily_health
        WHERE sleep > 0
    """)
    average_sleep = cur.fetchone()[0] or 0

    conn.close()

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        st.metric(
            "Total Users",
            total_users
        )

    with col2:

        st.metric(
            "Developers",
            total_developers
        )

    with col3:

        st.metric(
            "Profiles Completed",
            completed_profiles
        )

    with col4:

        st.metric(
            "Survey Responses",
            (
                len(pd.read_excel(SURVEY_FILE))
                if os.path.exists(SURVEY_FILE)
                else 0
            )
        )

    st.divider()

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        st.metric(
            "Total Meals",
            total_meals
        )

    with col2:

        st.metric(
            "Health Records",
            total_health_records
        )

    with col3:

        st.metric(
            "Total Steps",
            f"{int(total_steps):,}"
        )

    with col4:

        st.metric(
            "Average Sleep",
            f"{average_sleep:.1f} hrs"
        )

    st.divider()

    st.subheader("📌 Project Data Summary")

    st.write(
        f"💧 Total recorded water: **{total_water:.1f} ml**"
    )

    st.write(
        f"🏃 Total exercise minutes: **{int(total_exercise)}**"
    )

    st.write(
        f"👥 Total registered accounts: **{total_users}**"
    )


# =========================================================
# DEVELOPER SURVEY INSIGHTS
# =========================================================

elif page == "📊 Survey Insights":

    st.header("📊 Community Survey Insights")

    if not os.path.exists(SURVEY_FILE):

        st.error(
            "Survey file not found."
        )

        st.info(
            "Make sure survey_responses.xlsx is inside the data folder."
        )

    else:

        df = pd.read_excel(
            SURVEY_FILE
        )

        st.success(
            f"Survey loaded successfully — {len(df)} responses."
        )

        st.metric(
            "Total Survey Responses",
            len(df)
        )

        st.divider()

        # -------------------------------------------------
        # AGE
        # -------------------------------------------------

        age_columns = [
            col for col in df.columns
            if "age" in str(col).lower()
        ]

        if age_columns:

            age_col = age_columns[0]

            st.subheader("👥 Age Group")

            age_counts = df[age_col].value_counts()

            st.bar_chart(age_counts)

        # -------------------------------------------------
        # GENDER
        # -------------------------------------------------

        gender_columns = [
            col for col in df.columns
            if "gender" in str(col).lower()
        ]

        if gender_columns:

            gender_col = gender_columns[0]

            st.subheader("⚧ Gender")

            gender_counts = df[gender_col].value_counts()

            st.bar_chart(gender_counts)

        # -------------------------------------------------
        # HEALTH
        # -------------------------------------------------

        health_columns = [
            col for col in df.columns
            if "overall health" in str(col).lower()
        ]

        if health_columns:

            health_col = health_columns[0]

            st.subheader("❤️ Overall Health")

            health_counts = df[health_col].value_counts()

            st.bar_chart(health_counts)

        # -------------------------------------------------
        # EXERCISE
        # -------------------------------------------------

        exercise_columns = [
            col for col in df.columns
            if "exercise" in str(col).lower()
        ]

        if exercise_columns:

            exercise_col = exercise_columns[0]

            st.subheader("🏃 Exercise")

            exercise_counts = df[exercise_col].value_counts()

            st.bar_chart(exercise_counts)

        # -------------------------------------------------
        # SLEEP
        # -------------------------------------------------

        sleep_columns = [
            col for col in df.columns
            if "sleep" in str(col).lower()
        ]

        if sleep_columns:

            sleep_col = sleep_columns[0]

            st.subheader("😴 Sleep")

            sleep_counts = df[sleep_col].value_counts()

            st.bar_chart(sleep_counts)

        st.divider()

        st.subheader("📋 Survey Data")

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# DEVELOPER USERS
# =========================================================

elif page == "👥 Users & Profiles":

    st.header("👥 Users & Profiles")

    conn = get_connection()

    users_df = pd.read_sql_query(
        """
        SELECT
            id AS "ID",
            username AS "Username",
            name AS "Name",
            age AS "Age",
            gender AS "Gender",
            height AS "Height",
            weight AS "Weight",
            bmi AS "BMI",
            activity_level AS "Activity",
            food_preference AS "Food Preference",
            health_goal AS "Health Goal",
            role AS "Role"
        FROM users
        ORDER BY id DESC
        """,
        conn
    )

    conn.close()

    st.dataframe(
        users_df,
        use_container_width=True,
        hide_index=True
    )


# =========================================================
# DEVELOPER MEALS
# =========================================================

elif page == "🍎 Meals & Calories":

    st.header("🍎 Meals & Calories")

    conn = get_connection()

    meals_df = pd.read_sql_query(
        """
        SELECT
            meals.id AS "ID",
            users.username AS "Username",
            meals.meal_type AS "Meal Type",
            meals.food_name AS "Food",
            meals.quantity AS "Quantity",
            meals.calories AS "Calories",
            meals.date AS "Date"
        FROM meals
        LEFT JOIN users
        ON meals.user_id = users.id
        ORDER BY meals.id DESC
        """,
        conn
    )

    conn.close()

    st.metric(
        "Total Meals",
        len(meals_df)
    )

    if len(meals_df) > 0:

        st.metric(
            "Total Calories",
            int(meals_df["Calories"].sum())
        )

        st.dataframe(
            meals_df,
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info(
            "No meal records available."
        )


# =========================================================
# DEVELOPER WATER & ACTIVITY
# =========================================================

elif page == "💧 Water & Activity":

    st.header("💧 Water & Activity")

    conn = get_connection()

    health_df = pd.read_sql_query(
        """
        SELECT
            daily_health.id AS "ID",
            users.username AS "Username",
            daily_health.water AS "Water (ml)",
            daily_health.exercise AS "Exercise (min)",
            daily_health.date AS "Date"
        FROM daily_health
        LEFT JOIN users
        ON daily_health.user_id = users.id
        ORDER BY daily_health.id DESC
        """,
        conn
    )

    conn.close()

    if len(health_df) > 0:

        col1, col2 = st.columns(2)

        with col1:

            st.metric(
                "Total Water",
                f"{health_df['Water (ml)'].sum():.0f} l"
            )

        with col2:

            st.metric(
                "Total Exercise",
                f"{health_df['Exercise (min)'].sum():.0f} min"
            )

        st.dataframe(
            health_df,
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info(
            "No water/activity records available."
        )


# =========================================================
# DEVELOPER SLEEP & STEPS
# =========================================================

elif page == "😴 Sleep & Steps":

    st.header("😴 Sleep & Steps")

    conn = get_connection()

    sleep_df = pd.read_sql_query(
        """
        SELECT
            daily_health.id AS "ID",
            users.username AS "Username",
            daily_health.sleep AS "Sleep (hours)",
            daily_health.steps AS "Steps",
            daily_health.date AS "Date"
        FROM daily_health
        LEFT JOIN users
        ON daily_health.user_id = users.id
        ORDER BY daily_health.id DESC
        """,
        conn
    )

    conn.close()

    if len(sleep_df) > 0:

        col1, col2 = st.columns(2)

        with col1:

            avg_sleep = sleep_df["Sleep (hours)"].mean()

            st.metric(
                "Average Sleep",
                f"{avg_sleep:.1f} hrs"
            )

        with col2:

            total_steps = sleep_df["Steps"].sum()

            st.metric(
                "Total Steps",
                f"{int(total_steps):,}"
            )

        st.dataframe(
            sleep_df,
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info(
            "No sleep/steps records available."
        )


# =========================================================
# DATABASE OVERVIEW
# =========================================================

elif page == "🗄️ Database Overview":

    st.header("🗄️ Database Overview")

    conn = get_connection()
    cur = conn.cursor()

    tables = [
        "users",
        "daily_health",
        "meals"
    ]

    for table in tables:

        cur.execute(
            f"SELECT COUNT(*) FROM {table}"
        )

        count = cur.fetchone()[0]

        st.write(
            f"**{table}** → {count} records"
        )

    st.divider()

    cur.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
    """)

    table_names = [
        row[0]
        for row in cur.fetchall()
    ]

    conn.close()

    st.subheader("📋 Database Tables")

    for table_name in table_names:

        st.write(
            f"🗂️ {table_name}"
        )


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "🥗 Nutrition & Health Tracking App • 2026"
)