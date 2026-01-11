##  VAD Algorithm Sandbox: `vad_logic_simulation.py`

ไฟล์นี้คือ **Proof of Concept (PoC)** สำหรับทดสอบอัลกอริทึม **Voice Activity Detection (VAD)** และระบบ **In-Memory Processing** แบบ Standalone ไว้ทำสอบก่อนการเอาใส่ไว้ในcodeจริง

เนื่องจากการทดสอบกับ Hardware จริง (ESP32) อาจมีปัจจัยภายนอกแทรกซ้อน เราจึงสร้างสคริปต์จำลองนี้ขึ้นมาเพื่อ Validate Logic 3 ส่วนสำคัญ:
1.  **Silence Filtering:** การปรับจูนค่า `webrtcvad` (Mode 3) ให้กรองเสียงลมและเสียงรบกวนได้แม่นยำที่สุด
2.  **Sentence Segmentation:** การทดสอบ Logic การตัดจบประโยคเมื่อเกิดความเงียบ (Silence Timeout) ที่ 1 วินาที
3.  **RAM-Only Handling:** การพิสูจน์การทำงานของ `io.BytesIO` ในการสร้างไฟล์เสียงเสมือนบน RAM โดยไม่ต้องบันทึกลง Hard Disk เพื่อยืนยันแนวคิด **Privacy-First Architecture**

*Note: สคริปต์นี้ใช้ไมโครโฟนของคอมพิวเตอร์ในการจำลอง Input แทนข้อมูลจาก ESP32*

import webrtcvad
import pyaudio
import sys
import io
import wave
import time

SAMPLE_RATE = 16000
CHANNELS = 1
WIDTH = 2
ESP32_CHUNK = 240

VAD_MODE = 3
VAD_FRAME_MS = 20
VAD_CHUNK_SIZE = int(SAMPLE_RATE * (VAD_FRAME_MS / 1000.0) * WIDTH)

SILENCE_DURATION_MS = 1000
SILENCE_LIMIT_FRAMES = int(SILENCE_DURATION_MS / VAD_FRAME_MS)

def send_to_typhoon_simulation(wav_data):
    print(f"\n🚀 [API MOCK] Sending {len(wav_data)} bytes to Typhoon Engine...")
    time.sleep(0.5)
    print("✅ [API MOCK] Typhoon Response: 'Fraud Intent Detected'")
    print("-" * 60)
    print("🎤 Waiting for next sentence...\n")

def main():
    vad = webrtcvad.Vad(VAD_MODE)
    p = pyaudio.PyAudio()
    
    stream = p.open(format=pyaudio.paInt16,
                    channels=CHANNELS,
                    rate=SAMPLE_RATE,
                    input=True,
                    frames_per_buffer=ESP32_CHUNK // 2)

    print("\n" + "="*60)
    print("🎙️  SYSTEM READY: Simulation Mode Active")
    print(f"⏱️  Silence Timeout: {SILENCE_DURATION_MS} ms")
    print("="*60 + "\n")

    raw_buffer = b"" 
    frames_buffer = []       
    is_recording = False     
    silence_counter = 0      

    try:
        while True:
            try:
                chunk = stream.read(ESP32_CHUNK // 2, exception_on_overflow=False)
                raw_buffer += chunk
            except:
                continue

            while len(raw_buffer) >= VAD_CHUNK_SIZE:
                current_frame = raw_buffer[:VAD_CHUNK_SIZE]
                raw_buffer = raw_buffer[VAD_CHUNK_SIZE:]

                is_speech = vad.is_speech(current_frame, SAMPLE_RATE)

                if is_speech:
                    sys.stdout.write("🟢")
                else:
                    sys.stdout.write("·")
                sys.stdout.flush()

                if is_speech:
                    if not is_recording:
                        print("\n🔴 [START] RAM Recording Triggered...")
                        is_recording = True
                    
                    frames_buffer.append(current_frame)
                    silence_counter = 0                 

                elif is_recording: 
                    frames_buffer.append(current_frame)
                    silence_counter += 1

                    if silence_counter > SILENCE_LIMIT_FRAMES:
                        print(f"\n✂️  [CUT] End of Sentence Detected ({SILENCE_DURATION_MS}ms silence)")
                        
                        ram_file = io.BytesIO()
                        
                        with wave.open(ram_file, 'wb') as wf:
                            wf.setnchannels(CHANNELS)
                            wf.setsampwidth(WIDTH)
                            wf.setframerate(SAMPLE_RATE)
                            wf.writeframes(b''.join(frames_buffer))
                        
                        ram_file.seek(0)
                        wav_data = ram_file.read() 
                        
                        hex_preview = wav_data[:16].hex().upper()
                        
                        print(f"🧐 HEX HEADER CHECK: {hex_preview}")
                        if hex_preview.startswith("52494646"):
                            print("  Header Valid (RIFF/WAVE in RAM)")
                        else:
                            print("   Header Invalid")

                        send_to_typhoon_simulation(wav_data)

                        frames_buffer = []
                        is_recording = False
                        silence_counter = 0

    except KeyboardInterrupt:
        print("\n👋 Simulation Stopped")
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

if __name__ == "__main__":
    main()
