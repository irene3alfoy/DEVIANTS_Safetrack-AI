import ipaddress
import json
import os
import shutil
import socket
import subprocess
from pathlib import Path
from urllib.parse import urlparse
import cv2
import httpx
from .config import MAX_BYTES, MAX_DURATION

def ffmpeg_binary():
    configured = os.getenv('FFMPEG_PATH') or shutil.which('ffmpeg')
    if configured:
        return configured
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()

def metadata(path):
    cap = cv2.VideoCapture(str(path))
    try:
        if not cap.isOpened():
            raise ValueError('This file is not a readable video, or its codec is unsupported.')
        fps = cap.get(cv2.CAP_PROP_FPS)
        count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        width, height = int(cap.get(3)), int(cap.get(4))
        if fps <= 0 or count <= 0 or not width or not height:
            raise ValueError('Video metadata is missing. Try re-encoding to MP4.')
        duration = count / fps
        fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
        codec = ''.join(chr((fourcc >> 8*i) & 255) for i in range(4)).strip('\x00')
        result = dict(duration=duration, fps=fps, frame_count=int(count), width=width, height=height, codec=codec, format=Path(path).suffix[1:])
    finally:
        cap.release()
    probe = os.getenv('FFPROBE_PATH') or shutil.which('ffprobe')
    if probe:
        proc = subprocess.run([probe, '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(path)], capture_output=True, text=True, timeout=30)
        if proc.returncode != 0:
            raise ValueError('FFprobe could not read the video.')
        data = json.loads(proc.stdout)
        stream = next((s for s in data['streams'] if s['codec_type'] == 'video'), None)
        if stream:
            result['codec'] = stream['codec_name']
            result['duration'] = float(data.get('format', {}).get('duration', duration))
    if result['duration'] > MAX_DURATION:
        raise ValueError(f'Video exceeds the configured limit of {MAX_DURATION // 3600} hours.')
    return result

def make_preview(source, destination):
    # Browser-compatible H.264 output, streamed on disk. Never hold the file in RAM.
    command = [ffmpeg_binary(), '-nostdin', '-y', '-i', str(source), '-map', '0:v:0', '-map', '0:a?', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-movflags', '+faststart', str(destination)]
    result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=max(180, int(metadata(source)['duration']*4)))
    if result.returncode:
        destination.unlink(missing_ok=True)
        raise ValueError('Could not create a browser-compatible video preview. Check FFmpeg codec support.')

def public_url(url):
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('Use a public HTTP or HTTPS video URL without credentials.')
    if parsed.port not in (None, 80, 443):
        raise ValueError('Only standard public HTTP/HTTPS ports are supported.')
    try:
        addresses = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == 'https' else 80), type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise ValueError('The video host could not be found.')
    if not addresses or any(not ipaddress.ip_address(row[4][0]).is_global for row in addresses):
        raise ValueError('Local, private, and reserved network addresses are not supported.')
    return parsed, addresses

async def download(url, destination):
    # Pin a validated public IP, preserving Host/SNI; DNS cannot redirect the
    # subsequent socket to a private address. Revalidate each redirect.
    async with httpx.AsyncClient(timeout=httpx.Timeout(60, read=120), trust_env=False) as client:
        for _ in range(6):
            parsed, addresses = public_url(url)
            address = addresses[0][4][0]
            pinned = httpx.URL(url).copy_with(host=address)
            async with client.stream('GET', pinned, headers={'Host': parsed.netloc, 'Accept': 'video/*,application/octet-stream'}, extensions={'sni_hostname': parsed.hostname}) as response:
                if response.status_code in (301,302,303,307,308):
                    location = response.headers.get('location')
                    if not location:
                        raise ValueError('The video URL returned an invalid redirect.')
                    url = str(httpx.URL(url).join(location))
                    continue
                response.raise_for_status()
                if 'text/html' in response.headers.get('content-type', ''):
                    raise ValueError('This is a webpage. Use a direct public video file URL; streaming websites and DRM are not supported.')
                length = response.headers.get('content-length')
                if length and int(length) > MAX_BYTES:
                    raise ValueError('Video exceeds the upload size limit.')
                total = 0
                with destination.open('wb') as output:
                    async for chunk in response.aiter_bytes(1024*1024):
                        total += len(chunk)
                        if total > MAX_BYTES:
                            raise ValueError('Video exceeds the upload size limit.')
                        output.write(chunk)
                return total
        raise ValueError('Too many redirects while loading this video.')
