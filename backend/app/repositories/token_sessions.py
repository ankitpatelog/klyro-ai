from redis.asyncio import Redis


def _session_key(session_id: str) -> str:
    return f"auth:session:{session_id}"


async def create_session(
    redis: Redis,
    *,
    session_id: str,
    user_id: str,
    access_hash: str,
    refresh_hash: str,
    expires_in_seconds: int,
) -> None:
    key = _session_key(session_id)
    await redis.hset(key, mapping={
        "user_id": user_id,
        "access_hash": access_hash,
        "refresh_hash": refresh_hash,
    })
    await redis.expire(key, expires_in_seconds)


async def is_access_token_active(redis: Redis, session_id: str, user_id: str, access_hash: str) -> bool:
    session = await redis.hgetall(_session_key(session_id))
    return session.get("user_id") == user_id and session.get("access_hash") == access_hash


async def rotate_session(
    redis: Redis,
    *,
    old_session_id: str,
    old_refresh_hash: str,
    new_session_id: str,
    user_id: str,
    new_access_hash: str,
    new_refresh_hash: str,
    expires_in_seconds: int,
) -> bool:
    """Atomically replace a session only when the presented refresh hash matches."""
    result = await redis.eval(
        """
        local stored_hash = redis.call('HGET', KEYS[1], 'refresh_hash')
        if not stored_hash or stored_hash ~= ARGV[1] then return 0 end
        redis.call('DEL', KEYS[1])
        redis.call('HSET', KEYS[2], 'user_id', ARGV[2], 'access_hash', ARGV[3], 'refresh_hash', ARGV[4])
        redis.call('EXPIRE', KEYS[2], ARGV[5])
        return 1
        """,
        2,
        _session_key(old_session_id),
        _session_key(new_session_id),
        old_refresh_hash,
        user_id,
        new_access_hash,
        new_refresh_hash,
        expires_in_seconds,
    )
    return result == 1


async def delete_session_if_refresh_matches(redis: Redis, session_id: str, refresh_hash: str) -> bool:
    result = await redis.eval(
        """
        local stored_hash = redis.call('HGET', KEYS[1], 'refresh_hash')
        if not stored_hash or stored_hash ~= ARGV[1] then return 0 end
        redis.call('DEL', KEYS[1])
        return 1
        """,
        1,
        _session_key(session_id),
        refresh_hash,
    )
    return result == 1
