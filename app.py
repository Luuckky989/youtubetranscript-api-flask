from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import os

app = Flask(__name__)

@app.route("/")
def home():
    return "YouTube Transcript API is working!"

@app.route("/check-transcript", methods=["GET"])
def check_transcript():
    video_id = request.args.get("video_id")
    if not video_id:
        return jsonify({"error": "Missing video_id"}), 400
    
    try:
        # 공식 GitHub 문서에 따른 올바른 방법
        ytt_api = YouTubeTranscriptApi()
        transcript = ytt_api.fetch(video_id)
        return jsonify({
            "has_transcript": True,
            "transcript_count": len(transcript)
        })
    except (TranscriptsDisabled, NoTranscriptFound):
        return jsonify({"has_transcript": False})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/get-transcript", methods=["GET"])
def get_transcript():
    video_id = request.args.get("video_id")
    language = request.args.get("language", "en")
    
    if not video_id:
        return jsonify({"error": "Missing video_id"}), 400
    
    try:
        # 공식 GitHub 문서 방법
        ytt_api = YouTubeTranscriptApi()
        transcript_list = ytt_api.list(video_id)
        
        # 특정 언어 찾기
        transcript = transcript_list.find_transcript([language])
        
        # transcript 데이터 가져오기
        fetched_transcript = transcript.fetch()
        
        # FetchedTranscript를 dict로 변환 (to_raw_data 메서드 사용)
        transcript_data = fetched_transcript.to_raw_data()
        
        return jsonify({
            "has_transcript": True,
            "transcript": transcript_data,
            "language": transcript.language,
            "language_code": transcript.language_code,
            "is_generated": transcript.is_generated
        })
    except (TranscriptsDisabled, NoTranscriptFound):
        return jsonify({"has_transcript": False})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
