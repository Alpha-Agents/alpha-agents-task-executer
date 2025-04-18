from supabase import create_client, Client
import json
import os
from dotenv import load_dotenv
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def conversation_exists(job_id):
    response = supabase.table("conversations").select("job_id").eq("job_id", job_id).limit(1).execute()
    return len(response.data) > 0

def update_trade_signal(job_id, trade_signal):
    if conversation_exists(job_id):
        supabase.table("conversations").update({
            "trade_signal": trade_signal
        }).eq("job_id", job_id).execute()

def get_conversation_by_id(job_id):
    response = supabase.table("conversations").select("conversation_history").eq("job_id", job_id).limit(1).execute()

    if not response.data:
        raise ValueError(f"No conversation found for job_id {job_id}")

    return response.data[0]["conversation_history"]

def add_message(job_id, new_message):
    response = supabase.table("conversations").select("conversation_history").eq("job_id", job_id).limit(1).execute()

    if not response.data:
        raise ValueError(f"No conversation found for job_id {job_id}")

    conversation_history = response.data[0]["conversation_history"]
    conversation_history.append(new_message)

    supabase.table("conversations").update({
        "conversation_history": conversation_history
    }).eq("job_id", job_id).execute()

def add_conversation(job_id, conversation_history, user_email, symbol, agent):
    if conversation_exists(job_id):
        return

    supabase.table("conversations").insert({
        "job_id": job_id,
        "conversation_history": conversation_history,
        "user_email": user_email,
        "symbol": symbol,
        "agent": agent
    }).execute()

def deduct_user_credits(email: str, amount: int):
    # Fetch user by email
    response = supabase.table("users").select("monthly_credits", "extra_credits").eq("email_id", email).limit(1).execute()

    if not response.data:
        raise ValueError(f"No user found with email: {email}")

    user = response.data[0]
    monthly_credits = int(user.get("monthly_credits", 0))
    extra_credits = int(user.get("extra_credits") or 0)

    # Deduction logic using integers only
    to_deduct = amount

    if extra_credits >= to_deduct:
        extra_credits -= to_deduct
        to_deduct = 0
    else:
        to_deduct -= extra_credits
        extra_credits = 0
        monthly_credits -= to_deduct  # can go negative

    # Update in DB
    supabase.table("users").update({
        "extra_credits": extra_credits,
        "monthly_credits": monthly_credits
    }).eq("email_id", email).execute()

    print(f"[{email}] - {amount} credits → extra: {extra_credits}, monthly: {monthly_credits}")
