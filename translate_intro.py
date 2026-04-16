#!/usr/bin/env python3
"""Translate book intros to 8 languages using gemini-3.1-flash-lite API."""

import requests
import sys

headers = {"Authorization": "Bearer sk-2ws2ZbNo19IHKPMHu1WmyqIH5DeYApo6a1O7H2aflvjlh"}


def translate(text, lang):
    """Translate text to target language."""
    lang_names = {
        "bn": "Bengali",
        "fr": "French",
        "id": "Indonesian",
        "ru": "Russian",
        "ur": "Urdu",
        "es": "Spanish",
        "tr": "Turkish",
        "hi": "Hindi",
    }

    payload = {
        "model": "gemini-3.1-flash-lite",
        "messages": [
            {"role": "user", "content": f"Translate to {lang_names[lang]}:\n\n{text}"}
        ],
        "max_tokens": 2000,
        "temperature": 0.3,
    }

    response = requests.post(
        "http://localhost:8317/v1/chat/completions", headers=headers, json=payload
    )
    result = response.json()
    return result["choices"][0]["message"]["content"]


if __name__ == "__main__":
    text = sys.argv[1]
    lang = sys.argv[2]
    print(translate(text, lang))
