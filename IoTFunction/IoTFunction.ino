#include <Servo.h>
#define BLINKER_WIFI
#include <Blinker.h>
#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>

//needed for library   
#include <DNSServer.h>
#include <ESP8266WebServer.h>
#include <CustomWiFiManager.h>        
#include <NTPClient.h>
#include <WiFiUdp.h>

char auth[] = "xxx";   // 填入自己blinker app 的密匙
char ssid[] = "xxx";   // 填入wifi名称
char pswd[] = "xxx";   // 填入密码

//  心知天气服务器地址和端口
const char* host = "api.seniverse.com";     // 将要连接的服务器地址  
const int httpPort = 80;                    // 将要连接的服务器端口      
 
// 心知天气HTTP请求所需信息
String reqUserKey = "xxx";   // 私钥(填入你的心知天气的私钥)
String reqLocation = "xxx";            // 城市(填入需要的城市)
String reqUnit = "c";                      // 摄氏/华氏


// -------- 控制面板按键 -----------
BlinkerButton Button1("mode_switch");    //模式切换
BlinkerButton Button2("getFore");     //预报
BlinkerButton Button3("weather");    //天气
BlinkerButton Button4("time");        //获取时间
BlinkerButton Button5("btn1_k");    //舵机1的开
BlinkerButton Button6("btn1_g");    //舵机1的关


//------- 控制面板的数值和文字 ---------
BlinkerNumber body_temperature("body_temp");
BlinkerNumber person_name("name"); 
BlinkerNumber wea_temp("wea_t");
BlinkerText weather_("wea");

//舵机1
Servo myservo1;//定义（创建）一个舵机名称为myservo1

//ntp客户端
WiFiUDP ntpUDP;
NTPClient timeClient(ntpUDP, "ntp2.aliyun.com");


//---------- 控制面板的信息和预报天气---------------
int person_code = -1;
float body_t = 0.0;
String cur_weather;
int wea_temperature = -1;

int high = 0;
int low = 0;
String rainfall;//降水量mm
String precip;//降水概率
int humidity = 0;


//-------------------------产生http请求并解析返回的数据--------------------------------
String reqRes_1 = "/v3/weather/now.json?key=" + reqUserKey +
                  + "&location=" + reqLocation + 
                  "&language=en&unit=" +reqUnit;
String reqRes_2 = "/v3/weather/daily.json?key=" + reqUserKey +
                  + "&location=" + reqLocation + "&language=en&unit=" +
                  reqUnit + "&start=0&days=1";

int httpRequest(String reqRes, int type_wea){
    WiFiClient client;
    int flag = 1;
    // 建立http请求信息
    String httpRequest = String("GET ") + reqRes + " HTTP/1.1\r\n" + 
                                "Host: " + host + "\r\n" + 
                                "Connection: close\r\n\r\n";
    //  Serial.println(""); 
    //  Serial.print("Connecting to "); Serial.print(host);
 
    // 尝试连接服务器
    if (client.connect(host, 80)){
    //Serial.println(" Success!");
 
    // 向服务器发送http请求信息
        client.print(httpRequest);
        //    Serial.println("Sending request: ");
        //    Serial.println(httpRequest);  
 
        // 获取并显示服务器响应状态行 
        String status_response = client.readStringUntil('\n');
        //Serial.print("status_response: ");
        //Serial.println(status_response);
 
    // 使用find跳过HTTP响应头
        if (client.find("\r\n\r\n")) {
            //Serial.println("Found Header End. Start Parsing.");
        }
    
    // 利用ArduinoJson库解析心知天气响应信息
    parseInfo(client, type_wea); 
    } 
    else {
        flag == 0;
    //Serial.println(" connection failed!");
    }   
  //断开客户端与服务器连接工作
    client.stop(); 
    return flag;
}


void parseInfo(WiFiClient client, int type_wea){
    if(type_wea == 1) {
        const size_t capacity = JSON_ARRAY_SIZE(1) + JSON_OBJECT_SIZE(1) + 2*JSON_OBJECT_SIZE(3) + JSON_OBJECT_SIZE(6) + 230;
        DynamicJsonDocument doc(capacity);
        deserializeJson(doc, client);
        JsonObject results_0 = doc["results"][0];
        JsonObject results_0_now = results_0["now"];
  
        cur_weather = results_0_now["text"].as<String>();
        wea_temperature = results_0_now["temperature"].as<int>(); 
    }
    else {
        const size_t capacity = JSON_ARRAY_SIZE(1) + JSON_ARRAY_SIZE(3) + JSON_OBJECT_SIZE(1) + JSON_OBJECT_SIZE(3) + JSON_OBJECT_SIZE(6) + 3*JSON_OBJECT_SIZE(14) + 860;
        DynamicJsonDocument doc(capacity);
        deserializeJson(doc, client);
        JsonObject results_0 = doc["results"][0];
        JsonArray results_0_daily = results_0["daily"];
        JsonObject results_0_daily_0 = results_0_daily[0];
        high = results_0_daily_0["high"].as<int>(); 
        low = results_0_daily_0["low"].as<int>(); 
        rainfall = results_0_daily_0["rainfall"].as<String>();
        precip = results_0_daily_0["precip"].as<String>(); 
        humidity = results_0_daily_0["humidity"].as<int>();
    }

}

//--------------------获取天气和预报信息-------------------------
void getWea() {
    if(httpRequest(reqRes_1, 1) == 1) {
        delay(200);
        wea_temp.print(wea_temperature);
        weather_.print(cur_weather);
        Serial.print("weaaa-");
        Serial.print(cur_weather);
        Serial.print('-');
        Serial.print(wea_temperature);

        delay(200);
        Serial.write('\n');
    }
}

void getFore() {
    if(httpRequest(reqRes_2, 0) == 1) {
        delay(200);
        //发送UART信息
        Serial.print("Foreaa ");
        Serial.print(high);
        Serial.print(' ');
        Serial.print(low);
        Serial.print(' ');
        Serial.print(rainfall);
        Serial.print(' ');
        Serial.print(precip);
        Serial.print(' ');
        Serial.print(humidity);

        delay(200);
        Serial.write('\n');
   }
}

//-------------------------获取网络时间--------------------------------
//HTTPClient http;
//String GetUrl = "http://quan.suning.com/getSysTime.do";

void getTime() {
//    http.begin(GetUrl);
//    int httpCode = http.GET();
//        if (httpCode == HTTP_CODE_OK) {
//            //读取响应内容
//            String response = http.getString();
//            delay(200);
//            Serial.println(response);
//            delay(200); 
//            Blinker.print(response.substring(13, 23));
//            Blinker.print(response.substring(24, 32));
//        }
//    http.end();
    timeClient.update();
    time_t epochTime = timeClient.getEpochTime();
    String formattedTime = timeClient.getFormattedTime();
    //Get a time structure
    struct tm *ptm = gmtime ((time_t *)&epochTime); 
    int monthDay = ptm->tm_mday;
    int currentMonth = ptm->tm_mon + 1;
    int currentYear = ptm->tm_year + 1900;
      
    //Print complete date:
    String currentDate = String(currentYear) + "-" + String(currentMonth) + "-" + String(monthDay);
    String dateAndTime = currentDate + " " + formattedTime;
    Serial.print("Time ");
    Serial.print(dateAndTime);//发送UART信息
    delay(200);
    Serial.println("");
    
}


/*
struct tm {
int tm_sec; // 秒，取值0~59；
int tm_min; // 分，取值0~59；
int tm_hour; // 时，取值0~23；
int tm_mday; // 月中的日期，取值1~31；
int tm_mon; // 月，取值0~11；
int tm_year; // 年，其值等于实际年份减去1900；
int tm_wday; // 星期，取值0~6，0为周日，1为周一，依此类推；
int tm_yday; // 年中的日期，取值0~365，0代表1月1日，1代表1月2日，依此类推；
int tm_isdst; // 夏令时标识符，实行夏令时的时候，tm_isdst为正；不实行夏令时的进候，tm_isdst为0；不了解情况时，tm_isdst()为负
};
https://blog.csdn.net/Naisu_kun/article/details/115627629

*/


// ----------------------app 端按下按键即会执行该函数 回调函数-------------------------------
//void button1_callback(const String & state) {
//   BLINKER_LOG("get button state: ", state);//读取按键状态
//   Serial.println("button1, btn1_k");
//   myservo1.write(ser_max1);  //写入滑块1 的角度   这个角度大小可以通过滑块1 来设置
//   Blinker.vibrate();  //使手机震动
//   Blinker.delay(1000);//这个delay 一定要有  不然舵机转不过来 
//   myservo1.write(ser_mid1);  //15s后恢复到滑块3设置的角度  ，因为既然控制开关了   就必须考虑到我们用手按的时候   舵机不能挨着开关呀
//   Blinker.vibrate();  //使手机震动
//
//}
void button1_callback(const String & state) {
    BLINKER_LOG("get button state: ", state);//这个和上面的一样
        if (state=="on") {
            Serial.write('1');//发送UART信息
            delay(600);
        
            Serial.println("Detect Mode");
            Button1.color("#0099ff");
            Blinker.vibrate(); 
            Blinker.delay(1000);
            Blinker.vibrate();  //使手机震动
            Button1.print("on");// 反馈开关状态
        } 
        else if(state=="off") {
            Serial.write('2');
            delay(600);
    
            Button1.color("#cccccc");
            Serial.println("Sleep Mode");
            Blinker.vibrate(); 
            Blinker.delay(1000);
            Blinker.vibrate();  //使手机震动
            Button1.print("off");  // 反馈开关状态
            
        }

}
void button2_callback(const String & state) {
    BLINKER_LOG("get button state: ", state);//这个和上面的一样
    Blinker.print("get Forecast");//这个和上面的一样
    getFore();
    
    Blinker.vibrate(); 
    Blinker.delay(1000);
    Blinker.vibrate();  //使手机震动
}

void button3_callback(const String & state) {
    BLINKER_LOG("get button state: ", state);//这个和上面的一样
    Blinker.print("get Weather");//这个和上面的一样
    getWea();
    wea_temp.print(wea_temperature);
    weather_.print(cur_weather);
    Blinker.vibrate(); 
    Blinker.delay(1000);
    Blinker.vibrate();  //使手机震动
}
void button4_callback(const String & state) {
    BLINKER_LOG("get button state: ", state);//这个和上面的一样
    Blinker.print("get date and time");//这个和上面的一样
    getTime();

    Blinker.vibrate(); 
    Blinker.delay(1000);
    Blinker.vibrate();  //使手机震动
}


void button5_callback(const String & state) {
    BLINKER_LOG("get button state: ", state);//这个和上面的一样
    myservo1.write(0);
    Blinker.print("servo opened");
}
void button6_callback(const String & state) {
    BLINKER_LOG("get button state: ", state);//这个和上面的一样
    myservo1.write(90);
    Blinker.print("servo closed");
}

int count = 0;
void heartbeat() {//每隔10个心跳包就自动更新时间和天气
    count += 1;
    if(count >= 10) {
        count = 0; 
        Blinker.print("get weather");//这个和上面的一样
        getWea();
        delay(500);
        Blinker.print("get fore");//这个和上面的一样
        getFore();
        delay(500);
        Blinker.print("get date and time");
        getTime();
        delay(500);
    }
}

//-------------------------------------------------------------------------------------------------------------------------
void setup() {

// 初始化串口，并开启调试信息

    Serial.begin(115200);
  
    //自动配网，就是生成一个ap，手机连接后配网
    WiFiManager wifiManager;//自动配网
    wifiManager.autoConnect("AutoConnectAP");
    Serial.println("connected...yeey :)");

    //http.setTimeout(5000);
    // 初始化有LED的IO
    pinMode(LED_BUILTIN, OUTPUT);  //LED_BUILTIN 宏就是开发板指示灯的io口
    digitalWrite(LED_BUILTIN, HIGH);

    // 初始化blinker

    Blinker.begin(auth, ssid, pswd);

    Button1.attach(button1_callback); //绑定按键执行回调函数
    Button2.attach(button2_callback);
    Button3.attach(button3_callback);
    Button4.attach(button4_callback);
    //Button7.attach(button7_callback);
    Button5.attach(button5_callback);
    Button6.attach(button6_callback);
    Blinker.attachHeartbeat(heartbeat);

    timeClient.begin();//开启NTP服务器
    timeClient.setTimeOffset(28800);//GMT +8

    myservo1.attach(16); //esp8266的GIPIO16  对应NODEmcu 的D0 
    myservo1.write(90);

    getWea();
    delay(500);
    getFore();
    delay(500);
    getTime();
    delay(500);
}

//-----------------------------------------------------------------------------------------------------------

void loop() {

    digitalWrite(LED_BUILTIN, HIGH);
    Blinker.run();  //*每次运行都会将设备收到的数据进行一次解析。
    digitalWrite(LED_BUILTIN, LOW);//                在使用WiFi接入时，该语句也负责保持网络连接*/
    int ch = -1;
    int i = 0, flag = 0;
    char s[20];
    ch = Serial.read();
    
    //这以下是解析接收的UART数据
    while(ch != -1) {
        if(ch == 112 || ch == 116)//读取person1T36.5，就是识别结果，p的ascii为112，存到字符数组中就可以分开看人称代号和温度结果
            flag = 1;
        Serial.write(ch);
        if(flag == 1)
            s[i++] = (char)ch;
        ch = Serial.read();
    }
    s[i] = '\0';
    
    if(i != 0) {
      Serial.print('\n');
      Serial.println(s);
    }
    int k = 0;    
    if(flag == 1 && s[0] == 'p') {
        for(k = 0; k < strlen(s); k++){
            if(s[k] == 'n') {
            int sum = 0;
            for(int j = k + 1; s[j] <= '9' && s[j] >= '0'; j++)
                sum = sum * 10 + s[j] - '0';
            person_code = sum;
            }
            if(s[k] == 'T') {
                int sum = 0;
                for(int j = k + 1; j < strlen(s); j++){
                if(s[j] == '\n')
                    continue;
                    sum = sum * 10 + s[j] - '0';
                }
                body_t = sum / 100.0;
            }
        }
        //发送到手机端
        Blinker.print("person", person_code);
        Blinker.print("temp",body_t, "℃");
        body_temperature.print(body_t);
        person_name.print(person_code);
        body_temperature.color("#0099ff");
        person_name.color("#0099ff");
        if(body_t > 37.3) {
            body_temperature.color("#ff0000");
            person_name.color("#ff0000");
            Blinker.vibrate(); 
            Blinker.delay(500);
            Blinker.vibrate();  //使手机震动
            Blinker.delay(500);
            Blinker.vibrate();
          }
        Serial.write('\n'); 
    }
    if(flag == 1 && s[0] == 't') {
        Blinker.print("time", s + 1);
        myservo1.write(0);
        delay(5000);
        myservo1.write(90);

    }
    delay(200);
}
