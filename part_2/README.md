## Instructions

### How to Run the Python Files

##### For my main webserver

	python3 myserver2.py <PORT>

PORT = port being used by the main server.

**NOTE:** If you want to change the coordinator host/port you will have to do so by changing the global variables at the top of the myserver2.py file.

If you are using an aviary host you must provide the COMPLETE host name (e.g., **osprey.cs.umanitoba.ca** instead of just **osprey**)

##### For my coordinator

	python3 coord2.py <PORT> <WorkerHost1:WorkerPort1> <workerHost1:WorkerPort2> ...

PORT must be set to **8001** (the default in myserver.py) or you change the PORT:HOST in myserver.py.

Workers MUST be listed out in a HOST:PORT manner.

Workers MUST be executed before the coordinator otherwise it will not work.

##### For my worker

	python3 worker[#].py <PORT>

PORT = port being used by the worker.

---

### How to Communicate with the Coordinator

This differs across the API endpoints but generally the coordinator is expecting a json with the following fields:

	{description: [description], username: [username], text: [text], tid: [tid]}

**Description** is a description of the request
**Username** is the username of client
**Text** is the tweet text
**Tid** is the unique identifier for the tweet

Now for each api endpoint:

1. GET /api/tweet

> {description: GET_TWEETS}

2. POST /api/tweet

> {description: POST_TWEET, username: [username], text: [text]}

3. PUT /api/tweet/[tweet-id]

> {description: UPDATE_TWEET, username: [username], text: [text], tid: [tid]}

In all these cases the result will be in json form containing a summary of the data (e.g., GET will return all the tweets in json form while POST/PUT will return some form of confirmation that the operation was successful).

---

### How to Communicate with the Workers (Databases)


	{description: [description], tid: [tid], username: [username], text: [text], phase: [phase], cid: [cid], response: [response]}

**Description** is a description of the request
**Username** is the username of client
**Text** is the tweet text
**Tid** is the unique identifier for the tweet
**Cid** is the unique identifier for the commit the request is part of
**Phase** is the current phase in the two-phase commit we are in
**Response** is the workers response to the request

For the **phase** attribute, it can either be in "LOCK" or "COMMIT".
For the **response** attribute, it can be "YES", "NO" if we are in the LOCK phase and "TWEET_POSTED", "TWEET_UPDATED" or "NO" in the COMMIT phase. 

In all cases the only value that should change throughout the 2PC algorithm is the **response** attribute which should react to how the worker handles the request. The **phase** attribute WILL NOT be changed by the worker, that responsibility is put on the coordinator.




