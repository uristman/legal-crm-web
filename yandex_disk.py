import requests
import os
from datetime import datetime

YANDEX_API = "https://cloud-api.yandex.net/v1/disk"
APP_DIR = "Apps/LegalCRM/backups"


class YandexDisk:
    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"OAuth {token}"
        }

    def _request(self, method, url, **kwargs):
        r = requests.request(method, url, headers=self.headers, **kwargs)
        if r.status_code >= 400:
            raise Exception(r.text)
        return r

    def check_token(self):
        r = self._request("GET", f"{YANDEX_API}/")
        return r.status_code == 200

    def ensure_folder(self):
        r = requests.put(
            f"{YANDEX_API}/resources",
            headers=self.headers,
            params={"path": APP_DIR}
        )
        return r.status_code in (201, 409)

    def upload_backup(self, local_path):
        self.ensure_folder()

        name = f"backup_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.db"
        disk_path = f"{APP_DIR}/{name}"

        r = self._request(
            "GET",
            f"{YANDEX_API}/resources/upload",
            params={"path": disk_path, "overwrite": "true"}
        )

        upload_url = r.json()["href"]

        with open(local_path, "rb") as f:
            requests.put(upload_url, data=f)

        return name
