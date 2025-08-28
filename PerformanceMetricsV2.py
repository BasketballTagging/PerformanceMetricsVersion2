"""
StFx Mens Basketball Tagger
Single-file Streamlit app.

How to run:
  pip install -r requirements.txt
  streamlit run app.py

requirements.txt should include:
  streamlit
  pandas
  pillow

Features:
- Required sidebar inputs: Date, Opponent, Quarter, Players, Plays.
- Add players (name + picture). Player pictures are clickable (image link).
- Add plays manually in sidebar. When tagging, each play prompts Good Read / Bad Read.
- Tags stored in session and shown in an ordered table (Date, Opponent, Quarter, Player, Play, Read).
- CSV export (download button) and local CSV save option.
"""

import streamlit as st
from PIL import Image
import io
import base64
import pandas as pd
from datetime import date
import os

st.set_page_config(page_title="StFx Mens Basketball Tagger", layout="wide")

# ---------- Helper utilities ----------
def image_file_to_base64(img_file) -> str:
    img = Image.open(img_file).convert("RGBA")
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_b64 = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/png;base64,{img_b64}"

def ensure_session():
    if "players" not in st.session_state:
        # players: list of dicts {id, name, img_b64}
        st.session_state["players"] = []
    if "plays" not in st.session_state:
        st.session_state["plays"] = []
    if "tags" not in st.session_state:
        # tags: list of dicts {date, opponent, quarter, player_name, play, read}
        st.session_state["tags"] = []
    if "game_started" not in st.session_state:
        st.session_state["game_started"] = False
    if "current_tag_player" not in st.session_state:
        st.session_state["current_tag_player"] = None

ensure_session()

# ---------- Sidebar: required pre-game inputs ----------
st.sidebar.title("Game Setup (Required)")
game_date = st.sidebar.date_input("Date", value=date.today(), key="game_date")
opponent = st.sidebar.text_input("Opponent", key="opponent")
quarter = st.sidebar.selectbox("Quarter", ["1", "2", "3", "4", "OT"], index=0)

st.sidebar.markdown("---")
st.sidebar.subheader("Manage Plays (required)")
with st.sidebar.form("add_play_form", clear_on_submit=True):
    new_play = st.text_input("Add a play label (e.g. 'Help Defense', 'Closeout')", key="new_play")
    add_play_btn = st.form_submit_button("Add Play")
if add_play_btn and new_play:
    st.session_state["plays"].append(new_play.strip())
    st.experimental_rerun()  # refresh so plays appear immediately

# show current plays and remove option
if st.session_state["plays"]:
    for i, p in enumerate(st.session_state["plays"]):
        cols = st.sidebar.columns([0.85, 0.15])
        cols[0].write(f"- {p}")
        if cols[1].button("X", key=f"delplay_{i}"):
            st.session_state["plays"].pop(i)
            st.experimental_rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("Manage Players (required)")

# Add player form
with st.sidebar.form("add_player_form", clear_on_submit=True):
    player_name = st.text_input("Player name")
    player_img = st.file_uploader("Player picture (jpg/png)", type=["png", "jpg", "jpeg"])
    submitted_player = st.form_submit_button("Add Player")
if submitted_player:
    if not player_name:
        st.sidebar.error("Player name required.")
    elif not player_img:
        st.sidebar.error("Player picture required.")
    else:
        try:
            b64 = image_file_to_base64(player_img)
            new_id = len(st.session_state["players"]) + 1
            st.session_state["players"].append({"id": new_id, "name": player_name.strip(), "img_b64": b64})
            st.sidebar.success(f"Added player: {player_name}")
            st.experimental_rerun()
        except Exception as e:
            st.sidebar.error(f"Failed to process image: {e}")

# show players & allow deletion
if st.session_state["players"]:
    st.sidebar.markdown("**Current players**")
    for i, pl in enumerate(st.session_state["players"]):
        cols = st.sidebar.columns([0.6, 0.3, 0.1])
        cols[0].text(pl["name"])
        # small preview
        cols[1].image(pl["img_b64"], width=60)
        if cols[2].button("Del", key=f"del_{i}"):
            st.session_state["players"].pop(i)
            st.experimental_rerun()

st.sidebar.markdown("---")
start_ready = st.sidebar.button("Start Tagging (All fields required)")

# ---------- Validate required fields ----------
missing = []
if not opponent:
    missing.append("Opponent")
if not st.session_state["plays"]:
    missing.append("Plays")
if not st.session_state["players"]:
    missing.append("Players")
if missing:
    st.warning(f"Before starting tagging, add: {', '.join(missing)}")
if start_ready:
    if missing:
        st.sidebar.error("Cannot start: required fields missing.")
    else:
        st.session_state["game_started"] = True
        st.sidebar.success("Tagging started! Use the player images to tag plays.")
        # ensure query params cleared
        st.experimental_set_query_params()
        st.experimental_rerun()

# ---------- Main area ----------
st.title("StFx Mens Basketball Tagger")
st.markdown("Use the player images (below) to tag plays. Plays will ask for 'Good Read' or 'Bad Read'.")
st.markdown("---")

if not st.session_state["game_started"]:
    st.info("Complete the setup in the sidebar and press **Start Tagging**.")
    # still show small preview of players
    if st.session_state["players"]:
        st.subheader("Players (preview)")
        cols = st.columns(4)
        for idx, pl in enumerate(st.session_state["players"]):
            col = cols[idx % 4]
            col.image(pl["img_b64"], use_column_width="always")
            col.caption(pl["name"])
    st.stop()

# ---------- clickable player images (image link approach) ----------
st.subheader("Tap a Player to Tag a Play")
# Build clickable images as anchors with query params. Clicking reloads the app in the same tab with ?player=<id>
player_cols = st.columns(4)
for idx, pl in enumerate(st.session_state["players"]):
    c = player_cols[idx % 4]
    # inline HTML anchor with image
    player_anchor_html = f"""
    <a href='?player={pl["id"]}' style='text-decoration:none;'>
      <div style='text-align:center; padding:6px;'>
        <img src="{pl["img_b64"]}" style='width:140px; height:140px; object-fit:cover; border-radius:12px; display:block; margin-left:auto;margin-right:auto;'>
        <div style='margin-top:6px; font-weight:600; text-align:center; color:var(--secondary-text-color);'>{pl["name"]}</div>
      </div>
    </a>
    """
    c.markdown(player_anchor_html, unsafe_allow_html=True)

# Check query params for player click
query = st.experimental_get_query_params()
if "player" in query:
    try:
        player_id = int(query["player"][0])
    except:
        player_id = None
    # find player
    selected_player = next((p for p in st.session_state["players"] if p["id"] == player_id), None)
    # clear params (so re-clicking same image will work later)
    st.experimental_set_query_params()
    if selected_player:
        st.session_state["current_tag_player"] = selected_player
    else:
        st.error("Selected player not found.")

# ---------- Tagging UI (when player selected) ----------
if st.session_state["current_tag_player"]:
    sp = st.session_state["current_tag_player"]
    st.markdown("---")
    st.subheader(f"Tagging: {sp['name']}")
    cols = st.columns([0.3, 0.7])
    cols[0].image(sp["img_b64"], width=180)
    with cols[1]:
        # Play selection
        play_choice = st.selectbox("Select Play", options=st.session_state["plays"])
        read_choice = st.radio("Read", options=["Good Read", "Bad Read"])
        notes = st.text_area("Notes (optional)", max_chars=200)
        submit_tag = st.button("Submit Tag", key=f"submit_tag_{sp['id']}")
        cancel_tag = st.button("Cancel", key=f"cancel_tag_{sp['id']}")

    if cancel_tag:
        st.session_state["current_tag_player"] = None
        st.success("Tagging cancelled.")
        st.experimental_rerun()

    if submit_tag:
        # build tag record
        tag = {
            "Date": st.session_state.get("game_date", date.today()).isoformat(),
            "Opponent": opponent,
            "Quarter": quarter,
            "Player": sp["name"],
            "Play": play_choice,
            "Read": read_choice,
            "Notes": notes,
            "RecordedAt": pd.Timestamp.now().isoformat()
        }
        st.session_state["tags"].append(tag)
        st.success(f"Tagged {sp['name']} — {play_choice} / {read_choice}")
        # clear current tag player to return to player grid
        st.session_state["current_tag_player"] = None
        st.experimental_rerun()

# ---------- Tags table & export ----------
st.markdown("---")
st.subheader("Tagged Events (in order)")
if st.session_state["tags"]:
    df = pd.DataFrame(st.session_state["tags"])
    # show only required columns in requested order (Date, Opponent, Quarter, Player, Play, Read)
    display_df = df[["Date", "Opponent", "Quarter", "Player", "Play", "Read", "Notes", "RecordedAt"]]
    st.dataframe(display_df, use_container_width=True)

    # Download as CSV
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", data=csv_bytes, file_name=f"stfx_tags_{st.session_state['game_date']}.csv", mime="text/csv")

    # Save to local CSV file option (server/local)
    if st.button("Save to local CSV (server)"):
        out_dir = "tag_outputs"
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f"stfx_tags_{st.session_state['game_date']}.csv")
        df.to_csv(out_path, index=False)
        st.success(f"Saved to {out_path}")

    # Option to clear tags
    if st.button("Clear all tags (danger)"):
        st.session_state["tags"] = []
        st.experimental_rerun()
else:
    st.info("No tags recorded yet. Tap a player image above to tag a play.")

# ---------- Small help / usage ----------
st.markdown("---")
st.info("""
**Usage tips**
- Add players and plays in the **sidebar** before starting.
- Click **Start Tagging** to enable tagging.
- Tap a player's picture to open the tagging form (image click uses a query param and reloads the page in the same tab).
- Tags are appended in order and can be downloaded as CSV for external analytics.
""")
