from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import os  # Railway 환경에서 포트 가져오기 위해

app = Flask(__name__)

@app.route("/check-transcript", methods=["GET"])
def check_transcript():
    video_id = request.args.get("video_id")
    if not video_id:
        return jsonify({"error": "Missing video_id"}), 400

    try:
        # ✅ youtube-transcript-api 버전 0.4.5 기준
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return jsonify({"has_transcript": True})
    except (TranscriptsDisabled, NoTranscriptFound):
        return jsonify({"has_transcript": False})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # ✅ Railway의 환경변수 PORT 사용, 없으면 5000 기본값
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
