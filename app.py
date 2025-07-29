from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import os  # 환경변수에서 포트를 가져오기 위해 추가

app = Flask(__name__)

@app.route("/check-transcript", methods=["GET"])
def check_transcript():
    video_id = request.args.get("video_id")
    if not video_id:
        return jsonify({"error": "Missing video_id"}), 400

    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return jsonify({"has_transcript": True})
    except (TranscriptsDisabled, NoTranscriptFound):
        return jsonify({"has_transcript": False})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Railway가 주는 포트를 사용
    app.run(debug=True, host="0.0.0.0", port=port)
