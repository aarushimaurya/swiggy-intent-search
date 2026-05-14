import json
import os
import streamlit as st
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Swiggy Intent Search", layout="wide")

# ── Constants ──────────────────────────────────────────────────────────────────

CUISINE_EMOJI = {
    "biryani": "🍚", "north_indian": "🫕", "south_indian": "🥘",
    "chinese": "🥡", "italian": "🍕", "mughlai": "🍖",
    "fast_food": "🍔", "desserts": "🍮", "beverages": "☕",
    "healthy": "🥗", "continental": "🍽️",
}
SPICE_LABEL = {"mild": "🟢 Mild", "medium": "🟡 Medium", "spicy": "🔴 Spicy"}

CUISINE_OPTIONS = [
    "north_indian", "south_indian", "chinese", "italian", "mughlai",
    "biryani", "fast_food", "desserts", "beverages", "healthy", "continental",
]
MEAL_OPTIONS = ["breakfast", "lunch", "dinner", "snack", "dessert", "beverage"]

LABEL_MAP = {
    "cuisine": "Cuisine", "meal_type": "Meal",
    "max_price": "Max price", "min_price": "Min price",
    "is_veg": "Veg", "dietary": "Dietary",
    "spice_level": "Spice", "portion_size": "Portion",
    "max_prep_time": "Max prep", "min_rating": "Min rating",
}

# Injected once in main(); scoped to multiselect tags so nothing else is affected.
PILL_CSS = """
<style>
/* Reduce Streamlit's default top padding */
div.block-container { padding-top: 1.2rem !important; }
header[data-testid="stHeader"] { height: 0 !important; }

/* ── Orange filter pills ──────────────────────────────────────── */
span[data-baseweb="tag"] {
    background: #fff8f0 !important;
    border: 1px solid #fda85b !important;
    border-radius: 999px !important;
    padding: 3px 8px 3px 11px !important;
    margin: 2px 4px 2px 0 !important;
    height: auto !important;
    line-height: 1 !important;
    display: inline-flex !important;
    align-items: center !important;
    gap: 6px !important;
}
span[data-baseweb="tag"]:hover {
    background: #fde8d0 !important;
    cursor: pointer !important;
}
/* Label text inside the pill */
span[data-baseweb="tag"] span:first-child {
    color: #b84800 !important;
    font-size: 0.83rem !important;
    font-weight: 500 !important;
}
/* × icon wrapper — always red, pill darkens on hover */
span[data-baseweb="tag"] span[title="Clear"],
span[data-baseweb="tag"] [role="button"] {
    display: inline-flex !important;
    align-items: center !important;
    color: #c0392b !important;
    line-height: 1 !important;
}

/* ── Strip all chrome from every multiselect ─────────────────── */
div[data-testid="stMultiSelect"] > label { display: none !important; }
div[data-testid="stMultiSelect"] > div   { box-shadow: none !important; }
div[data-testid="stMultiSelect"] > div > div:first-child {
    border: none !important;
    background: transparent !important;
    padding: 0 !important;
    min-height: 0 !important;
    gap: 0 !important;
}
/* Hide text input, dropdown chevron, and global clear button */
div[data-testid="stMultiSelect"] input              { display: none !important; }
div[data-testid="stMultiSelect"] svg                { display: none !important; }
div[data-testid="stMultiSelect"] [data-baseweb="clear-icon"] { display: none !important; }
/* × icon inside pills — force red */
div[data-testid="stMultiSelect"] span[data-baseweb="tag"] svg,
div[data-testid="stMultiSelect"] span[data-baseweb="tag"] svg path {
    display: inline-flex !important;
    fill: #c0392b !important;
    color: #c0392b !important;
    width: 12px !important;
    height: 12px !important;
}

/* ── Gray pills for "couldn't interpret" unmapped terms ───────── */
div:has(.unmapped-marker) ~ div span[data-baseweb="tag"] {
    background: #f5f5f5 !important;
    border: 1px solid #ddd !important;
}
div:has(.unmapped-marker) ~ div span[data-baseweb="tag"]:hover {
    background: #e8e8e8 !important;
}
div:has(.unmapped-marker) ~ div span[data-baseweb="tag"] span:first-child {
    color: #888 !important;
}
div:has(.unmapped-marker) ~ div span[data-baseweb="tag"] span[title="Clear"] {
    color: #c5c5c5 !important;
}
div:has(.unmapped-marker) ~ div span[data-baseweb="tag"]:hover span[title="Clear"] {
    color: #555 !important;
}
/* × inside gray (unmapped) pills */
div:has(.unmapped-marker) ~ div span[data-baseweb="tag"] svg,
div:has(.unmapped-marker) ~ div span[data-baseweb="tag"] svg path {
    fill: #c5c5c5 !important;
}
div:has(.unmapped-marker) ~ div span[data-baseweb="tag"]:hover svg,
div:has(.unmapped-marker) ~ div span[data-baseweb="tag"]:hover svg path {
    fill: #555 !important;
}

/* ── "add filter" link-style button ───────────────────────────── */
button[data-testid="add-filter-btn"] { display: none; }
div[data-testid="stButton"]:has(button[kind="secondary"].add-filter) button {
    font-size: 0.78rem !important;
    padding: 0 !important;
    background: none !important;
    border: none !important;
    color: #ccc !important;
    text-decoration: underline !important;
    box-shadow: none !important;
}
div[data-testid="stButton"]:has(button[kind="secondary"].add-filter) button:hover {
    color: #fc8019 !important;
}
</style>
"""

# ── System prompt ──────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a filter extractor for a food delivery catalogue search.

The catalogue schema:
- cuisine: north_indian | south_indian | chinese | italian | mughlai | biryani | fast_food | desserts | beverages | healthy | continental
- meal_type: breakfast | lunch | dinner | snack | dessert | beverage
- price: integer in rupees
- prep_time_minutes: integer
- is_veg: boolean
- dietary: vegan | jain | gluten_free | high_protein | low_calorie
- spice_level: mild | medium | spicy
- portion_size: light | regular | filling
- rating: float 3.5–4.8

Extract filters from the user's query and return a single JSON object:
{
  "cuisine": string or null,
  "meal_type": string or null,
  "max_price": integer or null,
  "min_price": integer or null,
  "is_veg": boolean or null,
  "dietary": [strings] or null,
  "spice_level": string or null,
  "portion_size": string or null,
  "max_prep_time": integer or null,
  "min_rating": float or null,
  "unmapped_terms": [strings]
}

Synonym mappings (apply confidently):
- "filling" / "heavy" / "hearty" / "large"     → portion_size: "filling"
- "light" / "small" / "snack-sized"             → portion_size: "light"
- "healthy" / "diet"                             → cuisine: "healthy"
- "not spicy" / "not too spicy" / "mild"         → spice_level: "mild"
- "medium spicy"                                 → spice_level: "medium"
- "veg" / "vegetarian" / "pure veg"             → is_veg: true
- "non-veg" / "non vegetarian" / "meat"
  "chicken" / "mutton" / "fish" / "prawn"       → is_veg: false
- "under X" / "below X" / "less than X"         → max_price: X
- "above X" / "over X" / "at least X"           → min_price: X
- "quick" / "fast" / "in a hurry"               → max_prep_time: 15
- "high protein" / "protein-rich"               → dietary: ["high_protein"]
- "gluten free" / "gluten-free"                 → dietary: ["gluten_free"]
- "vegan"                                        → dietary: ["vegan"], is_veg: true
- "jain"                                         → dietary: ["jain"], is_veg: true
- "low calorie" / "low cal" / "diet-friendly"   → dietary: ["low_calorie"]
- "breakfast" / "morning"                        → meal_type: "breakfast"
- "lunch" / "afternoon meal"                     → meal_type: "lunch"
- "dinner" / "evening meal" / "supper"          → meal_type: "dinner"
- "snack" / "quick bite"                         → meal_type: "snack"
- "dessert" / "sweet"                            → meal_type: "dessert"
- "beverage" / "drink"                           → meal_type: "beverage"

unmapped_terms — BE CONSERVATIVE:
- Use for words/phrases that are genuinely ambiguous or don't map to any field.
- Examples: "comfort food", "rainy day", "festive", "soul food", "fusion", "healthy pizza".
- Do NOT guess: if a concept could map but you're not sure, put it in unmapped_terms.
- Return [] if the entire query was fully mapped.

Return ONLY valid JSON. No markdown, no code fences."""


# ── Cached resources ───────────────────────────────────────────────────────────

@st.cache_resource
def get_client():
    return Groq(api_key=os.getenv("GROQ_API_KEY"))


@st.cache_data
def load_catalogue():
    with open("catalogue.json") as f:
        return json.load(f)


@st.cache_data(show_spinner=False)
def extract_filters(query: str) -> dict:
    client = get_client()
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    return json.loads(response.choices[0].message.content)


# ── Filtering ──────────────────────────────────────────────────────────────────

def apply_filters(catalogue: list, filters: dict) -> list:
    results = []
    for item in catalogue:
        if filters.get("cuisine") and item["cuisine"] != filters["cuisine"]:
            continue
        if filters.get("meal_type") and filters["meal_type"] not in item["meal_type"]:
            continue
        if filters.get("max_price") is not None and item["price"] > filters["max_price"]:
            continue
        if filters.get("min_price") is not None and item["price"] < filters["min_price"]:
            continue
        if filters.get("is_veg") is not None and item["is_veg"] != filters["is_veg"]:
            continue
        if filters.get("dietary"):
            if not all(d in item["dietary"] for d in filters["dietary"]):
                continue
        if filters.get("spice_level") and item["spice_level"] != filters["spice_level"]:
            continue
        if filters.get("portion_size") and item["portion_size"] != filters["portion_size"]:
            continue
        if filters.get("max_prep_time") is not None and item["prep_time_minutes"] > filters["max_prep_time"]:
            continue
        if filters.get("min_rating") is not None and item["rating"] < filters["min_rating"]:
            continue
        results.append(item)
    return results


# ── UI helpers ─────────────────────────────────────────────────────────────────

def _format_value(key: str, val) -> str:
    if key == "is_veg":     return "Veg only" if val else "Non-veg only"
    if key == "dietary":    return ", ".join(d.replace("_", " ") for d in val)
    if key == "max_price":  return f"₹{val}"
    if key == "min_price":  return f"₹{val}+"
    if key == "max_prep_time": return f"≤{val} min"
    if key == "min_rating": return f"⭐{val}+"
    return str(val).replace("_", " ").title()


def render_filter_panel():
    active   = st.session_state.active_filters
    unmapped = st.session_state.unmapped_terms

    # Nothing to show — hide the panel entirely.
    if not active and not unmapped:
        return

    # Build label list and reverse map for removal detection.
    label_to_key: dict[str, str] = {}
    filter_labels: list[str] = []
    for k, v in active.items():
        if k in LABEL_MAP:
            lbl = f"{LABEL_MAP[k]}: {_format_value(k, v)}"
            filter_labels.append(lbl)
            label_to_key[lbl] = k

    # Change the widget key whenever the set of active filter keys changes so
    # Streamlit always uses `default=filter_labels` rather than stale state.
    ms_key = "fp__" + "_".join(sorted(active.keys()))

    with st.container():
        # Understood filters — header + pills only shown when filters exist.
        if filter_labels:
            st.markdown(
                '<p style="font-size:0.75rem;font-weight:600;color:#c0a898;'
                'letter-spacing:0.06em;margin:0 0 4px 0;">🧠 UNDERSTOOD</p>',
                unsafe_allow_html=True,
            )
            selected = st.multiselect(
                label="filters",
                options=filter_labels,
                default=filter_labels,
                label_visibility="collapsed",
                key=ms_key,
            )
            removed = set(filter_labels) - set(selected)
            if removed:
                for lbl in removed:
                    k = label_to_key.get(lbl)
                    if k and k in st.session_state.active_filters:
                        del st.session_state.active_filters[k]
                st.rerun()

        # Unmapped terms — gray removable pills.
        if unmapped:
            st.markdown(
                '<p style="font-size:0.76rem;color:#888;margin:5px 0 2px 0;">'
                "couldn't interpret: <span class='unmapped-marker'></span></p>",
                unsafe_allow_html=True,
            )
            um_key = "um__" + "__".join(sorted(unmapped))
            selected_unmapped = st.multiselect(
                label="unmapped",
                options=unmapped,
                default=unmapped,
                label_visibility="collapsed",
                key=um_key,
            )
            removed_unmapped = set(unmapped) - set(selected_unmapped)
            if removed_unmapped:
                st.session_state.unmapped_terms = [
                    t for t in st.session_state.unmapped_terms if t not in removed_unmapped
                ]
                st.rerun()

        # Subtle "add filter" link, left-aligned.
        if st.button("＋ add filter", key="toggle_manual"):
            st.session_state.show_manual = not st.session_state.get("show_manual", False)

        st.markdown(
            '<div style="margin-bottom:10px;border-bottom:1px solid #f5ede6;"></div>',
            unsafe_allow_html=True,
        )


def render_manual_filter_form():
    """Compact form toggled by the '＋ add filter' link."""
    if not st.session_state.get("show_manual", False):
        return

    with st.form("manual_filter_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            cuisine = st.selectbox("Cuisine", ["(any)"] + CUISINE_OPTIONS)
            meal    = st.selectbox("Meal type", ["(any)"] + MEAL_OPTIONS)
            portion = st.selectbox("Portion", ["(any)", "light", "regular", "filling"])
        with c2:
            max_price = st.number_input("Max price (₹)", min_value=0, value=0, step=50)
            min_price = st.number_input("Min price (₹)", min_value=0, value=0, step=50)
            max_prep  = st.number_input("Max prep (min)", min_value=0, value=0, step=5)
        with c3:
            veg    = st.selectbox("Veg", ["(any)", "Veg only", "Non-veg only"])
            spice  = st.selectbox("Spice", ["(any)", "mild", "medium", "spicy"])
            rating = st.slider("Min rating ⭐", 3.5, 4.8, 3.5, step=0.1)

        submitted = st.form_submit_button("Apply", use_container_width=True)

    if submitted:
        f = st.session_state.active_filters
        if cuisine != "(any)":      f["cuisine"]       = cuisine
        if meal    != "(any)":      f["meal_type"]     = meal
        if portion != "(any)":      f["portion_size"]  = portion
        if max_price > 0:           f["max_price"]     = max_price
        if min_price > 0:           f["min_price"]     = min_price
        if max_prep  > 0:           f["max_prep_time"] = max_prep
        if veg == "Veg only":       f["is_veg"]        = True
        elif veg == "Non-veg only": f["is_veg"]        = False
        if spice != "(any)":        f["spice_level"]   = spice
        if rating > 3.5:            f["min_rating"]    = round(rating, 1)
        st.session_state.show_manual = False
        st.rerun()


def render_card(item: dict):
    cuisine_icon = CUISINE_EMOJI.get(item["cuisine"], "🍴")
    dietary = [d for d in item["dietary"] if d != "none"]
    dietary_str = " · ".join(d.replace("_", " ") for d in dietary) if dietary else "—"
    veg_badge = "🟢 Veg" if item["is_veg"] else "🔴 Non-veg"

    st.markdown(
        f'<div style="border:1px solid #e0e0e0;border-radius:12px;padding:16px;'
        f'background:#fff;box-shadow:0 1px 4px rgba(0,0,0,0.05);">'
        f'<div style="font-size:12px;color:#aaa;margin-bottom:3px;">'
        f'{cuisine_icon} {item["cuisine"].replace("_"," ").title()}</div>'
        f'<div style="font-size:16px;font-weight:700;color:#1a1a1a;margin-bottom:1px;">'
        f'{item["name"]}</div>'
        f'<div style="font-size:12px;color:#777;margin-bottom:8px;">{item["restaurant"]}</div>'
        f'<hr style="margin:6px 0;border:none;border-top:1px solid #f5f5f5;">'
        f'<div style="display:flex;justify-content:space-between;margin-bottom:5px;">'
        f'<span style="font-size:17px;font-weight:700;color:#fc8019;">₹{item["price"]}</span>'
        f'<span style="font-size:12px;color:#aaa;">⏱ {item["prep_time_minutes"]} min</span></div>'
        f'<div style="font-size:12px;margin-bottom:3px;">'
        f'{veg_badge} &nbsp;·&nbsp; {SPICE_LABEL[item["spice_level"]]}</div>'
        f'<div style="font-size:12px;color:#777;margin-bottom:3px;">'
        f'📦 {item["portion_size"].title()} portion</div>'
        f'<div style="font-size:11px;color:#aaa;margin-bottom:5px;">🏷 {dietary_str}</div>'
        f'<div style="font-size:13px;font-weight:600;color:#333;">⭐ {item["rating"]}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    catalogue = load_catalogue()

    # Session state defaults
    for key, default in [
        ("active_filters", {}),
        ("unmapped_terms", []),
        ("last_query", ""),
        ("show_manual", False),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default

    # Inject pill CSS once per page load
    st.markdown(PILL_CSS, unsafe_allow_html=True)

    st.markdown(
        "<h1 style='color:#fc8019;margin-bottom:4px;font-size:clamp(1.4rem, 5vw, 2rem);'>🍱 Swiggy Intent Search "
        "<span style='font-size:clamp(0.7rem, 2vw, 0.95rem);color:#bbb;font-weight:400;'>(Prototype)</span></h1>",
        unsafe_allow_html=True,
    )

    query = st.text_input(
        "What are you looking for?",
        placeholder="e.g. filling lunch under 250, comfort food, quick non-veg dinner…",
    )

    if query.strip():
        if query.strip() != st.session_state.last_query:
            with st.spinner("Understanding your query..."):
                try:
                    result = extract_filters(query.strip())
                    st.session_state.last_query    = query.strip()
                    st.session_state.unmapped_terms = result.get("unmapped_terms") or []
                    st.session_state.active_filters = {
                        k: v for k, v in result.items()
                        if k != "unmapped_terms" and v is not None
                    }
                    st.session_state.show_manual = False
                except Exception as e:
                    st.error(f"Could not parse query: {e}")
                    st.session_state.active_filters = {}
                    st.session_state.unmapped_terms = []

        render_filter_panel()
        render_manual_filter_form()
        items = apply_filters(catalogue, st.session_state.active_filters)
    else:
        st.session_state.last_query     = ""
        st.session_state.active_filters = {}
        st.session_state.unmapped_terms = []
        st.session_state.show_manual    = False
        items = catalogue

    st.markdown(
        f"<p style='font-size:13px;color:#999;margin:4px 0 8px 0;'>"
        f"{len(items)} item{'s' if len(items) != 1 else ''} found</p>",
        unsafe_allow_html=True,
    )

    if not items:
        st.markdown(
            '<div style="text-align:center;padding:60px 20px;color:#ccc;">'
            '<div style="font-size:44px;margin-bottom:10px;">🍽️</div>'
            '<div style="font-size:18px;font-weight:600;margin-bottom:6px;color:#aaa;">No exact matches</div>'
            '<div style="font-size:13px;">Try broadening your query or removing a filter.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    st.divider()

    cols = st.columns(3, gap="medium")
    for i, item in enumerate(items):
        with cols[i % 3]:
            render_card(item)
            st.markdown("<div style='margin-bottom:14px'></div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
