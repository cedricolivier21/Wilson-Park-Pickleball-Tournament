import random
import pandas as pd
import streamlit as st

# Set page configuration
st.set_page_config(
    page_title="Wilson Park Pickleball Tournament",
    page_icon="🏓",
    layout="wide",
)

st.title("🏓 Wilson Park Pickleball Tournament")
st.caption("July 26 • 22 Players • 11 Teams")

# ---------------------------------------------------------
# SESSION STATE INITIALIZATION
# ---------------------------------------------------------
if "setup_complete" not in st.session_state:
    st.session_state.setup_complete = False

if "teams" not in st.session_state:
    st.session_state.teams = []

if "fixtures_a" not in st.session_state:
    st.session_state.fixtures_a = []

if "fixtures_b" not in st.session_state:
    st.session_state.fixtures_b = []

if "scores_a" not in st.session_state:
    st.session_state.scores_a = {}

if "scores_b" not in st.session_state:
    st.session_state.scores_b = {}

if "ko_scores" not in st.session_state:
    st.session_state.ko_scores = {
        "playin": [0, 0],
        "semi1": [0, 0],
        "semi2": [0, 0],
        "final": [0, 0],
    }


# Helper function to generate round robin matches
def generate_round_robin(team_list):
    matches = []
    for i in range(len(team_list)):
        for j in range(i + 1, len(team_list)):
            matches.append((team_list[i], team_list[j]))
    return matches


# Helper function to calculate group standings
def calculate_standings(teams, matches, scores_dict):
    stats = {
        t["name"]: {
            "Team": t["name"],
            "Players": " & ".join(t["members"]),
            "Played": 0,
            "Won": 0,
            "Drawn": 0,
            "Lost": 0,
            "Points": 0,
            "Diff": 0,
        }
        for t in teams
    }

    for idx, (t1, t2) in enumerate(matches):
        s1, s2 = scores_dict.get(idx, (None, None))
        if s1 is not None and s2 is not None:
            stats[t1["name"]]["Played"] += 1
            stats[t2["name"]]["Played"] += 1
            stats[t1["name"]]["Diff"] += s1 - s2
            stats[t2["name"]]["Diff"] += s2 - s1

            if s1 > s2:
                stats[t1["name"]]["Won"] += 1
                stats[t1["name"]]["Points"] += 2
                stats[t2["name"]]["Lost"] += 1
            elif s2 > s1:
                stats[t2["name"]]["Won"] += 1
                stats[t2["name"]]["Points"] += 2
                stats[t1["name"]]["Lost"] += 1
            else:
                stats[t1["name"]]["Drawn"] += 1
                stats[t1["name"]]["Points"] += 1
                stats[t2["name"]]["Drawn"] += 1
                stats[t2["name"]]["Points"] += 1

    df = pd.DataFrame(list(stats.values()))
    # Sort by Points (descending), then Differential (descending)
    df = df.sort_values(by=["Points", "Diff"], ascending=[False, False])
    return df.reset_index(drop=True)


# ---------------------------------------------------------
# STEP 1: PLAYER REGISTRATION & SETUP
# ---------------------------------------------------------
if not st.session_state.setup_complete:
    st.subheader("1. Setup Tournament & Teams")

    default_players = "\n".join([f"Player {i+1}" for i in range(22)])
    players_text = st.text_area(
        "Enter 22 Player Names (one per line):",
        value=default_players,
        height=250,
    )

    if st.button("🔀 Generate Random Teams & Schedule", type="primary"):
        player_list = [
            p.strip() for p in players_text.split("\n") if p.strip()
        ]

        if len(player_list) != 22:
            st.error(
                f"Please enter exactly 22 player names. Current count: {len(player_list)}"
            )
        else:
            random.shuffle(player_list)

            # Assign 11 teams
            teams = []
            for i in range(11):
                teams.append(
                    {
                        "id": i + 1,
                        "name": f"Team {i+1}",
                        "members": [
                            player_list[i * 2],
                            player_list[i * 2 + 1],
                        ],
                        "group": "A" if i < 6 else "B",
                    }
                )

            st.session_state.teams = teams

            # Split into Groups (A has 6, B has 5)
            teams_a = [t for t in teams if t["group"] == "A"]
            teams_b = [t for t in teams if t["group"] == "B"]

            # Generate fixtures
            st.session_state.fixtures_a = generate_round_robin(teams_a)
            st.session_state.fixtures_b = generate_round_robin(teams_b)

            # Clear old scores
            st.session_state.scores_a = {}
            st.session_state.scores_b = {}
            st.session_state.setup_complete = True
            st.rerun()

# ---------------------------------------------------------
# STEP 2: MAIN TOURNAMENT DASHBOARD
# ---------------------------------------------------------
else:
    if st.sidebar.button("🔄 Reset / Start Over"):
        st.session_state.setup_complete = False
        st.rerun()

    # SECTION: TEAM OVERVIEW
    with st.expander("👥 View Assigned Teams", expanded=False):
        col_t1, col_t2 = st.columns(2)
        teams_a = [t for t in st.session_state.teams if t["group"] == "A"]
        teams_b = [t for t in st.session_state.teams if t["group"] == "B"]

        with col_t1:
            st.markdown("### Group A")
            for t in teams_a:
                st.write(f"**{t['name']}**: { ' & '.join(t['members']) }")

        with col_t2:
            st.markdown("### Group B")
            for t in teams_b:
                st.write(f"**{t['name']}**: { ' & '.join(t['members']) }")

    # STANDINGS
    teams_a = [t for t in st.session_state.teams if t["group"] == "A"]
    teams_b = [t for t in st.session_state.teams if t["group"] == "B"]

    standings_a = calculate_standings(
        teams_a, st.session_state.fixtures_a, st.session_state.scores_a
    )
    standings_b = calculate_standings(
        teams_b, st.session_state.fixtures_b, st.session_state.scores_b
    )

    st.subheader("📊 Group Standings")
    col_s1, col_s2 = st.columns(2)

    with col_s1:
        st.markdown("#### Group A (Top 3 Advance)")
        st.dataframe(standings_a, hide_index=True, use_container_width=True)

    with col_s2:
        st.markdown("#### Group B (Top 2 Advance)")
        st.dataframe(standings_b, hide_index=True, use_container_width=True)

    st.divider()

    # FIXTURES & SCORE ENTRY
    st.subheader("⚔️ Group Stage Fixtures")
    col_f1, col_f2 = st.columns(2)

    with col_f1:
        st.markdown("#### Group A Matches")
        for idx, (t1, t2) in enumerate(st.session_state.fixtures_a):
            c1, c2, c3, c4 = st.columns([3, 2, 2, 3])
            c1.write(f"**{t1['name']}**")

            curr_s1, curr_s2 = st.session_state.scores_a.get(idx, (0, 0))

            s1 = c2.number_input(
                f"{t1['name']} score",
                min_value=0,
                value=curr_s1,
                key=f"a_s1_{idx}",
                label_visibility="collapsed",
            )
            s2 = c3.number_input(
                f"{t2['name']} score",
                min_value=0,
                value=curr_s2,
                key=f"a_s2_{idx}",
                label_visibility="collapsed",
            )

            c4.write(f"**{t2['name']}**")
            st.session_state.scores_a[idx] = (s1, s2)

    with col_f2:
        st.markdown("#### Group B Matches")
        for idx, (t1, t2) in enumerate(st.session_state.fixtures_b):
            c1, c2, c3, c4 = st.columns([3, 2, 2, 3])
            c1.write(f"**{t1['name']}**")

            curr_s1, curr_s2 = st.session_state.scores_b.get(idx, (0, 0))

            s1 = c2.number_input(
                f"{t1['name']} score",
                min_value=0,
                value=curr_s1,
                key=f"b_s1_{idx}",
                label_visibility="collapsed",
            )
            s2 = c3.number_input(
                f"{t2['name']} score",
                min_value=0,
                value=curr_s2,
                key=f"b_s2_{idx}",
                label_visibility="collapsed",
            )

            c4.write(f"**{t2['name']}**")
            st.session_state.scores_b[idx] = (s1, s2)

    st.divider()

    # ---------------------------------------------------------
    # STEP 3: KNOCKOUT STAGE BRACKET
    # ---------------------------------------------------------
    st.subheader("🏆 Knockout Stage")

    # Extract positions based on rules:
    # 3rd of Group A vs 2nd of Group B -> Play-in
    # Winner Play-in vs 1st Group A -> Semi 1
    # 1st Group B vs 2nd Group A -> Semi 2
    team_3rd_a = standings_a.iloc[2]["Team"]
    team_2nd_b = standings_b.iloc[1]["Team"]

    team_1st_a = standings_a.iloc[0]["Team"]
    team_1st_b = standings_b.iloc[0]["Team"]
    team_2nd_a = standings_a.iloc[1]["Team"]

    # --- PLAY-IN MATCH ---
    st.markdown("### 1. Play-in Knockout Match")
    st.caption("3rd Place Group A vs 2nd Place Group B")

    col_pi1, col_pi2, col_pi3, col_pi4 = st.columns([3, 2, 2, 3])
    col_pi1.write(f"**{team_3rd_a}**")

    pi_s1 = col_pi2.number_input(
        "Play-in Score 1",
        min_value=0,
        value=st.session_state.ko_scores["playin"][0],
        key="pi_s1",
        label_visibility="collapsed",
    )
    pi_s2 = col_pi3.number_input(
        "Play-in Score 2",
        min_value=0,
        value=st.session_state.ko_scores["playin"][1],
        key="pi_s2",
        label_visibility="collapsed",
    )

    col_pi4.write(f"**{team_2nd_b}**")
    st.session_state.ko_scores["playin"] = [pi_s1, pi_s2]

    # Play-in Winner
    playin_winner = (
        team_3rd_a
        if pi_s1 > pi_s2
        else (team_2nd_b if pi_s2 > pi_s1 else "Winner of Play-in")
    )

    # --- SEMIFINALS ---
    st.markdown("### 2. Semifinals")
    col_semi1, col_semi2 = st.columns(2)

    with col_semi1:
        st.markdown("**Semifinal 1**")
        st.caption("Winner Play-in vs 1st Place Group A")

        cs1_1, cs1_2, cs1_3, cs1_4 = st.columns([3, 2, 2, 3])
        cs1_1.write(f"**{playin_winner}**")

        sm1_s1 = cs1_2.number_input(
            "Semi 1 Score 1",
            min_value=0,
            value=st.session_state.ko_scores["semi1"][0],
            key="sm1_s1",
            label_visibility="collapsed",
        )
        sm1_s2 = cs1_3.number_input(
            "Semi 1 Score 2",
            min_value=0,
            value=st.session_state.ko_scores["semi1"][1],
            key="sm1_s2",
            label_visibility="collapsed",
        )

        cs1_4.write(f"**{team_1st_a}**")
        st.session_state.ko_scores["semi1"] = [sm1_s1, sm1_s2]

        semi1_winner = (
            playin_winner
            if sm1_s1 > sm1_s2
            else (team_1st_a if sm1_s2 > sm1_s1 else "Semi 1 Winner")
        )

    with col_semi2:
        st.markdown("**Semifinal 2**")
        st.caption("1st Place Group B vs 2nd Place Group A")

        cs2_1, cs2_2, cs2_3, cs2_4 = st.columns([3, 2, 2, 3])
        cs2_1.write(f"**{team_1st_b}**")

        sm2_s1 = cs2_2.number_input(
            "Semi 2 Score 1",
            min_value=0,
            value=st.session_state.ko_scores["semi2"][0],
            key="sm2_s1",
            label_visibility="collapsed",
        )
        sm2_s2 = cs2_3.number_input(
            "Semi 2 Score 2",
            min_value=0,
            value=st.session_state.ko_scores["semi2"][1],
            key="sm2_s2",
            label_visibility="collapsed",
        )

        cs2_4.write(f"**{team_2nd_a}**")
        st.session_state.ko_scores["semi2"] = [sm2_s1, sm2_s2]

        semi2_winner = (
            team_1st_b
            if sm2_s1 > sm2_s2
            else (team_2nd_a if sm2_s2 > sm2_s1 else "Semi 2 Winner")
        )

    # --- FINAL ---
    st.markdown("### 3. Championship Final")

    cf_1, cf_2, cf_3, cf_4 = st.columns([3, 2, 2, 3])
    cf_1.write(f"**{semi1_winner}**")

    f_s1 = cf_2.number_input(
        "Final Score 1",
        min_value=0,
        value=st.session_state.ko_scores["final"][0],
        key="f_s1",
        label_visibility="collapsed",
    )
    f_s2 = cf_3.number_input(
        "Final Score 2",
        min_value=0,
        value=st.session_state.ko_scores["final"][1],
        key="f_s2",
        label_visibility="collapsed",
    )

    cf_4.write(f"**{semi2_winner}**")
    st.session_state.ko_scores["final"] = [f_s1, f_s2]

    if f_s1 > f_s2 and semi1_winner != "Semi 1 Winner":
        st.balloons()
        st.success(f"🎉 **TOURNAMENT CHAMPION: {semi1_winner}!** 🎉")
    elif f_s2 > f_s1 and semi2_winner != "Semi 2 Winner":
        st.balloons()
        st.success(f"🎉 **TOURNAMENT CHAMPION: {semi2_winner}!** 🎉")
