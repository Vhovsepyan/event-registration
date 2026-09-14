class ResourceNotFoundError(Exception):
    def __init__(self, resource: str, identifier: object) -> None:
        super().__init__(f"{resource} '{identifier}' was not found")
