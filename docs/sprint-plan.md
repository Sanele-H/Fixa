# Sprint plan (summary)

This condenses the team's sprint plan page. Where they differ, the plan page wins.

## Scope

| Build for real | Keep simple or fake | Roadmap slide only |
|---|---|---|
| Translation with the trade glossary | Photo → trade (one AI call) | Home Affairs verification |
| Number, price and time protection | ID badges (static labels) | Voice skill questions |
| "See original" toggle | SMS confirmation of off-app jobs | Stock-photo detection |
| Contact masking in chat, including disguised numbers | Provider profiles (seed data) | Trusted-contact sharing and check-in |
| Server-enforced unlock flow | Scam warnings (a few rules) | WhatsApp entry point |
| Newcomer-friendly ranking | | PayShap payments |
| Fairness simulation with a chart | | ARPL portfolio export |

**Rule:** everything we build has to show up in the two-phone demo ([research/pitch/demo-script.md](../research/pitch/demo-script.md)). Anything else goes on the roadmap slide.

## Day by day

| Day | Goal | Role 1 | Role 2 | Role 3 | Role 4 |
|---|---|---|---|---|---|
| **Sat 26 Sep: Decide** | Scope, roles and demo story agreed | Everyone: pick the pilot area, 2–3 languages and 2–3 trades; everyone runs `npm run setup`; email the organisers | | | |
| Sun 27: Skeletons | Every part runs end to end, even if rough | 30 test messages; first real translation call | Screens clickable with mock data | Data model and job states | Book interviews; simulation v0 |
| Mon 28: Core | The hard parts work on their own | Number protection and glossary | Chat, quotes, unlock screens | Masking catches the 10 trickiest cases; unlock enforced on the server | First comparison numbers |
| Tue 29: Connect and test | Parts join up, and we test with real people | 30-message test on 2 backends | Frontend on the real backend (`VITE_USE_MOCK_API=false`) | Message pipeline end to end | Most interviews happen today |
| **Wed 30: Feature freeze** | Demo runs twice on two phones without help | Fix what the demo breaks | Fix what the demo breaks | Fix what the demo breaks | Final fairness chart |
| Thu 1 Oct: Polish and deck | Looks finished, story written | Results slide | Clean up screens; record the backup video | Safety slide | Full deck with quotes and test results |
| Fri 2: Rehearse | 3 timed run-throughs and Q&A | | | | Lead rehearsals |
| **Sat 3: Pitch** | Arrive early, test on the venue Wi-Fi, present | | | | |

**Gates:**
- **Day 1** is done when scope is frozen and everyone knows their role.
- **Day 5** is done when the demo runs start to finish twice without help. No new features after that night.

## Ask the organisers (Day 1)

- [ ] What are the judging criteria, and how are they weighted?
- [ ] How long is the pitch? Is there Q&A? Is a live demo expected?
- [ ] Is there a theme or track we should mention (for example social impact or AI)?
- [ ] Do they want the code or repo submitted, and by when?
- [ ] Can we use code or data we made before the hackathon (the glossary and speech-recognition work)?
