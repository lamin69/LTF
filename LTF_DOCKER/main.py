from flask import Flask, render_template, request, jsonify, send_file
import os
import paramiko
from werkzeug.utils import secure_filename
from smb.SMBConnection import SMBConnection
from ftplib import FTP
import requests
from webdav3.client import Client
import shutil

app = Flask(__name__)

client = None
sftp = None
ftp = None
smb = None
webdav = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/connect', methods=['POST'])
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
        else:
            return jsonify({'status': 'error', 'message': 'Unsupported protocol'}), 400
        return jsonify({'status': 'success', 'message': 'Connected successfully!'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/list_files', methods=['POST'])
def list_files():
    global sftp, ftp, smb, webdav
    data = request.json
    path = data['path']

    try:
        files = []
        if sftp:
            for entry in sftp.listdir_attr(path):
                files.append({
                    'name': entry.filename,
                    'isDirectory': entry.longname.startswith('d'),
                    'size': entry.st_size,
                    'modificationTime': entry.st_mtime
                })
        elif ftp:
            ftp.cwd(path)
            ftp.retrlines('LIST', lambda line: files.append(parse_ftp_line(line)))
        elif smb:
            for entry in smb.listPath('smb_share', path):
                files.append({
                    'name': entry.filename,
                    'isDirectory': entry.isDirectory,
                    'size': entry.file_size,
                    'modificationTime': entry.last_write_time
                })
        elif webdav:
            for item in webdav.list(path):
                files.append({
                    'name': item,
                    'isDirectory': webdav.is_dir(item),
                    'size': webdav.info(item).get('size', 0),
                    'modificationTime': webdav.info(item).get('modified', '')
                })
        return jsonify({'status': 'success', 'files': files})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/upload', methods=['POST'])
def upload_file():
    global sftp, ftp, smb, webdav
    file = request.files['file']
    path = request.form['path']

    try:
        filename = secure_filename(file.filename)
        remote_path = os.path.join(path, filename)
        if sftp:
            sftp.putfo(file.stream, remote_path)
        elif ftp:
            ftp.storbinary(f'STOR {remote_path}', file.stream)
        elif smb:
            with smb.openFile('smb_share', remote_path, 'w') as f:
                f.write(file.read())
        elif webdav:
            webdav.upload_to(remote_path, file.stream)
        return jsonify({'status': 'success', 'message': 'File uploaded successfully!'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/download')
def download_file():
    global sftp, ftp, smb, webdav
    path = request.args.get('path')

    try:
        filename = os.path.basename(path)
        local_path = os.path.join('/tmp', filename)
        if sftp:
            sftp.get(path, local_path)
        elif ftp:
            with open(local_path, 'wb') as f:
                ftp.retrbinary(f'RETR {path}', f.write)
        elif smb:
            with open(local_path, 'wb') as f:
                smb.retrieveFile('smb_share', path, f)
        elif webdav:
            webdav.download_file(path, local_path)
        return send_file(local_path, as_attachment=True, attachment_filename=filename)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/rename', methods=['POST'])
def rename_file():
    global sftp, ftp, smb, webdav
    data = request.json
    old_path = data['oldPath']
    new_path = data['newPath']

    try:
        if sftp:
            sftp.rename(old_path, new_path)
        elif ftp:
            ftp.rename(old_path, new_path)
        elif smb:
            smb.rename('smb_share', old_path, new_path)
        elif webdav:
            webdav.move(old_path, new_path)
        return jsonify({'status': 'success', 'message': 'File renamed successfully!'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/delete', methods=['POST'])
def delete_file():
    global sftp, ftp, smb, webdav
    data = request.json
    path = data['path']

    try:
        if sftp:
            sftp.remove(path)
        elif ftp:
            ftp.delete(path)
        elif smb:
            smb.deleteFiles('smb_share', path)
        elif webdav:
            webdav.clean(path)
        return jsonify({'status': 'success', 'message': 'File deleted successfully!'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/chmod', methods=['POST'])
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
