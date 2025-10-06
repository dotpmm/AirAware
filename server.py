import math
import random
import requests
from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, messaging

# Local-IP address of the AI-API server
WOOD = "http://172.30.68.202:6969"

app = Flask(__name__)

# Firebase SDK to send mobile notifications
try:
    firebase_admin.initialize_app(credentials.Certificate('airaware2-firebase-adminsdk-fbsvc-017dddaf26.json'))
    print("Firebase Admin SDK initialized successfully.")
except Exception as e:
    print(f"Error initializing Firebase Admin SDK: {e}")

def wood_ai_server_hitter(lat,lon,age,asthama_bool,preg_bool,cardio_bool,copd_bool,pollen_bool):
    try:
        response = requests.post(WOOD, json={
          "latitude": lat,
          "longitude": lon,
          "user_info": {
            "age": age,
            "asthama_bool": asthama_bool,
            "pollen_bool": pollen_bool,
            "copd_bool": copd_bool,
            "cardio_bool":  cardio_bool,
            "preg_bool": preg_bool
          }
        })
        response.raise_for_status() 
        data = response.json()

        return data
    except requests.exceptions.RequestException as e:
        print(f"Error calling wood_hitter API: {e}")
        return None 

# A simple function which takes the user's coords and returns 12 coords within a set radius
def random_coords_gen(lat, lon, radius_km, num_points=12):
    coords = []
    for _ in range(num_points):
        u = random.uniform(0, 1)
        v = random.uniform(0, 1)
        w = radius_km / 111
        t = 2 * math.pi * v
        x = w * math.sqrt(u) * math.cos(t)
        y = w * math.sqrt(u) * math.sin(t)
        new_lat = lat + x
        new_lon = lon + y / math.cos(math.radians(lat))
        coords.append({"lat": new_lat, "lon": new_lon})
    return coords


# The most popular way of finding the distance between two coordinates on earth
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = (math.sin(dLat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dLon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


# Firebase notification function
def notification(mtitle, mbody):
    with open("token.txt", "r") as f:
        TOKEN = f.read().strip()
    message = messaging.Message(
        notification=messaging.Notification(
            title=mtitle,
            body=mbody
        ),
        token=TOKEN
    )
    try:
        response = messaging.send(message)
        print("Notification sent successfully")
        return response
    except Exception as e:
        print("Failed to send notification: ", e)
        return None


# The main function which hits the AI-API server and returns the data to the front-end server
@app.route('/liveloc', methods=['POST'])
def main():
    req_data = request.get_json()

    coords_to_check = random_coords_gen(float(req_data['lat']), float(req_data['lon']), 5, num_points=5)
    results = []

    for coord in coords_to_check:
        temp_lat = coord['lat']
        temp_lon = coord['lon']

        api_response = wood_ai_server_hitter(
            lat=temp_lat,
            lon=temp_lon,
            age=int(req_data['user_info']['age']),
            asthama_bool=bool(req_data['user_info']['asthama_bool']),
            preg_bool=bool(req_data['user_info']['preg_bool']),
            cardio_bool=bool(req_data['user_info']['cardio_bool']),
            copd_bool=bool(req_data['user_info']['copd_bool']),
            pollen_bool=bool(req_data['user_info']['pollen_bool'])
        )


        point_data = api_response[1]
        # print(point_data)

        intensity = point_data.get('allergen_intensity')
        # v = ",".join(point_data.get('symptoms'))
        # print(v)
        # with open("symptoms.txt", "w") as f:
        #     f.write(f"{v}")
           
        if intensity is not None:
            results.append({
                "lat": temp_lat,
                "lon": temp_lon,
                "allergen_intensity": float(intensity)
            })
    global sorted_results
    sorted_results = sorted(results, key=lambda item: item['allergen_intensity'])
    print("Sorted Results:", sorted_results)
    with open("red.txt", "w") as f:
        f.write(f"{sorted_results[0]}")

    return sorted_results

@app.route('/', methods=['GET'])
def test():
    return "Hi"

@app.route('/token', methods=['POST'])
def all():
    data = request.get_json()
    with open("token.txt", "w") as f:
        f.write(data['token'])
    return "Got the FCM token"


@app.route('/notifier', methods=['POST'])
def loc_checker():
    daaata = request.get_json()
    print("hi")

    if (daaata['lat']) == (sorted_results[0]["lat"]) and (daaata['lon']) == (sorted_results[0]["lon"]):
        symptoms = sorted_results[0]["symptoms"]
        notification("ERROR 404: clean air not found", f"You have entered an area where you are prone to risks such as {symptoms}",)
        
    return 'Done'

@app.route('/store', methods=['POST'])
def database():
    meta_data = request.get_json()
    print(meta_data)
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
