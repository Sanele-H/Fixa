"""Use cases: the rules of the app. Routes call these; these call the store. Owner: Role 3.

Keeping rules here (not in routes) means tests can check them without HTTP, and the
server stays the only place contact details can be released.
"""
