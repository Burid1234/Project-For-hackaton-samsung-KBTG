# Firmware: ESP32 DSP Simulation Core (`bt_app_hf.c`)

ไฟล์ของ **Hardware** ทำหน้าที่จำลองการทำงานของ **DSP (Digital Signal Processor)** บนชิปเซ็ต Samsung โดยรับผิดชอบการจัดการสัญญาณเสียงแบบ Real-time, และการลดขนาดข้อมูลและจัดข้อมูล ก่อนส่งต่อไปยัง AI Engine

## Key Implementation Details

### 1. I2S Interface Configuration (Dual-Channel)
เราตั้งค่า I2S (Inter-IC Sound) แยกอิสระ 2 ช่องทางเพื่อความเสถียรสูงสุด:
* **Microphone (RX):** ใช้ `I2S_NUM_1` รับข้อมูลขนาด **32-bit** จาก INMP441 เพื่อให้ได้ Dynamic Range กว้างที่สุดก่อนที่จะนำมาประมวลผล
* **Speaker (TX):** ใช้ `I2S_NUM_0` ส่งข้อมูลขนาด **16-bit** ไปยัง MAX98357A เพื่อเล่นเสียงสนทนาของคู่สาย

### 2. Signal Optimization via Bit-Shifting Logic
ฟังก์ชัน `bt_app_hf_client_outgoing_cb` คือจุดที่เกิดการ Optimization สัญญาณเสียง:
```c
// Code Snippet: 32-bit to 16-bit Downsampling & Noise Reduction
for (int i = 0; i < samples_to_read; i++) {
    // Shift ขวา 14 บิต เพื่อลดขนาดข้อมูลและตัด Noise Floor ทิ้ง
    output_buffer[i] = (int16_t)(raw_buffer[i] >> 14); 
}

#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>
#include "esp_log.h"

#include "bt_app_core.h"
#include "bt_app_hf.h"
#include "esp_bt_main.h"
#include "esp_bt_device.h"
#include "esp_gap_bt_api.h"
#include "esp_hf_client_api.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "freertos/semphr.h"
#include "freertos/ringbuf.h"
#include "time.h"
#include "sys/time.h"
#include "sdkconfig.h"
#include "driver/uart.h" 
#include "driver/i2s.h" 

#define ESP_HFP_RINGBUF_SIZE (10 * 1024) 
#define ZENSEC_UART_PORT UART_NUM_0
#define ZENSEC_BAUD_RATE 460800 

#define I2S_SPK_NUM     I2S_NUM_0
#define I2S_SPK_BCK     26
#define I2S_SPK_WS      25
#define I2S_SPK_DO      27

#define I2S_MIC_NUM     I2S_NUM_1  
#define I2S_MIC_BCK     14
#define I2S_MIC_WS      13  
#define I2S_MIC_DI      32

static TaskHandle_t s_bt_app_send_task_hdl = NULL;
static RingbufHandle_t m_rb = NULL;

extern esp_bd_addr_t peer_addr;

void zensec_i2s_init(void) {
    i2s_config_t spk_config = {
        .mode = I2S_MODE_MASTER | I2S_MODE_TX, 
        .sample_rate = 16000,
        .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
        .channel_format = I2S_CHANNEL_FMT_ONLY_RIGHT, 
        .communication_format = I2S_COMM_FORMAT_STAND_I2S,
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count = 8,
        .dma_buf_len = 64,
        .use_apll = false,
        .tx_desc_auto_clear = true
    };
    i2s_pin_config_t spk_pin_config = {
        .bck_io_num = I2S_SPK_BCK,
        .ws_io_num = I2S_SPK_WS,
        .data_out_num = I2S_SPK_DO,
        .data_in_num = -1                                                       
    };
    i2s_driver_install(I2S_SPK_NUM, &spk_config, 0, NULL);
    i2s_set_pin(I2S_SPK_NUM, &spk_pin_config);
    i2s_zero_dma_buffer(I2S_SPK_NUM);

    i2s_config_t mic_config = {
        .mode = I2S_MODE_MASTER | I2S_MODE_RX, 
        .sample_rate = 16000,
        .bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT, 
        .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT, 
        .communication_format = I2S_COMM_FORMAT_STAND_I2S,
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count = 8,
        .dma_buf_len = 64,
        .use_apll = false,
    };
    i2s_pin_config_t mic_pin_config = {
        .bck_io_num = I2S_MIC_BCK,
        .ws_io_num = I2S_MIC_WS,
        .data_out_num = -1,
        .data_in_num = I2S_MIC_DI
    };
    i2s_driver_install(I2S_MIC_NUM, &mic_config, 0, NULL);
    i2s_set_pin(I2S_MIC_NUM, &mic_pin_config);
}

void zensec_i2s_deinit(void) {
    i2s_driver_uninstall(I2S_SPK_NUM);
    i2s_driver_uninstall(I2S_MIC_NUM);
}

#if CONFIG_BT_HFP_AUDIO_DATA_PATH_HCI

static void bt_app_send_task(void *arg)
{
    size_t item_size = 0;
    uint8_t *data = NULL;
    
    uart_config_t uart_config = {
        .baud_rate = ZENSEC_BAUD_RATE,
        .data_bits = UART_DATA_8_BITS,
        .parity    = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE
    };
    uart_param_config(ZENSEC_UART_PORT, &uart_config);

    while (1) {
        data = (uint8_t *)xRingbufferReceive(m_rb, &item_size, pdMS_TO_TICKS(10));
        
        if (data != NULL) {
            uint8_t header[2] = {0xCA, 0xDB}; 
            uart_write_bytes(ZENSEC_UART_PORT, (const char*)header, 2);
            uart_write_bytes(ZENSEC_UART_PORT, (const char*)data, item_size);
            vRingbufferReturnItem(m_rb, (void *)data);
        }
    }
}

static void bt_app_hf_client_audio_open(void)
{
    if (m_rb == NULL) {
        m_rb = xRingbufferCreate(ESP_HFP_RINGBUF_SIZE, RINGBUF_TYPE_BYTEBUF);
    }
    if (s_bt_app_send_task_hdl == NULL) {
        xTaskCreate(bt_app_send_task, "bt_app_send_task", 2048, NULL, configMAX_PRIORITIES - 3, &s_bt_app_send_task_hdl);
    }
    zensec_i2s_init();
}

static void bt_app_hf_client_audio_close(void)
{
    if (s_bt_app_send_task_hdl != NULL) {
        vTaskDelete(s_bt_app_send_task_hdl);
        s_bt_app_send_task_hdl = NULL;
    }
    if (m_rb != NULL) {
        vRingbufferDelete(m_rb);
        m_rb = NULL;
    }
    zensec_i2s_deinit(); 
}

static uint32_t bt_app_hf_client_outgoing_cb(uint8_t *p_buf, uint32_t sz)
{
    size_t samples_to_read = sz / 2;
    size_t bytes_read = 0;
    
    int32_t raw_buffer[samples_to_read]; 
    
    i2s_read(I2S_MIC_NUM, raw_buffer, samples_to_read * 4, &bytes_read, 0);
    
    int16_t *output_buffer = (int16_t *)p_buf; 
    
    for (int i = 0; i < samples_to_read; i++) {
        output_buffer[i] = (int16_t)(raw_buffer[i] >> 14); 
    }
    

    return sz;
}

static void bt_app_hf_client_incoming_cb(const uint8_t *buf, uint32_t sz)
{
    if (m_rb) {
        xRingbufferSend(m_rb, (uint8_t *)buf, sz, 0);
    }
    size_t bytes_written = 0;
    i2s_write(I2S_SPK_NUM, buf, sz, &bytes_written, portMAX_DELAY);
    esp_hf_client_outgoing_data_ready();
}
#endif

void bt_app_hf_client_cb(esp_hf_client_cb_event_t event, esp_hf_client_cb_param_t *param)
{
    switch (event) {
        case ESP_HF_CLIENT_CONNECTION_STATE_EVT:
            memcpy(peer_addr,param->conn_stat.remote_bda,ESP_BD_ADDR_LEN);
            break;

        case ESP_HF_CLIENT_AUDIO_STATE_EVT:
            #if CONFIG_BT_HFP_AUDIO_DATA_PATH_HCI
            if (param->audio_stat.state == ESP_HF_CLIENT_AUDIO_STATE_CONNECTED ||
                param->audio_stat.state == ESP_HF_CLIENT_AUDIO_STATE_CONNECTED_MSBC) {
                esp_hf_client_register_data_callback(bt_app_hf_client_incoming_cb, bt_app_hf_client_outgoing_cb);
                bt_app_hf_client_audio_open();
            } else if (param->audio_stat.state == ESP_HF_CLIENT_AUDIO_STATE_DISCONNECTED) {
                bt_app_hf_client_audio_close();
            }
            #endif
            break;
        default:
            break;
    }
}
