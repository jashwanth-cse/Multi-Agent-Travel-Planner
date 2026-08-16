import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = "xxx"

URL = "https://serpapi.com/search"


def search_hotels(
    city,
    check_in_date,
    check_out_date,
    adults=2,
    children=0,
    currency="INR"
):

    params = {
        "engine": "google_hotels",
        "q": city,
        "check_in_date": check_in_date,
        "check_out_date": check_out_date,
        "adults": adults,
        "children": children,
        "currency": currency,
        "gl": "in",
        "hl": "en",
        "api_key": API_KEY
    }

    response = requests.get(
        URL,
        params=params,
        timeout=30
    )

    print("Status:", response.status_code)

    if response.status_code != 200:
        print(response.text)
        return

    data = response.json()

    # Save complete response so we can inspect
    # the exact SerpApi structure.
    with open(
        "hotel_response.json",
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False
        )

    properties = data.get(
        "properties",
        []
    )

    print(
        f"\nHotels found: {len(properties)}"
    )

    print("=" * 80)

    for i, hotel in enumerate(
        properties,
        start=1
    ):

        name = hotel.get(
            "name",
            "N/A"
        )

        rating = hotel.get(
            "overall_rating"
        )

        reviews = hotel.get(
            "reviews"
        )

        hotel_class = hotel.get(
            "extracted_hotel_class"
        )

        coordinates = hotel.get(
            "gps_coordinates",
            {}
        )

        latitude = coordinates.get(
            "latitude"
        )

        longitude = coordinates.get(
            "longitude"
        )

        rate = hotel.get(
            "rate_per_night",
            {}
        )

        price = rate.get(
            "extracted_lowest"
        )

        currency_price = rate.get(
            "lowest"
        )

        images = hotel.get(
            "images",
            []
        )

        image_url = None

        if images:
            image_url = images[0].get(
                "original_image"
            )

        link = hotel.get(
            "link"
        )

        print(f"\n{i}. {name}")

        print(
            f"   Rating: {rating}"
        )

        print(
            f"   Reviews: {reviews}"
        )

        print(
            f"   Hotel Class: {hotel_class}"
        )

        print(
            f"   Price: {currency_price}"
        )

        print(
            f"   Extracted Price: {price}"
        )

        print(
            f"   Location: "
            f"{latitude}, {longitude}"
        )

        print(
            f"   Image: {image_url}"
        )

        print(
            f"   Website: {link}"
        )

        print("-" * 80)


if __name__ == "__main__":

    search_hotels(
        city="Coimbatore",
        check_in_date="2026-08-20",
        check_out_date="2026-08-22",
        adults=2,
        children=0
    )
