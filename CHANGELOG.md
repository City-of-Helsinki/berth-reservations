# [Unreleased]

<details>
  <summary>
    Changes that landed in develop and might be expected in the upcoming releases.
    Click to see more.
  </summary>
...
</details>

# rel/2020-10-28.1

**Added:** 
* CI config for the new production environment ([#347](https://github.com/City-of-Helsinki/berth-reservations/pull/347))
* Check for pending migrations on the review stage ([#345](https://github.com/City-of-Helsinki/berth-reservations/pull/345))
* Command to assign sticker numbers automatically ([#344](https://github.com/City-of-Helsinki/berth-reservations/pull/344))
* `storage on ice` additional service ([#346](https://github.com/City-of-Helsinki/berth-reservations/pull/346), [#342](https://github.com/City-of-Helsinki/berth-reservations/pull/342))
* Mutation to reject an application ([#335](https://github.com/City-of-Helsinki/berth-reservations/pull/335))

**Fixed:**
* Winter lease only allowed to last for a year ([#343](https://github.com/City-of-Helsinki/berth-reservations/pull/343))
* Update the local Postgres version to 11 ([#339](https://github.com/City-of-Helsinki/berth-reservations/pull/339))

# rel/2020-10-19.1

**Added:**
* GitLab pipeline for the new infra (only for staging) ([#322](https://github.com/City-of-Helsinki/berth-reservations/pull/322), [#323](https://github.com/City-of-Helsinki/berth-reservations/pull/323), [#324](https://github.com/City-of-Helsinki/berth-reservations/pull/324), [#325](https://github.com/City-of-Helsinki/berth-reservations/pull/325))
* Updates to the Django Admin ([#332](https://github.com/City-of-Helsinki/berth-reservations/pull/332), [#333](https://github.com/City-of-Helsinki/berth-reservations/pull/333))
* Sticker features for leases ([#327](https://github.com/City-of-Helsinki/berth-reservations/pull/327))
* Mutation to cancel orders ([#326](https://github.com/City-of-Helsinki/berth-reservations/pull/326), [#334](https://github.com/City-of-Helsinki/berth-reservations/pull/334))
* Disconnect customers from applications ([#329](https://github.com/City-of-Helsinki/berth-reservations/pull/329))

**Fixed:**
* Ignore empty OrderTokens when returning the payment url ([#336](https://github.com/City-of-Helsinki/berth-reservations/pull/336))

# rel/2020-10-15.1

**Added:**

- Add default section fixture for Merisatama ([#330](https://github.com/City-of-Helsinki/berth-reservations/pull/330))
