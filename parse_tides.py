"""Parses tide data from the Hydrographic Institute of the Navy (Government of Spain)
and creates JSON files to be consumed by the app
"""
import argparse
import datetime
import requests
import json
import os
import pdfplumber
from io import BytesIO

def main():
    ports = fetch_ports()
    write_ports_file(ports)
    current_year = datetime.datetime.now().year
    coefficients_map = fetch_coefficients(current_year)
    write_coefficients_file(coefficients_map)
    for port in ports:
        for month in range(1, 12 + 1, 1):
            handle_port_month(port, month, current_year, coefficients_map)

def fetch_ports():
    response = requests.get("http://ideihm.covam.es/api-ihm/getmarea?request=getlist&format=json")
    return response.json()["estaciones"]["puertos"]

def write_ports_file(ports):
    ports_json = {
        "ports": list(map(lambda port: {
            "id": port["id"],
            "code": port["code"],
            "name": port["puerto"],
            "lat": port["lat"],
            "lng": port["lon"]
        }, ports))
    }
    write_json(ports_json, "public/ports.json")

def fetch_coefficients(current_year):
    response = requests.get(f"https://armada.defensa.gob.es/ihm/Documentacion/Mareas/docs/coeficientes_{current_year}.pdf")
    coefficients_map = {"coefficients": {}}
    with pdfplumber.open(BytesIO(response.content)) as pdf:
        first_page = pdf.pages[0]
        rows = first_page.extract_table(table_settings={"vertical_strategy": "text", "horizontal_strategy": "text", "snap_tolerance": 4})
        first_semester = False
        for row in rows:
            first_semester = handle_coefficients_pdf_row(row, coefficients_map, current_year, first_semester)
    return coefficients_map

def handle_coefficients_pdf_row(row, coefficients_map, current_year, first_semester):
    if row[0].isnumeric():
        day = int(row[0])
        if day == 1:
            first_semester = not first_semester
        num_traversed_coefficients = 0
        month = 1 if first_semester else 7
        for i in range(1, len(row), 1):
            cell = row[i]
            coefficients = cell.split()
            if (len(coefficients) == 0):
                (num_traversed_coefficients, month) = register_coefficients("0", coefficients_map, current_year, month, day, num_traversed_coefficients)
            else:
                if i == len(row) - 2 and len(coefficients) < 2:
                    if not row[len(row) - 1]:
                        coefficients.append(0)
                    elif not row[len(row) - 3]:
                        coefficients.insert(0, 0)
                for j in range(len(coefficients)):
                    (num_traversed_coefficients, month) = register_coefficients(coefficients[j], coefficients_map, current_year, month, day, num_traversed_coefficients)

    return first_semester

def register_coefficients(coefficient_string, coefficients_map, current_year, month, day, num_traversed_coefficients):
    key = f"{current_year}-{month:02d}-{day:02d}"
    value = float(coefficient_string) if coefficient_string else 0
    if not key in coefficients_map["coefficients"]:
        coefficients_map["coefficients"][key] = [value]
    else:
        coefficients_map["coefficients"][key].append(value)
    num_traversed_coefficients += 1
    if num_traversed_coefficients >= 2:
        num_traversed_coefficients = 0
        month += 1
    return (num_traversed_coefficients, month)

def write_coefficients_file(coefficients_map):
    write_json(coefficients_map, "public/coefficients.json")

def handle_port_month(port, month, year, coefficients_map):
    tides_json = {
        "port_id": port["id"],
        "port_code": port["code"],
        "port_name": port["puerto"],
        "month": month
    }
    data = download_port_month_data(port, month, year)
    build_tides_json_for_port_month(data["mareas"]["datos"]["marea"], tides_json, coefficients_map)
    write_json(tides_json, f"public/tides/{year}/{port['code']}/{month:02d}.json")

def download_port_month_data(port, month, year):
    response = requests.get(f"http://ideihm.covam.es/api-ihm/getmarea?request=gettide&id={port['id']}&format=json&month={year}{month:02d}")
    return response.json()

def build_tides_json_for_port_month(values, tides_json, coefficients_map):
    i = 0
    while i + 2 < len (values):
        increment = build_tides_json_for_port_day(i, values, tides_json, coefficients_map)
        i += increment

def build_tides_json_for_port_day(index, values, tides_json, coefficients_map):
    tides_day = {
        "first_tide": build_tide_json(values[index], coefficients_map["coefficients"][values[index]["fecha"]]),
        "second_tide": build_tide_json(values[index + 1], coefficients_map["coefficients"][values[index + 1]["fecha"]]),
        "third_tide": build_tide_json(values[index + 2], coefficients_map["coefficients"][values[index + 2]["fecha"]])
    }
    increment = 3
    if index + 3 < len(values):
        if values[index + 3]["fecha"] == values[index]["fecha"]:
            tides_day["fourth_tide"] = build_tide_json(values[index + 3], coefficients_map["coefficients"][values[index + 3]["fecha"]])
            increment = 4
    tides_json[values[index]["fecha"]] = tides_day
    return increment

def build_tide_json(values, coefficients):
    return {
        "meters": values["altura"],
        "time": values["hora"],
        "coefficient": coefficients[0] if int(values["hora"].split(":")[0]) < 12 else coefficients[1],
        "high_tide": values["tipo"] == 'pleamar'
    }

def write_json(tides_json, filename):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w") as f:
        json.dump(tides_json, f, separators=(',', ':'))

if __name__ == '__main__':
    main()