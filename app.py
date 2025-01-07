from flask import Flask, render_template, request, session, redirect,jsonify,url_for
from dotenv import load_dotenv
import os
import sqlite3
from datetime import datetime,timezone
import requests
from forms import CarbonTrackerForm
import webbrowser as web
from threading import Timer
#from flask_session import Session
#from flask_cors import CORS
load_dotenv()
#api keys
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
AQI_API_KEY = os.getenv("AQI_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

app = Flask(__name__, template_folder="./templates", static_folder="./static")
app.secret_key = 'infosys'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # Session timeout (1 hour)
#cors = CORS(app, resources={r"/api/": {"origins": ""}})
# Database connection setup
connection = sqlite3.connect('./database.sqlite3', check_same_thread=False)
cursor = connection.cursor()

# API keys
#WEATHER_API_KEY = "b38afbc193795726083763cb8303718b"
#AQI_API_KEY = "af24c2ce21ec3076cdc8295685020505"
#NEWS_API_KEY = "pub_60491a68299253d0f8fb3af5da4a31facb78f"
cord={}
@app.route('/admin', methods=['GET', 'POST'])
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    """
    Displays the admin dashboard. Only accessible by the admin.
    """
    if 'username' not in session:
        return redirect('/login')  # Redirect to login if the user is not logged in

    username = session.get('username')
    cursor.execute("SELECT is_admin FROM infosys WHERE username=?", (username,))
    user = cursor.fetchone()
    
    if user and user[0] == 1:  # Check if the user is an admin
        # Fetch all users
        cursor.execute("SELECT * FROM infosys")
        users = cursor.fetchall()
        
        # Fetch posts with usernames (join community_posts and infosys on username)
        cursor.execute("""
            SELECT community_posts.id, community_posts.title, infosys.username,community_posts.likes
            FROM community_posts 
            JOIN infosys ON community_posts.username = infosys.username
        """)
        posts = cursor.fetchall()

        # Fetch comments
        cursor.execute("SELECT * FROM comments")
        comments = cursor.fetchall()
        # Fetch leaderboard data
        cursor.execute(""" 
            SELECT user_id, city, 
                   SUM(transport_distance * 0.2) + 
                   SUM(previous_month_usage * 0.4) + 
                   SUM(todays_usage * 0.3) + 
                   SUM((dry_waste * 0.1) + (wet_waste * 0.1)) AS total_emissions
            FROM carbon_tracker
            GROUP BY user_id, city
            ORDER BY total_emissions ASC
        """)
        leaderboard_data = cursor.fetchall()
        
        leaderboard = [
            {"user_id": row[0], "city": row[1], "total_emissions": round(row[2], 2), "rank": index + 1}
            for index, row in enumerate(leaderboard_data)
        ]


        # Handle user addition via POST request
        if request.method == 'POST':
            if 'add_post' in request.form:
                # Handling adding a post
                new_title = request.form['title']
                if not new_title:
                    return "Post title is required", 400

                cursor.execute("INSERT INTO community_posts (title, username, likes) VALUES (?, ?, ?)", 
                               (new_title, username, 0))  # Admin adds the post
                connection.commit()
                return redirect('/admin')  # Redirect to refresh the post list

            elif 'add_user' in request.form:
                # Handling adding a user
                new_username = request.form['new_username']
                new_password = request.form['new_password']  # Store plain password
                is_admin = 0  # Default to non-admin user

                try:
                    cursor.execute("INSERT INTO infosys (username, password, is_admin) VALUES (?, ?, ?)", 
                                   (new_username, new_password, is_admin))  # Store plain password
                    connection.commit()
                    return redirect('/admin')  # Redirect to refresh user list
                except Exception as e:
                    print(f"Error: {e}")
                    return "An error occurred while adding the user.", 500

        # Return admin page with all data
        return render_template('admin.html', users=users, posts=posts, comments=comments,leaderboard=leaderboard)
    else:
        # Redirect non-admin users to the homepage or another appropriate page
        return redirect('/index')  # If not an admin, redirect to the user dashboard

@app.route('/delete_user/<string:user_id>', methods=['GET', 'POST'])
def delete_user(user_id):
    """
    Admin can delete a user by username.
    """
    try:
        if 'username' in session:
            username = session['username']
            cursor.execute("SELECT is_admin FROM infosys WHERE username=?", (username,))
            user = cursor.fetchone()

            if user and user[0] == 1:  # Admin check
                cursor.execute("DELETE FROM infosys WHERE username=?", (user_id,))
                connection.commit()
                return redirect('/admin')  # Redirect to admin page after deletion
        return redirect('/login')
    except Exception as e:
        print(f"Error: {e}")
        return "An error occurred while deleting the user.", 500

@app.route('/delete_post/<int:post_id>', methods=['GET', 'POST'])
def delete_post(post_id):
    """
    Admin can delete a post by post_id.
    """
    try:
        if 'username' in session:
            username = session['username']
            cursor.execute("SELECT is_admin FROM infosys WHERE username=?", (username,))
            user = cursor.fetchone()

            if user and user[0] == 1:  # Admin check
                cursor.execute("DELETE FROM community_posts WHERE id=?", (post_id,))
                cursor.execute("DELETE FROM comments WHERE post_id=?", (post_id,))
                cursor.execute("DELETE FROM post_likes WHERE post_id=?", (post_id,))
                connection.commit()
                return redirect('/admin')  # Redirect to admin page after deletion
        return redirect('/login')
    except Exception as e:
        print(f"Error: {e}")
        return "An error occurred while deleting the post.", 500


@app.route('/delete_comment/<int:comment_id>', methods=['GET', 'POST'])
def delete_comment(comment_id):
    """
    Admin can delete a comment by comment_id.
    """
    try:
        if 'username' in session:
            username = session['username']
            cursor.execute("SELECT is_admin FROM infosys WHERE username=?", (username,))
            user = cursor.fetchone()

            if user and user[0] == 1:  # Admin check
                cursor.execute("DELETE FROM comments WHERE id=?", (comment_id,))
                connection.commit()
                return redirect('/admin')  # Redirect to admin page after deletion
        return redirect('/login')
    except Exception as e:
        print(f"Error: {e}")
        return "An error occurred while deleting the comment.", 500


@app.route('/')
def home():
    """
    Displays the home page (default page after registration).
    """
    return render_template("home.html")

@app.route('/index')
def index():
    """
    Displays the main dashboard (after login).
    """
    if 'username' in session:
        city = request.args.get('city', 'Thiruvananthapuram, India')  # Default city
        return render_template("index.html", username=session['username'])
    else:
        return redirect('/login')

@app.route('/login', methods=['POST', 'GET'])
def login():
    """
    Handles user login and redirects to the dashboard (index.html).
    """
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Query the database for the provided username and password
        cursor.execute("SELECT * FROM infosys WHERE username=? AND password=?", (username, password))
        user = cursor.fetchone()
        
        if user:
            # Store the username in the session
            session['username'] = username
            session['userId'] = user[0]
            session['is_admin'] = user[2]
            session.permanent = True
            return redirect('/index')  # Redirect to the dashboard
        else:
            return render_template('login.html', error="Invalid username or password")  # Show error

    return render_template('login.html')

@app.route('/register', methods=['POST', 'GET'])
def register():
    """
    Handles user registration and redirects to the home page (home.html) upon success.
    """
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Check if username already exists
        cursor.execute("SELECT * FROM infosys WHERE username=?", (username,))
        existing_user = cursor.fetchone()

        if existing_user:
            return render_template('register.html', error="Username already exists. Please choose another.")
        
        # Insert new user into the database
        cursor.execute("INSERT INTO infosys (username, password) VALUES (?, ?)", (username, password))
        connection.commit()

        return redirect('/')  # Redirect to the home page after successful registration

    return render_template('register.html')

@app.route('/logout')
def logout():
    """
    Logs out the user and redirects to the login page.
    """
    session.pop('username', None)  # Remove username from session
    return redirect('/login')  # Redirect to login page
@app.route('/weatheraqi/<city>', methods=['GET'])
def get_weather_and_aqi(city):
    weather_url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&units=metric&appid={WEATHER_API_KEY}"
    try:
        # Get weather data
        weather_response = requests.get(weather_url)
        if weather_response.status_code == 200:
            weather = weather_response.json()
            cord = weather.get('coord', {})
            
            # Log the coordinates for debugging
            print(f"Coordinates for {city}: {cord}")
            
            if not cord:
                return jsonify({"error": f"Could not get coordinates for {city}."}), 400

            # Store coordinates in session if needed
            session['cord'] = cord
            session.modified = True
            
            # Weather data processing
            sunrise_timestamp = weather['sys']['sunrise']
            sunset_timestamp = weather['sys']['sunset']
            weather_data = {
                'temperature': weather['main']['temp'],
                'feels_like': weather['main']['feels_like'],
                'humidity': weather['main']['humidity'],
                'wind_speed': round(weather['wind']['speed'] * 3.6, 2),
                'visibility': round(weather['visibility'] / 1000, 1),
                'pressure': weather['main']['pressure'],
                'sunrise_time': datetime.fromtimestamp(sunrise_timestamp + weather['timezone'], timezone.utc).strftime('%H:%M:%S'),
                'sunset_time': datetime.fromtimestamp(sunset_timestamp + weather['timezone'], timezone.utc).strftime('%H:%M:%S')
            }
            
            # Get AQI data
            aqi_url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={cord['lat']}&lon={cord['lon']}&appid={WEATHER_API_KEY}"
            aqi_response = requests.get(aqi_url)
            if aqi_response.status_code == 200:
                aqi = aqi_response.json()
                aqi_value = aqi['list'][0]['components']['pm2_5']
                aqi_data = {
                    'value': aqi_value,
                    'category': get_aqi_category(aqi_value)
                }
                return jsonify({'weather_data': weather_data, 'aqi_data': aqi_data})
            else:
                return jsonify({'error': 'Failed to retrieve AQI data.'}), 400
        else:
            return jsonify({'error': 'Failed to retrieve weather data.'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_aqi_category(aqi_value):
    """
    Returns AQI category based on the AQI value.
    """
    if aqi_value <= 50:
        return "Good"
    elif aqi_value <= 100:
        return "Moderate"
    elif aqi_value <= 150:
        return "Unhealthy for Sensitive Groups"
    elif aqi_value <= 200:
        return "Unhealthy"
    elif aqi_value <= 300:
        return "Very Unhealthy"
    else:
        return "Hazardous"

@app.route('/get-news', defaults={'city': 'default_city'}, methods=['GET'])
@app.route('/get-news/<city>', methods=['GET'])
def get_news(city):
    # Replace 'YOUR_API_KEY' with your actual API key
    city=city.lower()
    url = f"https://newsdata.io/api/1/news?apikey=pub_60623c484013efef7d48f51e46589c37f9375&q={city}&size=5&image=1&category=environment,politics"
    try:
        # Sending GET request to the API
        response = requests.get(url)
        
        # Raise an exception if the request failed
        response.raise_for_status()
        
        # Parse the JSON response
        data = response.json()
        # Prepare the list for the front-end template
        news_data = []
        if 'results' in data:
            for article in data['results']:
                news_data.append({
                    'title': article.get('title', 'No title available'),
                    'url': article.get('link', '#'),  # Use '#' as a placeholder for missing links
                     'image_url': article.get('image_url', '')  # Add image URL
                })
        
        # Pass news_data to the front-end template for rendering
        # Example output to verify
        print()
        return news_data
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e} ")
@app.route('/forecast')
def get_forecasts():
    """
    Returns weather and AQI forecasts using stored coordinates from the session.
    """
    try:
        cord = session.get('cord')  # Retrieve cord from session
        if not cord:
            return "Coordinates not set. Fetch weather data first.", 400
        print("Updated session cord:", session.get('cord'))
        # Weather Forecast URL
        weather_url = f"http://api.openweathermap.org/data/2.5/forecast?lat={cord['lat']}&lon={cord['lon']}&appid={WEATHER_API_KEY}&units=metric"
        weather_response = requests.get(weather_url)

        if weather_response.status_code == 200:
            weather_data = weather_response.json()
            forecast_list = weather_data["list"]
            daily_forecast_temp = {}

            for forecast in forecast_list:
                date_time = forecast["dt_txt"]
                temperature = forecast["main"]["temp"]
                date = date_time.split(" ")[0]
                day = datetime.strptime(date, "%Y-%m-%d").strftime("%A")

                if day not in daily_forecast_temp:
                    daily_forecast_temp[day] = temperature

        else:
            return f"Failed to fetch weather data. Status code: {weather_response.status_code}", 500

        # Air Pollution Forecast URL
        air_pollution_url = f"http://api.openweathermap.org/data/2.5/air_pollution/forecast?lat={cord['lat']}&lon={cord['lon']}&appid={WEATHER_API_KEY}"
        air_pollution_response = requests.get(air_pollution_url)

        if air_pollution_response.status_code == 200:
            air_pollution_data = air_pollution_response.json()
            forecast_list = air_pollution_data['list']
            daily_forecast_pm2_5 = {}

            for forecast in forecast_list:
                dt = datetime.utcfromtimestamp(forecast['dt']).strftime('%A')
                pm2_5_value = forecast['components']['pm2_5']
                if dt not in daily_forecast_pm2_5:
                    daily_forecast_pm2_5[dt] = pm2_5_value

        else:
            return f"Failed to fetch air pollution data. Status code: {air_pollution_response.status_code}", 500

        result = {
            "temperature_forecast": daily_forecast_temp,
            "pm2_5_forecast": daily_forecast_pm2_5
        }
        return jsonify(result)

    except Exception as e:
        return f"Error fetching data: {e}", 500
    
@app.route('/carbon-tracker', methods=['GET', 'POST'])
def carbon_tracker():
    if 'username' not in session:
        return redirect('/login')  # Redirect to login if the user is not logged in

    form = CarbonTrackerForm()
    user_id = get_user_id(session['username'])  # Get the user ID from the session

    if form.validate_on_submit():
        # Retrieve form data
        transport_distance = form.transport_distance.data or 0
        mode_of_transport = form.mode_of_transport.data
        previous_month_usage = form.previous_month_usage.data or 0
        todays_usage = form.todays_usage.data or 0
        dry_waste = form.dry_waste.data or 0
        wet_waste = form.wet_waste.data or 0
        city = form.city.data or 0

        # Insert the form data into the database
        cursor.execute("""
    INSERT INTO carbon_tracker (user_id, city, transport_distance, previous_month_usage, todays_usage, dry_waste, wet_waste)
    VALUES (?, ?, ?, ?, ?, ?, ?)
""", (user_id, city, transport_distance, previous_month_usage, todays_usage, dry_waste, wet_waste))

        connection.commit()

        # After inserting the data, redirect to the result page
        return redirect('/carbon_tracker_result')

    return render_template('carbon_tracker.html', form=form)
@app.route('/carbon_tracker_result')
def carbon_tracker_result():
    if 'username' not in session:
        return redirect('/login')  # Redirect to login if the user is not logged in

    user_id = get_user_id(session['username'])  # Get the user ID from the session

    # Fetch aggregated data for the logged-in user
    cursor.execute("""
        SELECT 
            SUM(transport_distance * 0.2) AS transport_emissions,
            SUM(previous_month_usage * 0.4) AS electricity_emissions,
            SUM(todays_usage * 0.3) AS daily_usage_emissions,
            SUM((dry_waste * 0.1) + (wet_waste * 0.1)) AS waste_emissions,
            MAX(created_at) AS last_updated
        FROM carbon_tracker
        WHERE user_id = ?
    """, (user_id,))
    data = cursor.fetchone()

    # Prepare aggregated results
    carbon_footprint = [
        {"category": "Transport", "value": round(data[0] or 0, 2)},
        {"category": "Electricity (Monthly)", "value": round(data[1] or 0, 2)},
        {"category": "Electricity (Today)", "value": round(data[2] or 0, 2)},
        {"category": "Waste Management", "value": round(data[3] or 0, 2)},
    ]
    total_carbon_emissions = sum(item['value'] for item in carbon_footprint)
    last_updated = data[4] if data[4] else "No data available"
    # Check if the table exists, and if not, create it
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS carbon_result (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id VARCHAR(20) NOT NULL,
        date DATE NOT NULL,
        total_carbon_footprint REAL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cursor.execute("""
        SELECT 
            SUM(transport_distance) AS transport_emissions,
            SUM(previous_month_usage) AS electricity_emissions,
            SUM(todays_usage) AS daily_usage_emissions,
            SUM((dry_waste*0.1) + (wet_waste*0.1)) AS waste_emissions
        FROM carbon_tracker
        WHERE user_id = ?
    """, (user_id,))
    data = cursor.fetchone()
    transport_distance,previous_month_usage,todays_usage,waste_emissions=data
    # Function to insert or update data
    def calculate_and_store_carbon_footprint(user_id, transport_distance, previous_month_usage, todays_usage,waste_emissions):
        # Calculate emissions based on the formula
        transport_emissions = transport_distance * 0.2
        electricity_emissions = previous_month_usage * 0.4
        daily_usage_emissions = todays_usage * 0.3
        waste_emissions = waste_emissions
        total_carbon_footprint = round(transport_emissions + electricity_emissions + daily_usage_emissions + waste_emissions, 2)

        # Insert data into the table
        cursor.execute("""
            INSERT INTO carbon_result (
                user_id, date, total_carbon_footprint
            ) VALUES (?, ?, ?)
        """, (
            user_id, datetime.now().date(), total_carbon_footprint
        ))
        print('done!')
        # Commit the changes to the database
        connection.commit()
    calculate_and_store_carbon_footprint(user_id,transport_distance,previous_month_usage,todays_usage,waste_emissions)
    # Prepare data for Plotly
    # Query to fetch the maximum emission per date for the graph
    cursor.execute("""
        SELECT date, MAX(total_carbon_footprint) AS max_emission
        FROM carbon_result
        WHERE user_id = ?
        GROUP BY date
        ORDER BY date
    """, (user_id,))
    graph_data = cursor.fetchall()
    carbon_data = [{"date": str(row[0]), "value": row[1]} for row in graph_data]
    
    return render_template(
        'carbon_tracker_result.html',
        carbon_footprint=carbon_footprint,
        total_carbon_emissions=total_carbon_emissions,
        carbon_data=carbon_data,
        last_updated=last_updated
    )
@app.route('/leaderboard')
def leaderboard():
    return render_template('leaderboard.html')
@app.route('/fetch_leaderboard', methods=['GET'])
def fetch_leaderboard():
    try:
        print("Fetching leaderboard data...")  # Debug log

        # Calculate total emissions for each user by summing their transport, electricity, and waste data
        cursor.execute("""
            SELECT 
                user_id,
                city,
                SUM(transport_distance * 0.2) + 
                SUM(previous_month_usage * 0.4) + 
                SUM(todays_usage * 0.3) + 
                SUM((dry_waste * 0.1) + (wet_waste * 0.1)) AS total_emissions
            FROM carbon_tracker
            GROUP BY user_id,city
            ORDER BY total_emissions ASC
        """)
        data = cursor.fetchall()
        print(f"Fetched data: {data}")  # Debug log

        leaderboard = [
            {"user_id": row[0], "city": row[1], "total_emissions": round(row[2], 2), "rank": index + 1}
            for index, row in enumerate(data)
        ]
        return jsonify(leaderboard)
    except Exception as e:
        print(f"Error: {e}")  # Debug log
        return jsonify({"error": str(e)}), 500


@app.route('/community', methods=['GET', 'POST'])
def community():
    """
    Community page: allows users to view and add posts.
    Anonymous users can also post and comment.
    """
    if request.method == 'POST':
        title = request.form.get('title')
        username = session.get('username', 'Anonymous')  # Default to 'Anonymous' if user is not logged in

        if not title:
            return jsonify({'error': 'Post title is required'}), 400

        # Insert a new post into the database
        cursor.execute(
            "INSERT INTO community_posts (title, username, likes) VALUES (?, ?, ?)",
            (title, username, 0)
        )
        connection.commit()
        return redirect('/community')

    # Fetch all posts with associated comments and likes
    cursor.execute("SELECT * FROM community_posts ORDER BY created_at DESC")
    posts = cursor.fetchall()

    post_list = []
    for post in posts:
        post_id = post[0]
        cursor.execute("SELECT * FROM comments WHERE post_id=?", (post_id,))
        comments = cursor.fetchall()
        # Get total likes by counting entries in the post_likes table
        cursor.execute("SELECT COUNT(*) FROM post_likes WHERE post_id=?", (post_id,))
        like_count = cursor.fetchone()[0]

        post_list.append({
            'id': post[0],
            'title': post[1],
            'username': post[2],
            'likes': like_count,
            'comments': [{'user_id': comment[2], 'content': comment[3]} for comment in comments]
        })

    return render_template(
        'community.html',
        posts=post_list,
        userId=session.get('userId', None),
        username=session.get('username', 'Anonymous')
    )

@app.route('/like_post/<int:post_id>', methods=['POST'])
def like_post(post_id):
    """Increments the like count of a post."""
    user_id = session.get('userId')
    
    if not user_id:
        return jsonify({'error': 'You must be logged in to like a post'}), 403

    try:
        # Check if the user has already liked the post
        cursor.execute("SELECT * FROM post_likes WHERE post_id=? AND user_id=?", (post_id, user_id))
        existing_like = cursor.fetchone()

        if existing_like:
            return jsonify({'error': 'You have already liked this post'}), 400
        

        # Insert the like into the post_likes table
        cursor.execute("INSERT INTO post_likes (post_id, user_id,like_count) VALUES (?, ?,?)", (post_id, user_id,1))
        cursor.execute("UPDATE community_posts SET likes = likes + 1 WHERE id=?", (post_id,))
        connection.commit()

        # Fetch the updated like count
        cursor.execute("SELECT likes FROM community_posts WHERE id=?", (post_id,))
        updated_likes = cursor.fetchone()[0]

        return jsonify({'likes': updated_likes})
    
    except Exception as e:
        print(f"Error liking post: {e}")
        return jsonify({'error': 'An error occurred while liking the post'}), 500

@app.route('/add_comment/<int:post_id>', methods=['POST'])
def add_comment(post_id):
    """Adds a comment to a specific post."""
    user_id = session.get('userId', 'Anonymous')
    
    try:
        data = request.get_json()
        content = data.get('content')

        if not content:
            return jsonify({'error': 'Comment cannot be empty'}), 400

        # Insert comment into the database
        cursor.execute(
            "INSERT INTO comments (post_id, user_id, content) VALUES (?, ?, ?)",
            (post_id, user_id, content)
        )
        connection.commit()

        # Return the new comment data
        return jsonify({
            'success': True,
            'user_id': user_id,
            'content': content
        })
    except Exception as e:
        print(f"Error adding comment: {e}")
        return jsonify({'error': 'An error occurred while adding the comment'}), 500

def get_user_id(username):
    """ Helper function to get user ID by username """
    cursor.execute("SELECT * FROM infosys WHERE username=?", (username,))
    user = cursor.fetchone()
    return user[0] if user else None


if __name__ == "__main__":
    try:
        # Test database connection
        if cursor:
            print("Database connection successful")
            app.run(debug=True)
        else:
            print("Database connection failed")
    except Exception as e:
        print("Error:", e)
