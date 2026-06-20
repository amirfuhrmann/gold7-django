# SMS & Phone Verification — Plan

> Status: **not implemented**. This is a design stub for the future SMS milestone.
> Today, `phone` is a login identifier and `User.phone_verified` exists but is
> never set to `True`. Nothing depends on verification yet.

## Goal

Prove a user controls a phone number before we trust it for:

- SMS-based notifications / alerts
- (optionally) SMS as a login or 2FA factor

A phone number is "trusted" when `User.phone_verified == True`.

## Building blocks

### 1. SMS backend abstraction

A pluggable backend selected by a `SMS_BACKEND` setting, mirroring Django's email
backends so dev and prod differ only by config.

- `core/sms/base.py` — `BaseSMSBackend.send(to: str, body: str)`
- `core/sms/console.py` — `ConsoleSMSBackend` (dev: prints to logs) — **default**
- `core/sms/twilio.py` — `TwilioSMSBackend` (prod) using `twilio` SDK

Settings:

```python
SMS_BACKEND = env("SMS_BACKEND", default="core.sms.console.ConsoleSMSBackend")
TWILIO_ACCOUNT_SID = env("TWILIO_ACCOUNT_SID", default="")
TWILIO_AUTH_TOKEN  = env("TWILIO_AUTH_TOKEN", default="")
TWILIO_FROM_NUMBER = env("TWILIO_FROM_NUMBER", default="")
```

Add `twilio` to `requirements/base.txt` only when this lands.

### 2. `PhoneVerification` model (`core/models.py`)

Tracks issued codes with expiry and rate limiting.

| Field         | Type            | Notes                                  |
| ------------- | --------------- | -------------------------------------- |
| `user`        | FK → User       | `related_name="phone_verifications"`   |
| `phone`       | CharField       | number the code was sent to            |
| `code`        | CharField(6)    | numeric one-time code                  |
| `created_at`  | DateTime        | `auto_now_add`                         |
| `expires_at`  | DateTime        | now + `PHONE_VERIFICATION_EXPIRY_MINUTES` |
| `verified_at` | DateTime, null  | set when the code is accepted          |

Helpers: `is_expired`, `is_verified`, `can_send_code(phone)` (rate limit),
`generate_code()` (zero-padded random N digits).

Settings:

```python
PHONE_VERIFICATION_CODE_LENGTH = 6
PHONE_VERIFICATION_EXPIRY_MINUTES = 10
PHONE_VERIFICATION_RATE_LIMIT_HOURS = 1
PHONE_VERIFICATION_RATE_LIMIT_MAX_ATTEMPTS = 5
```

### 3. Verification flow (on the profile page)

1. User saves a phone number → `phone_verified` is reset to `False`.
2. Profile shows an **"Unverified — send code"** action next to the number.
3. POST request:
   - check `PhoneVerification.can_send_code(phone)` (rate limit),
   - create a `PhoneVerification`, send the code via the SMS backend.
4. User enters the 6-digit code:
   - match the newest unexpired, unverified row for that phone,
   - on success set `verified_at`, set `User.phone_verified = True`,
   - show a **"Verified"** badge.

Forms (to add to `core/forms.py`): `PhoneVerificationRequestForm` (phone) and
`PhoneVerificationCodeForm` (6-digit code).

Routes (under `core/urls.py`): `phone/verify/send/`, `phone/verify/confirm/`.

### 4. Gating SMS notifications

Any "send SMS" path must short-circuit when `not user.phone_verified`. Add a
user preference (e.g. `sms_notifications_enabled`) and validate in forms that it
cannot be enabled without a verified phone.

## Security notes

- Rate-limit both **code issuance** (per phone) and **code attempts** (per row);
  lock/expire after N failed attempts.
- Codes are single-use and short-lived; never log the code in production.
- Normalise numbers to E.164 before send/compare (the form already strips
  separators via `core.forms.normalise_phone`).
- Resetting `phone_verified` to `False` on any phone change is mandatory.

## Testing checklist

- [ ] code issued, stored, and sent through the configured backend
- [ ] correct code within window → `phone_verified = True`
- [ ] expired / wrong code rejected; `phone_verified` unchanged
- [ ] rate limit blocks the 6th request within the window
- [ ] changing the phone number clears `phone_verified`
- [ ] SMS notification preference can't be enabled without a verified phone

## Out of scope (for now)

- SMS as a primary login factor or full 2FA enrolment
- WhatsApp / push fallbacks
- Per-country sender IDs / compliance (STOP handling, opt-in records)
