# ---------------------------
# Name: Demessie Amede
# StuNum: 7842385
# Class: COMP 3010 (A02)
# Assignment: 2
# Part: 2
# ---------------------------

import socket
import sys
import threading
import argparse
import json

import os
import time

server = "Duchess"

head = """HTTP/1.1 {}
Content-Length: {}
Content-Type: {}
Server: {}{}\r\n\r\n"""

cookies = {}


# ------------ Change the Coordinator HOST:PORT here if needed -----------------
coordinator_host = ''  # Replace with the actual coordinator host
coordinator_port = 8001  # Replace with the actual coordinator port
# ------------------------------------------------------------------------------

def parse_http_request(request:str):
    request_lines = request.split('\r\n')

    if not request_lines:
        return "400 Bad Request", None, None, None, None # Malformed request

    request_line = request_lines[0]

    if not request_line:
        return "400 Bad Request", None, None, None, None # Empty request line

    split_rl = request_line.split(" ", 2)

    if len(split_rl) != 3:
        return "400 Bad Request", None, None, None, None # Poorly formatted request

    method, path, _ = split_rl

    body = None
    header_dict = {}  # key-value pairs dict

    if '\r\n\r\n' in request:
        headers, body = request.split('\r\n\r\n', 1)
        headers = headers.split('\r\n')[1:] # ignore first line
        
        # split headers into key-value pairs
        for header in headers:
            key, value = header.split(":", 1)
            header_dict[key.strip()] = value.strip() 

    else:
        return "400 Bad Request", None, None, None, None # Poorly formatted request

    return (None, method, path, header_dict, body)


def get_username_from_cookie(headers_dict):
    if 'Cookie' in headers_dict:
        cookie_header = headers_dict['Cookie']
        cookies = cookie_header.split(';')

        for cookie in cookies:
            cookie_parts = cookie.strip().split('=')
            if len(cookie_parts) == 2 and cookie_parts[0].strip() == 'username':
                
                return cookie_parts[1].strip()

    return None


def send_coord_request(json_data: str):

    response = None

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((coordinator_host, coordinator_port))

            # Send the JSON body to the coordinator
            s.sendall(json_data.encode())

            response = s.recv(1024)

    except Exception as e:
        print(f"Error requesting data from the coordinator: {e}")
        return str("500 Internal Server Error: Error requesting data from the coordinator")

    return response.decode("utf-8")


def handle_api(api_path:str, method:str, header_dict:dict, body:str):

    data = ""
    username = get_username_from_cookie(header_dict)

    if body:
        try:
            data = json.loads(body)
        except Exception as e:
            return '400 Bad Request', 'text/plain', 'Invalid request data'

    # User asks for all existing tweets
    if method == 'GET' and api_path == '/api/tweet':
        if username != None:
            request_data = {"description": "GET_TWEETS"}

            response = send_coord_request(json.dumps(request_data))

            if ("500 Internal Server Error" not in response):
                return '200 OK', 'application/json', response

        else:
            return '401 Unauthorized', 'text/plain', 'You must be logged in to view tweets.'

    
    # User posts a new tweet
    elif method == 'POST' and api_path == '/api/tweet':
        if username != None:
            if data["text"] != "":
                request_data = {"description": "POST_TWEET", "username": username}
                request_data.update(data)
                
                response = send_coord_request(json.dumps(request_data))
                
                if "TWEET_POSTED" in response:
                    return '201 Created', 'text/plain', 'Post successful'
                else:
                    pass
            else:
                return '400 Bad Request', 'text/plain', "The tweet cannot be empty."
        else:
            return '401 Unauthorized', 'text/plain', 'You must be logged in to post a tweet.'

    # User login
    elif method == 'POST' and api_path == '/api/login':
        username = data['username']

        if username != "":
            cookies["username"] = username
            return '200 OK', 'text/plain', 'Login successful'
        else:
            return '400 Bad Request', 'text/plain', 'Username cannot be empty. Please provide a valid username.'

    # User updates an existing tweet
    elif method == 'PUT' and '/api/tweet/' in api_path:
        if username != None:
            if data["text"] != "":
                tweet_id = api_path.split('/')[-1]
                request_data = {"description": "UPDATE_TWEET", "tid": tweet_id, "username": username}
                request_data.update(data)

                response = send_coord_request(json.dumps(request_data))

                if "TWEET_UPDATED" in response:
                    return '204 No Content', 'text/plain', 'Update successful'
            else:
                return '400 Bad Request', 'text/plain', "The tweet cannot be empty."
        else:
            return '401 Unauthorized', 'text/plain', 'You must be logged in to update a tweet.'
    else:
        return '404 Not Found', 'text/plain', 'API Endpoint Not Found'

    print("Response: ", response)
    return '500 Internal Server Error', 'text/plain', response


def handle_thread(conn: socket):
    with conn:
        request = conn.recv(1024)
        print(request.decode("utf-8"))

        error, method, path, header_dict, body = parse_http_request(request.decode("utf-8"))
        content_type = b""

        if error == None:
            if method == "GET" or method == "POST" or method == "PUT":
                response_code = "200 OK"
                content_type = "text/html"
                content = b""  

                # Get index.html for root path
                if method == "GET" and path == "/":
                    try:
                        with open("index.html", "rb") as file:
                            content = file.read()
                    except Exception as e:
                        print(f"Error reading file: {e}")
                        response_code = "500 Internal Server Error"
                        content_type = "text/plain"
                        content = b"Internal Server Error: Failed to read the file."

                elif "api" in path:
                    response_code, content_type, content = handle_api(path, method, header_dict, body)
                    content = content.encode()

                # No need to handle favicon.ico
                elif "favicon.ico" in path:
                    pass # server still requests favicon.ico which is treated as an odd edgecase

                else:   
                    print(f"404 Not Found: {path} does not exist")  # 404 error
                    response_code = "404 Not Found"
                    content_type = "text/html"
                    content = f"The API Endpoint {path} not found."
                    content = content.encode()

            else:
                print(f"405 Method Not Allowed: The HTTP method {method} is not handled by {server}")
                response_code = "405 Method Not Allowed"
                content = b"Method not allowed. Supported methods: GET, POST, PUT"

        else:
            print(f"400 Bad Request: The request was poorly formatted.")
            response_code = "400 Bad Request"
            content_type = "text/plain"
            content = b"Invalid request format. Check your request."
      
        cookie_headers = ""
        
        if response_code == "200 OK" and cookies and path == '/api/login' and method == 'POST':
            for name, value in cookies.items():
                cookie_headers += f"\r\nSet-Cookie: {name}={value}; path=/"

        response = head.format(response_code, len(content), content_type, server, cookie_headers).encode()
        response = response + content 

        try:
            conn.sendall(response)
        except Exception as e:
            print(f"Error sending response: {e}") 
            pass
        cookies.clear()

def main():
    parser = argparse.ArgumentParser(description='Simple HTTP Server')
    parser.add_argument('port', type=int, help='Port number to listen on')
    args = parser.parse_args()

    HOST = ''         # Symbolic name meaning all available interfaces
    PORT = args.port  # Non-privileged port
 
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()

        print(f"{server} listening on port {PORT}.")

        try:
            while True:
                conn, addr = s.accept()
                theThread = threading.Thread(target=handle_thread, args=(conn,))
                theThread.start()
                #print("Running {} threads".format(threading.active_count()))
        except KeyboardInterrupt as ki:
            print(f"{server} stopped by user.")
            sys.exit()
        except Exception as e:
            print(f"Server error: {e}")
            pass

main()