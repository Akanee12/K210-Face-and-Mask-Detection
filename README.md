# K210-Face-and-Mask-Detection
使用MaixBit和ESP8266，分别使用MicroPython和Arduino编程，其具备口罩检测、人脸识别和物联网功能，可以设计为物联网防疫门禁系统。

使用方法：
1.0x500000_FeatureExtraction刷入flash的0x500000位置；
2.yolov2_voc_mask模型和font、framebuf、ssd1306、mlx90614这些额外的库文件存入SD卡（如果你不需要测温和OLED显示，可以不要这些库文件）；
3.接线并将程序刷入便可使用。

物联网功能中Blinker就是点灯科技，App Store和酷安都能找到，网上有使用教程，也可以看看官方文档，可以自定手机端控制面板的按键。
心知天气的数据需要注册心知天气的账号，获取私钥。这个可以看看太极创客的内容。

若要用自己的数据集训练模型，建议使用MxYolo3软件。然后在K210的运行代码中做出相应修改即可。
上面的模型就是yolov2+mobilenetv1训练出来的，然后人脸特征提取是用官方例程的模型。

接线图可参考原理图。
