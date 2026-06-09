#include "esp_camera.h"
#include <WiFi.h>
#include <WebSocketsClient.h>

// ================= WIFI =================
const char* ssid = "Vikass";
const char* password = "vikas22543";

// ================= SERVER =================
// PC IP address running Python server
const char* server_ip = "172.16.233.26";
const uint16_t server_port = 8765;

// ================= CAMERA PINS (AI Thinker) =================
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

WebSocketsClient webSocket;

// ================= WEBSOCKET EVENTS =================
void webSocketEvent(WStype_t type, uint8_t * payload, size_t length) {

  switch(type) {

    case WStype_DISCONNECTED:
      Serial.println("❌ WebSocket Disconnected");
      break;

    case WStype_CONNECTED:
      Serial.println("✅ Connected to Python Server");
      break;

    case WStype_TEXT:
      Serial.printf("Message: %s\n", payload);
      break;

    case WStype_ERROR:
      Serial.println("⚠ WebSocket Error");
      break;

    default:
      break;
  }
}

// ================= CAMERA SETUP =================
bool initCamera() {

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

  // Quality / speed balance
  config.frame_size = FRAMESIZE_VGA;   // 320x240
  config.jpeg_quality = 12;
  config.fb_count = 2;

  if(psramFound()) {
    config.fb_location = CAMERA_FB_IN_PSRAM;
  }

  esp_err_t err = esp_camera_init(&config);

  if(err != ESP_OK) {
    Serial.printf("Camera init failed: 0x%x\n", err);
    return false;
  }

  return true;
}

// ================= SETUP =================
void setup() {

  Serial.begin(115200);

  if(!initCamera()) {
    return;
  }

  Serial.println("Connecting to WiFi...");

  WiFi.begin(ssid, password);

  while(WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nConnected!");
  Serial.print("ESP32 IP: ");
  Serial.println(WiFi.localIP());

  delay(2000);

  webSocket.begin(server_ip, server_port, "/");
  webSocket.onEvent(webSocketEvent);
  webSocket.setReconnectInterval(5000);
}

// ================= LOOP =================
void loop() {

  webSocket.loop();

  if(!webSocket.isConnected()) {
    delay(100);
    return;
  }

  camera_fb_t *fb = esp_camera_fb_get();

  if(!fb) {
    Serial.println("Frame capture failed");
    return;
  }

  // Send JPEG frame as binary
  webSocket.sendBIN(fb->buf, fb->len);

  esp_camera_fb_return(fb);

  delay(100);   // ~10 FPS
}