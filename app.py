from flask import Flask, request, jsonify, send_from_directory
import yt_dlp as youtube_dl
import os
import re
from datetime import datetime, timedelta
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DOWNLOAD_FOLDER = 'downloads'
ALLOWED_DOMAINS = [
    'instagram.com', 'www.instagram.com',
    'youtube.com', 'www.youtube.com', 'youtu.be',
    'tiktok.com', 'www.tiktok.com',
    'facebook.com', 'www.facebook.com',
    'twitter.com', 'x.com', 'www.x.com'
]

if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

def cleanup_old_files():
    now = datetime.now()
    for filename in os.listdir(DOWNLOAD_FOLDER):
        file_path = os.path.join(DOWNLOAD_FOLDER, filename)
        if os.path.isfile(file_path):
            file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            if now - file_time > timedelta(hours=6):
                os.remove(file_path)
                logger.info(f"Deleted old file: {filename}")

def is_valid_url(url):
    platform_patterns = {
        'instagram': r'(https?://)?(www\.)?instagram\.com/(reel|p)/',
        'tiktok': r'(https?://)?(www\.)?tiktok\.com/@',
        'youtube': r'(https?://)?(www\.)?(youtube\.com/watch|youtu\.be/)',
        'facebook': r'(https?://)?(www\.)?facebook\.com/',
        'twitter': r'(https?://)?(www\.)?(twitter\.com|x\.com)/'
    }
    return any(re.search(pattern, url) for pattern in platform_patterns.values())

@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

@app.route('/download', methods=['POST'])

def download_video():
    data = request.json
    video_url = data.get('link', '').strip()

    if not is_valid_url(video_url):
        return jsonify({'success': False, 'error': 'Unsupported platform or invalid URL'})

    try:
        ydl_opts = {
            'format': 'best',
            'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s.%(ext)s'),
            'quiet': True,
            'noplaylist': True,
            # Add cookies configuration
            'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
            'extractor_args': {
                'instagram': ['--no-check-certificate'],
                'facebook': ['--no-check-certificate']
            }
        }

        # Add custom error handler
        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(video_url, download=True)
        except youtube_dl.utils.AgeRestrictedError:
            logger.error("Age restricted content detected")
            return jsonify({
                'success': False,
                'error': 'Age-restricted content. Please login using cookies.',
                'solution': 'https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp'
            })

        # Rest of the code remains the same...

    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

def detect_platform(url):
    if 'instagram.com' in url: return 'instagram'
    if 'tiktok.com' in url: return 'tiktok'
    if 'youtube.com' in url or 'youtu.be' in url: return 'youtube'
    if 'facebook.com' in url: return 'facebook'
    if 'twitter.com' in url or 'x.com' in url: return 'twitter'
    return 'unknown'

@app.route('/downloads/<filename>')
def serve_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))