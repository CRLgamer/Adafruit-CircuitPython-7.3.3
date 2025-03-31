# Demo for pot and servo

import time
import board
from analogio import AnalogIn
import neopixel
import adafruit_esp32spi.adafruit_esp32spi_socket as socket
import adafruit_minimqtt.adafruit_minimqtt as MQTT
import pwmio
from adafruit_motor import servo
from digitalio import DigitalInOut
import busio
from adafruit_esp32spi import adafruit_esp32spi
from adafruit_esp32spi import adafruit_esp32spi_wifimanager
from adafruit_seesaw.seesaw import Seesaw

# Get wifi details and stuff from the secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

# Setup i2c for moisture sensor.
i2c_bus = board.I2C()
ss = Seesaw(i2c_bus, addr=0x36)

# Setup ESP32 pins
esp32_cs = DigitalInOut(board.ESP_CS)
esp32_ready = DigitalInOut(board.ESP_BUSY)
esp32_reset = DigitalInOut(board.ESP_RESET)

# Start up the esp32
spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)

# Look for wifi networks
FoundNetwork = False
while not FoundNetwork:
    print("Scanning for aps")
    Networks = esp.scan_networks()
    for ap in Networks:
        APname = str(ap['ssid'], 'UTF-8')
        print("Trying: ", APname, end='  ')
        try:
            # Try to add in the ssid and passwork for this AP
            secrets['password'] = secrets[APname]
            secrets['ssid'] = APname
            print("Sucess!")
            FoundNetwork = True
            break
        except KeyError:
            print("Not found")

# create a PWMOut object on Pin D4 for the servo
pwm = pwmio.PWMOut(board.D4, duty_cycle=2 ** 15, frequency=50)

# Create a servo object
TestServo = servo.Servo(pwm)
TestServo.angle = 90  # Default to middle

# Setup the pot
Potentiometer = AnalogIn(board.D3)

# Setup status LED
status_light = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.2)

# Create WiFi object
wifi = adafruit_esp32spi_wifimanager.ESPSPI_WiFiManager(esp, secrets, status_light)

# MQTT Feeds
# Setup a feed to record pot positions
Moisture = secrets["aio_username"] + "/feeds/moisture"
ServoPos = secrets["aio_username"] + "/feeds/ServoPos"

# Called on connection to the broker
def connected(client, userdata, flags, rc):
    print("Connected to broker!")
    client.subscribe(ServoPos)

# Called when disconnected
def disconnected(client, userdata, rc):
    print("Disconnected from %s", secrets["broker"])

def message(client, topic, message):
    global TestServo

    print("New servo position {1} on topic {0}".format(topic, message))
    TestServo.angle = int(message)

# Connect to WiFi
print("Connecting to ssid", secrets["ssid"])
wifi.connect()
print("Connected to WiFi")

# Initialize MQTT interface with the esp interface
MQTT.set_socket(socket, esp)

# Set up a MQTT client
mqtt_client = MQTT.MQTT(
    broker=secrets["broker"],
    username=secrets["aio_username"],
    password=secrets["aio_key"]
)

# Setup the callback methods above
mqtt_client.on_connect = connected
mqtt_client.on_disconnect = disconnected
mqtt_client.on_message = message

# Connect the client to the MQTT broker.
print("Connecting to", secrets["broker"])
mqtt_client.connect()

# Times when last  messages were sent
last_pub = -100

while True:
    now = time.monotonic()  # Get current time

    mqtt_client.loop(1)

    #----------------------------------------------------------------
    #pos = (Potentiometer.value / 512)  # Read pot posistion from A to D
    #TestServo.angle = pos # Move servo


    #----------------------------------------------------------------
    # read moisture level through capacitive touch pad
    touch = ss.moisture_read()

    # read temperature from the temperature sensor


    print( "  moisture: " + str(touch))

    status_light [0] = touch
    status_light.show()

    # Time to send a new pot posistion message?
    if (now-last_pub) > 5:  # Longer than 2 seconds?
        #print("Publishing pot value:", pos)
        #mqtt_client.publish(PotPos, pos)

       # Time to send a new moisture sensor message...
       # print("Publishing moisture value:", touch)
        mqtt_client.publish(Moisture, touch)


        last_pub = now  # Reset timer

    time.sleep(.2)
