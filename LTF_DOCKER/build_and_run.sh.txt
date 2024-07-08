#!/bin/bash

# ~/LTF/LFT_DOCKER/build_and_run.sh

# Stop and remove any existing container with the same name
docker stop lft-app-container 2>/dev/null
docker rm lft-app-container 2>/dev/null

# Build the Docker image
echo "Building Docker image..."
docker build -t lft-app .

# Check if the build was successful
if [ $? -eq 0 ]; then
    echo "Docker image built successfully."
    
    # Run the Docker container
    echo "Starting the container..."
    docker run -d --name lft-app-container -p 5000:5000 lft-app
    
    # Check if the container started successfully
    if [ $? -eq 0 ]; then
        echo "Container started successfully."
        echo "LFT application is now running on http://localhost:5000"
    else
        echo "Failed to start the container."
    fi
else
    echo "Docker image build failed."
fi
