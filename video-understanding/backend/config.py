import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Tiny .env loader: existing process variables always take precedence.
env_file = ROOT / '.env'
if env_file.exists():
    for line in env_file.read_text(encoding='utf-8').splitlines():
        if '=' in line and not line.strip().startswith('#'):
            key, value = line.split('=', 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
DATA = Path(os.getenv('DATA_DIR', str(ROOT / 'data'))).resolve()
DATA.mkdir(parents=True, exist_ok=True)
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://127.0.0.1:11434').rstrip('/')
VISION_MODEL = os.getenv('VISION_MODEL', 'qwen2.5vl:7b')
MAX_BYTES = int(os.getenv('MAX_UPLOAD_MB', '2048')) * 1024 * 1024
MAX_DURATION = int(os.getenv('MAX_DURATION_SECONDS', '14400'))
EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}
