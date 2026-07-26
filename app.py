import random
import pandas as pd
import streamlit as st

# Page setup
st.set_page_config(
    page_title="Wilson Park Pickleball Tournament",
    page_icon="🏓",
    layout="wide",
)

st.title("🏓 Wilson Park Pickleball Tournament")
st.caption("July 26 • 22 Players • 11 Teams • 4 Courts")

# ---------------------------------------------------------
# SESSION STATE & AUTHENTICATION
# ---------------------------------------------------------
DIRECTOR_PINS = ["1234", "5678"]  # PINs for the 2 Tournament Directors

if "role" not in st.session_state:
    st.session_state.role = "Viewer"

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
        "playin": [None, None],
        "semi1": [None, None],
        "semi2": [None, None],
        "final": [None, None],
    }

# --- SIDEBAR AUTHENTICATION ---
st.sidebar.title("🔐 Access Control")
if st.session_state.role == "Viewer":
    st.sidebar.info("👤 Currently viewing as **Player / Spectator**")
    pin_input = st.sidebar.text_input(
        "Enter Director PIN to edit scores:", type="password"
    )
    if st.sidebar.button("Login as Director"):
        if pin_input in DIRECTOR_PINS:
            st.session_state.role = "Director"
            st.sidebar.success("Logged in as Tournament Director!")
            st.rerun()
        else:
            st.sidebar.error("Invalid Director PIN.")
else:
    st.sidebar.success("🔑 Logged in as **Tournament Director**")
    if st.sidebar.button("Logout to Viewer Mode"):
        st.session_state.role = "Viewer"
        st.rerun()


# ---------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------
def generate_round_robin(team_list):
    matches = []
    for i in range(len(team_list)):
        for j in range(i + 1, len(team_list)):
            matches.append({"t1": team_list[i], "t2": team_list[j]})
    return matches


def calculate_standings(teams, matches, scores_dict):
    stats = {
        t["name"]: {
            "Team": t["name"],
            "Players": " & ".join(t["members"]),
            "Played": 0,
            "Won": 0,
            "Drawn": 0,
            "Lost": 0,
            "Gained": 0,
            "Conceded": 0,
            "Diff": 0,
            "Points": 0,
        }
        for t in teams
    }

    for idx, match in enumerate(matches):
        s1, s2 = scores_dict.get(idx, (None, None))

        # Ignore match if scores are unentered or left at 0-0
        if s1 is None or s2 is None or (s1 == 0 and s2 == 0):
            continue

        t1_name = match["t1"]["name"]
        t2_name = match["t2"]["name"]

        stats[t1_name]["Played"] += 1
        stats[t2_name]["Played"] += 1

        # Track Gained, Conceded, Diff
        stats[t1_name]["Gained"] += s1
        stats[t1_name]["Conceded"] += s2
        stats[t1_name]["Diff"] += s1 - s2

        stats[t2_name]["Gained"] += s2
        stats[t2_name]["Conceded"] += s1
        stats[t2_name]["Diff"] += s2 - s1

        # Match Points: Win=2, Draw=1, Loss=0
        if s1 > s2:
            stats[t1_name]["Won"] += 1
            stats[t1_name]["Points"] += 2
            stats[t2_name]["Lost"] += 1
        elif s2 > s1:
            stats[t2_name]["Won"] += 1
            stats[t2_name]["Points"] += 2
            stats[t1_name]["Lost"] += 1
        else:
            stats[t1_name]["Drawn"] += 1
            stats[t1_name]["Points"] += 1
            stats[t2_name]["Drawn"] += 1
            stats[t2_name]["Points"] += 1

    df = pd.DataFrame(list(stats.values()))
    # Primary sort: Points -> Secondary sort: Diff -> Tertiary sort: Points Gained
    df = df.sort_values(
        by=["Points", "Diff", "Gained"], ascending=[False, False, False]
    )
    return df.reset_index(drop=True)


# ---------------------------------------------------------
# STEP 1: INITIAL SETUP (DIRECTOR ONLY)
# ---------------------------------------------------------
if not st.session_state.setup_complete:
    if st.session_state.role != "Director":
        st.warning(
            "⏳ Tournament is currently being configured by Directors. Please check back shortly!"
        )
    else:
        st.subheader("🛠️ Tournament Setup (Director Access)")
        default_players = "\n".join([f"Player {i+1}" for i in range(22)])
        players_text = st.text_area(
            "Enter 22 Player Names (one per line):",
            value=default_players,
            height=200,
        )

        if st.button("🔀 Generate Random Teams & Courts Schedule", type="primary"):
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

                # Generate round robin fixtures
                teams_a = [t for t in teams if t["group"] == "A"]
                teams_b = [t for t in teams if t["group"] == "B"]

                matches_a = generate_round_robin(teams_a)
                matches_b = generate_round_robin(teams_b)

                # Assign court numbers (1 to 4) dynamically across all fixtures
                all_fixtures = matches_a + matches_b
                for idx, match in enumerate(all_fixtures):
                    match["court"] = f"Court {(idx % 4) + 1}"

                st.session_state.fixtures_a = matches_a
                st.session_state.fixtures_b = matches_b
                st.session_state.scores_a = {}
                st.session_state.scores_b = {}
                st.session_state.setup_complete = True
                st.rerun()

# ---------------------------------------------------------
# STEP 2: LIVE TOURNAMENT DASHBOARD
# ---------------------------------------------------------
else:
    # TEAM OVERVIEW
    with st.expander("👥 View Roster & Assigned Teams", expanded=False):
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

    # STANDINGS TABLES
    teams_a = [t for t in st.session_state.teams if t["group"] == "A"]
    teams_b = [t for t in st.session_state.teams if t["group"] == "B"]

    standings_a = calculate_standings(
        teams_a, st.session_state.fixtures_a, st.session_state.scores_a
    )
    standings_b = calculate_standings(
        teams_b, st.session_state.fixtures_b, st.session_state.scores_b
    )

    st.subheader("📊 Live Standings")
    col_s1, col_s2 = st.columns(2)

    with col_s1:
        st.markdown("#### Group A (Top 3 Advance)")
        st.dataframe(standings_a, hide_index=True, use_container_width=True)

    with col_s2:
        st.markdown("#### Group B (Top 2 Advance)")
        st.dataframe(standings_b, hide_index=True, use_container_width=True)

    st.divider()

    # FIXTURES & SCORES BY COURT
    st.subheader("⚔️ Fixtures & Court Allocation")
    is_director = st.session_state.role == "Director"

    if not is_director:
        st.info("💡 Log in via the sidebar if you are a Tournament Director to edit scores.")

    col_f1, col_f2 = st.columns(2)

    # Function to render match score input or static display
    def render_fixture(idx, match, score_dict, key_prefix):
        curr_s1, curr_s2 = score_dict.get(idx, (0, 0))
        c1, c2, c3, c4, c5 = st.columns([1.5, 3, 1.5, 1.5, 3])

        c1.caption(f"📍 **{match['court']}**")
        c2.write(f"**{match['t1']['name']}**")

        if is_director:
            s1 = c3.number_input(
                f"{match['t1']['name']} score",
                min_value=0,
                value=curr_s1,
                key=f"{key_prefix}_s1_{idx}",
                label_visibility="collapsed",
            )
            s2 = c4.number_input(
                f"{match['t2']['name']} score",
                min_value=0,
                value=curr_s2,
                key=f"{key_prefix}_s2_{idx}",
                label_visibility="collapsed",
            )
            score_dict[idx] = (s1, s2)
        else:
            score_str = (
                f"{curr_s1} - {curr_s2}"
                if (curr_s1 > 0 or curr_s2 > 0)
                else "VS"
            )
            c3.write(f"**{score_str}**")

        c5.write(f"**{match['t2']['name']}**")

    with col_f1:
        st.markdown("#### Group A Matches")
        for idx, match in enumerate(st.session_state.fixtures_a):
            render_fixture(idx, match, st.session_state.scores_a, "a")

    with col_f2:
        st.markdown("#### Group B Matches")
        for idx, match in enumerate(st.session_state.fixtures_b):
            render_fixture(idx, match, st.session_state.scores_b, "b")

    st.divider()

    # ---------------------------------------------------------
    # STEP 3: DYNAMIC KNOCKOUT BRACKET
    # ---------------------------------------------------------
    st.subheader("🏆 Knockout Stage")

    team_3rd_a = standings_a.iloc[2]["Team"]
    team_2nd_b = standings_b.iloc[1]["Team"]

    team_1st_a = standings_a.iloc[0]["Team"]
    team_1st_b = standings_b.iloc[0]["Team"]
    team_2nd_a = standings_a.iloc[1]["Team"]

    # --- PLAY-IN MATCH ---
    st.markdown("### 1. Play-in Match (Court 1)")
    st.caption("3rd Group A vs 2nd Group B")

    col_pi1, col_pi2, col_pi3, col_pi4 = st.columns([3, 2, 2, 3])
    col_pi1.write(f"**{team_3rd_a}**")

    pi_s1, pi_s2 = st.session_state.ko_scores["playin"]
    if is_director:
        pi_s1 = col_pi2.number_input(
            "Play-in 1",
            min_value=0,
            value=pi_s1 if pi_s1 is not None else 0,
            key="pi_s1",
            label_visibility="collapsed",
        )
        pi_s2 = col_pi3.number_input(
            "Play-in 2",
            min_value=0,
            value=pi_s2 if pi_s2 is not None else 0,
            key="pi_s2",
            label_visibility="collapsed",
        )
        st.session_state.ko_scores["playin"] = [pi_s1, pi_s2]
    else:
        score_display = (
            f"{pi_s1} - {pi_s2}"
            if (pi_s1 is not None and (pi_s1 > 0 or pi_s2 > 0))
            else "VS"
        )
        col_pi2.write(f"**{score_display}**")

    col_pi4.write(f"**{team_2nd_b}**")

    playin_winner = (
        team_3rd_a
        if (pi_s1 and pi_s2 and pi_s1 > pi_s2)
        else (
            team_2nd_b
            if (pi_s1 and pi_s2 and pi_s2 > pi_s1)
            else "Winner Play-in"
        )
    )

    # --- SEMIFINALS ---
    st.markdown("### 2. Semifinals")
    col_semi1, col_semi2 = st.columns(2)

    with col_semi1:
        st.markdown("**Semifinal 1 (Court 2)**")
        st.caption("Winner Play-in vs 1st Group A")

        cs1_1, cs1_2, cs1_3, cs1_4 = st.columns([3, 2, 2, 3])
        cs1_1.write(f"**{playin_winner}**")

        sm1_s1, sm1_s2 = st.session_state.ko_scores["semi1"]
        if is_director:
            sm1_s1 = cs1_2.number_input(
                "Semi1 S1",
                min_value=0,
                value=sm1_s1 if sm1_s1 is not None else 0,
                key="sm1_s1",
                label_visibility="collapsed",
            )
            sm1_s2 = cs1_3.number_input(
                "Semi1 S2",
                min_value=0,
                value=sm1_s2 if sm1_s2 is not None else 0,
                key="sm1_s2",
                label_visibility="collapsed",
            )
            st.session_state.ko_scores["semi1"] = [sm1_s1, sm1_s2]
        else:
            score_display = (
                f"{sm1_s1} - {sm1_s2}"
                if (sm1_s1 is not None and (sm1_s1 > 0 or sm1_s2 > 0))
                else "VS"
            )
            cs1_2.write(f"**{score_display}**")

        cs1_4.write(f"**{team_1st_a}**")

        semi1_winner = (
            playin_winner
            if (sm1_s1 and sm1_s2 and sm1_s1 > sm1_s2)
            else (
                team_1st_a
                if (sm1_s1 and sm1_s2 and sm1_s2 > sm1_s1)
                else "Semi 1 Winner"
            )
        )

    with col_semi2:
        st.markdown("**Semifinal 2 (Court 3)**")
        st.caption("1st Group B vs 2nd Group A")

        cs2_1, cs2_2, cs2_3, cs2_4 = st.columns([3, 2, 2, 3])
        cs2_1.write(f"**{team_1st_b}**")

        sm2_s1, sm2_s2 = st.session_state.ko_scores["semi2"]
        if is_director:
            sm2_s1 = cs2_2.number_input(
                "Semi2 S1",
                min_value=0,
                value=sm2_s1 if sm2_s1 is not None else 0,
                key="sm2_s1",
                label_visibility="collapsed",
            )
            sm2_s2 = cs2_3.number_input(
                "Semi2 S2",
                min_value=0,
                value=sm2_s2 if sm2_s2 is not None else 0,
                key="sm2_s2",
                label_visibility="collapsed",
            )
            st.session_state.ko_scores["semi2"] = [sm2_s1, sm2_s2]
        else:
            score_display = (
                f"{sm2_s1} - {sm2_s2}"
                if (sm2_s1 is not None and (sm2_s1 > 0 or sm2_s2 > 0))
                else "VS"
            )
            cs2_2.write(f"**{score_display}**")

        cs2_4.write(f"**{team_2nd_a}**")

        semi2_winner = (
            team_1st_b
            if (sm2_s1 and sm2_s2 and sm2_s1 > sm2_s2)
            else (
                team_2nd_a
                if (sm2_s1 and sm2_s2 and sm2_s2 > sm2_s1)
                else "Semi 2 Winner"
            )
        )

    # --- CHAMPIONSHIP FINAL ---
    st.markdown("### 3. Championship Final (Court 1)")

    cf_1, cf_2, cf_3, cf_4 = st.columns([3, 2, 2, 3])
    cf_1.write(f"**{semi1_winner}**")

    f_s1, f_s2 = st.session_state.ko_scores["final"]
    if is_director:
        f_s1 = cf_2.number_input(
            "Final S1",
            min_value=0,
            value=f_s1 if f_s1 is not None else 0,
            key="f_s1",
            label_visibility="collapsed",
        )
        f_s2 = cf_3.number_input(
            "Final S2",
            min_value=0,
            value=f_s2 if f_s2 is not None else 0,
            key="f_s2",
            label_visibility="collapsed",
        )
        st.session_state.ko_scores["final"] = [f_s1, f_s2]
    else:
        score_display = (
            f"{f_s1} - {f_s2}"
            if (f_s1 is not None and (f_s1 > 0 or f_s2 > 0))
            else "VS"
        )
        cf_2.write(f"**{score_display}**")

    cf_4.write(f"**{semi2_winner}**")

    if f_s1 and f_s2:
        if f_s1 > f_s2 and semi1_winner != "Semi 1 Winner":
            st.balloons()
            st.success(f"🎉 **TOURNAMENT CHAMPION: {semi1_winner}!** 🎉")
        elif f_s2 > f_s1 and semi2_winner != "Semi 2 Winner":
            st.balloons()
            st.success(f"🎉 **TOURNAMENT CHAMPION: {semi2_winner}!** 🎉")
