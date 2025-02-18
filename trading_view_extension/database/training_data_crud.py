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

def add_training_data(image_url, user_email, agent_id, analysis, user_feedback):
    try:
        conn = get_connection()
        cur = conn.cursor()
        query = """
        INSERT INTO training_data (image_url, user_email, agent_id, analysis, user_feedback)
        VALUES (%s, %s, %s, %s, %s);
        """
        cur.execute(query, (image_url, user_email, agent_id, analysis, user_feedback))
        conn.commit()
        cur.close()
        conn.close()
        print("Training data added successfully.")
    except Exception as e:
        print(f"Error adding training data: {e}")

def delete_training_data(image_url):
    try:
        conn = get_connection()
        cur = conn.cursor()
        query = "DELETE FROM training_data WHERE image_url = %s;"
        cur.execute(query, (image_url,))
        conn.commit()
        cur.close()
        conn.close()
        print("Training data deleted successfully.")
    except Exception as e:
        print(f"Error deleting training data: {e}")

def update_training_analysis(image_url, new_analysis):
    try:
        conn = get_connection()
        cur = conn.cursor()
        query = "UPDATE training_data SET analysis = %s WHERE image_url = %s;"
        cur.execute(query, (new_analysis, image_url))
        conn.commit()
        cur.close()
        conn.close()
        print("Training data analysis updated successfully.")
    except Exception as e:
        print(f"Error updating training data analysis: {e}")

def update_training_feedback(image_url, new_feedback):
    try:
        conn = get_connection()
        cur = conn.cursor()
        query = "UPDATE training_data SET user_feedback = %s WHERE image_url = %s;"
        cur.execute(query, (new_feedback, image_url))
        conn.commit()
        cur.close()
        conn.close()
        print("Training data feedback updated successfully.")
    except Exception as e:
        print(f"Error updating training data feedback: {e}")

# if __name__ == "__main__":
#     # Example usage
#     add_training_data("s3://bucket/image1.jpg", "test@example.com", 1, "Initial analysis", "Initial feedback")
#     update_training_analysis("s3://bucket/image1.jpg", "Updated AI analysis")
#     update_training_feedback("s3://bucket/image1.jpg", "Updated user feedback")
#     delete_training_data("s3://bucket/image1.jpg")
