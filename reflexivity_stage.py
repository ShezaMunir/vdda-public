"""
reflexivity_stage.py
════════════════════
Stage 5 — Positionality Reflection

Place this file in the same directory as pilot_study.py.
See the bottom of this file for the exact 5 changes needed in pilot_study.py.
"""

import json
import random
import streamlit as st


# ── GCS loader ────────────────────────────────────────────────────────────────

def load_other_completed_sessions(bucket, current_prolific: str, scenario_id: str) -> list[dict]:
    """
    Returns all annotation records from COMPLETE.json files of *other* participants
    in the same scenario. Skips the current participant's own folder.
    """
    all_annotations = []
    try:
        blobs = list(bucket.list_blobs(prefix="sessions/"))
        for blob in blobs:
            if not blob.name.endswith("COMPLETE.json"):
                continue
            if f"sessions/{current_prolific}/" in blob.name:
                continue  # skip own file
            try:
                content = json.loads(blob.download_as_text())
                if content.get("scenario_id") != scenario_id:
                    continue
                for ann in content.get("annotations", []):
                    all_annotations.append(ann)
            except Exception:
                continue
    except Exception:
        pass
    return all_annotations


# ── Disagreement card builder ─────────────────────────────────────────────────

def build_disagreement_cards(
    my_annotations: list[dict],
    all_other_annotations: list[dict],
    max_posts: int = 3,
    max_others_per_post: int = 3,
) -> list[dict]:
    """
    For each annotated post, find other participants who chose a different label.

    Returns up to max_posts cards in natural study order.
    Posts where nobody disagreed are skipped.
    If a post has more than max_others_per_post disagreers, a random sample is shown.

    Each card:
      {
        "datapoint_id": str,
        "tweet_text": str,
        "my_label": str,
        "my_rationale": str,
        "others": [{"label": str, "rationale": str}, ...]   # max 3, anonymised
      }
    """
    others_by_dp: dict[str, list[dict]] = {}
    for ann in all_other_annotations:
        dp_id = ann.get("datapoint_id")
        if dp_id:
            others_by_dp.setdefault(dp_id, []).append(ann)

    cards = []
    for my_ann in my_annotations:
        dp_id        = my_ann.get("datapoint_id", "")
        my_label     = my_ann.get("participant_label", "")
        my_rationale = my_ann.get("rationale", "")
        tweet_text   = my_ann.get("tweet_text", "")

        disagreers = [
            o for o in others_by_dp.get(dp_id, [])
            if o.get("participant_label") != my_label
        ]

        if not disagreers:
            continue

        if len(disagreers) > max_others_per_post:
            disagreers = random.sample(disagreers, max_others_per_post)

        cards.append({
            "datapoint_id":  dp_id,
            "tweet_text":    tweet_text,
            "my_label":      my_label,
            "my_rationale":  my_rationale,
            "others": [
                {
                    "label":    o.get("participant_label", ""),
                    "rationale": o.get("rationale", ""),
                }
                for o in disagreers
            ],
        })

        if len(cards) >= max_posts:
            break

    return cards


# ── Stage renderer ────────────────────────────────────────────────────────────

def render_reflexivity_stage(data: dict, GCS_BUCKET: str, get_gcs_client,
                              save_complete_to_gcs, render_word_counter, prog):
    """
    Call from main() as:

        elif stage == "reflexivity":
            from reflexivity_stage import render_reflexivity_stage
            render_reflexivity_stage(
                data, GCS_BUCKET, get_gcs_client,
                save_complete_to_gcs, render_word_counter, prog,
            )
    """
    MIN_WORDS = 80

    st.markdown("<div class='step-label'>Step 5 of 5 — Reflection</div>", unsafe_allow_html=True)
    st.title("Your perspective, in context")
    prog(9, 10)  # 90%

    st.write(
        "Before you finish, we'd like you to reflect on the annotations you just made. "
        
    )

    # ── Load & cache disagreement cards ──────────────────────────────────────
    if "reflex_cards" not in st.session_state:
        with st.spinner("Loading other participants' annotations…"):
            try:
                gcs      = get_gcs_client()
                bucket   = gcs.bucket(GCS_BUCKET)
                prolific = data.get("prolific_pid") or data["participant_id"]
                other_anns = load_other_completed_sessions(
                    bucket, prolific, data["scenario_id"]
                )
                cards = build_disagreement_cards(data["annotations"], other_anns)
            except Exception:
                cards = []
        st.session_state["reflex_cards"] = cards

    cards = st.session_state["reflex_cards"]

    # ── Render cards ──────────────────────────────────────────────────────────
    if cards:
        st.markdown(
            f"**{len(cards)} post{'s' if len(cards) != 1 else ''} "
            f"where your reading differed from at least one other participant:**"
        )
        for card in cards:
            st.markdown(
                f"<div class='tweet-card'>{card['tweet_text']}</div>",
                unsafe_allow_html=True,
            )
            # Other participants first
            for i, other in enumerate(card["others"], 1):
                st.markdown(
                    f"<span class='meta-pill'>Person {i}</span>&nbsp;&nbsp;"
                    f"**{other['label']}**",
                    unsafe_allow_html=True,
                )
                if other["rationale"].strip():
                    st.caption(f"*\"{other['rationale']}\"*")
            # Current participant last, visually distinct
            st.markdown(
                f"<span class='meta-pill' style='background:#3A2A1A;color:#E8C87A;"
                f"border:1px solid #8B6F47;'>You</span>&nbsp;&nbsp;**{card['my_label']}**",
                unsafe_allow_html=True,
            )
            if card["my_rationale"].strip():
                st.caption(f"*\"{card['my_rationale']}\"*")
            st.markdown("---")
    else:
        # st.info(
        #     "Your labels were closely aligned with other participants across all the posts you annotated."
        # )
        st.markdown("---")

    # ── Static reflection prompt ──────────────────────────────────────────────
    if cards:
        st.markdown(
            "*Looking at the posts and rationales above, where your reading differed from others' — "
            "what aspects of your background, experiences, or values do you think shaped "
            "how you read these differently? There are no right or wrong answers here. "
            "We're interested in the connection between who you are and how you annotate.*"
        )
    else:
        st.markdown(
            "What aspects of your background, "
            "experiences, or values do you think shaped how you read and label this content? "
            "There are no right or wrong answers.*"
        )

    st.markdown(f"**Your reflection** *(minimum {MIN_WORDS} words)*")
    st.caption("Write freely — your perspective is the data.")

    reflection = st.text_area(
        "",
        height=220,
        label_visibility="collapsed",
        key="reflexivity_text",
    )
    render_word_counter(reflection, MIN_WORDS)

    st.markdown("---")

    if st.button("Submit & finish →", type="primary"):
        word_count = len(reflection.strip().split()) if reflection.strip() else 0
        if word_count < MIN_WORDS:
            st.warning(
                f"Your reflection is {word_count} words. "
                f"Please expand to at least {MIN_WORDS} words — "
                "the detail you provide is the most valuable part of this final step."
            )
        else:
            data["reflexivity_response"]    = reflection
            data["reflexivity_cards_shown"] = [
                {
                    "datapoint_id":  c["datapoint_id"],
                    "tweet_text":    c["tweet_text"],
                    "my_label":      c["my_label"],
                    "my_rationale":  c["my_rationale"],
                    "others_count":  len(c["others"]),
                    "others":        c["others"],  # labels + rationales only, no prolific IDs
                }
                for c in cards
            ]
            with st.spinner("Saving your responses securely…"):
                try:
                    save_complete_to_gcs(data)
                    data["workflow_stage"] = "complete"
                    st.session_state.pdata = data
                    for key in ["reflex_cards"]:
                        st.session_state.pop(key, None)
                    st.rerun()
                except Exception as e:
                    st.error(
                        "Failed to save your responses. Please leave this window open "
                        f"and contact the researcher. Error: {e}"
                    )


# ══════════════════════════════════════════════════════════════════════════════
# CHANGES REQUIRED IN pilot_study.py  (5 edits)
# ══════════════════════════════════════════════════════════════════════════════
#
# 1. ADD IMPORT — after the existing imports:
#
#        from reflexivity_stage import render_reflexivity_stage
#
#
# 2. ADD FIELDS in init_participant() — in the returned dict:
#
#        "reflexivity_response":    "",
#        "reflexivity_cards_shown": [],
#
#
# 3. ADD FIELDS in save_complete_to_gcs() — in the `final` dict:
#
#        "reflexivity_response":    data.get("reflexivity_response", ""),
#        "reflexivity_cards_shown": data.get("reflexivity_cards_shown", []),
#
#
# 4. ADD LABEL in the sidebar — in the `labels` dict:
#
#        "reflexivity": "5 — Reflect",
#
#
# 5. REPLACE the annotation completion `else:` block (around line 1071)
#
#    OLD:
#        else:
#            with st.spinner("Saving your responses securely…"):
#                try:
#                    save_complete_to_gcs(data)
#                    data["workflow_stage"] = "complete"
#                    st.session_state.pdata = data
#                    st.rerun()
#                except Exception as e:
#                    st.error(
#                        "Failed to save your responses. Please leave this window open "
#                        "and contact the researcher."
#                        f"Error: {e}"
#                    )
#
#    NEW:
#        else:
#            data["workflow_stage"] = "reflexivity"
#            st.session_state.pdata = data
#            st.rerun()
#
#    AND add this block immediately BEFORE `elif stage == "complete":`:
#
#        elif stage == "reflexivity":
#            render_reflexivity_stage(
#                data, GCS_BUCKET, get_gcs_client,
#                save_complete_to_gcs, render_word_counter, prog,
#            )
#
# ══════════════════════════════════════════════════════════════════════════════
