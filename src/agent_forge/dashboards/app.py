import streamlit as st
import streamlit as st
import os
import pandas as pd
import time
from agent_forge.dashboards.data_loader import (
    load_control, save_control, load_metrics, load_events, 
    get_available_agents, get_agent_checkpoints, load_checkpoint, load_messages,
    METRICS_FILE, LOG_DIR, MESSAGE_LOG, EVENT_LOG
)

st.set_page_config(page_title="Agent Forge Dashboard", layout="wide")

st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Simulation Control", "Checkpoint Inspector", "Message Traces"])

# Auto Refresh
st.sidebar.markdown("---")
auto_refresh = st.sidebar.checkbox("Auto Refresh (1s)", value=True)
if auto_refresh:
    time.sleep(1)
    st.rerun()

if page == "Simulation Control":
    st.title("Simulation Control & Monitoring")
    
    # 1. Control Panel
    st.subheader("Control Center")
    col1, col2, col3 = st.columns(3)
    
    config = load_control()
    current_status = config.get("status", "STOPPED")
    
    with col1:
        st.write(f"**Status:** {current_status}")
        if st.button("START", disabled=(current_status=="RUNNING")):
            config["status"] = "RUNNING"
            save_control(config)
            st.rerun()
            
    with col2:
        if st.button("PAUSE", disabled=(current_status!="RUNNING")):
            config["status"] = "PAUSED"
            save_control(config)
            st.rerun()
            
    with col3:
        if st.button("STOP", disabled=(current_status=="STOPPED")):
            config["status"] = "STOPPED"
            save_control(config)
            st.rerun()

    # 2. Parameters & Stress Injection
    st.subheader("Live Parameters")
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown("**Stress Testing**")
        latency = st.slider("Simulated Latency (sec)", 0.0, 2.0, config.get("stress_config", {}).get("latency_range", [0,0])[1])
        fail_rate = st.slider("Failure Injection Rate", 0.0, 1.0, config.get("stress_config", {}).get("failure_rate", 0.0))
        
        if latency != config["stress_config"].get("latency_range", [0,0])[1] or fail_rate != config["stress_config"].get("failure_rate", 0):
            config["stress_config"]["latency_range"] = [0.0, latency]
            config["stress_config"]["failure_rate"] = fail_rate
            save_control(config)
            st.success("Parameters Updated!")

    with c2:
        st.markdown("**Agent Params**")
        epsilon = st.slider("Exploration Rate (Epsilon)", 0.0, 1.0, config.get("agent_params", {}).get("epsilon", 1.0))
        
        if epsilon != config["agent_params"].get("epsilon", 1.0):
            config["agent_params"]["epsilon"] = epsilon
            save_control(config)
            
    # 3. Live Metrics
    st.markdown("---")
    st.subheader("Real-time Learning Metrics")
    
    df = load_metrics()
    if not df.empty:
        # Chart 1: Reward over Time
        st.line_chart(df[["step", "reward"]].set_index("step"))
        
        # Key Stats
        last_row = df.iloc[-1]
        m1, m2, m3 = st.columns(3)
        m1.metric("Current Step", int(last_row["step"]))
        m2.metric("Last Reward", f"{last_row['reward']:.2f}")
        m3.metric("Current Epsilon", f"{last_row['epsilon']:.2f}")
    else:
        st.warning("No metrics file found yet. Start the simulation!")

    # 4. Events
    st.subheader("System Events")
    events = load_events()
    if events:
        st.dataframe(pd.DataFrame(events).sort_values("timestamp", ascending=False))
    else:
        st.info("No events logged.")

elif page == "Checkpoint Inspector":
    st.title("Agent Forge MVP - Checkpoint Inspector")
    
    agents = get_available_agents()
    if not agents:
        st.warning(f"No logs found in {LOG_DIR}")
        st.stop()
        
    selected_agent = st.sidebar.selectbox("Select Agent", agents)
    
    if selected_agent:
        files = get_agent_checkpoints(selected_agent)
        st.sidebar.markdown(f"**Found {len(files)} checkpoints**")
        selected_file = st.selectbox("Select Checkpoint", files, format_func=lambda x: os.path.basename(x))
        if selected_file:
            data = load_checkpoint(selected_file)
            st.json(data)

elif page == "Message Traces":
    st.title("Agent Forge MVP - Message Traces")
    data = load_messages()
    
    if not data:
        st.warning("No message logs found.")
    else:
        st.dataframe(pd.DataFrame(data))
