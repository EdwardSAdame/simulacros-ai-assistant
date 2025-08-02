from src.assistant.audio_transcriber import transcribe_audio_url

def test_transcribe_audio():
    test_url = "https://www.dropbox.com/scl/fi/7ox07d7d8u1bsil59cg7k/You-are-Absolutely-Alone.mp3?rlkey=mhbntqm0wzpngn0t99xz3ea57&st=qzihr8uq&raw=1"
    
    transcript = transcribe_audio_url(test_url)

    assert isinstance(transcript, str)
    assert len(transcript) > 0
    print("✅ Transcript:", transcript)

# This makes it executable directly:
if __name__ == "__main__":
    test_transcribe_audio()
