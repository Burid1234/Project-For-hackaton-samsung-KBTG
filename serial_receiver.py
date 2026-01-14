## Python Audio Bridge & Anti-Drift Logic

ไฟล์ `serial_receiver.py` ที่ถูกออกแบบมาเพื่อจัดการความไม่เสถียรของการส่งข้อมูลผ่าน Serial Communication ความเร็วสูง (460,800 baud)

###  Key Implementation Logic

#### 1. Custom Protocol Synchronization (Anti-Drift)
เราไม่สามารถเชื่อใจได้ว่าข้อมูลจาก Serial จะมาเป็นก้อนที่สมบูรณ์ได้เสมอไป โค้ดเราชุดนี้จึงทำงานแบบ **State Machine** เพื่อค้นหาจุดเริ่มต้นของเฟรม:
```python
# Code Snippet Header Detection Logic
idx_ca = buffer.find(b'\xCA\xDB') , เรากำหนด(Logic)โปรโตคอลขึ้นมาเองเพื่อดักจับข้อมูลที่เริ่มต้นด้วย 0xCA , 0xDB จากการส่งข้อมูลที่ได้จาก {bt_app_hf.c}
จนผลสุดท้ายนั้น **เราจับข้อมูลได้แบ่งเป็น Chunk จับใส่ใน .wav เพื่อที่ว่า เราจึงสรุปได้ว่า เรานั้นสามารถจับเสียงได้มาเป็นก้อนจริงๆได้สำเร็จครับ** 
เป็นข้อสรุปได้ว่าในอนาคตเราจะสามารถใช้ VAD ในการแบ่งช่วงเสียงจาก .wav เพื่อทำเป็นรูปแบบ Real-time ได้จริง 


import serial
import wave
import time
import sys
import struct

SERIAL_PORT = "port"
BAUD_RATE = 460800 
OUTPUT_FILE = "voice_perfect(4).wav"

SAMPLE_RATE = 16000 
CHANNELS = 1
WIDTH = 2 

def main():
    ser = None
    packet_count = 0  
    frames = []       

    try:
        print(f" Connecting to {SERIAL_PORT} @ {BAUD_RATE}...")
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
        ser.dtr = False
        ser.rts = False
        
        print(" Anti-Drift Mode")
        print("1. ต่อ Bluetooth")
        print("2. โทรออกและคุยยาวๆ ได้เลย")
        print("="*50 + "\n")
        
        print(f" กำลังดูดข้อมูล (แก้เสียงซ่าอัตโนมัติ)")
        
        total_bytes = 0
        buffer = b""
        start_time = time.time()
        
        while True:
            if packet_count == 0 and (time.time() - start_time > 60):
                print("\n Timeout")
                break

            if ser.in_waiting > 0:
                chunk = ser.read(ser.in_waiting)
                buffer += chunk
                
                while True:
                 
                    idx_ca = buffer.find(b'\xCA\xDB')
                    idx_ea = buffer.find(b'\xEA\xFB')
                    
             
                    idx = -1
                    if idx_ca != -1 and idx_ea != -1: idx = min(idx_ca, idx_ea)
                    elif idx_ca != -1: idx = idx_ca
                    elif idx_ea != -1: idx = idx_ea
                    
                    if idx != -1:
                        if idx > 0:
                            payload = buffer[:idx]
                            
                           
                            if 20 <= len(payload) <= 400:
                                
                            
                                if len(payload) % 2 != 0:
                                    payload = payload[:-1] 
                                
                                frames.append(payload)
                                packet_count += 1
                                total_bytes += len(payload)
                                
                                if packet_count % 100 == 0:
                                    sys.stdout.write(f"\r Pkts: {packet_count} | Size: {total_bytes} bytes")
                                    sys.stdout.flush()
                        
        
                        buffer = buffer[idx+2:]
                    else:
                        break
                        
    except KeyboardInterrupt:
        print("\n\n หยุดบันทึก")
    except Exception as e:
        print(f"\n Error: {e}")
    finally:
        if ser and ser.is_open: ser.close()
        
    
        if packet_count > 0:
            print(f"\n บันทึกไฟล์ {OUTPUT_FILE}")
            with wave.open(OUTPUT_FILE, 'wb') as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(WIDTH)
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes(b''.join(frames))
            print(" เสร็จสิ้น! ลองฟังครับ ")
        else:
            print("\n ไม่ได้ข้อมูล")

if __name__ == "__main__":
    main()
