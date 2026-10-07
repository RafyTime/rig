# Rig

Rig keeps a personal agent setup consistent across machines.

## Language

**Setup repo**:
The authoritative repository containing the user's shared agent instructions and selected skills. It may also contain Rig's application code.

**Installed copy**:
The instructions or skill files in a location where an agent uses them on a machine.

**Sync**:
Bringing a machine's managed setup into agreement with the setup repo, including installing selected skills that are missing locally.

**Skill update**:
An explicit change to a downloaded skill using its upstream source, reflected in both the installed copy and the setup repo.

**Adoption**:
Establishing management of existing local files by comparing them with the setup repo and choosing which content to keep when they differ.

**Downloaded skill**:
A selected skill obtained from an upstream source and intended to retain that source's content.

**Custom skill**:
A skill whose content the user owns and maintains, including an intentionally customized former downloaded skill.

**Skill snapshot**:
The stored contents of a selected downloaded skill at a chosen point in time.
