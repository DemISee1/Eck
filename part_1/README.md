## Instructions

### Commands

For my main webserver

	python3 myserver.py <PORT>

PORT = port being used by the main server.

There is also coordinator PORT:HOST information but to edit that you will need to go into the myserver.py file and change the values by hand.

---

For my coordinator

	python3 coord.py <PORT> <WorkerHost1:WorkerPort1> <workerHost1:WorkerPort2> ...

PORT must be set to **8001** unless you change the PORT:HOST in myserver.py.

Workers MUST be listed out in a HOST:PORT manner.

Workers MUST be executed before the coordinator otherwise it will not work.

---

For my worker

	python3 worker.py <PORT>

PORT = port being used by the worker.