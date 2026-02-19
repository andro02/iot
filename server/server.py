from flask import Flask, jsonify, request
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import paho.mqtt.client as mqtt
import json

app = Flask(__name__)

# InfluxDB Configuration
token = "B8HDBR5Sh9cCibUUGyUAM2rDL4ajESUs_UyUHpRp52OT3mL1IriRtRCD2cnnix-09BGs1_OU9xv9HMNXnWDSGg=="
org = "FTN"
url = "http://localhost:8086"
bucket = "iot_db"
influxdb_client = InfluxDBClient(url=url, token=token, org=org)


# MQTT Configuration
mqtt_client = mqtt.Client()
mqtt_client.connect("localhost", 1883, 60)
mqtt_client.loop_start()

def on_connect(client, userdata, flags, rc):
    client.subscribe("Sensors/DS1")
    client.subscribe("Sensors/DS2")
    client.subscribe("Sensors/BTN")
    client.subscribe("Sensors/DMS")
    client.subscribe("Sensors/DUS1")
    client.subscribe("Sensors/DUS2")
    client.subscribe("Sensors/DPIR1")
    client.subscribe("Sensors/DPIR2")
    client.subscribe("Sensors/DPIR3")
    client.subscribe("Sensors/DHT")
    client.subscribe("Sensors/Gyro")
    client.subscribe("Actuators/DL")
    client.subscribe("Actuators/DB")
    client.subscribe("Actuators/BRGB")
    client.subscribe("Actuators/LCD")
    client.subscribe("Sensors/BIR")

mqtt_client.on_connect = on_connect
mqtt_client.on_message = lambda client, userdata, msg: save_to_db(json.loads(msg.payload.decode('utf-8')))


def save_to_db(data):
    write_api = influxdb_client.write_api(write_options=SYNCHRONOUS)
    point = Point(data["measurement"]) \
        .tag("simulated", data["simulated"]) \
        .tag("runs_on", data["runs_on"]) \
        .tag("name", data["name"])
    
    measurement_name = data["measurement"]

    # LISTA MERENJA KOJA UVEK MORAJU BITI TEKST
    # Za sad samo DMS
    text_measurements = [
        "Key_Pressed",   # Tastatura (DMS)
        "IR_Remote",     # Daljinski (IR)
        "RGB_Color",     # Boja svetla (BRGB)
        "LCD_Text",      # Tekst ekrana (LCD)
        "Acceleration",  # Ziroskop [x, y, z]
        "Rotation"       # Ziroskop [x, y, z]
    ]

    # if measurement_name in text_measurements: # Ako je tastatura, cuvaj kao string
    #      point = point.field("value_str", str(data["value"]))

    # # Ako je vrednost broj, konvertuj, inače ostavi kao string
    # try:
    #     val = float(data["value"])
    #     point = point.field("value", val)
    # except ValueError:
    #     # nije broj -> piši kao string
    #     point = point.field("value_str", str(data["value"]))

    if measurement_name in text_measurements: 
        # Znamo da je ovo tekst, cuvaj ga iskljucivo u value_str
        point = point.field("value_str", str(data["value"]))
    else:
        # Za ostale pokusaj da konvertujes u broj (Temperatura, Distanca, Motion 1/0...)
        try:
            val = float(data["value"])
            point = point.field("value", val)
        except (ValueError, TypeError):
            # Sigurnosna mreza ako ipak stigne neki cudan tekst
            point = point.field("value_str", str(data["value"]))

    write_api.write(bucket=bucket, org=org, record=point)


# Route to store dummy data
@app.route('/store_data', methods=['POST'])
def store_data():
    try:
        data = request.get_json()
        store_data(data)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


def handle_influx_query(query):
    try:
        query_api = influxdb_client.query_api()
        tables = query_api.query(query, org=org)

        container = []
        for table in tables:
            for record in table.records:
                container.append(record.values)

        return jsonify({"status": "success", "data": container})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@app.route('/simple_query', methods=['GET'])
def retrieve_simple_data():
    query = f"""from(bucket: "{bucket}")
    |> range(start: -10m)
    |> filter(fn: (r) => r._measurement == "Humidity")"""
    return handle_influx_query(query)


@app.route('/aggregate_query', methods=['GET'])
def retrieve_aggregate_data():
    query = f"""from(bucket: "{bucket}")
    |> range(start: -10m)
    |> filter(fn: (r) => r._measurement == "Humidity")
    |> mean()"""
    return handle_influx_query(query)


if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
