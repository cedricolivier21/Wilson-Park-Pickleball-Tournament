import streamlit as pd_streamlit_wrapper
import random
import time
import pandas as pd

# --- MOBILE-FIRST PAGE SETUP ---
pd_streamlit_wrapper.set_page_config(page_title="Pickleball Hub", page_icon="🏓", layout="centered")

# --- IMMUTABLE SYSTEM OWNER CREDENTIAL ---
OWNER_PASSKEY = "admin123"

# --- INITIALIZE GLOBAL DATABASE STATES ---
if "tournament_history" not in pd_streamlit_wrapper.session_state:
pd_streamlit_wrapper.session_state.tournament_history = []
if "current_tournament" not in pd_streamlit_wrapper.session_state:
pd_streamlit_wrapper.session_state.current_tournament = None
if "authorized_directors" not in pd_streamlit_wrapper.session_state:
pd_streamlit_wrapper.session_state.authorized_directors = set()

pd_streamlit_wrapper.title("🏓 Pro Pickleball Tournament Engine")
pd_streamlit_wrapper.write("---")

# ==========================================
# SIDEBAR: ADVANCED ACCESS MANAGEMENT
# ==========================================
pd_streamlit_wrapper.sidebar.header("🔐 Access Control Desk")

system_role = pd_streamlit_wrapper.sidebar.selectbox(
"Choose System Interface",
["1. Player (View Only)", "2. Tournament Director", "3. App Creator / Owner"]
)

is_owner = False
is_director = False

if system_role == "3. App Creator / Owner":
passkey = pd_streamlit_wrapper.sidebar.text_input("Enter App Creator Master Passkey:", type="password")
if passkey == OWNER_PASSKEY:
is_owner = True
pd_streamlit_wrapper.sidebar.success("⚡ Master Access Granted")
elif passkey:
pd_streamlit_wrapper.sidebar.error("❌ Invalid Passkey")

elif system_role == "2. Tournament Director":
director_name = pd_streamlit_wrapper.sidebar.text_input("Enter Registered Director Name:")
if director_name in pd_streamlit_wrapper.session_state.authorized_directors:
is_director = True
pd_streamlit_wrapper.sidebar.success(f"🎬 Director Access Granted: {director_name}")
elif director_name:
pd_streamlit_wrapper.sidebar.error("🔒 Name not authorized by Creator.")

if is_owner:
pd_streamlit_wrapper.sidebar.subheader("🛠️ Creator Control Panel")
new_dir = pd_streamlit_wrapper.sidebar.text_input("Authorize New Tournament Director Name:")
if pd_streamlit_wrapper.sidebar.button("Grant Director Rights") and new_dir:
pd_streamlit_wrapper.session_state.authorized_directors.add(new_dir)
pd_streamlit_wrapper.sidebar.success(f"Added: {new_dir}")

pd_streamlit_wrapper.sidebar.write("**Current Authorized Directors:**")
pd_streamlit_wrapper.sidebar.write(list(pd_streamlit_wrapper.session_state.authorized_directors) if pd_streamlit_wrapper.session_state.authorized_directors else "None")

has_edit_rights = is_owner or is_director
page = pd_streamlit_wrapper.sidebar.selectbox("🗺️ App Directory Navigation", ["Active Tournament Ground", "Historical Record Ledger"])

# ==========================================
# CORE STANDINGS ENGINE (LEADERBOARD MATH)
# ==========================================
def calculate_leaderboard(curr_state):
teams = curr_state["teams"]
stats = {t: {"Played": 0, "Wins": 0, "Losses": 0, "Ties": 0, "Gained": 0, "Lost": 0, "Diff": 0, "Points": 0} for t in teams}

for m in curr_state["matches"]:
if m["done"]:
t1, t2 = m["t1"], m["t2"]
s1, s2 = int(m["s1"]), int(m["s2"])

stats[t1]["Played"] += 1
stats[t2]["Played"] += 1
stats[t1]["Gained"] += s1
stats[t1]["Lost"] += s2
stats[t2]["Gained"] += s2
stats[t2]["Lost"] += s1

if s1 > s2:
stats[t1]["Wins"] += 1
stats[t1]["Points"] += 2
stats[t2]["Losses"] += 1
elif s2 > s1:
stats[t2]["Wins"] += 1
stats[t2]["Points"] += 2
stats[t1]["Losses"] += 1
else:
stats[t1]["Ties"] += 1
stats[t1]["Points"] += 1
stats[t2]["Ties"] += 1
stats[t2]["Points"] += 1

for t in teams:
stats[t]["Diff"] = stats[t]["Gained"] - stats[t]["Lost"]

df = pd.DataFrame.from_dict(stats, orient="index")
df.index.name = "Team Name"
df = df.reset_index()
df = df.sort_values(by=["Points", "Diff"], ascending=[False, False]).reset_index(drop=True)
return df

# ==========================================
# PAGE: ACTIVE TOURNAMENT GROUND
# ==========================================
if page == "Active Tournament Ground":
if pd_streamlit_wrapper.session_state.current_tournament is None:
pd_streamlit_wrapper.subheader("🏆 Build New Bracket Structure")

if not is_owner:
pd_streamlit_wrapper.warning("🔒 Access Blocked: Only the App Creator can deploy new tournaments.")
else:
t_type = pd_streamlit_wrapper.selectbox("Tournament Format", ["League Based", "Round Robin (2 Groups)"])

if t_type == "Round Robin (2 Groups)":
pd_streamlit_wrapper.info("💡 Dynamic Rule Restriction: Round Robin demands an even amount of teams (Min 8).")
num_teams = pd_streamlit_wrapper.number_input("Number of Teams", min_value=8, step=2, value=8)
else:
num_teams = pd_streamlit_wrapper.number_input("Number of Teams", min_value=4, step=1, value=4)

score_rule = pd_streamlit_wrapper.selectbox("Scoring Mode Rule Set", [
"Regular: Play to 11 (Win by 2)",
"Rally: Play to 15 (Win by 2)",
"Timed: 10-Minute Blitz (Most points wins - Ties Allowed)"
])

team_mode = pd_streamlit_wrapper.radio("Team Initialization Configuration", ["Manual Setup", "Random AI Shuffle Pairs"])

teams = []
if team_mode == "Manual Setup":
for i in range(int(num_teams)):
t_name = pd_streamlit_wrapper.text_input(f"Team {i+1} Name Designation", value=f"Team {chr(65+i)}", key=f"m_team_{i}")
teams.append(t_name)
else:
players = []
for i in range(int(num_teams * 2)):
p_name = pd_streamlit_wrapper.text_input(f"Individual Player Profile {i+1}", value=f"Player {i+1}", key=f"r_player_{i}")
players.append(p_name)

if pd_streamlit_wrapper.button("🔀 Execute Shuffled Pairing Matrix"):
shuffled = players.copy()
random.shuffle(shuffled)
teams = [f"{shuffled[i]} / {shuffled[i+1]}" for i in range(0, len(shuffled), 2)]
pd_streamlit_wrapper.success("🤖 AI Formed Standalone Teams Successfully:")
pd_streamlit_wrapper.write(teams)
pd_streamlit_wrapper.session_state.temp_teams = teams

if pd_streamlit_wrapper.button("🚀 Push Tournament Schedule Live"):
final_teams = teams if team_mode == "Manual Setup" else pd_streamlit_wrapper.session_state.get("temp_teams", [])
if len(final_teams) < num_teams:
pd_streamlit_wrapper.error("Validation Halt: Complete all team text input fields correctly first.")
else:
matches = []
if t_type == "League Based":
for i in range(len(final_teams)):
for j in range(i+1, len(final_teams)):
matches.append({"t1": final_teams[i], "t2": final_teams[j], "s1": 0, "s2": 0, "done": False, "group": "League Table"})
else:
half = len(final_teams) // 2
g1_teams, g2_teams = final_teams[:half], final_teams[half:]
for i in range(len(g1_teams)):
for j in range(i+1, len(g1_teams)):
matches.append({"t1": g1_teams[i], "t2": g1_teams[j], "s1": 0, "s2": 0, "done": False, "group": "Group A"})
for i in range(len(g2_teams)):
for j in range(i+1, len(g2_teams)):
matches.append({"t1": g2_teams[i], "t2": g2_teams[j], "s1": 0, "s2": 0, "done": False, "group": "Group B"})

pd_streamlit_wrapper.session_state.current_tournament = {
"type": t_type, "score_rule": score_rule, "teams": final_teams,
"matches": matches, "stage": "Qualifiers"
}
pd_streamlit_wrapper.rerun()
else:
curr = pd_streamlit_wrapper.session_state.current_tournament
pd_streamlit_wrapper.subheader(f"📊 Bracket Display: {curr['type']}")
pd_streamlit_wrapper.caption(f"Scoring System: {curr['score_rule']}")

pd_streamlit_wrapper.write("### 🏅 Live Standings Stand")
leaderboard_df = calculate_leaderboard(curr)

if curr["type"] == "Round Robin (2 Groups)":
half_team_count = len(curr["teams"]) // 2
pd_streamlit_wrapper.markdown("**Group A Table Grid**")
g1_list = curr["teams"][:half_team_count]
pd_streamlit_wrapper.dataframe(leaderboard_df[leaderboard_df["Team Name"].isin(g1_list)], hide_index=True)

pd_streamlit_wrapper.markdown("**Group B Table Grid**")
g2_list = curr["teams"][half_team_count:]
pd_streamlit_wrapper.dataframe(leaderboard_df[leaderboard_df["Team Name"].isin(g2_list)], hide_index=True)
else:
pd_streamlit_wrapper.dataframe(leaderboard_df, hide_index=True)

if not has_edit_rights:
pd_streamlit_wrapper.info("🔒 View-Only Active: Match score configuration panels are hidden for Players.")