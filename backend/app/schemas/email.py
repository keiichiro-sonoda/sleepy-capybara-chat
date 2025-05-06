from pydantic import BaseModel, EmailStr
from pydantic.config import ConfigDict


class ResendConfirmationRequest(BaseModel):
    """
    Schema for resending email confirmation request.
    Contains the email address of the user who needs a new confirmation link.
    """
    email: EmailStr
