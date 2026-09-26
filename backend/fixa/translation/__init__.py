"""Glossary-aware translation that never changes prices, times or numbers. Owner: Role 1.

Flow for one message (see pipeline.py):
    protect_tokens -> backend.translate (with glossary hints) -> restore_tokens -> flag if unsure
"""
