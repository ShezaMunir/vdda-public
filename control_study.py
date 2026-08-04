"""
control_study.py -- Ambiguous Hate Speech Annotation Study (No-Elicitation Control Arm)
Researcher: Sheza Munir

CONTROL ARM DESIGN NOTES (not shown to participants):
  This is the baseline descriptive annotation condition.
  Identical to pilot_study.py EXCEPT:
    1. Stages 2 (elicitation_chat) and 3 (synthesis/micronarrative) are removed.
    2. Workflow is: annotation → disclosure → reflexivity → complete.
    3. The study intro does NOT mention positionality or lived experience shaping annotation.
    4. The narrative expander in annotation is hidden (no micronarrative was produced).
    5. condition = "no_elicitation" is stored in every participant record.
  Everything else -- label taxonomy, rationale prompt, salience slider, reflexivity stage --
  is identical to the treatment arm. This ensures the only difference is elicitation activation.
  Per Röttger et al. (2022): both arms are descriptive-paradigm annotation.
  The comparison is latent positionality (control) vs. activated positionality (treatment).
"""

import streamlit as st
import json
import random
from datetime import datetime
from huggingface_hub import InferenceClient
import os
from google.cloud import storage
from google.oauth2 import service_account
import uuid
from reflexivity_stage import render_reflexivity_stage

# ─── Config ───────────────────────────────────────────────────────────────────

try:
    HF_TOKEN = st.secrets["HF_TOKEN"]
except KeyError:
    HF_TOKEN = os.environ.get("HF_TOKEN", "INSERT_HF_TOKEN_HERE")

client = InferenceClient(api_key=HF_TOKEN)

# SHEET_URL = "https://docs.google.com/spreadsheets/d/1xAvNGAvny-1uCS2s2Iw4ij5OG1gF1LjKAdbLlcDnAkM/edit"
GCS_BUCKET = st.secrets["gcs_config"]["bucket_name"]

@st.cache_resource
def get_gcs_client():
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcs"],
        scopes=["https://www.googleapis.com/auth/devstorage.read_write"]
    )
    return storage.Client(credentials=credentials)

MIN_RATIONALE_WORDS = 50

# ─── Dataset ──────────────────────────────────────────────────────────────────
# Source: Munir (2024) Ambiguous Hate Speech Dataset.
# Domain: IMM = Immigration/Nativism, REL = Religion, GEN = Gender/Sexuality, INT = Intersectional.
# All items satisfy C1-C4 of the ambiguity codebook (surface plausible deniability,
# experiential divergence, discourse embeddedness, no explicit derogation).

DATAPOINTS = [
    # ── Scenario A: Borders, Safety & Who Belongs ──────────────────────────────
    # Theme: nativist plausible-deniability framing, demographic anxiety, rule-of-law rhetoric.
    # High C2 divergence: in-group (immigrant/minority) vs. out-group readings diverge substantively.
    {"id": "A01", "scenario": "A", "domain": "IMM",
     "text": "Our hospitals can't keep up. At some point we have to ask who this country is actually for."},
    {"id": "A02", "scenario": "A", "domain": "IMM",
     "text": "My grandparents came here legally and waited years. Why should anyone get to skip that line?"},
    {"id": "A03", "scenario": "A", "domain": "IMM",
     "text": "When you flood a labor market, wages go down. Economics doesn't care about feelings."},
    {"id": "A04", "scenario": "A", "domain": "IMM",
     "text": "There's nothing wrong with wanting your hometown to stay recognizable."},
    {"id": "A05", "scenario": "A", "domain": "IMM",
     "text": "Demographic change at this pace isn't natural. Someone is choosing this."},
    {"id": "A06", "scenario": "A", "domain": "IMM",
     "text": "Chain migration turns one visa into fifty. That's not the deal Americans signed up for."},
    {"id": "A07", "scenario": "A", "domain": "IMM",
     "text": "Every nation has the right to exist as a distinct people. Even European ones."},
    {"id": "A08", "scenario": "A", "domain": "IMM",
     "text": "We keep importing poverty and then wonder why poverty doesn't go away."},
    {"id": "A09", "scenario": "A", "domain": "IMM",
     "text": "Western countries are the only ones expected to dissolve their own majorities."},
    {"id": "A10", "scenario": "A", "domain": "IMM",
     "text": "The people most affected by immigration policy are the working class, not politicians."},

    # ── Scenario B: Religion, Culture & the Politics of Belonging ──────────────
    # Theme: religious double-standards, secular liberal framing, epistemic proximity.
    # High C2 divergence: Muslim/religious minority annotators read threat-coding invisible to others.
    {"id": "B01", "scenario": "B", "domain": "REL",
     "text": "I support religious freedom, but some belief systems just aren't compatible with liberal democracy. That's not bigotry, it's observation."},
    {"id": "B02", "scenario": "B", "domain": "REL",
     "text": "We accommodate every faith's dietary rules in schools now. At some point you have to ask whose schools these are."},
    {"id": "B03", "scenario": "B", "domain": "REL",
     "text": "I have no problem with people praying five times a day. I do have a problem when it starts affecting workplace schedules for everyone else."},
    {"id": "B04", "scenario": "B", "domain": "REL",
     "text": "There's a reason the Enlightenment happened in one part of the world and not others. That's not racism, it's history."},
    {"id": "B05", "scenario": "B", "domain": "REL",
     "text": "If a Christian baker refusing a gay wedding is front-page news, why isn't a halal butcher refusing to serve a non-Muslim customer?"},
    {"id": "B06", "scenario": "B", "domain": "REL",
     "text": "Secularism means no religion gets special status. That includes the ones progressives have decided are beyond criticism."},
    {"id": "B07", "scenario": "B", "domain": "INT",
     "text": "Immigrant communities often hold the most conservative views on gender. The left just doesn't want to say that out loud."},
    {"id": "B08", "scenario": "B", "domain": "INT",
     "text": "Gay rights were won by fighting religious conservatism. Now we're importing more of it and calling it diversity."},
    {"id": "B09", "scenario": "B", "domain": "INT",
     "text": "Female genital mutilation is illegal here. Calling attention to where it's practiced is not Islamophobia."},
    {"id": "B10", "scenario": "B", "domain": "INT",
     "text": "The same activists who say believe all women go very quiet when the accused is from a protected group."},

    # ── Scenario C: Gender, Identity & Whose Experience Counts ────────────────
    # Theme: gender essentialism, weaponized empiricism, concern-trolling, intersectional erasure.
    # C2 divergence fractured: trans/NB, cisgender feminist, and non-feminist readers diverge.
    {"id": "C01", "scenario": "C", "domain": "GEN",
     "text": "I believe women. I also believe due process. These shouldn't be mutually exclusive."},
    {"id": "C02", "scenario": "C", "domain": "GEN",
     "text": "Calling everything a 'microaggression' doesn't empower women. It treats them like they can't handle everyday life."},
    {"id": "C03", "scenario": "C", "domain": "GEN",
     "text": "There are two genders. I'm sorry if that's hurtful, but being hurtful isn't the same as being wrong."},
    {"id": "C04", "scenario": "C", "domain": "GEN",
     "text": "If gender is a social construct, then so is the wage gap. You can't have it both ways."},
    {"id": "C05", "scenario": "C", "domain": "GEN",
     "text": "Women's sports existed to give women a fair playing field. That's it. That's the whole point."},
    {"id": "C06", "scenario": "C", "domain": "GEN",
     "text": "Men aren't broken women. Treating masculinity as a pathology isn't progressivism, it's prejudice with better vocabulary."},
    {"id": "C07", "scenario": "C", "domain": "INT",
     "text": "When a working-class white man loses a job to a diversity hire, he's not allowed to be angry. That anger has to go somewhere."},
    {"id": "C08", "scenario": "C", "domain": "INT",
     "text": "Intersectionality is just a hierarchy that puts some victims above others. It's oppression with extra steps."},
    {"id": "C09", "scenario": "C", "domain": "INT",
     "text": "First-generation immigrant women are often the most opposed to feminism. Nobody ever asks them why."},
    {"id": "C10", "scenario": "C", "domain": "INT",
     "text": "We have a word for communities where women can't leave the house without permission. We're just not allowed to use it anymore."},
]

# ─── Scenarios ────────────────────────────────────────────────────────────────

SCENARIOS = [
    {
        "id": "A",
        "theme": "Borders, Safety & Who Belongs",
        "vignette": (
            "A local community board is holding a heated town hall meeting about a proposed temporary "
            "housing facility for undocumented migrants. Outside the building, two groups have gathered. "
            "One group holds signs demanding strict border enforcement, shouting that the town must "
            "prioritize local safety and resources first. The other group is distributing hot tea and "
            "holding banners that read 'No one is illegal.' As everyday residents walk past the crowd "
            "to get to the grocery store next door, the tension in the air is palpable, forcing everyone "
            "to silently choose a side, engage, or just keep their heads down."
        ),
        "elicitation_focus": "personal safety, national identity, belonging, or community ties",
        "datapoint_ids": ["A01","A02","A03","A04","A05","A06","A07","A08","A09","A10"],
        "opening_q": (
            "Reading through that passage -- what stands out to you first? "
            "Is there something you connect with on a personal level, or something that feels distant?"
        ),
    },
    {
        "id": "B",
        "theme": "Religion, Culture & the Politics of Belonging",
        "vignette": (
            "A popular local bakery posts a photo celebrating a religious holiday that is not widely "
            "observed by the majority of the town. Within hours, a prominent local figure screenshots "
            "the post, claiming the bakery is 'erasing our traditional culture' and promoting dangerous "
            "ideologies. Followers flood the bakery's page with hostile reviews and calls for a boycott. "
            "In response, a coalition of neighbourhood residents organises a 'buy-out' day, lining up "
            "around the block to purchase pastries, hoping to drown out the hostility with a highly "
            "visible show of support and solidarity."
        ),
        "elicitation_focus": "cultural identity, religious belonging, dignity, or what 'home' means",
        "datapoint_ids": ["B01","B02","B03","B04","B05","B06","B07","B08","B09","B10"],
        "opening_q": (
            "Reading through that passage -- what stands out to you first? "
            "Is there something that resonates personally, or something that feels uncomfortable or foreign?"
        ),
    },
    {
        "id": "C",
        "theme": "Gender, Identity & Whose Experience Counts",
        "vignette": (
            "A university student forum erupts after a well-known professor publishes an op-ed arguing "
            "that 'identity politics has gone too far' and that certain protected categories now receive "
            "more institutional sympathy than others. The comments split immediately: some students share "
            "personal accounts of discrimination they say went unacknowledged, while others post "
            "screenshots of what they describe as reverse bias in hiring and disciplinary processes. "
            "Amidst the heated exchanges, one student reflects on their own experiences with marginalization but it drowns out in a sea of opinions."

        ),
        "elicitation_focus": "identity, fairness, visibility, belonging, or feeling counted",
        "datapoint_ids": ["C01","C02","C03","C04","C05","C06","C07","C08","C09","C10"],
        "opening_q": (
            "Reading through that passage -- what stands out to you first? "
            "Is there a moment, a feeling, or a person in it you find yourself drawn to?"
        ),
    },
]

# ─── Storage ──────────────────────────────────────────────────────────────────




def init_participant(prolific_pid=None, study_id=None, session_id=None) -> dict:
    return {
        "participant_id": str(uuid.uuid4()),
        "prolific_pid": prolific_pid,
        "prolific_study_id": study_id,
        "prolific_session_id": session_id,
        "created_at": datetime.utcnow().isoformat(),
        "condition": "no_elicitation",           # ← control arm marker
        "scenario_id": "C", 
        "workflow_stage": "annotation",
        "disclosure": {},
        "elicitation": [],                        # always empty in control arm
        "micronarrative": "",                     # always empty in control arm
        "annotations": [],
        "consented_at": datetime.utcnow().isoformat(),
        "reflexivity_response":     "",
        "reflexivity_cards_shown":  [],
    }

def get_scenario(sid: str) -> dict:
    return next(s for s in SCENARIOS if s["id"] == sid)

def get_datapoints(sid: str) -> list:
    ids = set(get_scenario(sid)["datapoint_ids"])
    return [d for d in DATAPOINTS if d["id"] in ids]

# ─── LLM ──────────────────────────────────────────────────────────────────────

def call_qwen(system_prompt: str, messages: list, max_tokens: int = 200) -> str:
    if HF_TOKEN == "INSERT_HF_TOKEN_HERE":
        return "[Set HF_TOKEN to enable the AI interviewer -- see README.]"
    formatted_messages = [{"role": "system", "content": system_prompt}] + messages
    try:
        response = client.chat_completion(
            model="Qwen/Qwen2.5-7B-Instruct",
            messages=formatted_messages,
            max_tokens=max_tokens,
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[Model temporarily unavailable: {e}. Please try again.]"


AXES_CONTEXT = """\
You are conducting a qualitative lived-experience elicitation as part of an academic study on annotation and positionality. \
The participant has just read a scenario. Your job is to draw out their personal relationship to the themes in it - \
not their opinions about the scenario, but their lived experience that shapes how they would read and interpret it.

The seven lived-experience axes below are lenses. Work through them across the conversation. \
Do NOT name them or list them -- use them invisibly:

  A. Sociocultural & geographic context -- where they grew up, cultural norms, value systems
  B. Linguistic background -- native language, code-switching, dialect, how they navigate registers
  C. Socioeconomic & labor -- class, economic precarity, workplace power dynamics
  D. Race & ethnicity -- racial identity, marginalization, how others perceive them
  E. Gender & sexuality -- lived gender/sexuality, how systems categorize them
  F. Disability & neurodivergence -- physical, cognitive, sensory experience; what 'normal' excludes
  G. Epistemic proximity -- how personally close they are to the people most affected by this scenario

CORE RULES -- apply every single turn:
- Ask exactly ONE question. If you feel the urge to ask two, cut the second one.
- 1-2 sentences maximum. No affirmations ('great', 'thank you', 'I see'). No summaries of what they said.
- Never paraphrase their answer back to them.
- Anchor every question to something specific they actually said -- never ask generically.
- If their last answer was thin (fewer than ~15 words), do NOT pivot to a new axis. Stay with the same thread and ask for a concrete example or memory.
- Move to a new axis only when you have substantive material on the current one.\
"""

def _axes_covered(elicitation: list) -> list[str]:
    """Heuristically identify which axes have been touched based on conversation content."""
    axes = {
        "A": ["grew up", "country", "city", "culture", "community", "hometown", "background", "where"],
        "B": ["language", "dialect", "english", "accent", "translate", "speak", "words"],
        "C": ["work", "job", "money", "class", "afford", "wage", "labor", "income", "economic"],
        "D": ["race", "racial", "ethnic", "skin", "minority", "discriminat", "immigrant", "foreign"],
        "E": ["gender", "woman", "man", "trans", "queer", "gay", "sexual", "she", "he", "they"],
        "F": ["disab", "chronic", "illness", "neurodiv", "adhd", "autism", "mental health", "pain"],
        "G": ["know someone", "personally", "my family", "close to", "affect me", "my own", "i've experienced"]
    }
    user_text = " ".join(
        m["content"].lower() for m in elicitation if m["role"] == "user"
    )
    covered = []
    for axis, keywords in axes.items():
        if any(kw in user_text for kw in keywords):
            covered.append(axis)
    return covered


def elicitation_sys(scenario: dict, user_turns: int, last_user: str = "", elicitation: list = None) -> str:
    if elicitation is None:
        elicitation = []

    covered = _axes_covered(elicitation)
    uncovered = [a for a in ["A", "B", "C", "D", "E", "F", "G"] if a not in covered]
    last_clean = last_user.strip()
    is_thin = len(last_clean.split()) <= 12

    # Build axis guidance for next question
    axis_labels = {
        "A": "sociocultural/geographic background",
        "B": "linguistic background or code-switching",
        "C": "class, labor, or economic experience",
        "D": "race, ethnicity, or experiences of marginalization",
        "E": "gender identity or sexuality",
        "F": "disability, chronic illness, or neurodivergence",
        "G": "how personally close they are to the people most affected"
    }

    p = f"{AXES_CONTEXT}\n\nSCENARIO the participant read:\n\"{scenario['vignette']}\"\n\n"
    p += f"Axes covered so far (based on conversation): {', '.join(covered) if covered else 'none yet'}\n"
    p += f"Axes not yet touched: {', '.join(uncovered) if uncovered else 'all covered'}\n\n"

    if user_turns == 1:
        p += (
            "TURN 1 -- OPENING:\n"
            "The participant just gave their first response. Pick the single most specific or emotionally "
            "loaded thing they said. Ask one question that connects it to their personal history -- "
            "where they're from, who they are, or how they relate to the people in the scenario. "
            "Axis A, D, or G are natural starting points. Stay concrete and personal."
        )

    elif is_thin:
        p += (
            f"REPAIR TURN -- the participant's last response was very short: \"{last_clean}\"\n"
            "Do not move to a new axis. Ask them to ground what they said in a specific moment, "
            "memory, or example from their own life. Stay on the same thread -- just go one level deeper."
        )

    elif user_turns <= 3:
        if uncovered:
            next_axis = uncovered[0]
            p += (
                f"TURN {user_turns} -- BROADEN:\n"
                f"You have good material from the current thread. Now open a new dimension. "
                f"The next untouched axis is {next_axis} ({axis_labels[next_axis]}). "
                f"Find a natural bridge from what they just said: \"{last_clean[:200]}\" "
                f"to ask about {axis_labels[next_axis]}. Don't announce the topic change -- "
                f"make the question feel like a natural follow from what they shared."
            )
        else:
            p += (
                f"TURN {user_turns} -- DEEPEN:\n"
                f"All major axes have been touched. Go deeper on the one that feels richest. "
                f"Ask: what made that experience personally significant -- not just what happened, "
                f"but what it revealed about how they see themselves in situations like this one. "
                f"Anchor to: \"{last_clean[:200]}\""
            )

    elif user_turns == 4:
        p += (
            "TURN 4 -- INTEGRATION:\n"
            "You are approaching the end. Ask one question that invites the participant to connect "
            "the threads -- how does their background, identity, or experience shape the lens "
            "through which they would read content like this scenario? Keep it open and gentle. "
            "Do NOT repeat a question type you've already asked.\n\n"
            "STOPPING CONDITION: If the participant has shared enough across the conversation "
            "to support a coherent 4-5 sentence narrative covering at least 3 axes, "
            "end your response with the exact text: READY_TO_BUILD"
        )

    elif user_turns >= 5:
        p += (
            "FINAL TURN -- CRITICAL OVERRIDE:\n"
            "Do NOT ask any question. Thank the participant warmly in exactly one sentence. "
            "You MUST end your response with the exact text: READY_TO_BUILD"
        )

    return p


SYNTHESIS_SYS = """\
Write a first-person narrative (minimum 120 words) that faithfully captures what this participant shared.

Rules:
- Use 'I' throughout.
- Preserve the participant's own specific words and phrases wherever possible -- do not sanitise their voice.
- Do NOT add feelings, interpretations, or experiences they did not express.
- Cover at least three distinct dimensions of lived experience (e.g. cultural background, personal memory, \
emotional response, sense of identity or belonging, relationship to the community depicted).
- The narrative should read as a coherent, flowing piece of personal reflection -- not a bullet list or summary.
- Friendly, natural, warm tone -- not clinical or academic.
- Do not include a title or preamble. Output ONLY the narrative text.\
"""

# ─── Styles ───────────────────────────────────────────────────────────────────

def inject_styles():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,500;1,400&family=IBM+Plex+Sans:wght@300;400;500&display=swap');
    html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; background: #000000 !important; color: #F0F0F0 !important; }
    h1, h2 { font-family: 'Lora', serif; font-weight: 400; letter-spacing: -0.01em; }
    .stApp { background: #000000; }
    .stTextInput input, .stTextArea textarea, [data-testid="stChatInput"] {
        background-color: #222222 !important;
        border: 1px solid #444444 !important;
        color: #F0F0F0 !important;
        border-radius: 8px !important;
    }
    .vignette-card {
        background: #EEEAE0; border-left: 4px solid #8B6F47;
        padding: 1.2rem 1.5rem; border-radius: 3px; margin: 1rem 0 1.4rem 0;
        font-size: 0.96rem; line-height: 1.85; color: #2A2A2A; font-style: italic;
    }
    .tweet-card {
        background: #111111;
        border: 1px solid #2A2A2A;
        border-radius: 10px;
        padding: 1.2rem 1.4rem;
        font-size: 1rem;
        line-height: 1.7;
        color: #EAEAEA;
        box-shadow: 0 2px 8px rgba(0,0,0,0.6);
        margin-bottom: 1.2rem;
    }
    .meta-pill {
        display: inline-block;
        background: #222;
        border-radius: 12px;
        font-size: 0.7rem;
        padding: 3px 10px;
        color: #B5B5B5;
        margin-right: 6px;
    }
    .prog-bg { background: #2A2A2A; border-radius: 20px; height: 5px; margin: 0.4rem 0 1.4rem 0; }
    .prog-fill { background: #8B6F47; height: 5px; border-radius: 20px; }
    .step-label { font-size: 0.71rem; color: #999; letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 0.2rem; }
    div[data-testid="stChatMessage"] { background: transparent !important; }
    .word-counter-ok { color: #6FCF97; font-size: 0.8rem; margin-top: 4px; }
    .word-counter-low { color: #EB5757; font-size: 0.8rem; margin-top: 4px; }
    .chat-replay {
        background: #0D0D0D;
        border: 1px solid #2A2A2A;
        border-radius: 8px;
        padding: 1rem 1.2rem;
        margin-bottom: 1.2rem;
        font-size: 0.88rem;
        line-height: 1.75;
        color: #C8C8C8;
    }
    .chat-replay .label {
        color: #8B6F47; font-weight: 600;
        font-size: 0.75rem; letter-spacing: 0.07em;
        text-transform: uppercase; display: block;
        margin-bottom: 0.6rem;
    }
    .chat-replay .turn { margin-bottom: 0.9rem; }
    .chat-replay .q { color: #9E9E9E; margin-bottom: 0.2rem; font-style: italic; }
    .chat-replay .a { color: #E0E0E0; padding-left: 0.8rem; border-left: 2px solid #333; }
    </style>
    """, unsafe_allow_html=True)

def disable_paste():
    st.components.v1.html(
        """
        <script>
        (function() {
            function blockPaste(e) {
                const tag = e.target.tagName.toLowerCase();
                const isEditable = e.target.isContentEditable;
                if (tag === 'textarea' || tag === 'input' || isEditable) {
                    e.preventDefault();
                    e.stopPropagation();
                    return false;
                }
            }
            // Run once on load, then re-run as Streamlit rerenders the DOM
            function attach() {
                window.parent.document.addEventListener('paste', blockPaste, true);
            }
            attach();
        })();
        </script>
        """,
        height=0,
    )

def _elapsed_seconds(start_iso: str, end_iso: str) -> int:
    try:
        fmt = "%Y-%m-%dT%H:%M:%S.%f"
        s = datetime.strptime(start_iso[:26], fmt)
        e = datetime.strptime(end_iso[:26], fmt)
        return max(0, int((e - s).total_seconds()))
    except Exception:
        return -1
    
def save_progress_to_gcs(data: dict):
    """
    Overwrites a single in-progress file per participant on every annotation save.
    Only one file exists at a time -- the most recent state.
    """
    try:
        gcs = get_gcs_client()
        bucket = gcs.bucket(GCS_BUCKET)
        pid = data["participant_id"]
        prolific = data.get("prolific_pid") or pid
        blob = bucket.blob(f"sessions/{prolific}/IN_PROGRESS.json")
        # blob = bucket.blob(f"sessions/{pid}/IN_PROGRESS.json")
        payload = {
            "participant_id": pid,
            # "participant_name": data["name"],
            "scenario_id": data["scenario_id"],
            "connection_type": data["disclosure"].get("connection_type", ""),
            "duration": data["disclosure"].get("duration", ""),
            "disclosure_text": data["disclosure"].get("text", ""),
            "micronarrative": data["micronarrative"],
            "chat_log": data["elicitation"],
            "annotations": data["annotations"],
            "annotations_complete": len(data["annotations"]),
            "status": f"in_progress_{len(data['annotations'])}",
            "last_saved": datetime.utcnow().isoformat(),
            "prolific_pid": data.get("prolific_pid"),
            "prolific_study_id": data.get("prolific_study_id"),
            "prolific_session_id": data.get("prolific_session_id"),
            "consented_at": data.get("consented_at"),
        }
        blob.upload_from_string(
            json.dumps(payload, ensure_ascii=False),
            content_type="application/json"
        )
    except Exception:
        pass  # Silent -- never interrupt participant flow


def save_complete_to_gcs(data: dict):
    """
    Writes the final complete record and deletes the in-progress file.
    """
    gcs = get_gcs_client()
    bucket = gcs.bucket(GCS_BUCKET)
    pid = data["participant_id"]

    final = {
        "participant_id": pid,
        "created_at": data["created_at"],
        "condition": data.get("condition", "no_elicitation"),   # ← control arm marker
        "scenario_id": data["scenario_id"],
        "connection_type": data["disclosure"].get("connection_type", ""),
        "duration": data["disclosure"].get("duration", ""),
        "disclosure_text": data["disclosure"].get("text", ""),
        "micronarrative": data["micronarrative"],
        "chat_log": data["elicitation"],
        "annotations": data["annotations"],
        "status": "complete",
        "saved_at": datetime.utcnow().isoformat(),
        "prolific_pid": data.get("prolific_pid"),
        "prolific_study_id": data.get("prolific_study_id"),
        "prolific_session_id": data.get("prolific_session_id"),
        "consented_at": data.get("consented_at"),
        "reflexivity_response":     data.get("reflexivity_response", ""),
        "reflexivity_cards_shown":  data.get("reflexivity_cards_shown", []),
    }

    # Write COMPLETE.json
    # bucket.blob(f"sessions/{pid}/COMPLETE.json").upload_from_string(
    prolific = data.get("prolific_pid") or pid
    bucket.blob(f"sessions/{prolific}/COMPLETE.json").upload_from_string(
        json.dumps(final, ensure_ascii=False),
        content_type="application/json"
    )

    # Delete IN_PROGRESS.json so only the clean final file remains
    try:
        # bucket.blob(f"sessions/{pid}/IN_PROGRESS.json").delete()
        bucket.blob(f"sessions/{prolific}/IN_PROGRESS.json").delete()
    except Exception:
        pass

def prog(step, total):
    pct = int(step / total * 100)
    st.markdown(
        f"<div class='prog-bg'><div class='prog-fill' style='width:{pct}%'></div></div>",
        unsafe_allow_html=True
    )

def render_word_counter(text: str, minimum: int):
    words = len(text.strip().split()) if text.strip() else 0
    if words >= minimum:
        st.markdown(f"<div class='word-counter-ok'>✓ {words} words</div>", unsafe_allow_html=True)
    else:
        remaining = minimum - words
        st.markdown(
            f"<div class='word-counter-low'>{words} / {minimum} words -- {remaining} more to go</div>",
            unsafe_allow_html=True
        )

def render_chat_replay(elicitation: list):
    """Renders a compact Q&A transcript of the elicitation exchange."""
    pairs = []
    for i, m in enumerate(elicitation):
        if m["role"] == "assistant":
            answer = elicitation[i + 1]["content"] if i + 1 < len(elicitation) and elicitation[i + 1]["role"] == "user" else None
            if answer:
                pairs.append((m["content"], answer))

    html = "<div class='chat-replay'><span class='label'>Your conversation</span>"
    for q, a in pairs:
        html += (
            f"<div class='turn'>"
            f"<div class='q'>{q}</div>"
            f"<div class='a'>{a}</div>"
            f"</div>"
        )
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

def scroll_to_bottom():
    """JS to scroll the last chat message into view."""
    st.components.v1.html(
        """
        <script>
        (function() {
            var msgs = window.parent.document.querySelectorAll('[data-testid="stChatMessage"]');
            if (msgs.length > 0) {
                msgs[msgs.length - 1].scrollIntoView({ behavior: 'smooth', block: 'end' });
            }
        })();
        </script>
        """,
        height=0,
    )

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    st.set_page_config(
        page_title="Hate Speech & Belonging -- Annotation Study",
        layout="centered",
        page_icon="🗣"
    )
    inject_styles()
    # disable_paste()

    # ── SIGN-IN + CONSENT ─────────────────────────────────────────────────────
    if "pdata" not in st.session_state:
        st.markdown("<div class='step-label'>Annotation Study</div>", unsafe_allow_html=True)
        st.title("Hate Speech & Belonging")
        st.markdown("*A content annotation study*")
        st.markdown("---")
        st.markdown(
            "This study takes about 20-25 minutes. You'll "
            "read and annotate a small set of social media posts, provide your thoughts on each post, and complete a brief survey. "
            "There are no right or wrong answers."
        )

        with st.expander("ℹ️ Participant information & consent -- please read before starting", expanded=True):
            st.markdown(
                """
**Purpose:** This study examines how people interpret ambiguous social media content. Your judgements and reasoning are the data.

**What you'll do:** Annotate 10 social media posts on topics around gender identity. Posts contain no slurs or explicit threats, but some may feel personally resonant.

**Data & consent:** Responses are stored securely and used for academic research only. Your rationales may be quoted anonymously in publications. You may stop at any time -- incomplete responses will not be used.

⚠️ Please do not use AI tools (ChatGPT, Claude, etc.) to answer any questions in this study. We are studying your personal perspective -- AI-generated responses undermine the research and may result in your submission being rejected.
                """
            )
        consent = st.checkbox("I have read the above information and agree to participate.")
        no_ai = st.checkbox("I confirm I will answer all questions myself, without AI tools or chatbots.")

        # name = st.text_input("Enter your first name or a pseudonym:")
        st.markdown("---")
        # st.markdown("**Returning? Paste your pause code to resume.**")
        # resume_code = st.text_area("Pause code (optional):", height=80, key="resume_code_input")
        # if st.button("Resume →"):
        #     if not resume_code.strip():
        #         st.warning("Please paste your pause code.")
        #     else:
        #         try:
        #             import base64, json as _json
        #             payload = _json.loads(base64.b64decode(resume_code.strip()).decode())
        #             payload["resumed_at"] = datetime.utcnow().isoformat()
        #             payload["paused_at"] = None
        #             payload["pause_code"] = None
        #             st.session_state.pdata = payload
        #             st.rerun()
        #         except Exception as e:
        #             st.error(f"Could not read pause code: {e}. Please check and try again.")

        # st.markdown("---")

        if st.button("Begin →", type="primary"):
            if not consent or not no_ai:
                st.warning("Please check both boxes before continuing.")
            else:
                params = st.query_params
                prolific_pid = params.get("PROLIFIC_PID", None)
                study_id = params.get("STUDY_ID", None)
                session_id = params.get("SESSION_ID", None)
                st.session_state.pdata = init_participant(
                    prolific_pid=prolific_pid,
                    study_id=study_id,
                    session_id=session_id,
                )
                st.rerun()
        return

    data = st.session_state.pdata
    scenario = get_scenario(data["scenario_id"])
    stage = data["workflow_stage"]


    with st.sidebar:
        # st.markdown(f"**{data['name']}**")
        st.markdown(f"*{scenario['theme']}*")
        labels = {
            "annotation": "1 -- Annotations",
            "disclosure": "2 -- Background",
            "reflexivity": "3 -- Reflect",
            "complete": "✓ Done"
        }
        st.caption(labels.get(stage, stage))
        # st.markdown("---")

        # ── PAUSE FEATURE ────────────────────────────────────────────────────
        # if stage not in ("complete",):
        #     with st.expander("⏸ Save & pause"):
        #         st.caption(
        #             "Generate a code to save your progress. "
        #             "Paste it when you return to pick up where you left off."
        #         )
        #         if st.button("Generate pause code"):
        #             import base64, json as _json
        #             payload = _json.dumps({
        #                 # "name": data["name"],
        #                 "participant_id": data["participant_id"],
        #                 "scenario_id": data["scenario_id"],
        #                 "workflow_stage": data["workflow_stage"],
        #                 "disclosure": data["disclosure"],
        #                 "elicitation": data["elicitation"],
        #                 "micronarrative": data["micronarrative"],
        #                 "annotations": data["annotations"],
        #                 "created_at": data["created_at"],
        #             })
        #             code = base64.b64encode(payload.encode()).decode()
        #             data["pause_code"] = code
        #             data["paused_at"] = datetime.utcnow().isoformat()
        #             st.session_state.pdata = data
        #             st.code(code, language=None)
        #             st.caption("Copy this code. It contains your full progress.")

        # st.markdown("---")
        st.caption("Data is held in memory and saved securely at the end.")

    # ── STAGE 1: ANNOTATION ───────────────────────────────────────────────────
    if stage == "annotation":
        datapoints = get_datapoints(data["scenario_id"])
        idx = len(data["annotations"])

        if idx < len(datapoints):
            dp = datapoints[idx]
            start_key = f"anno_start_{idx}"
            if start_key not in st.session_state:
                st.session_state[start_key] = datetime.utcnow().isoformat()
            st.components.v1.html(
                "<script>window.parent.scrollTo({top: 0, behavior: 'instant'});</script>",
                height=0,
            )
            st.markdown(
                f"<div class='step-label'>Step 1 of 3 -- Post {idx+1} of {len(datapoints)}</div>",
                unsafe_allow_html=True
            )
            st.title("Annotating social media posts")
            prog(idx, len(datapoints))
            if idx == 0:
                st.write(
                    "You'll now read and annotate ten social media posts. "
                    "There are no right or wrong answers -- your interpretation is the data."
                )

            # Instruction BEFORE the passage (improves flow)
            st.markdown("**Read the post below, then answer the questions.**")
            st.markdown(
                f"<div class='tweet-card'>"
                f"<span class='meta-pill'>Post {idx+1} of {len(datapoints)}</span>"
                f"<span class='meta-pill'>{dp['domain']}</span>"
                f"<br><br>{dp['text']}</div>",
                unsafe_allow_html=True,
            )

            # Q1 -- outside form so state persists across re-renders (#4 fix)
            st.markdown("**1. How would you label this post?**")
            label = st.radio(
                "",
                options=[
                    "Clearly harmful -- targets a group in a way that dehumanises or incites",
                    "Likely harmful -- framing that would harm most readers from the targeted group, even if deniable",
                    "Ambiguous -- could be read as harmful or legitimate depending on who is reading and why",
                    "Likely not harmful -- critical or provocative, but the harm reading requires a stretch",
                    "Not harmful -- policy concern, cultural commentary, or frustration with no hateful subtext",
                ],
                index=None,
                label_visibility="collapsed",
                key=f"label_{idx}",
            )

            st.markdown("---")

            # Q2 -- outside form
            st.markdown("**2. Who, if anyone, does this post seem directed at?**")
            target = st.selectbox(
                "",
                options=[
                    "-- select --",
                    "No one -- I don't read this as targeting anyone",
                    "A specific individual",
                    "Immigrants, refugees, or a racialised group",
                    "A religious community",
                    "A gender or LGBTQ+ community",
                    "Multiple overlapping groups",
                    "Unclear",
                ],
                index=0,
                label_visibility="collapsed",
                key=f"target_{idx}",
            )

            st.markdown("---")

            # Q3 -- outside form: live word counter works here (#4 fix)
            st.markdown(f"**3. Your rationale** *(minimum {MIN_RATIONALE_WORDS} words)*")
            st.caption(
                "What specific language, framing, or context shaped your judgement? "
                "Walk us through your reasoning."
            )
            rationale = st.text_area(
                "",
                height=170,
                label_visibility="collapsed",
                key=f"rationale_{idx}",
            )
            rationale_words = len(rationale.strip().split()) if rationale.strip() else 0
            render_word_counter(rationale, MIN_RATIONALE_WORDS)

            st.markdown("---")

            # Q4 + submit button -- only these need a form to batch the submit action
            with st.form(f"anno_{idx}"):
                st.markdown(
                    "**4. How relevant did your identity or personal experience feel "
                    "to how much this post resonated with you?**"
                )
                st.caption("1 = not at all relevant to my identity or experience · 5 = very much so")
                # salience = st.slider("", 1, 5, value=None, label_visibility="collapsed")
                salience = st.radio(
                        "",
                        options=[1, 2, 3, 4, 5],
                        index=None,               # truly no default
                        horizontal=True,
                        label_visibility="collapsed",
                        key=f"salience_{idx}",
                    )

                submitted = st.form_submit_button("Submit & next →", type="primary")

                if submitted:
                    # Read Q1-Q3 from session state (set outside form above)
                    label = st.session_state.get(f"label_{idx}")
                    target = st.session_state.get(f"target_{idx}", "-- select --")
                    rationale = st.session_state.get(f"rationale_{idx}", "")
                    rationale_words = len(rationale.strip().split()) if rationale.strip() else 0

                    errors = []
                    if label is None:
                        errors.append("Please select a label for question 1.")
                    if target == "-- select --":
                        errors.append("Please select an option for question 2.")
                    if rationale_words < MIN_RATIONALE_WORDS:
                        errors.append(
                            f"Your rationale is {rationale_words} words -- please expand to at least "
                            f"{MIN_RATIONALE_WORDS} words. The detail you provide is the most valuable "
                            "part of the study."
                        )
                    if salience is None:
                        errors.append("Please select an option for question 4.")


                    if errors:
                        for e in errors:
                            st.warning(e)
                    else:
    
                        annotation_end = datetime.utcnow().isoformat()
                        data["annotations"].append({
                            "datapoint_id": dp["id"],
                            "domain": dp["domain"],
                            "tweet_text": dp["text"],
                            "participant_label": label,
                            "participant_target": target,
                            "rationale": rationale,
                            "positionality_salience": salience,
                            "timestamp_start": st.session_state.get(f"anno_start_{idx}", annotation_end),
                            "timestamp_end": annotation_end,
                            "seconds_on_item": _elapsed_seconds(
                                st.session_state.get(f"anno_start_{idx}", annotation_end),
                                annotation_end
                            ),
                        })
                        save_progress_to_gcs(data)
                        st.rerun()

        else:
            # All annotations done -- advance to disclosure stage
            data["workflow_stage"] = "disclosure"
            st.session_state.pdata = data
            st.rerun()

    # ── STAGE 2: DISCLOSURE ───────────────────────────────────────────────────
    elif stage == "disclosure":
        st.markdown("<div class='step-label'>Step 2 of 3</div>", unsafe_allow_html=True)
        st.title("A bit about you")
        prog(2, 3)
        st.write(
            "Before we begin, we'd like to collect a few background details. "
            "This helps us understand the range of perspectives in the study."
        )

        conn = st.selectbox(
            "How would you describe your connection to topics of immigration, religion, or identity and belonging?",
            [
                "-- please select --",
                "I have direct personal experience (as an immigrant, refugee, religious minority, or member of a marginalised group)",
                "I'm a caregiver, partner, or close community member of someone with this experience",
                "I work or study in this area professionally or academically",
                "I'm an interested observer -- no direct personal connection",
            ],
        )
        duration = st.text_input(
            "How long has this been part of your life or work? (e.g., 'my whole life', '3 years')"
        )
        disclosure = st.text_area(
            "Briefly describe how this topic relates to your life.",
            height=100,
        )

        if st.button("Continue →", type="primary"):
            if conn == "-- please select --":
                st.warning("Please select an option before continuing.")
            elif not duration.strip():
                st.warning("Please fill in how long this topic has been part of your life.")
            else:
                data["disclosure"] = {"connection_type": conn, "duration": duration, "text": disclosure}
                data["workflow_stage"] = "reflexivity"
                st.rerun()

    # ── COMPLETE ──────────────────────────────────────────────────────────────
    # elif stage == "complete":
    #     st.balloons()
    #     st.title("Thank you.")
    #     st.markdown(
    #         "Your annotations and narrative are saved. "
    #         "The perspectives you bring -- including your background and lived experience -- "
    #         "are what makes this kind of research meaningful."
    #     )
    #     st.caption("Data stored securely · You may close this window.")

    elif stage == "reflexivity":
        render_reflexivity_stage(
                data, GCS_BUCKET, get_gcs_client,
                save_complete_to_gcs, render_word_counter, prog,
            )

    elif stage == "complete":
        st.balloons()
        st.title("Thank you.")
        st.markdown(
            "Your annotations and narrative are saved. "
            "The perspectives you bring -- including your background and lived experience -- "
            "are what makes this kind of research meaningful."
        )
        # prolific_pid = data.get("prolific_pid")
        
        try:
            completion_url = st.secrets["PROLIFIC_COMPLETION_URL"]
        except Exception:
            completion_url = None


        if completion_url:
            st.markdown(
                f"**Please click the button below to confirm your submission and receive payment.**"
            )
            st.link_button("Complete submission →", completion_url)
        else: 
            st.markdown(
                f"**There was a problem with your submission. Please contact researcher.**"
            )
        st.caption("Data stored securely.")


if __name__ == "__main__":
    main()
