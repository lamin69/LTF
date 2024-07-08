// ~/LTF/LFT_DOCKER/static/js/script.js

let currentPath = '/';

function updateDefaultPort() {
    const protocol = document.getElementById('protocol').value;
    const portInput = document.getElementById('port');
    switch(protocol) {
        case 'sftp': portInput.value = '22'; break;
        case 'ftp': portInput.value = '21'; break;
        case 'smb': portInput.value = '445'; break;
        case 'webdav': portInput.value = '80'; break;
    }
}

function connect() {
    const data = {
        protocol: document.getElementById('protocol').value,
        server: document.getElementById('server').value,
        port: document.getElementById('port').value,
        username: document.getElementById('username').value,
        password: document.getElementById('password').value
    };
    axios.post('/connect', data)
        .then(response => {
            alert(response.data.message);
            updateConnectionStatus(true);
            document.getElementById('fileBrowser').style.display = 'block';
            listFiles(currentPath);
        })
        .catch(error => {
            alert(error.response.data.message);
            updateConnectionStatus(false);
        });
}

function updateConnectionStatus(isConnected) {
    const statusIcon = document.querySelector('.status-icon');
    statusIcon.style.backgroundColor = isConnected ? 'green' : 'red';
}

function listFiles(path) {
    currentPath = path;
    axios.post('/list_files', { path: path })
        .then(response => {
            const fileList = document.getElementById('fileList');
            fileList.innerHTML = '';
            if (path !== '/') {
                const li = document.createElement('li');
                li.textContent = '..';
                li.classList.add('folder');
                li.onclick = () => listFiles(path.split('/').slice(0, -1).join('/') || '/');
                fileList.appendChild(li);
            }
            response.data.files.forEach(file => {
                const li = document.createElement('li');
                li.textContent = file.name;
                li.classList.add(file.isDirectory ? 'folder' : 'file');
                li.onclick = () => file.isDirectory ? listFiles(path + '/' + file.name) : selectFile(li);
                fileList.appendChild(li);
            });
        })
        .catch(error => alert(error.response.data.message));
}

function selectFile(element) {
    document.querySelectorAll('#fileList li').forEach(li => li.classList.remove('selected'));
    element.classList.add('selected');
}

function saveProfile() {
    const profileName = document.getElementById('profileName').value;
    if (!profileName) {
        alert('Please enter a profile name');
        return;
    }
    const profile = {
        name: profileName,
        protocol: document.getElementById('protocol').value,
        server: document.getElementById('server').value,
        port: document.getElementById('port').value,
        username: document.getElementById('username').value
    };
    const profiles = JSON.parse(localStorage.getItem('profiles') || '[]');
    profiles.push(profile);
    localStorage.setItem('profiles', JSON.stringify(profiles));
    updateProfileList();
}

function updateProfileList() {
    const profiles = JSON.parse(localStorage.getItem('profiles') || '[]');
    const select = document.getElementById('savedProfiles');
    select.innerHTML = '<option value="">Select a profile</option>';
    profiles.forEach((profile, index) => {
        const option = document.createElement('option');
        option.value = index;
        option.textContent = profile.name;
        select.appendChild(option);
    });
}

function deleteProfile() {
    const select = document.getElementById('savedProfiles');
    const index = select.value;
    if (index) {
        const profiles = JSON.parse(localStorage.getItem('profiles') || '[]');
        profiles.splice(index, 1);
        localStorage.setItem('profiles', JSON.stringify(profiles));
        updateProfileList();
    }
}

document.getElementById('savedProfiles').onchange = function() {
    const profiles = JSON.parse(localStorage.getItem('profiles') || '[]');
    const profile = profiles[this.value];
    if (profile) {
        document.getElementById('protocol').value = profile.protocol;
        document.getElementById('server').value = profile.server;
        document.getElementById('port').value = profile.port;
        document.getElementById('username').value = profile.username;
        updateDefaultPort();
    }
};

function uploadFile() {
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.onchange = (event) => {
        const file = event.target.files[0];
        const formData = new FormData();
        formData.append('file', file);
        formData.append('path', currentPath);
        axios.post('/upload', formData)
            .then(response => {
                alert(response.data.message);
                listFiles(currentPath);
            })
            .catch(error => alert(error.response.data.message));
    };
    fileInput.click();
}

function downloadFile() {
    const selectedFile = document.querySelector('#fileList li.selected');
    if (selectedFile && selectedFile.textContent !== '..') {
        const path = currentPath + '/' + selectedFile.textContent;
        window.location.href = `/download?path=${encodeURIComponent(path)}`;
    } else {
        alert('Please select a file to download');
    }
}

function renameFile() {
    const selectedFile = document.querySelector('#fileList li.selected');
    if (selectedFile && selectedFile.textContent !== '..') {
        const oldName = selectedFile.textContent;
        const newName = prompt('Enter new name:', oldName);
        if (newName && newName !== oldName) {
            const oldPath = currentPath + '/' + oldName;
            const newPath = currentPath + '/' + newName;
            axios.post('/rename', { oldPath, newPath })
                .then(response => {
                    alert(response.data.message);
                    listFiles(currentPath);
                })
                .catch(error => alert(error.response.data.message));
        }
    } else {
        alert('Please select a file or folder to rename');
    }
}

function deleteFile() {
    const selectedFile = document.querySelector('#fileList li.selected');
    if (selectedFile && selectedFile.textContent !== '..') {
        if (confirm('Are you sure you want to delete this file/folder?')) {
            const path = currentPath + '/' + selectedFile.textContent;
            axios.post('/delete', { path })
                .then(response => {
                    alert(response.data.message);
                    listFiles(currentPath);
                })
                .catch(error => alert(error.response.data.message));
        }
    } else {
        alert('Please select a file or folder to delete');
    }
}

function changePermissions() {
    const selectedFile = document.querySelector('#fileList li.selected');
    if (selectedFile && selectedFile.textContent !== '..') {
        const permissions = prompt('Enter new permissions (e.g., 755):');
        if (permissions) {
            const path = currentPath + '/' + selectedFile.textContent;
            axios.post('/chmod', { path, permissions })
                .then(response => {
                    alert(response.data.message);
                    listFiles(currentPath);
                })
                .catch(error => alert(error.response.data.message));
        }
    } else {
        alert('Please select a file or folder to change permissions');
    }
}

function matrixEffect() {
    const title = document.getElementById('matrixTitle');
    const text = title.textContent;
    let i = 0;
    title.textContent = '';
    const interval = setInterval(() => {
        if (i < text.length) {
            title.textContent += text[i];
            i++;
        } else {
            clearInterval(interval);
        }
    }, 100);
}

window.onload = function() {
    updateProfileList();
    matrixEffect();
    updateDefaultPort();
};
