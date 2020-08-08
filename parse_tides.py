"""Parses tide data from the Hydrographic Institute of the Navy (Government of Spain)
and creates JSON files to be consumed by the app
"""
import argparse
import datetime
import requests
import json
import os

PORTS = [
    "aguarda",
    "algeciras",
    "arinaga",
    "arrecife",
    "aviles",
    "ayamonte",
    "baiona",
    "barbate",
    "bilbao",
    "bonanza",
    "burela",
    "cadiz",
    "camarinas",
    "carino",
    "cedeira",
    "ceuta",
    "chipiona",
    "cillero",
    "conil",
    "coruna",
    "cudillero",
    "elpuertosantamaria",
    "ferrol",
    "fisterra",
    "foz",
    "gallineras",
    "gijon",
    "granadilla",
    "islacanela",
    "islacristina",
    "lacarraca",
    "langosteira",
    "lisboa",
    "llanes",
    "loscristianos",
    "losgigantes",
    "malpica",
    "marin",
    "mazagon",
    "morrojable",
    "navia",
    "pasajes",
    "pasitoblanco",
    "portosin",
    "ptocruz",
    "ptolaestaca",
    "ptolaluz",
    "ptolasnieves",
    "ptorosario",
    "puntaumbria",
    "ribadeo",
    "ribadesella",
    "rota",
    "sada",
    "sancibrao",
    "sanctipetri",
    "sansebastiangomera",
    "santander",
    "santauxia",
    "sanxenxo",
    "sevilla",
    "sotogrande",
    "stacruzpalma",
    "stacruztenerife",
    "tanger",
    "tapia",
    "tarifa",
    "vigo",
    "vilagarcia"
]

COEFFICIENTS_FILE = "coefficients.json"

def main():
    coefficients = load_coefficients()
    current_year = datetime.datetime.now().year
    for port in PORTS:
        for month in range(1, 12 + 1, 1):
            handle_port_month(port, month, current_year, coefficients)

def load_coefficients():
    with open(COEFFICIENTS_FILE) as f:
        return json.load(f)["coefficients"]

def handle_port_month(port, month, year, coefficients):
    tides_json = {
        "port": port,
        "month": month
    }
    data = download_port_month_data(port, month, year)
    hours = data["hours"]
    values = data["values"]
    build_tides_json_for_port_month(port, month, year, hours, values, coefficients, tides_json)
    write_json(tides_json, f"tides/{year}/{port}/{month:02d}.json")

def download_port_month_data(port, month, year):
    response = requests.get(f"https://armada.defensa.gob.es/ihm/Documentacion/Mareas//json/{year}/{port}/{port}_mes_{month:02d}.json")
    return response.json()

def build_tides_json_for_port_month(port, month, year, hours, values, coefficients, tides_json):
    i = 0
    while i + 2 < len(hours):
        increment = build_tides_json_for_port_day(port, i, month, year, hours, values, coefficients, tides_json)
        i += increment

def build_tides_json_for_port_day(port, index, month, year, hours, values, coefficients, tides_json):
    first_tide_time_parts = hours[index].split(" ")
    day = first_tide_time_parts[0]
    second_tide_time_parts = hours[index + 1].split(" ")
    third_tide_time_parts = hours[index + 2].split(" ")
    tides_day = {
        "first_tide": build_tide_json(values[index], first_tide_time_parts[1], day, coefficients),
        "second_tide": build_tide_json(values[index + 1], second_tide_time_parts[1], day, coefficients),
        "third_tide": build_tide_json(values[index + 2], third_tide_time_parts[1], day, coefficients)
    }
    increment = 3
    if index + 3 < len(hours):
        fourth_tide_time_parts = hours[index + 3].split(" ")
        if first_tide_time_parts[0] == fourth_tide_time_parts[0]:
            tides_day["fourth_tide"] = build_tide_json(values[index + 3], fourth_tide_time_parts[1], day, coefficients)
            increment = 4 
    tides_json[day] = tides_day
    return increment

def build_tide_json(meters, time, day, coefficients):
    return {
        "meters": meters,
        "time": time,
        "coefficient": coefficients[day][0] if int(time.split(":")[0]) < 12 else coefficients[day][1]
    }

def write_json(tides_json, filename):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w") as f:
        json.dump(tides_json, f)

if __name__ == '__main__':
    main()