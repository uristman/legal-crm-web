import requests
import os
from datetime import datetime

YANDEX_API = "https://cloud-api.yandex.net/v1/disk"

BASE_DIR = "Apps"
APP_DIR = "Apps/LegalCRM"
BACKUP_DIR = "Apps/LegalCRM/backups"


class YandexDisk:
    def __init__(self, token: str):
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

    def _create_folder(self, path):
        r = requests.put(
            f"{YANDEX_API}/resources",
            headers=self.headers,
            params={"path": path}
        )
        return r.status_code in (201, 409)

    def ensure_folders(self):
        self._create_folder(BASE_DIR)
        self._create_folder(APP_DIR)
        self._create_folder(BACKUP_DIR)

    def upload_backup(self, local_path):
        if not os.path.exists(local_path):
            raise Exception("Local database file not found")

        self.ensure_folders()

        filename = f"backup_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.db"
        disk_path = f"{BACKUP_DIR}/{filename}"

        r = self._request(
            "GET",
            f"{YANDEX_API}/resources/upload",
            params={"path": disk_path, "overwrite": "true"}
        )

        upload_url = r.json()["href"]

        with open(local_path, "rb") as f:
            requests.put(upload_url, data=f)

        return filename
