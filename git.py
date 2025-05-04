import os
import base64
import requests

# === CONFIGURATION ===
GITHUB_TOKEN = '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'  # paste your token here
REPO_OWNER = 'K-K-24'                 # e.g. 'krishna-dev'
REPO_NAME = '1Click'                      # the repo you're uploading to
LOCAL_FOLDER=r"C:\Users\I751179\Desktop\bp_content"
       

# === GITHUB API UPLOAD FUNCTION ===
def upload_file_to_github(local_path, repo_path):
    with open(local_path, 'rb') as file:
        content = base64.b64encode(file.read()).decode('utf-8')

    url = f'https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{repo_path}'
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json',
    }
    data = {
        'message': f'Add {repo_path}',
        'content': content,
    }

    response = requests.put(url, headers=headers, json=data)
    if response.status_code == 201:
        print(f'✅ Uploaded: {repo_path}')
    elif response.status_code == 422:
        print(f'⚠️ File already exists: {repo_path}')
    else:
        print(f'❌ Failed to upload {repo_path}: {response.json()}')

# === WALK THE DIRECTORY AND UPLOAD ===
def upload_folder_to_github(local_folder):
    for root, _, files in os.walk(local_folder):
        for file in files:
            local_path = os.path.join(root, file)
            relative_path = os.path.relpath(local_path, local_folder).replace("\\", "/")
            upload_file_to_github(local_path, relative_path)

# === EXECUTE ===
upload_folder_to_github(LOCAL_FOLDER)
