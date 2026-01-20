from fastapi import Depends, HTTPException, status
from auth.jwt import verify_token

def require_role(required_role: str):
    def role_checker(user=Depends(verify_token)):
        if user.get("role") != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden"
            )
        return user
    return role_checker
