import os
from fastapi import FastAPI, Request
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles

# ------------------------------------------------------
# Helper functions
# ------------------------------------------------------

def detect_platform(headers: dict) -> str:
    """Very rough detector for which platform sent the webhook."""
    h = {k.lower(): v for k, v in headers.items()}

    # Facebook / Instagram share x-hub-signature, you can refine later
    if "x-hub-signature" in h:
        if "instagram" in h["x-hub-signature"].lower():
            return "instagram"
        return "facebook"

    if "tiktok-signature" in h:
        return "tiktok"

    if "x-twitter-auth" in h:
        return "x"

    return "unknown"


def needs_manual_reply(text: str) -> bool:
    """Guess if a human should look at this message."""
    if not text:
        return False

    t = text.lower()

    urgent_words = [
        "help", "urgent", "problem", "question",
        "issue", "support", "can you", "please", "???"
    ]

    if any(w in t for w in urgent_words):
        return True

    # Long messages probably need human eyes
    if len(t) > 40:
        return True

    # Emojis as a rough signal of a real person
    if any(ch in text for ch in "🙂😊😢😭❤️"):
        return True

    return False


def nurse_greeting(name: str) -> str:
    """Simple, friendly nurse greeting."""
    return f"Hello {name}. How are you today? Is there anything you need?"


def pick(lst):
    return lst[0] if lst else ""


def render_template(t: str, **kw) -> str:
    return t.format(**kw)


def is_spam(t: str) -> bool:
    t = t.lower().strip()
    bad = ["buy followers", "crypto", "viagra", "casino", "loan"]
    return any(x in t for x in bad)


# ------------------------------------------------------
# App + config
# ------------------------------------------------------

app = FastAPI(title="Follower Greeter Bot", version="0.1.1-nurse")
app.mount("/static", StaticFiles(directory="../static"), name="static")

BRAND_NAME = os.getenv("BRAND_NAME", "Captain Lethargy")

NURSE_MEDIA_URL = os.getenv("NURSE_MEDIA_URL", "")
NURSE_CURTAIN_URL = os.getenv("NURSE_CURTAIN_URL", "")
NURSE_BED_URL = os.getenv("NURSE_BED_URL", "")
NURSE_NIL_URL = os.getenv("NURSE_NIL_URL", "")


class Message(BaseModel):
    name: str = "friend"
    text: str


DEFAULT_TEMPLATES = {
    "welcome": {
        "warm": [
            "Hey {NAME}! I’m {BRAND_NAME}. What are you into — guitars, lyrics, or good vibes?"
        ]
    },
    "probe": {
        "pro": [
            "Hello {NAME}. Are you interested in new releases, catalogue links, or something else?"
        ]
    },
    "boundary": {
        "pro": [
            "Hello {NAME}. This inbox is for music-related chat."
        ]
    },
}


# ------------------------------------------------------
# Routes
# ------------------------------------------------------

@app.get("/")
def health():
    """Simple health check."""
    return {"ok": True, "brand": BRAND_NAME}


@app.post("/reply")
async def reply(msg: Message, request: Request):
    """
    Main reply endpoint.

    - Uses nurse greeting when 'nurse' is mentioned.
    - Detects platform from headers.
    - Flags if a manual reply is probably needed.
    """
    platform = detect_platform(request.headers)
    manual_required = needs_manual_reply(msg.text)

    # 1) Spam guard
    if is_spam(msg.text):
        reply_text = render_template(
            pick(DEFAULT_TEMPLATES["boundary"]["pro"]),
            NAME=msg.name,
            BRAND_NAME=BRAND_NAME,
        )
        return {
            "reply": reply_text,
            "platform": platform,
            "manual_required": manual_required,
        }

    t = msg.text.lower()

    # 2) Nurse mode – just greet, check how they are, ask what they need
    if "nurse" in t:
        reply_text = nurse_greeting(msg.name)

        return {
            "reply": reply_text,
            "platform": platform,
            "manual_required": manual_required,
            "nurse_images": {
                "main": NURSE_MEDIA_URL,
                "curtain": NURSE_CURTAIN_URL,
                "bed": NURSE_BED_URL,
                "nil_by_mouth": NURSE_NIL_URL,
            },
        }

    # 3) Simple greeting words
    if any(word in t for word in ["hi", "hello", "hey", "yo"]):
        reply_text = render_template(
            pick(DEFAULT_TEMPLATES["welcome"]["warm"]),
            NAME=msg.name,
            BRAND_NAME=BRAND_NAME,
        )
        return {
            "reply": reply_text,
            "platform": platform,
            "manual_required": manual_required,
        }

    # 4) Default probe
    reply_text = render_template(
        pick(DEFAULT_TEMPLATES["probe"]["pro"]),
        NAME=msg.name,
        BRAND_NAME=BRAND_NAME,
    )
    return {
        "reply": reply_text,
        "platform": platform,
        "manual_required": manual_required,
    }


@app.get("/test-nurse")
async def test_nurse(request: Request):
    """
    Simple GET test endpoint so Keith can hit it from Safari.
    Pretends a follower called 'Keith' sent the word 'nurse'.
    """
    msg = Message(name="Keith", text="nurse")
    platform = detect_platform(request.headers)
    manual_required = needs_manual_reply(msg.text)

    reply_text = nurse_greeting(msg.name)

    return {
        "reply": reply_text,
        "platform": platform,
        "manual_required": manual_required,
        "nurse_images": {
            "main": NURSE_MEDIA_URL,
            "curtain": NURSE_CURTAIN_URL,
            "bed": NURSE_BED_URL,
            "nil_by_mouth": NURSE_NIL_URL,
        },
    }