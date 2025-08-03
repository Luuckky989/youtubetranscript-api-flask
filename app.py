from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import requests
import random
import time
import os
from urllib.parse import urlparse

app = Flask(__name__)

class AntiBlockYouTubeAPI:
    def __init__(self):
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15',
        ]
        
        self.countries = ['US', 'GB', 'CA', 'AU', 'DE', 'FR', 'JP', 'KR']
        self.languages = ['en-US,en;q=0.9', 'en-GB,en;q=0.9', 'ko-KR,ko;q=0.9', 'ja-JP,ja;q=0.9']
    
    def get_random_headers(self):
        """랜덤 헤더 생성"""
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': random.choice(self.languages),
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'X-Forwarded-For': f'{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}',
            'X-Real-IP': f'{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}',
            'CF-Connecting-IP': f'{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}',
        }
    
    def create_session(self):
        """세션 생성"""
        session = requests.Session()
        session.headers.update(self.get_random_headers())
        
        # 쿠키 추가 (YouTube 접근 이력 시뮬레이션)
        session.cookies.update({
            'CONSENT': 'YES+cb.20210328-17-p0.en+FX+' + str(random.randint(100, 999)),
            'VISITOR_INFO1_LIVE': 'dQw4w9WgXcQ',
            'YSC': ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=16)),
        })
        
        return session
    
    def get_transcript_with_retries(self, video_id, language="auto", max_retries=5):
        """여러 방법으로 transcript 시도"""
        
        for attempt in range(max_retries):
            try:
                # 각 시도마다 새로운 세션
                session = self.create_session()
                ytt_api = YouTubeTranscriptApi(http_client=session)
                
                # 랜덤 딜레이 (봇 감지 방지)
                if attempt > 0:
                    time.sleep(random.uniform(0.5, 2.0))
                
                # Transcript 목록 가져오기
                transcript_list = ytt_api.list(video_id)
                
                if language == "auto":
                    languages_to_try = [
                        'ko', 'en', 'ja', 'zh', 'zh-CN',
                        'ar', 'ar-SA', 'ar-EG', 'ar-AE', 'ar-JO', 'ar-LB',
                        'ms', 'id', 'ur', 'hi', 'tr', 'fa', 'bn',
                        'es', 'fr', 'de', 'it', 'pt', 'ru'
                    ]
                    transcript = transcript_list.find_transcript(languages_to_try)
                    used_language = transcript.language_code
                else:
                    transcript = transcript_list.find_transcript([language])
                    used_language = language
                
                # 실제 데이터 가져오기
                fetched_transcript = transcript.fetch()
                
                # 데이터 변환
                if hasattr(fetched_transcript, 'to_raw_data'):
                    transcript_data = fetched_transcript.to_raw_data()
                else:
                    transcript_data = []
                    for snippet in fetched_transcript:
                        transcript_data.append({
                            "text": snippet.text,
                            "start": snippet.start,
                            "duration": snippet.duration
                        })
                
                return {
                    "success": True,
                    "transcript": transcript_data,
                    "language": used_language,
                    "video_id": video_id,
                    "auto_detected": language == "auto",
                    "is_generated": transcript.is_generated,
                    "is_translatable": transcript.is_translatable,
                    "attempt": attempt + 1
                }
                
            except (TranscriptsDisabled, NoTranscriptFound) as e:
                return {
                    "success": False,
                    "error": f"No transcript available: {str(e)}",
                    "video_id": video_id
                }
            
            except Exception as e:
                last_error = str(e)
                print(f"Attempt {attempt + 1} failed: {last_error}")
                
                # IP 차단 관련 에러면 더 오래 기다림
                if "blocked" in last_error.lower() or "403" in last_error:
                    time.sleep(random.uniform(3, 8))
                
                continue
        
        return {
            "success": False,
            "error": f"All {max_retries} attempts failed. Last error: {last_error}",
            "video_id": video_id,
            "suggestion": "Video might be restricted or servers are blocking requests"
        }

# 전역 인스턴스
anti_block_api = AntiBlockYouTubeAPI()

@app.route("/")
def home():
    return "YouTube Transcript API with Anti-Block Protection is working!"

@app.route("/get-transcript", methods=["GET"])
def get_transcript():
    video_id = request.args.get("video_id")
    language = request.args.get("language", "auto")
    max_retries = int(request.args.get("max_retries", "5"))
    
    if not video_id:
        return jsonify({"error": "Missing video_id"}), 400
    
    # Anti-block API 사용
    result = anti_block_api.get_transcript_with_retries(video_id, language, max_retries)
    
    if result["success"]:
        return jsonify({
            "has_transcript": True,
            "transcript": result["transcript"],
            "language": result["language"],
            "video_id": result["video_id"],
            "auto_detected": result["auto_detected"],
            "is_generated": result["is_generated"],
            "is_translatable": result["is_translatable"],
            "attempt": result["attempt"]
        })
    else:
        return jsonify({
            "has_transcript": False,
            "error": result["error"],
            "video_id": result["video_id"]
        }), 500

@app.route("/bulk-transcript", methods=["POST"])
def bulk_transcript():
    """여러 비디오를 한 번에 처리 (딜레이 포함)"""
    video_ids = request.json.get("video_ids", [])
    language = request.json.get("language", "auto")
    
    if not video_ids:
        return jsonify({"error": "Missing video_ids"}), 400
    
    results = []
    
    for i, video_id in enumerate(video_ids):
        # 각 요청 사이에 랜덤 딜레이
        if i > 0:
            time.sleep(random.uniform(2, 5))
        
        result = anti_block_api.get_transcript_with_retries(video_id, language)
        results.append(result)
    
    success_count = sum(1 for r in results if r["success"])
    
    return jsonify({
        "total_processed": len(video_ids),
        "success_count": success_count,
        "failure_count": len(video_ids) - success_count,
        "success_rate": f"{success_count/len(video_ids)*100:.1f}%",
        "results": results
    })

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "anti_block": "enabled"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
