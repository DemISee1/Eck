# ---------------------------
# Name: Demessie Amede
# StuNum: 7842385
# Class: COMP 3010 (A02)
# Assignment: 2
# Part: 2
# ---------------------------


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

# -------------------------- Protocol Functions -----------------------------

def makeGetResponse(key, value):
    data = {

        'type': 'GET-RESPONSE',
        'key': key,
        'value': value
    }
    dumped = json.dumps(data)
    return dumped.encode()

def makeGetDB(db):
    response = {"type": "DB", "db":db}
    return json.dumps(response).encode()

def makeQueryReply(key: str, vote: bool) -> bytes:
    data = {
        'type': 'QUERY-REPLY',
        'key': key,
        'answer': vote
    }
    dumped = json.dumps(data)
    dumped = dumped + "\n"
    return dumped.encode()

def makeCommitReply(key: str, value: str, vote: bool) -> bytes:
    data = {
        'type': 'COMMIT-REPLY',
        'key': key,
        'value': value,
        'answer': vote
    } 
    dumped = json.dumps(data)
    dumped = dumped + "\n"
    return dumped.encode()

# ------------------------------ Worker Code -------------------------------

# Create an argument parser to specify the port
parser = argparse.ArgumentParser(description="Worker")
parser.add_argument("port", type=int, help="Port number for the worker")
args = parser.parse_args()


# Define the worker's address and port
worker_address = ''
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

    # Initialize response
    response_dict = request_dict.copy() # copy of request for now

    # Respond with "healthy if it is healthy"
    if description == "HEALTH_CHECK":
        response_dict.update({"response": "HEALTHY"})

    else:

        # No 2PC for getting tweets
        if description == "GET_TWEETS":
            # Retrieve all tweets from the database
            tweets = [tweet.__dict__ for tweet in tweet_database.values()]
            response_dict.update({"response": json.dumps(tweets)})

        # 2PC (POST/PUT)    
        else:
            phase = request_dict["phase"]
            tweet_id = request_dict["tid"]

            # Request to lock tweet
            if phase == "LOCK":
                
                # If posting a tweet always return no (no need to lock)
                if description == "POST_TWEET":
                    response_dict.update({"response": "YES"})

                # If updating a tweet check if the tid is already locked
                elif description == "UPDATE_TWEET":
                    
                    # Try and acquire lock on tid
                    if tweet_database[tweet_id].acquire_lock():
                        response_dict.update({"response": "YES"})
                    else:
                        response_dict.update({"response": "NO"})

            # Request to commit change
            elif phase == "COMMIT":

                text = request_dict["text"]
                username = request_dict["username"]

                # Post the tweet
                if description == "POST_TWEET":
                    # Create a new tweet based on the request data
                    new_tweet = Tweet(tweet_id, username, text)
                    tweet_database[new_tweet.tid] = new_tweet  # Store the tweet in the database

                    # Return an acknowledgement that the commit went through
                    response_dict.update({"response": "TWEET_POSTED"})
                    
                # Update the tweet
                elif description == "UPDATE_TWEET":

                    # Check if tweet exists
                    if tweet_id in tweet_database:

                        # Release lock before attempting update
                        tweet_database[tweet_id].release_lock()

                        # Update tweet and return ack if worked and no if not
                        if tweet_database[tweet_id].update_tweet(username, text):
                            response_dict.update({"response": "TWEET_UPDATED"})
                        else:
                            response_dict.update({"response": "NO"})

                       

                    else:
                        response_dict.update({"response": "NO"})



    return json.dumps(response_dict)
        

# Accept incoming connections
coord_conn, coord_addr = worker_socket.accept()

while True:
    try:
        
        # Receive task data from the coordinator
        request_data = coord_conn.recv(1024).decode("utf-8")
        if not request_data:
            continue # Continue waiting for data if none is received

        print("\n-----------------------------------------------------\n")
        print(f"Request: {request_data}\n")

        response_data = perform_task(request_data)
        
        print(f"Response: {response_data}")
        

        # Send the response back to the coordinator
        coord_conn.sendall(response_data.encode())

        
    except KeyboardInterrupt as ki:
        print(f"Worker stopped by user.")
        sys.exit()
    except Exception as e:
        print(f"Worker error: {e}")
        sys.exit()

# Clean up the client socket
coord_conn.close()

# Close the worker's listening socket
worker_socket.close()


