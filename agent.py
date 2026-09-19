import json
import time
from datetime import datetime
import requests
from supabase import create_client
from google import genai

SUPABASE_URL = "https://drevzwirzmsztttsigih.supabase.co/"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRyZXZ6d2lyem1zenR0dHNpZ2loIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODk4NDI3NjcsImV4cCI6MjEwNTQxODc2N30.Z4F-MsqntciQIwBemN7diROvnrcx95mFx1XRHKYqiww"
GEMINI_KEY = "AQ.Ab8RN6I5cDm6Xrt1u3SCjv4V9YD7Vt43cqMWOAE67Xo6afliIQ"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
ai_client = genai.Client(api_key=GEMINI_KEY)

INTERVAL_SECONDS = 15 * 60

def get_live_btc_price():
    url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
    res = requests.get(url, timeout=10).json()
    return float(res["price"])

def run_trading_cycle():
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n==========================================")
    print(f"[{now_str}] Autonomous Agent by Asad — Heartbeat")
    print(f"==========================================")

    res = supabase.table("agent_state").select("*").eq("id", 1).execute()
    if not res.data:
        return False

    state = res.data[0]
    if state["status"] == "DEAD":
        print("🚨 AGENT IS DEAD. Halted.")
        return False

    balance = float(state["balance"])
    btc_holding = float(state["holdings_btc"])
    btc_price = get_live_btc_price()
    total_net_worth = balance + (btc_holding * btc_price)

    print(f"Portfolio Net Worth: ${total_net_worth:.2f} | BTC Price: ${btc_price:.2f}")

    if total_net_worth < 0.50:
        print("☠️ AGENT TERMINATED. STATUS: DEAD")
        supabase.table("agent_state").update({
            "status": "DEAD",
            "last_action": "DEAD",
            "last_reason": "Capital depleted below threshold. Agent perished.",
            "last_checked": "now()"
        }).eq("id", 1).execute()
        return False

    prompt = f"""
    You are an autonomous AI trading agent named 'Autonomous Agent by Asad'.
    Capital: ${balance:.2f} USDT | BTC: {btc_holding:.6f} | Price: ${btc_price:.2f} | Total Equity: ${total_net_worth:.2f}

    Rules:
    - If you lose everything, you die.
    - If you have cash and 0 BTC, evaluate BUY vs HOLD.
    - If you hold BTC, evaluate SELL vs HOLD.
    - Factor in 0.1% exchange fee.

    Respond ONLY in raw JSON:
    {{"action": "BUY" or "SELL" or "HOLD", "reason": "1 short crisp sentence explaining your exact market thesis."}}
    """

    try:
        response = ai_client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt
        )
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_text)
        action = data.get("action", "HOLD").upper()
        reason = data.get("reason", "Observing price structure before entering trade.")
    except Exception as e:
        action = "HOLD"
        reason = f"Observation mode. Error: {str(e)[:40]}"

    print(f"AI Decision: {action} | Reasoning: {reason}")

    new_balance = balance
    new_btc = btc_holding

    if action == "BUY" and balance >= 4.50:
        spend = balance * 0.999
        new_btc = spend / btc_price
        new_balance = 0.0
    elif action == "SELL" and btc_holding > 0:
        proceeds = (btc_holding * btc_price) * 0.999
        new_balance = proceeds
        new_btc = 0.0

    supabase.table("agent_state").update({
        "balance": round(new_balance, 2),
        "holdings_btc": new_btc,
        "last_action": action,
        "last_reason": reason,
        "last_checked": "now()"
    }).eq("id", 1).execute()

    print("Synced with Supabase.")
    return True

if __name__ == "__main__":
    run_trading_cycle()
