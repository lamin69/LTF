from flask import Flask, render_template, request, jsonify, send_file, redirect, session, url_for
import os
import paramiko
from werkzeug.utils import secure_filename
from smb.SMBConnection import SMBConnection
from ftplib import FTP
import requests
from webdav3.client import Client
import shutil
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from msal import ConfidentialClientApplication
import io
import json
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a real secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///lft.db'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    profiles = db.relationship('Profile', backref='user', lazy=True)

class Profile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    protocol = db.Column(db.String(20), nullable=False)
    server = db.Column(db.String(120), nullable=False)
    port = db.Column(db.Integer, nullable=False)
    username = db.Column(db.String(80), nullable=False)
    password = db.Column(db.String(120), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

client = None
sftp = None
ftp = None
smb = None
webdav = None

SCOPES = ['https://www.googleapis.com/auth/drive.file']
CLIENT_SECRET_FILE = 'client_secret.json'  # Download this from Google Cloud Console

MSAL_CLIENT_ID = 'your_msal_client_id'
MSAL_CLIENT_SECRET = 'your_msal_client_secret'
MSAL_AUTHORITY = 'https://login.microsoftonline.com/common'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:  # In production, use proper password hashing
            login_user(user)
            return redirect(url_for('index'))
        else:
            return 'Invalid username or password'
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/connect', methods=['POST'])
@login_required
def connect():
    global client, sftp, ftp, smb, webdav
    data = request.json
    protocol = data['protocol']
    server = data['server']
    port = int(data['port'])
    username = data['username']
    password = data['password']

    try:
        if protocol == 'sftp':
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(server, port, username, password)
            sftp = client.open_sftp()
        elif protocol == 'ftp':
            ftp = FTP()
            ftp.connect(server, port)
            ftp.login(username, password)
        elif protocol == 'smb':
            smb = SMBConnection(username, password, 'client', server, use_ntlm_v2=True)
            smb.connect(server, port)
        elif protocol == 'webdav':
            options = {
                'webdav_hostname': f'http://{server}:{port}',
                'webdav_login': username,
                'webdav_password': password
            }
            webdav = Client(options)
            if not webdav.check():
                return jsonify({'status': 'error', 'message': 'Failed to connect to WebDAV server'}), 400
        elif protocol == 'gdrive':
            return redirect(url_for('authorize_gdrive'))
        elif protocol == 'onedrive':
            return redirect(url_for('authorize_onedrive'))
        else:
            return jsonify({'status': 'error', 'message': 'Unsupported protocol'}), 400
        
        # Save the connection as a profile
        new_profile = Profile(name=f"{protocol} connection", protocol=protocol, server=server, port=port, username=username, password=password, user=current_user)
        db.session.add(new_profile)
        db.session.commit()
        
        return jsonify({'status': 'success', 'message': 'Connected successfully!'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/authorize_gdrive')
@login_required
def authorize_gdrive():
    flow = Flow.from_client_secrets_file(CLIENT_SECRET_FILE, scopes=SCOPES)
    flow.redirect_uri = url_for('oauth2callback_gdrive', _external=True)
    authorization_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true')
    session['state'] = state
    return redirect(authorization_url)

@app.route('/oauth2callback_gdrive')
@login_required
def oauth2callback_gdrive():
    state = session['state']
    flow = Flow.from_client_secrets_file(CLIENT_SECRET_FILE, scopes=SCOPES, state=state)
    flow.redirect_uri = url_for('oauth2callback_gdrive', _external=True)
    authorization_response = request.url
    flow.fetch_token(authorization_response=authorization_response)
    credentials = flow.credentials
    session['gdrive_credentials'] = credentials_to_dict(credentials)
    return redirect(url_for('index'))

@app.route('/authorize_onedrive')
@login_required
def authorize_onedrive():
    msal_app = ConfidentialClientApplication(MSAL_CLIENT_ID, authority=MSAL_AUTHORITY, client_credential=MSAL_CLIENT_SECRET)
    auth_url = msal_app.get_authorization_request_url(scopes=['Files.ReadWrite.All'])
    return redirect(auth_url)

@app.route('/oauth2callback_onedrive')
@login_required
def oauth2callback_onedrive():
    msal_app = ConfidentialClientApplication(MSAL_CLIENT_ID, authority=MSAL_AUTHORITY, client_credential=MSAL_CLIENT_SECRET)
    result = msal_app.acquire_token_by_authorization_code(request.args['code'], scopes=['Files.ReadWrite.All'])
    if 'access_token' in result:
        session['onedrive_token'] = result
        return redirect(url_for('index'))
    return 'Error acquiring token: ' + str(result.get('error'))

@app.route('/list_files', methods=['POST'])
@login_required
def list_files():
    global sftp, ftp, smb, webdav
    data = request.json
    path = data['path']
    protocol = data['protocol']

    try:
        files = []
        if protocol == 'sftp' and sftp:
            for entry in sftp.listdir_attr(path):
                files.append({
                    'name': entry.filename,
                    'isDirectory': entry.longname.startswith('d'),
                    'size': entry.st_size,
                    'modificationTime': entry.st_mtime
                })
        elif protocol == 'ftp' and ftp:
            ftp.cwd(path)
            ftp.retrlines('LIST', lambda line: files.append(parse_ftp_line(line)))
        elif protocol == 'smb' and smb:
            for entry in smb.listPath('smb_share', path):
                files.append({
                    'name': entry.filename,
                    'isDirectory': entry.isDirectory,
                    'size': entry.file_size,
                    'modificationTime': entry.last_write_time
                })
        elif protocol == 'webdav' and webdav:
            for item in webdav.list(path):
                files.append({
                    'name': item,
                    'isDirectory': webdav.is_dir(item),
                    'size': webdav.info(item).get('size', 0),
                    'modificationTime': webdav.info(item).get('modified', '')
                })
        elif protocol == 'gdrive':
            files = list_gdrive_files()
        elif protocol == 'onedrive':
            files = list_onedrive_files()
        return jsonify({'status': 'success', 'files': files})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

def list_gdrive_files():
    if 'gdrive_credentials' not in session:
        return redirect(url_for('authorize_gdrive'))
    credentials = Credentials(**session['gdrive_credentials'])
    drive_service = build('drive', 'v3', credentials=credentials)
    results = drive_service.files().list(pageSize=10, fields="nextPageToken, files(id, name, mimeType, modifiedTime, size)").execute()
    items = results.get('files', [])
    files = []
    for item in items:
        files.append({
            'name': item['name'],
            'isDirectory': item['mimeType'] == 'application/vnd.google-apps.folder',
            'size': item.get('size', 'N/A'),
            'modificationTime': item['modifiedTime'],
            'id': item['id']
        })
    return files

def list_onedrive_files():
    if 'onedrive_token' not in session:
        return redirect(url_for('authorize_onedrive'))
    headers = {'Authorization': 'Bearer ' + session['onedrive_token']['access_token']}
    response = requests.get('https://graph.microsoft.com/v1.0/me/drive/root/children', headers=headers)
    items = response.json().get('value', [])
    files = []
    for item in items:
        files.append({
            'name': item['name'],
            'isDirectory': 'folder' in item,
            'size': item.get('size', 'N/A'),
            'modificationTime': item['lastModifiedDateTime'],
            'id': item['id']
        })
    return files

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    global sftp, ftp, smb, webdav
    file = request.files['file']
    path = request.form['path']
    protocol = request.form['protocol']

    try:
        filename = secure_filename(file.filename)
        remote_path = os.path.join(path, filename)
        if protocol == 'sftp' and sftp:
            sftp.putfo(file.stream, remote_path)
        elif protocol == 'ftp' and ftp:
            ftp.storbinary(f'STOR {remote_path}', file.stream)
        elif protocol == 'smb' and smb:
            with smb.openFile('smb_share', remote_path, 'w') as f:
                f.write(file.read())
        elif protocol == 'webdav' and webdav:
            webdav.upload_to(remote_path, file.stream)
        elif protocol == 'gdrive':
            upload_to_gdrive(file)
        elif protocol == 'onedrive':
            upload_to_onedrive(file)
        return jsonify({'status': 'success', 'message': 'File uploaded successfully!'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

def upload_to_gdrive(file):
    if 'gdrive_credentials' not in session:
        return redirect(url_for('authorize_gdrive'))
    credentials = Credentials(**session['gdrive_credentials'])
    drive_service = build('drive', 'v3', credentials=credentials)
    file_metadata = {'name': file.filename}
    media = MediaFileUpload(file, resumable=True)
    file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()

def upload_to_onedrive(file):
    if 'onedrive_token' not in session:
        return redirect(url_for('authorize_onedrive'))
    headers = {
        'Authorization': 'Bearer ' + session['onedrive_token']['access_token'],
        'Content-Type': 'application/octet-stream'
    }
    response = requests.put(
        f"https://graph.microsoft.com/v1.0/me/drive/root:/{file.filename}:/content",
        headers=headers,
        data=file.read()
    )
    if response.status_code == 201 or response.status_code == 200:
        return jsonify({'status': 'success', 'message': 'File uploaded to OneDrive successfully!'})
    else:
        return jsonify({'status': 'error', 'message': 'Failed to upload file to OneDrive'}), 500

@app.route('/download')
@login_required
def download_file():
    global sftp, ftp, smb, webdav
    path = request.args.get('path')
    protocol = request.args.get('protocol')

    try:
        filename = os.path.basename(path)
        local_path = os.path.join('/tmp', filename)
        if protocol == 'sftp' and sftp:
            sftp.get(path, local_path)
        elif protocol == 'ftp' and ftp:
            with open(local_path, 'wb') as f:
                ftp.retrbinary(f'RETR {path}', f.write)
        elif protocol == 'smb' and smb:
            with open(local_path, 'wb') as f:
                smb.retrieveFile('smb_share', path, f)
        elif protocol == 'webdav' and webdav:
            webdav.download_file(path, local_path)
        elif protocol == 'gdrive':
            file_id = request.args.get('id')
            local_path = download_from_gdrive(file_id)
        elif protocol == 'onedrive':
            file_id = request.args.get('id')
            local_path = download_from_onedrive(file_id)
        return send_file(local_path, as_attachment=True, attachment_filename=filename)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

def download_from_gdrive(file_id):
    if 'gdrive_credentials' not in session:
        return redirect(url_for('authorize_gdrive'))
    credentials = Credentials(**session['gdrive_credentials'])
    drive_service = build('drive', 'v3', credentials=credentials)
    request = drive_service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
    fh.seek(0)
    return fh

def download_from_onedrive(file_id):
    if 'onedrive_token' not in session:
        return redirect(url_for('authorize_onedrive'))
    headers = {'Authorization': 'Bearer ' + session['onedrive_token']['access_token']}
    response = requests.get(f"https://graph.microsoft.com/v1.0/me/drive/items/{file_id}/content", headers=headers)
    if response.status_code == 200:
        fh = io.BytesIO(response.content)
        return fh
    else:
        raise Exception('Failed to download file from OneDrive')

@app.route('/rename', methods=['POST'])
@login_required
def rename_file():
    global sftp, ftp, smb, webdav
    data = request.json
    old_path = data['oldPath']
    new_path = data['newPath']
    protocol = data['protocol']

    try:
        if protocol == 'sftp' and sftp:
            sftp.rename(old_path, new_path)
        elif protocol == 'ftp' and ftp:
            ftp.rename(old_path, new_path)
        elif protocol == 'smb' and smb:
            smb.rename('smb_share', old_path, new_path)
        elif protocol == 'webdav' and webdav:
            webdav.move(old_path, new_path)
        elif protocol == 'gdrive':
            rename_gdrive_file(data['fileId'], os.path.basename(new_path))
        elif protocol == 'onedrive':
            rename_onedrive_file(data['fileId'], os.path.basename(new_path))
        return jsonify({'status': 'success', 'message': 'File renamed successfully!'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

def rename_gdrive_file(file_id, new_name):
    if 'gdrive_credentials' not in session:
        return redirect(url_for('authorize_gdrive'))
    credentials = Credentials(**session['gdrive_credentials'])
    drive_service = build('drive', 'v3', credentials=credentials)
    file_metadata = {'name': new_name}
    drive_service.files().update(fileId=file_id, body=file_metadata).execute()

def rename_onedrive_file(file_id, new_name):
    if 'onedrive_token' not in session:
        return redirect(url_for('authorize_onedrive'))
    headers = {
        'Authorization': 'Bearer ' + session['onedrive_token']['access_token'],
        'Content-Type': 'application/json'
    }
    data = {'name': new_name}
    response = requests.patch(f"https://graph.microsoft.com/v1.0/me/drive/items/{file_id}", headers=headers, json=data)
    if response.status_code != 200:
        raise Exception('Failed to rename file in OneDrive')

@app.route('/delete', methods=['POST'])
@login_required
def delete_file():
    global sftp, ftp, smb, webdav
    data = request.json
    path = data['path']
    protocol = data['protocol']

    try:
        if protocol == 'sftp' and sftp:
            sftp.remove(path)
        elif protocol == 'ftp' and ftp:
            ftp.delete(path)
        elif protocol == 'smb' and smb:
            smb.deleteFiles('smb_share', path)
        elif protocol == 'webdav' and webdav:
            webdav.clean(path)
        elif protocol == 'gdrive':
            delete_gdrive_file(data['fileId'])
        elif protocol == 'onedrive':
            delete_onedrive_file(data['fileId'])
        return jsonify({'status': 'success', 'message': 'File deleted successfully!'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

def delete_gdrive_file(file_id):
    if 'gdrive_credentials' not in session:
        return redirect(url_for('authorize_gdrive'))
    credentials = Credentials(**session['gdrive_credentials'])
    drive_service = build('drive', 'v3', credentials=credentials)
    drive_service.files().delete(fileId=file_id).execute()

def delete_onedrive_file(file_id):
    if 'onedrive_token' not in session:
        return redirect(url_for('authorize_onedrive'))
    headers = {'Authorization': 'Bearer ' + session['onedrive_token']['access_token']}
    response = requests.delete(f"https://graph.microsoft.com/v1.0/me/drive/items/{file_id}", headers=headers)
    if response.status_code != 204:
        raise Exception('Failed to delete file from OneDrive')

@app.route('/chmod', methods=['POST'])
@login_required
def chmod_file():
    global sftp
    data = request.json
    path = data['path']
    permissions = int(data['permissions'], 8)

    try:
        if sftp:
            sftp.chmod(path, permissions)
            return jsonify({'status': 'success', 'message': 'Permissions changed successfully!'})
        else:
            return jsonify({'status': 'error', 'message': 'CHMOD is only supported for SFTP connections'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

def parse_ftp_line(line):
    parts = line.split()
    is_directory = parts[0].startswith('d')
    name = ' '.join(parts[8:])
    return {
        'name': name,
        'isDirectory': is_directory,
        'size': int(parts[4]),
        'modificationTime': ' '.join(parts[5:8])
    }

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)