#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Update package list and upgrade existing packages
echo "Updating and upgrading packages..."
sudo apt-get update && sudo apt-get upgrade -y

# Install Python 3 and pip if not already installed
echo "Installing Python 3 and pip..."
sudo apt-get install -y python3 python3-pip

# Install virtual environment
echo "Installing virtualenv..."
sudo pip3 install virtualenv

# Create a virtual environment
echo "Creating virtual environment..."
python3 -m venv lft_env

# Activate the virtual environment
echo "Activating virtual environment..."
source lft_env/bin/activate

# Install required packages
echo "Installing required packages..."
pip install -r requirements.txt

# Initialize the database
echo "Initializing the database..."
flask db init
flask db migrate
flask db upgrade

# Set up environment variables (replace with your actual values)
echo "Setting up environment variables..."
export SECRET_KEY="your_secret_key_here"
export MSAL_CLIENT_ID="your_msal_client_id_here"
export MSAL_CLIENT_SECRET="your_msal_client_secret_here"

echo "Setup complete! You can now run the LFT application."
echo "To activate the virtual environment in the future, run:"
echo "source lft_env/bin/activate"

#This script does the following:
#Updates and upgrades system packages
#Installs Python 3 and pip if not already installed
#Installs virtualenv
#Creates a virtual environment named 'lft_env'
#Activates the virtual environment
#Installs the required packages from requirements.txt
#Initializes the database
#Sets up some environment variables (you'll need to replace these with your actual values)
#Remember to make this script executable with:  chmod +x setup_lft.sh
#You can then run it with:  ./setup_lft.sh