import psycopg2
from psycopg2 import sql

def create_tables():
    try:
        # Database credentials
        RDS_ENDPOINT = "database-1.c7mcu4qq0ofd.us-east-1.rds.amazonaws.com"
        RDS_PORT = 5432
        RDS_DB_NAME = "ATS"
        RDS_USERNAME = "postgres_admin"
        RDS_PASSWORD = "TLYX0mxibUR1yakz"

        # Establish connection
        conn = psycopg2.connect(
            host=RDS_ENDPOINT,
            port=RDS_PORT,
            database=RDS_DB_NAME,
            user=RDS_USERNAME,
            password=RDS_PASSWORD
        )
        
        cur = conn.cursor()
        
        # SQL Queries to create tables
        # queries = [
        #     """
        #     CREATE TABLE IF NOT EXISTS users (
        #         email VARCHAR(255) PRIMARY KEY,
        #         password VARCHAR(255) NOT NULL,
        #         plan VARCHAR(50),
        #         total_credits INT DEFAULT 0,
        #         credits_used INT DEFAULT 0,
        #         credits_remaining INT GENERATED ALWAYS AS (total_credits - credits_used) STORED,
        #         subscription_date DATE,
        #         credit_refill_date DATE
        #     );
        #     """,
        #     """
        #     CREATE TABLE IF NOT EXISTS agents (
        #         agent_id SERIAL PRIMARY KEY,
        #         user_email VARCHAR(255) REFERENCES users(email) ON DELETE CASCADE,
        #         system_prompt TEXT,
        #         agent_name VARCHAR(100)
        #     );
        #     """,
        #     """
        #     CREATE TABLE IF NOT EXISTS training_data (
        #         image_url TEXT PRIMARY KEY,  -- Image URL is stored in Amazon S3
        #         user_email VARCHAR(255) REFERENCES users(email) ON DELETE CASCADE,
        #         agent_id INT REFERENCES agents(agent_id) ON DELETE CASCADE,
        #         analysis TEXT,
        #         user_feedback TEXT
        #     );
        #     """
        # ]
        
        # Execute each query
        # for query in queries:
        #     cur.execute(query)
        
        # Commit changes
        # conn.commit()
        # print("Tables created successfully.")
        
        # Check if tables exist
        check_query = """
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name IN ('users', 'agents', 'training_data');
        """
        cur.execute(check_query)
        tables = cur.fetchall()
        print("Existing tables:", [table[0] for table in tables])
        
        # Close cursor and connection
        cur.close()
        conn.close()
        print("Connection closed successfully.")
    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    create_tables()
