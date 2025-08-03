from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import os
import time
import random
import requests

app = Flask(__name__)

def create_enhanced_session():
    """향상된 세션 생성"""
    session = requests.Session()
    
    # 랜덤 User-Agent
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    ]
    
    session.headers.update({
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,ko;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    })
    
    # 간단한 쿠키
    session.cookies.update({
        'CONSENT': f'YES+cb.20210328-17-p0.en+FX+{random.randint(100, 999)}',
        'VISITOR_INFO1_LIVE': ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=22)),
    })
    
    return session

@app.route("/")
def home():
    return "Simple YouTube Transcript API is working!"

@app.route("/get-transcript", methods=["GET"])
def get_transcript():
    video_id = request.args.get("video_id")
    language = request.args.get("language", "auto")
    
    if not video_id:
        return jsonify({"error": "Missing video_id"}), 400
    
    # 짧은 딜레이
    time.sleep(random.uniform(0.5, 1.5))
    
    try:
        # 향상된 세션으로 API 생성
        session = create_enhanced_session()
        ytt_api = YouTubeTranscriptApi(http_client=session)
        
        # TranscriptList 먼저 가져오기
        transcript_list = ytt_api.list(video_id)
        
        if language == "auto":
            # 자동 언어 감지: 우선순위 언어 리스트로 찾기
            languages_to_try = [
                'ko', 'en', 'ja', 'zh', 'zh-CN',
                'ar', 'ar-SA', 'ar-EG', 'ar-AE', 'ar-JO', 'ar-LB',
                'ms', 'id', 'ur', 'hi', 'tr', 'fa', 'bn',
                'es', 'fr', 'de'
            ]
            
            # find_transcript 메서드로 우선순위 언어 찾기
            transcript = transcript_list.find_transcript(languages_to_try)
            used_language = transcript.language_code
        else:
            # 특정 언어 지정
            transcript = transcript_list.find_transcript([language])
            used_language = language
        
        # 실제 transcript 데이터 가져오기
        fetched_transcript = transcript.fetch()
        
        # FetchedTranscript 객체를 raw data로 변환
        if hasattr(fetched_transcript, 'to_raw_data'):
            transcript_data = fetched_transcript.to_raw_data()
        else:
            # 만약 to_raw_data가 없다면 직접 변환
            transcript_data = []
            for snippet in fetched_transcript:
                transcript_data.append({
                    "text": snippet.text,
                    "start": snippet.start,
                    "duration": snippet.duration
                })
        
        return jsonify({
            "has_transcript": True,
            "transcript": transcript_data,
            "language": used_language,
            "video_id": video_id,
            "auto_detected": language == "auto",
            "is_generated": transcript.is_generated,
            "is_translatable": transcript.is_translatable,
            "method": "simple_enhanced"
        })
        
    except (TranscriptsDisabled, NoTranscriptFound):
        return jsonify({
            "has_transcript": False, 
            "error": "No transcript available",
            "video_id": video_id
        })
    except Exception as e:
        return jsonify({
            "error": str(e), 
            "has_transcript": False,
            "video_id": video_id
        }), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
