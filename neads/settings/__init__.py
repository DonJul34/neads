from .base import *
import os

# Determine which settings to use based on environment
if os.environ.get('DJANGO_ENV') == 'production':
    from .prod import *
else:
    from .dev import * 