#!/bin/bash
if [[ "$WAIT_FOR_IT" == "none" ]]; then
    uvicorn main:app --host 0.0.0.0 --port 8080
else
    chmod +x ./wait-for-it.sh
    ./wait-for-it.sh $WAIT_FOR_IT -- uvicorn main:app --host 0.0.0.0 --port 8080
fi
