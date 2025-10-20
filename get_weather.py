import requests
import pandas as pd

def get_weather_data(city="Yangon"):
    API_KEY = "424c61d0f57ccf937c87cc1f286d2088"
    URL = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"

    response = requests.get(URL)
    data = response.json()

    # Debug: print the response
    print("API Response:", data)

    # Check if valid data returned
    if "main" not in data or "wind" not in data:
        print("⚠️ API returned an error:", data.get("message", "Unknown error"))
        return pd.DataFrame([{
            "city": city,
            "temperature": None,
            "humidity": None,
            "pressure": None,
            "wind_speed": None,
            "weather": None
        }])

    weather = {
        "city": data.get("name", city),
        "temperature": data["main"]["temp"],
        "humidity": data["main"]["humidity"],
        "pressure": data["main"]["pressure"],
        "wind_speed": data["wind"]["speed"],
        "weather": data["weather"][0]["main"]
    }

    return pd.DataFrame([weather])
if __name__ == "__main__":
    df = get_weather_data("Yangon")
    print(df)
