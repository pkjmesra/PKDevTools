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
from base64 import b64encode
from nacl import encoding, public

class PKGitHubSecretsManager:
    def __init__(self, owner="pkjmesra", repo=None, token=None):
        """
        Initialize GitHub Secrets Manager
        
        Args:
            owner (str): GitHub organization or username (default: pkjmesra)
            repo (str): Repository name (required)
            token (str): GitHub PAT token. If None, uses PKEnvironment().GITHUB_TOKEN
        """
        self.owner = owner
        self.repo = repo
        self.token = token or PKEnvironment().GITHUB_TOKEN
        self.base_url = f"https://api.github.com/repos/{owner}/{repo}"
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        
        if not self.repo:
            raise ValueError("Repository name must be provided")
        if not self.token:
            raise ValueError("GitHub token not found in environment")

    def _get_public_key(self):
        """
        Retrieve the public key for encrypting secrets
        
        Returns:
            dict: Public key data with key_id and key content
        """
        url = f"{self.base_url}/actions/secrets/public-key"
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

    def create_or_update_secret(self, secret_name, secret_value):
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
            response = requests.put(url, json=payload, headers=self.headers)
            
            if response.status_code in [201, 204]:
                print(f"✅ Successfully set secret: {secret_name}")
                return True
            else:
                raise Exception(f"Failed to create/update secret: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"❌ Error setting secret {secret_name}: {str(e)}")
            raise

    def get_secret(self, secret_name):
        """
        Get a repository secret (metadata only - GitHub doesn't return decrypted values)
        
        Args:
            secret_name (str): Name of the secret to retrieve
            
        Returns:
            dict: Secret metadata or None if not found
        """
        url = f"{self.base_url}/actions/secrets/{secret_name}"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 404:
            return None  # Secret doesn't exist
        elif response.status_code != 200:
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
        response = requests.delete(url, headers=self.headers)
        
        if response.status_code in [204, 404]:  # 204=Success, 404=Already deleted
            print(f"✅ Successfully deleted secret: {secret_name}")
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
            print(f"✅ Public key retrieved successfully")
            print(f"   Key ID: {public_key_data['key_id']}")
            print(f"   Key: {public_key_data['key']}")
            
            # Test encryption
            test_secret = "test_value_123"
            encrypted = self._encrypt_nacl_secret(public_key_data["key"], test_secret)
            print(f"✅ Encryption test successful")
            print(f"   Original: {test_secret}")
            print(f"   Encrypted: {encrypted}")
            
            return True
            
        except Exception as e:
            print(f"❌ Encryption test failed: {str(e)}")
            raise

# # Example usage and test
# if __name__ == "__main__":
#     # Initialize with your repository name
#     secrets_manager = PKGitHubSecretsManager(repo="pkbrokers")
    
#     try:
#         # First test the encryption
#         print("🧪 Testing encryption...")
#         secrets_manager.test_encryption()
        
#         # Create or update a secret
#         print("\n🔧 Setting a test secret...")
#         secrets_manager.create_or_update_secret("TEST_SECRET", "my_test_value_123")
        
#         # Get secret metadata
#         print("\n📋 Getting secret info...")
#         secret_info = secrets_manager.get_secret("TEST_SECRET")
#         if secret_info:
#             print(f"   Secret exists: {secret_info['name']} created at {secret_info['created_at']}")
        
#         # List all secrets
#         print("\n📋 Listing all secrets...")
#         all_secrets = secrets_manager.list_secrets()
#         print(f"   Total secrets: {len(all_secrets)}")
#         for secret in all_secrets:
#             print(f"   - {secret['name']}")
            
#     except Exception as e:
#         print(f"❌ Error: {str(e)}")
