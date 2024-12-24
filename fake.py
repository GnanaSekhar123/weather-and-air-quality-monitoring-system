import sqlite3
from datetime import datetime, timedelta
import random

# Connect to SQLite database (or create it if it doesn't exist)
connection = sqlite3.connect("database.sqlite3")
cursor = connection.cursor()

def fetch_data_for_chart():
    # Retrieve unique user IDs from the table
    cursor.execute("SELECT DISTINCT user_id FROM carbon_result")
    user_ids = [row[0] for row in cursor.fetchall()]

    # Prepare data for the chart
    data = {}
    for user_id in user_ids:
        # Fetch date and total_carbon_footprint for each user
        cursor.execute("""
            SELECT date, total_carbon_footprint
            FROM carbon_result
            WHERE user_id = ?
            ORDER BY date ASC
        """, (user_id,))
        results = cursor.fetchall()

        # Store data for each user in a dictionary
        dates = [datetime.strptime(row[0], "%Y-%m-%d").date() for row in results]
        carbon_values = [row[1] for row in results]
        data[user_id] = (dates, carbon_values)
    
    return data
connection.close()
