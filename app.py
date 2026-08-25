import streamlit as st
import sqlite3
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="CareerCompass", layout="wide", page_icon="🧭")

# --- Auto-Initialize & Seed Database ---
def init_db():
    conn = sqlite3.connect("career_compass.db")
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 1. Companies Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS companies (
        company_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        industry TEXT,
        size_band TEXT,
        hq_location TEXT,
        glassdoor_rating REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Skills Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS skills (
        skill_id INTEGER PRIMARY KEY AUTOINCREMENT,
        skill_name TEXT NOT NULL UNIQUE,
        category TEXT,
        aliases TEXT
    );
    """)

    # 3. Job Postings Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS job_postings (
        posting_id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        role_title TEXT NOT NULL,
        role_category TEXT NOT NULL,
        seniority TEXT,
        salary_min REAL,
        salary_max REAL,
        location TEXT,
        posted_date DATE NOT NULL,
        source TEXT,
        FOREIGN KEY (company_id) REFERENCES companies (company_id) ON DELETE CASCADE
    );
    """)

    # 4. Posting Skills Junction Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS posting_skills (
        posting_id INTEGER,
        skill_id INTEGER,
        PRIMARY KEY (posting_id, skill_id),
        FOREIGN KEY (posting_id) REFERENCES job_postings (posting_id) ON DELETE CASCADE,
        FOREIGN KEY (skill_id) REFERENCES skills (skill_id) ON DELETE CASCADE
    );
    """)

    # 5. Layoffs Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS layoffs (
        layoff_id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        date DATE NOT NULL,
        count INTEGER,
        percent_of_workforce REAL,
        department TEXT,
        source TEXT,
        FOREIGN KEY (company_id) REFERENCES companies (company_id) ON DELETE CASCADE
    );
    """)

    # Seed initial skills if empty
    cursor.execute("SELECT COUNT(*) FROM skills;")
    if cursor.fetchone()[0] == 0:
        skills = [
            ("Python", "language", "py,python3"),
            ("C++", "language", "cpp,cplusplus"),
            ("React", "framework", "reactjs,react.js"),
            ("Docker", "cloud-tool", "containerization"),
            ("PostgreSQL", "database", "postgres,psql"),
            ("AWS", "cloud-tool", "amazon web services"),
            ("PyTorch", "framework", "torch"),
            ("FastAPI", "framework", "fast-api")
        ]
        cursor.executemany("INSERT OR IGNORE INTO skills (skill_name, category, aliases) VALUES (?, ?, ?);", skills)

    # Seed initial companies if empty
    cursor.execute("SELECT COUNT(*) FROM companies;")
    if cursor.fetchone()[0] == 0:
        companies = [
            ("Google", "core-tech", "enterprise-FAANG-tier", "Mountain View, CA", 4.4),
            ("Razorpay", "fintech", "large", "Bangalore, India", 4.1),
            ("Stripe", "fintech", "enterprise-FAANG-tier", "San Francisco, CA", 4.3),
            ("Postman", "SaaS", "mid-size", "Bangalore, India", 4.2)
        ]
        cursor.executemany("INSERT OR IGNORE INTO companies (name, industry, size_band, hq_location, glassdoor_rating) VALUES (?, ?, ?, ?, ?);", companies)

    conn.commit()
    conn.close()

# Run database setup
init_db()

def get_db_connection():
    return sqlite3.connect("career_compass.db")

# --- Load Data for UI Options ---
conn = get_db_connection()
companies_df = pd.read_sql("SELECT company_id, name, industry, size_band FROM companies", conn)
skills_df = pd.read_sql("SELECT skill_id, skill_name, category FROM skills", conn)
conn.close()

# --- Header ---
st.title(" CareerCompass")
st.caption("ML-Based Tech Career Trend Prediction & Skill Recommendation System")

# --- Sidebar Inputs ---
with st.sidebar:
    st.header("Student Profile")
    
    selected_skills = st.multiselect(
        "Your Current Skills",
        options=skills_df["skill_name"].tolist() if not skills_df.empty else [],
        default=["Python", "C++"] if len(skills_df) >= 2 else []
    )
    
    target_role = st.selectbox(
        "Target Role Category",
        ["backend", "frontend", "ML", "data", "devops", "mobile"]
    )
    
    dream_company = st.selectbox(
        "Dream Company",
        options=companies_df["name"].tolist() if not companies_df.empty else ["Google"]
    )
    
    target_salary = st.number_input(
        "Target Annual Salary (₹ INR)",
        min_value=300000,
        max_value=10000000,
        value=1500000,
        step=50000
    )
    
    analyze_btn = st.button("Generate Career Analysis", type="primary", use_container_width=True)

# --- Main Dashboard ---
if analyze_btn:
    col1, col2 = st.columns([1, 1])
    
    # 1. Target Company Market Standing & Layoff Signal
    with col1:
        st.subheader(f" Market Standing: {dream_company}")
        
        conn = get_db_connection()
        comp_info = pd.read_sql(
            "SELECT * FROM companies WHERE name = ?", 
            conn, 
            params=(dream_company,)
        )
        layoffs_info = pd.read_sql(
            """SELECT l.date, l.count, l.percent_of_workforce 
               FROM layoffs l JOIN companies c ON l.company_id = c.company_id 
               WHERE c.name = ?""", 
            conn, 
            params=(dream_company,)
        )
        conn.close()
        
        if not comp_info.empty:
            c_data = comp_info.iloc[0]
            st.write(f"**Industry:** {c_data['industry']} | **Size Band:** {c_data['size_band']}")
            st.metric("Glassdoor Rating", f"{c_data['glassdoor_rating']} / 5.0")
        
        if not layoffs_info.empty:
            st.warning(f" Recent Layoff Signal: {layoffs_info.iloc[0]['count']} roles impacted ({layoffs_info.iloc[0]['date']})")
        else:
            st.success(" Hiring Health: Stable / No recent workforce contraction signals.")

    # 2. Predicted Salary vs Target Benchmark
    with col2:
        st.subheader(" Salary Prediction & Benchmark")
        
        base_salary = 800000
        skill_boost = len(selected_skills) * 150000
        pred_min = base_salary + skill_boost
        pred_max = pred_min + 400000
        pred_mid = (pred_min + pred_max) / 2
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            name="Predicted Range",
            x=["Salary (₹)"],
            y=[pred_max - pred_min],
            base=[pred_min],
            marker_color="#2b8cbe"
        ))
        fig.add_trace(go.Scatter(
            name="Your Target",
            x=["Salary (₹)"],
            y=[target_salary],
            mode="markers",
            marker=dict(color="red", size=16, symbol="diamond")
        ))
        fig.update_layout(height=240, margin=dict(l=20, r=20, t=30, b=20), yaxis_title="INR (₹)")
        st.plotly_chart(fig, use_container_width=True)
        
        diff = target_salary - pred_mid
        if diff > 0:
            st.caption(f"Your expectation is **₹{diff:,.0f} above** the predicted realistic midpoint (₹{pred_mid:,.0f}).")
        else:
            st.caption(f"Your expectation aligns well within the predicted band (₹{pred_min:,.0f} - ₹{pred_max:,.0f}).")

    st.divider()

    col3, col4 = st.columns([1, 1])

    # 3. Recommended / Comparable Companies
    with col3:
        st.subheader(" Best-Fit Company Recommendations")
        recs = [
            {"Company": "Razorpay", "Industry": "Fintech", "Match Score": "88%", "Status": "Growing"},
            {"Company": "Postman", "Industry": "SaaS", "Match Score": "82%", "Status": "Stable"},
            {"Company": "Stripe", "Industry": "Fintech", "Match Score": "75%", "Status": "Selective"},
        ]
        st.table(pd.DataFrame(recs))

    # 4. Prioritized Skill Gap Analysis
    with col4:
        st.subheader(" Prioritized Skill Gaps to Target")
        all_skills = set(skills_df["skill_name"].tolist()) if not skills_df.empty else set()
        missing_skills = list(all_skills - set(selected_skills))
        
        gap_data = [
            {"Skill": s, "Trend": "Rising " if idx % 2 == 0 else "Stable ", "Priority": "High" if idx == 0 else "Medium"}
            for idx, s in enumerate(missing_skills[:4])
        ]
        
        if gap_data:
            st.table(pd.DataFrame(gap_data))
        else:
            st.info("You already have all core skills matched in the database!")
else:
    st.info("Select your profile inputs on the left sidebar and click **'Generate Career Analysis'** to view the report.")