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
        # 원래 코드가 맞습니다 - 공식 문서 방식
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
    language = request.args.get("language", "en")  # 기본값은 영어
    
    if not video_id:
        return jsonify({"error": "Missing video_id"}), 400
    
    try:
        # 공식 문서 방식: 인스턴스 생성 후 fetch
        ytt_api = YouTubeTranscriptApi()
        transcript = ytt_api.fetch(video_id, languages=[language])
        return jsonify({
            "has_transcript": True,
            "transcript": transcript,
            "language": language
        })
    except (TranscriptsDisabled, NoTranscriptFound):
        return jsonify({"has_transcript": False})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
