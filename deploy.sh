#!/bin/bash

# Build the container image
podman build -t bullrohchat .

# Run the container
podman run -d --name bullrohchat-container -p 8000:8000 bullrohchat
