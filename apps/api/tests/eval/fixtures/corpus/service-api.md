# Account Service API

Version: 3.2

The Account Service exposes REST endpoints under the `/v1` prefix.
All requests must be authenticated with a bearer token.
Bearer tokens remain valid for 30 days after they are issued.
Token revocation takes effect within 60 seconds of the revoke call.
The service accepts at most 100 requests per second per tenant.
Request payloads are limited to 10 megabytes.
