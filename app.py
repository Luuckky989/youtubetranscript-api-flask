from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import os

app = Flask(__name__)

@app.route("/check-transcript", methods=["GET"])
def check_transcript():
    video_id = request.args.get("video_id")
    if not video_id:
        return jsonify({"error": "Missing video_id"}), 400
    
    try:
        # 원래 코드가 맞습니다 - 인스턴스를 생성한 후 fetch 메서드 사용
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
    language = request.args.get("language", "ko")  # 기본값은 한국어
    
    if not video_id:
        return jsonify({"error": "Missing video_id"}), 400
    
    try:
        # 정적 메서드도 사용 가능하지만, 언어 지정은 다르게 작동
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[language])
        return jsonify({
            "has_transcript": True,
            "transcript": transcript,
            "language": language
        })
    except (TranscriptsDisabled, NoTranscriptFound):
        return jsonify({"has_transcript": False})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/get-available-languages", methods=["GET"])
def get_available_languages():
    video_id = request.args.get("video_id")
    
    if not video_id:
        return jsonify({"error": "Missing video_id"}), 400
    
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        languages = []
        
        for transcript in transcript_list:
            languages.append({
                "language": transcript.language,
                "language_code": transcript.language_code,
                "is_generated": transcript.is_generated,
                "is_translatable": transcript.is_translatable
            })
        
        return jsonify({
            "available_languages": languages
        })
    except (TranscriptsDisabled, NoTranscriptFound):
        return jsonify({"has_transcript": False})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
