"""Seed a demo database with conversations in every interesting state, using the offline demo brain.

python -m scripts.seed_demo            # into KP_STORAGE_DIR (default ./storage)
python -m scripts.seed_demo --force    # even if quotes already exist
"""

import argparse
import asyncio

from app.agent.deps import DEMO_MODEL
from app.config import get_settings
from app.llm.demo import scenarios
from app.main import create_app
from app.schemas.decision import Approve, DecisionAdapter

SCENES = {sc["id"]: sc for sc in scenarios()}


async def seed(force: bool = False) -> dict[str, str]:
    settings = get_settings().model_copy(update={"llm_model": DEMO_MODEL})
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        runtime, repo = app.state.runtime, app.state.repo
        if await repo.list_quotes() and not force:
            print("Quotes already exist; use --force to add the demo set anyway.")
            return {}

        async def say(conv: str, who: dict, text: str):  # noqa: ANN202
            return await runtime.handle_message(conv, text, customer=who)

        ravi = {"name": "Ravi Kumar", "phone": "+91 98260 11111", "state": "CG"}
        asha = {"name": "Asha Mehta", "phone": "+91 98200 22222", "state": "MH"}
        imran = {"name": "Imran Shaikh", "phone": "+91 99000 33333", "state": None}
        meera = {"name": "Meera Iyer", "phone": "+91 94440 44444", "state": "TN"}
        karan = {"name": "Karan Singh", "phone": "+91 98100 55555", "state": "DL"}
        sunil = {"name": "Sunil", "phone": "", "state": "CG"}

        out: dict[str, str] = {}
        r = await say("seed_ravi", ravi, SCENES["complete-apparel"]["message"])
        out["Ravi (awaiting approval)"] = r.status

        r = await say("seed_asha", asha, SCENES["fabrication-multi"]["message"])
        await runtime.decide(r.quote_id, Approve(action="approve"))
        out["Asha (sent, follow-up scheduled)"] = (await repo.get_quote(r.quote_id)).status

        r = await say("seed_imran", imran, SCENES["hinglish-incomplete"]["message"])
        out["Imran (needs clarification)"] = r.status

        r = await say("seed_meera", meera, "50 black hoodies, DTF on back, M 20 L 20 XL 10")
        discount = {"action": "edit", "edits": {"discount": {"kind": "percent", "value": 500}}}
        await runtime.decide(r.quote_id, DecisionAdapter.validate_python(discount))
        out["Meera (edited to revision 2, awaiting)"] = (await repo.get_quote(r.quote_id)).status

        r = await say("seed_karan", karan, SCENES["complete-apparel"]["message"])
        await runtime.decide(r.quote_id, Approve(action="approve"))
        await say("seed_karan", karan, "YES")
        out["Karan (accepted)"] = (await repo.get_quote(r.quote_id)).status

        r = await say("seed_sunil", sunil, SCENES["injection"]["message"])
        out["Sunil (injection refused)"] = "refused" if r.quote_id is None else r.status

        for label, status in out.items():
            print(f"  {label:45} {status}")
        return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    asyncio.run(seed(parser.parse_args().force))
