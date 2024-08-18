class CORSConfig:
    """
    Initializes a CORSConfig object.

    Args:
        allow_origins (list[str], optional): List of allowed origins. Defaults to ["*"].
        allow_methods (list[str], optional): List of allowed HTTP methods. Defaults to ["GET", "POST", "OPTIONS"].
        allow_headers (list[str], optional): List of allowed headers. Defaults to ["Content-Type"].
        allow_credentials (bool, optional): Whether to allow credentials. Defaults to False.
        max_age (int, optional): Maximum age of the CORS policy. Defaults to None.
    """
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