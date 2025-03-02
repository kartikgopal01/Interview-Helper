import os
import platform
import subprocess
import requests
from zipfile import ZipFile
import sys

def download_file(url, filename):
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    
    with open(filename, 'wb') as f:
        if total_size == 0:
            f.write(response.content)
        else:
            downloaded = 0
            for data in response.iter_content(chunk_size=4096):
                downloaded += len(data)
                f.write(data)
                done = int(50 * downloaded / total_size)
                sys.stdout.write('\r[{}{}]'.format('=' * done, ' ' * (50 - done)))
                sys.stdout.flush()
    print()

def setup_ollama():
    if platform.system() == 'Windows':
        ollama_path = os.path.join(os.getenv('LOCALAPPDATA'), 'ollama')
        os.makedirs(ollama_path, exist_ok=True)
        
        # Download Ollama
        print("Downloading Ollama...")
        download_file(
            'https://ollama.ai/download/ollama-windows-amd64.zip',
            'ollama-windows-amd64.zip'
        )
        
        # Extract Ollama
        print("Extracting Ollama...")
        with ZipFile('ollama-windows-amd64.zip', 'r') as zip_ref:
            zip_ref.extractall(ollama_path)
        
        # Cleanup
        os.remove('ollama-windows-amd64.zip')
        print("Ollama installed successfully!")
    else:
        print("Please install Ollama manually from https://ollama.ai/download")

if __name__ == "__main__":
    setup_ollama() 