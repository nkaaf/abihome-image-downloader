#!/usr/bin/env python3

import os

import requests
from dotenv import load_dotenv
from lxml import html

# For compatibility with python-dotenv prior to 0.8.0
dotenv_path = ".env"
load_dotenv(dotenv_path)


def main():
    print("Retrieve login tokens...")
    credentials = login()
    print("Collect all galleries...")
    galleries = get_galleries(credentials)
    print("Collect all images from the galleries...")
    galleries = get_images(credentials, galleries)
    print("Download images...")
    download_images(credentials, galleries)


def login() -> str:
    json = {"mail": os.getenv("EMAIL"), "passwort": os.getenv("PASSWORD")}
    response = requests.post('https://www.app.abihome.de/API/session', json=json)
    if response.status_code != 200:
        raise Exception("Programming Error - Login")

    response = response.json()
    if not response["success"]:
        raise Exception("Incorrect credentials!")
    response = response["payload"]["session"]

    print("Successful get login tokens!")
    return f'{response["uid"]}|{response["sectoken"]}|{response["key"]}|{response["key2"]}'


def get_galleries(credentials: str) -> dict:
    headers = {"Cookie": f'Abihome={credentials}'}
    response = requests.get("https://www.app.abihome.de/fotos", headers=headers)
    if response.status_code != 200:
        raise Exception("Programming Error - Get Galleries")

    response = response.content
    tree = html.fromstring(response)
    titles = tree.xpath('//div[@class="album_titel"]/text()')
    gallery_entries = tree.xpath('//div[contains(@class, "one_gallery") and contains(@class, "entries")]')

    galleries = {}
    i = 0
    for entry in gallery_entries:
        print(f'Found gallery: {titles[i]}')
        galleries[entry.attrib["id"].split("entry", 1)[1]] = {"title": titles[i]}
        i += 1
    return galleries


def get_images(credentials: str, galleries: dict) -> dict:
    headers = {"Cookie": f'Abihome={credentials}'}
    for gallery_id in galleries:
        galleries[gallery_id]["images"] = []

        page = 0
        while True:
            response = requests.post(
                f'https://www.app.abihome.de/ajax.php?aktion=load_fotos&id={gallery_id}&page={page}',
                headers=headers)
            if response.status_code != 200:
                raise Exception("Programming Error - Get Images")
            response = response.json()["payload"]["message"]
            if response == "":
                print(
                    f"Found {len(galleries[gallery_id]['images'])} images in gallery '{galleries[gallery_id]['title']}'")
                break

            tree = html.fromstring(response)
            images = tree.xpath('//div[@class="foto_quader"]')

            for image in images:
                galleries[gallery_id]["images"].append(image.attrib["id"].split("foto", 1)[1])

            page += 1

    return galleries


def download_images(credentials: str, galleries: dict):
    realpath = os.path.realpath(__file__)
    images_dir = os.path.join(os.path.dirname(realpath), "images")
    headers = {"Cookie": f'Abihome={credentials}'}

    for gallery_id in galleries:
        gallery_path = os.path.join(images_dir, galleries[gallery_id]["title"])
        try:
            os.makedirs(gallery_path, exist_ok=True)
        except OSError:
            raise Exception("Creation of directory {} failed".format(gallery_path))

        print(f"Download images from gallery '{galleries[gallery_id]['title']}'")
        for image_id in galleries[gallery_id]["images"]:
            response = requests.get("https://www.app.abihome.de/file_load.php?id={}".format(image_id), headers=headers)
            if response.status_code != 200:
                raise Exception("Programming Error - Download Images")
            with open(os.path.join(gallery_path, f'{image_id}.jpeg'), "wb") as f:
                f.write(response.content)

    print("Downloaded all images!")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Keyboard Interrupt occurred. Exiting...")
