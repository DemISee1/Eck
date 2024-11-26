import socket
import json
import random
import sys
import argparse
import uuid
import select

worker_connections = {}  # These are long-lasting connections

def establish_worker_conns(worker_host_ports):
    for worker_host_port in worker_host_ports:
        if worker_host_port not in worker_connections:
            worker_host, worker_port = worker_host_port.split(":")
            worker_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                worker_conn.connect((worker_host, int(worker_port)))
                worker_connections[worker_host_port] = worker_conn
            except Exception as e:
                raise RuntimeError(f"Error connecting to worker {worker_host_port}.\n" +
                    "Make sure to run workers before running the coordinator.\n" +
                    "Program terminated.\n")

def check_worker_health():
    for worker_host_port, worker_conn in worker_connections.items():
        health_check_request = {"description": "HEALTH_CHECK"}
    
        worker_conn.sendall(json.dumps(health_check_request).encode('utf-8'))
        worker_response = worker_conn.recv(1024).decode("utf-8")

        if "HEALTHY" in worker_response:
            print(f"Worker {worker_host_port} is healthy")
        else:
            raise RuntimeError(f"Worker {worker_host_port} is not responding correctly.\n" +
                "Program terminated.\n")

def main():
    # Create an argument parser
    parser = argparse.ArgumentParser(description="Coordinator")

    # Add the coordinator's port as a positional argument
    parser.add_argument("myport", type=int, help="Port number for the coordinator")

    # Add a list of worker host:port pairs as positional arguments
    parser.add_argument("workers", nargs="+", help="List of worker host:port pairs")

    # Parse the command-line arguments
    args = parser.parse_args()

    # Access the coordinator's port and worker list
    HOST = ''
    PORT = args.myport
    worker_host_ports = args.workers
    current_worker_index = 0

    print(f"Coordinator Port: {PORT}")
    print(f"Worker Host:Port Pairs: {worker_host_ports}")

    establish_worker_conns(worker_host_ports)
    check_worker_health()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((HOST, PORT))
            s.listen()

            print(f"2PC Coordinator is listening on port {PORT}")

            while True:

                conn, addr = s.accept()
                request_data = conn.recv(1024).decode("utf-8")

                if request_data:
                    print(request_data)
                    request_dict = json.loads(request_data)
                    description = request_dict["description"]


                    if description == "GET_TWEETS":

                        random_worker_host_port = random.choice(list(worker_connections.keys()))
                        worker_conn = worker_connections[random_worker_host_port]
                        worker_conn.sendall(request_data.encode('utf-8'))
                        worker_response = worker_conn.recv(1024)
                        print(f"Loaded: {json.loads(worker_response)} --- Raw: {worker_response}")
                        conn.sendall(worker_response)

                    else:
                        # Initiate 2PC for POST/PUT requests on all worker connections
                        response_data = []

                        if description == "POST_TWEET":
                            unique_id = {"tid": str(uuid.uuid4())}
                            request_dict = json.loads(request_data)  
                            request_dict.update(unique_id)  
                            request_data = json.dumps(request_dict)  

                        for worker_host_port, worker_conn in worker_connections.items():
                            
                            worker_conn.sendall(request_data.encode('utf-8'))
                            
                            # Receive and process the response from the worker
                            worker_response = worker_conn.recv(1024)
                            worker_response = worker_response.decode("utf-8")
                            
                            response_data.append(worker_response)

                        success = all(response == response_data[0] for response in response_data)
                        
                        final_response = None

                        if success:
                            final_response = json.dumps(response_data[0])
                        else:
                            final_response = json.dumps("Failure")

                        conn.sendall(final_response.encode('utf-8'))

                conn.close()

    except KeyboardInterrupt as ki:
        print(f"Coordinator stopped by user.")

    except Exception as e:
        print(f"Coordinator error: {e}")
        

    for worker_conn in worker_connections.values():
        worker_conn.close()


# This stops execution if a worker could not connect
try:
    main()
except RuntimeError as e: 
    print(e)  

