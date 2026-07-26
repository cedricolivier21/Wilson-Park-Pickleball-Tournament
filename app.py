import json
import os
import random
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Wilson Park Pickleball Tournament",
    page_icon="🏓",
    layout="wide",
)

st.title("🏓 Wilson Park Pickleball Tournament")
st.caption("July 26 • 22 Players • 11 Teams • 4 Courts")

DIRECTOR_PINS = ["1234", "5678"]
DATA_FILE = "tournament_data.json"

# ---------------------------------------------------------
# PERSISTENT STORAGE (FILE I/O)
# ---------------------------------------------------------
def load_tournament_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return None
    return None


def save_tournament_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


# Load existing tournament or initialize defaults
db = load_tournament_data()

if "role" not in st.session_state:
    st.session_state.role = "Viewer"

if db is not None:
    st.session_state.setup_complete = db.get("setup_complete", False)
    st.session_state.teams = db.get("teams", [])
    st.session_state.fixtures_a = db.get("fixtures_a", [])
    st.session_state.fixtures_b = db.get("fixtures_b", [])
    # JSON converts integer dict keys to strings; convert them back
    st.session_state.scores_a = {
        int(k): v for k, v in db.get("scores_a", {}).items()
    }
    st.session_state.scores_b = {
        int(k): v for k, v in db.get("scores_b", {}).items()
    }
    st.session_state.ko_scores = db.get(
        "ko_scores",
        {
            "playin": [None, None],
            "semi1": [None, None],
            "semi2": [None, None],
            "final": [None, None],
        },
    )
else:
    st.session_state.setup_complete = False
    st.session_state.teams = []
    st.session_state.fixtures_a = []
    st.session_state.fixtures_b = []
    st.session_state.scores_a = {}
    st.session_state.scores_b = {}
    st.session_state.ko_scores = {
        "playin": [None, None],
        "semi1": [None, None],
        "semi2": [None, None],
        "final": [None, None],
    }


def sync_to_file():
    data = {
        "setup_complete": st.session_state.setup_complete,
        "teams": st.session_state.teams,
        "fixtures_a": st.session_state.fixtures_a,
        "fixtures_b": st.session_state.fixtures_b,
        "scores_a": st.session_state.scores_a,
        "scores_b": st.session_state.scores_b,
        "ko_scores": st.session_state.ko_scores,
    }
    save_tournament_data(data)


# ---------------------------------------------------------
# SIDEBAR AUTHENTICATION & RESET
# ---------------------------------------------------------
st.sidebar.title("📲 Tournament Portal")

if st.session_state.role == "Viewer":
    st.sidebar.info("👀 **Spectator Mode** (Read-Only)")
    pin_input = st.sidebar.text_input(
        "Director PIN (To edit scores/teams):", type="password"
    )
    if st.sidebar.button("Director Login"):
        if pin_input in DIRECTOR_PINS:
            st.session_state.role = "Director"
            st.sidebar.success("Logged in as Director!")
            st.rerun()
        else:
            st.sidebar.error("Incorrect PIN")
else:
    st.sidebar.success("🔑 **Director Mode Active**")

    if st.sidebar.button("Log Out"):
        st.session_state.role = "Viewer"
        st.rerun()

    st.sidebar.divider()
    if st.sidebar.button("⚠️ Reset / Start New Tournament", type="primary"):
        if os.path.exists(DATA_FILE):
            os.remove(DATA_FILE)
        st.session_state.setup_complete = False
        st.session_state.teams = []
        st.session_state.fixtures_a = []
        st.session_state.fixtures_b = []
        st.session_state.scores_a = {}
        st.session_state.scores_b = {}
        st.session_state.ko_scores = {
            "playin": [None, None],
            "semi1": [None, None],
            "semi2": [None, None],
            "final": [None, None],
        }
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

        # Skip unplayed matches or default unentered scores
        if s1 is None or s2 is None or (s1 == 0 and s2 == 0):
            continue

        t1_name = match["t1"]["name"]
        t2_name = match["t2"]["name"]

        stats[t1_name]["Played"] += 1
        stats[t2_name]["Played"] += 1

        stats[t1_name]["Gained"] += s1
        stats[t1_name]["Conceded"] += s2
        stats[t1_name]["Diff"] += s1 - s2

        stats[t2_name]["Gained"] += s2
        stats[t2_name]["Conceded"] += s1
        stats[t2_name]["Diff"] += s2 - s1

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
    df = df.sort_values(
        by=["Points", "Diff", "Gained"], ascending=[False, False, False]
    )
    return df.reset_index(drop=True)


# ---------------------------------------------------------
# STEP 1: INITIAL SETUP & TEAM CUSTOMIZATION
# ---------------------------------------------------------
if not st.session_state.setup_complete:
    if st.session_state.role != "Director":
        st.info(
            "⏳ The tournament is being initialized by Directors. Please check back shortly!"
        )
    else:
        st.subheader("🛠️ Step 1: Generate & Customize Teams")
        default_players = "\n".join([f"Player {i+1}" for i in range(22)])
        players_text = st.text_area(
            "Enter 22 Player Names (one per line):",
            value=default_players,
            height=180,
        )

        if st.button("🔀 Step A: Auto-Generate Random Pairs"):
            player_list = [
                p.strip() for p in players_text.split("\n") if p.strip()
            ]

            if len(player_list) != 22:
                st.error(
                    f"Please enter exactly 22 player names. Current count: {len(player_list)}"
                )
            else:
                random.shuffle(player_list)

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
                st.rerun()

        # MANUAL TEAM EDITING SECTION FOR DIRECTORS
        if len(st.session_state.teams) == 11:
            st.divider()
            st.subheader("✏️ Step B: Manually Edit Teams & Roster (Optional)")
            st.caption(
                "You can rename teams or swap player names before locking in the fixtures."
            )

            col_a, col_b = st.columns(2)
            for idx, team in enumerate(st.session_state.teams):
                target_col = col_a if team["group"] == "A" else col_b
                with target_col:
                    st.markdown(
                        f"**{team['name']} (Group {team['group']})**"
                    )
                    c1, c2 = st.columns(2)
                    p1 = c1.text_input(
                        f"Team {team['id']} Player 1",
                        value=team["members"][0],
                        key=f"edit_p1_{idx}",
                    )
                    p2 = c2.text_input(
                        f"Team {team['id']} Player 2",
                        value=team["members"][1],
                        key=f"edit_p2_{idx}",
                    )
                    team["members"] = [p1, p2]

            st.divider()
            if st.button(
                "🚀 Lock Teams & Generate Schedule", type="primary"
            ):
                teams_a = [
                    t for t in st.session_state.teams if t["group"] == "A"
                ]
                teams_b = [
                    t for t in st.session_state.teams if t["group"] == "B"
                ]

                matches_a = generate_round_robin(teams_a)
                matches_b = generate_round_robin(teams_b)

                all_fixtures = matches_a + matches_b
                for idx, match in enumerate(all_fixtures):
                    match["court"] = f"Court {(idx % 4) + 1}"

                st.session_state.fixtures_a = matches_a
                st.session_state.fixtures_b = matches_b
                st.session_state.scores_a = {}
                st.session_state.scores_b = {}
                st.session_state.setup_complete = True

                sync_to_file()
                st.rerun()

# ---------------------------------------------------------
# STEP 2: PUBLIC TOURNAMENT DASHBOARD
# ---------------------------------------------------------
else:
    is_director = st.session_state.role == "Director"

    # EDIT TEAMS EXPANDER (IF DIRECTOR WANTS TO EDIT MID-TOURNAMENT)
    with st.expander("👥 Roster & Team Management", expanded=False):
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

    # LIVE STANDINGS
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

    # FIXTURES & SCORES
    st.subheader("⚔️ Matches & Court Allocation")
    col_f1, col_f2 = st.columns(2)

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
            if s1 != curr_s1 or s2 != curr_s2:
                score_dict[idx] = (s1, s2)
                sync_to_file()
                st.rerun()
        else:
            score_str = (
                f"**{curr_s1} - {curr_s2}**"
                if (curr_s1 > 0 or curr_s2 > 0)
                else "VS"
            )
            c3.write(score_str)

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

    # KNOCKOUT STAGE
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
        new_pi_s1 = col_pi2.number_input(
            "Play-in 1",
            min_value=0,
            value=pi_s1 if pi_s1 is not None else 0,
            key="pi_s1",
            label_visibility="collapsed",
        )
        new_pi_s2 = col_pi3.number_input(
            "Play-in 2",
            min_value=0,
            value=pi_s2 if pi_s2 is not None else 0,
            key="pi_s2",
            label_visibility="collapsed",
        )
        if new_pi_s1 != pi_s1 or new_pi_s2 != pi_s2:
            st.session_state.ko_scores["playin"] = [new_pi_s1, new_pi_s2]
            sync_to_file()
            st.rerun()
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
            new_sm1_s1 = cs1_2.number_input(
                "Semi1 S1",
                min_value=0,
                value=sm1_s1 if sm1_s1 is not None else 0,
                key="sm1_s1",
                label_visibility="collapsed",
            )
            new_sm1_s2 = cs1_3.number_input(
                "Semi1 S2",
                min_value=0,
                value=sm1_s2 if sm1_s2 is not None else 0,
                key="sm1_s2",
                label_visibility="collapsed",
            )
            if new_sm1_s1 != sm1_s1 or new_sm1_s2 != sm1_s2:
                st.session_state.ko_scores["semi1"] = [
                    new_sm1_s1,
                    new_sm1_s2,
                ]
                sync_to_file()
                st.rerun()
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
            new_sm2_s1 = cs2_2.number_input(
                "Semi2 S1",
                min_value=0,
                value=sm2_s1 if sm2_s1 is not None else 0,
                key="sm2_s1",
                label_visibility="collapsed",
            )
            new_sm2_s2 = cs2_3.number_input(
                "Semi2 S2",
                min_value=0,
                value=sm2_s2 if sm2_s2 is not None else 0,
                key="sm2_s2",
                label_visibility="collapsed",
            )
            if new_sm2_s1 != sm2_s1 or new_sm2_s2 != sm2_s2:
                st.session_state.ko_scores["semi2"] = [
                    new_sm2_s1,
                    new_sm2_s2,
                ]
                sync_to_file()
                st.rerun()
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
        new_f_s1 = cf_2.number_input(
            "Final S1",
            min_value=0,
            value=f_s1 if f_s1 is not None else 0,
            key="f_s1",
            label_visibility="collapsed",
        )
        new_f_s2 = cf_3.number_input(
            "Final S2",
            min_value=0,
            value=f_s2 if f_s2 is not None else 0,
            key="f_s2",
            label_visibility="collapsed",
        )
        if new_f_s1 != f_s1 or new_f_s2 != f_s2:
            st.session_state.ko_scores["final"] = [new_f_s1, new_f_s2]
            sync_to_file()
            st.rerun()
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
