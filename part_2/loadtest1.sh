#!/bin/bash

# Change this!
PORT=8001

for item in `seq 1 30`
do
    (echo '{"description": "POST_TWEET", "username": "'${item}'", "text": "'$item'"}' | nc -w4 localhost $PORT) &
done
wait
echo "Done setting. Should have taken less than four seconds"

# do an update

for item in `seq 1 30`
do
    (echo '{"description": "UPDATE_TWEET", "username": "'${item}'", "text": "'$item'", "tid": "1"}' | nc -w4 localhost $PORT) &
done
wait
echo "Done updating. Should have taken less than four seconds"

# get them all (any order)

echo '{"description": "GET_TWEETS"}' | nc -w1 localhost $PORT

wait
echo "Done"