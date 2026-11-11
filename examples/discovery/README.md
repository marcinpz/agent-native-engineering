# Local discovery fixture

`manifest.json` declares logical backend/web/mobile/store roots and dependencies.
These are not application implementations. No nested Git repositories are tracked.

From the project root, create **new, disposable local repositories** explicitly:

```sh
mkdir discovery-demo
for name in backend web mobile store; do
  mkdir "discovery-demo/$name"
  git -C "discovery-demo/$name" init
  git -C "discovery-demo/$name" -c core.hooksPath=/dev/null \
    -c user.name='Demo' -c user.email='demo@example.invalid' \
    commit --allow-empty -m 'Local discovery fixture'
done
uv run python - <<'PY'
import json
from pathlib import Path
from lsm.discovery import discover
from lsm.storage import save_model

manifest = json.loads(Path('examples/discovery/manifest.json').read_text())
model = discover(manifest, Path('discovery-demo'))
assert discover(manifest, Path('discovery-demo'), model) == model
save_model(model, Path('discovery-demo/model.json'))
PY
uv run lsm validate discovery-demo/model.json
```

Only the setup commands create repositories. Discovery does not write or execute
repository scripts. All emitted claims are unverified; a recorded commit does not
verify the declared architecture. See [the API contract](../../docs/DISCOVERY.md).
