#!/usr/bin/env python3

#   Copyright 2024 Niklas Kaaf <nkaaf@protonmail.com>
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

"""
Module to download images from the Platform "Abihome". More information can be found on the
GitHub repo: https://github.com/nkaaf/abihome-image-downloader
"""

import os

import requests
from dotenv import load_dotenv
from lxml import html

# For compatibility with python-dotenv prior to 0.8.0
DOTENV_PATH = ".env"
load_dotenv(DOTENV_PATH)


def main() -> None:
    """Main function. Controls the program process."""
    print("Retrieve login tokens...")
    authentication_token = login()
    print("Collect all galleries...")
    galleries = get_galleries(authentication_token)
    print("Collect all images from the galleries...")
    galleries = get_images(authentication_token, galleries)
    print("Download images...")
    download_images(authentication_token, galleries)


def login() -> str:
    """
    Retrieving the login token.

    :returns: login token which can be used for further requests.
    :raises AssertionError: if the server returns something unexpected.
    :raises ValueError: if the login credentials are incorrect.
    """
    json = {"mail": os.getenv("EMAIL"), "passwort": os.getenv("PASSWORD")}
    response = requests.post("https://www.app.abihome.de/API/session", json=json)
    if response.status_code != 200:
        raise AssertionError(
            "Something went wrong while retrieving the authentication token."
        )

    response = response.json()
    if not response["success"]:
        raise ValueError("Incorrect credentials!")
    response = response["payload"]["session"]

    print("Successful get login tokens!")
    return (
        f'{response["uid"]}|{response["sectoken"]}|{response["key"]}|{response["key2"]}'
    )


def get_galleries(authentication_token: str) -> dict:
    """
    Retrieving all galleries from the Abihome portal.

    :param authentication_token: Authentication Token.
    :returns: Dictionary containing all gallery titles.
    :raises AssertionError: if the server returns something unexpected.
    """
    headers = {"Cookie": f"Abihome={authentication_token}"}
    response = requests.get("https://www.app.abihome.de/fotos", headers=headers)
    if response.status_code != 200:
        raise AssertionError("Something went wrong while retrieving the galleries.")
    response = response.content
    tree = html.fromstring(response)
    titles = tree.xpath('//div[@class="album_titel"]/text()')
    gallery_entries = tree.xpath(
        '//div[contains(@class, "one_gallery") and contains(@class, "entries")]'
    )

    galleries = {}
    i = 0
    for entry in gallery_entries:
        print(f"Found gallery: {titles[i]}")
        galleries[entry.attrib["id"].split("entry", 1)[1]] = {"title": titles[i]}
        i += 1
    return galleries


def get_images(authentication_token: str, galleries: dict) -> dict:
    """
    Retrieving all images from the Abihome portal.

    :param authentication_token: Authentication Token.
    :param galleries: Dictionary of all galleries.
    :return: Dictionary of all images which are contained in the galleries.
    :raises AssertionError: if the server returns something unexpected.
    """
    headers = {"Cookie": f"Abihome={authentication_token}"}
    for gallery_id in galleries:
        galleries[gallery_id]["images"] = []

        page = 0
        while True:
            response = requests.post(
                f"https://www.app.abihome.de/ajax.php?"
                f"aktion=load_fotos&id={gallery_id}&page={page}",
                headers=headers,
            )
            if response.status_code != 200:
                raise AssertionError(
                    "Something went wrong while retrieving the images."
                )
            response = response.json()["payload"]["message"]
            if response == "":
                print(
                    f"Found {len(galleries[gallery_id]['images'])} images in gallery "
                    f"'{galleries[gallery_id]['title']}'"
                )
                break

            tree = html.fromstring(response)
            images = tree.xpath('//div[@class="foto_quader"]')

            for image in images:
                galleries[gallery_id]["images"].append(
                    image.attrib["id"].split("foto", 1)[1]
                )

            page += 1

    return galleries


def download_images(authentication_token: str, galleries: dict) -> None:
    """
    Downloading all images from the Abihome portal.

    :param authentication_token: Authentication token.
    :param galleries: Galleries including their pictures.
    :raises AssertionError: if the server returns something unexpected.
    :raises OSError: if the dictionary cannot be created.
    """
    realpath = os.path.realpath(__file__)
    images_dir = os.path.join(os.path.dirname(realpath), "images")
    headers = {"Cookie": f"Abihome={authentication_token}"}

    for gallery_id in galleries:
        gallery_path = os.path.join(images_dir, galleries[gallery_id]["title"])
        try:
            os.makedirs(gallery_path, exist_ok=True)
        except OSError as e:
            raise OSError(f"Creation of directory {gallery_path} failed") from e

        print(f"Download images from gallery '{galleries[gallery_id]['title']}'")
        for image_id in galleries[gallery_id]["images"]:
            response = requests.get(
                f"https://www.app.abihome.de/file_load.php?id={image_id}",
                headers=headers,
            )
            if response.status_code != 200:
                raise AssertionError(
                    "Something went wrong while downloading the images."
                )
            with open(os.path.join(gallery_path, f"{image_id}.jpeg"), "wb") as f:
                f.write(response.content)

    print("Downloaded all images!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Keyboard Interrupt occurred. Exiting...")
