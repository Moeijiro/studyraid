from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Request, Response

from app.api.deps import CurrentUser, Now, Session, client_ip, require_client_header
from app.core.config import get_settings
from app.core.errors import Unauthorized
from app.core.rate_limit import login_limiter, refresh_limiter, register_limiter
from app.db.uow import commit
from app.schemas.auth import LoginIn, RegisterIn, TokenOut, UserOut
from app.services import auth as auth_service
from app.services.auth import IssuedTokens

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "sr_refresh"


def _set_refresh_cookie(response: Response, tokens: IssuedTokens) -> None:
    settings = get_settings()
    response.set_cookie(
        REFRESH_COOKIE,
        tokens.refresh_token,
        max_age=settings.refresh_token_ttl_days * 86400,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(REFRESH_COOKIE, path="/", httponly=True, secure=get_settings().cookie_secure, samesite="lax")


def _token_out(tokens: IssuedTokens) -> TokenOut:
    return TokenOut(access_token=tokens.access_token, expires_at=tokens.access_expires_at, user=UserOut.model_validate(tokens.user))


@router.post("/register", response_model=TokenOut, status_code=201)
async def register(body: RegisterIn, request: Request, response: Response, session: Session, now: Now) -> TokenOut:
    register_limiter.hit(f"ip:{client_ip(request)}")
    user = await auth_service.register(
        session,
        email=body.email,
        username=body.username,
        display_name=body.display_name,
        password=body.password,
        timezone=body.timezone,
        now=now,
    )
    tokens = await auth_service.start_session(session, user, now, request.headers.get("user-agent"))
    await commit(session)
    _set_refresh_cookie(response, tokens)
    return _token_out(tokens)


@router.post("/login", response_model=TokenOut)
async def login(body: LoginIn, request: Request, response: Response, session: Session, now: Now) -> TokenOut:
    login_limiter.hit(f"ip:{client_ip(request)}")
    login_limiter.hit(f"email:{body.email.lower()}")
    tokens = await auth_service.login(session, body.email, body.password, now, request.headers.get("user-agent"))
    await commit(session)
    _set_refresh_cookie(response, tokens)
    return _token_out(tokens)


@router.post(
    "/refresh",
    response_model=TokenOut,
    dependencies=[Depends(require_client_header)],
    responses={204: {"description": "No session cookie: the visitor is signed out"}},
)
async def refresh(
    request: Request,
    response: Response,
    session: Session,
    now: Now,
    sr_refresh: Annotated[str | None, Cookie()] = None,
) -> TokenOut | Response:
    refresh_limiter.hit(f"ip:{client_ip(request)}")
    if not sr_refresh:
        # Not an error: every signed-out page load asks. 204 keeps consoles clean.
        return Response(status_code=204)
    try:
        tokens = await auth_service.refresh(session, sr_refresh, now, request.headers.get("user-agent"))
    except Unauthorized as exc:
        exc.headers = {"set-cookie": f"{REFRESH_COOKIE}=; Max-Age=0; Path=/; HttpOnly; SameSite=lax"}
        raise
    await commit(session)
    _set_refresh_cookie(response, tokens)
    return _token_out(tokens)


@router.post("/logout", status_code=204, dependencies=[Depends(require_client_header)])
async def logout(response: Response, session: Session, now: Now, sr_refresh: Annotated[str | None, Cookie()] = None) -> Response:
    if sr_refresh:
        await auth_service.logout(session, sr_refresh, now)
        await commit(session)
    response.status_code = 204
    _clear_refresh_cookie(response)
    return response


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)
