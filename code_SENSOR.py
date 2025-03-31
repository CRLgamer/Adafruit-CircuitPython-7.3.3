# Demo for MQTT publish

import time
import board
from analogio import AnalogIn
import neopixel
import adafruit_esp32spi.adafruit_esp32spi_socket as socket
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from digitalio import DigitalInOut
import busio
from adafruit_esp32spi import adafruit_esp32spi
from adafruit_esp32spi import adafruit_esp32spi_wifimanager

# Get wifi details and stuff from the secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

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

# Setup the light sensor
light_sensor = AnalogIn(board.LIGHT)

# Setup status LED
status_light = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.2)

# Create WiFi object
wifi = adafruit_esp32spi_wifimanager.ESPSPI_WiFiManager(esp, secrets, status_light)

# MQTT Feeds
# Setup a feed for publishing light sensor data
LightSensor = secrets["aio_username"] + "/feeds/LightSensor"

# Called on connection to the broker
def connected(client, userdata, flags, rc):
    print("Connected to broker!")

# Called when disconnected
def disconnected(client, userdata, rc):
    print("Disconnected from %s", secrets["broker"])


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

# Connect the client to the MQTT broker.
print("Connecting to", secrets["broker"])
mqtt_client.connect()

# Times when last  messages were sent
last_light = -100

while True:
    # Poll the message queue
    mqtt_client.loop(1)

    now = time.monotonic()  # Get current time

    # Time to send a new light message?
    if (now-last_light) > 5:  # Longer than 5 seconds?
        light = light_sensor.value
        print("Publishing light sensor value:", light)
        mqtt_client.publish(LightSensor, light)
        last_light = now  # Reset timer

import time
import board
import Seesaw

i2c_bus = board.I2C()

ss = Seesaw(i2c_bus, addr=0x36)

while True:
    # read moisture level through capacitive touch pad
    touch = ss.moisture_read()

    # read temperature from the temperature sensor
    temp = ss.get_temp()

    print("temp: " + str(temp) + "  moisture: " + str(touch))
    time.sleep(2)