#include "esp_camera.h"
#include <WiFi.h>
#include "esp_http_server.h"

// ===== WIFI =====
const char* ssid = "Teja4g";
const char* password = "Charan@2131";

// ===== AI THINKER PINS =====
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

httpd_handle_t stream_httpd = NULL;

static esp_err_t stream_handler(httpd_req_t *req){
    camera_fb_t * fb = NULL;
    esp_err_t res = ESP_OK;

    res = httpd_resp_set_type(req, "multipart/x-mixed-replace; boundary=frame");
    if(res != ESP_OK){
        return res;
    }

    while(true){
        fb = esp_camera_fb_get();
        if(!fb){
            Serial.println("Capture failed");
            continue;
        }

        httpd_resp_send_chunk(req, "--frame\r\n", strlen("--frame\r\n"));
        httpd_resp_send_chunk(req, "Content-Type: image/jpeg\r\n\r\n",
                              strlen("Content-Type: image/jpeg\r\n\r\n"));
        httpd_resp_send_chunk(req, (const char *)fb->buf, fb->len);
        httpd_resp_send_chunk(req, "\r\n", strlen("\r\n"));

        esp_camera_fb_return(fb);
    }
}

void startCameraServer(){
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    config.server_port = 80;
    config.ctrl_port = 32768;

    if (httpd_start(&stream_httpd, &config) == ESP_OK) {
    Serial.println("HTTP server started");
} else {
    Serial.println("Failed to start HTTP server");
}

    httpd_uri_t stream_uri = {
        .uri = "/stream",
        .method = HTTP_GET,
        .handler = stream_handler,
        .user_ctx = NULL
    };

    httpd_register_uri_handler(stream_httpd, &stream_uri);
}

void setup(){
    Serial.begin(115200);

    camera_config_t config;
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer = LEDC_TIMER_0;
    config.pin_d0 = Y2_GPIO_NUM;
    config.pin_d1 = Y3_GPIO_NUM;
    config.pin_d2 = Y4_GPIO_NUM;
    config.pin_d3 = Y5_GPIO_NUM;
    config.pin_d4 = Y6_GPIO_NUM;
    config.pin_d5 = Y7_GPIO_NUM;
    config.pin_d6 = Y8_GPIO_NUM;
    config.pin_d7 = Y9_GPIO_NUM;
    config.pin_xclk = XCLK_GPIO_NUM;
    config.pin_pclk = PCLK_GPIO_NUM;
    config.pin_vsync = VSYNC_GPIO_NUM;
    config.pin_href = HREF_GPIO_NUM;
    config.pin_sscb_sda = SIOD_GPIO_NUM;
    config.pin_sscb_scl = SIOC_GPIO_NUM;
    config.pin_pwdn = PWDN_GPIO_NUM;
    config.pin_reset = RESET_GPIO_NUM;

    config.xclk_freq_hz = 20000000;
    config.pixel_format = PIXFORMAT_JPEG;

    // 🔥 FAST SETTINGS
    config.frame_size = FRAMESIZE_QVGA;   // 320x240 (fast)
    config.jpeg_quality = 12;             // lower = better quality (10–20 ideal)
    config.fb_count = 2;                  // double buffer
    config.grab_mode = CAMERA_GRAB_LATEST;

    if(psramFound()){
        config.fb_location = CAMERA_FB_IN_PSRAM;
    }

    if(esp_camera_init(&config) != ESP_OK){
        Serial.println("Camera init failed");
        return;
    }

    WiFi.begin(ssid, password);
    WiFi.setSleep(false);  // 🔥 disable WiFi sleep for speed

    Serial.print("Connecting");
    while(WiFi.status() != WL_CONNECTED){
        delay(500);
        Serial.print(".");
    }

    Serial.println("\nConnected!");
    Serial.print("Stream URL: http://");
    Serial.print(WiFi.localIP());
    Serial.println(":80/stream");

    startCameraServer();
}

void loop(){
}