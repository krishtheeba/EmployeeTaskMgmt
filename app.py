import streamlit as st
import pandas as pd
from datetime import datetime, time
from database import *
from datetime import timezone, timedelta
from streamlit_autorefresh import st_autorefresh
import time as tm
import requests
import json
from google import genai
import streamlit.components.v1 as components
API_KEY = st.secrets["my_api_key"]

IST = timezone(timedelta(hours=5, minutes=30))

# =====================================================
# INIT
# =====================================================
create_tables()
initialize_default_data()

st.set_page_config(page_title="CTPL Employee Checklist System", layout="wide",initial_sidebar_state="expanded")


#=====================================================
#CUSTOM CS
#===========================================
# Compact spreadsheet CSS
st.markdown("""
        <style>
       

/* Remove top space */
.block-container {
    padding-top: 0.4rem !important;
    padding-bottom: 0rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
    max-width: 100% !important;
}

/* This is the actual culprit — Streamlit injects this div with large top margin */
[data-testid="stAppViewContainer"] > section > div:first-child {
    padding-top: 0rem !important;
}

/* Also target the decorator/toolbar area Streamlit adds at top */
[data-testid="stDecoration"] {
    display: none !important;
}

[data-testid="stHeader"] {
    display: none !important;
}

/* Remove top margin from first element */
.main > div:first-child {
    margin-top: 0 !important;
    padding-top: 0 !important;
}

        /* Kill ALL Streamlit column gaps */
        [data-testid="stHorizontalBlock"] {
            gap: 0px !important;
            padding: 0px !important;
            margin: 0px !important;
            align-items: center !important;
        }
        [data-testid="stHorizontalBlock"] > div {
            padding: 0px 4px !important;
            margin: 0px !important;
        }
        /* Kill vertical gaps between rows */
        [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockWithBorder"],
        [data-testid="stVerticalBlock"] > div.element-container {
        margin: 0px !important;
        padding: 0px !important;
        gap: 0px !important;
        }
        /* Compact done buttons */
        div[data-testid="stButton"] > button {
            height: 24px !important;
            min-height: 24px !important;
            padding: 0px 8px !important;
            font-size: 11px !important;
            line-height: 1 !important;
            margin: 0px !important;
            border-radius: 3px !important;
            background-color: #2ecc71 !important;
            color: white !important;
            border: none !important;
            width: 100% !important;
        }
        /* Row divider */
        hr.row-divider {
            margin: 0px !important;
            border: none !important;
            border-top: 1px solid #e0e0e0 !important;
        }
        </style>
""", unsafe_allow_html=True)
st.markdown("""
<script>
// Force remove top padding injected by Streamlit JS
window.addEventListener('load', function() {
    const container = window.parent.document.querySelector('.block-container');
    if (container) container.style.paddingTop = '0px';
    
    const appView = window.parent.document.querySelector('[data-testid="stAppViewBlockContainer"]');
    if (appView) appView.style.paddingTop = '0.5rem';
});
</script>
""", unsafe_allow_html=True)
      
# =====================================================
# AUTO REFRESH (10 sec)
# =====================================================
st_autorefresh(interval=10000, limit=None, key="refresh")


# =====================================================
# HELPERS
# =====================================================
def format_datetime(value):
    if not value:
        return "-"
    try:
        return pd.to_datetime(value).strftime("%d %b %Y %H:%M:%S")
    except:
        return value


def get_quarter(dt_str):
    if not dt_str:
        return "Not Completed"

    try:
        t = datetime.fromisoformat(dt_str).time()
    except:
        return "Invalid"

    if time(8, 0) <= t < time(11, 0):
        return "Q1 (8AM-11AM)"
    elif time(11, 0) <= t < time(13, 0):
        return "Q2 (11AM-1PM)"
    elif time(14, 0) <= t < time(16, 0):
        return "Q3 (2PM-4PM)"
    elif time(16, 0) <= t < time(18, 0):
        return "Q4 (4PM-6PM)"
    elif (time(18,0) <= t < time(23,59,59)) or (time(0,0) <= t < time(8,0)):
        return "Q5 (Outside Hours)"
    else:
        return "Invalid"


# =====================================================
# STATUS COLORS
# =====================================================
def color_status(status, current_time):
    if status == "Pending" and current_time >= time(18, 0):
        return '<div style="background:red;color:white;padding:5px;border-radius:6px;text-align:center;">🔴 OVERDUE</div>'

    elif status == "Completed":
        return '<div style="background:green;color:white;padding:5px;border-radius:6px;text-align:center;">✔ Completed</div>'

    elif status == "Pending":
        return '<div style="background:orange;color:black;padding:5px;border-radius:6px;text-align:center;">⏳ Pending</div>'

    return status


# =====================================================
# QUARTER COLORS
# =====================================================
def color_quarter(q):
    if q.startswith("Q1"):
        return '<div style="background:#3498db;color:white;padding:5px;border-radius:6px;text-align:center;">Q1 (8AM-11AM)</div>'
    elif q.startswith("Q2"):
        return '<div style="background:#9b59b6;color:white;padding:5px;border-radius:6px;text-align:center;">Q2 (11AM-1PM)</div>'
    elif q.startswith("Q3"):
        return '<div style="background:#f39c12;color:white;padding:5px;border-radius:6px;text-align:center;">Q3 (2PM-4PM)</div>'
    elif q.startswith("Q4"):
        return '<div style="background:#1abc9c;color:white;padding:5px;border-radius:6px;text-align:center;">Q4 (4PM-6PM)</div>'
    elif q.startswith("Q5"):
        return '<div style="background:gray;color:white;padding:5px;border-radius:6px;text-align:center;">Q5 (Outside Hours)</div>'
    else:
        return '<div style="background:gray;color:white;padding:5px;border-radius:6px;text-align:center;">N/A</div>'


# =====================================================
# LOGIN
# =====================================================
st.sidebar.header("Login")

employee_name = st.sidebar.text_input("Employee Name")
password = st.sidebar.text_input("Password", type="password")

if st.sidebar.button("Login"):
    user = login(employee_name, password)

    if user:
        st.session_state["user"] = user
        st.success("Login successful")
    else:
        st.error("Invalid credentials")


# =====================================================
# SESSION
# =====================================================
if "user" in st.session_state:

    user = st.session_state["user"]
    user_id = user[0]
    role = user[4]

    current_time = datetime.now(IST).time()
    overdue_time = time(18, 0)
   
    # =================================================
    # ADMIN DASHBOARD
    # =================================================
    if role == "admin":
        
        # =====================================================
        # EMPLOYEE ENROLLMENT
        # =====================================================
        st.sidebar.markdown("---")
        st.sidebar.subheader("Employee Enrollment")

        new_employee_name = st.sidebar.text_input(
            "New Employee Name"
        )

        new_department = st.sidebar.text_input(
            "Department"
        )

        new_password = st.sidebar.text_input(
            "Create Password",
            type="password"
        )

        if st.sidebar.button("Enroll Employee"):

            if (
                new_employee_name
                and new_department
                and new_password
            ):

                success, message = register_employee(
                    new_employee_name,
                    new_department,
                    new_password
                )

                if success:
                    st.sidebar.success(message)
                else:
                    st.sidebar.error(message)

            else:
                st.sidebar.warning("Please fill all fields")


        # =================================================
        # DATA
        # =================================================
        data = get_all_employee_status()

        df = pd.DataFrame(data, columns=[
            "Employee ID",
            "Employee Name",
            "Department",
            "Task",
            "Status",
            "Created Time",
            "Completed Time"
            ])

        df = df.dropna(subset=["Employee Name"])

        # =================================================
        # RAW COLUMNS (IMPORTANT)
        # =================================================
        df["Status_raw"] = df["Status"]
        df["Quarter_raw"] = df["Completed Time"].apply(get_quarter)

        page = st.sidebar.radio("Navigation", ["Admin Dashboard","Done"])
        if page == "Admin Dashboard":
            st.markdown("##### CTPL Employee Daily Checklist System- Admin Dashboard")
            # Compact spreadsheet CSS
            st.markdown("""
        <style>
        /* Kill ALL Streamlit column gaps */
        [data-testid="stHorizontalBlock"] {
            gap: 0px !important;
            padding: 0px !important;
            margin: 0px !important;
            align-items: center !important;
        }
        [data-testid="stHorizontalBlock"] > div {
            padding: 0px 4px !important;
            margin: 0px !important;
        }
        /* Kill vertical gaps between rows */
        [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockWithBorder"],
        [data-testid="stVerticalBlock"] > div.element-container {
        margin: 0px !important;
        padding: 0px !important;
        gap: 0px !important;
        }
        /* Compact done buttons */
        div[data-testid="stButton"] > button {
            height: 24px !important;
            min-height: 24px !important;
            padding: 0px 8px !important;
            font-size: 11px !important;
            line-height: 1 !important;
            margin: 0px !important;
            border-radius: 3px !important;
            background-color: #2ecc71 !important;
            color: white !important;
            border: none !important;
            width: 100% !important;
        }
        /* Row divider */
        hr.row-divider {
            margin: 0px !important;
            border: none !important;
            border-top: 1px solid #e0e0e0 !important;
        }
        </style>
            """, unsafe_allow_html=True)

            # =================================================
            # REFRESH CONTROLS
            # =================================================
            col1, col2 = st.columns([1, 5])

            with col1:
                if st.button("🔄 Refresh"):
                    st.rerun()

            with col2:
                st.caption("Auto-refresh every 10 seconds enabled")
           

            
            # =================================================
            # OVERDUE LOGIC (RESTORED)
            # =================================================
            overdue_tasks = df[
                (df["Status_raw"] == "Pending") &
                (current_time >= overdue_time)
            ]

            if current_time >= overdue_time:
                if not overdue_tasks.empty:
                    st.error(
                        f"🚨 ALERT: {len(overdue_tasks)} overdue tasks detected after 6 PM!"
                    )
                    st.warning("Pending tasks must be completed immediately.")

            # =================================================
            # SORT OPTIONS
            # =================================================
            sort_option = st.selectbox(
                "Sort Options",
                [
                    "Employee Name (A-Z)",
                    "Pending First",
                
                ]
            )

            if sort_option == "Employee Name (A-Z)":
                df = df.sort_values(by=["Employee Name", "Task"])

            elif sort_option == "Pending First":
                df["sort_key"] = df["Status_raw"].apply(
                    lambda x: 0 if x == "Pending" else 1
                )
                df = df.sort_values(by=["sort_key", "Employee Name"])
                df.drop(columns=["sort_key"], inplace=True)


            # =================================================
            # UI FORMATTING
            # =================================================
            df["Status"] = df["Status_raw"].apply(
                lambda x: color_status(x, current_time)
            )

            df["Quarter"] = df["Quarter_raw"].apply(color_quarter)

            #df["Task"] = df.apply( lambda r: f'<div> {r}</div>', axis=1 )

            df["Created Time"] = df["Created Time"].apply(format_datetime)
            df["Completed Time"] = df["Completed Time"].apply(format_datetime)

            # =================================================
            # TABLE
            # =================================================
            st.subheader("All Tasks")
            COLS = [0.6, 3.5, 1.5, 1.8, 1.8, 1.0]

            header = st.columns(COLS)
            header_labels = ["ID", "EMPLOYEE NAME", "DEPARTMENT", "Task", "Status", "Created TIME", "Completed", "Action"]
            header_style = "background:#f0f2f6; font-weight:700; font-size:12px; padding:4px 4px; border-top:2px solid #666; border-bottom:2px solid #666;"

            for col, label in zip(header, header_labels):
                col.markdown(
                f'<div style="{header_style}">{label}</div>',
                unsafe_allow_html=True
                )

            # ── DATA ROWS ────────────────────────────────────────────────
            cell_style = "font-size:12px; padding:3px 4px; border-bottom:1px solid #e8e8e8; line-height:1.4;"


            # =================================================
            # DISPLAY DATAFRAME (HIDE RAW COLUMNS ONLY IN UI)
            # =================================================
            #df.drop(df[df["Status_raw"]=="Completed"].index,inplace=True)
            display_df = df[df["Status_raw"] != "Completed"].copy()
            display_df = display_df[
                [
                    col for col in display_df.columns
                    if col not in ["Status_raw", "Quarter_raw", "Completed Time", "Quarter"]
                ]
            ]
            #display_df=display_df.iloc[1:]
            cellData = st.columns(COLS)
            for _, row in display_df.iterrows():
                for col,label in zip(cellData, row):
                    col.markdown(
                    f'<div style="{cell_style}">{label}</div>',
                    unsafe_allow_html=True
                    )
            
           
        elif page == "Done":

            st.markdown("## 📊 Task Completion Quarter-wise Breakdown")
            # =================================================
            # REFRESH CONTROLS
            # =================================================
            col1, col2 = st.columns([1, 5])

            with col1:
                if st.button("🔄 Refresh"):
                    st.rerun()

            with col2:
                st.caption("Auto-refresh every 10 seconds enabled")
                        

            # =================================================
            # QUARTER BREAKDOWN
            # =================================================

            quarters = [
                "Q1 (8AM-11AM)",
                "Q2 (11AM-1PM)",
                "Q3 (2PM-4PM)",
                "Q4 (4PM-6PM)",
                "Q5 (Outside Hours)"
            ]
            df["Created Time"] = df["Created Time"].apply(format_datetime)
            df["Completed Time"] = df["Completed Time"].apply(format_datetime)

            for q in quarters:

                st.markdown(color_quarter(q), unsafe_allow_html=True)

                subset = df[df["Quarter_raw"].str.contains(q.split()[0])][
                    ["Employee Name", "Task", "Created Time","Completed Time"]
                    ]

                if subset.empty:
                    st.write("No tasks")
                else:
                    st.write(
                        subset.to_html(
                            escape=False,
                            index=False
                        ),
                        unsafe_allow_html=True
                    )

    # =================================================
    # EMPLOYEE DASHBOARD
    # =================================================
    else:
        st.session_state.last_action_time = tm.time()
        st.sidebar.markdown("---")
        st.sidebar.markdown("### Add a Task")
        st.markdown("##### CTPL Employee Daily Checklist System- Employee Dashboard")
        # =================================================
        # REFRESH CONTROLS
        # =================================================
        col1, col2 = st.columns([1, 5])

        with col1:
            if st.button("🔄 Refresh"):
                st.rerun()

        with col2:
            st.caption("Auto-refresh every 10 seconds enabled")


        
        # =====================================================
        # TASK INPUT + AI DURATION ESTIMATOR + ALARM
        # =====================================================

        if "task_timers" not in st.session_state:
            st.session_state.task_timers = {}  # {task_id: {"duration_min": X, "start_time": T, "alarmed": False}}

        task_input = st.sidebar.text_input("Enter task description")
        button_pressed=st.sidebar.button("➕ Add Task & Estimate Duration")
        # ── AI DURATION ESTIMATOR ──────────────────────────
        if task_input:
            if button_pressed:
        
              


                client = genai.Client(api_key=API_KEY)

                
                prompt = f"""You are a task duration estimator for office/workplace tasks.
        Given this task description, estimate the time required to complete it.
        Respond ONLY in this exact JSON format, nothing else:
        {{"estimated_minutes": <number>, "reasoning": "<one line explanation>"}}

        Task: {task_input}"""

                try:
                    response = client.models.generate_content(model= "gemini-3.5-flash",contents= prompt)
                    raw_text = response.text.strip()
                    
                    # Strip markdown fences if present
                    clean = raw_text.replace("```json", "").replace("```", "").strip()
                    estimate = json.loads(clean)
                    estimated_minutes = estimate["estimated_minutes"]
                    reasoning = estimate["reasoning"]

                except Exception as e:
                    
                    estimated_minutes = 30  # fallback
                    reasoning = "Could not estimate, defaulting to 30 minutes"

                # 2. Add task to DB
                checklist_id = get_or_create_checklist(user_id)
                task_id = add_task(checklist_id, task_input)  # make sure add_task returns task_id

                # 3. Store timer in session state
                st.session_state.task_timers[str(task_id)] = {
                    "duration_min": estimated_minutes,
                    "start_time": tm.time(),
                    "task_desc": task_input,
                    "reasoning": reasoning,
                    "alarmed": False
                }

                st.success(f"✅ Task added! Estimated duration: **{estimated_minutes} minutes** — {reasoning}")
                st.rerun()


        # ── ALARM CHECKER + DISPLAY ────────────────────────
        st.subheader("⏱ Active Task Timers")

        if st.session_state.task_timers:

            alarm_triggers = []  # collect tasks that need alarm

            for tid, tdata in st.session_state.task_timers.items():
                elapsed_sec  = tm.time() - tdata["start_time"]
                total_sec    = tdata["duration_min"] * 60
                remaining    = total_sec - elapsed_sec
                progress     = min(elapsed_sec / total_sec, 1.0)

                if remaining > 0:
                    mins = int(remaining // 60)
                    secs = int(remaining % 60)
                    time_label = f"⏳ {mins}m {secs}s remaining"
                    bar_color  = "#2ecc71" if progress < 0.7 else "#e67e22" if progress < 0.9 else "#e74c3c"
                else:
                    time_label = "🔔 TIME UP!"
                    bar_color  = "#e74c3c"
                    if not tdata["alarmed"]:
                        alarm_triggers.append(tid)
                        st.session_state.task_timers[tid]["alarmed"] = True

                st.markdown(f"""
                <div style="border:1px solid #ddd; border-radius:6px; padding:8px; margin-bottom:6px; font-size:13px;">
                    <b>Task {tid}:</b> {tdata['task_desc']}<br>
                    <span style="color:#888; font-size:11px;">Est: {tdata['duration_min']} min — {tdata['reasoning']}</span><br>
                    <div style="background:#eee; border-radius:4px; height:8px; margin:4px 0;">
                        <div style="background:{bar_color}; width:{progress*100:.1f}%; height:8px; border-radius:4px;"></div>
                    </div>
                    <span style="color:{bar_color}; font-weight:bold;">{time_label}</span>
                </div>
                """, unsafe_allow_html=True)

            # ── BROWSER ALARM (plays when time elapses) ──
            if alarm_triggers:
                alarm_js = """
                <script>
                function playAlarm() {
                    const ctx = new (window.AudioContext || window.webkitAudioContext)();
            
                    function beep(freq, start, duration) {
                        const osc = ctx.createOscillator();
                        const gain = ctx.createGain();
                        osc.connect(gain);
                        gain.connect(ctx.destination);
                        osc.frequency.value = freq;
                        osc.type = 'sine';
                        gain.gain.setValueAtTime(0.3, ctx.currentTime + start);
                        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + start + duration);
                        osc.start(ctx.currentTime + start);
                        osc.stop(ctx.currentTime + start + duration);
                    }

                    // Play 3 beeps
                    beep(880, 0.0, 0.3);  
                    beep(880, 0.4, 0.7);
                    beep(1100, 0.8, 0.3);
  
                    beep(880, 1.1, 0.3);
                    beep(1100, 1.4, 0.5);
                    beep(1100, 2.0, 0.5);
                }

                // Auto-trigger
                playAlarm();

                // Show browser notification if permitted
                if (Notification.permission === "granted") {
                    new Notification("⏰ Task Time Up!", {
                        body: "Your estimated task duration has elapsed!",
                        icon: ""
                    });
                } else if (Notification.permission !== "denied") {
                    Notification.requestPermission().then(p => {
                        if (p === "granted") {
                            new Notification("⏰ Task Time Up!", {
                                body: "Your estimated task duration has elapsed!"
                            });
                        }
                    });
                }
                </script>
                """
                components.html(alarm_js, height=0)
                st.error("🔔 ALARM! One or more tasks have exceeded their estimated duration!")

        else:
            st.caption("No active timers. Add a task to start tracking.")

                tasks = get_tasks(user_id)
        task_df = pd.DataFrame(tasks, columns=["ID","Task Description","Status","Created","Completed"])
        original_df = task_df.copy()
        edited_df = st.data_editor(
            task_df,
            hide_index=True,
            use_container_width=True,
            disabled=["ID","Status","Created","Completed"],
            key="task_editor"
        )
        for _, r in edited_df.iterrows():
            old = original_df.loc[original_df["ID"]==r["ID"],"Task Description"].iloc[0]
            if old != r["Task Description"]:
                try:
                    update_task_description(int(r["ID"]), r["Task Description"])
                except Exception:
                    pass
        tasks = get_tasks(user_id)
        st.subheader("Today's Tasks")
        # Compact spreadsheet CSS
        st.markdown("""
        <style>
        /* Kill ALL Streamlit column gaps */
        [data-testid="stHorizontalBlock"] {
            gap: 0px !important;
            padding: 0px !important;
            margin: 0px !important;
            align-items: center !important;
        }
        [data-testid="stHorizontalBlock"] > div {
            padding: 0px 4px !important;
            margin: 0px !important;
        }
        /* Kill vertical gaps between rows */
        [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockWithBorder"],
        [data-testid="stVerticalBlock"] > div.element-container {
        margin: 0px !important;
        padding: 0px !important;
        gap: 0px !important;
        }
        /* Compact done buttons */
        div[data-testid="stButton"] > button {
            height: 24px !important;
            min-height: 24px !important;
            padding: 0px 8px !important;
            font-size: 11px !important;
            line-height: 1 !important;
            margin: 0px !important;
            border-radius: 3px !important;
            background-color: #2ecc71 !important;
            color: white !important;
            border: none !important;
            width: 100% !important;
        }
        /* Row divider */
        hr.row-divider {
            margin: 0px !important;
            border: none !important;
            border-top: 1px solid #e0e0e0 !important;
        }
        </style>
        """, unsafe_allow_html=True)

        # ── HEADER ROW ──────────────────────────────────────────────
        COLS = [0.6, 3.5, 1.5, 1.8, 1.8, 1.0]
		edited_df = st.data_editor(
    	df,
    	use_container_width=True,
    	num_rows="dynamic"
		)

        header = st.columns(COLS)
        header_labels = ["ID", "Task Description", "Status", "Created", "Completed", "Action"]
        header_style = "background:#f0f2f6; font-weight:700; font-size:12px; padding:4px 4px; border-top:2px solid #666; border-bottom:2px solid #666;"

        for col, label in zip(header, header_labels):
            col.markdown(
                f'<div style="{header_style}">{label}</div>',
                unsafe_allow_html=True
            )

        # ── DATA ROWS ────────────────────────────────────────────────
        cell_style = "font-size:12px; padding:3px 4px; border-bottom:1px solid #e8e8e8; line-height:1.4;"

        for task_id, task_desc, status, created, completed in tasks:

            row = st.columns(COLS)
    
            row[0].markdown(f'<div style="{cell_style} color:#888;">{task_id}</div>', unsafe_allow_html=True)
            row[1].markdown(f'<div style="{cell_style}">{task_desc}</div>', unsafe_allow_html=True)
            row[2].markdown(color_status(status, current_time), unsafe_allow_html=True)
            row[3].markdown(f'<div style="{cell_style} color:#555;">{format_datetime(created)}</div>', unsafe_allow_html=True)
            row[4].markdown(f'<div style="{cell_style} color:#555;">{format_datetime(completed)}</div>', unsafe_allow_html=True)

            with row[5]:
                if status == "Pending":
                    if st.button("✔ Done", key=f"done_{task_id}"):
                        if (tm.time() - st.session_state.get("last_action_time", 0)) < 5:
                            st.warning("⏳ Wait 5s")
                            tm.sleep(5)
                        complete_task(task_id)
                        st.session_state.last_action_time = tm.time()
                        st.rerun()
                else:
                    st.markdown(
                    '<div style="font-size:11px;color:#27ae60;text-align:center;padding:3px;">✔ Done</div>',
                    unsafe_allow_html=True
                    )
    # =====================================================
    # LOGOUT
    # =====================================================
    st.sidebar.markdown("---")

    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()
