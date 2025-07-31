from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import os

app = Flask(__name__)

@app.route("/")
def home():
    return "YouTube Transcript API is working!"

@app.route("/get-transcript", methods=["GET"])
def get_transcript():
    video_id = request.args.get("video_id")
    language = request.args.get("language", "auto")
    
    if not video_id:
        return jsonify({"error": "Missing video_id"}), 400
    
    try:
        ytt_api = YouTubeTranscriptApi()
        
        # TranscriptList 먼저 가져오기
        transcript_list = ytt_api.list(video_id)
        
        if language == "auto":
            # 자동 언어 감지: 우선순위 언어 리스트로 찾기
            languages_to_try = ['ko', 'en', 'ja', 'zh', 'zh-CN', 'es', 'fr', 'de']
            
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
            "is_translatable": transcript.is_translatable
        })
        
    except (TranscriptsDisabled, NoTranscriptFound):
        return jsonify({"has_transcript": False, "error": "No transcript available"})
    except Exception as e:
        return jsonify({"error": str(e), "has_transcript": False}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
