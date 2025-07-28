from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import NoTranscriptFound

app = Flask(__name__)

@app.route("/check-transcript", methods=["POST"])
def check_transcript():
    data = request.get_json()
    video_id = data.get("videoId")

    if not video_id:
        return jsonify({"error": "videoId is required"}), 400

    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=["en", "ko"])
        text = " ".join([entry["text"] for entry in transcript])
        return jsonify({"has_transcript": True, "transcript": text})
    except NoTranscriptFound:
        return jsonify({"has_transcript": False})

@app.route("/")
def home():
    return "Transcript API is running"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
