#!/usr/bin/env python

# Downloads counter for PixelBuilds
#
# Counts downloads for each device and sends
# them in telegram message every day

from datetime import datetime
from dotenv import load_dotenv

import asyncio
import json
import os
import requests
import telegram


async def main():
    load_dotenv("config.env")

    TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")
    TG_CHAT_ID = os.environ.get("TG_CHAT_ID")

    date = datetime.now()

    totalDownloads = totalPrevious = diff = 0

    skippeddevices = []

    with open("downloads.json", "r") as f:
        downloads = json.load(f)

    devices_url = "https://raw.githubusercontent.com/PixelBuildsROM/pixelbuilds_devices/main/devices.json"

    response = requests.get(devices_url).json()

    message = f"Download stats as of {date} in last 24 hours:\n"

    for device in response:
        codename = device["codename"]
        manufacturer = device["manufacturer"].lower()

        deviceDownloads = 0

        print(f"Processing {manufacturer}/{codename}...")

        deviceresponse_github = requests.get(
            f"https://api.github.com/repos/PixelBuilds-Releases/{codename}/releases"
        )
        deviceresponse_gitea = requests.get(
            f"https://git.pixelbuilds.org/api/v1/repos/releases/{codename}/releases"
        )

        if (
            deviceresponse_github.status_code != 200
            and deviceresponse_gitea.status_code != 200
        ):
            print(
                f"Failed to get data for device {codename}!\n"
                f"Github responded: {deviceresponse_github.status_code}: {deviceresponse_github.text}"
                f"Gitea responded: {deviceresponse_gitea.status_code}: {deviceresponse_gitea.text}"
            )
            skippeddevices.append(f"{codename} - no data from both GitHub and Gitea")
            continue

        if deviceresponse_github.status_code == 200:
            if len(deviceresponse_github.json()) == 0:
                print(f"No releases on GitHub for {codename}")
                skippeddevices.append(f"{codename} (GitHub) - no releases")
            else:
                print("Counting downloads from GitHub")

                for release in deviceresponse_github.json():
                    for asset in release["assets"]:
                        if not asset["name"].startswith("PixelBuilds_") and not asset[
                            "name"
                        ].endswith(".zip"):
                            continue

                        print(f"\tadding {asset['download_count']} from GitHub")
                        deviceDownloads += asset["download_count"]
        else:
            print(f"Failed to get data from GitHub for {codename}!")
            print(
                f"Response: {deviceresponse_github.status_code}: {deviceresponse_github.text}"
            )
            skippeddevices.append(f"{codename} (GitHub) - no data")

        if deviceresponse_gitea.status_code == 200:
            if len(deviceresponse_gitea.json()) == 0:
                print(f"No releases on Gitea for {codename}")
                skippeddevices.append(f"{codename} (Gitea) - no releases")
            else:
                print("Counting downloads from Gitea")

                for release in deviceresponse_gitea.json():
                    for asset in release["assets"]:
                        if not asset["name"].startswith("PixelBuilds_") and not asset[
                            "name"
                        ].endswith(".zip"):
                            continue

                        print(f"\tadding {asset['download_count']} from Gitea")
                        deviceDownloads += asset["download_count"]
        else:
            print(f"Failed to get data from Gitea for {codename}!")
            print(
                f"Response: {deviceresponse_gitea.status_code}: {deviceresponse_gitea.text}"
            )
            skippeddevices.append(f"{codename} (Gitea) - no data")

        print(f"{deviceDownloads} downloads in total for {codename}")

        try:
            downloads[codename]
        except KeyError:
            downloads[codename] = 0

        previous = downloads[codename]

        downloads[codename] = deviceDownloads

        totalDownloads += downloads[codename]
        totalPrevious += previous

        diff = downloads[codename] - previous

        downloads[codename + "_diff"] = diff

        message += f"\n{codename}: {deviceDownloads}"
        if diff != 0:
            message += f" (+{diff})" if diff > 0 else f" ({diff})"

        print("")

    totalDiff = totalDownloads - totalPrevious

    message += "\n"
    message += "\n"

    if len(skippeddevices) > 0:
        message += "Skipped devices:"

        for codename in skippeddevices:
            message += f"\n{codename}"

        message += "\n"
        message += "\n"

    message += f"Total: {totalDownloads}"
    if totalDiff != 0:
        message += f" (+{totalDiff})" if totalDiff > 0 else f" ({totalDiff})"

    downloads["_date"] = date

    downloads["_total"] = totalDownloads
    downloads["_total_diff"] = totalDiff

    print(message)

    # Write to JSON
    with open("downloads.json", "w") as f:
        f.write(json.dumps(downloads, indent=2, sort_keys=True, default=str))

    # Send telegram message with results
    if TG_BOT_TOKEN and TG_CHAT_ID:
        bot = telegram.Bot(TG_BOT_TOKEN)
        async with bot:
            await bot.send_message(text=message, chat_id=TG_CHAT_ID)


if __name__ == "__main__":
    asyncio.run(main())
