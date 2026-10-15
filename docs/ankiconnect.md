# AnkiConnect

[AnkiConnect](https://foosoft.net/projects/anki-connect/) is the API most Anki tools use: browser extensions (Yomitan), note-taking plugins (Obsidian to Anki), scripts. It's an add-on, so it normally needs the desktop app running. The stack offers it two ways.

## The worker's API (always on)

The worker answers AnkiConnect's protocol (version 6) at `ANKICONNECT_BIND` (`http://127.0.0.1:8765` by default), with no desktop. Every request needs the key:

```bash
curl -s http://127.0.0.1:8765 -d '{"action":"deckNames","version":6,"key":"<ANKICONNECT_KEY>"}'
```

`anki-stack endpoint --show-token` prints the key. For a browser extension, add its origin to `ANKICONNECT_CORS`.

Supported actions:

| | |
|---|---|
| Decks | `deckNames`, `deckNamesAndIds`, `createDeck`, `deleteDecks`, `changeDeck`, `getDecks` |
| Note types | `modelNames`, `modelNamesAndIds`, `modelFieldNames` |
| Notes | `addNote`, `addNotes`, `canAddNotes`, `findNotes`, `notesInfo`, `updateNoteFields`, `updateNote`, `updateNoteTags`, `deleteNotes` |
| Cards | `findCards`, `cardsInfo`, `cardsToNotes`, `suspend`, `unsuspend`, `areSuspended`, `getNumCardsReviewedToday` |
| Tags | `getTags`, `addTags`, `removeTags` |
| Media | `storeMediaFile`, `retrieveMediaFile`, `getMediaFilesNames`, `deleteMediaFile`, `getMediaDirPath` |
| Other | `version`, `requestPermission`, `sync`, `multi` |

Anything else answers `unsupported action`. Two differences from the add-on: `addNote` creates a missing deck rather than refusing, and nothing that needs a screen (opening the browser or the add-cards window, the review GUI) exists.

## The real add-on (the desktop)

For actions the worker doesn't have, run the [desktop](desktop.md) with AnkiConnect on:

```bash
anki-stack desktop on
anki-stack desktop ankiconnect on
```

It answers at `DESKTOP_ANKICONNECT_BIND` (`http://127.0.0.1:8766`), with the same key. It's the add-on itself (a pinned version), running inside the desktop app, so everything AnkiConnect can do works, as long as the desktop is running.
