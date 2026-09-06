import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, timezone, date, time
import time as time_module

# Configure Streamlit Page
st.set_page_config(
    page_title="DevTrack - Task Time Tracker",
    page_icon="⏱️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern polished design
st.markdown("""
<style>
    /* Global Styles */
    .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Active timer card */
    .timer-banner {
        background: linear-gradient(135deg, #1e3a8a 0%, #1e293b 100%);
        border: 2px solid #3b82f6;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 25px;
        color: white;
        box-shadow: 0 10px 25px -5px rgba(59, 130, 246, 0.3);
    }
    
    .timer-clock {
        font-family: 'JetBrains Mono', 'Courier New', monospace;
        font-size: 2.6rem;
        font-weight: 700;
        color: #60a5fa;
        letter-spacing: 2px;
    }
    
    .idle-warning {
        background: linear-gradient(135deg, #78350f 0%, #451a03 100%);
        border: 1px solid #f59e0b;
        color: #fef3c7;
        padding: 12px 16px;
        border-radius: 8px;
        margin-top: 10px;
        font-size: 0.95rem;
    }

    /* Metric card styling */
    div[data-testid="stMetricValue"] {
        font-size: 1.8rem;
        font-weight: 700;
        color: #38bdf8;
    }
    
    .badge-todo { background-color: #64748b; color: white; padding: 3px 8px; border-radius: 4px; font-size: 0.8rem; }
    .badge-inprogress { background-color: #3b82f6; color: white; padding: 3px 8px; border-radius: 4px; font-size: 0.8rem; }
    .badge-done { background-color: #10b981; color: white; padding: 3px 8px; border-radius: 4px; font-size: 0.8rem; }
</style>
""", unsafe_allow_html=True)

# Configuration
API_BASE_URL = st.sidebar.text_input("Backend API URL", value="http://127.0.0.1:8000")

# API Helper Functions
def api_get(endpoint: str, params: dict = None):
    try:
        res = requests.get(f"{API_BASE_URL}{endpoint}", params=params, timeout=5)
        if res.status_code == 200:
            return res.json()
        return None
    except Exception as e:
        return None

def api_post(endpoint: str, json_data: dict = None):
    try:
        res = requests.post(f"{API_BASE_URL}{endpoint}", json=json_data, timeout=5)
        return res
    except Exception as e:
        return None

def api_patch(endpoint: str, json_data: dict):
    try:
        return requests.patch(f"{API_BASE_URL}{endpoint}", json=json_data, timeout=5)
    except Exception:
        return None

def api_delete(endpoint: str):
    try:
        return requests.delete(f"{API_BASE_URL}{endpoint}", timeout=5)
    except Exception:
        return None

# Check backend health
health = api_get("/health")
if not health:
    st.sidebar.error("⚠️ Backend API is offline! Run `uvicorn backend.main:app --port 8000`")
else:
    st.sidebar.success("🟢 Backend Connected")

# Sidebar navigation & actions
st.sidebar.title("⏱️ DevTracker")
nav = st.sidebar.radio(
    "Navigation",
    ["📊 Dashboard & Timer", "📋 Task Management", "✍️ Manual Time Entry", "📈 Analytics & Reports", "📜 Session Audit Log"]
)

# Fetch active timer
active_timer = api_get("/tasks/active/timer")

import streamlit.components.v1 as components

# Top Header / Active Timer Banner (Live Real-Time Ticking Clock)
if active_timer and active_timer.get("active"):
    task_id = active_timer['task_id']
    task_title_escaped = active_timer['task_title'].replace('"', '&quot;').replace("'", "&#39;")
    project_escaped = active_timer['project'].replace('"', '&quot;').replace("'", "&#39;")
    start_time_iso = active_timer['start_time']

    timer_html = f"""
    <div style="
        background: linear-gradient(135deg, #1e3a8a 0%, #0f172a 100%);
        border: 2px solid #3b82f6;
        border-radius: 12px;
        padding: 16px 22px;
        color: #f8fafc;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        box-shadow: 0 10px 25px -5px rgba(59, 130, 246, 0.3);
    ">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px;">
            <div style="display: flex; align-items: center; gap: 14px;">
                <div style="
                    width: 14px;
                    height: 14px;
                    background-color: #ef4444;
                    border-radius: 50%;
                    box-shadow: 0 0 12px #ef4444;
                    animation: pulse 1.5s infinite;
                "></div>
                <div>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="background: #ef4444; color: white; font-weight: 700; font-size: 0.7rem; padding: 2px 7px; border-radius: 4px; letter-spacing: 0.5px;">ACTIVE TIMER</span>
                        <span style="color: #93c5fd; font-size: 0.85rem; font-weight: 500;">📁 {project_escaped}</span>
                    </div>
                    <h2 style="margin: 4px 0 0 0; font-size: 1.35rem; font-weight: 700; color: #ffffff;">{task_title_escaped}</h2>
                </div>
            </div>
            <div style="display: flex; align-items: center; gap: 16px;">
                <div id="live-timer-clock" style="
                    font-family: 'JetBrains Mono', 'Courier New', monospace;
                    font-size: 2.4rem;
                    font-weight: 700;
                    color: #60a5fa;
                    letter-spacing: 2px;
                    text-shadow: 0 0 12px rgba(96, 165, 250, 0.4);
                ">00:00:00</div>
                <button id="live-stop-btn" onclick="stopActiveTimer()" style="
                    background-color: #ef4444;
                    color: white;
                    border: none;
                    padding: 10px 18px;
                    font-size: 0.95rem;
                    font-weight: 700;
                    border-radius: 8px;
                    cursor: pointer;
                    box-shadow: 0 4px 6px -1px rgba(239, 68, 68, 0.3);
                    transition: all 0.2s ease;
                ">⏹️ Stop Timer</button>
            </div>
        </div>
        <div id="idle-warning-box" style="
            display: none;
            background: linear-gradient(135deg, #78350f 0%, #451a03 100%);
            border: 1px solid #f59e0b;
            color: #fef3c7;
            padding: 10px 14px;
            border-radius: 8px;
            margin-top: 12px;
            font-size: 0.88rem;
        ">
            ⚠️ <strong>Idle Alert:</strong> This timer has been running continuously for over 2 hours! Remember to review this session.
        </div>
    </div>

    <style>
    @keyframes pulse {{
        0% {{ transform: scale(0.95); opacity: 0.8; }}
        50% {{ transform: scale(1.15); opacity: 1; }}
        100% {{ transform: scale(0.95); opacity: 0.8; }}
    }}
    #live-stop-btn:hover {{
        background-color: #dc2626 !important;
        transform: translateY(-1px);
    }}
    </style>

    <script>
    (function() {{
        const startTimeStr = "{start_time_iso}";
        const startTimeMs = new Date(startTimeStr).getTime();
        const taskId = {task_id};
        const apiUrl = "{API_BASE_URL}";

        function formatTime(totalSec) {{
            if (totalSec < 0) totalSec = 0;
            const h = Math.floor(totalSec / 3600);
            const m = Math.floor((totalSec % 3600) / 60);
            const s = totalSec % 60;
            return String(h).padStart(2, '0') + ':' + 
                   String(m).padStart(2, '0') + ':' + 
                   String(s).padStart(2, '0');
        }}

        function tick() {{
            const now = Date.now();
            const diffSec = Math.floor((now - startTimeMs) / 1000);
            const clockEl = document.getElementById('live-timer-clock');
            if (clockEl) {{
                clockEl.innerText = formatTime(diffSec);
            }}
            const idleEl = document.getElementById('idle-warning-box');
            if (idleEl) {{
                if (diffSec >= 7200) {{
                    idleEl.style.display = 'block';
                }} else {{
                    idleEl.style.display = 'none';
                }}
            }}
        }}

        tick();
        const intervalId = setInterval(tick, 1000);

        window.stopActiveTimer = function() {{
            const btn = document.getElementById('live-stop-btn');
            if (btn) {{
                btn.innerText = 'Stopping...';
                btn.disabled = true;
            }}
            clearInterval(intervalId);
            fetch(apiUrl + '/tasks/' + taskId + '/stop', {{ method: 'POST' }})
                .then(res => {{
                    try {{
                        window.parent.location.reload();
                    }} catch(e) {{
                        window.location.reload();
                    }}
                }})
                .catch(err => {{
                    alert('Error stopping timer: ' + err);
                    if (btn) {{
                        btn.innerText = '⏹️ Stop Timer';
                        btn.disabled = false;
                    }}
                }});
        }};
    }})();
    </script>
    """
    components.html(timer_html, height=140)

    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        if st.button("⏹️ Stop Timer (Python)", type="primary", use_container_width=True):
            res = api_post(f"/tasks/{active_timer['task_id']}/stop")
            if res and res.status_code == 200:
                st.toast("Timer stopped and session recorded!", icon="✅")
                time_module.sleep(0.5)
                st.rerun()
            else:
                st.error("Failed to stop timer.")
    with col2:
        if st.button("🔄 Sync Timer", use_container_width=True):
            st.rerun()

# ----------------- VIEW 1: DASHBOARD & TIMER -----------------
if nav == "📊 Dashboard & Timer":
    st.title("👨‍💻 Developer Dashboard")
    
    # Load tasks and summary
    tasks = api_get("/tasks") or []
    summary = api_get("/reports/summary", params={"range": "week"}) or {}

    # High-level Metrics Row
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Weekly Tracked Time", summary.get("formatted_time", "0h 0m"))
    m2.metric("Total Tasks", len(tasks))
    m3.metric("Weekly Sessions", summary.get("total_sessions", 0))
    m4.metric("Idle Flags", summary.get("idle_flagged_count", 0))

    st.markdown("---")

    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.subheader("⚡ Quick Task Tracker")
        st.caption("Start or stop tracking time on your active development tasks with a single click.")

        if not tasks:
            st.info("No tasks yet. Create one from the 'Task Management' tab or below!")
        else:
            for task in tasks:
                with st.container():
                    t_col1, t_col2, t_col3 = st.columns([4, 2, 2])
                    with t_col1:
                        if task.get("is_active"):
                            st.markdown(f"**{task['title']}** &nbsp; <span style='background:#ef4444; color:white; padding:2px 6px; border-radius:4px; font-size:0.75rem; font-weight:bold;'>🔴 RUNNING</span>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"**{task['title']}**")
                        st.caption(f"📁 `{task['project']}` | Priority: `{task['priority'].upper()}` | Status: `{task['status']}`")
                    with t_col2:
                        st.markdown(f"⏱️ **{task['total_formatted']}**")
                    with t_col3:
                        if task.get("is_active"):
                            if st.button("⏹️ Stop", key=f"stop_{task['id']}", type="primary", use_container_width=True):
                                api_post(f"/tasks/{task['id']}/stop")
                                st.rerun()
                        else:
                            if st.button("▶️ Start", key=f"start_{task['id']}", use_container_width=True):
                                api_post(f"/tasks/{task['id']}/start")
                                st.rerun()
                    st.divider()

    with col_right:
        st.subheader("📊 Time Distribution by Project (Week)")
        projects_data = summary.get("projects", [])
        if projects_data:
            df_proj = pd.DataFrame(projects_data)
            fig = px.pie(
                df_proj,
                values="total_hours",
                names="project",
                hole=0.45,
                color_discrete_sequence=px.colors.qualitative.Prism
            )
            fig.update_layout(margin=dict(l=20, r=20, t=20, b=20), height=280)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No session data recorded for this week yet.")

        st.subheader("🚀 Quick Create Task")
        with st.form("quick_task_form"):
            q_title = st.text_input("Task Title", placeholder="e.g. Optimize Database Indexes")
            q_proj = st.text_input("Project", placeholder="e.g. Core API")
            q_prio = st.selectbox("Priority", ["low", "medium", "high", "critical"], index=1)
            submitted = st.form_submit_button("Add Task")
            if submitted and q_title and q_proj:
                res = api_post("/tasks", {"title": q_title, "project": q_proj, "priority": q_prio, "status": "todo"})
                if res and res.status_code == 201:
                    st.success("Task created!")
                    time_module.sleep(0.5)
                    st.rerun()

# ----------------- VIEW 2: TASK MANAGEMENT -----------------
elif nav == "📋 Task Management":
    st.title("📋 Task Management")
    st.caption("Organize your development backlog, assign project tags, set priorities, and track progress.")

    tab_list, tab_create = st.tabs(["All Tasks", "+ Create Task"])

    with tab_create:
        with st.form("new_task_form", clear_on_submit=True):
            f_title = st.text_input("Task Title *", placeholder="e.g. Implement OAuth2 Refresh Token Flow")
            f_proj = st.text_input("Project Name / Component *", placeholder="e.g. Auth Service")
            c1, c2 = st.columns(2)
            with c1:
                f_priority = st.selectbox("Priority", ["low", "medium", "high", "critical"], index=1)
            with c2:
                f_status = st.selectbox("Status", ["todo", "in-progress", "done"], index=0)
            
            submit_btn = st.form_submit_button("Create Task", type="primary")
            if submit_btn:
                if not f_title or not f_proj:
                    st.error("Please fill in both Title and Project.")
                else:
                    res = api_post("/tasks", {
                        "title": f_title,
                        "project": f_proj,
                        "priority": f_priority,
                        "status": f_status
                    })
                    if res and res.status_code == 201:
                        st.success("Task created successfully!")
                        time_module.sleep(0.5)
                        st.rerun()

    with tab_list:
        tasks = api_get("/tasks") or []
        if not tasks:
            st.info("No tasks found.")
        else:
            # Filter bar
            f_col1, f_col2, f_col3 = st.columns([2, 1, 1])
            with f_col1:
                search_query = st.text_input("🔍 Search", placeholder="Filter by title or project...")
            with f_col2:
                status_filter = st.selectbox("Filter Status", ["All", "todo", "in-progress", "done"])
            with f_col3:
                priority_filter = st.selectbox("Filter Priority", ["All", "low", "medium", "high", "critical"])

            filtered_tasks = tasks
            if search_query:
                q = search_query.lower()
                filtered_tasks = [t for t in filtered_tasks if q in t["title"].lower() or q in t["project"].lower()]
            if status_filter != "All":
                filtered_tasks = [t for t in filtered_tasks if t["status"] == status_filter]
            if priority_filter != "All":
                filtered_tasks = [t for t in filtered_tasks if t["priority"] == priority_filter]

            st.write(f"Showing **{len(filtered_tasks)}** of **{len(tasks)}** tasks:")

            for t in filtered_tasks:
                with st.expander(f"{'🔴 ACTIVE: ' if t.get('is_active') else ''}{t['title']} ({t['project']}) - {t['total_formatted']}"):
                    ec1, ec2, ec3 = st.columns([2, 2, 2])
                    with ec1:
                        st.write(f"**ID:** `{t['id']}`")
                        st.write(f"**Created:** `{t['created_at'][:19]}`")
                        st.write(f"**Tracked Time:** `{t['total_formatted']}`")
                    with ec2:
                        new_status = st.selectbox("Status", ["todo", "in-progress", "done"], index=["todo", "in-progress", "done"].index(t["status"]), key=f"st_{t['id']}")
                        new_priority = st.selectbox("Priority", ["low", "medium", "high", "critical"], index=["low", "medium", "high", "critical"].index(t["priority"]), key=f"pr_{t['id']}")
                        if new_status != t["status"] or new_priority != t["priority"]:
                            if st.button("Update Attributes", key=f"up_{t['id']}"):
                                api_patch(f"/tasks/{t['id']}", {"status": new_status, "priority": new_priority})
                                st.success("Updated!")
                                st.rerun()
                    with ec3:
                        if t.get("is_active"):
                            if st.button("⏹️ Stop Timer", key=f"m_stop_{t['id']}", type="primary"):
                                api_post(f"/tasks/{t['id']}/stop")
                                st.rerun()
                        else:
                            if st.button("▶️ Start Timer", key=f"m_start_{t['id']}"):
                                api_post(f"/tasks/{t['id']}/start")
                                st.rerun()
                        
                        if st.button("🗑️ Delete Task", key=f"del_{t['id']}"):
                            api_delete(f"/tasks/{t['id']}")
                            st.toast("Task deleted!", icon="🗑️")
                            time_module.sleep(0.5)
                            st.rerun()

# ----------------- VIEW 3: MANUAL TIME ENTRY -----------------
elif nav == "✍️ Manual Time Entry":
    st.title("✍️ Manual / Retroactive Time Entry")
    st.caption("Log time retroactively for offline work, client meetings, architecture reviews, or debugging sessions.")

    tasks = api_get("/tasks") or []
    if not tasks:
        st.warning("No tasks available to log time for. Create a task first.")
    else:
        task_options = {f"#{t['id']} - {t['title']} ({t['project']})": t["id"] for t in tasks}
        
        with st.form("manual_session_form"):
            selected_task_label = st.selectbox("Select Task", list(task_options.keys()))
            selected_task_id = task_options[selected_task_label]

            mc1, mc2 = st.columns(2)
            with mc1:
                entry_date = st.date_input("Date of Work", value=date.today())
                start_t = st.time_input("Start Time", value=time(9, 0))
            with mc2:
                # Default end time 1 hour later
                end_t = st.time_input("End Time", value=time(10, 30))
                note = st.text_input("Session Note (Optional)", placeholder="e.g., Code review with team")

            # Calculate estimated duration
            start_dt = datetime.combine(entry_date, start_t)
            end_dt = datetime.combine(entry_date, end_t)
            duration_secs = (end_dt - start_dt).total_seconds()

            if duration_secs > 0:
                hours = duration_secs / 3600.0
                st.info(f"⏱️ Calculated Duration: **{hours:.2f} hours** ({int(duration_secs//60)} minutes)")
                if duration_secs >= 7200:
                    st.warning("⚠️ This session exceeds 2 hours and will be flagged for review.")
            else:
                st.error("End time must be later than start time.")

            submit_manual = st.form_submit_button("Log Session", type="primary")
            if submit_manual:
                if duration_secs <= 0:
                    st.error("Invalid duration. End time must be after start time.")
                else:
                    payload = {
                        "task_id": selected_task_id,
                        "start_time": start_dt.isoformat(),
                        "end_time": end_dt.isoformat(),
                        "note": note or None
                    }
                    res = api_post("/sessions/manual", payload)
                    if res and res.status_code == 201:
                        st.success("Session logged successfully!")
                        time_module.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Failed to log session.")

# ----------------- VIEW 4: ANALYTICS & REPORTS -----------------
elif nav == "📈 Analytics & Reports":
    st.title("📈 Developer Productivity & Time Analytics")

    r_col1, r_col2 = st.columns([2, 4])
    with r_col1:
        range_choice = st.selectbox("Report Time Range", ["day", "week", "month", "all"], index=1)

    report = api_get("/reports/summary", params={"range": range_choice})

    if not report:
        st.error("Unable to load summary report.")
    else:
        # Top KPI cards
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Tracked Time", report["formatted_time"])
        k2.metric("Total Hours", f"{report['total_hours']}h")
        k3.metric("Completed Sessions", report["total_sessions"])
        k4.metric("Idle Flagged Sessions", report["idle_flagged_count"])

        st.markdown("---")

        projects = report.get("projects", [])
        tasks_rep = report.get("tasks", [])

        if not projects and not tasks_rep:
            st.info(f"No time tracking sessions recorded for the '{range_choice}' window.")
        else:
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Time Spent by Project")
                df_p = pd.DataFrame(projects)
                if not df_p.empty:
                    fig_bar = px.bar(
                        df_p,
                        x="project",
                        y="total_hours",
                        text="formatted_time",
                        labels={"project": "Project", "total_hours": "Hours"},
                        color="total_hours",
                        color_continuous_scale="Blues"
                    )
                    fig_bar.update_layout(showlegend=False, height=350)
                    st.plotly_chart(fig_bar, use_container_width=True)
                else:
                    st.write("No project records.")

            with c2:
                st.subheader("Time Spent by Task (Top Items)")
                df_t = pd.DataFrame(tasks_rep)
                if not df_t.empty:
                    df_t_top = df_t.head(8)
                    fig_t = px.bar(
                        df_t_top,
                        y="task_title",
                        x="total_hours",
                        text="formatted_time",
                        orientation="h",
                        labels={"task_title": "Task", "total_hours": "Hours"},
                        color="project",
                        color_discrete_sequence=px.colors.qualitative.Safe
                    )
                    fig_t.update_layout(yaxis={'categoryorder':'total ascending'}, height=350)
                    st.plotly_chart(fig_t, use_container_width=True)
                else:
                    st.write("No task records.")

            # Tabular breakdown
            st.subheader("Project Summary Table")
            if not df_p.empty:
                st.dataframe(
                    df_p[["project", "formatted_time", "total_hours", "task_count", "session_count"]].rename(
                        columns={
                            "project": "Project",
                            "formatted_time": "Time Spent",
                            "total_hours": "Hours",
                            "task_count": "Tasks",
                            "session_count": "Sessions"
                        }
                    ),
                    use_container_width=True
                )

# ----------------- VIEW 5: SESSION AUDIT LOG & CSV EXPORT -----------------
elif nav == "📜 Session Audit Log":
    st.title("📜 Session Audit Log & CSV Export")
    st.caption("Complete history of all work sessions with start and end timestamps, durations, and idle flags.")

    # Export CSV button
    ec1, ec2 = st.columns([3, 1])
    with ec2:
        try:
            csv_res = requests.get(f"{API_BASE_URL}/export/csv")
            if csv_res.status_code == 200:
                st.download_button(
                    label="📥 Download CSV Export",
                    data=csv_res.content,
                    file_name="developer_time_tracking_sessions.csv",
                    mime="text/csv",
                    type="primary",
                    use_container_width=True
                )
        except Exception:
            st.button("📥 Download CSV", disabled=True)

    sessions = api_get("/sessions", params={"limit": 200}) or []
    if not sessions:
        st.info("No session records found.")
    else:
        df_sess = pd.DataFrame(sessions)
        
        # Format columns for display
        df_sess["Flagged Idle"] = df_sess["flagged_idle"].apply(lambda x: "⚠️ EXCEEDED 2H" if x else "✅ Normal")
        df_sess["Duration"] = df_sess["duration_formatted"]
        
        display_cols = ["id", "task_title", "project", "start_time", "end_time", "Duration", "Flagged Idle", "note"]
        display_df = df_sess[[c for c in display_cols if c in df_sess.columns]]
        st.dataframe(display_df, use_container_width=True, height=450)

        # Delete session tool
        with st.expander("🛠️ Manage / Delete a Session"):
            del_sess_id = st.number_input("Session ID to delete", min_value=1, step=1)
            if st.button("Delete Session Record", type="secondary"):
                del_res = api_delete(f"/sessions/{del_sess_id}")
                if del_res and del_res.status_code == 200:
                    st.success(f"Session {del_sess_id} deleted!")
                    time_module.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Failed to delete session.")
