# VAULTSEC-For-hackaton-samsung-KBTG
การนำเสนอความคืบหน้าของผลงงานและการพัฒนาของทีมเราในการสร้างโปรเจคในครั้งนี้

# VAULTSEC On-Device AI Fraud Prevention Chipset Architecture

> **Solution for Samsung x KBTG Digital Fraud Cybersecurity Hackathon **

**นวัตกรรมสถาปัตยกรรมจำลองชิป AI ป้องกัน ที่ถูกออกแบบมาเพื่อดักจับและสกัดกั้นเหล่าแก๊งคอลเซ็นเตอร์แบบ **Real-time** โดยจำลองการทำงานภายในชิปสมาร์ทโฟน Samsung เพื่อปิดช่องโหว่ ตั้งแต่วินาทีแรกที่ตรวขเจอเบอร์ใหม่ ที่ระบบฐานข้อมูลแบบเดิมตรวจจับไม่ทัน


## องค์ประกอบหลักในการออกแบบ

###  Low-Power DSP Simulation 
เราออกแบบส่วนรับสัญญาณโดยจำลองการทำงานของ DSP (Digital Signal Processor) บนชิปมือถือด้วยบอร์ด ESP32
**Real-time Bluetooth Sniffing** ใช้โปรโตคอล HFP (Hands-Free Profile) ในการดักจับข้อมูล เสียงสนทนาสดๆ (Synchronous Connection Oriented - SCO) จากต้นทาง โดยทำงานแบบ Pass-through ที่ไม่รบกวนคุณภาพสัญญาณหรือการทำงานของโทรศัพท์

**Robust Ring Buffer Implementation** แก้ปัญหา Jitter (ความไม่สม่ำเสมอของข้อมูล) และ Packet Loss ที่เกิดจากการส่งผ่าน Bluetooth ด้วยการใช้โครงสร้างข้อมูลแบบ Circular Buffer (Ring Buffer) ขนาด 10KB เพื่อพักข้อมูล (Buffer) ให้กระแสเสียงมีความต่อเนื่องและเสถียรก่อนส่งผ่าน UART

**Bit-Depth Optimization & Noise Floor Reduction** ทำการ Bit-Shifting (>> 14) ข้อมูลดิบจากไมค์ I2S (ซึ่งเป็น 32-bit) ให้เหลือ 16-bit เพื่อให้ตรงกับมาตรฐาน PCM Audio ของ Bluetooth วิธีนี้ช่วยลดขนาด Packet ข้อมูลลง 50% (Data Compression) และเป็นการตัดสัญญาณรบกวน (Noise Floor) ในระดับ Hardware ไปในตัว

**Custom Packet Framing Protocol** เราออกแบบโปรโตคอลการส่งข้อมูลเฉพาะตัว โดยการแทรก Header Bytes (0xCA 0xDB) นำหน้าทุกชุดข้อมูล (Chunk) เพื่อป้องกันปัญหา Data Drift หรือการเลื่อนของเฟรมข้อมูล ทำให้ฝั่ง AI สามารถ Reconstruct ไฟล์เสียงกลับมาได้อย่างแม่นยำ 100% แม้ในการส่งข้อมูลความเร็วสูง

**High-Speed UART Bridge** ใช้การส่งข้อมูลผ่าน UART ที่ Baud Rate 460,800 bps ซึ่งสูงกว่ามาตรฐานทั่วไป เพื่อลดค่าความหน่วง (Latency) ให้ต่ำที่สุดในระดับ Millisecond


###  AI 
ส่วนสมองกล (NPU Simulation) เราเปลี่ยนวิธีคิดจากการตรวจจับแบบ "Matching" (ตรงกันหรือไม่) มาเป็นการตรวจจับแบบ "Cognitive Analysis" (การคิดวิเคราะห์) โดยใช้ Typhoon (Thai LLM) ผสานกับ Pre-processing Logic:

**Intelligent Gatekeeper (VAD Logic)** ก่อนเริ่มการวิเคราะห์ เราใช้อัลกอริทึม Voice Activity Detection (VAD) ที่ทำงานบน Local Machine เพื่อคัดกรอง "ความเงียบ" และ "เสียงรบกวน" (Noise) ออกจากเสียงพูดจริง ช่วยลดภาระการประมวลผลของ AI และประหยัดพลังงาน

**Intent Recognition over Identity** ระบบจะไม่สนใจว่า "ใครโทรมา" (Identity) แต่จะสนใจว่า "เขาต้องการอะไร" (Intent) โดยใช้ AI ถอดรหัสบริบทภาษาไทยที่ซับซ้อน เช่น ประโยคข่มขู่, การสร้างสถานการณ์ฉุกเฉิน, หรือแพทเทิร์นการหลอกถามข้อมูลส่วนตัว (Social Engineering)

**Thai Linguistic Nuance Analysis** โมเดลถูกปรับจูนให้เข้าใจ "บริบทภาษาไทยฉบับโจร" โดยเฉพาะ เช่น การใช้คำราชาศัพท์ที่คนไทยชอบใช้กัน, หรือสแลงที่แก๊งคอลเซ็นเตอร์มักใช้ ซึ่งโมเดลต่างประเทศมักตรวจจับไม่ได้

**Zero-Day Threat Defense** ด้วยการวิเคราะห์ที่ตัว เนื้อหา ทำให้ระบบสามารถตรวจจับมิจฉาชีพที่ใช้ Sim Card เปิดใหม่หรือเป็นเบอร์ที่ไม่ได้อยู่ในรายการตรวจสอบ ได้ทันทีในวินาทีแรกที่เริ่มบทสนทนาหลอกลวง โดยไม่ต้องรอให้มีประวัติใน Blacklist Database


### Privacy-First 
เราให้ความสำคัญสูงสุดกับความปลอดภัยของข้อมูล (Data Privacy) โดยออกแบบระบบภายใต้หลักการ Privacy-by-Design เพื่อสร้าง Digital Trust

**Ephemeral In-Memory Processing**  กระบวนการวิเคราะห์เสียงทั้งหมดเกิดขึ้นบน Volatile Memory (RAM) ผ่าน Virtual File Object (เราสร้างขึ้นมา) เท่านั้น ข้อมูลเสียงจะถูกสร้างขึ้นมาเพียงเสี้ยววินาทีเพื่อประมวลผล

**Automatic Garbage Collection**  ทันทีที่ AI ประมวลผลเสร็จสิ้น ระบบจะทำการ "ทำลายตัวเองทันที" (Instant Purge) ผ่านกลไก Memory Garbage Collection ทำให้ข้อมูลหายไปจากระบบอย่างสมบูรณ์

**Zero-Persistence Guarantee** เราการันตีว่าไม่มีร่องรอยทางดิจิทัล (Digital Footprint) หลงเหลือให้กู้คืนได้ (Forensic-proof) สอดคล้องกับมาตรฐาน PDPA อย่างเคร่งครัด ผู้ใช้งานจึงมั่นใจได้ว่าบทสนทนาส่วนตัวจะไม่มีวันรั่วไหล 


## Full Tech Stack (เทคโนโลยีที่ใช้ทั้งหมด)

| Category | Technology | Role |

| **Hardware Core** | **ESP32-WROVER** | จำลอง DSP สำหรับจัดการ Bluetooth และ Audio Buffer |
| **Audio Interface** | INMP441 (Mic) / MAX98357A (Speaker) | รับ-ส่งสัญญาณเสียงดิจิทัลผ่านพอร์ต I2S |
| **Firmware OS** | **FreeRTOS (ESP-IDF)** | จัดการ Real-time Tasks และระบบ Ring Buffer |
| **Connectivity** | Bluetooth HFP / UART (460.8 kbps) | เชื่อมต่อสัญญาณเสียงความเร็วสูง (Low Latency Stream) |
| **AI Processing** | **Python / WebRTC VAD** | กรองเสียงเงียบและตัดเสียงรบกวน (Pre-processing) |
| **LLM Model** | **Typhoon (Thai LLM)** | วิเคราะห์บริบทและเจตนาของมิจฉาชีพ (Intent Analysis) |
| **Privacy Tech** |  (In-Memory) | ประมวลผลบน RAM และลบทำลายทันที (No Disk Write) |
| **Backend (Mock)** | Python FastAPI / Flask | จำลอง Server ธนาคาร (KBTG API) สำหรับคำสั่ง Soft Lock |
| **Database** | SQLite / JSON (Mock) | จำลองฐานข้อมูล Samsung Hiya และบัญชีม้า (Mule Hunter) |
| **Notification** | **LINE Messaging API** | แจ้งเตือนภัยและรับ Feedback จากผู้ใช้ (Community Shield) |

##  Roadmap & Future Integration

- [x] **Phase 1: Hardware Interception** (Complete) - รับส่งเสียงผ่าน Bluetooth และจัดการ Buffer ได้สมบูรณ์
- [x] **Phase 2: VAD & Privacy Engine** (Complete) - ตัดเสียงเงียบและจัดการข้อมูลใน RAM (**ขั้นตอนที่ถึงในปัจจุบัน**)
- [ ] **Phase 3: Typhoon LLM Integration** (In Progress) - เชื่อมต่อ API โมเดลภาษาไทย
- [ ] **Phase 4: Banking Ecosystem** (Planned) - เชื่อมต่อ KBTG API สำหรับฟีเจอร์ Soft Lock
- [ ] **Phase 5: On-Device Porting** (Ultimate Goal) - ย้าย Logic ทั้งหมดลงชิป NPU ของ Samsung จริง (**ในอนาคต**)






