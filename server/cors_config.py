class CORSConfig:
    def __init__(
        self,
        allow_origins=None,
        allow_methods=None,
        allow_headers=None,
        allow_credentials=False,
        max_age=None,
    ):
        self.allow_origins = allow_origins or ["*"]
        self.allow_methods = allow_methods or ["GET", "POST", "OPTIONS"]
        self.allow_headers = allow_headers or ["Content-Type"]
        self.allow_credentials = allow_credentials
        self.max_age = max_age