let currentPath = '/';
let selectedFiles = new Set();

function updateDefaultPort() {
    const protocol = document.getElementById('protocol').value;
    const portInput = document.getElementById('port');
    switch(protocol) {
        case 'sftp':
            portInput.value = '22';
            break;
        case 'ftp':
            portInput.value = '21';
            break;
        case 'smb':
            portInput.value = '445';
            break;
        case 'webdav':
            portInput.value = '80';
            break;
        case 'gdrive':
        case 'onedrive':
            portInput.value = '';
            portInput.disabled = true;
            break;
        default:
            portInput.value = '';
            portInput.disabled = false;
    }
}

function connect() {
    const protocol = document.getElementById('protocol').value;
    const server = document.getElementById('server').value;
    const port = document.getElementById('port').value;
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    axios.post('/connect', {
        protocol: protocol,
        server: server,
        port: port,
        username: username,
        password: password
    })
    .then(function (response) {
        document.querySelector('.status-icon').style.backgroundColor = 'green';
        document.getElementById('fileBrowser').style.display = 'block';
        listFiles('/');
    })
    .catch(function (error) {
        alert('Connection failed: ' + error.response.data.message);
    });
}

function listFiles(path) {
    currentPath = path;
    axios.post('/list_files', {
        path: path,
        protocol: document.getElementById('protocol').value
    })
    .then(function (response) {
        const fileList = document.getElementById('fileList');
        fileList.innerHTML = '';
        response.data.files.forEach(function(file) {
            const li = document.createElement('li');
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.className = 'file-checkbox';
            checkbox.addEventListener('change', function() {
                if (this.checked) {
                    selectedFiles.add(file.name);
                } else {
                    selectedFiles.delete(file.name);
                }
            });
            li.appendChild(checkbox);
            
            const icon = document.createElement('span');
            icon.className = 'file-icon';
            icon.innerHTML = file.isDirectory ? '📁' : '📄';
            li.appendChild(icon);
            
            const nameSpan = document.createElement('span');
            nameSpan.textContent = file.name;
            li.appendChild(nameSpan);
            
            li.addEventListener('dblclick', function() {
                if (file.isDirectory) {
                    listFiles(path + '/' + file.name);
                }
            });
            fileList.appendChild(li);
        });
    })
    .catch(function (error) {
        alert('Failed to list files: ' + error.response.data.message);
    });
}
function uploadFile() {
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.onchange = function(event) {
        const file = event.target.files[0];
        const formData = new FormData();
        formData.append('file', file);
        formData.append('path', currentPath);
        formData.append('protocol', document.getElementById('protocol').value);

        axios.post('/upload', formData, {
            headers: {
                'Content-Type': 'multipart/form-data'
            }
        })
        .then(function (response) {
            alert('File uploaded successfully!');
            listFiles(currentPath);
        })
        .catch(function (error) {
            alert('Upload failed: ' + error.response.data.message);
        });
    };
    fileInput.click();
}

function downloadFile() {
    if (selectedFiles.size !== 1) {
        alert('Please select exactly one file to download.');
        return;
    }
    const fileName = Array.from(selectedFiles)[0];
    const filePath = currentPath + '/' + fileName;
    const protocol = document.getElementById('protocol').value;
    
    window.location.href = `/download?path=${encodeURIComponent(filePath)}&protocol=${protocol}`;
}

function renameFile() {
    if (selectedFiles.size !== 1) {
        alert('Please select exactly one file to rename.');
        return;
    }
    const oldName = Array.from(selectedFiles)[0];
    const newName = prompt('Enter new name:', oldName);
    if (newName && newName !== oldName) {
        const oldPath = currentPath + '/' + oldName;
        const newPath = currentPath + '/' + newName;
        const protocol = document.getElementById('protocol').value;

        axios.post('/rename', {
            oldPath: oldPath,
            newPath: newPath,
            protocol: protocol
        })
        .then(function (response) {
            alert('File renamed successfully!');
            listFiles(currentPath);
        })
        .catch(function (error) {
            alert('Rename failed: ' + error.response.data.message);
        });
    }
}

function deleteFile() {
    if (selectedFiles.size === 0) {
        alert('Please select at least one file to delete.');
        return;
    }
    if (confirm('Are you sure you want to delete the selected file(s)?')) {
        const protocol = document.getElementById('protocol').value;
        const deletePromises = Array.from(selectedFiles).map(fileName => {
            const filePath = currentPath + '/' + fileName;
            return axios.post('/delete', {
                path: filePath,
                protocol: protocol
            });
        });

        Promise.all(deletePromises)
        .then(function (responses) {
            alert('File(s) deleted successfully!');
            listFiles(currentPath);
        })
        .catch(function (error) {
            alert('Delete failed: ' + error.response.data.message);
        });
    }
}

function changePermissions() {
    if (selectedFiles.size !== 1) {
        alert('Please select exactly one file to change permissions.');
        return;
    }
    const fileName = Array.from(selectedFiles)[0];
    const filePath = currentPath + '/' + fileName;
    const permissions = prompt('Enter new permissions (e.g., 755):', '');
    if (permissions) {
        axios.post('/chmod', {
            path: filePath,
            permissions: permissions,
            protocol: document.getElementById('protocol').value
        })
        .then(function (response) {
            alert('Permissions changed successfully!');
        })
        .catch(function (error) {
            alert('Failed to change permissions: ' + error.response.data.message);
        });
    }
}

function saveProfile() {
    const profileName = document.getElementById('profileName').value;
    if (!profileName) {
        alert('Please enter a profile name.');
        return;
    }
    const profile = {
        protocol: document.getElementById('protocol').value,
        server: document.getElementById('server').value,
        port: document.getElementById('port').value,
        username: document.getElementById('username').value,
        password: document.getElementById('password').value
    };
    localStorage.setItem('profile_' + profileName, JSON.stringify(profile));
    loadProfiles();
}

function loadProfiles() {
    const profileSelect = document.getElementById('savedProfiles');
    profileSelect.innerHTML = '<option value="">Select a profile</option>';
    for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key.startsWith('profile_')) {
            const profileName = key.substring(8);
            const option = document.createElement('option');
            option.value = profileName;
            option.textContent = profileName;
            profileSelect.appendChild(option);
        }
    }
}

function loadProfile() {
    const profileName = document.getElementById('savedProfiles').value;
    if (profileName) {
        const profile = JSON.parse(localStorage.getItem('profile_' + profileName));
        document.getElementById('protocol').value = profile.protocol;
        document.getElementById('server').value = profile.server;
        document.getElementById('port').value = profile.port;
        document.getElementById('username').value = profile.username;
        document.getElementById('password').value = profile.password;
    }
}

function deleteProfile() {
    const profileName = document.getElementById('savedProfiles').value;
    if (profileName) {
        localStorage.removeItem('profile_' + profileName);
        loadProfiles();
    }
}

document.addEventListener('DOMContentLoaded', function() {
    loadProfiles();
    document.getElementById('savedProfiles').addEventListener('change', loadProfile);
});