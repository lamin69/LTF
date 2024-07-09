# LFT (Lamine File Transfer)

LFT is a versatile file management web application that supports multiple protocols including SFTP, FTP, SMB, WebDAV, Google Drive, and Microsoft OneDrive.

## Features

- Connect to various file storage protocols:
  - SFTP
  - FTP
  - SMB
  - WebDAV
  - Google Drive
  - Microsoft OneDrive
- Browse, upload, download, rename, and delete files
- Change file permissions (CHMOD) for SFTP connections
- User authentication system
- Save and manage connection profiles
- Right-click context menu for file operations
- Multi-file selection for batch operations

## Prerequisites

- Python 3.9+
- Docker (optional, for containerized deployment)

## Installation

1. Clone the repository:  https://github.com/lamin69/lamine-files-tranfer.git


cd lft
2. Install the required packages:   

3. Set up the database:
flask db init
flask db migrate
flask db upgrade



4. Set up Google Drive API:
- Go to the Google Cloud Console
- Create a new project
- Enable the Google Drive API
- Create credentials (OAuth 2.0 client ID)
- Download the client configuration file and save it as `client_secret.json` in the project root

5. Set up Microsoft OneDrive API:
- Go to the Microsoft Azure Portal
- Register a new application
- Add the necessary permissions for OneDrive access
- Note down the client ID and client secret

6. Update the configuration:
- Rename `config.example.py` to `config.py`
- Update the configuration values, including the OneDrive client ID and secret

## Running the Application

1. Start the Flask development server:  flask run


2. Open a web browser and navigate to `http://localhost:5000`

## Docker Deployment

1. Build the Docker image:   docker build -t lft .


2. Run the container: docker run -p 5000:5000 lft
 
## Usage

1. Register a new account or log in to an existing one
2. Select a protocol and enter the connection details
3. Click "Connect" to establish a connection
4. Use the file browser to manage your files
5. Right-click on files for additional options
6. Use the toolbar buttons for upload, download, and other operations

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
