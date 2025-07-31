from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import os

app = Flask(__name__)

@app.route("/")
def home():
    return "YouTube Transcript API is working!"

@app.route("/check-transcript", methods=["GET"])
def check_transcript():
    """자막 유무만 빠르게 체크"""
    video_id = request.args.get("video_id")
    
    if not video_id:
        return jsonify({"error": "Missing video_id"}), 400
    
    try:
        ytt_api = YouTubeTranscriptApi()
        transcript_list = ytt_api.list(video_id)
        
        available_languages = []
        for transcript in transcript_list:
            available_languages.append({
                "language": transcript.language,
                "language_code": transcript.language_code,
                "is_generated": transcript.is_generated,
                "is_translatable": transcript.is_translatable
            })
        
        return jsonify({
            "has_transcript": True,
            "video_id": video_id,
            "available_languages": available_languages,
            "count": len(available_languages)
        })
        
    except (TranscriptsDisabled, NoTranscriptFound):
        return jsonify({
            "has_transcript": False,
            "video_id": video_id,
            "available_languages": []
        })
    except Exception as e:
        return jsonify({
            "has_transcript": False,
            "video_id": video_id,
            "error": str(e)
        })

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
            # 자동 언어 감지: 우선순위 언어 리스트로 찾기 (이슬람 국가 언어 포함)
            languages_to_try = [
                'ko', 'en', 'ja', 'zh', 'zh-CN',  # 주요 동아시아 언어
                'ar', 'ar-SA', 'ar-EG', 'ar-AE', 'ar-JO', 'ar-LB',  # 아랍어 방언
                'ms', 'id',  # 말레이시아어, 인도네시아어
                'ur', 'hi',  # 우르두어(파키스탄), 힌디어(인도)
                'tr',  # 터키어
                'fa',  # 페르시아어(이란)
                'bn',  # 벵골어(방글라데시)
                'es', 'fr', 'de'  # 기타 주요 언어
            ]
            
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

@app.route("/bulk-check", methods=["POST"])
def bulk_check_transcripts():
    """여러 비디오 ID를 한 번에 체크"""
    video_ids = request.json.get("video_ids", [])
    
    if not video_ids:
        return jsonify({"error": "Missing video_ids"}), 400
    
    results = []
    ytt_api = YouTubeTranscriptApi()
    
    for video_id in video_ids:
        try:
            transcript_list = ytt_api.list(video_id)
            available_count = len(list(transcript_list))
            
            results.append({
                "video_id": video_id,
                "has_transcript": True,
                "language_count": available_count
            })
        except:
            results.append({
                "video_id": video_id,
                "has_transcript": False,
                "language_count": 0
            })
    
    # 자막이 있는 비디오와 없는 비디오 분리
    with_transcript = [r for r in results if r["has_transcript"]]
    without_transcript = [r for r in results if not r["has_transcript"]]
    
    return jsonify({
        "total_checked": len(video_ids),
        "with_transcript": len(with_transcript),
        "without_transcript": len(without_transcript),
        "results": results,
        "success_rate": f"{len(with_transcript)/len(video_ids)*100:.1f}%"
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
