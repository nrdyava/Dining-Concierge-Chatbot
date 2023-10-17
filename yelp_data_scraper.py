from __future__ import print_function
import argparse
import json
import requests
import sys

# Yelp API Key
api_key = 'UOFVPZ0S3_5GHFMM2y-6-fjMEIFqdg_GpsJ3bUm7mwfn3s4lcxYk64INNR6ie48FD8ZwOc-CFigxf-iDGDH_lvPz1zU-UoQTic94CFLNRbd9PIBlBKnpxylA_UcrZXYx'

SEARCH_LIMIT = 50

def list_of_strings_type(arg):
    return arg.split(',')

def fetch_data(cuisines_list, location, num_per_cus):
    unique_restaurant_ids = set()

    restaurant_data = {}

    attributes_to_store = ['id', 'name', 'address', 'coordinates', 'num_reviews', 'rating', 'zip_code']

    url = 'https://api.yelp.com/v3/businesses/search'
    headers = {'Authorization': f'Bearer {api_key}'}

    for cuisine in cuisines_list:
        restaurant_data[cuisine] = []

        for offset in range(0, num_per_cus, SEARCH_LIMIT):
            params = {
                'location': location,
                'categories': cuisine,
                'limit': min(SEARCH_LIMIT, num_per_cus - offset),
                'offset': offset
            }

            response = requests.get(url, headers=headers, params=params)
            data = response.json()

            if 'businesses' in data:
                for restaurant in data['businesses']:
                    restaurant_id = restaurant['id']

                    if restaurant_id not in unique_restaurant_ids:
                        restaurant_details = {}

                        restaurant_details['id'] = restaurant.get('id', '')
                        restaurant_details['name'] = restaurant.get('name', '')
                        if 'location' in restaurant:
                            restaurant_details['address'] = ', '.join(restaurant['location'].get('display_address', []))
                        else:
                            restaurant_details['address'] = ''
                        if 'coordinates' in restaurant:
                            if 'latitude' in restaurant['coordinates'] and 'longitude' in restaurant['coordinates']:
                                restaurant_details['coordinates'] = 'latitude: ' + str(
                                    restaurant['coordinates'].get('latitude', '')) + ', ' + 'longitude: ' + str(
                                    restaurant['coordinates'].get('longitude', ''))
                            else:
                                restaurant_details['coordinates'] = ''
                        else:
                            restaurant_details['coordinates'] = ''
                        restaurant_details['num_reviews'] = restaurant.get('review_count', 0)
                        restaurant_details['rating'] = restaurant.get('rating', 0.0)
                        if 'location' in restaurant:
                            restaurant_details['zip_code'] = restaurant['location'].get('zip_code', '')
                        else:
                            restaurant_details['zip_code'] = ''

                        restaurant_data[cuisine].append(restaurant_details)
                        unique_restaurant_ids.add(restaurant_id)

    return restaurant_data


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='Yelp Restaurant Data Scraper',
        description='Scrapes the restaurant data based on location and cuisine preferences and outputs the data to a specified file',
        epilog='Have a Good Day!'
    )

    parser.add_argument('-q', '--cuisines-list', dest='cuisines_list', default=['Indian'], type=list_of_strings_type,
                        help='Search Cuisines (default: %(default)s)')
    parser.add_argument('-l', '--location', dest='location', default='Manhattan', type=str,
                        help='Search location (default: %(default)s)')
    parser.add_argument('-o', '--output-file', dest='output_file', default='yelp_restaurant_data.json', type=str,
                        help='Output file name (full path, JSON file) (default: %(default)s)')
    parser.add_argument('-n', '--num-per-cus', dest='num_per_cus', default=1000, type=int,
                        help='Number of restarants per cuisine (default: %(default)s)')

    input_values = parser.parse_args()

    try:
        data = fetch_data(input_values.cuisines_list, input_values.location, input_values.num_per_cus)
        print("Fetched data from Yelp API")

        with open(input_values.output_file, "w") as outfile:
            json.dump(data, outfile, indent=2)
        print("Wrote fetched data to {}".format(input_values.output_file))
        print("Data collection ended!")

    except HTTPError as error:
        sys.exit(
            'Encountered HTTP error {0} on {1}:\n {2}\nAbort program.'.format(
                error.code,
                error.url,
                error.read(),
            )
        )

