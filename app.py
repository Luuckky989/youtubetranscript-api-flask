from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import os
import time
import random
import requests
import hashlib
import json
from datetime import datetime, timedelta

app = Flask(__name__)

class SessionPool:
    """Apify 스타일의 Session Pool 구현"""
    
    def __init__(self, max_pool_size=50, session_max_age_hours=24):
        self.sessions = {}
        self.max_pool_size = max_pool_size
        self.session_max_age = timedelta(hours=session_max_age_hours)
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/120.0',
        ]
        
    def create_session_fingerprint(self):
        """고유한 브라우저 핑거프린트 생성"""
        base_data = {
            'user_agent': random.choice(self.user_agents),
            'viewport': random.choice(['1920x1080', '1366x768', '1440x900', '1536x864']),
            'timezone': random.choice(['America/New_York', 'Europe/London', 'Asia/Seoul', 'Asia/Tokyo']),
            'language': random.choice(['en-US', 'en-GB', 'ko-KR', 'ja-JP']),
            'platform': random.choice(['Win32', 'MacIntel', 'Linux x86_64']),
        }
        
        # 고유 식별자 생성
        fingerprint_str = json.dumps(base_data, sort_keys=True)
        fingerprint_hash = hashlib.md5(fingerprint_str.encode()).hexdigest()[:16]
        
        return fingerprint_hash, base_data
    
    def create_session_cookies(self, session_id):
        """세션별 고유 쿠키 생성"""
        base_time = int(time.time())
        return {
            'CONSENT': f'YES+cb.20210328-17-p0.en+FX+{random.randint(100, 999)}',
            'VISITOR_INFO1_LIVE': f'session_{session_id}_{base_time}',
            'YSC': ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_', k=16)),
            'PREF': f'f4=4000000&tz=Asia.Seoul&f6=40000000&f5=20000',
            'GPS': '1',
            '__Secure-3PSID': f'session_{session_id}_secure',
        }
    
    def get_or_create_session(self, session_hint=None):
        """세션 가져오기 또는 생성"""
        
        # 만료된 세션 정리
        self._cleanup_expired_sessions()
        
        # 세션 힌트가 있으면 해당 세션 찾기
        if session_hint and session_hint in self.sessions:
            session = self.sessions[session_hint]
            session['last_used'] = datetime.now()
            session['usage_count'] += 1
            return session_hint, session
        
        # 새 세션 생성
        if len(self.sessions) >= self.max_pool_size:
            # 가장 오래된 세션 제거
            oldest_session = min(self.sessions.keys(), 
                                key=lambda k: self.sessions[k]['last_used'])
            del self.sessions[oldest_session]
        
        # 고유 세션 ID 생성
        session_id = f"yt_session_{len(self.sessions)}_{int(time.time())}"
        fingerprint_id, fingerprint_data = self.create_session_fingerprint()
        
        # 새 세션 데이터
        session_data = {
            'session_id': session_id,
            'fingerprint_id': fingerprint_id,
            'fingerprint_data': fingerprint_data,
            'cookies': self.create_session_cookies(session_id),
            'created_at': datetime.now(),
            'last_used': datetime.now(),
            'usage_count': 1,
            'success_count': 0,
            'failure_count': 0,
        }
        
        self.sessions[session_id] = session_data
        return session_id, session_data
    
    def mark_session_result(self, session_id, success=True):
        """세션 결과 기록"""
        if session_id in self.sessions:
            if success:
                self.sessions[session_id]['success_count'] += 1
            else:
                self.sessions[session_id]['failure_count'] += 1
                
                # 실패율이 높으면 세션 제거
                session = self.sessions[session_id]
                failure_rate = session['failure_count'] / session['usage_count']
                if failure_rate > 0.7 and session['usage_count'] > 5:
                    del self.sessions[session_id]
    
    def _cleanup_expired_sessions(self):
        """만료된 세션 정리"""
        now = datetime.now()
        expired_sessions = []
        
        for session_id, session_data in self.sessions.items():
            if now - session_data['last_used'] > self.session_max_age:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
    
    def create_session_request(self, session_data):
        """세션 데이터로 HTTP 세션 생성"""
        session = requests.Session()
        
        # 헤더 설정
        session.headers.update({
            'User-Agent': session_data['fingerprint_data']['user_agent'],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': f"{session_data['fingerprint_data']['language']},en;q=0.9",
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': f'"{session_data["fingerprint_data"]["platform"]}"',
        })
        
        # 쿠키 설정
        session.cookies.update(session_data['cookies'])
        
        return session

class ApifyStyleYouTubeAPI:
    def __init__(self):
        self.session_pool = SessionPool()
        self.request_count = 0
        self.success_count = 0
        
    def get_transcript_with_session_pool(self, video_id, language="auto", max_retries=5):
        """Session Pool을 사용한 transcript 추출"""
        
        # 스마트 딜레이 (하루 500개 기준)
        delay = max(86400 / 500, 2.0) + random.uniform(1, 3)
        time.sleep(delay)
        
        self.request_count += 1
        
        # 세션 로테이션 (5번 사용 후 변경)
        session_hint = f"batch_{self.request_count // 5}"
        
        for attempt in range(max_retries):
            try:
                # 세션 가져오기
                session_id, session_data = self.session_pool.get_or_create_session(session_hint)
                
                # HTTP 세션 생성
                http_session = self.session_pool.create_session_request(session_data)
                
                # YouTube API 생성
                ytt_api = YouTubeTranscriptApi(http_client=http_session)
                
                print(f"Request #{self.request_count}, Session: {session_id[:12]}..., Attempt: {attempt + 1}")
                
                # 추가 딜레이 (재시도시)
                if attempt > 0:
                    time.sleep(random.uniform(5, 15))
                
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
                
                # 데이터 가져오기
                fetched_transcript = transcript.fetch()
                
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
                
                # 성공 기록
                self.session_pool.mark_session_result(session_id, True)
                self.success_count += 1
                
                return {
                    "success": True,
                    "transcript": transcript_data,
                    "language": used_language,
                    "video_id": video_id,
                    "auto_detected": language == "auto",
                    "is_generated": transcript.is_generated,
                    "is_translatable": transcript.is_translatable,
                    "session_id": session_id[:12],
                    "attempt": attempt + 1,
                    "request_count": self.request_count,
                    "success_rate": f"{self.success_count/self.request_count*100:.1f}%"
                }
                
            except (TranscriptsDisabled, NoTranscriptFound):
                self.session_pool.mark_session_result(session_id, False)
                return {
                    "success": False,
                    "error": "No transcript available",
                    "video_id": video_id,
                    "skip": True
                }
            
            except Exception as e:
                error_msg = str(e).lower()
                print(f"Attempt {attempt + 1} failed: {e}")
                
                # 실패 기록
                self.session_pool.mark_session_result(session_id, False)
                
                # 파싱 에러는 건너뛰기
                if "not parsable" in error_msg:
                    return {
                        "success": False,
                        "error": "Video data not parsable",
                        "video_id": video_id,
                        "skip": True
                    }
                
                # IP 차단 시 더 긴 대기
                if "blocked" in error_msg or "403" in error_msg:
                    if attempt < max_retries - 1:
                        time.sleep(random.uniform(30, 60))
                        continue
                
                # 마지막 시도
                if attempt == max_retries - 1:
                    return {
                        "success": False,
                        "error": str(e),
                        "video_id": video_id,
                        "skip": False
                    }
        
        return {
            "success": False,
            "error": "Max retries exceeded",
            "video_id": video_id,
            "skip": False
        }

# 전역 인스턴스
apify_style_api = ApifyStyleYouTubeAPI()

@app.route("/")
def home():
    return f"Apify-Style YouTube API | Sessions: {len(apify_style_api.session_pool.sessions)} | Requests: {apify_style_api.request_count} | Success: {apify_style_api.success_count}"

@app.route("/get-transcript", methods=["GET"])
def get_transcript():
    video_id = request.args.get("video_id")
    language = request.args.get("language", "auto")
    
    if not video_id:
        return jsonify({"error": "Missing video_id"}), 400
    
    result = apify_style_api.get_transcript_with_session_pool(video_id, language)
    
    if result["success"]:
        return jsonify({
            "has_transcript": True,
            "transcript": result["transcript"],
            "language": result["language"],
            "video_id": result["video_id"],
            "auto_detected": result["auto_detected"],
            "is_generated": result["is_generated"],
            "is_translatable": result["is_translatable"],
            "session_id": result["session_id"],
            "attempt": result["attempt"],
            "request_count": result["request_count"],
            "success_rate": result["success_rate"],
            "method": "apify_style_session_pool"
        })
    else:
        status_code = 200 if result.get("skip") else 500
        return jsonify({
            "has_transcript": False,
            "error": result["error"],
            "video_id": result["video_id"],
            "skip_video": result.get("skip", False)
        }), status_code

@app.route("/session-stats", methods=["GET"])
def session_stats():
    sessions = apify_style_api.session_pool.sessions
    return jsonify({
        "total_sessions": len(sessions),
        "active_sessions": len([s for s in sessions.values() if s['usage_count'] > 0]),
        "total_requests": apify_style_api.request_count,
        "total_success": apify_style_api.success_count,
        "overall_success_rate": f"{apify_style_api.success_count/max(apify_style_api.request_count,1)*100:.1f}%",
        "sessions_detail": {
            sid[:12]: {
                "usage_count": data['usage_count'],
                "success_count": data['success_count'],
                "failure_count": data['failure_count'],
                "success_rate": f"{data['success_count']/max(data['usage_count'],1)*100:.1f}%"
            }
            for sid, data in sessions.items()
        }
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
