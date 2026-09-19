import os
import json
import requests
from datetime import datetime
from supabase import create_client
from google import genai

SUPABASE_URL = "https://drevzwirzmsztttsigih.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRyZXZ6d2lyem1zenR0dHNpZ2loIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODk4NDI3NjcsImV4cCI6MjEwNTQxODc2N30.Z4F-MsqntciQIwBemN7diROvnrcx95mFx1XRHKYqiww"
GEMINI_KEY = "AQ.Ab8RN6I5cDm6Xrt1u3SCjv4V9YD7Vt43cqMWOAE67Xo6afliIQ" # <-- Apni Gemini API key yahan paste karein

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
ai_client = genai.Client(api_key=GEMINI_KEY)

def get_live_btc_price():
    headers = {"User-Agent": "Mozilla/5.0"}
    
    # Provider 1: Coinbase Public API (Cloud servers par hamesha unblocked hoti hai)
    try:
        res = requests.get("https://api.coinbase.com/v2/prices/spot?currency=USD", headers=headers, timeout=5).json()
        if "data" in res and "amount" in res["data"]:
            return float(res["data"]["amount"])
    except Exception:
        pass

    # Provider 2: CoinGecko
    try:
        res = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", headers=headers, timeout=5).json()
        if "bitcoin" in res and "usd" in res["bitcoin"]:
            return float(res["bitcoin"]["usd"])
    except Exception:
        pass

    # Provider 3: Binance Public
    try:
        res = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", headers=headers, timeout=5).json()
        if "price" in res:
            return float(res["price"])
    except Exception:
        pass

    raise RuntimeError("Could not retrieve price from any source")

def run_trading_cycle():
    print("==============================================")
    print(f"[{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}] Autonomous Agent by Asad Naseer")
    print("==============================================")

    res = supabase.table("agent_state").select("*").eq("id", 1).execute()
    state = res.data[0]

    if state["status"] == "DEAD":
        print("AGENT STATUS: DEAD. Trading halted.")
        return

    btc_price = get_live_btc_price()
    balance = float(state["balance"])
    btc_holding = float(state["holdings_btc"])
    net_worth = balance + (btc_holding * btc_price)

    print(f"Current State -> Cash: ${balance:.2f} | BTC: {btc_holding:.6f} | Live Price: ${btc_price:.2f} | Net Worth: ${net_worth:.2f}")

    if net_worth <= 0.10:
        print("AGENT DEATH TRIGGERED: Capital depleted to 0.")
        supabase.table("agent_state").update({"status": "DEAD", "balance": 0.0, "holdings_btc": 0.0}).eq("id", 1).execute()
        return

    prompt = f"""
    You are an autonomous AI trading agent.
    Current USDT Cash: ${balance:.2f}
    Current BTC Holdings: {btc_holding:.6f}
    Live BTC Price: ${btc_price:.2f}
    Total Portfolio Value: ${net_worth:.2f}

    Survival Rule: If total portfolio drops to $0, you die. Protect capital.
    - If you hold cash and identify upside, choose BUY.
    - If you hold BTC and want to secure profit or avoid a drop, choose SELL.
    - Otherwise, choose HOLD.

    Reply ONLY with valid JSON (no markdown formatting):
    {{"action": "BUY" or "SELL" or "HOLD", "reason": "brief 1-sentence reasoning"}}
    """

    response = ai_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    clean_text = response.text.replace("```json", "").replace("```", "").strip()
    data = json.loads(clean_text)
    action = data.get("action", "HOLD").upper()
    reason = data.get("reason", "Scanning price patterns")

    print(f"AI Decision: {action}")
    print(f"Reason: {reason}")

    new_balance = balance
    new_btc = btc_holding

    if action == "BUY" and balance >= 4.50:
        spend = balance * 0.999
        new_btc = spend / btc_price
        new_balance = 0.0
        print(f"Executed BUY: Acquired {new_btc:.6f} BTC")
    elif action == "SELL" and btc_holding > 0:
        proceeds = (btc_holding * btc_price) * 0.999
        new_balance = proceeds
        new_btc = 0.0
        print(f"Executed SELL: Converted to ${new_balance:.2f} USDT")
    else:
        print("Executed HOLD: Position maintained")

    supabase.table("agent_state").update({
        "balance": round(new_balance, 2),
        "holdings_btc": new_btc,
        "last_checked": "now()"
    }).eq("id", 1).execute()

    print("State successfully synced with Supabase.")

if __name__ == "__main__":
    run_trading_cycle()
