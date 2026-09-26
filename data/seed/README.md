# Demo seed data (P4)

P4's seed generator writes the demo data here. P2's seed loader reads it into SQLite locally and Supabase Postgres when live.

It needs:

- providers, each with a hidden true skill, trades, suburbs and some licences, and a hidden group label such as first language
- one provider with a long history, for the ARPL export demo
- customers, jobs and quotes

Agree the file format with P2 before writing the loader, then note it here. Only use made-up names, numbers and addresses.
