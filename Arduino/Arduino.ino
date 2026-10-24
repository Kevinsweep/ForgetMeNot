#include <WiFi.h>
#include <HTTPClient.h>
#include "MAX30105.h"
#include "heartRate.h"
#include <OneWire.h>
#include <DallasTemperature.h>
#include "spo2_algorithm.h"
#include "config.h"

// constants
const char* SSID = WIFI_SSID;
const char* PASSWORD = WIFI_PASS;
const char* SERVER_NAME = UPLOAD_URL;

int http_response_code;
MAX30105 sensor_hr;

// max30102 settings
// hr
const byte RATE_SIZE = 4;   // How many beats we average
byte rates[RATE_SIZE];      // Store last few valid BPM values
byte rate_spot = 0;
byte valid_beats = 0;
long last_beat = 0;
float current_BPM = 0;
int average_BPM = 0;
const float MIN_BPM = 45;
const float MAX_BPM = 180;

// spo2
#define BUFFER_SIZE 100
uint32_t ir_buffer[BUFFER_SIZE];
uint32_t red_buffer[BUFFER_SIZE];
int32_t spo2;          // Oxygen saturation value
int8_t  valid_SPO2;     // 1 = valid reading, 0 = not valid yet
int32_t heart_rate;     // Not used, but required by the function
int8_t  valid_heart_rate;

// byte led_brightness = 60;  // 0=Off to 255=50mA
// byte sample_average = 4;   // 1, 2, 4, 8, 16, 32
// byte led_mode = 2;         // 1 = Red only, 2 = Red + IR, 3 = Red + IR + Green
// byte sample_rate = 100;    // 50, 100, 200, 400, 800, 1000, 1600, 3200
// int pulse_width = 411;     // 69, 118, 215, 411
// int adc_range = 4096;      // 2048, 4096, 8192, 16384

byte led_brightness = 60;  // 0=Off to 255=50mA
byte sample_average = 4;   // 1, 2, 4, 8, 16, 32
byte led_mode = 2;         // 1 = Red only, 2 = Red + IR, 3 = Red + IR + Green
byte sample_rate = 100;    // 50, 100, 200, 400, 800, 1000, 1600, 3200
int pulse_width = 411;     // 69, 118, 215, 411
int adc_range = 4096;      // 2048, 4096, 8192, 16384

// DS18B20 settings
#define BODY_TEMP_PIN 4
OneWire oneWire(BODY_TEMP_PIN);
DallasTemperature sensor_body_temp(&oneWire);

// to send
double body_temp_to_send = 0;
int heart_rate_to_send = 0;
double spo2_to_send = 0;


const unsigned long API_interval = 10000;
const unsigned long serial_interval = 2000; 
unsigned long previous_API_millis = 0;
unsigned long previous_serial_millis = 0; 

// taskhandle
TaskHandle_t monitoring;

void setup() {
  // put your setup code here, to run once:
  Serial.begin(115200);

  // connect WIFI
  WiFi.begin(SSID, PASSWORD);
  Serial.println("Connecting");
  while(WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.print("Connected to WiFi network with IP Address: ");
  Serial.println(WiFi.localIP());

  // sensor init
  sensor_hr.begin(Wire, I2C_SPEED_FAST);
  sensor_body_temp.begin();
  
  sensor_hr.setup(led_brightness, sample_average, led_mode, sample_rate, pulse_width, adc_range);
  // use core 0 for monitoring
  xTaskCreatePinnedToCore(
    monitor_sensors,       /* Task function. */
    "monitor_sensors",     /* name of task. */
    10000,                 /* Stack size of task */
    NULL,                  /* parameter of the task */
    0,                     /* priority of the task */
    &monitoring,           /* Task handle to keep track of created task */
    0                      /* pin task to core 0 */     
  );                       
  delay(500); 
}


double read_body_temp(){
  sensor_body_temp.requestTemperatures(); 
  double temperatureC = sensor_body_temp.getTempCByIndex(0);
  return temperatureC;
}

void monitor_sensors(void * pvParameters){
  for (byte i = 0; i < 75; i++){
    while (sensor_hr.available() == false){ //do we have new data?
      sensor_hr.check();
      vTaskDelay(pdMS_TO_TICKS(2));
    }
    red_buffer[i] = sensor_hr.getRed();
    ir_buffer[i]  = sensor_hr.getIR();
    sensor_hr.nextSample();
  }

  int buffer_index = 75;

  for(;;){
    // hr
    while (sensor_hr.available() == false) {
      sensor_hr.check();
      vTaskDelay(pdMS_TO_TICKS(2));
    }
    long ir_value = sensor_hr.getIR();

    red_buffer[buffer_index] = sensor_hr.getRed();
    ir_buffer[buffer_index]  = ir_value;
    buffer_index++;

    // if (checkForBeat(ir_value)){
      long time_between_beats = millis() - last_beat;
      last_beat = millis();

      current_BPM = 60.0 / (time_between_beats / 1000.0);

      // keep realistic values
      if (current_BPM >= MIN_BPM && current_BPM <= MAX_BPM){
        rates[rate_spot] = (byte)current_BPM;
        rate_spot++;
        if (rate_spot >= RATE_SIZE){
          rate_spot = 0;
        }

        if (valid_beats < RATE_SIZE){
          valid_beats++;
        }
        
        if (valid_beats >= RATE_SIZE) {
          // Calculate the average
          average_BPM = 0;
          for (byte i = 0; i < RATE_SIZE; i++) {
            average_BPM += rates[i];
          }
          average_BPM /= RATE_SIZE;
        }
      }
    // }

    sensor_hr.nextSample();

    if (buffer_index >= BUFFER_SIZE) {
      maxim_heart_rate_and_oxygen_saturation(ir_buffer, BUFFER_SIZE, red_buffer, &spo2, &valid_SPO2, &heart_rate, &valid_heart_rate);
      
      spo2_to_send = spo2;
      heart_rate_to_send = average_BPM; 
      
      for (byte i = 0; i < 75; i++){
        red_buffer[i] = red_buffer[i + 25];
        ir_buffer[i]  = ir_buffer[i + 25];
      }

      buffer_index = 75;
    }
    body_temp_to_send = read_body_temp();

  }
}

bool value_sanity_check(double temp, int rate, double spo2){
  if(temp < -100 || rate <= 0 || spo2 <= 0){
    return false;
  }
  return true;
}

void rodok_API(){
  WiFiClient client;
  HTTPClient http;

  // Your Domain name with URL path or IP address with path
  http.begin(client, SERVER_NAME);
  http.addHeader("Content-Type", "application/json");
  char post_string[150];
  sprintf(post_string, "{\"body_temp\":%.2lf, \"heart_rate\":%d, \"spo2\":%.2lf}",body_temp_to_send, heart_rate_to_send, spo2_to_send);
  http_response_code = http.POST(post_string);
  Serial.print("HTTP Response code: ");
  Serial.println(http_response_code);
  Serial.println(post_string);
}

void loop() {
  // put your main code here, to run repeatedly:
  unsigned long current_millis = millis(); 

  // Print to serial monitor
  if (current_millis - previous_serial_millis >= serial_interval){
    previous_serial_millis = current_millis;

    Serial.println(body_temp_to_send);
    Serial.println(heart_rate_to_send);
    Serial.println(spo2_to_send);
  }

  // call API
  if (current_millis - previous_API_millis >= API_interval && value_sanity_check(body_temp_to_send, heart_rate_to_send, spo2_to_send)) {
    // 5. Save the last time you ran the code block
    previous_API_millis = current_millis; 

    rodok_API();
  }
}
