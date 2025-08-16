# Todo

---
#### Short Term

- Implement the POST session as a non-blocking endpoint and have the UI ping a session progress endpoint every *X*ms
for discrete progress updates (both current action i.e. scaling video and rough percent).
- Redesign current SQLite schema and design the 'rest' of it, including all the metrics that we want to calculate
at this current stage.

---
#### Medium Term

- Fix/Improve all system and model level imports
- Implement full endpoint and services testing suite
- Full user input validation (primarily backend)
- Design UI structure (and decide if a framework like svelte is an optimal approach)

---

#### Long Term

- Complete overhaul of README.md
- Look into setting up and installer and uninstaller so that sqlite executable and app media can go back to 
being stored in local %appdata%
