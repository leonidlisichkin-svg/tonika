# Vision

## The problem

Voice is becoming a default interface: narrated video, audiobooks, voice agents, accessibility.
Every one of them depends on a TTS engine reading text correctly. In many languages the spelling
does not say how a word sounds:

- Russian, Ukrainian, Belarusian: unwritten, movable stress (за́мок / замо́к) and the letter ё (все / всё).
- English: heteronyms (read / read, lead / lead).
- Mandarin: characters with several readings.
- Hebrew, Arabic: vowels that are usually not written.

Engines guess, and a wrong guess is one of the most audible defects in synthetic speech.

## What Tonika is

An open pronunciation layer that sits in front of any TTS engine. Text goes in; the same text
comes out, marked so the engine reads it as the author meant.

It rests on three assets, in order of long-term value:

1. **An open dataset** of sentences with the correct reading of a word in context. Anyone can
   correct it; every change is reviewed and versioned. "Wikipedia for pronunciation."
2. **An engine** with language packs behind one interface. It wraps the best open model for each
   language and, where none exists, learns from the dataset.
3. **Renderers and engine presets** that turn one decision into the notation each TTS understands,
   plus a public compatibility map of what each engine actually honours.

## Who it is for

- Creators who voice long scripts and cannot proofread every word by ear.
- Developers of voice agents who need fast, deterministic pronunciation control.
- TTS vendors who need open evaluation data for languages they do not speak.

## What success looks like

- A 30-minute Russian script voiced with no stress errors after one pass.
- Tonika is the default text transform in open voice-agent frameworks.
- Every language with a contributor community has a golden set and a published accuracy figure.

## What Tonika is not

- Not a TTS engine. It makes every engine better.
- Not a promise of "all languages at once". Coverage grows by tier, honestly reported:
  **A** context-aware, **B** dictionary stress, **C** user dictionary only.
