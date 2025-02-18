import psycopg2

# Database credentials
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

def add_agent(user_email, system_prompt, agent_name):
    try:
        conn = get_connection()
        cur = conn.cursor()
        query = "INSERT INTO agents (user_email, system_prompt, agent_name) VALUES (%s, %s, %s);"
        cur.execute(query, (user_email, system_prompt, agent_name))
        conn.commit()
        cur.close()
        conn.close()
        print("Agent added successfully.")
    except Exception as e:
        print(f"Error adding agent: {e}")

def delete_agent(agent_id):
    try:
        conn = get_connection()
        cur = conn.cursor()
        query = "DELETE FROM agents WHERE agent_id = %s;"
        cur.execute(query, (agent_id,))
        conn.commit()
        cur.close()
        conn.close()
        print("Agent deleted successfully.")
    except Exception as e:
        print(f"Error deleting agent: {e}")

def update_agent_name(agent_id, new_agent_name):
    try:
        conn = get_connection()
        cur = conn.cursor()
        query = "UPDATE agents SET agent_name = %s WHERE agent_id = %s;"
        cur.execute(query, (new_agent_name, agent_id))
        conn.commit()
        cur.close()
        conn.close()
        print("Agent name updated successfully.")
    except Exception as e:
        print(f"Error updating agent name: {e}")

def update_agent_prompt(agent_id, new_system_prompt):
    try:
        conn = get_connection()
        cur = conn.cursor()
        query = "UPDATE agents SET system_prompt = %s WHERE agent_id = %s;"
        cur.execute(query, (new_system_prompt, agent_id))
        conn.commit()
        cur.close()
        conn.close()
        print("Agent system prompt updated successfully.")
    except Exception as e:
        print(f"Error updating agent system prompt: {e}")

# if __name__ == "__main__":
    # Example usage
    # add_agent("test@example.com", "Test system prompt", "Test Agent")
    # update_agent_name(1, "Updated Agent Name")
    # update_agent_prompt(1, "Updated system prompt")
    # delete_agent(1)
