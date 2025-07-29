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
    language = request.args.get("language", "en")
    
    if not video_id:
        return jsonify({"error": "Missing video_id"}), 400
    
    try:
        # 가장 간단한 방법 - 인스턴스만 생성하고 fetch만 사용
        ytt_api = YouTubeTranscriptApi()
        
        # 언어 지정하여 fetch
        transcript = ytt_api.fetch(video_id, languages=[language])
        
        # FetchedTranscript 객체를 raw data로 변환
        if hasattr(transcript, 'to_raw_data'):
            transcript_data = transcript.to_raw_data()
        else:
            # 만약 to_raw_data가 없다면 직접 변환
            transcript_data = []
            for snippet in transcript:
                transcript_data.append({
                    "text": snippet.text,
                    "start": snippet.start,
                    "duration": snippet.duration
                })
        
        return jsonify({
            "has_transcript": True,
            "transcript": transcript_data,
            "language": language,
            "video_id": video_id
        })
        
    except (TranscriptsDisabled, NoTranscriptFound):
        return jsonify({"has_transcript": False, "error": "No transcript available"})
    except Exception as e:
        return jsonify({"error": str(e), "has_transcript": False}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
