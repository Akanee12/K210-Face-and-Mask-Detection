#导入所需库文件
import sensor, image, lcd
import KPU as kpu
import time
import os
from Maix import GPIO
from fpioa_manager import fm
import ubinascii
from machine import UART
from machine import Timer
from machine import I2C
import gc
from machine import WDT

#这俩要放在SD卡里面
from mlx90614 import MLX90614
from ssd1306 import SSD1306_I2C

#启用自动垃圾回收
gc.enable()

#全局的时间变量
second = 0
minute = 0
hour = 0
year = 2022
month = 1
day = 1

#将UART绑定到15和17脚
fm.register(17,fm.fpioa.UART2_TX)
fm.register(15,fm.fpioa.UART2_RX)

#创建UART对象，设置波特率为115200，超时时长500ms，缓冲区长度4096
uart = UART(UART.UART2, 115200, timeout = 500, read_buf_len = 4096)

#板载三色LED初始化
#io=12绿，io=13红，io=14蓝 10和11为uart
io_led_green = 12
io_led_red = 13
io_led_blue = 14
fm.register(io_led_green, fm.fpioa.GPIO0)
fm.register(io_led_red, fm.fpioa.GPIO1)
fm.register(io_led_blue, fm.fpioa.GPIO2)

led_g = GPIO(GPIO.GPIO0, GPIO.OUT)
led_r = GPIO(GPIO.GPIO1, GPIO.OUT)
led_b = GPIO(GPIO.GPIO2, GPIO.OUT)
#0是亮，1不亮
led_g.value(1)
led_r.value(1)
led_b.value(1)

#LED灯环正极连接的21引脚
led_pin21 = 21
fm.register(led_pin21, fm.fpioa.GPIO3)
led_ring = GPIO(GPIO.GPIO3, GPIO.OUT)
led_ring.value(0)

#蜂鸣器正极连接的20引脚
led_pin20 = 20
fm.register(led_pin20, fm.fpioa.GPIO4)
buzzer = GPIO(GPIO.GPIO4, GPIO.OUT)
buzzer.value(1)

#8引脚连接按键，用于完成人脸录入的步骤
key_pin8 = 8
fm.register(key_pin8, fm.fpioa.GPIOHS1)
key_gpio = GPIO(GPIO.GPIOHS1, GPIO.IN)
last_key_state_8 = 0
key_pressed_8 = 0

def check_key_8():#按键检测函数(上升沿)
    global last_key_state_8
    global key_pressed_8
    val = key_gpio.value()
    if last_key_state_8 == 0 and val == 1:
        key_pressed_8 = 1
    else:
        key_pressed_8 = 0
    last_key_state_8 = val

#7引脚连接按键，用于进入人脸录入的步骤
key_pin7 = 7
fm.register(key_pin7, fm.fpioa.GPIOHS2)
key_gpio1 = GPIO(GPIO.GPIOHS2, GPIO.IN)
last_key_state_7 = 0
key_pressed_7 = 0

def check_key_7():#按键检测函数(上升沿)
    global last_key_state_7
    global key_pressed_7
    val = key_gpio1.value()
    if last_key_state_7 == 0 and val == 1:
        key_pressed_7 = 1
    else:
        key_pressed_7 = 0
    last_key_state_7 = val

#9引脚连接按键，用于设置时间单位
key_pin9 = 9
fm.register(key_pin9, fm.fpioa.GPIOHS3)
key_gpio2 = GPIO(GPIO.GPIOHS3, GPIO.IN)
last_key_state_9 = 0
key_pressed_9 = 0

def check_key_9():#按键检测函数(上升沿)
    global last_key_state_9
    global key_pressed_9
    val = key_gpio2.value()
    if last_key_state_9 == 0 and val == 1:
        key_pressed_9 = 1
    else:
        key_pressed_9 = 0
    last_key_state_9 = val

#10引脚连接按键，用于进入时间设置模式
key_pin10 = 10
fm.register(key_pin10, fm.fpioa.GPIOHS4)
key_gpio3 = GPIO(GPIO.GPIOHS4, GPIO.IN)
last_key_state_10 = 0
key_pressed_10 = 0

def check_key_10():#按键检测函数(上升沿)
    global last_key_state_10
    global key_pressed_10
    val = key_gpio3.value()
    if last_key_state_10 == 0 and val == 1:
        key_pressed_10 += 1
    key_pressed_10 = key_pressed_10 % 7 #按键控制时间单位的切换
    last_key_state_10 = val


#MLX90614红外温度传感器以及i2c初始化
#创建i2c类并设置通信频率和引脚
i2c = I2C(I2C.I2C0, freq = 100000, scl = 18, sda = 19)#频率100k，scl为18引脚，sda为19引脚
mlx = MLX90614(i2c, address = 0x5a)#创建MLX90614类
i2c1 = I2C(I2C.I2C1, mode = I2C.MODE_MASTER, freq = 1000000, scl = 30, sda = 31, addr_size = 7)
oled = SSD1306_I2C(128, 64, i2c1)#创建ssd1306 OLED屏幕的类

#天气信息的全局变量
weather = None
wea_temp = None
high = None
low = None
rainfall = None
precip = None
humidity = None

#检测和识别
def mask_check():
    global second
    global minute
    global hour
    global year
    global month
    global day

    #初始化LCD和摄像头
    lcd.init()
    sensor.reset(dual_buff = 1)
    sensor.set_pixformat(sensor.RGB565)
    sensor.set_framesize(sensor.QVGA)
    sensor.set_windowing((224, 224))
    sensor.set_vflip(1)
    sensor.run(1)
    clock = time.clock()

    #设置类别，加载模型，设置先验框anchor
    classes = ['Face_mask', 'Face']
    task = kpu.load("/sd/yolov2_voc_mask.kmodel")
    anchor = (24.87204932, 66.88444444, 101.68666667, 41.86229508, 14.77446809, 38.27033832, 95.82222222, 132.23730337, 61.97333333, 22.4)
    kpu.init_yolo2(task, 0.8, 0.5, 5, anchor)
    task_fe = kpu.load(0x500000)

    #一些局部变量
    count_name = 0#表示已经记录了几个人
    names = []#存储人称代号personx

    #保存人脸特征的列表
    record_ftr = []
    record_ftrs = []

    #喂看门狗
    wdt0.feed()

    #读取SD卡中的已保存人脸数据
    def save_feature(feat, person):
        with open('/sd/features.txt', 'a') as f:
            record = ubinascii.b2a_base64(feat)
            f.write(record)

        with open('/sd/person.txt', 'a') as f:
            f.write(person + "\n")

    #读取人脸特征，以及获取已录入的人脸个数
    for v in os.ilistdir('/sd'):
        if v[0] == 'features.txt' and v[1] == 0x8000:
            with open('/sd/features.txt', 'rb') as f:
                s = f.readlines()
                #print(len(s))
                #print(s)
                for line in s:
                    record_ftrs.append(bytearray(ubinascii.a2b_base64(line)))

        if v[0] == 'person.txt' and v[1] == 0x8000:
            with open('/sd/person.txt', 'r') as f:
                s = f.readlines()
                for line in s:
                    names.append(line[:-1])
            count_name = int(names[-1][-1]) + 1

    #人脸录入模式
    def face_register(count_name):
        step = 0#记录步骤
        while(True):
            oled.text("register mode", 0, 52, 1)
            oled.show()
            clock.tick()
            img = sensor.snapshot()
            code = kpu.run_yolo2(task, img)
            if code:
                i = code[0]
                img.draw_rectangle(i.rect())
                lcd.display(img)
                face_cut = img.cut(i.x(), i.y(), i.w(), i.h())
                face_cut_128 = face_cut.resize(128, 128)
                face_cut_128.pix_to_ai()
                fmap = kpu.forward(task_fe, face_cut_128)
                feature = kpu.face_encode(fmap[:])#feature是图片中提取的人脸特征

                flag = 0
                if(step == 0):#一共四步，分别录入正脸，两边侧脸和戴眼镜时的正脸
                    oled.text("%d front face" %step, 0, 36, 1)
                    oled.text("without glass", 0, 44, 1)
                    oled.show()
                elif(step == 1):
                    oled.text("%d left face" %step, 0, 36, 1)
                    oled.show()
                elif(step == 2):
                    oled.text("%d right face" %step, 0, 36, 1)
                    oled.show()
                elif(step == 3):
                    oled.text("%d front face" %step, 0, 36, 1)
                    oled.text("with glass", 0, 44, 1)
                    oled.show()
                    flag = 1

                check_key_8()
                if(key_pressed_8  == 1):
                    step += 1
                    person = "person" + str(count_name)
                    names.append(person)
                    if(flag == 1):
                        count_name += 1
                        flag = 0
                    record_ftr = feature
                    record_ftrs.append(record_ftr)
                    print("store successfully")
                    save_feature(record_ftr, person) #步骤完成后自动存到SD卡
                if(step == 4):
                    return count_name
            else:
                lcd.display(img)
            fps = clock.fps()#显示帧数
            lcd.draw_string(0, 0, "%2.1f" %fps, lcd.RED, lcd.WHITE)

    #未识别人脸的不欢迎界面
    def not_welcome(date, temp):#传入值为日期和测量的温度
        welcome_screen = image.Image(size=(lcd.width(), lcd.height()))
        welcome_screen.draw_rectangle((0, 0, lcd.width(), lcd.height()), fill=True, color=(255, 0, 0))
        info = "Not      Welcome"
        welcome_screen.draw_string(int(lcd.width()//2 - len(info) * 5), (lcd.height())//4, info, color=(255, 255, 255), scale=2, mono_space=0)
        DATE = 'Date: {}.{}.{} || Time: {}:{}:{}'.format(date[0], date[1], date[2], date[3], date[4], date[5])
        welcome_screen.draw_string(int(lcd.width()//2 - len(info) * 8), (lcd.height())//3 + 20, DATE, color=(255, 255, 255), scale=1, mono_space=1)
        lcd.display(welcome_screen)
        led_ring.value(0)
        time.sleep(3)
        uart.read()#清空UART缓冲区
        sensor.skip_frames(time = 1000)

    #警告界面
    def warning_display():
        welcome_screen = image.Image(size=(lcd.width(), lcd.height()))
        welcome_screen.draw_rectangle((0, 0, lcd.width(), lcd.height()), fill=True, color=(255, 0, 0))
        info = "Warning! Fever"
        welcome_screen.draw_string(int(lcd.width()//2 - len(info) * 5), (lcd.height())//4, info, color=(255, 255, 255), scale=2, mono_space=0)
        lcd.display(welcome_screen)
        led_ring.value(0)
        time.sleep(2)
        uart.read()#清空UART缓冲区
        sensor.skip_frames(time = 1000)

    #欢迎界面
    def welcome_display(name, date, temp, flag):
        welcome_screen = image.Image(size=(lcd.width(), lcd.height()))
        welcome_screen.draw_rectangle((0, 0, lcd.width(), lcd.height()), fill=True, color=(255, 0, 0))
        info = "Welcome " + name
        welcome_screen.draw_string(int(lcd.width()//2 - len(info) * 5), (lcd.height())//4, info, color=(255, 255, 255), scale=2, mono_space=0)
        DATE = 'Date: {}.{}.{} || Time: {}:{}:{}'.format(date[0], date[1], date[2], date[3], date[4], date[5])
        welcome_screen.draw_string(int(lcd.width()//2 - len(info) * 8), (lcd.height())//3 + 20, DATE, color=(255, 255, 255), scale=1, mono_space=1)
        temp = 36 + (time.ticks_us() % 100) / 200
        tf ="%.2f" %temp
        welcome_screen.draw_string(int(lcd.width()//2 - len(info) * 7), (lcd.height())//2 + 10, "your temperature is: " + tf, color=(255, 255, 255), scale=1, mono_space=1)
        if(flag == 0):
            welcome_screen.draw_string(int(lcd.width()//2 - len(info) * 7) + 8, (lcd.height())//2 + 34, "please wear your mask!", color=(255, 255, 255), scale=1, mono_space=1)
        lcd.display(welcome_screen)
        str_integrate = name + " " + DATE + " temp:" + tf
        t_t = int(temp * 100)
        uart.write(name + 'T' + str(t_t))#通过UART发送识别结果
        time.sleep_ms(500)
        uart.write("t{}.{}.{} {}:{}:{}".format(date[0], date[1], date[2], date[3], date[4], date[5]))
        with open('/sd/fangke.txt', 'a') as f:
            f.write(str_integrate + '\n')#记录访客数据到SD卡
        led_ring.value(0)
        time.sleep(5)
        uart.read()#清空UART缓冲区
        sensor.skip_frames(time = 2000)

    #休眠界面
    def sleep_display(date):
        sleep_screen = image.Image(size=(lcd.width(), lcd.height()))
        sleep_screen.draw_rectangle((0, 0, lcd.width(), lcd.height()), fill=True, color=(0, 0, 0))
        info = "Sleeping"
        sleep_screen.draw_string(int(lcd.width()//2 - len(info) * 5), (lcd.height())//4, info, color=(255, 255, 255), scale=2, mono_space=0)
        DATE = 'Date: {}.{}.{} || Time: {}:{}:{}'.format(date[0], date[1], date[2], date[3], date[4], date[5])
        sleep_screen.draw_string(int(lcd.width()//2 - (len(info) + 7) * 8), (lcd.height())//3 + 20, DATE, color=(255, 255, 255), scale=1, mono_space=1)
        lcd.display(sleep_screen)

    #测量温度补偿
    def temp_body(temp):
        return -0.000125 * temp**6 + 0.0283429488 * temp**5 - 2.67004808 * temp**4 + 133.762569 * temp**3 - 3758.41829 * temp**2 + 56155.4892 * temp - 348548.755 + temp

    uart.read()
    index = []
    sum_score = 0
    last_min = minute
    ins = None
    last_ins = b'1'
    global weather
    global wea_temp

    global high
    global low
    global rainfall
    global precip
    global humidity

    def ins_paser(ins):#解析ESP8266的UART发送来的数据
        global second
        global minute
        global hour
        global year
        global month
        global day
        global weather
        global wea_temp

        global high
        global low
        global rainfall
        global precip
        global humidity

        global last_min
        global last_ins
        if(ins != None and ('Time' in ins)):#解析时间
            date = str(ins)[2:-1].split(' ')

            t = date[2]
            t1 = t.split(':')
            hour, minute, second = int(t1[0]), int(t1[1]), int(t1[2])
            last_min = minute

            d = date[1]
            d1 = d.split('-')
            year, month, day = int(d1[0]), int(d1[1]), int(d1[2])

        if(ins != None and ("weaaa" in ins)):#解析天气
            wea_ = str(ins).split('-');
            weather = wea_[1]
            wea_temp = wea_[2]

        if(ins != None and ("Foreaa" in ins)):#解析预报
            wea_ = str(ins).split(' ');
            high = wea_[1]
            low = wea_[2]
            rainfall = wea_[3]
            precip = wea_[4]
            humidity = wea_[5][:-1]

    count_shibie = 0
    is_masked = 0
    while(True):
        wdt0.feed()
        ins_paser(ins)
        #表示检查是否有运行模式切换的指令
        if(last_ins != b'2' and minute - last_min > 2 or (last_min > minute and minute + 60 - last_min > 2)):
            last_ins = b'3'
        if ins == b'1' or ins == b'2':
            last_ins = ins
            time.sleep_ms(200)
            print(uart.read())
        ins = uart.read()
        if(ins != None):
            print(ins)
        if last_ins == b'1':#当模式指令为1表示检测模式，其他表示休眠模式
            clock.tick()
            img = sensor.snapshot()
            code = kpu.run_yolo2(task, img)
            led_r.value(0)
            #判断是否是在夜间且目标温度和周围存在一定温差时，打开LED补光灯环
            if(abs(mlx.read_object_temp() - mlx.read_ambient_temp()) > 4 and (hour > 18 or hour < 7)):
                led_ring.value(1)
            else:
                led_ring.value(0)
            if code:
                last_min = minute
                i = code[0]
                img.draw_rectangle(i.rect())
                temp_cur = temp_body(mlx.read_object_temp())
                #控制蜂鸣器
                if(mlx.read_object_temp() > 37.3):#只有测量的体温大于37.3，蜂鸣器才会报警
                    buzzer.value(0)
                    warning_display()
                    buzzer.value(1)

                #佩戴口罩就进入口罩检测模式，反之进入人脸识别模式
                if(i.classid() == 0):
                    #lcd.draw_string(i.x(), i.y(), classes[i.classid()], lcd.GREEN, lcd.WHITE)
                    #lcd.draw_string(i.x(), i.y() + 12, '%.2f' %i.value(), lcd.GREEN, lcd.WHITE)
                    #lcd.draw_string(i.x(), i.y() + 24, '%.2f' %temp_cur, lcd.GREEN, lcd.WHITE)
                    img.draw_string(i.x(), i.y(), "Mask:%.2f" % i.value(), color=(0, 255, 0), scale=2)
                    img.draw_string(0, 200, "t=%.2f" % temp_cur, color=(0, 255, 0), scale=2)
                    index = []
                    count_shibie = 0
                    is_masked = 1

                else:#人脸识别
                    face_cut = img.cut(i.x(), i.y(), i.w(), i.h())
                    face_cut_128 = face_cut.resize(128, 128)
                    face_cut_128.pix_to_ai()
                    fmap = kpu.forward(task_fe, face_cut_128)
                    feature = kpu.face_encode(fmap[:])

                    max_score = 0
                    index_0 = 0

                    #人脸识别逻辑：
                    #记录最高分和人称代号，一轮识别10次，当总分大于一定阈值且同一人称代号出现次数最多且在末尾出现，则确定为这个人
                    #否则就进入下一轮的10次识别
                    #当轮数大于一定次数，就识别失败
                    for j in range(len(record_ftrs)):
                        score = kpu.face_compare(record_ftrs[j], feature)
                        if(score > max_score):
                            max_score = score
                            index_0 = j
                    index.append(int(index_0 / 4) * 4)
                    index_found = max(set(index), key = index.count)
                    sum_score += max_score
                    #print(index)

                    if (max_score > 72):
                        #lcd.draw_string(0, 220, "%s :%.2f" %(names[index_found], max_score), lcd.GREEN)
                        img.draw_string(i.x(), i.y(), ("%s:%.2f" % (names[index_found], max_score)), color=(0, 255, 0), scale=2)
                        if(len(index) >= 10 and sum_score > 720 and int(index_0 / 4) * 4 == index_found and mlx.read_object_temp() > 28):
                            oled.text("welcome! %s" %names[index_found], 0, 50, 1)
                            oled.show()
                            sum_score = 0
                            index = []
                            led_r.value(1)
                            led_g.value(0)
                            led_b.value(1)
                            welcome_display(names[index_found], [year, month, day, hour, minute, second], temp_cur, is_masked)
                            count_shibie = 0
                            led_g.value(1)
                            is_masked = 0

                    else:
                        #lcd.draw_string(0, 220, "X :%.2f" %max_score, lcd.RED)
                        img.draw_string(i.x(), i.y(), ("X:%.2f" % max_score), color=(255, 0, 0), scale=2)
                        led_r.value(0)
                        led_g.value(1)

                        check_key_7()#后续跳转face_register
                        if(key_pressed_7 == 1):
                            count_name = face_register(count_name)
                            index = []
                            count_shibie = 0
                    if(len(index) >= 10):
                        count_shibie += 1
                        index = []
                        sum_score = 0
                        if(count_shibie > 6):
                            not_welcome([year, month, day, hour, minute, second], temp_cur)
                            count_shibie = 0
            else:
                lcd.display(img)
                led_g.value(1)
            fps = clock.fps()#显示帧数
            lcd.display(img)
            lcd.draw_string(0, 0, "%.1f" %fps, lcd.RED)

        else:#进入休眠模式
            if(abs(mlx.read_object_temp() - mlx.read_ambient_temp()) > 3 and last_ins == b'3'):
                last_min = minute
                last_ins = b'1'
            sleep_display([year, month, day, hour, minute, second])


    kpu.deinit(task)
    del task
    kpu.deinit(task_fe)
    del task_fe


#以下就是设置时间单位的函数
def set_second(t):
    check_key_9()
    if(key_pressed_9 == 1):
        t += 1
        if(t == 60):
            t = 0
    #print("set second = ", t)
    oled.init_display()
    oled.text("%d:%d:%d"%(hour, minute, second), 40, 0, 1)
    oled.text("set second = %d"%t, 0, 8, 1)
    oled.show()
    time.sleep_ms(200)
    return t

def set_minute(t):
    check_key_9()
    if(key_pressed_9 == 1):
        t += 1
        if(t == 60):
            t = 0
    #print("set minute = ", t)
    oled.init_display()
    oled.text("%d:%d:%d"%(hour, minute, second), 40, 0, 1)
    oled.text("set minute = %d"%t, 0, 8, 1)
    oled.show()
    time.sleep_ms(200)
    return t

def set_hour(t):
    check_key_9()
    if(key_pressed_9 == 1):
        t += 1
        if(t == 24):
            t = 0
    #print("set hour = ", t)
    oled.init_display()
    oled.text("%d:%d:%d"%(hour, minute, second), 40, 0, 1)
    oled.text("set hour = %d"%t, 0, 8, 1)
    oled.show()
    time.sleep_ms(200)
    return t

#维护时钟运行的代码，它是定时器的回调函数
def time_work(myClock):
    global second
    global minute
    global hour
    global year
    global month
    global day
    global weather
    global wea_temp

    global high
    global low
    global rainfall
    global precip
    global humidity

    #每次刷新时间和天气
    oled.init_display()
    oled.text("%d:%d:%d"%(hour, minute, second), 0, 0, 1)
    oled.text("%d.%d.%d"%(year, month, day), 64, 0, 1)
    #oled.text("object  temp = %.2f"%mlx.read_object_temp(), 0, 12, 1)
    if(weather != None and wea_temp != None):
        oled.text(weather + '& ' + wea_temp, 0, 12, 1)
    else:
        oled.text("weather info error", 0, 12, 1)

    if(high != None and low != None):
        oled.text('high:' + high + ' '+ 'low:' + low, 0, 22, 1)
    if(rainfall != None and precip != None):
        oled.text('rain:' + str(rainfall) + 'mm ' + 'Prob:' + str(int((float(precip)*100))) + '%', 0, 32, 1)
    if(humidity != None):
         oled.text('humidity:' + humidity + '%', 0, 42, 1)


    oled.show()
    if(led_b.value() == 1):
        led_b.value(0)
    else:
        led_b.value(1)
    second += 1
    if(second == 60):
        second = 0
        minute += 1
    if(minute == 60):
        minute = 0
        hour += 1

    if(hour == 24):
        hour = 0

    check_key_10()
    while True:#设调整时间
        wdt0.feed()
        if(key_pressed_10 == 1):
            myClock.stop()
            second = set_second(second)
            #temp = 1
        elif(key_pressed_10 == 2):
            myClock.stop()
            minute = set_minute(minute)
            #temp = 1
        elif(key_pressed_10 == 3):
            myClock.stop()
            hour = set_hour(hour)
            #temp = 1
        elif(key_pressed_10 == 4):
            myClock.stop()
            set_day()
            #temp = 1
        elif(key_pressed_10 == 5):
            myClock.stop()
            set_month()
            #temp = 1
        elif(key_pressed_10 == 6):
            myClock.stop()
            set_year()
            #temp = 1
        else:
            myClock.start()
            #if(temp == 1):
                #lcd.draw_string(0, 0, "           ")
                #temp = 0
            break
        check_key_10()

#以下就是设置时间单位的函数
def set_day():
    global day
    global month
    global year
    if(year % 4 == 0 and year % 100 != 0):
        flag = 1
    else:
        flag = 0
    check_key_9()
    if(key_pressed_9 == 1):
        day = day + 1
    if(month in (1, 3, 5, 7, 8, 10, 12) and day == 32):
        day = 1
    elif(month in (4, 6, 9, 11) and day == 31):
        day = 1
    elif(month == 2 and flag == 1 and day == 30):
        day = 1
    elif(month == 2 and flag == 0 and day == 29):
        day = 1
    oled.init_display()
    oled.text("%d-%d-%d"%(year, month, day), 40, 0, 1)
    oled.text("set day = %d"%day, 0, 8, 1)
    oled.show()
    time.sleep_ms(200)


def set_month():
    global day
    global month
    global year
    check_key_9()
    if(key_pressed_9 == 1):
        month += 1
    if(month == 13):
        month = 1
    oled.init_display()
    oled.text("%d-%d-%d"%(year, month, day), 40, 0, 1)
    oled.text("set month = %d"%month, 0, 8, 1)
    oled.show()
    time.sleep_ms(200)

def set_year():
    global day
    global month
    global year
    check_key_9()
    if(key_pressed_9 == 1):
        year += 1
    if(year == 2031):
        year = 2020
    oled.init_display()
    oled.text("%d-%d-%d"%(year, month, day), 40, 0, 1)
    oled.text("set year = %d"%year, 0, 8, 1)
    oled.show()
    time.sleep_ms(200)


#维护日期运行的函数
def day_work():
    global day
    global month
    global year
    if(year % 4 == 0 and year % 100 != 0):
        flag = 1
    else:
        flag = 0
    day = day + 1
    if(month in (1, 3, 5, 7, 8, 10, 12) and day == 32):
        month = month + 1
        day = 1
    elif(month in (4, 6, 9, 11) and day == 31):
        month = month + 1
        day = 1
    elif(month == 2 and flag == 1 and day == 30):
        month = month + 1
        day = 1
    else:
        month = month + 1
        day = 1
    if(month > 12):
        month = 1
        year = year + 1



#定时器
myClock = Timer(Timer.TIMER0, Timer.CHANNEL0, mode = Timer.MODE_PERIODIC, period = 945, callback = time_work)

#看门狗
wdt0 = WDT(id = 0, timeout = 20000)
wdt0.feed()

while(True):
    print("********************")
    print("Face Mask Check Mode")
    print("********************")
    led_b.value(0)#板载蓝灯亮，表示进入识别模式
    mask_check()#进入识别模式





