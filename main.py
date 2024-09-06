#!/usr/bin/env python

# Downloads counter for tequilaOS
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

    date = str(datetime.now().replace(second=0, microsecond=0))

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

        urlGH = f"https://api.github.com/repos/PixelBuilds-Releases/{codename}/releases"
        deviceresponseGH = requests.get(urlGH)
        
        urlGT = f"https://git.pixelbuilds.org/api/v1/repos/releases/{codename}/releases"
        deviceresponseGT = requests.get(urlGT)

        if deviceresponseGH.status_code != 200 and deviceresponseGT.status_code != 200:
            print(
                f"Failed to get data for device {codename}!\n"
                f"Github responded: {deviceresponseGH.status_code}: {deviceresponseGH.text}"
                f"Gitea responded: {deviceresponseGT.status_code}: {deviceresponseGT.text}"
            )
            skippeddevices.append(codename)
            continue
        elif deviceresponseGH.status_code != 200 and deviceresponseGT.status_code == 200:
            if len(deviceresponseGT.json) == 0:
                skippeddevices.append(f"{codename} - no releases")
                continue
            
            for release in deviceresponseGT:
                for asset in release["assets"]:
                    if not asset["name"].startswith("PixelBuilds_") and not asset[
                        "name"].endswith(".zip"):
                        continue
                    
                    print(f"  adding {asset['download_count']}")
                    deviceDownloads += asset["download_count"]
        else:
            if len(deviceresponseGH.json) == 0 and len(deviceresponseGT) == 0:
                skippeddevices.append(f"{codename} - no releases")
                continue
            
            for deviceresponse in [deviceresponseGH.json, deviceresponseGT.json]:
                for release in deviceresponse:
                    for asset in release["assets"]:
                        if not asset["name"].startswith("PixelBuilds_") and not asset[
                            "name"].endswith(".zip"):
                            continue
                        
                        print(f"  adding {asset['download_count']}")
                        deviceDownloads += asset["download_count"]

        try:
            previous = downloads[codename]
        except KeyError:
            downloads[codename] = 0
        finally:
            previous = downloads[codename]

        downloads[codename] = deviceDownloads

        totalDownloads += downloads[codename]
        totalPrevious += previous

        diff = downloads[codename] - previous

        downloads[codename + "_diff"] = diff

        message += f"\n{codename}: {deviceDownloads}"
        if diff != 0:
            message += f" (+{diff})" if diff > 0 else f" ({diff})"

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

    print(message)

    # Write to JSON
    with open("downloads.json", "w") as f:
        f.write(json.dumps(downloads, indent=4, sort_keys=True))

    # Send telegram message with results
    bot = telegram.Bot(TG_BOT_TOKEN)
    async with bot:
        await bot.send_message(text=message, chat_id=TG_CHAT_ID)

    downloads["_date"] = date

    downloads["_total"] = totalDownloads
    downloads["_total_diff"] = totalDiff


if __name__ == "__main__":
    asyncio.run(main())
