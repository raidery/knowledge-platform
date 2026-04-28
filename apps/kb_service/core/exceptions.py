from fastapi import HTTPException


class KBServiceException(Exception):
    def __init__(self, message: str, code: int = 400):
        self.message = message
        self.code = code


class JobNotFoundError(KBServiceException):
    def __init__(self, job_id: str):
        super().__init__(f"Job {job_id} not found", code=404)


class InvalidStatusError(KBServiceException):
    def __init__(self, message: str):
        super().__init__(message, code=400)


def register_exceptions(app):
    @app.exception_handler(KBServiceException)
    async def kb_exception_handler(request, exc: KBServiceException):
        raise HTTPException(status_code=exc.code, detail=exc.message)