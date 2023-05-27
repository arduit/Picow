#Motor_Motor_Didectionection of rotation  (Forward/Reverse)
#Motor_speed_open  (0..100)
#Motor_speed_close  (0..100)
#Motor_limit_travel..(Max encoder read)
#Motor_soft_limit..(Encoder set)

import network
import machine
import socket
import ujson
import time
import os
import select
import gc
import re
from secrets import secrets
from machine import Pin,ADC,PWM
from time import sleep

default_setings = {'Motor_Didection': 'Forward','Motor_speed_open': 50,'Motor_speed_close': 20,'Motor_limit_travel': 5000,'Soft_encoder_Limit': 5000}


buton = Pin(15, mode=Pin.IN, pull=Pin.PULL_UP)   # Buton Pin
butonF = Pin(11, mode=Pin.IN, pull=Pin.PULL_UP)   # Buton Pin >>
butonR = Pin(10, mode=Pin.IN, pull=Pin.PULL_UP)   # Buton Pin <<
end_stop = Pin(14, mode=Pin.IN, pull=Pin.PULL_UP)   # End_stop Pin

Motor_Didection =''
Motor_speed_open =''
Motor_speed_close =''
Motor_limit_travel =''
Soft_encoder_Limit =''



estatus = ['stop', 'runF', 'runR', 'setup']
pozision = ['end_Stop', 'soft_limit', 'max_soft_limit', 'unknown']

#****  Difault Status   ***
old_buton_state = -1
old_butonF_state = -1
old_butonR_state = -1
old_end_stop_state = -1
status = estatus[0]
#****  End Difault Status   ***


#****  Encoder Setings   ***
encoderA = Pin(13, mode=Pin.IN, pull=Pin.PULL_UP)   # Encoder Pin
encoderB = Pin(12, mode=Pin.IN, pull=Pin.PULL_UP)   # Encoder Pin

encoder_counts = 0
previous_counts =-1

def handler(p):
    global encoder_counts
    if encoderA.value():
        encoder_counts -= 1
    else:
        encoder_counts += 1
    print("Encoder counter:", encoder_counts)
    
def handler1(p):
    global encoder_counts
    if encoderA.value():
        encoder_counts += 1
    else:
        encoder_counts -= 1

encoderB.irq(handler, Pin.IRQ_FALLING)     
encoderB.irq(handler1, Pin.IRQ_RISING)
#****  End Encoder Setings   ***

#*** Motor Setings  ***
motor_IN1 = Pin(22, mode=Pin.OUT, value=0) # Motor control Pin IN1
motor_IN2 = Pin(21, mode=Pin.OUT, value=0) # Motor control Pin IN2
motor_enable = PWM(Pin(8)) # Motor  PWM pin
motor_enable.freq(12000) # Motor Speed Friqunsi	
motor_enable.duty_u16(0) # Motor Speed PWM

def motor_forward():
   motor_IN1.high()
   motor_IN2.low()
   
def motor_go_forward(speed):
    motor_forward()
    motor_enable.duty_u16(speed*655)
    print('motor_go_forward')

def motor_backward():
   motor_IN1.low()
   motor_IN2.high()
   
def motor_go_backward(speed):
    motor_backward()
    motor_enable.duty_u16(speed*655)
    print('motor_go_backward')   
   
def motor_stop():
   motor_IN1.low()
   motor_IN2.low()
   motor_enable.duty_u16(0)
   
#*** End Motor Setings   ***

led = machine.Pin('LED', machine.Pin.OUT)

def blink_onboard_led(num_blinks, delta_t):
    led = machine.Pin('LED', machine.Pin.OUT)
    for i in range(num_blinks):
        led.on()
        time.sleep(delta_t)
        led.off()
        time.sleep(delta_t)

def set_setings():
    global Motor_Didection
    global Motor_speed_open
    global Motor_speed_close
    global Motor_limit_travel
    global Soft_encoder_Limit

    with open('Setings.json', 'r') as f:
        setings_read = f.read()
    var = ujson.loads(setings_read)
    Motor_Didection = var['Motor_Didection']
    Motor_speed_open = var['Motor_speed_open']
    Motor_speed_close = var['Motor_speed_close']
    Motor_limit_travel = var['Motor_limit_travel']
    Soft_encoder_Limit = var['Soft_encoder_Limit']
    
if 'Setings.json' in os.listdir():
    print('Setings found')
    blink_onboard_led(2,0.5)
    set_setings()
else:
    print('Setings not found')
    blink_onboard_led(5,0.5)
    with open('Setings.json', 'w') as f:
        ujson.dump(default_setings, f)
    set_setings()
    
    
def save_web_to_setings():
    web_setings = {}
    web_setings["Motor_Didection"] = Motor_Didection
    web_setings["Motor_speed_open"] = Motor_speed_open
    web_setings["Motor_speed_close"] = Motor_speed_close
    web_setings["Motor_limit_travel"] = Motor_limit_travel
    web_setings["Soft_encoder_Limit"] = Soft_encoder_Limit
    with open('Setings.json', 'w') as f:
        ujson.dump(web_setings, f)
    set_setings()
    blink_onboard_led(3,0.5)
    
#***  Network setup  ***      
# Ap Network setup
def network_up():
    essid = secrets['ssid']
    password = secrets['pw']

    ap = network.WLAN(network.AP_IF)
    ap.config(essid=essid, password=password)
    ap.active(True)

    while ap.active() == False:
      pass

    print('Connection successful')
    print(ap.ifconfig())

network_up()

# HTTP server with socket
addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
print('Listening on', addr)

s = socket.socket()
s.settimeout(0.9)
#s.setblocking(0)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
#s.settimeout(0)
s.bind(addr)
s.listen(1)#data = "My data read from the Web"

def Listen_for_connections():
    global Motor_Didection, Motor_speed_open, Motor_speed_close, Motor_limit_travel, Soft_encoder_Limit
    try:
        #print('try_connections')
        
        cl, addr = s.accept()
        gc.collect()
        #print('in',gc.mem_free())
        #print('Client connected from', addr)
        r = 0
        r = cl.recv(1024)
        #print(r)
        
        r = str(r)

        if (r.find('?reverse=5')) > 0 :
            Motor_Didection = 'Reverse'
            print('set revers')
        if (r.find('?forward=5')) > 0:
            Motor_Didection = 'Forward'
            print('set forward')
        if (r.find('?So=')) > 0:
            print('set So='+ r[11:14])
            Motor_speed_open = r[11:14]
        if (r.find('?Sc=')) > 0:
            print('set Sc='+ r[11:14])
            Motor_speed_close = r[11:14]
        if (r.find('?reset_encoder')) > 0:
            print('reset_encoder')    
        if (r.find('?start_Cal')) > 0:
            print('start_Cal')
        if (r.find('?stop_Cal')) > 0:
            print('stop_Cal')
        if (r.find('?save_setings')) > 0:
            save_web_to_setings()
            print('save_setings')

        cl.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
        cl.send(Website())
        gc.collect()
        #print('out',gc.mem_free())
        cl.close()
        #print('Connection closed')
        
    except OSError as e:
        pass
        #cl.close()
        #print('Connection closed')
        #main()
    #finally:
        #print('finished')

#***  End Network setup  ***    

#<meta http-equiv="refresh" content="5"> 
#***  Web Page  ***
def Website():
    global Motor_limit_travel, Motor_Didection, Motor_speed_open, Motor_speed_close
    
    website = """<!DOCTYPE html>
<html><head>
    <title>Motor Control</title>
    
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #fff;
        }
        .header {
            color: #333;
            padding: 10px;
            text-align: center;
            font-size: 24px;
        }
        .company-name {
            color: #4B0082; /* Indigo color */
            text-align: center;
            padding: 20px;
            font-size: 30px;
            font-weight: bold;
        }
        .sub-header {
            color: #666;
            padding: 10px;
            text-align: center;
            font-size: 20px;
        }
        .button-group {
            display: flex;
            justify-content: center;
            padding: 20px;
        }
        button {
            margin: 0 10px;
            padding: 10px 20px;
            font-size: 16px;
            background-color: #6495ED; /* Cornflower Blue */
            color: #fff;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        button:hover {
            background-color: #1E90FF; /* Dodger Blue */
        }
        .input-group {
            display: flex;
            justify-content: center;
            padding: 20px;
        }
        .output-value {
            margin: 0 10px;
            width: 100px;
            height: 30px;
            text-align: center;
        }
        .input-value {
            margin: 0 10px;
            width: 100px;
            height: 30px;
            text-align: center;
        }
        .minus-button {
            margin-right: 10px;
        }
        hr {
            border: none;
            border-top: 1px solid #ccc;
        }
    </style>

    <script>

       var nMotor_speed_open = '50';
       var nMotor_speed_close = '50';

        function sendRequest(action,data) {
            if (data==1) {
                data = nMotor_speed_open;

            };
            if (data==2) {
                data = nMotor_speed_close;

            };

            var xhttp = new XMLHttpRequest();
            xhttp.open("GET", "/?" + action + "=" + data, true);
            xhttp.send();
            };

        function ch(value2, i){
            if (i==1) {
                document.getElementById("Motor_speed_open_neo_view").value = value2;
                nMotor_speed_open = value2;

            };
            if (i==2) {
                document.getElementById("Motor_speed_close_neo_view").value = value2;
                nMotor_speed_close = value2; 

            };
        };

        function changeColor(newColor) {
              const elem = document.getElementById("value_one");
              elem.style.color = newColor;
        };

    </script>
</head>
<body>
    <div class="company-name">Your Company Name</div>
    <div class="header">Motor Default Direction</div>
    <div class="button-group">
        <button onclick="sendRequest('forward','5')">Forward</button>
        <button onclick="sendRequest('reverse','5')">Reverse</button>
        <p id="Motor_Didection" style="font-size: x-large;margin-bottom: 5px;margin-top: 5px;">""" + 'Actual value ' + Motor_Didection + """</p>
    </div>
    <div class="header">Motor Speed (Open)</div>
    <div class="input-group">
        <input id="Motor_speed_open_neo" type="range" min="0" max="100" step="1" oninput="ch(this.value, 1)">
        <input type="text" id="Motor_speed_open_neo_view" name="lname" value="50" style="width: 50px;align-content: center;display: grid;text-align: right;font-size: x-large;color: red;">
        <button onclick="sendRequest('So','1')">Set</button>
        <p id="Motor_speed_open" style="font-size: x-large;margin-bottom: 5px;margin-top: 5px;">""" + 'Actual value ' + str(Motor_speed_open) + """</p>
    </div>
    <div class="header">Motor Speed (Close)</div>
    <div class="input-group">
        <input id="Motor_speed_close_neo" type="range" min="0" max="100" step="1" oninput="ch(this.value, 2)">
        <input type="text" id="Motor_speed_close_neo_view" name="lname" value="50" style="width: 50px;align-content: center;display: grid;text-align: right;font-size: x-large;color: red;">
        <button onclick="sendRequest('Sc', '2')">Set</button>
        <p id="Motor_speed_close" style="font-size: x-large;margin-bottom: 5px;margin-top: 5px;">""" + 'Actual value ' + str(Motor_speed_close) + """</p>
    </div>
    <hr>
    <div class="header">Set Open Position</div>
    <div class="sub-header">1. Put motor in closed position and press "Start"</div>
    <div class="button-group">
        <button onclick="sendRequest('reset_encoder')">Start</button>
    </div>
    <div class="header">2. Move motor manually into end position (encoder is counting)</div>
    <div class="button-group">
        <button onclick="sendRequest('start_Cal')">Go</button>
        <button onclick="sendRequest('stop_Cal')">Stop</button>
    </div>    
    <div class="header">3. When in end position press "Save"</div>
    <div class="button-group">
        <button onclick="sendRequest('save_setings')">Save</button>
    </div>

</body></html>
    """
    return website


#***  End Web Page  ***


def buton_status():
    global buton_state, butonF_state, butonR_state, end_stop_state
    buton_state = buton.value() 
    butonF_state = butonF.value() 
    butonR_state = butonR.value() 
    end_stop_state = end_stop.value()
   
        
while True:
    #print('in mein')
    if (encoder_counts != previous_counts):
        previous_counts = encoder_counts
        print("Encoder counter:", encoder_counts)

    if encoder_counts >= Soft_encoder_Limit:
        motor_stop()
        status = estatus[0]
        
    buton_status()
    #logic_state = buton.value()    
    if not (old_buton_state == buton_state):
        old_buton_state = buton_state
        if buton_state == 0 and status == estatus[0] and encoder_counts <= Soft_encoder_Limit :     # if push_button pressed
            print('buton pres_run')             # led will turn ON
            motor_go_backward(50)
            status = estatus[1]
        elif buton_state == 0 and status == estatus[0] and encoder_counts >= Soft_encoder_Limit :     # if push_button pressed
            print('buton pres_run')             # led will turn ON
            motor_go_forward(50)
            status = estatus[2]    
        elif buton_state == 0 and status != estatus[0] :
            print('buton pres_stop')
            motor_stop()
            status = estatus[0]
            
    if not (old_butonF_state == butonF_state):
        old_butonF_state = butonF_state
        if butonF_state == 0:     # if push_button pressed
            print('butonF pres')             # led will turn ON
            status = estatus[1]
            motor_go_backward(50)
            
    if not (old_butonR_state == butonR_state):
        old_butonR_state = butonR_state
        if butonR_state == 0:     # if push_button pressed
            print('butonR pres')             # led will turn ON
            status = estatus[2]
            motor_go_forward(50)
            
    if not (old_end_stop_state == end_stop_state):
        old_end_stop_state = end_stop_state
        if (end_stop_state == 0 ):
            print('end_stop')
            motor_stop()
            status = estatus[0]
            poz = pozision[0]
            encoder_counts = 0
    Listen_for_connections()
   
    sleep(0.1)