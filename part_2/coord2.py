# ---------------------------
# Name: Demessie Amede
# StuNum: 7842385
# Class: COMP 3010 (A02)
# Assignment: 2
# Part: 2
# ---------------------------

import sys
import socket
import select
import json
import time # might not need
import random

import argparse
import uuid



# -------------------------- Request Obj Class -----------------------------

class Request:
    def __init__(self, commit_id, client: socket.socket, list_of_workers: list, task):
        self.commit_id = commit_id
        self.client = client  
        self.list_of_workers = list_of_workers.copy()
        self.task = task
        self.responses_received = 0
        self.replies = [False] * len(list_of_workers)
        self.responses = []

    def send_requests(self):
        for worker_conn in self.list_of_workers:
            # Check if the socket is ready for writing
            _, write_sockets, _ = select.select([], [worker_conn], [], 0)

            if worker_conn in write_sockets:
                print("WRITE")
                
                worker_conn.sendall(self.task)
            else:
                print("NO WRITE")
                self.client.sendall("Failure".encode())

    def startRequest(self):
        for w in self.list_of_workers:
            w.sendall(makeQuery(self.key,self.value))

    def handle_reply(self, who: socket.socket, what: dict) -> bool:
        
        try:
            # look up the index of this socket
            which = self.list_of_workers.index(who)
        except ValueError:
            # client is not in the list
            print("Client not in list of clients? " + str(who.getsockopt()))
            return False

        # update my list

        done = False

        try:
            # on failure, don't update, just let it time out
            if what:
                # agreed
                self.replies[which] = True
                # was that the last one?
                # Innocent until proven guilty
                done = True

                # Check if all responses were true
                for entry in self.replies:
                    if not entry:
                        done = False

                if done:
                    out = makeSetReply(True)
                    self.client.sendall(out)

                    # also send to workers
                    for w in self.list_of_workers:
                        w.sendall(makeCommit(self.key, self.value))
            else:
                # stop, fail
                out = makeSetReply(False)
                self.client.sendall(out)
                done = True

        except Exception as e:
            print(e)

    # def handle_timeout(self):
    #     # request timeout, reply failure

    #     out = makeSetReply(False)
    #     self.client.sendall(out)

    # def __str__(self):
    #     return f"Request: {self.key}:{self.value}"


    def request_to_workers(self, response_data, need_verification):
        # Store the response
        self.responses.append(response_data)

        # Increment the responses received
        self.responses_received += 1

        if not need_verification:
            self.responses_received = self.expected_responses

        # If all responses are received, compare and send the final response
        if self.responses_received == self.expected_responses:
            success = all(response == self.responses[0] for response in self.responses)
           
            request = None

            if success:
                print("REQUEST")
                request = response_data.encode()
                self.responses.clear()
                self.responses_received = 0
            else:
                raise RuntimeError("Failed to lock")

            print (f"Request-to-worker: {request}")

            for worker_conn in self.list_of_workers:
                worker_conn.sendall(request)

    def respond_to_client(self, response_data):

        if ("Error" in response_data):
            self.client.sendall(response_data.encode())

        # Store the response
        self.responses.append(response_data)

        # Increment the responses received
        self.responses_received += 1

        # If all responses are received, compare and send the final response
        if self.responses_received == self.expected_responses:

            success = all(response == self.responses[0] for response in self.responses)
           
            final_response = None

            if success:
                print("RESPOND")
                final_response = response_data
            else:
                print("NO RESPOND") 
                final_response = json.dumps("Failure")

            self.responses.clear()

            self.client.sendall(final_response.encode())
            to_do.remove(self)


# -------------------------- Protocol Functions -----------------------------

def makeQuery(key, value):
    j = json.dumps(
        {
            'type': 'QUERY',
            'key': key,
            'value': value
        }
    ) + "\n"

    return j.encode()

def makeCommit(key, value):
    j = json.dumps(
        {
            'type': 'COMMIT',
            'key': key,
            'value': value
        }
    ) + "\n"

    return j.encode()

def makeSetReply(value):
    j = json.dumps(
        {
            'type': 'SET',
            'value': value
        }
    ) + "\n"

    return j.encode()





# -------------------------- Coordinator Code -----------------------------

#worker_connections = {}  # These are long-lasting connections

to_do = [] # list of current requests

def find_commit_by_id(commit_id):
    for commit in to_do:
        if commit.commit_id == commit_id:
            return commit
    return None  # return none if not found


def establish_worker_conns(workers: list):
    my_workers = []

    try:
        for w in workers:
            if w not in my_workers: 
                tmp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                tmp_sock.connect(w)
                tmp_sock.setblocking(0)
                my_workers.append(tmp_sock)
    except Exception as e:
        print(f"Failed to connect to {w}")
        print(e)
        sys.exit(1)

    return my_workers


def check_worker_health(my_workers: dict):
    for worker_conn in my_workers.items():
        health_check_request = {"description": "HEALTH_CHECK"}
    
        worker_conn.sendall(json.dumps(health_check_request).encode('utf-8'))
        worker_response = worker_conn.recv(1024).decode("utf-8")

        if "HEALTHY" in worker_response:
            print(f"Worker {worker_conn.getsockname()} is healthy")
        else:
            raise RuntimeError(f"Worker {worker_conn.getsockname()} is not responding correctly.\n" +
                "Program terminated.\n")



def listen(PORT: int, workers: list):
    my_clients = [] # are transient
    my_workers = establish_worker_conns(workers)
    check_worker_health(my_workers)

    setRequests = SetRequests()
    getRequests = GetRequests()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.setblocking(0)  # Set the server socket to non-blocking mode
        server.bind(('', PORT))
        server.listen()

        print(f"2PC Coordinator is listening on port {PORT}")

        try:

            while True:
                # Get readables when available
                (readable, writable, error) = select.select(
                    [server, ] + my_clients + my_workers, [], [])

                for sock in readable:
                    if sock is server:
                        # Handle new client connections
                        conn, addr = server.accept()
                        conn.setblocking(0)
                        my_clients.append(conn)  # Add the new connection to inputs

                    # Handle client data in from client
                    elif sock in my_clients:
                        try:
                            # Get data from socket
                            data = sock.recv(4096).decode("utf-8")

                            if not data:
                                # No data received, remove the socket from client
                                my_clients.remove(sock)
                                print(f"Removing client {str(socket.getsockname())}")

                            else:
                                print("Client Data: ", data)
                                data_dict = json.loads(data) #assume data is json
                            
                                description = data_dict["description"]
                                
                                # For getting all tweets
                                if description == "GET_TWEETS":

                                    # Find random worker connection (round-robin esque)
                                    random_worker = random.choice(my_workers)

                                    # Add commit id to data before creating new commit
                                    new_cid = str(uuid.uuid4())
                                    data_dict.update({"cid": new_cid})

                                    # Create new commit and add to global to-do list
                                    new_commit = Request(new_cid, sock, random_worker, json.dumps(data_dict).encode('utf-8'))
                                    to_do.append(new_commit)

                                    new_commit.request_to_workers(json.dumps(data_dict), False)

                                # For posting or updating an existing tweet
                                else: 

                                    # Set up for first phase of 2PC
                                    data_dict.update({"phase": "LOCK"})

                                    # Change tid to a new id if posting a new tweet
                                    if description == "POST_TWEET":
                                        data_dict.update({"tid": str(uuid.uuid4())})

                                    # Add commit id to data before creating new commit
                                    new_cid = str(uuid.uuid4())
                                    data_dict.update({"cid": new_cid})

                                    # Create new commit and add to global to-do list
                                    new_commit = Request(new_cid, sock, my_workers, json.dumps(data_dict).encode('utf-8'))
                                    to_do.append(new_commit)
                                    new_commit.request_to_workers(json.dumps(data_dict), False)

                        except Exception as e:
                            print(f"Error handling client: {e}")
                            my_clients.remove(sock)
                            sock.close()
                    
                    # For responding to workers
                    elif sock in my_workers:
                        try:
                            # Get data from socket
                            data = sock.recv(1024).decode("utf-8")

                            if not data:
                                for commit in to_do:
                                    commit.respond_to_client("One of the worker closed")
                                raise RuntimeError("One of the workers closed")

                            print("Worker Data: ", data)
                            data_dict = json.loads(data) # assume data is json
                            description = data_dict["description"]
                                
                            # Find the commit to send the client response immediately
                            # No need to 2PC for get query
                            if description == "GET_TWEETS":
                                commit = find_commit_by_id(data_dict["cid"])

                                if commit:
                                    commit.respond_to_client(data_dict["response"])
                                    my_clients.remove(commit.client)
                                    commit.client.close()      

                            # 2PC
                            else:  
                                # Get the current phase
                                phase = data_dict["phase"]
                                response = data_dict["response"]

                                # Handling worker response to lock request
                                if phase == "LOCK":
                                    print("CHANGE COMMIT")
                                    data_dict["phase"] = "COMMIT"

                                    commit = find_commit_by_id(data_dict["cid"])
                                    #print(f"{commit.responses_received} : {commit.expectefd_responses}")
                                    if commit:
                                        print("Request request: ", data_dict)
                                        #commit.task = json.dumps(data_dict).encode("utf-8")
                                        commit.request_to_workers(json.dumps(data_dict), True)
                                        
                                # Handling worker response to commit request
                                elif phase == "COMMIT":
                                    commit = find_commit_by_id(data_dict["cid"])
                                    if commit:
                                        print("Request response", data_dict["response"])
                                        if commit.respond_to_client(data_dict["response"]):
                                            my_clients.remove(commit.client)
                                            commit.client.close()

                        except Exception as e:
                            print(f"Error handling worker: {e}")
                            my_clients.remove(sock)
                            sock.close()

        except KeyboardInterrupt as ki:
            print(f"Coordinator stopped by user.")
        except Exception as e:
            print(f"Coordinator error: {e}")

    for worker_conn in worker_connections.values():
        worker_conn.close()


def main():
    # Create an argument parser
    parser = argparse.ArgumentParser(description="Coordinator")

    # Add the coordinator's port as an arg
    parser.add_argument("myport", type=int, help="Port number for the coordinator")

    # Add a list of worker host:port pairs as args
    parser.add_argument("workers", nargs="+", help="List of worker host:port pairs")

    # Parse the command-line arguments
    args = parser.parse_args()

    # Access the coordinator's port and worker list
    PORT = args.myport

    print(f"Coordinator Port: {PORT}")
    print(f"Worker Host:Port Pairs: {args.workers}")

    workers = []
    for w in args.workers:
        (HOST, PORT) = w.split(":")
        workers.append((HOST, int(PORT)))

    listen(PORT, workers)
    

# This stops execution if a worker could not connect
try:
    main()
except RuntimeError as e: 
    print(e)
