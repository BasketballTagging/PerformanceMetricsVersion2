import streamlit as st
import pandas as pd
from datetime import datetime
import uuid
from io import BytesIO
from PIL import Image

st.set_page_config(page_title="StFx Mens Basketball Tagger", layout="wide")

# --- Helpers -----------------------------------------------------------------

def init_state():
    if "players" not in st.session_state:
        st.session_state.players = []  # list of dicts: {id,name,image_bytes}
    if "plays" not in st.session_state:
        st.session_state.plays = []
    if "tags" not in st.session_state:
        st.session_state.tags = []  # list of tag dicts
    if "game_info" not in st.session_state:
        st.session_state.game_info = {"date": None, "opponent": "", "quarter": "1"}
    if "selected_player" not in st.session_state:
        st.session_state.selected_player = None


def add_player(name, image_file):
    image_bytes = None
    if image_file is not None:
        image_bytes = image_file.read()
    player = {"id": str(uuid.uuid4()), "name": name, "image": image_bytes}
    st.session_state.players.append(player)


def add_play(play_name):
    if play_name and play_name.strip() != "":
        st.session_state.plays.append(play_name.strip())


def create_tag(player_id, play_name, note, timestamp=None):
    if timestamp is None:
        timestamp = datetime.utcnow().isoformat()
    tag = {
        "tag_id": str(uuid.uuid4()),
        "player_id": player_id,
        "player_name": next((p["name"] for p in st.session_state.players if p["id"] == player_id), ""),
        "play": play_name,
        "note": note,
        "timestamp_utc": timestamp,
    }
    st.session_state.tags.append(tag)
    return tag


def players_df():
    rows = []
    for p in st.session_state.players:
        rows.append({"id": p["id"], "name": p["name"]})
    return pd.DataFrame(rows)


def tags_df():
    if not st.session_state.tags:
        return pd.DataFrame(columns=["tag_id", "player_id", "player_name", "play", "note", "timestamp_utc"]) 
    return pd.DataFrame(st.session_state.tags)


# --- Init --------------------------------------------------------------------
init_state()

# --- Sidebar: game setup -----------------------------------------------------
with st.sidebar:
    st.header("Game Setup (Required)")
    date = st.date_input("Game date", value=datetime.now().date())
    opponent = st.text_input("Opponent")
    quarter = st.selectbox("Quarter", ["1", "2", "3", "4", "OT"], index=0)

    st.session_state.game_info["date"] = date.isoformat()
    st.session_state.game_info["opponent"] = opponent
    st.session_state.game_info["quarter"] = quarter

    st.markdown("---")
    st.subheader("Manage Players")
    with st.form("add_player_form", clear_on_submit=True):
        pname = st.text_input("Player name", key="pname_input")
        pimg = st.file_uploader("Upload player picture (png/jpg)", type=["png", "jpg", "jpeg"], key="pimg_upload")
        submitted = st.form_submit_button("Add Player")
        if submitted:
            if not pname:
                st.warning("Please enter a player name before adding.")
            else:
                add_player(pname, pimg)
                st.success(f"Added player: {pname}")

    st.markdown("---")
    st.subheader("Manage Plays")
    with st.form("add_play_form", clear_on_submit=True):
        play_name = st.text_input("Play name", key="play_input")
        add_play_sub = st.form_submit_button("Add Play")
        if add_play_sub:
            if not play_name:
                st.warning("Please enter a play name")
            else:
                add_play(play_name)
                st.success(f"Play added: {play_name}")

    if st.session_state.plays:
        st.write("Current plays:")
        for p in st.session_state.plays:
            st.write(f"- {p}")

    st.markdown("---")
    st.subheader("Export / Save")
    if st.button("Download tags as CSV"):
        df = tags_df()
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Click to download CSV", data=csv, file_name="tags.csv", mime="text/csv")

    if st.button("Download tags as JSON"):
        df = tags_df()
        json_bytes = df.to_json(orient="records").encode("utf-8")
        st.download_button("Click to download JSON", data=json_bytes, file_name="tags.json", mime="application/json")


# --- Main layout -------------------------------------------------------------
st.title("StFx Mens Basketball Tagger")
st.write("Fill the game setup in the sidebar before tagging. Add players and plays there.")

cols = st.columns([2, 3])
left = cols[0]
right = cols[1]

# Left column: players gallery with clickable interface ---------------------------------
with left:
    st.subheader("Players")
    if not st.session_state.players:
        st.info("No players yet. Add players in the sidebar.")
    else:
        # display players in grid
        per_row = 3
        players = st.session_state.players
        for i in range(0, len(players), per_row):
            row = players[i : i + per_row]
            cols_row = st.columns(per_row)
            for col, player in zip(cols_row, row):
                with col:
                    # show image if present, else placeholder
                    if player["image"]:
                        img = Image.open(BytesIO(player["image"]))
                        st.image(img, use_column_width=True, caption=player["name"])
                    else:
                        st.write("[No image]")
                    # Clicking the image: currently implemented as button beneath the image
                    if st.button(f"Tag {player['name']}", key=f"btn_{player['id']}"):
                        st.session_state.selected_player = player["id"]

# Right column: tagging panel -------------------------------------------------
with right:
    st.subheader("Tagging Panel")
    if st.session_state.selected_player is None:
        st.info("Select a player (click the button under their picture) to start tagging.")
    else:
        pid = st.session_state.selected_player
        pname = next((p["name"] for p in st.session_state.players if p["id"] == pid), "(unknown)")
        st.markdown(f"**Selected player:** {pname}")
        with st.form("tag_form"):
            play = st.selectbox("Select play", options=st.session_state.plays if st.session_state.plays else ["No plays defined"])
            note = st.text_area("Note (optional)")
            custom_time = st.time_input("Tag time (UTC)", value=datetime.utcnow().time())
            tag_submit = st.form_submit_button("Save Tag")
            if tag_submit:
                if not st.session_state.plays:
                    st.warning("No plays defined. Add plays in the sidebar before tagging.")
                else:
                    # assemble ISO timestamp from date (game date) + custom_time
                    iso_ts = datetime.combine(datetime.fromisoformat(st.session_state.game_info["date"]).date(), custom_time).isoformat()
                    created = create_tag(pid, play, note, timestamp=iso_ts)
                    st.success(f"Tag saved: {created['play']} for {created['player_name']} at {created['timestamp_utc']}")

    st.markdown("---")
    st.subheader("Recent Tags")
    df_tags = tags_df()
    if df_tags.empty:
        st.write("No tags yet.")
    else:
        st.dataframe(df_tags.sort_values(by="timestamp_utc", ascending=False))

# --- Footer: quick actions --------------------------------------------------
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("Clear selected player"):
        st.session_state.selected_player = None
with col2:
    if st.button("Clear tags (all)"):
        st.session_state.tags = []
        st.success("All tags cleared")
with col3:
    if st.button("Reset app (clears players, plays, tags)"):
        st.session_state.players = []
        st.session_state.plays = []
        st.session_state.tags = []
        st.success("App reset")

# --- Notes for developer (displayed in app) ---------------------------------
st.sidebar.markdown("---")
st.sidebar.caption("Built for quick tagging. For true image-as-button behavior (image itself clickable), a Streamlit Component is required — I can add that on request.")

# --- End --------------------------------------------------------------------
