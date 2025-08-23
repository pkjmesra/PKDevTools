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

from dotenv import dotenv_values

from PKDevTools.classes.Singleton import SingletonType


class PKEnvironment(metaclass=SingletonType):
    def __init__(self):
        super(PKEnvironment, self).__init__()
        self._load_secrets()

    def _load_secrets(self):
        """Load all secrets from .env.dev file and expose as attributes"""
        self._allSecrets = dotenv_values(".env.dev")

        # Ensure required keys exist with empty defaults
        required_keys = ["GITHUB_TOKEN", "CHAT_ID", "TOKEN", "chat_idADMIN"]
        for key in required_keys:
            if key not in self._allSecrets:
                self._allSecrets[key] = ""

        # Dynamically create attributes for all keys
        for key, value in self._allSecrets.items():
            # Convert key to valid Python identifier if needed
            attr_name = self._sanitize_key(key)
            setattr(self, attr_name, value)

    def _sanitize_key(self, key: str) -> str:
        """Convert environment key to valid Python attribute name"""
        # Replace invalid characters with underscore
        sanitized = "".join([c if c.isalnum() else "_" for c in key])
        # Ensure it doesn't start with number
        if sanitized[0].isdigit():
            sanitized = f"_{sanitized}"
        return sanitized

    def __getattr__(self, name):
        """Handle access to undefined attributes (for new keys added later)"""
        if name in self._allSecrets:
            return self._allSecrets[name]
        raise AttributeError(
            f"'{self.__class__.__name__}' has no attribute '{name}'")

    @property
    def secrets(self):
        """Legacy property returning tuple of main secrets"""
        return (
            self.CHAT_ID,
            self.TOKEN,
            self.chat_idADMIN,
            self.GITHUB_TOKEN,
        )

    @property
    def allSecrets(self):
        """Property returning all secrets as dict"""
        return self._allSecrets

    def refresh(self):
        """Reload secrets from file (for detecting new keys)"""
        self._load_secrets()
