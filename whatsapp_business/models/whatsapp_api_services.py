from odoo import api, fields, models, _
import requests
import logging
from typing import Dict, Optional
from odoo.exceptions import UserError

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
API_VERSION = "v23.0"
DEFAULT_URL = "https://graph.facebook.com"

class WhatsappServiceAPI(models.AbstractModel):
    _name = 'whatsapp.api.services'
    _description = 'Whatsapp Services'

    def _build_url(self, url: str) -> str:
        """Helper to build the full API URL."""
        return f"{DEFAULT_URL}/{API_VERSION}/{url}"

    def _log_and_raise(self, error_text: str, log_instance, message_loging=False):
        """Helper to log error and optionally raise UserError."""
        logging.error(error_text)
        log_instance.sudo().create({'name': "API Error", "error_msg": error_text})
        self.env.cr.commit()
        if not message_loging:
            raise UserError(_("API error occurred: Please check API Log."))

    def send_request(self, url: str, body=False, headers=False, files=False, data=False, params=False, message_loging=False):
        """
        Sends a POST request to the specified Whatsapp API endpoint.
        """
        full_url = self._build_url(url)
        logging.info(f"Sending POST request to {full_url}")
        log_instance = self.env['whatsapp.api.log']
        try:
            response = requests.post(full_url, json=body, headers=headers, params=params, data=data, files=files, timeout=30)
            response.raise_for_status()
            logging.info(f"Request successful: {response.status_code}")
            return response.json()
        except requests.exceptions.HTTPError as e:
            error_text = f"HTTP error occurred: {e.response.status_code} - {e.response.text}"
            self._log_and_raise(error_text, log_instance, message_loging)
        return None

    def get_request(self, url: str, headers=False, params=False, response_only=False, endpoint_include=False):
        """
        Sends a GET request to the specified Whatsapp API endpoint.
        """
        full_url = self._build_url(url)
        logging.info(f"Sending GET request to {full_url}")
        log_instance = self.env['whatsapp.api.log']
        try:
            if endpoint_include:
                full_url = url
            response = requests.get(full_url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            logging.info(f"Request successful: {response.status_code}")
            return response if response_only else response.json()
        except requests.exceptions.HTTPError as e:
            error_text = f"HTTP error occurred: {e.response.status_code} - {e.response.text}"
            self._log_and_raise(error_text, log_instance)
        return None

    def delete_request(self, url: str, headers: Dict) -> Optional[Dict]:
        """
        Sends a DELETE request to the specified Whatsapp API endpoint.
        """
        full_url = self._build_url(url)
        logging.info(f"Sending DELETE request to {full_url}")
        log_instance = self.env['whatsapp.api.log']
        try:
            response = requests.delete(full_url, headers=headers, timeout=30)
            response.raise_for_status()
            logging.info(f"Request successful: {response.status_code}")
            return response.json()
        except requests.exceptions.HTTPError as e:
            error_text = f"HTTP error occurred: {e.response.status_code} - {e.response.text}"
            self._log_and_raise(error_text, log_instance)
        return None
