from flask import Flask, request, jsonify
from youtube_transcript_api._api import YouTubeTranscriptApi
from youtube_transcript_api import TranscriptsDisabled, NoTranscriptFound
import os

app = Flask(__name__)

@app.route("/check-transcript", methods=["GET"])
def check_transcript():
    video_id = request.args.get("video_id")
    if not video_id:
        return jsonify({"error": "Missing video_id"}), 400

    try:
        transcript = YouTubeTranscriptApi().get_transcript(video_id)
        return jsonify({"has_transcript": True})
    except (TranscriptsDisabled, NoTranscriptFound):
        return jsonify({"has_transcript": False})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
