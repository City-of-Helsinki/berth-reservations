import base64
import hashlib
import hmac
import json
from email.utils import formatdate
from os import path
from typing import Dict, List

import requests

from berth_reservations import settings
from leases.models import BerthLease, WinterStorageLease

from ..enums import ContractStatus
from ..models import (
    BerthContract,
    VismaBerthContract,
    VismaContract,
    VismaWinterStorageContract,
    WinterStorageContract,
)
from .base import ContractService

VISMASIGN_CLIENT_IDENTIFIER = "VISMASIGN_CLIENT_IDENTIFIER"
VISMASIGN_SECRET = "VISMASIGN_SECRET"
VISMASIGN_API_URL = "VISMASIGN_API_URL"
VISMASIGN_TEST_SSN = "VISMASIGN_TEST_SSN"


class VismaContractService(ContractService):
    api_url: str
    client_identifier: str
    secret: str

    def __init__(self, **kwargs):
        if "config" in kwargs:
            self.config = kwargs.get("config")

        self.api_url = self.config.get(VISMASIGN_API_URL).rstrip("/")
        self.client_identifier = self.config.get(VISMASIGN_CLIENT_IDENTIFIER)
        self.secret = self.config.get(VISMASIGN_SECRET)
        self.test_ssn = self.config.get(VISMASIGN_TEST_SSN)

    def create_berth_contract(self, lease: BerthLease) -> BerthContract:
        document_name = f"berth_contract_{lease.id}"
        document_id = self._create_document(document_name)

        if lease.application is not None:
            language = lease.application.language or settings.LANGUAGE_CODE
        else:
            language = settings.LANGUAGE_CODE

        # FIXME: No contract files exist yet for berth contracts.
        file_relative_path = f"../files/berth_contracts/berth_contract_{language}.pdf"
        file_path = path.join(path.abspath(path.dirname(__file__)), file_relative_path)
        self._add_file_to_document(document_id, file_path)

        invitation_id, passphrase = self._create_invitation(document_id)

        return VismaBerthContract.objects.create(
            document_id=document_id,
            invitation_id=invitation_id,
            passphrase=passphrase,
            lease=lease,
        )

    def create_winter_storage_contract(
        self, lease: WinterStorageLease
    ) -> WinterStorageContract:
        document_name = f"winter_storage_contract_{lease.id}"
        document_id = self._create_document(document_name)

        if lease.application is not None:
            language = lease.application.language or settings.LANGUAGE_CODE
        else:
            language = settings.LANGUAGE_CODE

        file_relative_path = (
            f"../files/winter_storage_contracts/winter_storage_contract_{language}.pdf"
        )
        file_path = path.join(path.abspath(path.dirname(__file__)), file_relative_path)
        self._add_file_to_document(document_id, file_path)

        invitation_id, passphrase = self._create_invitation(document_id)

        return VismaWinterStorageContract.objects.create(
            document_id=document_id,
            invitation_id=invitation_id,
            passphrase=passphrase,
            lease=lease,
        )

    def update_and_get_contract_status(self, contract: VismaContract) -> ContractStatus:
        r = self._make_request(f"/api/v1/document/{contract.document_id}", "GET")
        status = ContractStatus(r.json()["status"])
        contract.status = status
        contract.save()
        return status

    def get_auth_methods(self) -> List[Dict]:
        r = self._make_request("/api/v1/auth/methods", "GET")
        return r.json()["methods"]

    def fulfill_contract(
        self, contract: VismaContract, auth_service: str, return_url: str,
    ) -> str:
        payload = {"returnUrl": return_url, "authService": auth_service}
        if self.test_ssn:
            payload["identifier"] = self.test_ssn
        r = self._make_request(
            f"/api/v1/invitation/{contract.invitation_id}/signature",
            "POST",
            self._json_to_bytes(payload),
        )
        return r.headers["Location"]

    def get_document(self, contract: VismaContract) -> bytes:
        r = self._make_request(
            f"/api/v1/document/{contract.document_id}/files/0", "GET",
        )
        return r.content

    @staticmethod
    def get_config_template():
        return {
            VISMASIGN_CLIENT_IDENTIFIER: str,
            VISMASIGN_SECRET: str,
            VISMASIGN_API_URL: str,
            VISMASIGN_TEST_SSN: str,
        }

    def _create_document(self, name: str) -> str:
        payload = self._json_to_bytes({"document": {"name": name}})
        r = self._make_request("/api/v1/document/", "POST", payload)
        document_id = r.headers["Location"].split("/")[-1]
        return document_id

    def _add_file_to_document(self, document_id, file_path) -> None:
        with open(file_path, "rb") as file:
            file_data = file.read()
        self._make_request(
            f"/api/v1/document/{document_id}/files",
            "POST",
            file_data,
            "application/pdf",
        )

    def _create_invitation(self, document_id: str) -> (str, str):
        payload = self._json_to_bytes([{"signature_type": "strong"}])

        r = self._make_request(
            f"/api/v1/document/{document_id}/invitations", "POST", payload
        )

        response_json = r.json()[0]
        return response_json["uuid"], response_json["passphrase"]

    def _make_request(
        self,
        path: str,
        method: str,
        payload: bytes = b"",
        content_type: str = "application/json",
    ) -> requests.Response:
        url = f"{self.api_url}{path}"
        headers = self._get_headers(path, method, payload, content_type)

        if payload is None:
            r = requests.request(method, url=url, headers=headers)
        else:
            r = requests.request(method, url=url, data=payload, headers=headers)

        r.raise_for_status()

        return r

    def _get_headers(
        self, path: str, method: str, payload: bytes, content_type: str,
    ) -> Dict[str, str]:
        # date format: RFC 2822
        date = formatdate()

        # content_md5 format: base64(md5(body)), RFC 1864
        content_md5 = hashlib.md5(payload).digest()  # md5 json body (as bytes)
        content_md5 = base64.b64encode(content_md5).decode("utf8")  # base64 string

        def get_mac():
            mac_string = "\n".join([method, content_md5, content_type, date, path])
            mac_string_bytes = mac_string.encode("utf8")
            secret_bytes = base64.b64decode(self.secret)
            mac = hmac.new(secret_bytes, mac_string_bytes, hashlib.sha512).digest()
            return base64.b64encode(mac).decode("utf8")

        return {
            "Date": date,
            "Content-MD5": content_md5,
            "Content-Type": content_type,
            "Authorization": f"Onnistuu {self.client_identifier}:{get_mac()}",
        }

    @staticmethod
    def _json_to_bytes(data):
        return json.dumps(data).encode("utf8")
