"""Builds evals/dataset.json from the labelled cases below.

Each case is labelled with what a perfect reader would extract (`ideal`). The builder then runs the
deterministic pipeline once (validate → price) and freezes the expected SKUs, quantities, missing
specs and totals into the dataset. After that the dataset is static: if validator or pricing code
changes behaviour, the ideal-mode eval fails until the change is reviewed and the dataset rebuilt.

    python -m evals.build_dataset          # rewrite evals/dataset.json
"""

import json
from pathlib import Path

from app.schemas.extraction import ExtractedItem, Extraction, Spec
from app.services.catalog import load_catalog
from app.services.guardrail import rule_check
from app.services.pricing import price_quote
from app.services.states import state_code
from app.services.validator import validate

OUT = Path(__file__).resolve().parent / "dataset.json"
ADVERSARIAL = Path(__file__).resolve().parent.parent / "tests" / "adversarial" / "cases.json"
BUSINESS_STATE = "CG"


def item(text: str, qty: int | None, **specs: str) -> dict:
    return {"item_text": text, "quantity": qty, "specs": specs}


def tee(colour: str, qty: int | None, **specs: str) -> dict:
    return item(f"{colour} round-neck t-shirt", qty, **specs)


S = {"print_type": "screen", "placement": "front"}  # common apparel specs
# fmt: off
CASES: list[tuple] = [
    # (id, category, input, profile_state, intent, items, delivery, customer_state_in_text)
    # --- clean English ----------------------------------------------------------------------------
    ("clean-01", "clean", "Need 100 black round neck t-shirts, sizes S:20 M:40 L:40, screen print on front.", "CG", "new_quote", [tee("black", 100, size_mix="S:20, M:40, L:40", **S)], None, None),
    ("clean-02", "clean", "Please quote 60 white t-shirts with DTF print on the back, sizes M 30 L 30.", "CG", "new_quote", [tee("white", 60, size_mix="M:30, L:30", print_type="dtf", placement="back")], None, None),
    ("clean-03", "clean", "We need 25 navy polo shirts with embroidered logo on the chest. Sizes M:10, L:10, XL:5.", "MH", "new_quote", [item("navy polo t-shirt", 25, size_mix="M:10, L:10, XL:5", print_type="embroidery", placement="chest")], None, None),
    ("clean-04", "clean", "Quote for 40 black hoodies, screen print front, sizes M 20 L 20.", "CG", "new_quote", [item("black hoodie", 40, size_mix="M:20, L:20", **S)], None, None),
    ("clean-05", "clean", "Requesting a quote: 10 corporate blazers, navy colour, embroidered logo. Sizes 38:4, 40:4, 42:2.", "KA", "new_quote", [item("corporate blazer", 10, size_mix="38:4, 40:4, 42:2", color="navy", logo="embroidery")], None, None),
    ("clean-06", "clean", "Main gate, 10 ft wide and 7 ft high, simple design, enamel paint finish.", "CG", "new_quote", [item("ms gate", None, width_ft="10", height_ft="7", design="simple", finish="enamel")], None, None),
    ("clean-07", "clean", "Stainless steel balcony railing, 30 running feet, no glass.", "CG", "new_quote", [item("ss balcony railing", None, length_rft="30", glass="none")], None, None),
    ("clean-08", "clean", "One wardrobe 6 ft wide by 7 ft high, hinged shutters, walnut laminate.", "CG", "new_quote", [item("laminated wardrobe", 1, width_ft="6", height_ft="7", shutter="hinged", laminate="walnut")], None, None),
    ("clean-09", "clean", "Modular kitchen base cabinets, 12 running feet, BWP ply, acrylic shutters.", "MH", "new_quote", [item("modular kitchen base unit", None, length_rft="12", material="bwp_ply", shutter_finish="acrylic")], None, None),
    ("clean-10", "clean", "8 flex banners, each 6 ft x 3 ft, standard flex.", "CG", "new_quote", [item("flex banner", 8, width_ft="6", height_ft="3", material="standard")], None, None),
    # --- Hinglish ---------------------------------------------------------------------------------
    ("hing-01", "hinglish", "bhaiya 50 kaali tshirt chahiye, aage screen print, size M 25 L 25", "CG", "new_quote", [tee("black", 50, size_mix="M:25, L:25", **S)], None, None),
    ("hing-02", "hinglish", "safed tee 30 piece, peeche DTF wala print, sizes S 10 M 10 L 10", "CG", "new_quote", [tee("white", 30, size_mix="S:10, M:10, L:10", print_type="dtf", placement="back")], None, None),
    ("hing-03", "hinglish", "40 kaali aur 20 safed tshirt, front pe kadhai, sizes baad me", "CG", "new_quote", [tee("black", 40, print_type="embroidery", placement="front"), tee("white", 20, print_type="embroidery", placement="front")], None, None),
    ("hing-04", "hinglish", "hoodie chahiye 30, kaala, front screen print, M 15 L 15, Pune bhejna hai", "CG", "new_quote", [item("black hoodie", 30, size_mix="M:15, L:15", **S)], None, "Maharashtra"),
    ("hing-05", "hinglish", "gate banwana hai loha ka, 12 by 6 feet, simple design, powder coating chahiye", "CG", "new_quote", [item("ms gate", None, width_ft="12", height_ft="6", design="simple", finish="powder_coat")], None, None),
    ("hing-06", "hinglish", "seedhi ke liye SS railing 18 running feet, 12mm toughened glass ke saath", "CG", "new_quote", [item("ss railing", None, length_rft="18", glass="toughened_12mm")], None, None),
    ("hing-07", "hinglish", "2 almari banwani hai 5x7 feet, sliding shutter, white laminate", "CG", "new_quote", [item("laminated wardrobe", 2, width_ft="5", height_ft="7", shutter="sliding", laminate="white")], None, None),
    ("hing-08", "hinglish", "kitchen ka kaam hai, 10 running feet, HDHMR, laminate shutter", "CG", "new_quote", [item("modular kitchen base unit", None, length_rft="10", material="hdhmr", shutter_finish="laminate")], None, None),
    ("hing-09", "hinglish", "dukaan ke liye 4 flex chahiye 8x4 feet star flex", "CG", "new_quote", [item("flex banner", 4, width_ft="8", height_ft="4", material="star_flex")], None, None),
    ("hing-10", "hinglish", "polo tshirt 20 navy, chest pe embroidery, M 10 L 10, Mumbai office", "CG", "new_quote", [item("navy polo t-shirt", 20, size_mix="M:10, L:10", print_type="embroidery", placement="chest")], None, "Maharashtra"),
    ("hing-11", "hinglish", "bhai 100 kaali tee urgent, kal tak, aage logo screen print", "CG", "new_quote", [tee("black", 100, **S)], "kal tak", None),
    ("hing-12", "hinglish", "gate ka rate batao", "CG", "new_quote", [item("gate", None)], None, None),
    ("hing-13", "hinglish", "railing lagwani hai balcony me, kitna lagega?", "CG", "new_quote", [item("balcony railing", None)], None, None),
    ("hing-14", "hinglish", "25 hoodie kaali, peeche dtf, sizes L 15 XL 10", "CG", "new_quote", [item("black hoodie", 25, size_mix="L:15, XL:10", print_type="dtf", placement="back")], None, None),
    ("hing-15", "hinglish", "white tshirt 200 pcs, front screen print, S 50 M 50 L 50 XL 50", "CG", "new_quote", [tee("white", 200, size_mix="S:50, M:50, L:50, XL:50", **S)], None, None),
    # --- typos & slang ----------------------------------------------------------------------------
    ("typo-01", "typos", "need 60 blak tshrts frnt scren prnt M30 L30", "CG", "new_quote", [tee("black", 60, size_mix="M:30, L:30", **S)], None, None),
    ("typo-02", "typos", "wardobe 6x7ft slidng shuter, grey lamnate", "CG", "new_quote", [item("wardrobe", 1, width_ft="6", height_ft="7", shutter="sliding", laminate="grey")], None, None),
    ("typo-03", "typos", "hoody x 20 blk, embrodery on chest, M10 L10", "CG", "new_quote", [item("black hoodie", 20, size_mix="M:10, L:10", print_type="embroidery", placement="chest")], None, None),
    ("typo-04", "typos", "ss raling 15 rft no glas", "CG", "new_quote", [item("ss railing", None, length_rft="15", glass="none")], None, None),
    ("typo-05", "typos", "flx banr 10x5 vinyl x3", "CG", "new_quote", [item("flex banner", 3, width_ft="10", height_ft="5", material="vinyl")], None, None),
    ("typo-06", "typos", "pls send rate 4 50 wht tees dtf bak M 25 L 25", "CG", "new_quote", [tee("white", 50, size_mix="M:25, L:25", print_type="dtf", placement="back")], None, None),
    ("typo-07", "typos", "polo navi 30 nos embroidry chest S10 M10 L10", "CG", "new_quote", [item("navy polo t-shirt", 30, size_mix="S:10, M:10, L:10", print_type="embroidery", placement="chest")], None, None),
    ("typo-08", "typos", "gaate 8x6 ft, simpl desin, primr only", "CG", "new_quote", [item("ms gate", None, width_ft="8", height_ft="6", design="simple", finish="primer")], None, None),
    ("typo-09", "typos", "kichen 9 rft bwp ply pu finsh", "CG", "new_quote", [item("modular kitchen base unit", None, length_rft="9", material="bwp_ply", shutter_finish="pu")], None, None),
    ("typo-10", "typos", "blazr 6 pcs blk, no logo, sizes 40:3 42:3", "CG", "new_quote", [item("corporate blazer", 6, size_mix="40:3, 42:3", color="black", logo="none")], None, None),
    # --- voice-transcript style -------------------------------------------------------------------
    ("voice-01", "voice", "haan bhaiya woh na hume chahiye pachaas um 50 kaali t shirt front mein screen print aur size M pachchis L pachchis", "CG", "new_quote", [tee("black", 50, size_mix="M:25, L:25", **S)], None, None),
    ("voice-02", "voice", "hello ji gate ke baare mein tha ki twelve feet chauda six feet ooncha simple design powder coating", "CG", "new_quote", [item("ms gate", None, width_ft="12", height_ft="6", design="simple", finish="powder_coat")], None, None),
    ("voice-03", "voice", "so we need uh around forty hoodies black with dtf on the back sizes medium twenty large twenty", "CG", "new_quote", [item("black hoodie", 40, size_mix="M:20, L:20", print_type="dtf", placement="back")], None, None),
    ("voice-04", "voice", "flex banner chahiye do piece das by chaar standard wala", "CG", "new_quote", [item("flex banner", 2, width_ft="10", height_ft="4", material="standard")], None, None),
    ("voice-05", "voice", "haan toh railing balcony ki twenty running feet glass nahi chahiye", "CG", "new_quote", [item("balcony railing", None, length_rft="20", glass="none")], None, None),
    ("voice-06", "voice", "um white tshirt thirty pieces logo embroidery front sizes later batata hoon", "CG", "new_quote", [tee("white", 30, print_type="embroidery", placement="front")], None, None),
    ("voice-07", "voice", "ek wardrobe chahiye seven by seven sliding shutter laminate abhi decide nahi kiya", "CG", "new_quote", [item("wardrobe", 1, width_ft="7", height_ft="7", shutter="sliding")], None, None),
    ("voice-08", "voice", "polo navy blue twenty five pieces chest embroidery small five medium ten large ten", "CG", "new_quote", [item("navy polo t-shirt", 25, size_mix="S:5, M:10, L:10", print_type="embroidery", placement="chest")], None, None),
    # --- multi-item -------------------------------------------------------------------------------
    ("multi-01", "multi", "60 black and 40 white t-shirts, screen print front. Black M30 L30, white M20 L20.", "CG", "new_quote", [tee("black", 60, size_mix="M:30, L:30", **S), tee("white", 40, size_mix="M:20, L:20", **S)], None, None),
    ("multi-02", "multi", "Gate 10x6 simple powder coat, plus SS railing 20 rft with 8mm toughened glass.", "CG", "new_quote", [item("ms gate", None, width_ft="10", height_ft="6", design="simple", finish="powder_coat"), item("ss railing", None, length_rft="20", glass="toughened_8mm")], None, None),
    ("multi-03", "multi", "30 hoodies black DTF back M15 L15 and 20 navy polos embroidery chest M10 L10", "CG", "new_quote", [item("black hoodie", 30, size_mix="M:15, L:15", print_type="dtf", placement="back"), item("navy polo t-shirt", 20, size_mix="M:10, L:10", print_type="embroidery", placement="chest")], None, None),
    ("multi-04", "multi", "Wardrobe 6x7 sliding white laminate and kitchen 10 rft HDHMR acrylic", "CG", "new_quote", [item("wardrobe", 1, width_ft="6", height_ft="7", shutter="sliding", laminate="white"), item("modular kitchen base unit", None, length_rft="10", material="hdhmr", shutter_finish="acrylic")], None, None),
    ("multi-05", "multi", "5 flex 6x3 standard and 2 flex 10x4 vinyl", "CG", "new_quote", [item("flex banner", 5, width_ft="6", height_ft="3", material="standard"), item("flex banner", 2, width_ft="10", height_ft="4", material="vinyl")], None, None),
    ("multi-06", "multi", "100 white tees front screen S25 M25 L25 XL25 plus 10 blazers navy no logo 38:5 40:5", "DL", "new_quote", [tee("white", 100, size_mix="S:25, M:25, L:25, XL:25", **S), item("corporate blazer", 10, size_mix="38:5, 40:5", color="navy", logo="none")], None, None),
    ("multi-07", "multi", "50 kaali tee front screen M25 L25, aur ek gate 8x6 simple primer", "CG", "new_quote", [tee("black", 50, size_mix="M:25, L:25", **S), item("ms gate", None, width_ft="8", height_ft="6", design="simple", finish="primer")], None, None),
    ("multi-08", "multi", "hoodies 20 black and tshirts 30 black, both front screen print, sizes later", "CG", "new_quote", [item("black hoodie", 20, **S), tee("black", 30, **S)], None, None),
    # --- missing specs / clarification -----------------------------------------------------------
    ("miss-01", "missing", "50 black t-shirts please", "CG", "new_quote", [tee("black", 50)], None, None),
    ("miss-02", "missing", "I need some t-shirts with our logo", "CG", "new_quote", [item("t-shirt", None)], None, None),
    ("miss-03", "missing", "gate 10x6 chahiye", "CG", "new_quote", [item("ms gate", None, width_ft="10", height_ft="6")], None, None),
    ("miss-04", "missing", "wardrobe ka quote do", "CG", "new_quote", [item("wardrobe", None)], None, None),
    ("miss-05", "missing", "10 hoodies black dtf back", "CG", "new_quote", [item("black hoodie", 10, print_type="dtf", placement="back")], None, None),
    ("miss-06", "missing", "5 black tshirts screen print front M5", "CG", "new_quote", [tee("black", 5, size_mix="M:5", **S)], None, None),
    ("miss-07", "missing", "flex banner 4 pieces", "CG", "new_quote", [item("flex banner", 4)], None, None),
    ("miss-08", "missing", "100 coffee mugs with logo", "CG", "new_quote", [item("coffee mug", 100)], None, None),
    # --- cancellations ----------------------------------------------------------------------------
    ("cancel-01", "cancel", "Please cancel my order", "CG", "cancel", [], None, None),
    ("cancel-02", "cancel", "order cancel kar do bhaiya, plan change ho gaya", "CG", "cancel", [], None, None),
    ("cancel-03", "cancel", "rehne do, ab nahi chahiye", "CG", "cancel", [], None, None),
    ("cancel-04", "cancel", "We won't need the quote anymore, cancel it.", "CG", "cancel", [], None, None),
    # --- off-topic --------------------------------------------------------------------------------
    ("other-01", "off_topic", "Shop kitne baje khulti hai?", "CG", "other", [], None, None),
    ("other-02", "off_topic", "Thanks for the quick delivery last time!", "CG", "other", [], None, None),
    ("other-03", "off_topic", "Where is your shop located?", "CG", "other", [], None, None),
]
# fmt: on


def build() -> list[dict]:
    catalog = load_catalog()
    out: list[dict] = []
    for cid, category, text, profile, intent, items, delivery, text_state in CASES:
        extraction = Extraction(
            items=[
                ExtractedItem(
                    item_text=i["item_text"],
                    quantity=i["quantity"],
                    specs=[Spec(name=k, value=v) for k, v in i["specs"].items()],
                )
                for i in items
            ],
            delivery_by=delivery,
            customer_state=text_state,
        )
        expected: dict = {"intent": intent, "outcome": {"new_quote": "clarify"}.get(intent, intent)}
        if intent == "new_quote":
            result = validate(extraction, catalog)
            expected["items"] = [
                {"sku": v.sku, "quantity": v.quantity, "specs": v.specs} for v in result.items
            ]
            expected["missing"] = sorted(
                f"{v.index}:{i.code}:{i.field or ''}" for v in result.items for i in v.issues
            )
            if result.complete:
                state = state_code(profile) or state_code(text_state)
                priced = price_quote(
                    result.pricing_inputs(),
                    catalog=catalog,
                    business_state=BUSINESS_STATE,
                    customer_state=state,
                )
                expected["outcome"] = "quote"
                expected["total_paise"] = priced.totals.total_paise
        out.append(
            {
                "id": cid,
                "category": category,
                "input": text,
                "customer_state": profile,
                "ideal": {"intent": intent, "extraction": extraction.model_dump(mode="json")},
                "expected": expected,
            }
        )

    for case in json.loads(ADVERSARIAL.read_text(encoding="utf-8")):
        refused = case["expect"] in ("refused", "refused_llm")
        out.append(
            {
                "id": f"adv-{case['id']}",
                "category": "adversarial",
                "input": case["text"],
                "customer_state": "CG",
                "ideal": {"intent": "other", "extraction": Extraction().model_dump(mode="json")},
                "expected": {
                    "intent": "other",
                    "outcome": "refused" if refused else "allowed",
                    "refused_by": "llm" if case["expect"] == "refused_llm" else "rules",
                    "money_flag": case["expect"] == "quoted_flagged",
                    "rule_blocks": rule_check(case["text"]).flagged,
                },
            }
        )
    return out


if __name__ == "__main__":
    data = build()
    OUT.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {len(data)} cases to {OUT.name}")
