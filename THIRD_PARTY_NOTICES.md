# Third-party dependencies and sources

Maa-Agent project code is licensed under AGPL-3.0-only; see LICENSE.
The user-provided logo is project branding featuring game-related artwork;
the code license does not grant rights to third-party characters or artwork.

This repository exports project source only. It does not redistribute these
projects' binaries, OCR models, templates, documentation mirrors or game assets.
Users install upstream tools/resources separately; their licenses still apply.

- MAA Core: https://github.com/MaaAssistantArknights/MaaAssistantArknights
  License and additional README notices must be consulted (AGPLv3 license text).
- maa-cli: https://github.com/MaaAssistantArknights/maa-cli (AGPLv3 license text).
- MaaFramework 5.14.3: https://github.com/MaaXYZ/MaaFramework/tree/v5.14.3
  LGPLv3; installed as the maafw Python dependency.
- Pillow: https://github.com/python-pillow/Pillow (see upstream LICENSE).
- NumPy: https://github.com/numpy/numpy (see upstream LICENSE).
- Operator metadata: https://prts.wiki/ ; fetched on demand, with source recorded.
- Community battle scripts: https://prts.plus/ ; author terms must be checked
  individually. None are included in this repository.

Runtime observation copies selected models/templates from the user's installed
MAA resources into local cache. Do not publish that cache as project-owned assets.
This provenance list does not relicense any upstream material.
