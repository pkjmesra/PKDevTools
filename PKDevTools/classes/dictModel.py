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

class SmartDictModel:
    """An enhanced model with type validation and default values."""
    
    def __init__(self, data_dict=None, **kwargs):
        """
        Initialize with dictionary and/or keyword arguments.
        
        Args:
            data_dict (dict): Dictionary containing attribute values
            **kwargs: Additional attributes as keyword arguments
        """
        # Combine dictionary and keyword arguments
        all_data = {}
        if data_dict and isinstance(data_dict, dict):
            all_data.update(data_dict)
        all_data.update(kwargs)
        
        # Set attributes
        for key, value in all_data.items():
            setattr(self, key, value)
    
    def __getattr__(self, name):
        """Handle missing attributes gracefully."""
        if name in self.__dict__:
            return self.__dict__[name]
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
    
    def __setattr__(self, name, value):
        """Allow setting any attribute."""
        self.__dict__[name] = value
    
    def __contains__(self, key):
        """Check if attribute exists."""
        return key in self.__dict__
    
    def get(self, key, default=None):
        """Get attribute value with default if not exists."""
        return getattr(self, key, default)
    
    def to_dict(self):
        """Convert to dictionary, excluding private attributes."""
        return {k: v for k, v in self.__dict__.items() 
                if not k.startswith('_')}
    
    def __repr__(self):
        """User-friendly representation."""
        attrs = []
        for key, value in self.__dict__.items():
            if not key.startswith('_'):
                # Truncate long values for readability
                value_str = str(value)
                if len(value_str) > 50:
                    value_str = value_str[:47] + '...'
                attrs.append(f"{key}={value_str}")
        return f"{self.__class__.__name__}({', '.join(attrs)})"
