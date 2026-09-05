# ADR-003: Use JWT access tokens and rotating opaque refresh tokens

- Status: Accepted
- Date: 2026-09-06

## Context

RideFlow needs short-lived authorization credentials, durable sessions, immediate user deactivation, replay protection, and support for browser and non-browser clients.

## Decision

Issue HS256 JWT access tokens with subject, role, type, issuer, audience, unique ID, issued time, and expiration. Validate the signature and registered claims, then load the user from PostgreSQL before authorizing. Access tokens expire after 15 minutes by default.

Generate refresh tokens from 64 random URL-safe bytes. Persist only SHA-256 digests. Every refresh locks and revokes the presented row, then creates a child in the same family. Reuse of a revoked token revokes active family members. Browser clients receive refresh tokens in `HttpOnly`, `SameSite=Lax` cookies; API clients may use the response/body form.

Passwords use Argon2 through `pwdlib`. Public registration supports riders and drivers but never administrators.

## Consequences

Most requests require a user lookup, trading some performance for immediate deactivation and authoritative roles. Token-family rows require retention and eventual cleanup. HS256 requires careful shared-secret management; production configuration rejects the repository's local-only default. If independently deployed services later need verification without sharing a signing secret, asymmetric signing can replace HS256 behind the token module.
