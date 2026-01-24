import streamlit as st
import os
import json
import glob

st.set_page_config(page_title="Agent Forge Dashboard", layout="wide")

st.title("Agent Forge MVP - Debug Dashboard")

LOG_DIR = "logs/checkpoints"

if not os.path.exists(LOG_DIR):
    st.warning(f"No logs found in {LOG_DIR}")
    st.stop()

# 1. Sidebar: Select Agent
agents = [d for d in os.listdir(LOG_DIR) if os.path.isdir(os.path.join(LOG_DIR, d))]
selected_agent = st.sidebar.selectbox("Select Agent", agents)

if selected_agent:
    agent_dir = os.path.join(LOG_DIR, selected_agent)
    files = glob.glob(os.path.join(agent_dir, "*.json"))
    files.sort(reverse=True) # Newest first

    st.sidebar.markdown(f"**Found {len(files)} checkpoints**")
    
    # 2. Timeline
    selected_file = st.selectbox("Select Checkpoint (Timestamp)", files, format_func=lambda x: os.path.basename(x))
    
    if selected_file:
        with open(selected_file, "r") as f:
            data = json.load(f)
            
        # 3. Detail View
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Metadata")
            st.text_input("Timestamp", data.get("timestamp"), disabled=True)
            st.text_input("Agent ID", data.get("agent_id"), disabled=True)
            st.text_area("Task", data.get("task"), disabled=True)
            st.text_area("Result", data.get("result"), disabled=True)
            
        with col2:
            st.subheader("Full State")
            st.json(data.get("state"))
            
        st.subheader("Raw JSON")
        st.code(json.dumps(data, indent=2), language="json")
