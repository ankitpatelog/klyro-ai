========================================================
1. LOGIN FLOW
========================================================

START
  |
  v
User enters email and password in frontend
  |
  v
Frontend sends POST /auth/login
  |
  v
FastAPI receives email and password
  |
  v
Find user in PostgreSQL using email
  |
  v
Does user exist?
  |
  +---- NO ----> Return 401 INVALID CREDENTIALS
  |                       |
  |                       v
  |                      END
  |
  YES
  |
  v
Verify entered password against stored password hash
  |
  v
Is password correct?
  |
  +---- NO ----> Return 401 INVALID CREDENTIALS
  |                       |
  |                       v
  |                      END
  |
  YES
  |
  v
Generate ACCESS TOKEN (JWT)
  |
  |-- Contains user ID (sub)
  |-- Contains expiry (exp)
  |-- Contains token type (access)
  |-- Contains session ID (sid)
  |
  v
Generate REFRESH TOKEN (random secret)
  |
  |-- Generate unique session ID
  |-- Set refresh token expiry (7 days)
  |
  v
Store refresh session in Redis
  |
  |-- Key: refresh:<session_id>
  |-- Value: user_id + refresh_token_hash
  |-- TTL: 7 days
  |
  v
Send ACCESS TOKEN to frontend
Send REFRESH TOKEN in secure HttpOnly cookie
  |
  v
Frontend stores access token in memory
  |
  v
LOGIN SUCCESS
  |
  v
END








========================================================
2. ACCESS PROTECTED ROUTE
========================================================

START
  |
  v
Frontend wants user profile or protected data
  |
  v
Send request to FastAPI
  |
  |-- GET /users/me
  |-- Authorization: Bearer <access_token>
  |
  v
FastAPI authentication dependency receives request
  |
  v
Extract access token from Authorization header
  |
  v
Decode JWT and verify signature
  |
  v
Is JWT signature valid?
  |
  +---- NO ----> Return 401 UNAUTHORIZED
  |                       |
  |                       v
  |                      END
  |
  YES
  |
  v
Check JWT expiration (exp)
  |
  v
Is access token expired?
  |
  +---- YES ---> Return 401 ACCESS TOKEN EXPIRED
  |                       |
  |                       v
  |                 Frontend calls refresh
  |
  NO
  |
  v
Check token type is "access"
  |
  v
Extract user ID and session ID from JWT
  |
  v
Is session active in Redis?
  |
  |-- Required if immediate logout/revocation
  |-- Skip if using short-lived JWT-only validation
  |
  v
Is user/session valid?
  |
  +---- NO ----> Return 401 UNAUTHORIZED
  |
  YES
  |
  v
Execute protected API
  |
  v
Return requested data to frontend
  |
  v
END







========================================================
3. REFRESH ACCESS TOKEN
========================================================

START
  |
  v
Frontend calls a protected API
  |
  v
Access token expired
  |
  v
FastAPI returns 401
  |
  v
Frontend calls POST /auth/refresh
  |
  |-- Refresh token sent through HttpOnly cookie
  |
  v
FastAPI receives refresh token
  |
  v
Find corresponding session in Redis
  |
  v
Does Redis session exist?
  |
  +---- NO ----> Return 401
  |             Refresh session invalid or logged out
  |                       |
  |                       v
  |                 Redirect to login
  |
  YES
  |
  v
Verify refresh token hash matches stored hash
  |
  v
Is refresh token valid?
  |
  +---- NO ----> Return 401
  |
  YES
  |
  v
Check refresh session expiry
  |
  v
Is refresh session expired?
  |
  +---- YES ---> Delete expired session
  |             Return 401
  |             Redirect to login
  |
  NO
  |
  v
Generate NEW access JWT
  |
  v
Generate NEW refresh token
  |
  v
Atomically rotate refresh token in Redis
  |
  |-- Old refresh token becomes invalid
  |-- Store new refresh token hash
  |-- Preserve remaining session lifetime
  |
  v
Return NEW access token
Set NEW refresh token cookie
  |
  v
Frontend replaces old access token
  |
  v
Frontend retries original protected API
  |
  v
API request succeeds
  |
  v
END












========================================================
4. LOGOUT FLOW
========================================================

START
  |
  v
User clicks logout
  |
  v
Frontend calls POST /auth/logout
  |
  |-- Sends refresh token cookie
  |
  v
FastAPI receives logout request
  |
  v
Identify current session
  |
  v
Delete refresh session from Redis
  |
  v
Session is revoked
  |
  v
Clear refresh token cookie
  |
  v
Frontend clears access token from memory
  |
  v
Frontend redirects to login page
  |
  v
LOGOUT SUCCESS
  |
  v
END










User has logged out
       |
       v
Redis refresh session deleted
       |
       v
Frontend access token cleared
       |
       v
Someone tries to use old refresh token
       |
       v
Redis session not found
       |
       v
Refresh rejected with 401
       |
       v
User must login again