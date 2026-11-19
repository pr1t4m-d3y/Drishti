"""Admin UI: chat with the copilot, see cited sources, trace id and per-request metrics, and
approve or reject recommended interventions (the human-in-the-loop step).

    streamlit run ui/streamlit_app.py
Env: DRISHTI_API_URL (default http://localhost:8000), DRISHTI_API_KEY
"""

from __future__ import annotations

import os

import httpx
import streamlit as st

API = os.getenv("DRISHTI_API_URL", "http://localhost:8000")
KEY = os.getenv("DRISHTI_API_KEY", "")

st.set_page_config(page_title="Drishti copilot", page_icon="👁", layout="wide")
st.title("Drishti: credit-risk copilot")
st.caption("Recommendations only. Every action requires human approval; nothing is executed automatically.")

headers = {"X-API-Key": KEY}
client = httpx.Client(base_url=API, headers=headers, timeout=120)

with st.sidebar:
    st.subheader("Connection")
    st.text(API)
    try:
        h = client.get("/health").json()
        st.success(f"API up, {h['customers']:,} customers")
    except Exception as e:  # noqa: BLE001
        st.error(f"API unreachable: {e}")
    if st.button("New session"):
        st.session_state.pop("session_id", None)
        st.session_state["messages"] = []
    st.markdown("**Try:**")
    for ex in (
        "Which 10 customers are most at risk this month and why?",
        "What can we offer customer #4521 under our policies?",
        "Is a 10-day EMI extension allowed for a customer with two missed payments?",
        "Now draft a counselling note for the top 3.",
    ):
        if st.button(ex, key=ex):
            st.session_state["pending"] = ex

chat_tab, approvals_tab = st.tabs(["Copilot", "Pending approvals"])

with chat_tab:
    st.session_state.setdefault("messages", [])
    for m in st.session_state["messages"]:
        with st.chat_message(m["role"]):
            st.markdown(m["text"])
            if m.get("meta"):
                meta = m["meta"]
                cols = st.columns(4)
                cols[0].metric("Latency", f"{meta['metrics'].get('latency_s', 0):.1f}s")
                cols[1].metric("Tokens in/out", f"{meta['metrics'].get('input_tokens', 0)}/{meta['metrics'].get('output_tokens', 0)}")
                cost = meta["metrics"].get("cost_usd")
                cols[2].metric("Cost", "n/a" if cost is None else f"${cost:.5f}")
                cols[3].metric("Agent steps", meta["metrics"].get("agent_steps", 0))
                st.caption(f"trace id: `{meta['trace_id']}`  |  grounded: {meta.get('grounded')}")
                if meta.get("citations"):
                    with st.expander(f"Sources ({len(meta['citations'])})"):
                        for c in meta["citations"]:
                            st.markdown(f"- **{c.get('doc')}**, {c.get('section')}, p.{c.get('page')}")

    prompt = st.chat_input("Ask about risk, policy or an intervention") or st.session_state.pop("pending", None)
    if prompt:
        st.session_state["messages"].append({"role": "user", "text": prompt})
        with st.spinner("Agents working..."):
            r = client.post("/chat", json={"message": prompt, "session_id": st.session_state.get("session_id")})
        if r.status_code == 200:
            j = r.json()
            st.session_state["session_id"] = j["session_id"]
            st.session_state["messages"].append({"role": "assistant", "text": j["answer"], "meta": j})
        else:
            st.session_state["messages"].append({"role": "assistant", "text": f"Error: {r.json().get('error', {}).get('message', r.text)}"})
        st.rerun()

with approvals_tab:
    items = client.get("/interventions", params={"status": "proposed"}).json()
    if not isinstance(items, list) or not items:
        st.info("No pending recommendations.")
    else:
        for it in items:
            with st.container(border=True):
                st.markdown(f"**Customer {it['customer_id']}**: {it['action_type']}")
                st.write(it["rationale"])
                for c in it["citations"]:
                    st.caption(f"{c.get('doc')}, {c.get('section')}, p.{c.get('page')}")
                note = st.text_input("Decision note", key=f"n{it['id']}")
                a, b = st.columns(2)
                if a.button("Approve", key=f"a{it['id']}"):
                    client.post(f"/interventions/{it['id']}/decision", json={"decision": "approved", "note": note})
                    st.rerun()
                if b.button("Reject", key=f"r{it['id']}"):
                    client.post(f"/interventions/{it['id']}/decision", json={"decision": "rejected", "note": note})
                    st.rerun()
