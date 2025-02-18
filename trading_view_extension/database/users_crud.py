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

def add_user(email, password, plan, total_credits, credits_used, subscription_date, credit_refill_date):
        try:
            conn = get_connection()
            cur = conn.cursor()
            query = """
            INSERT INTO users (email, password, plan, total_credits, credits_used, subscription_date, credit_refill_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s);
            """
            cur.execute(query, (email, password, plan, total_credits, credits_used, subscription_date, credit_refill_date))
            conn.commit()
            cur.close()
            conn.close()
            print("User added successfully.")
        except Exception as e:
            print(f"Error adding user: {e}")

def delete_user(email):
    try:
        conn = get_connection()
        cur = conn.cursor()
        query = "DELETE FROM users WHERE email = %s;"
        cur.execute(query, (email,))
        conn.commit()
        cur.close()
        conn.close()
        print("User deleted successfully.")
    except Exception as e:
        print(f"Error deleting user: {e}")

def update_user_field(email, field, value):
    try:
        conn = get_connection()
        cur = conn.cursor()
        query = f"UPDATE users SET {field} = %s WHERE email = %s;"
        cur.execute(query, (value, email))
        conn.commit()
        cur.close()
        conn.close()
        print(f"User {field} updated successfully.")
    except Exception as e:
        print(f"Error updating user {field}: {e}")

def update_user_credits(email, total_credits, credits_used):
    try:
        credits_remaining = total_credits - credits_used
        conn = get_connection()
        cur = conn.cursor()
        query = "UPDATE users SET total_credits = %s, credits_used = %s, credits_remaining = %s WHERE email = %s;"
        cur.execute(query, (total_credits, credits_used, credits_remaining, email))
        conn.commit()
        cur.close()
        conn.close()
        print("User credits updated successfully.")
    except Exception as e:
        print(f"Error updating user credits: {e}")

if __name__ == "__main__":
    # Example usage
    add_user("shruti@gmail.com", "password", "premium", 100, 10, "2025-01-01", "2025-02-01")
#     update_user_field("test@example.com", "plan", "enterprise")
#     update_user_field("test@example.com", "password", "newsecurepassword")
#     update_user_credits("test@example.com", 200, 50)
#     update_user_field("test@example.com", "subscription_date", "2025-03-01")
#     update_user_field("test@example.com", "credit_refill_date", "2025-04-01")
#     delete_user("test@example.com")
