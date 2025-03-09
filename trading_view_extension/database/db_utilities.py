import psycopg2
from psycopg2.extras import Json

RDS_ENDPOINT = "database-1.c7mcu4qq0ofd.us-east-1.rds.amazonaws.com"
RDS_PORT = 5432
RDS_DB_NAME = "ATS"
RDS_USERNAME = "postgres_admin"
RDS_PASSWORD = "TLYX0mxibUR1yakz"

def get_connection():
    return psycopg2.connect(
        host=RDS_ENDPOINT,
        port=RDS_PORT,
        database=RDS_DB_NAME,
        user=RDS_USERNAME,
        password=RDS_PASSWORD
    )

def conversation_exists(job_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT 1 FROM conversations WHERE job_id = %s LIMIT 1", (job_id,))
    exists = cur.fetchone() is not None

    cur.close()
    conn.close()

    return exists


def get_conversation_by_id(job_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT conversation_history FROM conversations WHERE job_id = %s", (job_id,))
    result = cur.fetchone()

    cur.close()
    conn.close()

    if result is None:
        raise ValueError(f"No conversation found for job_id {job_id}")

    return result[0]  # This is the actual list of messages


def add_message(job_id, new_message):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT conversation_history FROM conversations WHERE job_id = %s", (job_id,))
    result = cur.fetchone()
    if not result:
        raise ValueError(f"No conversation found for job_id {job_id}")

    conversation_history = result[0]
    conversation_history.append(new_message)

    cur.execute("UPDATE conversations SET conversation_history = %s WHERE job_id = %s", (Json(conversation_history), job_id))
    conn.commit()
    cur.close()
    conn.close()

def add_conversation(job_id, conversation_history):
    if conversation_exists(job_id):
        return  # Conversation already exists, no need to insert again

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO conversations (job_id, conversation_history)
        VALUES (%s, %s)
    """, (job_id, Json(conversation_history)))

    conn.commit()
    cur.close()
    conn.close()
