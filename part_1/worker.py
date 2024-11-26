import argparse
import socket
import json
import sys

# -------------------------- Tweet Obj Class -----------------------------

class Tweet:
    def __init__(self, tid, username, text):
        self.tid = tid
        self.username = username
        self.text = text
        self.locked = False  # Initially, the tweet is not locked
       

    def acquire_lock(self):
        if not self.locked:
            self.locked = True
            return True
        return False

    def release_lock(self):
        self.locked = False

    def is_locked(self):
        return self.locked

    def update_tweet(self, new_username, new_text):
        if not self.locked:
            self.username = new_username
            self.text = new_text
            return True
        return False

# ------------------------------------------------------------------------

# Create an argument parser to specify the port
parser = argparse.ArgumentParser(description="Worker")
parser.add_argument("port", type=int, help="Port number for the worker")
args = parser.parse_args()


# Define the worker's address and port
worker_address = ""
worker_port = args.port

# Create a socket for the worker
worker_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
worker_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
# Bind the socket to the worker's address and port
worker_socket.bind((worker_address, worker_port))

# Listen for incoming connections
worker_socket.listen()

# Current Requests
#List of requets to do (or todo list)

# In-memory tweet database
tweet_database = {}

print(f"Worker is listening on port {worker_port}")

# Function to perform a task
def perform_task(task_data):
    request_dict = json.loads(task_data)
    description = request_dict["description"]

    if description == "HEALTH_CHECK":
        return "HEALTHY"

    elif description == "POST_TWEET":
        tweet_id = request_dict["tid"]
        text = request_dict["text"]
        username = request_dict["username"]

        print (tweet_database)

        # Create a new tweet based on the request data
        new_tweet = Tweet(tweet_id, username, text)
        tweet_database[new_tweet.tid] = new_tweet  # Store the tweet in the database

        return "TWEET_POSTED"

    elif description == "GET_TWEETS":
        # Retrieve all tweets from the database
        tweets = [tweet.__dict__ for tweet in tweet_database.values()]
        return json.dumps(tweets)

    elif description == "UPDATE_TWEET":
        tweet_id = request_dict["tid"]
        new_text = request_dict["text"]
        new_username = request_dict["username"]

        if tweet_id is not None and new_text is not None and new_username is not None:
            # Check if the tweet exists in the database
            if tweet_id in tweet_database:
                # Update the tweet's text and/or username
                tweet_database[tweet_id].update_tweet(new_username, new_text)
                return "TWEET_UPDATED"
            else:
                return "TWEET_NOT_FOUND"

    return "INVALID_REQUEST"

# Accept incoming connections
coord_conn, coord_addr = worker_socket.accept()

request_data = None

while True:
    try:
        
        # Receive task data from the coordinator
        request_data = coord_conn.recv(1024).decode("utf-8")
        if not request_data:
            break # Exit the loop if the connection is closed

        response_data = perform_task(request_data)

        # Send the response back to the coordinator
        coord_conn.sendall(response_data.encode())

        
    except KeyboardInterrupt as ki:
        print(f"Worker stopped by user.")
        sys.exit()
    except Exception as e:
        print(f"Worker error: {e}")

# Clean up the client socket
coord_conn.close()

# Close the worker's listening socket
worker_socket.close()


