# stfx_mens_basketball_tagger.py
# StFx Mens Basketball Tagger
# Single-file Streamlit app ready for GitHub -> Streamlit deploy

import streamlit as st
import pandas as pd
from datetime import datetime
import io

st.set_page_config(page_title="StFx Mens Basketball Tagger", layout="wide")

# --------------------
# Session state init
# --------------------
def init_state():
    st.session_state.setdefault("players", [])  # list of dicts: {id, name, photo_bytes}
    st.session_state.setdefault("selected_player", None)
    st.session_state.setdefault("log", [])      # list of event dicts
    st.session_state.setdefault("session_meta", {})

init_state()

# --------------------
# Helpers
# --------------------

def generate_player_id(name):
    return name.strip().replace(' ', '_').lower()


def add_player(name, photo_file):
    if not name:
        st.warning("Player name required")
        return
    pid = generate_player_id(name)
    # prevent duplicate
    if any(p['id'] == pid for p in st.session_state['players']):
        st.warning("Player already exists (same name). Consider adding a number after name to differentiate.")
        return
    photo_bytes = photo_file.read() if photo_file is not None else None
    st.session_state['players'].append({"id": pid, "name": name.strip(), "photo": photo_bytes})
    st.success(f"Added player: {name}")


def log_tag(player_id, player_name, meta, outcome, notes=""):
    event = {
        "timestamp_utc": datetime.utcnow().isoformat(),
        "session_date": meta.get('date'),
        "opponent": meta.get('opponent'),
        "quarter": meta.get('quarter'),
        "player_id": player_id,
        "player_name": player_name,
        "outcome": outcome,
        "notes": notes,
    }
    st.session_state['log'].append(event)


def players_ready():
    return len(st.session_state['players']) > 0

# --------------------
# Sidebar: Session context + Roster
# --------------------
with st.sidebar.expander("Game / Session Context (required)", expanded=True):
    st.markdown("**Enter session details before tagging.**")
    s_date = st.date_input("Date", key="meta_date")
    s_opponent = st.text_input("Opponent", key="meta_opponent")
    s_quarter = st.selectbox("Quarter", options=["1","2","3","4","OT"], index=0, key="meta_quarter")

    # Save meta
    st.session_state['session_meta'] = {
        'date': s_date.isoformat(),
        'opponent': s_opponent.strip(),
        'quarter': s_quarter,
    }

    st.markdown("---")
    st.markdown("### Add player to roster (name + photo)")
    with st.form("add_player_form", clear_on_submit=True):
        p_name = st.text_input("Player name (e.g. John Doe #12)")
        p_photo = st.file_uploader("Player photo (PNG/JPG)", type=["png","jpg","jpeg"], help="Photo will be used as a touch-friendly button")
        add_sub = st.form_submit_button("Add player")
        if add_sub:
            add_player(p_name, p_photo)

    st.markdown("---")
    st.markdown("#### Current roster")
    if players_ready():
        for p in st.session_state['players']:
            cols = st.columns([1,3])
            with cols[0]:
                if p['photo']:
                    st.image(p['photo'], width=64)
                else:
                    st.write("🖼️")
            with cols[1]:
                st.write(p['name'])
    else:
        st.info("No players yet — add players (name + photo) before tagging")

# --------------------
# Main area
# --------------------
st.title("StFx Mens Basketball Tagger")
st.write("Quick, touch-friendly tagging for reads during practice.\n\n**Workflow:** add session context in the left sidebar, add players with photos, then tap a player photo to tag a 'Good Read' or 'Bad Read'. All tags are collected in a table and can be downloaded as CSV.")

# Validate required session inputs
if not st.session_state['session_meta'].get('opponent'):
    st.warning("Please enter the Opponent in the sidebar to proceed.")
    st.stop()

if not players_ready():
    st.warning("Please add at least one player (name + photo) in the sidebar roster to proceed.")
    st.stop()

# Display player photo buttons in a responsive grid
st.subheader("Tap a player to tag")
players = st.session_state['players']
cols_per_row = 4
rows = (len(players) + cols_per_row - 1) // cols_per_row
for r in range(rows):
    cols = st.columns(cols_per_row)
    for c in range(cols_per_row):
        idx = r * cols_per_row + c
        if idx >= len(players):
            cols[c].empty()
            continue
        p = players[idx]
        # Show image (large) then a button underneath
        if p['photo']:
            cols[c].image(p['photo'], use_column_width='always')
        else:
            cols[c].write("No image")
        # big button for touch
        if cols[c].button(p['name'], key=f"player_btn_{p['id']}"):
            st.session_state['selected_player'] = p['id']
            st.experimental_rerun()

# If a player selected, show play buttons
if st.session_state.get('selected_player'):
    selected = next((x for x in players if x['id'] == st.session_state['selected_player']), None)
    if selected:
        st.markdown("---")
        st.subheader(f"Tagging: {selected['name']}")
        st.write("Choose the read outcome below. Add optional notes then save the tag.")
        notes = st.text_area("Notes (optional)", key="tag_notes")
        col1, col2, col3 = st.columns([1,1,2])
        if col1.button("Good Read", key="good_read"):
            log_tag(selected['id'], selected['name'], st.session_state['session_meta'], "Good Read", notes)
            st.success(f"Logged Good Read for {selected['name']}")
            # reset selection and notes
            st.session_state['selected_player'] = None
            st.session_state['tag_notes'] = ''
            st.experimental_rerun()
        if col2.button("Bad Read", key="bad_read"):
            log_tag(selected['id'], selected['name'], st.session_state['session_meta'], "Bad Read", notes)
            st.success(f"Logged Bad Read for {selected['name']}")
            st.session_state['selected_player'] = None
            st.session_state['tag_notes'] = ''
            st.experimental_rerun()
        if col3.button("Cancel", key="tag_cancel"):
            st.session_state['selected_player'] = None
            st.session_state['tag_notes'] = ''
            st.experimental_rerun()

# Show log table and export
st.markdown("---")
st.subheader("Session tags")
if st.session_state['log']:
    df = pd.DataFrame(st.session_state['log'])
    # show a friendly table
    st.dataframe(df.astype(str))
    # CSV export
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("Download tags as CSV", data=csv, file_name=f"stfx_tags_{st.session_state['session_meta'].get('date')}.csv", mime='text/csv')
else:
    st.info("No tags logged yet — tap a player photo, choose Good Read or Bad Read to start logging.")

# Footer instructions
st.markdown("---")
st.caption("Built for quick practice tagging — let me know if you want: auto-timestamp sync with video, extra tag types, or per-player dashboards.")

