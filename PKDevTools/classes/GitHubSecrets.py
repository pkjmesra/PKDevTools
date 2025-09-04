"""
The MIT License (MIT)

Copyright (c) 2023 pkjmesra

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

"""

import requests
from PKDevTools.classes.Environment import PKEnvironment
from PKDevTools.classes.log import default_logger
from base64 import b64encode
from nacl import encoding, public

class PKGitHubSecretsManager:
    def __init__(self, owner="pkjmesra", repo=None, token=None):
        """
        Initialize GitHub Secrets Manager
        
        Args:
            owner (str): GitHub organization or username (default: pkjmesra)
            repo (str): Repository name (required)
            token (str): GitHub PAT token. If None, uses PKEnvironment().CI_PAT
        """
        self.owner = owner
        self.repo = repo
        self.token = token or PKEnvironment().CI_PAT
        self.base_url = f"https://api.github.com/repos/{owner}/{repo}"
        self.headers = None
        self._update_headers()
        if not self.repo:
            raise ValueError("Repository name must be provided")
        if not self.token:
            raise ValueError("GitHub token not found in environment")

    def _update_headers(self):
        default_logger().info(f"GITHUB-MANAGER: Repo:{self.repo}, token:{len(self.token)}, CI_PAT: {len(PKEnvironment().CI_PAT)}")
        self.headers = {
            "Authorization": f"token {self.token or PKEnvironment().CI_PAT}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        
    def _get_public_key(self):
        """
        Retrieve the public key for encrypting secrets
        
        Returns:
            dict: Public key data with key_id and key content
        """
        url = f"{self.base_url}/actions/secrets/public-key"
        self._update_headers()
        response = requests.get(url, headers=self.headers)
        
        if response.status_code != 200:
            raise Exception(f"Failed to get public key: {response.status_code} - {response.text}")
        
        return response.json()

    def _encrypt_nacl_secret(self, public_key: str, secret_value: str) -> str:
        """
        Encrypt a secret value using the repository's public key.
        Encrypt a Unicode string using the public key.
        
        Args:
            public_key (str): Base64 encoded Public key from GitHub API
            secret_value (str): Plain text secret value to encrypt
            
        Returns:
            str: Base64 encoded encrypted secret. Encrypts the secret using 
            the PyNaCl library
        """
        public_key = public.PublicKey(public_key.encode("utf-8"), encoding.Base64Encoder())
        sealed_box = public.SealedBox(public_key)
        encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
        return b64encode(encrypted).decode("utf-8")

    def create_or_update_secret(self, secret_name, secret_value, retrial=False):
        """
        Create or update a repository secret
        
        Args:
            secret_name (str): Name of the secret
            secret_value (str): Plain text value of the secret
            
        Returns:
            bool: True if successful
        """
        try:
            # Get public key for encryption
            public_key_data = self._get_public_key()
            
            # Encrypt the secret value
            encrypted_value = self._encrypt_nacl_secret(public_key_data["key"], secret_value)
            
            # Prepare the request payload
            payload = {
                "encrypted_value": encrypted_value,
                "key_id": public_key_data['key_id']
            }
            
            # Create or update the secret
            url = f"{self.base_url}/actions/secrets/{secret_name}"
            self._update_headers()
            response = requests.put(url, json=payload, headers=self.headers)
            
            if response.status_code in [201, 204]:
                default_logger().info(f"✅ Successfully set secret: {secret_name}")
                return True
            else:
                if not retrial:
                    self.create_or_update_secret(secret_name=secret_name, secret_value=secret_value, retrial=True)
                else:
                    raise Exception(f"Failed to create/update secret: {response.status_code} - {response.text}")
                
        except Exception as e:
            if not retrial:
                    self.create_or_update_secret(secret_name=secret_name, secret_value=secret_value, retrial=True)
            else:
                default_logger().error(f"❌ Error setting secret {secret_name}: {str(e)}")
            raise

    def get_secret(self, secret_name, retrial=False):
        """
        Get a repository secret (metadata only - GitHub doesn't return decrypted values)
        
        Args:
            secret_name (str): Name of the secret to retrieve
            
        Returns:
            dict: Secret metadata or None if not found
        """
        url = f"{self.base_url}/actions/secrets/{secret_name}"
        self._update_headers()
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 404:
            return None  # Secret doesn't exist
        elif response.status_code != 200:
            if not retrial:
                return self.get_secret(secret_name=secret_name, retrial=True)
            raise Exception(f"Failed to get secret: {response.status_code} - {response.text}")
        
        return response.json()

    def delete_secret(self, secret_name):
        """
        Delete a repository secret
        
        Args:
            secret_name (str): Name of the secret to delete
            
        Returns:
            bool: True if successful
        """
        url = f"{self.base_url}/actions/secrets/{secret_name}"
        self._update_headers()
        response = requests.delete(url, headers=self.headers)
        
        if response.status_code in [204, 404]:  # 204=Success, 404=Already deleted
            default_logger().info(f"✅ Successfully deleted secret: {secret_name}")
            return True
        else:
            raise Exception(f"Failed to delete secret: {response.status_code} - {response.text}")

    def list_secrets(self):
        """
        List all repository secrets
        
        Returns:
            list: List of secret metadata objects
        """
        url = f"{self.base_url}/actions/secrets"
        secrets = []
        page = 1
        self._update_headers()
        while True:
            response = requests.get(url, headers=self.headers, params={"page": page, "per_page": 100})
            
            if response.status_code != 200:
                raise Exception(f"Failed to list secrets: {response.status_code} - {response.text}")
            
            data = response.json()
            secrets.extend(data['secrets'])
            
            if 'next' not in response.links:
                break
                
            page += 1
        
        return secrets

    def test_encryption(self):
        """
        Test the encryption process with the repository's public key
        """
        try:
            public_key_data = self._get_public_key()
            default_logger().info(f"✅ Public key retrieved successfully")
            default_logger().debug(f"   Key ID: {public_key_data['key_id']}")
            default_logger().debug(f"   Key: {public_key_data['key']}")
            
            # Test encryption
            test_secret = "test_value_123"
            encrypted = self._encrypt_nacl_secret(public_key_data["key"], test_secret)
            default_logger().info(f"✅ Encryption test successful")
            default_logger().debug(f"   Original: {test_secret}")
            default_logger().debug(f"   Encrypted: {encrypted}")
            
            return True
            
        except Exception as e:
            msg = f"❌ Encryption test failed: {str(e)}"
            default_logger().error(msg)
            return False
